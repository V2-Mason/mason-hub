部署 surenxuan 到阿里云生产环境：

1. 检查 ~/surenxuan git status 是否 clean（有未提交改动先提醒 Mason）
2. 运行 skills/deploy-to-aliyun.sh
3. 如果部署失败，分析日志并给出修复建议
4. 部署成功后，运行 skills/run-smoke-tests.sh 验证生产环境
5. 汇报结果给 Mason
