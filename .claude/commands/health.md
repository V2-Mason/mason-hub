执行全局健康检查：

1. 运行 skills/agent-status-report.sh 获取 agent 系统状态
2. 运行 skills/health-check-full.sh 检查基础设施
3. 运行 skills/agent-doctor.sh 检查 agent 配置完整性
4. 检查 GCP 系统资源（df -h, free -h）
5. 检查阿里云 health endpoint（curl http://106.14.44.68:8000/api/health）
6. 汇总为简洁报告，只报告异常项，正常的一行带过
