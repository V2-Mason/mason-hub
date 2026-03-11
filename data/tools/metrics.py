"""
数据中台标准指标 — Single Source of Truth

所有业务脚本应从此模块导入指标计算函数，禁止本地重复实现。
维护者：EMP_0014

指标定义同步于 data/data_catalog.yaml 的 key_metrics 字段。
"""


def parse_count(s):
    """将 XHS 的中文数字格式归一化为整数。

    Examples:
        >>> parse_count("1.2万")
        12000
        >>> parse_count("3亿")
        300000000
        >>> parse_count("1234")
        1234
        >>> parse_count(None)
        0
    """
    if s is None:
        return 0
    s = str(s).strip().replace('+', '')
    if '万' in s:
        return int(float(s.replace('万', '')) * 10000)
    if '亿' in s:
        return int(float(s.replace('亿', '')) * 100000000)
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def interaction_score(liked, collected, comment, shared):
    """XHS 互动评分（唯一口径）。

    公式: liked + collected*3 + comment*5 + shared*8

    Args:
        liked: 点赞数（int 或 中文格式字符串）
        collected: 收藏数
        comment: 评论数
        shared: 转发数

    Returns:
        int: 互动分
    """
    liked = parse_count(liked) if not isinstance(liked, int) else liked
    collected = parse_count(collected) if not isinstance(collected, int) else collected
    comment = parse_count(comment) if not isinstance(comment, int) else comment
    shared = parse_count(shared) if not isinstance(shared, int) else shared
    return liked + collected * 3 + comment * 5 + shared * 8


def engage_rate(comment, liked):
    """评赞比 (%)。"""
    if liked <= 0:
        return 0.0
    return round(comment / liked * 100, 2)


def save_rate(collected, liked):
    """藏赞比 (%)。"""
    if liked <= 0:
        return 0.0
    return round(collected / liked * 100, 1)


def share_rate(shared, liked):
    """转赞比 (%)。"""
    if liked <= 0:
        return 0.0
    return round(shared / liked * 100, 1)


def fake_traffic_flags(liked, collected, comment, shared):
    """假流量检测标记。

    规则:
        - liked > 1000 且 评赞比 < 0.2% → "评赞比过低"
        - liked > 1000 且 藏赞比 < 5% → "藏赞比过低"

    Returns:
        list[str]: 可疑标记列表，空列表表示正常
    """
    flags = []
    if liked > 1000:
        if engage_rate(comment, liked) < 0.2:
            flags.append('评赞比过低')
        if save_rate(collected, liked) < 5:
            flags.append('藏赞比过低')
    return flags


def keyword_competition(count, avg_score, global_median):
    """关键词竞争密度判定。

    Returns:
        str: "蓝海" | "红海" | "待观察"
    """
    if count < 5 and avg_score > global_median:
        return '蓝海'
    elif count > 15:
        return '红海'
    elif count >= 5 and avg_score < global_median * 0.5:
        return '红海'
    return '待观察'
