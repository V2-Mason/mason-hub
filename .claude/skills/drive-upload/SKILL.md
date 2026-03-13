---
name: drive-upload
description: >
  上传文件到 Google Drive，自动检测 MIME 类型，支持指定目标文件夹。
  触发词：上传到 Drive、传文件到 Google Drive、备份到 Drive
user_invocable: true
---

# /drive-upload — Google Drive 文件上传

> **前提**：需要 Google OAuth 认证。首次使用会引导认证流程。
> **CAUTION**：这是写操作——执行前必须确认文件和目标。

## 用法

```
/drive-upload <file_path> [--folder FOLDER_ID] [--name "目标文件名"]
```

## 参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `<file_path>` | ✓ | — | 本地文件路径 |
| `--folder` | — | Drive 根目录 | 目标文件夹 ID |
| `--name` | — | 源文件名 | 上传后的文件名 |

## 示例

```
/drive-upload ./data/reports/2026-03-13/daily.json
/drive-upload ./intel/reports/2026-03-12.md --folder 1x34nuR2nvT-gJHDQQaHxiOMhKrc0fPLW
/drive-upload ./export.csv --name "素仁轩销售数据.csv"
```

## 执行流程

### Step 1. 确认上传

向用户确认：
```
📤 准备上传：
  文件：{file_path} ({size})
  目标：{folder_name or "Drive 根目录"}
  文件名：{target_name}
  MIME：{auto_detected_mime}
确认上传？
```

### Step 2. 执行上传

```bash
~/mason-hub/.venv/bin/python3 ~/mason-hub/skills/drive-upload.py \
  "{file_path}" \
  --folder "{folder_id}" \
  --name "{target_name}"
```

### Step 3. 报告结果

```
✅ 上传成功
  文件 ID：{file_id}
  链接：https://drive.google.com/file/d/{file_id}/view
  大小：{size}
```

## 认证

首次使用需要 OAuth：
1. 检查 `~/.config/gcloud/` 或 `~/mason-hub/credentials/` 是否有 token
2. 没有 → 引导用户执行 `~/mason-hub/.venv/bin/python3 skills/drive-upload.py --auth`
3. 完成后 token 保存到本地，后续自动使用

## 注意事项

- MIME 类型自动检测（基于文件扩展名）
- 同名文件不会覆盖，Drive 会创建新版本
- 大文件（>5MB）使用 resumable upload
- **不上传敏感文件**（.env, credentials.json, API keys）
