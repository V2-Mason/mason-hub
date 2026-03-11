"""Drive <-> Sheet 双向同步：内容看板自动化

用法：
  python content_board.py sync              # 双向同步
  python content_board.py drive-to-sheet    # 只扫描新内容到 Sheet
  python content_board.py sheet-to-drive    # 只处理 Mason 状态变更
  python content_board.py status            # 打印当前看板状态

工作流：
  Pass 1 (Drive→Sheet): 扫描 Drive 文件夹发现新内容 → 插入 Sheet 行
  Pass 2 (Sheet→Drive): 读取 Mason 状态变更 → 移动 Drive 文件夹
  Pass 3: 从素材明细聚合更新月度排期总览
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdrive_upload import get_drive_service, find_folder, find_or_create_folder

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')
SPREADSHEET_ID = '1icNxvwx8LHZaXvcl7EV010x7id4ZxAwYwg3EgZDXsDs'

# Drive folder IDs
FOLDER_IDS = {
    '初版-待反馈': '1A1uxv9Rv7A8hCI1CCycoIMTazvACKFnI',
    '修改版-待确认': '1XufI-CuitoNXqjkb6Ktk6x_zS0htySTg',
    '已确认-待排期': '1wAtYNFWQVROW0Mr2ZPHb1O7dMn2oBPwS',
    '03-已发布': '1AvXvB7Q6_EEaAStk1U3T-j9_upM0mNhd',
}

# Status → target Drive folder
STATUS_FOLDER_MAP = {
    '🔄审核中': '初版-待反馈',
    '✅已确认': '已确认-待排期',
    '📋排期': '已确认-待排期',
    '🚀已发布': '03-已发布',
    '📊监测中': '03-已发布',
}

STATUS_OPTIONS = list(STATUS_FOLDER_MAP.keys())

# Folder → default status when first discovered
FOLDER_DEFAULT_STATUS = {
    '初版-待反馈': '🔄审核中',
    '修改版-待确认': '🔄审核中',
    '已确认-待排期': '✅已确认',
}

# Column layout: A-L
# A:内容ID B:主题 C:渠道 D:内容形式 E:文案状态 F:图片/视频状态
# G:Drive链接 H:计划发布日 I:实际发布日 J:发布链接 K:状态 L:生成日期
COL_RANGE = 'A:L'


def get_sheets_service():
    """Build Sheets API service using existing OAuth credentials."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

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
    return build('sheets', 'v4', credentials=creds)


def _ensure_columns(sheets):
    """Ensure 状态(K) and 生成日期(L) columns exist with proper formatting."""
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='素材明细!A1:L1',
    ).execute()
    headers = result.get('values', [[]])[0]

    # Pad headers to at least 12 columns
    while len(headers) < 12:
        headers.append('')

    updates = []
    if headers[10] != '状态':
        updates.append({'range': '素材明细!K1', 'values': [['状态']]})
    if headers[11] != '生成日期':
        updates.append({'range': '素材明细!L1', 'values': [['生成日期']]})

    if updates:
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={'valueInputOption': 'RAW', 'data': updates},
        ).execute()

    # Set dropdown validation for column K + bold headers K-L
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={'requests': [
            {
                'setDataValidation': {
                    'range': {
                        'sheetId': 1,  # 素材明细 is sheet index 1
                        'startRowIndex': 1,
                        'endRowIndex': 200,
                        'startColumnIndex': 10,  # K = index 10
                        'endColumnIndex': 11,
                    },
                    'rule': {
                        'condition': {
                            'type': 'ONE_OF_LIST',
                            'values': [{'userEnteredValue': s} for s in STATUS_OPTIONS],
                        },
                        'showCustomUi': True,
                        'strict': False,
                    },
                }
            },
            # Bold headers K-L
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 1,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 10,
                        'endColumnIndex': 12,
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)',
                }
            },
        ]},
    ).execute()


def _list_project_folders(drive, parent_id):
    """List project subfolders under a parent folder."""
    results = []
    page_token = None
    while True:
        resp = drive.files().list(
            q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields='nextPageToken, files(id, name, webViewLink)',
            pageToken=page_token,
        ).execute()
        results.extend(resp.get('files', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return results


def _extract_metadata(drive, project_folder_id):
    """Try to extract topic from localized_analysis.json in project folder."""
    files = drive.files().list(
        q=f"'{project_folder_id}' in parents and name='localized_analysis.json' and trashed=false",
        fields='files(id)',
    ).execute().get('files', [])

    if not files:
        # Try project.json
        files = drive.files().list(
            q=f"'{project_folder_id}' in parents and name='project.json' and trashed=false",
            fields='files(id)',
        ).execute().get('files', [])

    # For simplicity, return empty — topic comes from folder name
    return {}


def _get_project_parent(drive, folder_id):
    """Get parent folder name for a project folder."""
    info = drive.files().get(fileId=folder_id, fields='parents').execute()
    parents = info.get('parents', [])
    if not parents:
        return None
    parent_id = parents[0]
    for name, fid in FOLDER_IDS.items():
        if fid == parent_id:
            return name
    return None


def _move_folder(drive, folder_id, from_parent_id, to_parent_id):
    """Move a folder from one parent to another."""
    drive.files().update(
        fileId=folder_id,
        addParents=to_parent_id,
        removeParents=from_parent_id,
        fields='id, parents',
    ).execute()


def _read_details_tab(sheets):
    """Read all rows from 素材明细 tab. Returns list of row lists."""
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='素材明细!' + COL_RANGE,
    ).execute()
    return result.get('values', [])


def sync_drive_to_sheet(project_id=None):
    """Pass 1: Scan Drive folders, add new content to Sheet."""
    from datetime import datetime
    drive = get_drive_service()
    sheets = get_sheets_service()

    _ensure_columns(sheets)

    # Read existing content IDs from Sheet
    rows = _read_details_tab(sheets)
    existing_ids = set()
    for row in rows[1:]:  # skip header
        if row:
            existing_ids.add(row[0])  # column A = 内容ID

    # Scan all content creation folders
    new_rows = []
    today = datetime.now().strftime('%Y-%m-%d')
    scan_folders = ['初版-待反馈', '修改版-待确认', '已确认-待排期']

    for folder_name in scan_folders:
        folder_id = FOLDER_IDS[folder_name]
        projects = _list_project_folders(drive, folder_id)

        for proj in projects:
            proj_name = proj['name']

            # If filtering by project_id, skip non-matching
            if project_id and proj_name != project_id:
                continue

            if proj_name in existing_ids:
                continue

            # Extract topic from folder name (format: YYYY-MM-DD_topic or test-YYYY-MM-DD_topic)
            topic = proj_name.split('_', 1)[1] if '_' in proj_name else proj_name
            drive_link = proj.get('webViewLink', '')
            status = FOLDER_DEFAULT_STATUS.get(folder_name, '🔄审核中')

            # One row per project (can expand to per-platform later)
            new_rows.append([
                proj_name,       # A: 内容ID
                topic,           # B: 主题
                'xhs',           # C: 渠道
                '短视频',         # D: 内容形式
                '',              # E: 文案状态
                '',              # F: 图片/视频状态
                drive_link,      # G: Drive链接
                '',              # H: 计划发布日
                '',              # I: 实际发布日
                '',              # J: 发布链接
                status,          # K: 状态
                today,           # L: 生成日期
            ])

            existing_ids.add(proj_name)

    if new_rows:
        sheets.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='素材明细!' + COL_RANGE,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': new_rows},
        ).execute()
        print(f"Drive→Sheet: Added {len(new_rows)} new rows")
        for r in new_rows:
            print(f"  + {r[0]} ({r[2]}) [{r[10]}]")
    else:
        print("Drive→Sheet: No new content found")

    return len(new_rows)


def register_review_content(project_id, topic='', drive_link='', channels=None):
    """Register a new review item directly in the Sheet.

    Called by content_pipeline step_review after uploading storyboard doc.
    This writes the row immediately — no folder scan needed.

    Args:
        project_id: Content ID (e.g., '2026-03-02_cleanmakeup-base-makeup').
        topic: Content topic.
        drive_link: Google Docs link for review.
        channels: List of target platforms (default: ['xhs']).

    Returns:
        Number of rows added.
    """
    from datetime import datetime
    sheets = get_sheets_service()

    _ensure_columns(sheets)

    # Check if already registered
    rows = _read_details_tab(sheets)
    existing_ids = set()
    for row in rows[1:]:
        if row:
            existing_ids.add(row[0])

    if project_id in existing_ids:
        # Already exists — update Drive link and status if needed
        for i, row in enumerate(rows[1:], start=2):
            if row and row[0] == project_id:
                # Update drive link (G) and status (K) if currently empty
                updates = []
                if drive_link and (len(row) < 7 or not row[6]):
                    updates.append({'range': f'素材明细!G{i}', 'values': [[drive_link]]})
                if len(row) < 11 or not row[10]:
                    updates.append({'range': f'素材明细!K{i}', 'values': [['🔄审核中']]})
                if updates:
                    sheets.spreadsheets().values().batchUpdate(
                        spreadsheetId=SPREADSHEET_ID,
                        body={'valueInputOption': 'RAW', 'data': updates},
                    ).execute()
                    print(f"Board: Updated existing row for {project_id}")
                else:
                    print(f"Board: {project_id} already registered, no update needed")
                return 0
        return 0

    channels = channels or ['xhs']
    today = datetime.now().strftime('%Y-%m-%d')

    new_rows = []
    for ch in channels:
        new_rows.append([
            project_id,          # A: 内容ID
            topic,               # B: 主题
            ch,                  # C: 渠道
            '短视频',             # D: 内容形式
            '',                  # E: 文案状态
            '',                  # F: 图片/视频状态
            drive_link,          # G: Drive链接
            '',                  # H: 计划发布日
            '',                  # I: 实际发布日
            '',                  # J: 发布链接
            '🔄审核中',           # K: 状态
            today,               # L: 生成日期
        ])

    sheets.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='素材明细!' + COL_RANGE,
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': new_rows},
    ).execute()

    print(f"Board: Registered {project_id} ({len(new_rows)} channels) as 🔄审核中")
    return len(new_rows)


def sync_sheet_to_drive():
    """Pass 2: Read Sheet status changes, move Drive folders accordingly."""
    drive = get_drive_service()
    sheets = get_sheets_service()

    rows = _read_details_tab(sheets)
    if len(rows) <= 1:
        print("Sheet→Drive: No data rows")
        return 0

    moves = 0
    for i, row in enumerate(rows[1:], start=2):  # start=2 for Sheet row numbers
        if len(row) < 11:
            continue

        content_id = row[0]
        status = row[10] if len(row) > 10 else ''

        if not content_id or not status:
            continue

        target_folder_name = STATUS_FOLDER_MAP.get(status)
        if not target_folder_name:
            continue

        target_folder_id = FOLDER_IDS.get(target_folder_name)
        if not target_folder_id:
            continue

        # Find the project folder in Drive
        # Search across all content creation folders
        proj_folder_id = None
        current_parent_name = None

        for folder_name, folder_id in FOLDER_IDS.items():
            results = drive.files().list(
                q=f"'{folder_id}' in parents and name='{content_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields='files(id)',
            ).execute().get('files', [])
            if results:
                proj_folder_id = results[0]['id']
                current_parent_name = folder_name
                break

        if not proj_folder_id:
            continue

        current_parent_id = FOLDER_IDS.get(current_parent_name)
        if current_parent_id == target_folder_id:
            continue  # Already in correct folder

        # Move!
        _move_folder(drive, proj_folder_id, current_parent_id, target_folder_id)
        print(f"Sheet→Drive: Moved '{content_id}' from {current_parent_name} → {target_folder_name}")
        moves += 1

    if moves == 0:
        print("Sheet→Drive: No moves needed")

    return moves


def update_overview():
    """Pass 3: Rebuild 月度排期总览 from 素材明细 data."""
    sheets = get_sheets_service()
    rows = _read_details_tab(sheets)

    if len(rows) <= 1:
        return

    # Group by content_id → aggregate
    from collections import OrderedDict
    projects = OrderedDict()
    for row in rows[1:]:
        if not row:
            continue
        content_id = row[0] if len(row) > 0 else ''
        topic = row[1] if len(row) > 1 else ''
        channel = row[2] if len(row) > 2 else ''
        plan_date = row[7] if len(row) > 7 else ''
        status = row[10] if len(row) > 10 else ''

        key = content_id
        if key not in projects:
            projects[key] = {
                'topic': topic,
                'date': plan_date,
                'channels': {},
                'status': status,
            }
        projects[key]['channels'][channel] = status

    # Build overview rows
    overview_rows = []
    for content_id, info in projects.items():
        ch = info['channels']
        overview_rows.append([
            info['date'] or content_id,   # 日期
            info['topic'],                 # 主题/活动
            ch.get('xhs', ''),            # 小红书
            ch.get('朋友圈', ''),          # 朋友圈
            ch.get('douyin', ''),          # 抖音
            ch.get('视频号', ''),          # 视频号
            info['status'],                # 状态
            '',                            # 备注
        ])

    if overview_rows:
        # Clear old data rows (keep header)
        sheets.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range='月度排期总览!A2:I200',
        ).execute()

        sheets.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='月度排期总览!A2',
            valueInputOption='RAW',
            body={'values': overview_rows},
        ).execute()
        print(f"Overview: Updated {len(overview_rows)} rows in 月度排期总览")


def show_status():
    """Print current board status."""
    sheets = get_sheets_service()
    rows = _read_details_tab(sheets)

    if len(rows) <= 1:
        print("Board is empty")
        return

    print(f"Content Board ({len(rows) - 1} items):")
    print(f"{'ID':<40} {'Channel':<8} {'Status':<12} {'Generated':<12} {'Scheduled':<12}")
    print('-' * 86)
    for row in rows[1:]:
        if not row:
            continue
        cid = row[0] if len(row) > 0 else ''
        ch = row[2] if len(row) > 2 else ''
        status = row[10] if len(row) > 10 else ''
        gen_date = row[11] if len(row) > 11 else ''
        plan_date = row[7] if len(row) > 7 else ''
        print(f"{cid:<40} {ch:<8} {status:<12} {gen_date:<12} {plan_date:<12}")


def sync():
    """Run full bidirectional sync."""
    print("=== Content Board Sync ===\n")
    added = sync_drive_to_sheet()
    print()
    moved = sync_sheet_to_drive()
    print()
    update_overview()
    print(f"\nDone. Added: {added}, Moved: {moved}")


def main():
    parser = argparse.ArgumentParser(description='Content board: Drive <-> Sheet sync')
    parser.add_argument('command', choices=['sync', 'drive-to-sheet', 'sheet-to-drive', 'status'],
                        help='Sync command')
    args = parser.parse_args()

    if args.command == 'sync':
        sync()
    elif args.command == 'drive-to-sheet':
        sync_drive_to_sheet()
    elif args.command == 'sheet-to-drive':
        sync_sheet_to_drive()
    elif args.command == 'status':
        show_status()


if __name__ == '__main__':
    main()
