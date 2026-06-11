🎬 KwaiDub AI — Emotional Video Dubbing Toolkit

Download → Transcribe → Translate → Dub (Single-Person Voice, Emotion Mimic)
🔥 Give any video a voice in YOUR language — copying the ORIGINAL speaker's emotion!

https://img.shields.io/badge/Python-3.12-blue.svg
https://img.shields.io/badge/Docker-Ready-2496ED.svg
https://img.shields.io/badge/License-MIT-yellow.svg
https://img.shields.io/badge/⭐_Star_me_on_GitHub-100?style=social

---

<p align="center">
  <img src="https://github.com/user-attachments/assets/a0bc7d2d-7d84-4561-b131-59aa9fd2928a" alt="KwaiDub UI" width="300"/>
</p>

---

🤯 What Is This?

Found an amazing Chinese/YouTube/TikTok video in a language you don't understand?
Want to dub it into Bengali, English, or Hindi — but with the original speaker's emotion?

KwaiDub AI solves all of that:

· ✅ YouTube, TikTok, Instagram, Kuaishou — paste ANY URL
· ✅ Exact word-level subtitles (Groq Whisper Large v3)
· ✅ Auto-translate Chinese → Bengali/English (Groq LLaMA 3.3)
· ✅ THREE TTS engines — including Emotion Mimic
· ✅ FREE TTS (Edge‑TTS) — no API key needed
· ✅ YouTube bot bypass via Xray/V2Ray local SOCKS5 proxy

---

🔥 THE KILLER FEATURE: Emotion Mimic

<p align="center">
  <img src="https://github.com/user-attachments/assets/1968a3ed-ca86-47ca-9360-cba571018d93" alt="Dubbing progress" width="300"/>
</p>

Normal AI dubs = flat, robotic voice.
KwaiDub's Emotion Mimic = Gemini listens to the original audio, captures the emotion, pace, pitch, energy, and recreates it in the new language!

Chinese video with angry shouting → Bengali dub ALSO sounds angry and intense!
Slow, emotional speech → The dub preserves that exact mood!

This is not just TTS — it's emotional voice cloning for dubbing.

📹 See it in action: Demo Video

---

🚀 Quick Start (No Setup — Docker Only)

1. Pull & Run

```bash
docker pull your-dockerhub/kwaidub-ai:latest
docker run -d -p 3000:3000 --name kwaidub your-dockerhub/kwaidub-ai:latest
```

Open http://localhost:3000 and start dubbing!
No Python install, no pip, no requirements.txt needed.

---

🔑 API Keys Setup (Important!)

📝 Groq API Key (for Transcription & Translation)

1. Go to console.groq.com
2. Sign up (free credits available)
3. Create an API key → it starts with gsk_
4. Paste it in the "Groq API Keys" box (multiple keys separated by newline)

⚠️ For Translation, use Groq (LLaMA), NOT Gemini!
Gemini's free tier often blocks translation requests from Bangladesh.
Groq (LLaMA 3.3 70B) handles Chinese→Bengali translation perfectly.

🎙️ Gemini API Keys (for TTS — Optional)

1. Create 13-14 different Google accounts (yes, you read that right!)
2. For each account, go to Google AI Studio
3. Click "Get API key" → "Create API key"
4. Copy each key (they start with AIza...)
5. Paste ALL 13-14 keys in the "Gemini API Keys" box — one per line

Why 13-14 accounts?
Gemini TTS free tier = only 15 requests per minute per key.
A 2-minute video can have 30-40 subtitle segments.
With 13 keys rotating, you'll get 195 requests/minute — enough for smooth dubbing!

---

🛡️ YouTube Bot Bypass (V2Ray / Xray)

YouTube may rate-limit or block automated downloads.
KwaiDub uses Xray/V2Ray to create a local SOCKS5 proxy for bypassing.

Get a free V2Ray node:

1. Visit www.v2nodes.com
2. Copy any vmess:// or vless:// link
3. In the app: Setup tab → Paste the link → "Save & Start"
4. Click "Test Proxy" to verify

The proxy auto-starts in the container and routes only yt-dlp traffic through it.
Works with any vmess/vless provider — not just v2nodes.

---

🎨 Features

Feature Status Details
🌐 Multi-platform ✅ YouTube, TikTok, Instagram, Kuaishou
🎯 Word-level Transcript ✅ Groq Whisper Large v3
🌍 Auto Translate ✅ Chinese → Bengali/English (Groq LLaMA)
🎙️ TTS Providers ✅ Gemini Normal / Emotion Mimic / Edge‑TTS (FREE)
🎭 Emotion Mimic ✅ Copies original speaker's emotion & tone
🔑 Key Rotation ✅ Auto-rotates 13+ Gemini keys to bypass limits
🛡️ YouTube Bypass ✅ Built-in Xray/V2Ray local SOCKS5 proxy
🍪 YouTube Cookies ✅ For age-restricted / login-required videos
🎛️ Pitch & Speed ✅ Fine-tune Edge‑TTS voice (-5% pitch, +12% speed)
📥 One-click Download ✅ Final dubbed video direct download
🐳 Docker Deploy ✅ No requirements.txt — just run the image
👤 Single-Person Voice ✅ Current version (multi-person coming soon!)

---

🎭 TTS Engines Compared

 Gemini Normal Gemini Emotion Mimic 🔥 Edge‑TTS (FREE)
Cost Free tier (15 RPM) Free tier (15 RPM) Completely FREE
Voice Quality Good Excellent + Emotional Very Good
Emotion Copy ❌ ✅ Copies original! ❌
Languages English, Hindi, etc. English, Hindi + more Bengali, Chinese, 50+
API Key Required (13+ for smooth) Required (13+ for smooth) NOT needed!

---

📸 Screenshots

<p align="center">
  <img src="https://github.com/user-attachments/assets/4c04862e-62d0-439c-aaad-4495479d1648" alt="Main Interface" width="280"/>
  <img src="https://github.com/user-attachments/assets/71dc9af7-c6ad-414f-a911-4ff1695a465c" alt="Segment view" width="280"/>
  <img src="https://github.com/user-attachments/assets/196eabf4-38d2-4090-89a0-497a3118548f" alt="Setup tab" width="280"/>
</p>

---

🧠 How Emotion Mimic Works

1. Transcribe the video → saves the original job_id.mp3
2. For each subtitle segment:
   · Cut original audio chunk (ffmpeg -ss start -to end)
   · Convert to base64
   · Send to Gemini Multimodal (audio + text in, audio out):
     "Listen to this audio. Copy the emotion, tone, pace. Now speak THIS text."
   · Gemini returns new audio with the same emotion!
3. Replace original audio track with new segments (ffmpeg amix)

---

🛠️ Tech Stack

· Backend: Python 3.12, Flask, asyncio
· Container: Docker (single image, no external deps)
· Transcription: Groq API (Whisper Large v3)
· Translation: Groq LLaMA 3.3 70B (NOT Gemini — blocked in Bangladesh)
· TTS: Gemini TTS, Edge‑TTS (Microsoft)
· Audio Processing: FFmpeg, ffprobe
· Video Download: yt‑dlp, httpx
· Proxy: Xray core (vmess/vless → local SOCKS5)

---

📦 Docker Deployment Only

No requirements.txt. No pip install. Just Docker.

```bash
# Build yourself
docker build -t kwaidub-ai .
docker run -d -p 3000:3000 --name kwaidub kwaidub-ai

# Or pull from registry
docker run -d -p 3000:3000 your-registry/kwaidub-ai:latest
```

---

🚧 Roadmap

· Single-person voice dubbing
· Emotion Mimic (Gemini multimodal)
· YouTube/TikTok/Kuaishou support
· V2Ray/Xray local proxy
· Multi-person voice separation (coming soon!)
· Speaker diarization
· More TTS engines (Azure, ElevenLabs)
· WebUI dark/light themes

---

🌟 Why This Will Work

1. FREE & Open Source — Edge‑TTS needs NO API key
2. Emotion Mimic — First open-source tool with emotional dubbing
3. Works on ANY platform — YouTube, TikTok, Instagram, Kuaishou
4. Any language pair — Chinese audio → Bengali/English/Hindi dub
5. One-click — Paste URL → Get dubbed video
6. YouTube bypass built-in — No more geo-blocks
7. Docker only — Zero setup, runs anywhere

---

⚠️ Disclaimer

This tool is for educational and personal use only.
Respect copyright laws. Do not redistribute dubbed content without proper rights.

---

⭐ Star This Repo!

If this tool helped you dub even ONE video, drop a ⭐ — it motivates us to add multi-person voice support!

<p align="center">
  <b>Made with ❤️ by a developer who just wanted to watch Chinese videos in Bengali</b><br>
  <sub>Single-person now, multi-person soon 🚀</sub>
</p>
