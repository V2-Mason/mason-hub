# EMP_0004 SRE 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: nginx 部署必须配 gzip

部署 nginx 反代时必须配置 gzip 压缩（js/css/json/html/xml/svg），这是基本项，不是优化项。素仁轩 819KB JS bundle 未压缩传输，开 gzip 后压到 ~200KB（压缩率 75%）。应加入部署 checklist：nginx 上线 → 验证 gzip（curl -H "Accept-Encoding: gzip" 看 Content-Encoding 响应头）。
