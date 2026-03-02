"""视频组装：ffmpeg 拼接 segment 视频片段 → 成片

用法：
  python assemble.py --clips-dir ./video_clips/ [--output ./final/final.mp4]

流程：
  1. 按文件名排序读取 segment_NNN_*.mp4
  2. 生成 ffmpeg concat 列表
  3. ffmpeg -f concat 拼接
  4. 可选：上传到 Drive
"""
import argparse
import glob
import json
import os
import subprocess
import sys


def assemble_clips(clips_dir, output_path):
    """Concatenate video clips using ffmpeg.

    Args:
        clips_dir: Directory containing segment_NNN_*.mp4 files.
        output_path: Output video file path.

    Returns:
        output_path on success, None on failure.
    """
    # Find and sort clips
    pattern = os.path.join(clips_dir, 'segment_*.mp4')
    clips = sorted(glob.glob(pattern))

    if not clips:
        print("ERROR: No video clips found", file=sys.stderr)
        return None

    print(f"Assembling {len(clips)} clips...")
    for c in clips:
        size_kb = os.path.getsize(c) // 1024
        print(f"  {os.path.basename(c)} ({size_kb}KB)")

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Create concat list file
    concat_path = os.path.join(clips_dir, '_concat_list.txt')
    with open(concat_path, 'w') as f:
        for clip in clips:
            # ffmpeg concat requires absolute paths or paths relative to list file
            abs_path = os.path.abspath(clip)
            f.write(f"file '{abs_path}'\n")

    # Run ffmpeg
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_path,
        '-c', 'copy',
        output_path,
    ]

    print(f"Running ffmpeg...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr[:500]}", file=sys.stderr)
            # Fallback: re-encode if codec mismatch
            print("Retrying with re-encode...", file=sys.stderr)
            cmd_reencode = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_path,
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                output_path,
            ]
            result = subprocess.run(cmd_reencode, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"ffmpeg re-encode error: {result.stderr[:500]}", file=sys.stderr)
                return None
    except FileNotFoundError:
        print("ERROR: ffmpeg not found. Install with: sudo apt install ffmpeg", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("ERROR: ffmpeg timed out", file=sys.stderr)
        return None
    finally:
        # Cleanup concat list
        if os.path.exists(concat_path):
            os.remove(concat_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Assembly complete: {output_path} ({size_mb:.1f}MB)")
    return output_path


def upload_to_drive(video_path, project_id):
    """Upload assembled video to Drive.

    Target: 素仁轩-内容中台/01-内容创作/初版-待反馈/{project_id}/
    """
    from gdrive_upload import get_drive_service, resolve_target_folder
    from googleapiclient.http import MediaFileUpload

    drive = get_drive_service()

    # Navigate to target folder
    # Start from 素仁轩-内容中台 root
    folder_path = ['01-内容创作', '初版-待反馈', project_id]
    parent_id = resolve_target_folder(drive, 'content')  # Will need adjustment

    filename = os.path.basename(video_path)
    result = drive.files().create(
        body={'name': filename, 'parents': [parent_id]},
        media_body=MediaFileUpload(video_path, mimetype='video/mp4', resumable=True),
        fields='id,name,webViewLink',
    ).execute()

    link = result.get('webViewLink', '')
    print(f"Uploaded to Drive: {result['name']} ({link})")
    return link


def main():
    parser = argparse.ArgumentParser(description='Assemble video clips with ffmpeg')
    parser.add_argument('--clips-dir', required=True, help='Directory with segment_*.mp4 clips')
    parser.add_argument('--output', default=None,
                        help='Output path (default: {clips_dir}/../final/final.mp4)')
    parser.add_argument('--upload', action='store_true', help='Upload to Google Drive')
    parser.add_argument('--project-id', default=None, help='Project ID for Drive folder')
    args = parser.parse_args()

    if not os.path.isdir(args.clips_dir):
        print(f"ERROR: Directory not found: {args.clips_dir}", file=sys.stderr)
        return 1

    output_path = args.output or os.path.join(
        os.path.dirname(args.clips_dir.rstrip('/')), 'final', 'final.mp4'
    )

    result = assemble_clips(args.clips_dir, output_path)
    if not result:
        return 1

    if args.upload and args.project_id:
        try:
            upload_to_drive(result, args.project_id)
        except Exception as e:
            print(f"Drive upload failed: {e}", file=sys.stderr)
            # Non-fatal: video is still saved locally

    return 0


if __name__ == '__main__':
    exit(main())
