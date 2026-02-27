# /deploy — 部署到阿里云生产环境

执行一键部署流程。每个步骤必须成功才能继续下一步，任何失败立即停止并报告。

## 部署流程

### Step 1: 预检
```bash
echo "=== 预检 ==="
# 确认 surenxuan 工作目录干净
cd ~/surenxuan
changes=$(git status --short | wc -l)
if [ "$changes" -gt 0 ]; then
  echo "❌ surenxuan 有 $changes 个未提交改动，先 commit 再部署"
  git status --short
  exit 1
fi

# 确认阿里云 SSH 连通
timeout 5 ssh -o ConnectTimeout=3 root@106.14.44.68 "echo ok" > /dev/null 2>&1 || {
  echo "❌ 阿里云 SSH 不通，部署终止"
  exit 1
}

echo "✅ 预检通过"
```

### Step 2: 推送代码
```bash
echo "=== 推送代码 ==="
cd ~/surenxuan
# 推到 GitHub
git push origin main 2>&1 || {
  echo "⚠️ GitHub push 失败，尝试直接 SCP..."
  # fallback: 直接传文件到阿里云
  tar czf /tmp/surenxuan-deploy.tar.gz --exclude='.git' --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' .
  scp /tmp/surenxuan-deploy.tar.gz root@106.14.44.68:/tmp/
  ssh root@106.14.44.68 "cd /opt/surenxuan && tar xzf /tmp/surenxuan-deploy.tar.gz"
}
echo "✅ 代码已推送"
```

### Step 3: 阿里云端部署
```bash
echo "=== 阿里云部署 ==="
ssh root@106.14.44.68 << 'DEPLOY'
  cd /opt/surenxuan

  # 拉取最新代码（如果是 git 方式）
  git pull origin main 2>/dev/null || echo "跳过 git pull（使用 SCP 方式）"

  # 安装后端依赖
  cd backend
  source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
  pip install -r requirements.txt -q 2>&1 | tail -3

  # 编译前端（如果有变更）
  cd ../frontend
  if [ -f package.json ]; then
    npm install --silent 2>&1 | tail -3
    npm run build 2>&1 | tail -3
  fi

  # 重启后端服务
  cd ..
  systemctl restart surenxuan-backend 2>/dev/null || {
    echo "systemctl 不可用，尝试手动重启..."
    pkill -f "uvicorn\|gunicorn" 2>/dev/null
    cd backend && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/surenxuan.log 2>&1 &
  }

  echo "✅ 后端已重启"
DEPLOY
```

### Step 4: 健康检查
```bash
echo "=== 健康检查 ==="
sleep 5  # 等后端启动

# 检查 API 端点
code=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" http://106.14.44.68:8000/api/health 2>/dev/null)
if [ "$code" = "200" ]; then
  echo "✅ API 健康检查通过"
else
  echo "❌ API 健康检查失败 (HTTP $code)"
  echo "查看日志: ssh root@106.14.44.68 'tail -20 /var/log/surenxuan.log'"
  exit 1
fi

echo ""
echo "🎉 部署完成！"
```

## 注意
- 如果部署失败在 Step 3 或 Step 4，阿里云上的旧版本可能已被覆盖
- 遇到严重问题时，告诉 Mason 手动 SSH 到阿里云检查
- 部署前不要自动 commit——如果有未提交改动，提醒用户先处理
