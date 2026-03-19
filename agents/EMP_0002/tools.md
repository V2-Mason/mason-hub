# Platform Dev · 工具与协议索引

## 我能用的 Skills
→ skills/check-syntax/
→ skills/run-backend-tests/
→ skills/dev-verify-loop/

## 按需参考的协议（需要时才读，不是每次都读）
| 文件 | 何时读 |
|------|--------|
| kernel/standards/protocols/dev-execution.md | 需要任务执行流程细节时 |
| kernel/standards/protocols/escalation-architecture.md | 需要理解 escalation 链路时 |
| kernel/standards/protocols/tools.md | 使用通用工具时 |
| kernel/standards/protocols/agent-log-schema.md | 写入或查询 agent.log 时 |

## 关键工具路径
| 工具 | 路径 | 用途 |
|------|------|------|
| log-query.sh | scripts/log-query.sh | 查询结构化 agent log |
| backlog-scanner | scripts/backlog-scanner.py | 扫描可执行 backlog 任务 |
| distill-skills | scripts/distill-skills.py | 从 gateway-memory 提取 skill |
| worktree | scripts/worktree.sh | 并行开发 Git worktree 管理 |
| dispatcher | scripts/control/ | 任务调度（不要直接修改） |

## 不能碰的
- /opt/ 下所有内容
- data/ 下业务数据库
- 不能在 Claude Code session 内调用 run-agent.sh
