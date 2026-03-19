# EMP_0003 ecommerce-manager — 工具与资源

## Skills

→ run-backend-tests
→ compact-memory

## MCP 服务

→ mcp-search: `node /home/hangn/claude-mem/scripts/mcp-server.cjs`（知识库搜索）

## 主动汇报

```bash
$SLACK_NOTIFY "$SLACK_CHANNEL" "消息内容"
```

Slack 频道：#ecommerce

## 按需参考

| 文件 | 何时读 |
|------|--------|
| `kernel/standards/protocols/startup.md` | 标准启动流程 |
| `kernel/standards/org-chart.md` | 组织架构 |
| `kernel/standards/ecommerce_knowledge_base.md` | 行业知识库 |

## 关键路径

- 知识库：`kernel/standards/ecommerce_knowledge_base.md`
- 下属 PM：EMP_0001（素仁轩）
- 下属分析师：EMP_0015（数据分析）
- Escalation 目标：EMP_0000（Meta Manager）

## 禁区

- 禁止跳过 mcp-search 直接更新 knowledge_base.md
- 禁止无 task_id 分配任务
- 禁止修改 `meta/knowledge_base.md`
- 不直接执行代码任务
- 不做跨域判断
