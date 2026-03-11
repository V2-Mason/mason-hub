#!/usr/bin/env python3
"""上传优化报告到 Google Drive，返回分享链接。

用法：
  python3 gdrive_upload_report.py <local_file> [--folder-name "优化报告"]

输出 JSON：{"link": "https://drive.google.com/file/d/xxx/view", "file_id": "xxx"}
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "video-download"))
from gdrive_upload import get_drive_service, find_folder, find_or_create_folder

MIME_TYPES = {
    ".md": "text/markdown",
    ".json": "application/json",
    ".txt": "text/plain",
    ".html": "text/html",
    ".pdf": "application/pdf",
}


def upload_report(local_path, folder_name="优化报告"):
    service = get_drive_service()

    # 在 Drive 根目录找或建"优化报告"文件夹
    folder_id = find_folder(service, folder_name)
    if not folder_id:
        # 创建在 My Drive 根目录
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = service.files().create(body=metadata, fields="id").execute()
        folder_id = folder["id"]

    # 上传文件
    ext = os.path.splitext(local_path)[1].lower()
    mime = MIME_TYPES.get(ext, "text/plain")
    file_name = os.path.basename(local_path)

    # 检查是否已存在同名文件（避免重复上传）
    q = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    existing = service.files().list(q=q, fields="files(id)").execute()
    if existing["files"]:
        # 更新已有文件
        file_id = existing["files"][0]["id"]
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(local_path, mimetype=mime)
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        # 新建文件
        from googleapiclient.http import MediaFileUpload

        metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(local_path, mimetype=mime)
        result = service.files().create(
            body=metadata, media_body=media, fields="id"
        ).execute()
        file_id = result["id"]

    # 设置为"知道链接的人可查看"
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    link = f"https://drive.google.com/file/d/{file_id}/view"
    return {"link": link, "file_id": file_id, "folder_id": folder_id}


def main():
    parser = argparse.ArgumentParser(description="上传报告到 Google Drive")
    parser.add_argument("file", help="本地文件路径")
    parser.add_argument("--folder-name", default="优化报告", help="Drive 文件夹名称")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(json.dumps({"error": f"文件不存在: {args.file}"}))
        sys.exit(1)

    result = upload_report(args.file, args.folder_name)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
