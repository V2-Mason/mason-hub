"""
TikTok Viral Analysis Connector Transforms
将 tiktok-viral 的数据与 mason-hub 标准 schema 互转。

v0.1: 只定义接口签名，不写实现。
"""

from typing import Any


def to_standard_content(tiktok_data: dict) -> dict:
    """tiktok-viral 视频数据 → 标准 content schema"""
    raise NotImplementedError("v0.2 实现")


def to_competitor_prices(amazon_data: list) -> list:
    """Amazon 爬取的竞品数据 → 标准 price schema 的 competitor_prices"""
    raise NotImplementedError("v0.2 实现")


def to_review_insights(review_data: list) -> dict:
    """Amazon 评论 NLP 分析结果 → 结构化洞察"""
    raise NotImplementedError("v0.2 实现")


def execute_command(command: dict) -> dict:
    """
    接收 mason-hub 标准指令，调用对应脚本执行。

    支持的 action:
    - data.scrape_tiktok: 调用 Apify 采集 TikTok 数据
    - data.scrape_amazon: 采集 Amazon 评论/价格
    - analysis.viral_score: 计算爆款评分
    - analysis.review_nlp: 评论 NLP 分析
    - video.generate: 调用 Kling API 生成视频
    """
    raise NotImplementedError("v0.2 实现")
