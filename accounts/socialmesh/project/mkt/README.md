# SocialMesh 内容运营方法论

> 内化自 shared/mkt/ 公共技能库，适配 SocialMesh 项目上下文。
> Creator (EMP_0010) 和 Dev (EMP_0009) 读这个目录，不读 shared/mkt/。

## 文件清单

| 文件 | 用途 | 主要读者 |
|------|------|---------|
| context.md | 品牌上下文（品牌定位、人设、调性、禁忌） | Creator / PM |
| content-strategy.md | 内容分类 + 支柱 + 选题 + 发布节奏 + 复盘 | PM |
| scoring.md | 选题优先级评分 + 采集数据对接 | PM |
| hooks-xhs.md | XHS 标题/开头/CTA 公式库 | Creator |
| copywriting-xhs.md | XHS 文案框架 + 质量检查清单 | Creator |
| customer-language.md | 客户原话采集方法 + 语言对照表 | Creator / PM |

## 品牌上下文说明

context.md 由品牌 PM 或 Mason 定义，内容运营总监不负责品牌定位。
当前 context.md 为模板状态，所有品牌特定字段标注为"待品牌 PM 填写"。

## 数据管道对接

本目录的方法论与以下自动化管道集成：

```
MediaCrawler 采集 (阿里云)
  → xhs-analyze.sh (GCP cron 每周六)
    → weekly_analysis.json (关键词洞察 + 爆帖排行)
      → xhs-strategy-briefing.sh
        → briefings/YYYY-MM-DD.json (策略简报，推 Slack #socialmesh)
          → PM 读取，结合本目录方法论产出 weekly-direction.md
            → Creator 读取执行
```

## 内化记录

| 日期 | 动作 | 说明 |
|------|------|------|
| 2026-02-28 | 首次内化 | 选取 5/6 技能，deferred competitor-analysis（先跑通再优化） |

## 迭代规则

- 公共库更新时：PM 评估是否同步到本目录
- 项目实践中发现新 pattern：PM 提炼后反馈到 shared/mkt/（上游贡献）
- 每月复盘：哪些框架有用、哪些没用，调整选用
