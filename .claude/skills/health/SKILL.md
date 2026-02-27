---
name: health
description: "全局健康检查：GCP、阿里云、进程、Git、Agent 系统"
---

# /health — 全局健康检查

执行全面的系统健康检查，**只报告异常**。如果一切正常，只输出一行"✅ 全部正常"。

## 检查项

### GCP 服务器
```bash
echo "=== GCP 基础 ==="
uptime
df -h / | awk 'NR==2 {if ($5+0 > 80) print "⚠️ 磁盘: "$5; else print "✅ 磁盘: "$5}'
free -h | awk 'NR==2 {print "内存: "$3"/"$2}'
```

### 关键进程
```bash
echo "=== 进程 ==="
# 检查 slack-bot
pgrep -f "slack-bot" > /dev/null && echo "✅ Slack Bot 运行中" || echo "❌ Slack Bot 未运行"

# 检查 cron
systemctl is-active cron > /dev/null 2>&1 && echo "✅ Cron 运行中" || echo "❌ Cron 未运行"
```

### 阿里云连通性
```bash
echo "=== 阿里云 ==="
timeout 5 ssh -o ConnectTimeout=3 root@106.14.44.68 "
  echo '✅ SSH 连通'
  uptime
  df -h / | awk 'NR==2 {if (\$5+0 > 80) print \"⚠️ 磁盘: \"\$5; else print \"✅ 磁盘: \"\$5}'
  systemctl is-active china-site 2>/dev/null && echo '✅ 后端运行中' || echo '⚠️ 后端状态未知'
" 2>/dev/null || echo "❌ 阿里云 SSH 不通"
```

### 阿里云 Web 端点
```bash
echo "=== Web 端点 ==="
timeout 5 curl -s -o /dev/null -w "%{http_code}" https://surenxuan.com/api/health 2>/dev/null | {
  read code
  if [ "$code" = "200" ]; then echo "✅ API 端点正常"
  else echo "❌ API 端点异常 (HTTP $code)"
  fi
} || echo "❌ API 端点不可达"
```

### Git 仓库状态
```bash
echo "=== Git ==="
cd ~/mason-hub && {
  changes=$(git status --short | wc -l)
  [ "$changes" -eq 0 ] && echo "✅ mason-hub clean" || echo "⚠️ mason-hub: $changes 未提交改动"
}
cd ~/surenxuan && {
  changes=$(git status --short | wc -l)
  [ "$changes" -eq 0 ] && echo "✅ surenxuan clean" || echo "⚠️ surenxuan: $changes 未提交改动"
}
```

### Agent 系统
```bash
echo "=== Agent 系统 ==="
# 检查角色文件完整性
for emp in 0000 0001 0002 0004 0005 0006; do
  [ -f ~/mason-hub/agents/EMP_${emp}.md ] && true || echo "❌ EMP_${emp}.md 缺失"
done

# 检查 skills 脚本可执行权限
for skill in check-syntax run-backend-tests dev-verify-loop health-check-full run-smoke-tests; do
  [ -x ~/mason-hub/skills/${skill}.sh ] && true || echo "⚠️ ${skill}.sh 不可执行"
done

# 检查记忆文件大小
for mem in ~/mason-hub/memory/EMP_*_lessons.md; do
  if [ -f "$mem" ]; then
    size=$(wc -c < "$mem")
    if [ "$size" -gt 10240 ]; then
      echo "⚠️ $(basename $mem): ${size} bytes — 考虑 compaction"
    fi
  fi
done
```

## 输出原则
- 正常的不报，只报异常
- 如果全部正常，就一行：✅ 全部正常（GCP ✅ | 阿里云 ✅ | Agent ✅）
- 有异常时按严重程度排序：❌ 最前，⚠️ 其次
