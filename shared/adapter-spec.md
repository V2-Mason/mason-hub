# Adapter 规范 v0.1

## 概述

每个联邦节点（独立项目）通过 `.mason/adapter.yaml` 向 mason-hub 声明自己的能力。
mason-hub 通过读取各节点的 adapter.yaml 了解整个联邦的能力全景。

## adapter.yaml 必填字段

```yaml
project: string        # 项目名（与目录名一致）
version: string        # adapter 版本
status: string         # active | inactive | planned
endpoint: string       # API地址 或 "script-based"
type: string           # api | script | hybrid
capabilities: [string] # 能力列表，格式为 domain.action
```

## 可选字段

```yaml
markets:               # 支持的市场（电商项目适用）
  - id: string
    currency: string
    channels: [string]
    status: string     # active | planned

dependencies:          # 依赖的外部服务
  - name: string
    type: string       # api | database | service
    required: boolean

health_check:          # 健康检查端点
  endpoint: string
  interval: string     # 检查频率，如 "5m"
```

## 能力命名规范

格式：`domain.action`

常用 domain:
- `inventory` — 库存相关
- `product` — 商品相关
- `order` — 订单相关
- `pricing` — 定价相关
- `content` — 内容相关
- `data` — 数据采集/处理
- `analysis` — 分析相关
- `video` — 视频相关
- `analytics` — 数据分析/统计
- `report` — 报表相关

常用 action:
- `query` / `list` / `detail` — 读取
- `create` / `update` / `delete` — 写入
- `suggest` / `predict` — AI 建议
- `publish` / `schedule` — 发布

## hooks 规范

`hooks/on_command.sh` 接收 mason-hub 发来的指令：

```bash
#!/bin/bash
# 参数: $1 = command JSON (base64 encoded)
# 返回: stdout = result JSON
# 退出码: 0 = 成功, 1 = 失败, 2 = 需要人工确认

COMMAND=$(echo "$1" | base64 -d)
echo "received: $COMMAND"
# v0.1: 空壳，不做实际处理
```

## 版本演进计划

- v0.1（当前）: 声明式，mason-hub 只读 adapter.yaml，不实际调用
- v0.2: mason-hub 可通过 hooks 向节点发送指令
- v0.3: 节点可主动向 mason-hub 上报事件
- v1.0: 完整双向通信，支持 A2A 协议
