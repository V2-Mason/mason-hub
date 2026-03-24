# 微信聊天分析工具

## 数据流

```
员工微信PC → wechat-decrypt 解密 → analyze_chat.py 分析 → 素仁轩后端
```

## 使用

```bash
# 1. 设置 DeepSeek API Key
export DEEPSEEK_API_KEY="sk-xxx"

# 2. 编辑 config.json，填入要监控的 wxid

# 3. 分析（增量 + 上传）
python analyze_chat.py --db /path/to/decrypted_msg.db --incremental --upload

# 4. 只看图片进货单
python analyze_chat.py --db /path/to/decrypted_msg.db --images-only
```

## 过滤策略

1. **白名单** — config.json 的 watched_contacts/groups，只分析这些会话
2. **关键词** — product_keywords + business_keywords，无关消息跳过
3. **增量** — --incremental 只分析上次之后的新消息
4. **图片OCR** — 进货单/报价单图片用 DeepSeek Vision 提取产品+价格

## 输出

- `daily_report_YYYY-MM-DD.json` — 每日分析结果（订单/反馈/需求信号）
- `price_list_YYYY-MM-DD.json` — 从图片提取的进货单明细
- `last_analyzed.json` — 增量分析检查点
