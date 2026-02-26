# Agent Communication Protocol v1.0

## task_assign
触发者：Manager或PM
目标：Dev agent
必填字段：
  - task_id: 唯一标识（格式：{project}_{date}_{序号}，例如srx_20260225_001）
  - assignee: 目标agent名称
  - description: 任务描述（清晰到Dev agent不需要猜测）
  - context_files: 需要读取的文件路径列表
  - expected_output: 期望的输出格式和内容
  - allowed_paths: 允许读写的路径列表
  - retry_policy: {max_retries: 3, notify_on_failure: "pm"}

## task_complete
触发者：Dev agent（主动上报，不等被问）
目标：PM
必填字段：
  - task_id: 对应的task_id
  - output_summary: 做了什么（100字以内）
  - files_modified: 修改了哪些文件
  - insights: 这个任务产生了什么新发现（没有则填null）
  - needs_escalation: true/false
  - escalation_reason: 如果needs_escalation为true，说明原因

## task_failed
触发者：Dev agent
目标：PM
必填字段：
  - task_id: 对应的task_id
  - failure_reason: 失败原因
  - retry_count: 已重试次数
  - last_state: 失败前的最后状态

## escalate
触发者：PM
目标：Manager
必填字段：
  - issue_description: 问题描述
  - options: 可选方案列表（至少两个）
  - pm_recommendation: PM的推荐方案和理由
  - urgency: low/medium/high

## memory_update_request
触发者：任何agent
目标：上级agent
必填字段：
  - content: 建议写入的内容
  - target_layer: project/domain/meta
  - reason: 为什么这个值得被记住

## shutdown_request
触发者：Manager或PM
目标：任何agent
必填字段：
  - reason: 关闭原因
  - allow_refusal: true/false（是否允许agent拒绝）

## shutdown_response
触发者：被关闭的agent
目标：发出shutdown_request的agent
必填字段：
  - approve: true/false
  - reason: 如果拒绝，说明原因
  - estimated_completion: 如果拒绝，预计完成时间
