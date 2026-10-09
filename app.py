import os
import io
import zipfile
import tempfile
import streamlit as st
from utils import extract_gdrive_file_id, extract_audio_from_video
from downloader import download_from_gdrive
from transcriber import transcribe_local_whisper, transcribe_cloud_whisper
from gdrive_uploader import upload_srt_to_gdrive

st.set_page_config(
    page_title="Google Drive Video to SRT Subtitles",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        color: white;
    }
    .success-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #ECFDF5;
        border: 1px solid #10B981;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    transcription_engine = st.radio(
        "Transcription Engine",
        ["Local Whisper (faster-whisper)", "Cloud Turbo (Groq whisper-large-v3)"],
        help="Local uses the open-source model on your host/container. Cloud Turbo uses high-speed open-source Whisper via Groq."
    )
    
    if "Local" in transcription_engine:
        model_size = st.selectbox(
            "Whisper Model Size",
            ["base", "tiny", "small", "medium", "large-v3"],
            index=0,
            help="'tiny' and 'base' are fastest. 'medium' and 'large-v3' offer highest accuracy on Macs with 8GB+ RAM."
        )
        groq_api_key = None
    else:
        model_size = "whisper-large-v3"
        groq_api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=os.environ.get("GROQ_API_KEY", ""),
            help="Get a free key at console.groq.com. Processes a 10-minute video in ~3 seconds."
        )

    language = st.selectbox(
        "Spoken Language",
        ["Auto-detect", "English", "Hindi", "Spanish", "French", "German", "Italian", "Portuguese", "Japanese", "Chinese"],
        index=0
    )
    selected_lang_code = None if language == "Auto-detect" else language.lower()

    st.markdown("---")
    st.subheader("☁️ Google Drive Upload")
    auto_upload_drive = st.checkbox(
        "Upload SRT back to same Google Drive folder",
        value=bool(os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")),
        help="Uploads the generated .srt file directly into the original Google Drive folder alongside the video."
    )
    
    service_account_json = None
    if auto_upload_drive and not os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON"):
        service_account_input = st.text_area(
            "Google Service Account JSON",
            help="Paste your Google Cloud Service Account JSON key to grant write access to Drive.",
            placeholder='{"type": "service_account", "project_id": ...}'
        )
        if service_account_input.strip():
            service_account_json = service_account_input.strip()


# Main Page Header
st.markdown('<div class="main-header">🎬 Video to SRT Subtitles Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Give any video file directly or paste a Google Drive link — audio is extracted automatically using ffmpeg and transcribed with Whisper.</div>', unsafe_allow_html=True)

tab_local, tab_gdrive = st.tabs(["📁 Local Video Files (Drag & Drop)", "🔗 Google Drive Link(s)"])

with tab_local:
    uploaded_files = st.file_uploader(
        "Drop your video file(s) here (MP4, MOV, MKV, AVI, WebM, etc.)",
        type=["mp4", "mov", "mkv", "avi", "webm", "m4v", "flv", "mp3", "wav", "m4a"],
        accept_multiple_files=True,
        help="Select one or multiple heavy raw video files — audio will be stripped automatically using ffmpeg."
    )
    if uploaded_files:
        total_size_mb = sum(f.size for f in uploaded_files) / (1024 * 1024)
        if total_size_mb >= 1024:
            st.info(f"📁 **{len(uploaded_files)} file(s) selected** ({total_size_mb / 1024:.2f} GB total)")
        else:
            st.info(f"📁 **{len(uploaded_files)} file(s) selected** ({total_size_mb:.1f} MB total)")
            
    btn_local = st.button("🚀 Generate Subtitles for Selected Files", use_container_width=True, key="btn_local")

with tab_gdrive:
    gdrive_input = st.text_area(
        "Google Drive Video Link(s) or File ID(s) — one per line",
        placeholder="https://drive.google.com/file/d/1A2B3C4D5E.../view?usp=sharing\nhttps://drive.google.com/file/d/2F3G4H.../view?usp=sharing",
        help="Paste one or multiple shareable Google Drive links or File IDs (one per line).",
        height=100
    )
    btn_gdrive = st.button("🚀 Generate Subtitles from Google Drive", use_container_width=True, key="btn_gdrive")

col_info1, col_info2 = st.columns([1, 1])
with col_info1:
    st.caption("💡 Supports multiple raw video files (MP4, MOV, MKV, etc.) — audio extracted in seconds via ffmpeg.")
with col_info2:
    st.caption("🔒 All processing runs locally/privately with stream-to-disk and automatic temp cleanup.")

# Build Task List
tasks = []

if btn_local:
    if not uploaded_files:
        st.warning("⚠️ Please select or drop at least one video file first.")
    else:
        for f in uploaded_files:
            tasks.append({"type": "local", "input": f, "name": f.name})

elif btn_gdrive:
    if not gdrive_input.strip():
        st.warning("⚠️ Please provide at least one valid Google Drive video URL or File ID.")
    else:
        lines = [line.strip() for line in gdrive_input.strip().splitlines() if line.strip()]
        for line in lines:
            file_id = extract_gdrive_file_id(line)
            if file_id:
                tasks.append({"type": "gdrive", "input": file_id, "name": file_id})
            else:
                st.error(f"❌ Could not extract a valid Google Drive File ID from: `{line}`")

if tasks:
    total_tasks = len(tasks)
    overall_progress = st.progress(0)
    status_container = st.container()
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, task in enumerate(tasks, start=1):
            task_type = task["type"]
            task_name = task["name"]

            status_container.markdown(f"#### 🎬 Processing file {idx}/{total_tasks}: `{task_name}`")
            file_progress = st.progress(0)

            try:
                # Step 1: Ingest Video
                if task_type == "local":
                    file_obj = task["input"]
                    base_name = os.path.splitext(file_obj.name)[0]
                    video_path = os.path.join(tmpdir, file_obj.name)
                    status_container.info(f"⏳ [{idx}/{total_tasks}] Streaming `{file_obj.name}` to disk...")
                    file_progress.progress(15)
                    # Write in 16MB chunks to handle heavy files up to TBs with minimal memory
                    with open(video_path, "wb") as f_out:
                        CHUNK_SIZE = 16 * 1024 * 1024
                        while True:
                            chunk = file_obj.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            f_out.write(chunk)
                    file_id = None
                else:
                    file_id = task["input"]
                    base_name = f"subtitles_{file_id}"
                    status_container.info(f"⏳ [{idx}/{total_tasks}] Downloading from Google Drive (ID: `{file_id}`)...")
                    file_progress.progress(15)
                    video_path = download_from_gdrive(file_id, output_dir=tmpdir)

                video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                status_container.info(f"✅ Video ready ({video_size_mb:.1f} MB).")
                file_progress.progress(35)

                # Step 2: Extract Audio via ffmpeg
                status_container.info(f"⏳ [{idx}/{total_tasks}] Extracting audio track via ffmpeg (16kHz mono)...")
                audio_path = os.path.join(tmpdir, f"audio_{idx}.wav")
                extracted = extract_audio_from_video(video_path, audio_path)
                if not extracted:
                    audio_path = video_path

                file_progress.progress(50)
                status_container.info(f"✅ Audio track extracted.")

                # If local file, delete raw video to instantly free up disk space
                if task_type == "local" and extracted and os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except Exception:
                        pass

                # Step 3: Transcribe
                engine_label = "Cloud Turbo (Groq)" if "Cloud" in transcription_engine else f"Local Whisper ({model_size})"
                status_container.info(f"⏳ [{idx}/{total_tasks}] Transcribing speech with Whisper ({engine_label})...")

                if "Cloud" in transcription_engine:
                    if not groq_api_key:
                        raise ValueError("Groq API Key is required for Cloud Turbo mode. Enter it in the sidebar or switch to Local Whisper.")
                    srt_content, segments = transcribe_cloud_whisper(
                        audio_path=audio_path,
                        api_key=groq_api_key,
                        language=selected_lang_code
                    )
                else:
                    srt_content, segments = transcribe_local_whisper(
                        audio_path=audio_path,
                        model_size=model_size,
                        language=selected_lang_code
                    )

                file_progress.progress(85)
                status_container.info(f"✅ Transcribed {len(segments)} subtitle segments.")

                # Clean up temporary audio file
                if os.path.exists(audio_path) and audio_path != video_path:
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass

                # Step 4: Save local SRT
                srt_file_name = f"{base_name}.srt"
                local_srt_path = os.path.join(tmpdir, srt_file_name)
                with open(local_srt_path, "w", encoding="utf-8") as f_srt:
                    f_srt.write(srt_content)

                drive_web_link = None
                if task_type == "gdrive" and auto_upload_drive and file_id:
                    status_container.info(f"⏳ [{idx}/{total_tasks}] Uploading SRT to Google Drive...")
                    drive_result = upload_srt_to_gdrive(
                        srt_file_path=local_srt_path,
                        original_video_file_id=file_id,
                        service_account_info_or_path=service_account_json
                    )
                    if drive_result and drive_result.get("web_link"):
                        drive_web_link = drive_result["web_link"]

                file_progress.progress(100)
                results.append({
                    "name": task_name,
                    "srt_name": srt_file_name,
                    "content": srt_content,
                    "segments": len(segments),
                    "drive_link": drive_web_link
                })

            except Exception as e:
                file_progress.progress(0)
                status_container.error(f"❌ Error processing `{task_name}`: {str(e)}")

            overall_progress.progress(int((idx / total_tasks) * 100))

    if results:
        st.success(f"🎉 Successfully generated subtitles for {len(results)} of {total_tasks} file(s)!")

        # ZIP Download for batch
        if len(results) > 1:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for r in results:
                    zip_file.writestr(r["srt_name"], r["content"])
            zip_buffer.seek(0)

            st.download_button(
                label=f"📦 Download All Subtitles (.ZIP) — {len(results)} Files",
                data=zip_buffer,
                file_name="subtitles_batch.zip",
                mime="application/zip",
                use_container_width=True
            )
            st.markdown("---")

        # Results Previews & Individual Downloads
        st.subheader("📥 Subtitles Output & Downloads")
        for r in results:
            with st.expander(f"📄 {r['srt_name']} ({r['segments']} segments)", expanded=(len(results) == 1)):
                col_d1, col_d2 = st.columns([1, 1])
                with col_d1:
                    st.download_button(
                        label=f"📥 Download {r['srt_name']}",
                        data=r["content"],
                        file_name=r["srt_name"],
                        mime="text/plain",
                        key=f"dl_{r['srt_name']}"
                    )
                with col_d2:
                    if r.get("drive_link"):
                        st.link_button("🔗 View in Google Drive", r["drive_link"])
                st.text_area("SubRip (.srt) Preview", value=r["content"], height=280, key=f"preview_{r['srt_name']}")
