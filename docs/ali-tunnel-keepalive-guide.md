# 阿里云隧道保活部署指南

> SRE 编写 | 2026-02-26 | Mason 在阿里云 (106.14.44.68) 上执行

## 背景

GCP 侧已部署每 5 分钟的隧道检测脚本，但隧道断开时 GCP 无法 SSH 到阿里云重启。
需要在阿里云侧也部署保活，形成双向守护。

当前 `reverse-tunnel.service` 已配置 `Restart=always`，systemd 会自动重启。
但有些场景 systemd 判断服务"存活"实际上隧道已不通（SSH 进程在但连接死了），所以需要额外的主动检测。

---

## Step 1：创建保活脚本

SSH 到阿里云后，执行：

```bash
cat > /opt/surenxuan/scripts/tunnel-keepalive.sh << 'EOF'
#!/bin/bash
# 阿里云侧反向隧道保活
# 检测隧道是否真正可用，不可用则重启 reverse-tunnel.service
TS=$(date '+%Y-%m-%d %H:%M:%S')
LOG="/opt/surenxuan/logs/tunnel-keepalive.log"
mkdir -p /opt/surenxuan/logs

# 通过隧道反向连接 GCP 来验证隧道是否真正通畅
# 如果 SSH 进程活着但隧道实际已死，这个检测会失败
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i /root/.ssh/id_ed25519 hangn@34.63.188.198 "echo ok" >/dev/null 2>&1; then
    echo "[$TS] ✅ 隧道正常" >> "$LOG"
    exit 0
fi

echo "[$TS] ❌ 隧道不通，重启 reverse-tunnel.service" >> "$LOG"
systemctl restart reverse-tunnel
sleep 5

if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i /root/.ssh/id_ed25519 hangn@34.63.188.198 "echo ok" >/dev/null 2>&1; then
    echo "[$TS] ✅ 重启后恢复" >> "$LOG"
else
    echo "[$TS] 🚨 重启后仍不通，可能是网络问题" >> "$LOG"
fi
EOF
```

```bash
chmod +x /opt/surenxuan/scripts/tunnel-keepalive.sh
```

## Step 2：注册 crontab

```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/surenxuan/scripts/tunnel-keepalive.sh") | crontab -
```

## Step 3：验证

```bash
# 确认脚本可执行
ls -la /opt/surenxuan/scripts/tunnel-keepalive.sh

# 确认 crontab 已注册
crontab -l

# 手动运行一次测试
/opt/surenxuan/scripts/tunnel-keepalive.sh

# 查看日志
cat /opt/surenxuan/logs/tunnel-keepalive.log
```

期望看到 `✅ 隧道正常`。

---

全部三条命令（Step 1 + 2 + 3）复制粘贴执行即可，约 1 分钟完成。
