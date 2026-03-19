# Connectors

Mason 联邦体系的项目适配器。每个 connector 负责将 mason-hub 的标准指令转换为对应项目能理解的调用。

## 结构

```
connectors/
  [project-name]/
    config.yaml       ← 连接配置
    transforms.py     ← 数据格式转换（标准schema ↔ 项目内部格式）
```

## 当前状态

| Connector | 项目路径 | 通信方式 | 状态 |
|-----------|----------|----------|------|
| surenxuan | ~/surenxuan | HTTP API (localhost:8000) | v0.1 声明式 |
| tiktok-viral | ~/tiktok-viral-analysis | Script 调用 | v0.1 声明式 |
| socialmesh | ~/socialmesh | HTTP API (localhost:8001) | v0.1 声明式 |

## 版本说明

v0.1: config.yaml 只记录连接信息，transforms.py 只定义接口签名。
实际通信能力将在 v0.2 实现。
