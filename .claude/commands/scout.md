执行斥候情报巡逻：

1. 运行以下 4 个 scout 脚本收集原始数据：
   - skills/scout/scout-github.sh
   - skills/scout/scout-trending.sh
   - skills/scout/scout-anthropic.sh
   - skills/scout/scout-search-topic.sh（搜索当前 watchlist 中的主题）
2. 读取 intel/watchlist.md 获取关注列表
3. 将原始数据整理为情报简报，保存到 intel/digests/YYYY-WXX-digest.md
4. 保存原始数据到 intel/raw/YYYY-WXX-tech.md
5. 更新 intel/watchlist.md（新增值得关注的项目）
6. 发送简报摘要到 Slack #scout（C0AJBR8B82C）
