# ─────────────────────────────────────────────────────────────────────────────
# tts_job_routes.py  —  এটা app.py তে paste করো (existing routes এর আগে)
#
# zip প্রজেক্টের মতো:
#   1. Job server-side JSON এ save হয়  →  refresh করলেও হারায় না
#   2. প্রতিটা segment আলাদা file হিসেবে save  →  crash হলে resume করে
#   3. Key rotation: সব key একবার ঘুরে 429 হলে 60s wait, তারপর আবার
#   4. SSE দিয়ে live progress browser এ দেখায়
# ─────────────────────────────────────────────────────────────────────────────

import os, json, time, uuid, base64, struct, subprocess, asyncio, threading
from pathlib import Path
from flask import request, jsonify, Response, stream_with_context
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
TEMP_DIR   = os.environ.get("TEMP_DIR", "/tmp/asr")
JOBS_DIR   = os.path.join(TEMP_DIR, "tts_jobs")
Path(JOBS_DIR).mkdir(parents=True, exist_ok=True)

GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_TTS_URL   = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_TTS_MODEL}:generateContent?key={{key}}"
)
EDGE_TTS_SAMPLE_RATE = 24000

# ── Job helpers ───────────────────────────────────────────────────────────────
def _job_path(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.json")

def _seg_wav_path(job_id: str, idx: int) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}_seg{idx}.wav")

def load_job(job_id: str) -> dict | None:
    p = _job_path(job_id)
    if not os.path.exists(p):
        return None
    try:
        return json.loads(open(p).read())
    except Exception:
        return None

def save_job(job: dict):
    open(_job_path(job["id"]), "w").write(json.dumps(job, ensure_ascii=False, indent=2))

def _pcm_to_wav(pcm: bytes, sample_rate=24000) -> bytes:
    num_channels    = 1
    bits_per_sample = 16
    data_size       = len(pcm)
    byte_rate       = sample_rate * num_channels * (bits_per_sample // 8)
    block_align     = num_channels * (bits_per_sample // 8)
    chunk_size      = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
        num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    return header + pcm

# ── Gemini TTS (একটা segment) ─────────────────────────────────────────────────
async def _gemini_tts_once(text: str, voice: str, api_key: str) -> bytes:
    """Raw PCM bytes ফেরত দেয়। 429 হলে raise করে।"""
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            },
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(GEMINI_TTS_URL.format(key=api_key), json=payload)
        if resp.status_code == 429:
            raise httpx.HTTPStatusError("429", request=resp.request, response=resp)
        resp.raise_for_status()
        data = resp.json()
        b64 = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("inlineData", {})
            .get("data")
        )
        if not b64:
            raise ValueError("Gemini returned no audio data")
        return base64.b64decode(b64)

# ── Edge-TTS fallback ─────────────────────────────────────────────────────────
async def _edge_tts_once(text: str, voice="bn-IN-TanishaaNeural",
                          pitch="-5Hz", rate="+12%") -> bytes:
    import edge_tts, tempfile
    fd, mp3 = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        comm = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
        await comm.save(mp3)
        fd2, wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd2)
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3,
             "-ar", "24000", "-ac", "1", "-sample_fmt", "s16", wav],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with open(wav, "rb") as f:
            wav_bytes = f.read()
        return wav_bytes[44:]  # raw PCM
    finally:
        for p in (mp3, wav if "wav" in dir() else ""):
            try:
                if p: os.unlink(p)
            except Exception:
                pass

# ── zip-এর মতো key rotation logic ────────────────────────────────────────────
async def synthesize_one_segment(
    text: str, voice: str, gemini_keys: list[str],
    edge_pitch="-5Hz", edge_rate="+12%",
    key_idx_ref: list = None,   # [current_idx]  — mutable ref
) -> tuple[bytes, str]:
    """
    Returns (pcm_bytes, provider_used)
    zip এর মতো:
      - সব key একবার ঘুরায়
      - সবাই 429  →  60s sleep  →  আবার ঘুরায়  (max 3 full rounds)
      - তারপর Edge-TTS fallback
    """
    if not gemini_keys:
        pcm = await _edge_tts_once(text, pitch=edge_pitch, rate=edge_rate)
        return pcm, "edge"

    if key_idx_ref is None:
        key_idx_ref = [0]

    MAX_ROUNDS   = 3
    cooldown_sec = 60

    for round_num in range(MAX_ROUNDS):
        all_limited = True
        for _ in range(len(gemini_keys)):
            key = gemini_keys[key_idx_ref[0] % len(gemini_keys)]
            key_idx_ref[0] += 1
            try:
                pcm = await _gemini_tts_once(text, voice, key)
                return pcm, f"gemini(key#{key_idx_ref[0] % len(gemini_keys)})"
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    continue   # next key
                raise
            except Exception:
                raise

        # পুরো একটা round শেষ — সব key limited
        if round_num < MAX_ROUNDS - 1:
            await asyncio.sleep(cooldown_sec)

    # সব round শেষ → Edge fallback
    pcm = await _edge_tts_once(text, pitch=edge_pitch, rate=edge_rate)
    return pcm, "edge-fallback"

# ── Background worker thread ──────────────────────────────────────────────────
def _run_tts_job(job_id: str):
    """
    Blocking worker — thread এ চলে।
    zip এর synthesize_speech_worker এর মতো:
      - segment file আগে থেকে থাকলে skip (resume)
      - নতুন হলে TTS করে file save
      - job JSON update করে progress track করে
    """
    job = load_job(job_id)
    if not job:
        return

    job["status"]     = "running"
    job["started_at"] = time.time()
    save_job(job)

    segments   = job["segments"]
    keys       = job.get("gemini_keys", [])
    voice      = job.get("voice", "Charon")
    pitch      = job.get("edge_pitch", "-5Hz")
    rate       = job.get("edge_rate", "+12%")
    key_idx    = [job.get("_key_idx", 0)]   # resume করলে rotation continue করে

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for i, seg in enumerate(segments):
            wav_path = _seg_wav_path(job_id, i)

            # ── Resume: file আগে থেকে আছে? ──────────────────────────────────
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
                seg["status"]   = "done"
                seg["wav_path"] = wav_path
                job["done"]     = i + 1
                save_job(job)
                continue

            seg["status"] = "processing"
            job["current"] = i
            save_job(job)

            try:
                pcm, provider = loop.run_until_complete(
                    synthesize_one_segment(
                        text       = seg["text"],
                        voice      = voice,
                        gemini_keys= keys,
                        edge_pitch = pitch,
                        edge_rate  = rate,
                        key_idx_ref= key_idx,
                    )
                )
                wav_bytes = _pcm_to_wav(pcm)
                with open(wav_path, "wb") as f:
                    f.write(wav_bytes)

                seg["status"]   = "done"
                seg["wav_path"] = wav_path
                seg["provider"] = provider

            except Exception as e:
                seg["status"] = "error"
                seg["error"]  = str(e)

            job["done"]     = sum(1 for s in segments if s["status"] == "done")
            job["_key_idx"] = key_idx[0]
            save_job(job)

        job["status"] = "complete"
        save_job(job)

    except Exception as e:
        job["status"] = "error"
        job["error"]  = str(e)
        save_job(job)
    finally:
        loop.close()


# ══════════════════════════════════════════════════════════════════════════════
# Flask Routes  —  app.py তে এগুলো যোগ করো
# ══════════════════════════════════════════════════════════════════════════════

def register_tts_routes(app):
    """
    app.py তে এইভাবে call করো:

        from tts_job_routes import register_tts_routes
        register_tts_routes(app)
    """

    # ── POST /tts/start  →  job তৈরি করে background এ শুরু করে ──────────────
    @app.route("/tts/start", methods=["POST"])
    def tts_start():
        data = request.get_json(force=True)
        segments    = data.get("segments", [])       # [{start, end, text}, ...]
        gemini_keys = data.get("gemini_keys", [])
        voice       = data.get("voice", "Charon")
        edge_pitch  = data.get("edge_pitch", "-5Hz")
        edge_rate   = data.get("edge_rate", "+12%")
        resume_id   = data.get("resume_id", "").strip()

        if not segments:
            return jsonify({"error": "segments required"}), 400

        # resume: পুরনো job আছে কিনা চেক
        if resume_id:
            old_job = load_job(resume_id)
            if old_job and old_job.get("status") not in ("complete", "error"):
                # আগের job চলছে বা pending — একই id ফেরত
                return jsonify({"job_id": resume_id, "resumed": True})

        job_id = uuid.uuid4().hex[:12]
        job = {
            "id":          job_id,
            "status":      "pending",
            "created_at":  time.time(),
            "gemini_keys": gemini_keys,
            "voice":       voice,
            "edge_pitch":  edge_pitch,
            "edge_rate":   edge_rate,
            "done":        0,
            "total":       len(segments),
            "current":     -1,
            "_key_idx":    0,
            "segments": [
                {
                    "idx":    i,
                    "start":  s["start"],
                    "end":    s["end"],
                    "text":   s["text"],
                    "status": "pending",
                }
                for i, s in enumerate(segments)
            ],
        }
        save_job(job)

        t = threading.Thread(target=_run_tts_job, args=(job_id,), daemon=True)
        t.start()

        return jsonify({"job_id": job_id, "resumed": False})


    # ── GET /tts/status/<job_id>  →  SSE stream (live progress) ──────────────
    @app.route("/tts/status/<job_id>")
    def tts_status(job_id):
        def generate():
            last_done = -1
            while True:
                job = load_job(job_id)
                if not job:
                    yield f"event: error\ndata: {json.dumps({'msg': 'job not found'})}\n\n"
                    return

                done  = job.get("done", 0)
                total = job.get("total", 1)
                curr  = job.get("current", -1)

                if done != last_done or job["status"] in ("complete", "error"):
                    # current segment এর info
                    seg_info = ""
                    if 0 <= curr < len(job["segments"]):
                        seg_info = job["segments"][curr].get("text", "")[:30]

                    yield (
                        f"event: progress\n"
                        f"data: {json.dumps({'done': done, 'total': total, 'current': curr, 'seg_text': seg_info, 'status': job['status']})}\n\n"
                    )
                    last_done = done

                if job["status"] in ("complete", "error"):
                    # সব segment এর result পাঠাও
                    results = []
                    for s in job["segments"]:
                        wav_path = s.get("wav_path", "")
                        if s["status"] == "done" and wav_path and os.path.exists(wav_path):
                            with open(wav_path, "rb") as f:
                                wav_bytes = f.read()
                            pcm_bytes = wav_bytes[44:]   # header skip
                            results.append({
                                "idx":      s["idx"],
                                "start":    s["start"],
                                "end":      s["end"],
                                "pcm_b64":  base64.b64encode(pcm_bytes).decode(),
                                "provider": s.get("provider", "?"),
                            })
                        else:
                            results.append({
                                "idx":    s["idx"],
                                "start":  s["start"],
                                "end":    s["end"],
                                "error":  s.get("error", "failed"),
                            })

                    yield (
                        f"event: done\n"
                        f"data: {json.dumps({'results': results, 'status': job['status']})}\n\n"
                    )
                    return

                time.sleep(1.5)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )


    # ── GET /tts/job/<job_id>  →  JSON snapshot (refresh recovery) ───────────
    @app.route("/tts/job/<job_id>")
    def tts_job_get(job_id):
        job = load_job(job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        # key গুলো expose করি না
        safe = {k: v for k, v in job.items() if k not in ("gemini_keys", "_key_idx")}
        return jsonify(safe)


    # ── DELETE /tts/job/<job_id>  →  job + files মুছে দাও ───────────────────
    @app.route("/tts/job/<job_id>", methods=["DELETE"])
    def tts_job_delete(job_id):
        job = load_job(job_id)
        if job:
            for i in range(job.get("total", 0)):
                p = _seg_wav_path(job_id, i)
                try:
                    os.unlink(p)
                except Exception:
                    pass
        p = _job_path(job_id)
        try:
            os.unlink(p)
        except Exception:
            pass
        return jsonify({"ok": True})
