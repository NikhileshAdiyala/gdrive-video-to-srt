import os
import re
import tempfile
import requests
import gdown
from typing import Optional
from utils import extract_gdrive_file_id

def download_from_gdrive(url_or_id: str, output_dir: Optional[str] = None) -> str:
    """
    Downloads a video file from Google Drive given a shareable link or file ID.
    Returns the local path of the downloaded file.
    """
    file_id = extract_gdrive_file_id(url_or_id)
    if not file_id:
        raise ValueError(f"Invalid Google Drive URL or File ID: '{url_or_id}'")

    if output_dir is None:
        output_dir = tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)

    # Output path placeholder
    output_path = os.path.join(output_dir, f"{file_id}.mp4")

    # If already downloaded in cache/temp
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        return output_path

    # Attempt download using gdown (handles large files and confirmation cookies)
    download_url = f"https://drive.google.com/uc?id={file_id}"
    
    try:
        downloaded = gdown.download(id=file_id, output=output_path, quiet=False, fuzzy=True)
        if downloaded and os.path.exists(downloaded) and os.path.getsize(downloaded) > 1024:
            return downloaded
    except Exception as e:
        print(f"gdown encountered an issue: {e}, falling back to direct stream download...")

    # Fallback to direct requests streaming
    session = requests.Session()
    response = session.get(download_url, stream=True)
    
    # Check for Google Drive virus scan warning token
    token = None
    for k, v in response.cookies.items():
        if k.startswith("download_warning"):
            token = v
            break
            
    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get("https://drive.google.com/uc", params=params, stream=True)
        
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
            if chunk:
                f.write(chunk)

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
        raise RuntimeError("Failed to download video from Google Drive. Ensure the file sharing is set to 'Anyone with the link can view'.")

    return output_path
