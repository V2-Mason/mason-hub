# ComfyUI + Gemini 图片生成 (2026-03-07)

## GPU 实例
- 实例名：instance-20260307-184545，Zone: us-central1-a，IP: 136.114.202.32
- Docker 镜像：yanwk/comfyui-boot:cu128-slim，端口 8188
- 持久化卷：`~/comfyui-storage:/root`
- 输出目录：`~/comfyui-storage/ComfyUI/output/`

## 自定义节点 "Gemini Direct Pro"
- 位置：`~/comfyui-storage/ComfyUI/custom_nodes/comfyui-gemini-direct/`
- 备份：`mason-hub/skills/comfyui-gemini-direct/`
- 用自己的 Gemini API key 直接调 Google API

## Python 脚本
- `skills/gemini_image_gen.py`：text-to-image + 参考图编辑

## 安全教训
- NakanoSanku/ComfyUI-Gemini 插件内置第三方代理会泄露 API key
- **安装任何 ComfyUI 插件前必须检查源码有没有第三方代理**

## 待解决
- 自动化工作流集成方案（ComfyUI API / Python 脚本 / 混合）
- AutoClip 长视频切片待部署（等 Mason 做长视频内容时再上）
