"""Scout v2 Engine 架构 — 6 引擎串行管道

引擎顺序: spider → query → media → insight → forum → report
入口: python -m intel.engines.pipeline [--resume] [--force spider,query] [--days 3]
"""
