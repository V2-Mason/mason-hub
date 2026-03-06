# Editing Intelligence — Styles 目录说明

> 维护者：EMP_0008 (SocialMesh PM) + EMP_0009 (Content-Tech Dev)
> 创建日期：2026-03-06
> 状态：v1 — 从现有代码整理的第一版

## 目录结构

```
styles/
  00-README.md          ← 本文件
  小红书.md             ← 渠道剪辑规则（每平台一个）
  抖音.md
  视频号.md
  快手.md
  公众号.md
  微信私域.md
  产品聚焦.md
  00-通用规则.md         ← 跨渠道通用：转场、音画对齐、自更新日志格式
```

品牌特定覆盖文件（不在本目录，在品牌目录下）：
```
shared/brands/surenxuan/editing_overrides.md  ← 素仁轩专属：语气词典、品牌色、禁用词
```

## 设计原则

### 三源归一

本目录是视频生产线剪辑规则的 **Single Source of Truth**。
以前规则分散在三个地方，现在统一到这里：

| 原始位置 | 内容 | 现在在哪 |
|---------|------|---------|
| `multicut.py` CHANNEL_GUIDES | Gemini prompt 用的风格叙述 | 每个渠道 .md 的正文部分 |
| `channel_profiles.json` | FFmpeg 渲染硬参数 | 每个渠道 .md 顶部 YAML frontmatter |
| `voiceover_writer.py` VOICE_STYLES | TTS 旁白风格一句话描述 | 每个渠道 .md「口播/旁白风格」章节 |

### 数据流（当前 v1）

v1 阶段，styles/*.md 是**参考文档**，代码仍从原位置读取参数。
v2 阶段将实现自动构建：

```
styles/*.md (YAML frontmatter)
  └──→ build_profiles.py
        ├──→ channel_profiles.json    (assemble.py 消费)
        └──→ channel_guides.json      (multicut.py 消费)
```

### 文件格式约定

每个渠道 .md 文件结构：

```markdown
---
# YAML frontmatter — 可解析的 FFmpeg 参数
channel_id: 小红书
color: { saturation: 0.85, contrast: 0.95, brightness: 0.05 }
text: { font_size_scale: 1.0, ... }
audio: { volume_scale: 1.0, mute_original: false }
layout: { letterbox: false }
voice_style: "闺蜜聊天式、温柔自然..."
---
# 渠道名 — 剪辑规则

## 参数来源对照
（标注每个参数对应代码中的哪个位置）

## 受众画像
## 画面节奏
## 花字/字幕设计
## 声音处理
## 转场
## 内容结构
## Do / Don't 示例
```

### 品牌覆盖机制

渠道规则是**平台通用**的（任何品牌都适用）。
品牌特定内容（如素仁轩的"姐妹"称呼、品牌色 #D4A853）放在品牌目录下的 `editing_overrides.md`。

应用优先级：`品牌覆盖 > 渠道规则 > 全局默认`

## 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-03-06 | v1 | 从 multicut.py / channel_profiles.json / voiceover_writer.py 整理初版 |
