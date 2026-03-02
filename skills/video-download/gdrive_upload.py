"""上传文件到 Google Drive 素仁轩-内容中台目录

用法：
  python gdrive_upload.py <local_file> --platform xhs [--subfolder 拆解结果]

默认上传到: 素仁轩-内容中台/00-竞品情报/视频素材/{platform}/
"""
import argparse
import json
import os
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
}


def get_drive_service():
    with open(os.path.join(CRED_DIR, 'google-token.json')) as f:
        token_data = json.load(f)
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data['refresh_token'],
        token_uri=token_data['token_uri'],
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret'],
        scopes=token_data['scopes'],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_data['token'] = creds.token
        with open(os.path.join(CRED_DIR, 'google-token.json'), 'w') as f:
            json.dump(token_data, f, indent=2)
    return build('drive', 'v3', credentials=creds)


def find_folder(service, name, parent_id=None):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    r = service.files().list(q=q, fields='files(id)', spaces='drive').execute()
    return r['files'][0]['id'] if r['files'] else None


def find_or_create_folder(service, name, parent_id):
    fid = find_folder(service, name, parent_id)
    if fid:
        return fid
    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id],
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    return folder['id']


def resolve_target_folder(service, platform, subfolder=None):
    """Navigate to target folder: 素仁轩-内容中台/00-竞品情报/{subfolder or 视频素材/{platform}}"""
    root = find_folder(service, '素仁轩-内容中台')
    if not root:
        raise RuntimeError("找不到 '素仁轩-内容中台' 根目录")

    d00 = find_folder(service, '00-竞品情报', root)
    if not d00:
        raise RuntimeError("找不到 '00-竞品情报' 目录")

    if subfolder:
        return find_or_create_folder(service, subfolder, d00)

    video_dir = find_folder(service, '视频素材', d00)
    if not video_dir:
        raise RuntimeError("找不到 '视频素材' 目录")

    platform_names = {'xhs': '小红书', 'douyin': '抖音', 'ins': 'INS', 'tiktok': 'TikTok'}
    pname = platform_names.get(platform, platform)
    return find_or_create_folder(service, pname, video_dir)


def upload_file(service, local_path, folder_id):
    filename = os.path.basename(local_path)
    ext = os.path.splitext(filename)[1].lower()
    mime = MIME_TYPES.get(ext, 'application/octet-stream')

    metadata = {
        'name': filename,
        'parents': [folder_id],
    }
    media = MediaFileUpload(local_path, mimetype=mime, resumable=True)
    f = service.files().create(body=metadata, media_body=media, fields='id,name,webViewLink').execute()
    return f


def main():
    parser = argparse.ArgumentParser(description='Upload file to Google Drive 内容中台')
    parser.add_argument('file', help='Local file path')
    parser.add_argument('--platform', choices=['xhs', 'douyin', 'ins', 'tiktok'], default='xhs')
    parser.add_argument('--subfolder', help='Upload to 00-竞品情报/{subfolder} instead of 视频素材/')
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        return 1

    service = get_drive_service()
    folder_id = resolve_target_folder(service, args.platform, args.subfolder)

    size_mb = os.path.getsize(args.file) / (1024 * 1024)
    print(f"Uploading {os.path.basename(args.file)} ({size_mb:.1f}MB) ...")

    result = service.files().create(
        body={'name': os.path.basename(args.file), 'parents': [folder_id]},
        media_body=MediaFileUpload(args.file,
                                   mimetype=MIME_TYPES.get(os.path.splitext(args.file)[1].lower(), 'application/octet-stream'),
                                   resumable=True),
        fields='id,name,webViewLink'
    ).execute()

    print(f"Uploaded: {result['name']}")
    print(f"Drive ID: {result['id']}")
    print(f"Link: {result.get('webViewLink', 'N/A')}")

    # Output JSON for pipeline
    print(json.dumps({
        'drive_file_id': result['id'],
        'drive_name': result['name'],
        'drive_link': result.get('webViewLink'),
        'folder_id': folder_id,
    }))

    return 0


if __name__ == '__main__':
    exit(main())
