# 程序员鱼皮 57×9 Grid (preset: bilibili-dev-content v0.1)

**N=57** (19 top + 19 mid + 19 bot by selected.tsv bucket, re-split to 12/33/12 per Mason spec)
**K=12** (Top 12 = rows 1-12, Mid 33 = rows 13-45, Bot 12 = rows 46-57)

**Check 清单**:
- C1 反差/极端开场 (预期反向)
- C2 具名主角
- C3 系列索引
- C4 常青长尾查询词 (只看标题)
- C5 故事/事件开场
- C6 真实数据证据 (≥3 数字 + 真实锚点)
- C7 实操产出型标题
- C8 你/我代词
- C9 可抄作业 (福利/源码承诺)

**Notes**:
- `-` = UNKNOWN (转录缺失)，按保守 FAIL 计
- 2 条视频 (#2 BV1YF411a75Y, #56 BV1DB4y1c7zZ_330189610) 转录缺失，仅用标题评 C3/C4/C7/C9，其余 check UNKNOWN→FAIL
- "混合" 标注 = C1+C5 双 PASS 经复核后合法的案例
- C1 与 C5 互斥时，优先 C5 (preset 要求)

---

## Top 12 (K, views 3,084,612 ~ 676,709)

| # | BV | 标题(缩) | bucket | views | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BV1sQBPBmEGU | 突发快手被色情直播刷屏 | top | 3,084,612 | FAIL 事件陈述非数字反差 | PASS 快手具名 | FAIL 无系列 | FAIL 突发临时热点 | PASS 时间锚点2025-12-22 | PASS 10万/几百万/两个疑点 | FAIL 背后原因评论型 | PASS 我/大家 | FAIL 无产物 | C1/C5 复核取C5 |
| 2 | BV1YF411a75Y | 该无脑计算机吗b站大学上期 | top | 2,983,892 | FAIL UNKNOWN | FAIL 全抽象 | PASS b站大学+上期系列 | PASS 计算机/专业/讲透 | FAIL UNKNOWN | FAIL UNKNOWN | PASS 一个视频讲透所有专业 | FAIL UNKNOWN | FAIL 无产物 | 转录缺失 |
| 3 | BV15g41157NK | 2025最新Java学习路线一条龙 | top | 1,582,913 | FAIL Hello自介 | PASS Java/程序员于皮 | FAIL 无集数 | PASS Java+学习路线+零基础 | FAIL 自介陈述 | FAIL 仅八个阶段1数字 | PASS 学习路线一条龙 | PASS 我/大家 | PASS 回复Java路线领取 | — |
| 4 | BV1tT4y1y7T4 | 托大家的福网站又被攻击了 | top | 1,532,144 | FAIL 感叹句非反差 | PASS 鱼皮/网站 | FAIL 无系列 | PASS 网站+攻击 | PASS 正要出去吃烧烤+对话 | PASS 一小时/六十万次/两千次 | FAIL 事件报告型 | PASS 兄弟们/我/大家 | FAIL 无产物 | — |
| 5 | BV1aM411K7tD | 我开业啦 | top | 1,139,098 | FAIL 宣告陈述 | PASS 云渊网络/鱼皮 | FAIL 无集数 | FAIL 开业非长尾 | FAIL 自介陈述 | FAIL 无数字 | FAIL 宣告型 | PASS 我/大家 | FAIL 无产物 | — |
| 6 | BV1iM411T7ey | 再见了腾讯 | top | 968,455 | FAIL 辞职陈述 | PASS 腾讯具名 | FAIL 无系列 | PASS 腾讯平台名 | PASS 时间回到大三暑假 | FAIL 仅四年/大三2数字 | FAIL 离职宣告 | PASS 我/你/朋友们 | FAIL 无产物 | — |
| 7 | BV1xp2hYHEVn | 程序员攻占小猿口算炸哭小学生 | top | 964,934 | PASS 小学生被大学生博士暴打 | PASS 小猿口算/GitHub | FAIL 无系列 | FAIL 攻占情绪词 | FAIL 情境铺陈非时间动作 | FAIL 前60秒内无3数字 | FAIL 事件报道型 | FAIL 无人称 | FAIL 无产物 | — |
| 8 | BV1y3411r7pX | 我该学哪个编程语言10+对比 | top | 836,832 | FAIL 哈喽自介 | PASS Java/Python/Go/C语言 | FAIL 无系列 | PASS 编程语言+入门+自学 | FAIL 自介陈述 | FAIL 10+ 1数字 | PASS 入门科普10+对比 | PASS 我/大家/你 | FAIL 无产物 | — |
| 9 | BV1rU4y1J785 | 手把手带你从0搭建个人网站 | top | 823,910 | FAIL 哈喽自介 | PASS 鱼皮 | FAIL 无系列 | PASS 搭建网站+博客+自学 | FAIL 自介式 | FAIL 两种/一个数字弱 | PASS 手把手保姆级2种方法 | PASS 我/大家/你 | FAIL 无明确包 | — |
| 10 | BV1nJCxBmEmi | 颜色网站为啥都收费 | top | 733,674 | FAIL 场景非数字反差 | PASS 编程导航/鱼皮 | FAIL 无系列 | PASS 多少钱+网站+为啥 | PASS 这天深夜你打开网站 | FAIL 无具体数字 | PASS 从开发到运营完整流程 | PASS 你/我/大家 | FAIL 无福利承诺 | C5 场景对话 |
| 11 | BV15XZLBLEab | 我用OpenClaw做了个女朋友 | top | 695,351 | PASS 女朋友其实是AI反差揭秘 | PASS OpenClaw/GLM5/OpenCloud | FAIL 无系列 | PASS OpenClaw+AI女友+程序员 | FAIL 介绍式非时间动作 | FAIL 24小时/第一步2个 | PASS 我用做了个+流程四步 | PASS 我/大家/你 | FAIL 无产物 | — |
| 12 | BV1Tb411Q7V4 | 没想到又被攻击了赔了1.5万 | top | 676,709 | PASS 1.5万流量费极端数字 | FAIL 无具名主角 | FAIL 无明确系列 | FAIL 被攻击事件词 | PASS 2月28日那天收到告警 | PASS 1.5万/1万/5000/5G/2000G | FAIL 事件报告型 | PASS 我/大家 | FAIL 无产物 | C1+C5 复核合法 |

---

## Mid 33 (views 618,173 ~ 31,800)

| # | BV | 标题(缩) | bucket | views | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 13 | BV1CM4y137kF | 99%的网站根本不用自己做 | top | 618,173 | PASS 99%网站不用自己做 | PASS WordPress/Doxify/鱼皮 | FAIL 无系列 | PASS 网站+建站 | FAIL 大家好自介 | PASS 99%/十个/8000+ | PASS 分享十个 | PASS 你/我/大家 | FAIL 无包 | — |
| 14 | BV1fuyZBqEES | CSDN离谱操作把程序员整破防 | top | 597,027 | PASS 八年博客只赚3.4元极端反差 | PASS CSDN具名 | FAIL 无系列 | PASS CSDN+程序员 | FAIL 过分陈述 | PASS 三天/八年/3.4元/2块6/8毛/400篇 | FAIL 事件评论 | PASS 我/大家/你 | FAIL 无产物 | — |
| 15 | BV1xnZ3BDEXj | 26年春晚魔术揭秘给程序员看笑 | top | 586,595 | FAIL 陈述式 | PASS 春晚/AI/计算器 | FAIL 无系列 | FAIL 春晚临时热点 | FAIL 陈述 | PASS 五分钟/9527/12315/21842/2140486/2月16号 | PASS 我教大家怎么变 | PASS 你/我/大家 | FAIL 无产物 | — |
| 16 | BV1Ab4y1r7bo | 编程5年30个编程工具大分享 | top | 552,936 | FAIL 哈喽自介 | PASS 程序员于皮 | FAIL 无系列 | PASS 编程工具+新手自学+开发效率 | FAIL 自介 | PASS 5年/30个/四大类/近30种 | PASS 30个工具大分享 | PASS 我/大家/你 | FAIL 无产物 | — |
| 17 | BV1LZ4y1B7Q1 | 网站天天被攻击后我终于出手了 | top | 517,624 | FAIL 陈述式 | FAIL 全抽象 | FAIL 无系列 | FAIL 被攻击事件词 | FAIL 陈述 | FAIL 数字弱 | FAIL 事件报告 | PASS 大家/我 | FAIL 无产物 | — |
| 18 | BV1eP411N7B7 | 我做了个小工具帮你提升100倍 | top | 511,871 | PASS 100倍效率标题反差 | PASS 于皮/sircle之父 | FAIL 无系列 | FAIL 100倍非长尾 | FAIL 自介式 | FAIL 100倍1数字 | PASS 我做了个小工具 | PASS 我/大家/你 | FAIL 无产物 | — |
| 19 | BV1xQ2WBZEgs | 紧急全球服务器被挖矿入侵 | top | 506,147 | FAIL 事件陈述 | PASS React/Next.js/腾讯云/GitHub | FAIL 无系列 | PASS React+Next.js+服务器 | PASS 2025-12-5下午腾讯云告警 | PASS 12月5日/晚7点59/早6点9点 | FAIL 事件报告型 | PASS 我/大家 | FAIL 无产物 | C1/C5复核取C5 |
| 20 | BV1b142187Tb | 10招反爬虫经验分享 | mid | 156,087 | FAIL 对话无反差 | FAIL 全抽象 | FAIL 无系列 | PASS 爬虫+程序员+10招 | PASS 面试对话引入 | FAIL 4000+/100+2数字 | PASS 10招+经验分享 | PASS 我/你/我们 | FAIL 无产物 | — |
| 21 | BV1Fc411y7HS | 离谱的Bug咋就让我撞上了 | mid | 154,531 | FAIL 大家好自介 | PASS Swider/OpenAPI/JSON | FAIL 无系列 | FAIL 离谱Bug情绪词 | FAIL 自介 | FAIL 无数字 | FAIL 感叹型 | PASS 我/大家 | FAIL 无产物 | — |
| 22 | BV1rG411k7BQ | 重构云计算大厂都在卷这个 | mid | 153,851 | FAIL 大家好自介 | PASS 百度/千帆/文心 | FAIL 无系列 | PASS 云计算+大模型 | FAIL 自介 | PASS 十倍/八次/几十种 | FAIL 大会观察型 | PASS 我/你/我们 | FAIL 无产物 | — |
| 23 | BV15g411R7dE | 给王心凌男孩做个超甜的网站 | mid | 152,240 | FAIL 半小时非极端 | PASS 王心凌/wiki.js | FAIL 无系列 | FAIL 王心凌男孩临时热点 | PASS 我花半小时帮朋友做 | FAIL 数字弱 | PASS 带大家安装体验 | PASS 我/你/大家 | FAIL 无产物 | — |
| 24 | BV1ho4y1b75o | AutoGPT傻瓜式使用教程 | mid | 151,515 | FAIL 陈述式 | PASS AutoGPT/ChatGPT | FAIL 无系列 | PASS AutoGPT+ChatGPT+教程 | FAIL 定义式 | FAIL 两周/10万+弱 | PASS 傻瓜式教程+真实体验 | PASS 我/大家/你 | FAIL 无产物 | — |
| 25 | BV1S34y1Y7TS | 我年纪轻轻代码量3200一个月 | mid | 148,220 | PASS 3200代码量标题反差 | FAIL 无真具名 | FAIL 无系列 | FAIL 代码量情绪词 | PASS 有次开组会对话 | FAIL 前60秒仅3200+1月 | FAIL 段子宣告 | PASS 我/大家/你 | FAIL 无产物 | C1+C5 混合 |
| 26 | BV1DYmxBkEBV | 我去IDEA竟然免费了 | mid | 148,019 | PASS IDEA免费反差 | PASS IDEA/Java/Kotlin/Spring | FAIL 无系列 | PASS IDEA+Java+程序员 | FAIL 新闻陈述 | FAIL 30天1数字 | FAIL 新闻报道 | FAIL 前60秒无代词 | FAIL 无产物 | — |
| 27 | BV1LQ4y1V79r | 做网站不需要写代码VuePress | mid | 147,410 | FAIL 大家好自介 | PASS Codefather/VuePress/鱼皮 | FAIL 无系列 | PASS 做网站+VuePress+保姆级 | FAIL 自介陈述 | FAIL 五分钟/30秒2数字 | PASS 模板+保姆级教程 | PASS 我/大家/你 | PASS 提供二次开发文档网站模板 | — |
| 28 | BV1i9Z8YhEja | 学AI看这个视频就够了 | mid | 147,041 | PASS AI会淘汰程序员吗会反差 | FAIL 全抽象AI概念 | FAIL 无系列 | PASS AI+程序员+学+指南 | FAIL 提问陈述 | FAIL 无数字 | PASS 最全程序员AI指南 | PASS 你/我/大家 | FAIL 无产物 | — |
| 29 | BV1oP4y1W7qm | 面试阿里6次全挂 | mid | 146,851 | PASS 6次全挂极端 | PASS 阿里/腾讯/Spring Cloud | FAIL 无系列 | PASS 阿里+大厂面试+程序员 | FAIL Hello自介 | FAIL 六次同数字 | PASS 面试经验分享 | PASS 我/大家 | FAIL 无产物 | — |
| 30 | BV1zq4y1K7bS | 学计算机读研还是就业我的故事 | mid | 146,425 | FAIL 自介陈述 | PASS 上海东华大学/腾讯 | FAIL 无系列 | PASS 学计算机+读研+就业 | FAIL 自介 | FAIL 无数字 | FAIL 故事叙事型 | PASS 我/大家/你 | FAIL 无产物 | — |
| 31 | BV1e92eBTEkL | 什么是负载均衡加台服务器 | mid | 144,817 | PASS 一万用户冲爆服务器 | PASS 鱼蛋/鱼皮/LB | FAIL 无系列 | PASS 负载均衡+服务器 | PASS 你是小阿爸场景+动作 | PASS 前几天/一周后/一万/三台 | FAIL 概念讲解型 | PASS 你/我 | FAIL 无产物 | C1+C5 混合 |
| 32 | BV1Ki4y1T7Cu | 不会找编程项目大厂教你不求人 | mid | 144,275 | FAIL 陈述自介 | PASS Github/Gitty/开源中国 | FAIL 无系列 | PASS 编程项目+大厂程序员+找 | FAIL 自介 | FAIL 十几个/100万弱 | PASS 硬核干货手把手教 | PASS 我/大家/你 | FAIL 无产物 | — |
| 33 | BV1WX4y1o7aL | 用ChatGPT自动解决问题 | mid | 143,817 | FAIL 陈述式 | PASS ChatGPT/OpenAI/Java Spring Boot | FAIL 无系列 | PASS ChatGPT工具 | FAIL 陈述 | FAIL 无数字 | PASS 自己动手开发工具 | PASS 我/大家/你 | PASS 代码完全开源 | — |
| 34 | BV1M64y1X7DE | 给计算机同学的血泪建议 | mid | 143,712 | FAIL 梗开场非数字反差 | PASS 鱼皮/鹅厂 | FAIL 无系列 | PASS 学好编程+大学生活+程序员 | FAIL 自介式 | FAIL 大学四年1数字 | PASS 血泪建议+实用建议分享 | PASS 我/大家/你 | FAIL 无产物 | — |
| 35 | BV1pZ421M76B | 离谱B站又崩了这次真的不怪他 | mid | 139,694 | FAIL 并列情境陈述 | PASS B站/小红书/扑安网 | FAIL 无系列 | PASS B站+小红书平台名 | PASS 今天上午10-11点 | FAIL 10-11/-500 2数字 | FAIL 事件报告+猜测 | PASS 我/大家/你 | FAIL 无产物 | — |
| 36 | BV1YqyGYGEoN | 神反转8年程序员被半年小白血虐 | mid | 138,754 | PASS 8年vs半年标题反差 | PASS 于皮尔/云安网络/首届马王争霸赛 | FAIL 无集数 | FAIL 神反转/血虐情绪词 | PASS 欢迎来到争霸赛场景引入 | PASS 8年/半年/25岁/2000元 | FAIL 比赛事件 | PASS 我/我们/各位 | FAIL 无产物 | C1+C5 双PASS合法 |
| 37 | BV1uP411x78n | 网站崩了我却很开心 | mid | 137,010 | FAIL 情绪反差非数字 | FAIL 鱼皮+网站抽象 | FAIL 无系列 | FAIL 崩了事件词 | PASS 今天周末+刚起床+用户反馈 | FAIL 一秒/几十秒2数字 | FAIL 事件叙述 | PASS 我/大家/你 | FAIL 无产物 | C1/C5 复核取C5 |
| 38 | BV1TV4y1j76t | 1分钟上线个人网站工具杀疯了 | mid | 136,952 | PASS 1分钟上线极端数字 | PASS Warsel/GitHub | FAIL 无系列 | PASS 上线个人网站+工具 | FAIL Hello自介 | PASS 几年前/一分钟/两种 | PASS 傻瓜式神器分享 | PASS 我/大家/你 | FAIL 无产物 | — |
| 39 | BV15KF5z1EWk | Java程序员必做的AI项目智能体 | bot | 31,800 | FAIL 教程中段非反差 | PASS Java/Solverless/腾讯云/Railway | FAIL 无系列 | PASS Java+AI项目+程序员+简历 | FAIL 教程讲解 | FAIL 四核/八核2数字 | PASS 必做的AI项目写满简历 | PASS 我/你/大家 | FAIL 无产物 | — |
| 40 | BV1KbXQY8Ey6 | DeepSeek隐藏技巧+保姆级教程 | bot | 30,490 | PASS 腾讯市值飙升3000亿 | PASS DeepSeek/腾讯 | FAIL 无系列 | PASS DeepSeek+保姆级教程 | FAIL 陈述式 | PASS 3000亿/数十条/破千 | PASS 隐藏技巧+信息差+汇总 | PASS 我/大家/你 | PASS AI知识库链接评论区 | — |
| 41 | BV1Xm421N7Xj | Java程序员必做的AI答题平台 | bot | 28,991 | FAIL Hello自介 | PASS Java/MBTI/AI/编程导航 | FAIL 无系列 | PASS Java+AI项目+程序员+简历 | FAIL 自介式 | FAIL 16种1数字 | PASS 必做的AI项目+答题平台 | PASS 我/大家/你 | PASS 开源版本GitHub获取 | — |
| 42 | BV18NmnB4EeM | 干掉Visio程序员画图神器 | bot | 28,845 | PASS 谁还人工画图AI几十秒 | PASS Visio/编程导航/Warsel AISDK | FAIL 无系列 | PASS Visio+程序员+画图 | FAIL 反问陈述 | PASS 几十秒/几天/5000STAR | PASS 神器+干掉 | PASS 我/你 | FAIL 无产物 | — |
| 43 | BV15M4m127dV | 99%网站都死在了这件事上 | bot | 27,995 | PASS 99%死在标题反差 | FAIL 语却抽象概念 | FAIL 无系列 | PASS 网站开发+经验分享 | FAIL 陈述式 | FAIL 无≥3数字 | PASS 经验分享+流程 | PASS 我/你/我们 | FAIL 无产物 | — |
| 44 | BV1dW4tz9E5M | AI程序员练兵场专治技术焦虑 | bot | 27,327 | PASS 月薪三千极端数字 | PASS Spring Boot/MyBatis/DDD/CQRS/鱼皮 | FAIL 无系列 | PASS AI+程序员+技术 | PASS 你是月薪三千的程序员慕名来到 | FAIL 三千/八千2数字 | PASS 我造了个练兵场 | PASS 你/我 | FAIL 无产物 | C1+C5 混合 |
| 45 | BV17N4y1h7YM | 一键生成GitHub年总结视频 | bot | 26,922 | FAIL 新闻陈述 | PASS GitHub/Remotion/GraphQL API | FAIL 无系列 | PASS GitHub+生成+视频 | FAIL 陈述 | FAIL 无数字 | PASS 一键生成+演示 | PASS 我/你 | FAIL 无产物 | — |

---

## Bot 12 (views 25,831 ~ 10,871)

| # | BV | 标题(缩) | bucket | views | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 46 | BV1zVAHesEv7 | DeepSeek满血版API教程 | bot | 25,831 | FAIL 陈述式 | PASS DeepSeek/Java/腾讯云/阿里云/火山引擎 | FAIL 无系列 | PASS DeepSeek+API+教程 | FAIL 陈述 | FAIL 两分钟1数字 | PASS API使用教程 | PASS 我/你/大家 | PASS 第三方平台对比表格 | — |
| 47 | BV1MnpVzdETW | 用AI读文档Claude Code+Kimi | bot | 24,274 | FAIL 陈述式 | PASS Claude Code/Kimi/Node/K2/API | FAIL 无系列 | PASS AI+Claude Code+文档助手 | FAIL 陈述 | FAIL 256k/几十万2数字 | PASS 做了个网站+开发助手 | PASS 我/你/大家 | PASS 代码完全开源+启动脚本 | — |
| 48 | BV1tf4y1E7H3 | 自己搭建写文档最佳利器 | bot | 21,361 | FAIL 教程中段切入 | PASS Tapra/pitchergo/语却/腾讯文档 | FAIL 无系列 | PASS 写文档+搭建+手把手 | FAIL 教程中段 | FAIL 无数字 | PASS 手把手教程+最佳利器 | PASS 我/大家 | FAIL 无明确包 | — |
| 49 | BV1QFTJzzENP | 无限执行AI Flowith保姆级教程 | bot | 21,019 | PASS 万字小说极端能力+数字 | PASS FlowWays/Flowith | FAIL 无系列 | PASS Flowith+AI智能体+教程 | FAIL 能力陈述 | PASS 几十页/万字/千万字/2.0 | PASS 保姆级教程+体验 | PASS 我们/你/大家 | FAIL 无产物 | — |
| 50 | BV11hx5euEbD | 我做了程序员面试刷题沉浸摸鱼 | bot | 19,262 | FAIL Hello自介 | PASS 面试鸭/JetBrains/WebStorm/PiCharm | FAIL 无系列 | PASS 程序员面试+刷题工具 | FAIL 自介 | PASS 两月/十万+/9-12点/14-18点/一月/一分钟 | PASS 我做了面试刷题工具 | PASS 我/大家/你 | FAIL 无承诺 | — |
| 51 | BV14NyrBTEeB | 什么是AI网关大厂开发神器 | bot | 17,830 | FAIL 人物设定非反差 | PASS OpenAI/GPT/Cloud/通力千万 | FAIL 无系列 | PASS AI网关+AI开发 | PASS 你是小阿爸+老板对话 | FAIL 无数字 | FAIL 概念讲解型 | PASS 你/老板 | FAIL 无产物 | — |
| 52 | BV1f1XJYtEbm | 鉴定网络热门应用神奇APP大赏 | bot | 17,245 | PASS 赛博拉屎抽烟荒诞反差 | PASS 爸爸简史/赛博吸/Turcer | FAIL 无集数 | FAIL 赛博拉屎情绪热点词 | FAIL 列表式 | PASS 5万/3.8万点赞/1.2万评论 | FAIL 评论娱乐型 | PASS 我们/你 | FAIL 无产物 | — |
| 53 | BV1CkUDBiEMR | 10个免费网站分析神器省几万 | bot | 16,018 | PASS 10个省几万极端数字 | PASS 百度统计/五一拉/谷歌分析/SimilarWeb/AITDK | FAIL 无系列 | PASS 网站分析+免费神器 | PASS 学妹问我UPJJ对话 | FAIL 10个/几万2数字 | PASS 10个神器+省掉几万元 | PASS 我/你 | FAIL 无承诺 | — |
| 54 | BV1ph411p76w | 最硬程序员中秋节月饼 | bot | 12,996 | FAIL 标题猎奇非反差 | FAIL 中秋/月饼抽象 | FAIL 无系列 | FAIL 中秋月饼节日热点 | PASS 中秋节+德才采访 | FAIL 无数字 | FAIL 采访娱乐 | PASS 你/我/我们 | FAIL 无产物 | — |
| 55 | BV1KXkkBKExf | 我做出取消回合制的技能五子棋 | bot | 11,096 | PASS 取消回合制反差+反问 | PASS 技能五子棋/五子棋大赛 | FAIL 无系列 | FAIL 五子棋非长尾 | PASS 自我介绍+踢馆对话 | FAIL 第一个1数字 | PASS 我做出了五子棋 | PASS 我/你 | FAIL 无产物 | C1+C5 双PASS合法 |
| 56 | BV1DB4y1c7zZ_330189610 | 用代码让小电视动起来 | bot | 13,564 | FAIL UNKNOWN | PASS 小电视 | FAIL 无系列 | PASS 用代码+编程实战 | FAIL UNKNOWN | FAIL UNKNOWN | PASS 用代码让小电视动起来 | FAIL UNKNOWN | FAIL 无承诺 | 转录缺失 |
| 57 | BV1wqTTzoEoo | AI高考分数预测器终于能上清华 | bot | 10,871 | PASS 终于能上清华调侃反差 | PASS 清华/北大/985211/AI | FAIL 无系列 | PASS AI+高考+清华 | PASS 马上高考我参加不了 | FAIL 0.001%1数字 | PASS 做了个预测器 | PASS 我/你/大家 | FAIL 无产物 | C1+C5 双PASS合法 |

---

## Grid Complete — 57 × 9 = 513 格全部 PASS/FAIL 填完 (含 2 UNKNOWN→FAIL 转录缺失条)
