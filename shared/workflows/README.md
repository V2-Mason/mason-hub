# Workflow Templates — v1.1 §7

Workflow 模板定义多步骤管道，dispatcher 按 state.yaml 推进。

## 格式

```yaml
id: workflow-name
account: surenxuan          # 品牌上下文
trigger:                    # 触发方式
  type: manual | cron | event
  input: [field1, field2]   # manual 时需要的输入

steps:
  - id: step-name
    role: EMP_XXXX           # 执行角色
    task: "任务描述"
    coupling: tight_with_next | loose_with_next | conditional
    requires_approval: false  # true = 暂停等 Mason 审批
    output_artifact: path    # 产出文件路径（相对 artifacts/）
    input_from: [step.output] # 从哪个步骤获取输入
    runtime_override: {}     # 覆盖角色默认 runtime
    on_fail: retry | skip | rerun_from_step_id
    timeout: 600             # 秒
```

## 文件

- `surenxuan-content-production.yaml` — 内容生产管道
- `surenxuan-video-replication.yaml` — 视频复制管道（Phase 6）
- `pm-dev-negotiation.yaml` — PM-Dev 协商（Phase 4）
