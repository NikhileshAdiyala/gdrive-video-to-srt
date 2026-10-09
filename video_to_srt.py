#!/usr/bin/env python3
"""
CLI tool: Transcribe local video files to .SRT subtitles directly.
Usage:
    python video_to_srt.py video.mp4
    python video_to_srt.py /path/to/movie.mov --model medium
    python video_to_srt.py *.mp4 --language en
"""

import os
import sys
import argparse
import tempfile
import time
from utils import extract_audio_from_video
from transcriber import transcribe_local_whisper, transcribe_cloud_whisper

def process_file(video_path: str, model_size: str, language: str = None, groq_api_key: str = None, output_srt: str = None):
    if not os.path.exists(video_path):
        print(f"❌ Error: File not found: {video_path}")
        return False

    if output_srt is None:
        base_name, _ = os.path.splitext(video_path)
        output_srt = f"{base_name}.srt"

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"\n🎬 Processing: {os.path.basename(video_path)} ({file_size_mb:.1f} MB)")
    start_total = time.time()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Extract Audio
        audio_path = os.path.join(tmpdir, "extracted_audio.wav")
        print("🔊 Extracting audio track via ffmpeg (16kHz mono)...")
        t0 = time.time()
        if not extract_audio_from_video(video_path, audio_path):
            print("⚠️ ffmpeg audio extraction failed, attempting direct file transcription...")
            audio_path = video_path
        else:
            print(f"✅ Audio extracted in {time.time() - t0:.1f}s")

        # Step 2: Transcription
        lang_code = None if (not language or language.lower() in ("auto", "auto-detect")) else language.lower()
        if groq_api_key:
            print("🤖 Transcribing with Cloud Turbo (Groq whisper-large-v3)...")
            t1 = time.time()
            srt_content, segments = transcribe_cloud_whisper(
                audio_path=audio_path,
                api_key=groq_api_key,
                language=lang_code
            )
            print(f"✅ Transcribed in {time.time() - t1:.1f}s ({len(segments)} segments)")
        else:
            print(f"🤖 Transcribing with Local Whisper ({model_size})...")
            t1 = time.time()
            srt_content, segments = transcribe_local_whisper(
                audio_path=audio_path,
                model_size=model_size,
                language=lang_code
            )
            print(f"✅ Transcribed in {time.time() - t1:.1f}s ({len(segments)} segments)")

        # Step 3: Write Output SRT
        with open(output_srt, "w", encoding="utf-8") as f:
            f.write(srt_content)

    print(f"🎉 Subtitles saved: {output_srt}")
    print(f"⏱️ Total time: {time.time() - start_total:.1f}s\n")
    return True

def main():
    parser = argparse.ArgumentParser(description="Extract audio and transcribe video files to .SRT subtitles.")
    parser.add_argument("videos", nargs="+", help="One or more video files (MP4, MOV, MKV, AVI, WebM, etc.)")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: base). Use medium or large-v3 for best accuracy.")
    parser.add_argument("--language", default=None, help="Spoken language code (e.g. en, hi, es, fr). Default: auto-detect.")
    parser.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"),
                        help="Optional Groq API key for instant Cloud Turbo transcription.")
    parser.add_argument("-o", "--output", default=None, help="Output .srt file path (only valid for single video).")

    args = parser.parse_args()

    for video_file in args.videos:
        process_file(
            video_path=video_file,
            model_size=args.model,
            language=args.language,
            groq_api_key=args.groq_key,
            output_srt=args.output if len(args.videos) == 1 else None
        )

if __name__ == "__main__":
    main()
