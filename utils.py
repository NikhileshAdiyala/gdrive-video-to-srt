import re
import os
import subprocess
import tempfile
from typing import Optional, Tuple, List

def extract_gdrive_file_id(url: str) -> Optional[str]:
    """
    Extracts the Google Drive file ID from various URL formats.
    Supported formats:
    - https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
    - https://drive.google.com/open?id=<FILE_ID>
    - https://drive.google.com/uc?id=<FILE_ID>
    - Just the file ID itself
    """
    if not url:
        return None
    url = url.strip()
    
    # Direct file ID check (alphanumeric, dashes, underscores, usually 25-45 chars)
    if re.fullmatch(r"[-a-zA-Z0-9_]{25,50}", url):
        return url
        
    patterns = [
        r"/file/d/([-a-zA-Z0-9_]+)",
        r"[?&]id=([-a-zA-Z0-9_]+)",
        r"/open\?id=([-a-zA-Z0-9_]+)",
        r"/uc\?id=([-a-zA-Z0-9_]+)"
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def format_timestamp_srt(seconds: float) -> str:
    """
    Converts seconds (float) to SRT timestamp format: HH:MM:SS,mmm
    Example: 65.42 -> 00:01:05,420
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    if milliseconds >= 1000:
        milliseconds = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def generate_srt_content(segments: List[dict]) -> str:
    """
    Formats transcription segments into valid SubRip (.srt) string.
    Each segment is a dict: {'start': float, 'end': float, 'text': str}
    """
    srt_lines = []
    for idx, seg in enumerate(segments, start=1):
        start_str = format_timestamp_srt(seg["start"])
        end_str = format_timestamp_srt(seg["end"])
        text = seg["text"].strip()
        srt_lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
    return "\n".join(srt_lines)


def extract_audio_from_video(video_path: str, output_audio_path: str) -> bool:
    """
    Uses ffmpeg to extract a lightweight 16kHz mono audio track from the video.
    This drastically speeds up Whisper and reduces memory consumption.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                   # No video
        "-acodec", "pcm_s16le",  # Standard 16-bit PCM WAV
        "-ar", "16000",          # 16kHz sample rate optimal for Whisper
        "-ac", "1",              # Mono channel
        output_audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0
