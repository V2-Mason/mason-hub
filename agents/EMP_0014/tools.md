# EMP_0014 Data Engineer — 工具与资源

## Skills

（无注册 skills）

## 核心工作路径

- → `data/data_catalog.yaml` — 数据目录（核心工作文件）
- → `data/pipelines/` — 管道脚本（xhs-clean.py, assemble-data.py）
- → `data/schemas/` — Schema 定义
- → `data/tools/` — SDK 接口 v0.2.0（pipeline.py, sdk.py, metrics.py）
- → `data/mirror/` — 阿里云数据镜像

## 按需参考

| 文件 | 何时读 |
|------|--------|
| `data/data_catalog.yaml` | 核心工作文件 |
| `shared/protocols/startup.md` | 标准启动流程 |

## 关键脚本

- → `data-sync.sh` — 阿里云→GCP 文件同步（方案 A）
- → `data_health_check.sh` — 17 数据集健康检查
- → `skills/xhs/_xhs_helper_full_crawl.py` / `_xhs_school_fetch_details.py` — XHS 文档月度刷新

## 禁区

- 不做业务分析或情报判断
- 不做 agent 框架开发
- 不做管道监控告警执行
