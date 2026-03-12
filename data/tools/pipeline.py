"""
管道状态查询 + 数据装配器 — 下游消费者一行代码获取管道全链路数据。

用法:
    from data.tools.pipeline import get_pipeline_status, assemble_optimization_data

    # 管道状态
    status = get_pipeline_status()
    print(status['stages']['analyze']['ok'])  # True/False

    # 优化周期数据装配（替代 optimization-cycle.sh 中的手工文件读取）
    data = assemble_optimization_data()
    print(data['sources'])      # 可用数据源列表
    print(data['issues'])       # 数据问题列表
    print(data['xhs_briefing']) # XHS 策略简报内容

维护者: EMP_0014
"""
import json
import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# 项目根目录
_HUB_DIR = Path(__file__).parent.parent.parent  # mason-hub/
_MARKER_DIR = _HUB_DIR / 'data' / 'pipelines' / 'markers'
_MIRROR_DIR = _HUB_DIR / 'data' / 'mirror'


def _today():
    """美东时间今日日期。"""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def get_pipeline_status(date=None):
    """查询 XHS 主干管道各阶段状态。

    Args:
        date: 日期字符串 "YYYY-MM-DD"，默认今天（美东时间）

    Returns:
        dict: {
            "date": "2026-03-12",
            "stages": {
                "crawl":    {"ok": bool, "marker": str|None, "age_min": int},
                "sync":     {...},
                "analyze":  {...},
                "optimize": {...},
            },
            "mirror_sync": {"last_sync": str|None, "age_hours": float},
        }
    """
    date = date or _today()
    stages = {}

    for stage in ['crawl', 'sync', 'analyze', 'optimize']:
        marker_path = _MARKER_DIR / f'.done_{stage}_{date}'
        if marker_path.exists():
            try:
                mtime = os.path.getmtime(str(marker_path))
                age_min = int((datetime.now().timestamp() - mtime) / 60)
                content = marker_path.read_text().strip()[:200]
            except Exception:
                age_min = -1
                content = None
            stages[stage] = {'ok': True, 'marker': content, 'age_min': age_min}
        else:
            stages[stage] = {'ok': False, 'marker': None, 'age_min': -1}

    # Mirror sync 状态
    last_sync_path = _MIRROR_DIR / '.last_sync'
    mirror_sync = {'last_sync': None, 'age_hours': -1}
    if last_sync_path.exists():
        try:
            mirror_sync['last_sync'] = last_sync_path.read_text().strip()
            mtime = os.path.getmtime(str(last_sync_path))
            mirror_sync['age_hours'] = round(
                (datetime.now().timestamp() - mtime) / 3600, 1
            )
        except Exception:
            pass

    return {
        'date': date,
        'stages': stages,
        'mirror_sync': mirror_sync,
    }


def _read_radar_report(weeks=2):
    """读取 Radar 关注率周报。

    Returns:
        dict: {"ok": bool, "report": str, "error": str|None}
    """
    tracker_db = _HUB_DIR / 'tools' / 'radar-tracker' / 'tracker.db'
    weekly_report_py = _HUB_DIR / 'tools' / 'radar-tracker' / 'weekly_report.py'
    venv_python = _HUB_DIR / '.venv' / 'bin' / 'python3'

    if not tracker_db.exists():
        return {'ok': False, 'report': '', 'error': 'tracker.db 不存在'}

    python_bin = str(venv_python) if venv_python.exists() else 'python3'

    try:
        result = subprocess.run(
            [python_bin, str(weekly_report_py), '--weeks', str(weeks)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return {'ok': True, 'report': result.stdout.strip(), 'error': None}
        else:
            return {'ok': False, 'report': '', 'error': f'退出码 {result.returncode}'}
    except Exception as e:
        return {'ok': False, 'report': '', 'error': str(e)}


def _read_scout_intel_red():
    """读取 Scout 红色优先级情报。

    使用 SDK 标准接口，不直接读文件。

    Returns:
        dict: {"ok": bool, "report": str, "count": int, "source": str, "error": str|None}
    """
    # 优先使用 SDK 读标准化 JSONL
    try:
        from . import sdk
        red_items = sdk.get_scout_intel(priority='red')
        if red_items:
            lines = []
            for i, item in enumerate(red_items, 1):
                title = item.get('title', '无标题')
                summary = item.get('summary', '无摘要')
                action = item.get('suggested_action', '无建议行动')
                lines.append(f'[{i}] {title}')
                lines.append(f'    摘要: {summary}')
                lines.append(f'    建议行动: {action}')
                lines.append('')
            lines.append(f'共 {len(red_items)} 条 red 优先级情报')
            return {
                'ok': True,
                'report': '\n'.join(lines),
                'count': len(red_items),
                'source': 'JSONL (SDK)',
                'error': None,
            }
    except Exception:
        pass

    # Fallback: markdown digest
    digest_dir = _HUB_DIR / 'intel' / 'digests'
    if digest_dir.is_dir():
        import glob as _glob
        md_files = sorted(_glob.glob(str(digest_dir / '*.md')), reverse=True)
        if md_files:
            latest = md_files[0]
            age_days = int(
                (datetime.now().timestamp() - os.path.getmtime(latest)) / 86400
            )
            if age_days <= 14:
                try:
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = ''.join(f.readlines()[:100])
                    return {
                        'ok': True,
                        'report': content,
                        'count': -1,
                        'source': f'markdown fallback ({os.path.basename(latest)}, {age_days}天前)',
                        'error': None,
                    }
                except Exception:
                    pass
            else:
                return {
                    'ok': False, 'report': '', 'count': 0,
                    'source': 'markdown',
                    'error': f'最新情报已过期（{age_days}天前）',
                }

    return {
        'ok': False, 'report': '', 'count': 0,
        'source': 'none', 'error': '无 Scout 情报（JSONL 和 markdown 均不可用）',
    }


def _read_xhs_briefing(max_age_days=7):
    """读取 XHS 策略简报。

    使用 SDK 标准接口，不直接 ls -t + cat。

    Returns:
        dict: {"ok": bool, "briefing": str, "filename": str, "age_days": int, "error": str|None}
    """
    try:
        from . import sdk
        briefing = sdk.get_xhs_briefing()
        if briefing:
            # 检查新鲜度
            source_file = briefing.pop('_source_file', '')
            filename = os.path.basename(source_file) if source_file else 'unknown'
            age_days = 0
            if source_file and os.path.exists(source_file):
                age_days = int(
                    (datetime.now().timestamp() - os.path.getmtime(source_file)) / 86400
                )
            if age_days > max_age_days:
                return {
                    'ok': False,
                    'briefing': '',
                    'filename': filename,
                    'age_days': age_days,
                    'error': f'简报已过期（{age_days}天前），data-sync 可能未运行',
                }
            return {
                'ok': True,
                'briefing': json.dumps(briefing, ensure_ascii=False, indent=2),
                'filename': filename,
                'age_days': age_days,
                'error': None,
            }
    except FileNotFoundError:
        return {
            'ok': False, 'briefing': '', 'filename': '',
            'age_days': -1, 'error': '无 XHS 策略简报（mirror 目录为空，请先运行 data-sync.sh）',
        }
    except Exception as e:
        return {
            'ok': False, 'briefing': '', 'filename': '',
            'age_days': -1, 'error': f'读取失败: {e}',
        }


def _read_trendradar_freshness(max_age_hours=24):
    """检查 TrendRadar 数据新鲜度。

    Returns:
        dict: {"ok": bool, "age_hours": int, "error": str|None}
    """
    tr_report = _HUB_DIR / 'tools' / 'trendradar' / 'output' / 'index.html'
    if not tr_report.exists():
        return {'ok': False, 'age_hours': -1, 'error': 'TrendRadar 输出文件不存在'}

    age_hours = int(
        (datetime.now().timestamp() - os.path.getmtime(str(tr_report))) / 3600
    )
    if age_hours <= max_age_hours:
        return {'ok': True, 'age_hours': age_hours, 'error': None}
    else:
        return {
            'ok': False, 'age_hours': age_hours,
            'error': f'TrendRadar 数据陈旧（{age_hours}h 未更新，cron 可能停了）',
        }


def assemble_optimization_data():
    """装配优化周期所需全部数据。

    替代 optimization-cycle.sh 中的手工文件读取，统一走 SDK 标准接口。

    Returns:
        dict: {
            "sources": [str],       # 可用数据源描述列表
            "issues": [str],        # 数据问题列表
            "source_count": int,    # 可用数据源数量（/4）
            "issue_count": int,     # 问题数量
            "radar_report": str,    # Radar 关注率文本（空=不可用）
            "scout_digest": str,    # Scout 情报文本（空=不可用）
            "xhs_briefing": str,    # XHS 策略简报 JSON 文本（空=不可用）
            "trendradar_ok": bool,  # TrendRadar 是否新鲜
            "gate1_pass": bool,     # Gate 1 数据完整性判定
            "gate1_result": str,    # Gate 1 结果描述
        }
    """
    sources = []
    issues = []

    # 1. Radar 关注率
    radar = _read_radar_report()
    radar_report = ''
    if radar['ok']:
        radar_report = radar['report']
        sources.append('Radar 关注率周报 ✅')
    else:
        issues.append(f'Radar: {radar["error"]}')

    # 2. Scout 情报
    scout = _read_scout_intel_red()
    scout_digest = ''
    if scout['ok']:
        scout_digest = scout['report']
        sources.append(f'Scout 情报简报 ✅ ({scout["source"]}, {scout["count"]} 条 red)')
    else:
        issues.append(f'Scout: {scout["error"]}')

    # 3. XHS 策略简报
    xhs = _read_xhs_briefing()
    xhs_briefing = ''
    if xhs['ok']:
        xhs_briefing = xhs['briefing']
        sources.append(f'XHS 策略简报 ✅ ({xhs["filename"]}, mirror {xhs["age_days"]}天前)')
    else:
        issues.append(f'XHS: {xhs["error"]}')

    # 4. TrendRadar
    tr = _read_trendradar_freshness()
    if tr['ok']:
        sources.append(f'TrendRadar 热榜 ✅ ({tr["age_hours"]}h 前更新)')
    else:
        issues.append(f'TrendRadar: {tr["error"]}')

    # Gate 1 判定
    source_count = len(sources)
    if source_count == 0:
        gate1_pass = False
        gate1_result = 'FAIL — 没有任何数据源可用，无法生成优化建议'
    elif source_count < 2:
        gate1_pass = True  # WARN but pass
        gate1_result = f'WARN — 仅 {source_count}/4 个数据源可用，建议质量有限'
    else:
        gate1_pass = True
        gate1_result = f'PASS — {source_count}/4 个数据源可用'

    return {
        'sources': sources,
        'issues': issues,
        'source_count': source_count,
        'issue_count': len(issues),
        'radar_report': radar_report,
        'scout_digest': scout_digest,
        'xhs_briefing': xhs_briefing,
        'trendradar_ok': tr['ok'],
        'gate1_pass': gate1_pass,
        'gate1_result': gate1_result,
    }
