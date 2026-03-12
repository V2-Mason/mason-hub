"""
Mason Hub 数据中台 SDK

一行代码获取干净数据，业务 agent 无需关心物理存储细节。

快速开始:
    from data.tools import get_xhs_analysis, get_xhs_notes, get_scout_intel

    # XHS 互动分析
    report = get_xhs_analysis()

    # XHS 笔记（含互动分计算）
    notes = get_xhs_notes(keywords=["韩国护肤"])

    # Scout 红色情报
    red = get_scout_intel(priority="red")

    # 通用读取
    data = get_dataset("analysis_xhs_trends")

    # 指标计算
    score = interaction_score(100, 50, 10, 5)  # 385

维护者：EMP_0014
"""

# 高级 API — 业务 agent 最常用
from .sdk import (
    get_dataset,
    get_xhs_analysis,
    get_xhs_notes,
    get_xhs_trends,
    get_xhs_comments,
    get_xhs_briefing,
    get_scout_intel,
    get_srx_history,
    get_srx_snapshot,
    get_trendradar_news,
    list_datasets,
    dataset_info,
    check_freshness,
    DataError,
    DatasetNotFoundError,
    DataStaleError,
)

# 标准指标 — 唯一口径
from .metrics import (
    parse_count,
    interaction_score,
    engage_rate,
    save_rate,
    share_rate,
    fake_traffic_flags,
    keyword_competition,
)

# 管道级接口 — 数据装配 + 状态查询
from .pipeline import (
    get_pipeline_status,
    assemble_optimization_data,
)

__version__ = '0.2.0'
__all__ = [
    # SDK
    'get_dataset', 'get_xhs_analysis', 'get_xhs_notes', 'get_xhs_trends',
    'get_xhs_comments', 'get_xhs_briefing', 'get_scout_intel',
    'get_srx_history', 'get_srx_snapshot',
    'get_trendradar_news', 'list_datasets', 'dataset_info', 'check_freshness',
    # Pipeline
    'get_pipeline_status', 'assemble_optimization_data',
    # Errors
    'DataError', 'DatasetNotFoundError', 'DataStaleError',
    # Metrics
    'parse_count', 'interaction_score', 'engage_rate', 'save_rate',
    'share_rate', 'fake_traffic_flags', 'keyword_competition',
]
