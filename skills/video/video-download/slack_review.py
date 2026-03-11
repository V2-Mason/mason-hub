"""Slack 通知：内容管线各阶段状态通知

用法（作为模块导入）：
  from slack_review import notify_review_request, notify_delivery

通知类型：
  1. EMP_0008 核对请求 — 选题/参照视频/分发策略 → #socialmesh
  2. Mason 交付通知 — 成片 + 分镜预览 + 脚本 → #socialmesh
  3. 管线状态通知 — 步骤完成/失败 → #socialmesh-dev
  4. 产品匹配推荐 — Top 3 产品推荐 + 理由 → #socialmesh
"""
import json
import os
import sys
import urllib.request
import urllib.error

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')
ENV_FILE = os.path.expanduser('~/mason-hub/.env')

# Slack channel IDs
CH_SOCIALMESH = 'C0AHTA97EAY'
CH_SOCIALMESH_DEV = 'C0AHPMX5V6W'


def _get_slack_token():
    """Load Slack bot token from environment or .env file."""
    token = os.environ.get('SLACK_BOT_TOKEN')
    if token:
        return token

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith('SLACK_BOT_TOKEN='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")

    return None


def _post_slack(token, channel, text):
    """Post message to Slack. Returns True on success."""
    url = 'https://slack.com/api/chat.postMessage'
    data = json.dumps({
        'channel': channel,
        'text': text,
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8',
    })

    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read().decode('utf-8'))
        if not result.get('ok'):
            print(f"Slack API error: {result.get('error', 'unknown')}", file=sys.stderr)
            return False
        return True
    except urllib.error.URLError as e:
        print(f"Slack request failed: {e}", file=sys.stderr)
        return False


def notify_review_request(project):
    """Send review request to #socialmesh for EMP_0008 confirmation.

    Args:
        project: dict with project_id, topic, reference_video_url, etc.
    Returns:
        True if message sent successfully.
    """
    token = _get_slack_token()
    if not token:
        print("WARNING: SLACK_BOT_TOKEN not found, skipping notification", file=sys.stderr)
        return False

    text = (
        f"--- 内容管线核对请求 ---\n"
        f"项目: {project.get('project_id', 'unknown')}\n"
        f"选题: {project.get('topic', '')}\n"
        f"参照视频: {project.get('reference_video_url', '')}\n"
        f"参照平台: {project.get('reference_platform', '')}\n"
        f"品牌: {project.get('brand', 'surenxuan')}\n"
        f"目标平台: {', '.join(project.get('target_platforms', []))}\n"
        f"备注: {project.get('notes', '')}\n"
        f"\n"
        f"请 EMP_0008 核对后回复\"确认\"继续管线。"
    )

    return _post_slack(token, CH_SOCIALMESH, text)


def notify_delivery(project_id, drive_links=None, segment_count=0, status='success'):
    """Send delivery notification to #socialmesh.

    Args:
        project_id: Project identifier.
        drive_links: dict with keys like 'final_video', 'storyboard_folder', 'script'.
        segment_count: Number of storyboard segments generated.
        status: 'success' or 'partial'.
    """
    token = _get_slack_token()
    if not token:
        print("WARNING: SLACK_BOT_TOKEN not found, skipping notification", file=sys.stderr)
        return False

    drive_links = drive_links or {}

    status_emoji = 'OK' if status == 'success' else 'PARTIAL'
    lines = [
        f"--- 内容管线交付 [{status_emoji}] ---",
        f"项目: {project_id}",
        f"分镜数量: {segment_count}",
    ]

    if drive_links.get('storyboard_folder'):
        lines.append(f"分镜预览: {drive_links['storyboard_folder']}")
    if drive_links.get('script'):
        lines.append(f"本地化脚本: {drive_links['script']}")
    if drive_links.get('final_video'):
        lines.append(f"成片: {drive_links['final_video']}")

    return _post_slack(token, CH_SOCIALMESH, '\n'.join(lines))


def notify_pipeline_status(project_id, step, status, detail=''):
    """Send pipeline status update to #socialmesh-dev.

    Args:
        project_id: Project identifier.
        step: Pipeline step name (e.g., 'localize', 'storyboard').
        status: 'started', 'completed', 'failed'.
        detail: Optional detail message.
    """
    token = _get_slack_token()
    if not token:
        return False

    text = f"[{project_id}] {step}: {status}"
    if detail:
        text += f" - {detail}"

    return _post_slack(token, CH_SOCIALMESH_DEV, text)


def notify_product_recommendations(project_id, recommendations, analysis_products,
                                   resume_cmd=''):
    """发送产品匹配推荐到 #socialmesh，等待 Mason 确认。

    Args:
        project_id: 项目 ID。
        recommendations: 推荐列表（含 product_name, brand, reasoning, match_type, rank）。
        analysis_products: 原视频 product_catalog 条目。
        resume_cmd: 续跑命令提示。
    Returns:
        True if message sent successfully.
    """
    token = _get_slack_token()
    if not token:
        print("WARNING: SLACK_BOT_TOKEN not found, skipping notification", file=sys.stderr)
        return False

    lines = [
        f"--- 产品匹配推荐 [{project_id}] ---",
        "",
        "参照视频产品:",
    ]
    for p in analysis_products[:5]:
        lines.append(f"  - {p.get('product_type', '?')}: {p.get('core_function', '')}")

    lines.append("")
    lines.append("推荐匹配 (Top 3):")
    for rec in recommendations:
        match_type = rec.get('match_type', 'unknown')
        tag = '同品类' if match_type == 'same_category' else '跨品类'
        lines.append(
            f"  {rec.get('rank', '?')}. {rec.get('product_name', '?')} "
            f"({rec.get('brand', '?')}) [{tag}]"
        )
        if rec.get('reasoning'):
            lines.append(f"     理由: {rec['reasoning']}")

    lines.append("")
    if resume_cmd:
        lines.append(f"确认后执行: {resume_cmd}")
    lines.append("Mason 请确认或修改后继续管线。")

    return _post_slack(token, CH_SOCIALMESH, '\n'.join(lines))
