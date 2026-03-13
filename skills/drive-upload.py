#!/usr/bin/env python3
"""
drive-upload.py — Google Drive 文件上传工具

用法:
  python3 drive-upload.py <file_path> [--folder FOLDER_ID] [--name NAME]
  python3 drive-upload.py --auth     # 首次认证

依赖: google-api-python-client, google-auth-oauthlib (已在 .venv 中)
"""

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

# 认证文件路径
TOKEN_PATH = Path.home() / "mason-hub" / "credentials" / "drive_token.json"
CREDENTIALS_PATH = Path.home() / "mason-hub" / "credentials" / "drive_credentials.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_service():
    """获取已认证的 Drive API 服务"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
        else:
            print("❌ 未认证。请先运行: python3 drive-upload.py --auth")
            sys.exit(1)

    return build("drive", "v3", credentials=creds)


def do_auth():
    """执行 OAuth 认证流程"""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CREDENTIALS_PATH.exists():
        print(f"❌ 需要 OAuth client credentials 文件: {CREDENTIALS_PATH}")
        print("   请从 Google Cloud Console 下载 OAuth 2.0 Client ID JSON")
        print("   保存到上述路径")
        sys.exit(1)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    print(f"✅ 认证成功，token 保存到 {TOKEN_PATH}")


def upload_file(file_path: str, folder_id: str = "", name: str = ""):
    """上传文件到 Google Drive"""
    from googleapiclient.http import MediaFileUpload

    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)

    service = get_service()

    # 自动检测 MIME 类型
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"

    # 文件元数据
    file_metadata = {"name": name or path.name}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    # 上传
    file_size = path.stat().st_size
    size_str = f"{file_size / 1024:.1f}KB" if file_size < 1048576 else f"{file_size / 1048576:.1f}MB"

    print(f"📤 上传中: {path.name} ({size_str}, {mime_type})")

    # 大文件用 resumable upload
    resumable = file_size > 5 * 1024 * 1024
    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=resumable)

    result = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name,webViewLink,size"
    ).execute()

    file_id = result.get("id")
    link = result.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")

    print(f"✅ 上传成功")
    print(f"   文件 ID: {file_id}")
    print(f"   链接: {link}")
    print(f"   大小: {size_str}")

    # 输出 JSON（供脚本消费）
    print(json.dumps({
        "status": "success",
        "file_id": file_id,
        "name": result.get("name"),
        "link": link,
        "size": file_size
    }))


def main():
    parser = argparse.ArgumentParser(description="Upload file to Google Drive")
    parser.add_argument("file", nargs="?", help="File to upload")
    parser.add_argument("--folder", default="", help="Parent folder ID")
    parser.add_argument("--name", default="", help="Target filename")
    parser.add_argument("--auth", action="store_true", help="Run OAuth flow")

    args = parser.parse_args()

    if args.auth:
        do_auth()
        return

    if not args.file:
        parser.print_help()
        sys.exit(1)

    upload_file(args.file, args.folder, args.name)


if __name__ == "__main__":
    main()
