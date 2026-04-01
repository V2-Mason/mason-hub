"""
直接调用可灵 API 生成视频（独立脚本，不依赖 ComfyUI）
用法: python scripts/kling_generate.py
"""
import os
import json
import time
import hashlib
import hmac
import base64
import urllib.request
import urllib.error
from pathlib import Path

# 从 .env 读取
def load_env(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

AK = os.getenv("KLING_ACCESS_KEY", "")
SK = os.getenv("KLING_SECRET_KEY", "")
BASE_URL = "https://api.klingai.com"

if not AK or not SK:
    raise ValueError("请在 .env 中配置 KLING_ACCESS_KEY 和 KLING_SECRET_KEY")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate_jwt(access_key: str, secret_key: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "iss": access_key,
        "iat": now - 5,
        "exp": now + 1800,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = b64url(hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def api_request(url, token, data=None, method="POST"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        raise RuntimeError(f"Kling API error {e.code}: {error_body}")


def create_text2video(prompt, model="kling-v3-omni", duration="5",
                       aspect_ratio="9:16", mode="std", negative_prompt="blur, distort, low quality"):
    token = generate_jwt(AK, SK)
    body = {
        "model_name": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "mode": mode,
    }
    result = api_request(f"{BASE_URL}/v1/videos/text2video", token, body)
    task_id = result.get("data", {}).get("task_id")
    print(f"任务已提交: task_id={task_id}")
    return task_id


def poll_task(task_id, timeout=600):
    token = generate_jwt(AK, SK)
    url = f"{BASE_URL}/v1/videos/text2video/{task_id}"
    start = time.time()
    while time.time() - start < timeout:
        result = api_request(url, token, method="GET")
        data = result.get("data", {})
        status = data.get("task_status", "")
        print(f"  状态: {status} ({int(time.time()-start)}s)")
        if status == "succeed":
            videos = data.get("task_result", {}).get("videos", [])
            if videos:
                return videos[0].get("url")
            return None
        elif status == "failed":
            msg = data.get("task_status_msg", "Unknown error")
            raise RuntimeError(f"任务失败: {msg}")
        time.sleep(10)
    raise RuntimeError(f"超时 ({timeout}s)")


def download_video(url, output_path):
    print(f"下载中: {output_path}")
    urllib.request.urlretrieve(url, output_path)
    print(f"完成: {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.1f}MB)")


# === ANUA 产品视频 Prompts ===

ANUA_PROMPTS = [
    {
        "name": "anua-toner",
        "prompt": (
            "Product promo video, vertical 9:16 format, Instagram Stories style. "
            "A sleek transparent bottle of green-tinted toner with minimalist Korean label, "
            "rotating slowly on a clean white surface. Soft green botanical leaves falling gently in background. "
            "Text overlay appears with smooth animation: 'ANUA Heartleaf 77% Soothing Toner'. "
            "Price tag slides in: '$18'. Clean, minimal, premium K-beauty aesthetic. "
            "Soft natural lighting, shallow depth of field."
        ),
    },
    {
        "name": "anua-ampoule",
        "prompt": (
            "Product promo video, vertical 9:16 format, Instagram Stories style. "
            "A small frosted green glass dropper bottle on a marble surface, "
            "golden serum droplet falling from the dropper in slow motion. "
            "Soft bokeh lights in warm tones behind. "
            "Text overlay: 'ANUA Heartleaf 80% Soothing Ampoule'. "
            "Subtitle: 'Repair · Soothe · Strengthen'. "
            "Premium skincare commercial feel, elegant and calming."
        ),
    },
    {
        "name": "anua-serum",
        "prompt": (
            "Product promo video, vertical 9:16 format, Instagram Stories style. "
            "A minimalist white dropper bottle with clean label, "
            "camera slowly pushing in with cinematic motion. "
            "Soft particles of light floating around the product. "
            "Text overlay with smooth fade-in: 'Niacinamide 10% + TXA 4%'. "
            "Subtitle: 'Dark Spot Correcting Serum'. Price: '$24'. "
            "Clean studio lighting, pure white background, high-end beauty brand feel."
        ),
    },
]

if __name__ == "__main__":
    output_dir = Path("accounts/surenxuan/content/anua-promo")
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in ANUA_PROMPTS:
        print(f"\n{'='*50}")
        print(f"生成: {item['name']}")
        print(f"{'='*50}")

        task_id = create_text2video(
            prompt=item["prompt"],
            aspect_ratio="9:16",
            duration="5",
            mode="std",
        )

        video_url = poll_task(task_id)
        if video_url:
            download_video(video_url, str(output_dir / f"{item['name']}.mp4"))
        else:
            print(f"警告: {item['name']} 没有返回视频URL")

    print(f"\n全部完成! 视频保存在 {output_dir}/")
