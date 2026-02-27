使用 run-agent.sh 启动 Dev (EMP_0005) 执行开发任务。

参数: $ARGUMENTS（任务描述）

执行步骤：
1. 将用户的任务描述格式化为 task_id（格式: srx_YYYYMMDD_简短描述）
2. 运行: bash ~/mason-hub/scripts/run-agent.sh agents/EMP_0005.md "$ARGUMENTS"
3. 监控输出，如果 agent 完成：
   - 汇报修改了哪些文件
   - 汇报验证结果（通过/失败）
   - 如果代码已提交，显示 commit hash
4. 如果 agent 失败且触发了 escalation，跟踪链式触发的结果
5. 最终汇报给 Mason
