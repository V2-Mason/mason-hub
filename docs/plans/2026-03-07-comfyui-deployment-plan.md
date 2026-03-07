# ComfyUI GPU 部署方案 — 视频复刻管线图片生成

日期: 2026-03-07
状态: 待 Mason 确认

## 背景

Nano Banana Pro（Gemini 图片生成）一步法换人换品效果差：构图偏移、背景重新生成、人物不一致。
需要更精确的图片控制能力：背景像素级保留 + ControlNet 约束姿势 + IP-Adapter 保持人物一致性。

## 架构总览

```
GCP 现有主机 (34.63.188.198)          GCP GPU 实例 (新建)
┌─────────────────────┐              ┌─────────────────────┐
│  mason-hub          │              │  ComfyUI Server     │
│  socialmesh         │   HTTP API   │                     │
│  replicate.py ──────│─────────────→│  :8188/api          │
│                     │   内网通信    │                     │
│  Gemini 分析        │              │  GPU: T4 (16GB)     │
│  Seedance 视频生成   │              │  模型: SD + CN + IP │
│  ffmpeg 拼接        │              │  按需启停           │
└─────────────────────┘              └─────────────────────┘
```

replicate.py 只改 Step 2：Nano Banana → ComfyUI API 调用。其余步骤不变。

## GPU 实例选型

### 推荐: T4 Spot 实例

| 配置项 | 值 |
|--------|-----|
| 机型 | n1-standard-4 + 1x NVIDIA T4 |
| GPU 显存 | 16GB (跑 SDXL + ControlNet + IP-Adapter 够用) |
| 内存 | 15GB |
| 磁盘 | 100GB SSD (系统 + 模型 + ComfyUI) |
| 区域 | europe-west4 (跟主机同区，内网通信) |
| 类型 | Spot (抢占式) |
| 成本 | ~$0.11/hr (Spot), 按需 ~$0.35/hr |
| 使用模式 | 用时开机，跑完关机。月均 <10 小时 = <$1.10/月 |

### 备选: L4 (如果 T4 不够)

| 配置项 | 值 |
|--------|-----|
| 机型 | g2-standard-4 + 1x NVIDIA L4 |
| GPU 显存 | 24GB (可跑更大模型) |
| 成本 | ~$0.24/hr (Spot) |

### 为什么不用 A100/V100

- A100: $1.5+/hr，杀鸡用牛刀。单张图推理 T4 几秒搞定
- V100: 老架构，Spot 价格不比 T4 便宜

## ComfyUI 工作流设计

### 换人换品工作流（核心）

```
输入:
  - 原始关键帧 (keyframe_001.png)
  - 人物参考照 (model_photo.png)
  - 产品参考照 (product_photo.png)

节点图:

  原始帧 ──→ ControlNet-OpenPose ──→ 姿势骨架
         ──→ ControlNet-Depth ─────→ 深度图
         ──→ SAM2 分割 ───────────→ 人物 mask + 产品 mask

  人物参考照 ──→ IP-Adapter-FaceID ──→ 面部特征

  产品参考照 ──→ IP-Adapter ─────────→ 产品外观特征

  组合:
    原始帧 (背景不动)
    + 人物 mask 区域: Inpaint (SD/Flux) + ControlNet-Pose 约束 + IP-Adapter-Face 约束
    + 产品 mask 区域: Inpaint (SD/Flux) + IP-Adapter 约束

输出:
  - swap_001.png (背景不变, 人物/产品已替换)
```

### 关键 ControlNet 模型

| 模型 | 作用 | 大小 |
|------|------|------|
| control_v11p_sd15_openpose | 姿势骨架约束 | ~1.4GB |
| control_v11f1p_sd15_depth | 深度空间约束 | ~1.4GB |
| ip-adapter-faceid-plusv2_sd15 | 面部一致性 | ~100MB |
| ip-adapter-plus_sd15 | 整体风格/外观参考 | ~100MB |
| SAM2 (segment-anything-2) | 自动分割人物/产品 | ~2.5GB |

### 基础模型选择

| 选项 | 优势 | 劣势 |
|------|------|------|
| SD 1.5 + 真实感 checkpoint (如 RealisticVision) | ControlNet 生态最成熟，T4 够跑 | 分辨率 512x768 需要后期放大 |
| SDXL | 分辨率 1024x，画质更好 | ControlNet 选择少一些，T4 刚好够 |
| Flux.1 Dev | 最新最强 | ControlNet 生态还在发展，T4 可能吃力 |

**推荐: SD 1.5 + RealisticVision v5.1** — ControlNet 工具链最完整，T4 16GB 轻松跑，社区换人换品工作流最多。

## 部署步骤

### Phase 1: 基础设施 (~30 min)

```bash
# 1. 创建 GPU 实例
gcloud compute instances create comfyui-gpu \
  --zone=europe-west4-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --provisioning-model=SPOT \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --metadata="install-nvidia-driver=True"

# 2. 防火墙规则（只允许主机内网访问 8188）
gcloud compute firewall-rules create allow-comfyui-internal \
  --allow=tcp:8188 \
  --source-ranges=10.0.0.0/8 \
  --target-tags=comfyui-gpu
```

### Phase 2: ComfyUI 安装 (~20 min)

```bash
# SSH 进入 GPU 实例
gcloud compute ssh comfyui-gpu --zone=europe-west4-a

# 安装 ComfyUI
cd /opt
git clone https://github.com/Comfy-Org/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# 安装自定义节点
cd custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
git clone https://github.com/storyicon/comfyui_segment_anything.git
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
pip install -r ComfyUI_IPAdapter_plus/requirements.txt
pip install -r comfyui_controlnet_aux/requirements.txt
pip install -r comfyui_segment_anything/requirements.txt
```

### Phase 3: 模型下载 (~15 min)

```bash
cd /opt/ComfyUI/models

# 基础模型
wget -P checkpoints/ "https://huggingface.co/SG161222/Realistic_Vision_V5.1_noVAE/resolve/main/Realistic_Vision_V5.1_fp16-no-ema.safetensors"

# VAE
wget -P vae/ "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors"

# ControlNet
wget -P controlnet/ "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_openpose.pth"
wget -P controlnet/ "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11f1p_sd15_depth.pth"

# IP-Adapter
mkdir -p ipadapter
wget -P ipadapter/ "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sd15.bin"
wget -P ipadapter/ "https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus_sd15.safetensors"

# CLIP Vision (IP-Adapter 依赖)
wget -P clip_vision/ "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"

# SAM2
mkdir -p sam
wget -P sam/ "https://huggingface.co/facebook/sam2-hiera-large/resolve/main/sam2_hiera_large.pt"
```

### Phase 4: 启动 + API 验证

```bash
# 启动 ComfyUI（headless API 模式，监听所有接口）
cd /opt/ComfyUI
python main.py --listen 0.0.0.0 --port 8188 &

# 从主机测试连接
# (在主机 34.63.188.198 上执行)
curl http://<comfyui-internal-ip>:8188/system_stats
```

### Phase 5: 工作流 JSON + replicate.py 集成

在主机上保存工作流 JSON，replicate.py 通过 HTTP API 提交任务：

```python
# replicate.py 新增 ComfyUI 后端
def generate_swap_image_comfyui(keyframe_path, person_ref, product_ref, output_path):
    """通过 ComfyUI API 换人换品。"""
    workflow = load_workflow('swap_person_product.json')

    # 注入输入图片
    workflow['nodes']['load_keyframe']['inputs']['image'] = upload_image(keyframe_path)
    workflow['nodes']['load_person_ref']['inputs']['image'] = upload_image(person_ref)
    workflow['nodes']['load_product_ref']['inputs']['image'] = upload_image(product_ref)

    # 提交并等待
    result = submit_workflow(workflow)
    download_output(result, output_path)
```

## 启停管理

ComfyUI GPU 实例不需要 24 小时运行。

```bash
# 开机（replicate.py 自动调用）
gcloud compute instances start comfyui-gpu --zone=europe-west4-a

# 关机（任务完成后自动调用）
gcloud compute instances stop comfyui-gpu --zone=europe-west4-a
```

replicate.py 在 Step 2 开始前自动开机，Step 2 完成后自动关机。
开机到就绪约 60-90 秒（模型加载）。

## 成本估算

| 场景 | 时间 | 成本 |
|------|------|------|
| 单次复刻测试 (8 张图) | ~5 min GPU 时间 | ~$0.01 (Spot) |
| 一条完整视频复刻 (20 张图) | ~15 min | ~$0.03 |
| 每周 5 条视频 | ~75 min/周 | ~$0.55/月 |
| 磁盘 (100GB SSD 常驻) | 24/7 | ~$17/月 |

**总月成本: ~$18/月**（主要是磁盘，GPU 按需几乎可忽略）

### 省钱选项
- 磁盘用 pd-balanced (非 SSD): ~$10/月
- 模型存 GCS bucket，开机时挂载: 磁盘可缩到 30GB = ~$5/月
- 用 preemptible 而非 spot: 价格类似但有 24h 上限

## 里程碑

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| M1 | 创建 GPU 实例 + 装 ComfyUI + 下载模型 | 1 小时 |
| M2 | 搭建换人换品工作流（ComfyUI 界面调试） | 2-3 小时 |
| M3 | 导出工作流 JSON + replicate.py 集成 | 1-2 小时 |
| M4 | 用面膜视频端到端测试 | 30 分钟 |
| M5 | 启停自动化 + 成本监控 | 30 分钟 |

**总计: 约半天可以跑通。**

## 风险

1. **T4 显存不够** — SD 1.5 + ControlNet + IP-Adapter 峰值约 10-12GB，T4 16GB 够用。如果加 SAM2 同时跑可能紧张，可分两步执行（先分割，再生成）
2. **Spot 实例被抢占** — 任务跑到一半被 kill。解决：checkpoint 机制（replicate.py 已有）
3. **模型版本兼容** — ControlNet/IP-Adapter 版本需匹配基础模型。锁定具体版本号
4. **ComfyUI 更新** — 锁 git commit，不自动更新

## 决策点（需 Mason 确认）

1. **GPU 型号**: T4 ($0.11/hr) 还是 L4 ($0.24/hr)？推荐 T4 先试
2. **基础模型**: SD 1.5 (成熟) 还是 SDXL (画质好)？推荐 SD 1.5 先跑通
3. **区域**: europe-west4 (跟主机同区) 还是 us-central1 (GPU 库存多)？
4. **是否现在部署**: 确认后我可以直接执行 Phase 1-4
