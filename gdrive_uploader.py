import os
import json
from typing import Optional, Dict

def upload_srt_to_gdrive(
    srt_file_path: str,
    original_video_file_id: str,
    service_account_info_or_path: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """
    Uploads an SRT file directly to the same Google Drive folder as the original video.
    Returns a dict with {'id': file_id, 'web_link': webViewLink} or None if not configured.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("google-api-python-client or google-auth not installed.")
        return None

    creds = None
    # 1. Check if provided directly or via env
    raw_cred = service_account_info_or_path or os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    
    if not raw_cred:
        # Check standard local file paths
        for path in ["service_account.json", "credentials.json"]:
            if os.path.exists(path):
                raw_cred = path
                break

    if not raw_cred:
        print("No Google Service Account credentials provided.")
        return None

    SCOPES = ['https://www.googleapis.com/auth/drive']

    try:
        if os.path.isfile(raw_cred):
            creds = service_account.Credentials.from_service_account_file(raw_cred, scopes=SCOPES)
        else:
            # Assume it's a JSON string passed via env var
            info = json.loads(raw_cred)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            
        service = build('drive', 'v3', credentials=creds)

        # 1. Fetch parent folder ID and original video name
        video_metadata = service.files().get(
            fileId=original_video_file_id,
            fields='id, name, parents',
            supportsAllDrives=True
        ).execute()

        parents = video_metadata.get('parents', [])
        video_name = video_metadata.get('name', 'video')
        base_name = os.path.splitext(video_name)[0]
        srt_name = f"{base_name}.srt"

        # 2. Upload SRT file into the same parent folder
        file_metadata = {
            'name': srt_name,
            'parents': parents
        }
        media = MediaFileUpload(srt_file_path, mimetype='text/plain', resumable=True)

        created_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink',
            supportsAllDrives=True
        ).execute()

        print(f"Uploaded SRT to Google Drive: {created_file.get('webViewLink')}")
        return {
            "id": created_file.get("id"),
            "name": created_file.get("name"),
            "web_link": created_file.get("webViewLink")
        }

    except Exception as e:
        print(f"Error uploading SRT to Google Drive: {e}")
        return None
