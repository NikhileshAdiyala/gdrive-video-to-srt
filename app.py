import os
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

tab_local, tab_gdrive = st.tabs(["📁 Local Video File (Drag & Drop)", "🔗 Google Drive Link"])

with tab_local:
    uploaded_file = st.file_uploader(
        "Drop your video file here (MP4, MOV, MKV, AVI, WebM, etc.)",
        type=["mp4", "mov", "mkv", "avi", "webm", "m4v", "flv", "mp3", "wav", "m4a"],
        help="Accepts heavy raw video directly — no prior audio conversion needed!"
    )
    btn_local = st.button("🚀 Generate Subtitles from Local File", use_container_width=True, key="btn_local")

with tab_gdrive:
    gdrive_url = st.text_input(
        "Google Drive Video Link or File ID",
        placeholder="https://drive.google.com/file/d/1A2B3C4D5E.../view?usp=sharing",
        help="Ensure the video sharing permission is set to 'Anyone with the link can view'."
    )
    btn_gdrive = st.button("🚀 Generate Subtitles from Google Drive", use_container_width=True, key="btn_gdrive")

col_info1, col_info2 = st.columns([1, 1])
with col_info1:
    st.caption("💡 Works with raw video (MP4, MOV, MKV, etc.) — audio extracted in seconds via ffmpeg.")
with col_info2:
    st.caption("🔒 All processing runs locally/privately in temporary storage with auto-cleanup.")

# Processing Trigger
should_process = False
mode = None
video_input = None

if btn_local:
    if not uploaded_file:
        st.warning("⚠️ Please select or drop a video file first.")
    else:
        should_process = True
        mode = "local"
        video_input = uploaded_file

elif btn_gdrive:
    if not gdrive_url:
        st.warning("⚠️ Please provide a valid Google Drive video URL or File ID.")
    else:
        file_id = extract_gdrive_file_id(gdrive_url)
        if not file_id:
            st.error("❌ Could not extract a valid Google Drive File ID. Please check the URL format.")
        else:
            should_process = True
            mode = "gdrive"
            video_input = file_id

if should_process:
    status_container = st.container()
    progress_bar = st.progress(0)

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Step 1: Ingest Video
            if mode == "local":
                base_name = os.path.splitext(uploaded_file.name)[0]
                status_container.info(f"⏳ Step 1/4: Loading local file `{uploaded_file.name}`...")
                progress_bar.progress(15)
                video_path = os.path.join(tmpdir, uploaded_file.name)
                with open(video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_id = None
            else:
                base_name = f"subtitles_{video_input}"
                status_container.info(f"⏳ Step 1/4: Downloading video from Google Drive (ID: `{video_input}`)...")
                progress_bar.progress(15)
                video_path = download_from_gdrive(video_input, output_dir=tmpdir)
                file_id = video_input

            video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            status_container.info(f"✅ Video ready ({video_size_mb:.1f} MB).")
            progress_bar.progress(35)

            # Step 2: Extract Audio via ffmpeg
            status_container.info("⏳ Step 2/4: Extracting optimized audio track (16kHz mono PCM) via ffmpeg...")
            audio_path = os.path.join(tmpdir, "extracted_audio.wav")
            if not extract_audio_from_video(video_path, audio_path):
                # Fallback: Whisper can take raw video if ffmpeg extraction fails
                audio_path = video_path

            progress_bar.progress(50)
            status_container.info("✅ Audio track extracted in seconds.")

            # Step 3: Transcription
            engine_label = "Cloud Turbo (Groq)" if "Cloud" in transcription_engine else f"Local Whisper ({model_size})"
            status_container.info(f"⏳ Step 3/4: Transcribing speech with Whisper ({engine_label})...")

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

            progress_bar.progress(85)
            status_container.info(f"✅ Transcription complete! Generated {len(segments)} timed subtitle segments.")

            # Step 4: Save local SRT and optional Drive Upload
            srt_file_name = f"{base_name}.srt"
            local_srt_path = os.path.join(tmpdir, srt_file_name)
            with open(local_srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            drive_result = None
            if mode == "gdrive" and auto_upload_drive and file_id:
                status_container.info("⏳ Step 4/4: Uploading SRT back to Google Drive...")
                drive_result = upload_srt_to_gdrive(
                    srt_file_path=local_srt_path,
                    original_video_file_id=file_id,
                    service_account_info_or_path=service_account_json
                )
                if drive_result and drive_result.get("web_link"):
                    status_container.success(f"🎉 SRT uploaded to Google Drive: [Open in Drive]({drive_result['web_link']})")
                else:
                    status_container.warning("⚠️ Could not upload directly to Google Drive (Service Account credentials missing or invalid). You can still download the file below.")

            progress_bar.progress(100)
            st.success("🎉 Subtitle generation completed successfully!")

            # Results View
            res_col1, res_col2 = st.columns([1, 1])
            with res_col1:
                st.download_button(
                    label="📥 Download .SRT File",
                    data=srt_content,
                    file_name=srt_file_name,
                    mime="text/plain",
                    use_container_width=True
                )

            with res_col2:
                if drive_result and drive_result.get("web_link"):
                    st.link_button("🔗 View in Google Drive", drive_result["web_link"], use_container_width=True)

            # Subtitles Viewer
            st.subheader("📝 Subtitles Preview & Editor")
            st.text_area("SubRip (.srt) Output", value=srt_content, height=350)

        except Exception as e:
            progress_bar.progress(0)
            st.error(f"❌ An error occurred during processing: {str(e)}")
            st.exception(e)
