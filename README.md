# 🎬 Google Drive Video to SRT Generator

A production-ready web tool that takes any video stored on **Google Drive**, extracts its audio, transcribes it with **open-source Whisper**, and outputs timed **SubRip (.SRT) subtitles**.

Features:
- 🔗 **Google Drive Ingestion:** Accepts any shareable Google Drive link or File ID.
- 🔊 **Lightweight ffmpeg Audio Extraction:** Strips 16kHz mono audio on the fly to maximize processing speed.
- 🤖 **Open-Source Whisper:**
  - **Local Whisper (`faster-whisper`):** Runs 100% free open-source models on CPU/GPU (`tiny`, `base`, `small`, `medium`).
  - **Cloud Turbo Mode (Groq `whisper-large-v3`):** High-speed hosted open-source Whisper (transcribes a 10-minute video in ~3 seconds with zero server memory footprint).
- 📥 **Direct Browser Download:** Instantly download the formatted `.srt` file to your computer.
- ☁️ **Auto-Upload to Google Drive:** Optionally uploads the generated `.srt` directly into the original Google Drive folder alongside the video.
- 🚀 **Deploy-Ready for Render:** Complete with `Dockerfile` and `render.yaml` for 1-click team deployment.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/NikhileshAdiyala/gdrive-video-to-srt)

---

## 🏗️ Architecture: Why Render instead of Vercel?

| Platform | Fit for this tool | Why? |
| :--- | :--- | :--- |
| **Render (Recommended)** | ✅ **Perfect** | Supports persistent Docker services, background execution, unlimited video processing duration, and full `ffmpeg` installation. |
| **Vercel** | ❌ **Not Recommended** | Vercel is designed for serverless frontends. It has strict execution timeouts (10s–60s limit), a 4.5MB payload limit, and cannot run heavy media processing or `ffmpeg`. |

---

## 🍎 Running on macOS (MacBook Air / Mac Studio)

### Option 1: 1-Click Desktop Launcher
Simply double-click:
```bash
run_mac.command
```
This automatically initializes a local virtual environment, installs dependencies, and launches the app in your browser at `http://localhost:8501`.

### Option 2: Command-Line (CLI) Direct Video to SRT
If you have a video file and just want `.srt` directly without opening a browser:
```bash
python video_to_srt.py "path/to/my_video.mp4"
```
Options:
```bash
# High accuracy with larger model (recommended on Mac Studio / Air 16GB+)
python video_to_srt.py interview.mov --model medium

# Specify language
python video_to_srt.py film.mp4 --language en
```

---

## 🚀 Running Locally (Linux / Windows / Manual)

### 1. Prerequisites
Ensure you have `ffmpeg` installed on your machine:
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install -y ffmpeg
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Web App
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🌐 Deploying to Render (for Team Access)

### Option A: 1-Click via Docker on Render (Easiest)
1. Push this folder to a GitHub repository (e.g. `your-org/gdrive-video-to-srt`).
2. Log into [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. In **Runtime**, select **Docker**.
6. (Optional) Under **Environment Variables**, set:
   - `GROQ_API_KEY`: *(Optional)* Your free Groq API key if you want instant 3-second transcription.
   - `GDRIVE_SERVICE_ACCOUNT_JSON`: *(Optional)* Service Account credentials to enable auto-uploading back to Drive.
7. Click **Create Web Service**. Render will automatically build the Docker image and provide a live public HTTPS URL for your team!

### Option B: Deploy via Render Blueprint (`render.yaml`)
1. Click **New +** -> **Blueprint**.
2. Select your repository containing `render.yaml`.
3. Render will configure the port, health checks, and Docker environment automatically.

---

## 🔑 Google Drive Auto-Upload Setup (Optional)

To enable uploading the `.srt` directly back into the same Google Drive folder:
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Drive API**.
3. Create a **Service Account** and download its JSON key file.
4. Share the Google Drive video folder with your Service Account's email address (with **Editor** permissions).
5. Paste the JSON into the app sidebar, or set it as the environment variable:
   ```bash
   GDRIVE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
   ```

---

## 🧪 Testing the Pipeline
You can run the built-in unit tests:
```bash
python3 test_pipeline.py
```
