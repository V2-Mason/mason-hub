"""情报采集端到端管道

用法：
  python pipeline.py <source_url> [--platform xhs] [--model gemini-2.5-flash] [--keep-local]

流程：
  1. 通过 greenvideo.cc 下载视频
  2. 上传到 Google Drive (00-竞品情报/视频素材/{platform}/)
  3. 用 Gemini 分析视频内容
  4. 拆解结果上传到 Drive (00-竞品情报/拆解结果/)
  5. 输出汇总 JSON
"""
import argparse
import json
import os
import sys
import tempfile

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from download import detect_platform, make_filename, extract_video_info, download_file  # noqa
from gdrive_upload import get_drive_service, resolve_target_folder
from gemini_analyze import analyze_video
from googleapiclient.http import MediaFileUpload


def main():
    parser = argparse.ArgumentParser(description='Video intelligence pipeline')
    parser.add_argument('url', help='Source video URL')
    parser.add_argument('--platform', choices=['xhs', 'douyin', 'ins', 'tiktok'])
    parser.add_argument('--model', default='gemini-3-flash-preview')
    parser.add_argument('--keep-local', action='store_true', help='Keep local video file')
    parser.add_argument('--output-dir', default=None, help='Local output dir (default: temp)')
    args = parser.parse_args()

    platform = args.platform or detect_platform(args.url)
    if not platform:
        print("ERROR: Cannot detect platform. Use --platform.", file=sys.stderr)
        return 1

    work_dir = args.output_dir or tempfile.mkdtemp(prefix='vidpipe_')
    os.makedirs(work_dir, exist_ok=True)
    print(f"=== Video Intelligence Pipeline ===")
    print(f"Source: {args.url}")
    print(f"Platform: {platform}")
    print(f"Work dir: {work_dir}")
    print()

    # --- Step 1: Download ---
    print("--- [1/4] Downloading video ---")
    video_url, title, cover_url = extract_video_info(args.url, platform)
    print(f"Title: {title}")
    filename = make_filename(args.url, platform, title)
    local_path = os.path.join(work_dir, filename)
    download_file(video_url, local_path)
    print()

    # --- Step 2: Upload video to Drive ---
    print("--- [2/4] Uploading to Google Drive ---")
    drive = get_drive_service()
    video_folder = resolve_target_folder(drive, platform)
    result = drive.files().create(
        body={'name': filename, 'parents': [video_folder]},
        media_body=MediaFileUpload(local_path, mimetype='video/mp4', resumable=True),
        fields='id,name,webViewLink'
    ).execute()
    drive_video_id = result['id']
    drive_video_link = result.get('webViewLink', '')
    print(f"Uploaded: {result['name']} ({drive_video_link})")
    print()

    # --- Step 3: Gemini analysis ---
    print("--- [3/4] Analyzing with Gemini ---")
    analysis = analyze_video(local_path, model=args.model)
    analysis_filename = filename.replace('.mp4', '_analysis.json')
    analysis_path = os.path.join(work_dir, analysis_filename)
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print()

    # --- Step 4: Upload analysis to Drive ---
    print("--- [4/4] Uploading analysis to Drive ---")
    analysis_folder = resolve_target_folder(drive, platform, subfolder='拆解结果')
    a_result = drive.files().create(
        body={'name': analysis_filename, 'parents': [analysis_folder]},
        media_body=MediaFileUpload(analysis_path, mimetype='application/json'),
        fields='id,name,webViewLink'
    ).execute()
    drive_analysis_link = a_result.get('webViewLink', '')
    print(f"Uploaded: {a_result['name']} ({drive_analysis_link})")
    print()

    # --- Summary ---
    summary = {
        'source_url': args.url,
        'platform': platform,
        'video': {
            'drive_id': drive_video_id,
            'drive_link': drive_video_link,
            'local_path': local_path if args.keep_local else None,
        },
        'analysis': {
            'drive_id': a_result['id'],
            'drive_link': drive_analysis_link,
            'products_count': len(analysis.get('products', [])),
            'tone': analysis.get('overall_tone', ''),
            'reusable_patterns': analysis.get('reusable_patterns', []),
        },
        'model': args.model,
    }

    summary_path = os.path.join(work_dir, filename.replace('.mp4', '_summary.json'))
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("=== Pipeline Complete ===")
    print(f"Video: {drive_video_link}")
    print(f"Analysis: {drive_analysis_link}")
    print(f"Products: {summary['analysis']['products_count']}")
    print(f"Tone: {summary['analysis']['tone']}")

    # Clean up local files unless --keep-local
    if not args.keep_local and not args.output_dir:
        os.remove(local_path)
        os.remove(analysis_path)
        os.remove(summary_path)
        os.rmdir(work_dir)
        print("Local files cleaned up")

    return 0


if __name__ == '__main__':
    exit(main())
