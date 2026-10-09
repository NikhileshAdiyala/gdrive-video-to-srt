import os
from typing import List, Dict, Optional, Tuple
from utils import generate_srt_content

def transcribe_local_whisper(
    audio_path: str,
    model_size: str = "base",
    language: Optional[str] = None,
    device: str = "auto",
    compute_type: str = "int8"
) -> Tuple[str, List[Dict]]:
    """
    Transcribes audio using faster-whisper (CTranslate2 open-source engine).
    Returns (srt_content, list_of_segments).
    """
    from faster_whisper import WhisperModel

    if device == "auto":
        # Check if CUDA is available, otherwise default to CPU
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    # CPU uses int8 for optimal speed and memory efficiency
    if device == "cpu":
        compute_type = "int8"

    print(f"Loading Whisper model '{model_size}' on {device} ({compute_type})...")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    transcribe_args = {
        "audio": audio_path,
        "beam_size": 5,
        "vad_filter": True, # Voice activity detection to trim silence
        "vad_parameters": dict(min_silence_duration_ms=500),
    }
    if language and language.lower() != "auto":
        transcribe_args["language"] = language.lower()

    segments_generator, info = model.transcribe(**transcribe_args)
    print(f"Detected language: {info.language} with probability {info.language_probability:.2f}")

    segments_list = []
    for s in segments_generator:
        segments_list.append({
            "start": s.start,
            "end": s.end,
            "text": s.text.strip()
        })

    srt_content = generate_srt_content(segments_list)
    return srt_content, segments_list


def transcribe_cloud_whisper(
    audio_path: str,
    api_key: str,
    language: Optional[str] = None
) -> Tuple[str, List[Dict]]:
    """
    Transcribes using Groq's high-speed hosted open-source Whisper (whisper-large-v3).
    Transcribes 10-minute audio in 2-3 seconds, ideal for lightweight cloud deployments.
    """
    from groq import Groq

    client = Groq(api_key=api_key)
    
    with open(audio_path, "rb") as file:
        prompt_kwargs = {
            "file": (os.path.basename(audio_path), file.read()),
            "model": "whisper-large-v3",
            "response_format": "verbose_json",
        }
        if language and language.lower() != "auto":
            prompt_kwargs["language"] = language.lower()

        transcription = client.audio.transcriptions.create(**prompt_kwargs)

    segments_list = []
    # Groq returns segments in verbose_json format
    raw_segments = getattr(transcription, "segments", None)
    if raw_segments:
        for s in raw_segments:
            segments_list.append({
                "start": s["start"] if isinstance(s, dict) else s.start,
                "end": s["end"] if isinstance(s, dict) else s.end,
                "text": (s["text"] if isinstance(s, dict) else s.text).strip()
            })
    else:
        # Fallback if no segments broken down
        text = getattr(transcription, "text", str(transcription))
        segments_list.append({
            "start": 0.0,
            "end": 5.0,
            "text": text
        })

    srt_content = generate_srt_content(segments_list)
    return srt_content, segments_list
