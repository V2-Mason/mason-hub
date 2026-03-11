"""
Kling Direct API nodes for ComfyUI — text-to-video and image-to-video
using your own Kling API key (access_key + secret_key).

Supports models: kling-v3-omni, kling-v2-5-turbo, and others.

Usage: Copy this entire folder into ComfyUI/custom_nodes/ and restart.
No extra pip dependencies required (uses stdlib only).
"""
import os
import json
import time
import hashlib
import hmac
import base64
import struct
import urllib.request
import urllib.error
import tempfile
from io import BytesIO

import torch
import numpy as np
from PIL import Image


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _generate_jwt(access_key: str, secret_key: str) -> str:
    """Generate JWT token for Kling API authentication (HS256, no dependencies)."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url(json.dumps({
        "iss": access_key,
        "iat": now - 5,
        "exp": now + 1800,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = _b64url(hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def _api_request(url: str, token: str, data: dict = None, method: str = "POST"):
    """Make an API request to Kling API."""
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


def _image_to_data_url(pil_img: Image.Image) -> str:
    """Convert PIL Image to base64 data URL."""
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _poll_task(base_url: str, task_id: str, token: str, timeout: int = 600) -> dict:
    """Poll task status until completion or timeout."""
    url = f"{base_url}/v1/videos/text2video/{task_id}"
    start = time.time()
    while time.time() - start < timeout:
        result = _api_request(url, token, method="GET")
        data = result.get("data", {})
        status = data.get("task_status", "")
        if status == "succeed":
            return data
        elif status == "failed":
            msg = data.get("task_status_msg", "Unknown error")
            raise RuntimeError(f"Kling task failed: {msg}")
        time.sleep(5)
    raise RuntimeError(f"Kling task timed out after {timeout}s (task_id: {task_id})")


def _download_video_frames(video_url: str) -> torch.Tensor:
    """Download video and extract frames as image tensor batch."""
    req = urllib.request.Request(video_url)
    with urllib.request.urlopen(req, timeout=120) as resp:
        video_data = resp.read()

    # Save to temp file for frame extraction
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_data)
        temp_path = f.name

    try:
        # Try using cv2 if available
        import cv2
        cap = cv2.VideoCapture(temp_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # cv2 reads BGR, convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_np = frame_rgb.astype(np.float32) / 255.0
            frames.append(frame_np)
        cap.release()

        if not frames:
            raise RuntimeError("No frames extracted from video")

        return torch.from_numpy(np.stack(frames))
    except ImportError:
        # Fallback: return first frame via PIL (for formats PIL can handle)
        raise RuntimeError(
            "opencv-python (cv2) is required to extract video frames. "
            "Install it in the container: pip install opencv-python-headless"
        )
    finally:
        os.unlink(temp_path)


BASE_URL = "https://api.klingai.com"

MODELS = [
    "kling-v3-omni",
    "kling-v2-5-turbo",
    "kling-v2-6",
    "kling-v2-1",
    "kling-v1-6",
]


class KlingTextToVideo:
    """Generate video from text prompt using Kling API."""

    VALIDATE_INPUTS = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "access_key": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"default": ""}),
                "model": (MODELS, {"default": "kling-v3-omni"}),
                "duration": (["5", "10"], {"default": "5"}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3", "21:9"], {"default": "16:9"}),
                "mode": (["std", "pro"], {"default": "std"}),
            },
            "optional": {
                "negative_prompt": ("STRING", {"multiline": True, "default": "blur, distort, low quality"}),
                "cfg_scale": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "timeout": ("INT", {"default": 600, "min": 60, "max": 1800}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("frames", "video_url")
    FUNCTION = "generate"
    CATEGORY = "kling"

    def generate(self, prompt, access_key, secret_key, model, duration, aspect_ratio,
                 mode, negative_prompt="blur, distort, low quality", cfg_scale=0.5,
                 seed=-1, timeout=600):
        ak = access_key.strip() or os.getenv("KLING_ACCESS_KEY", "")
        sk = secret_key.strip() or os.getenv("KLING_SECRET_KEY", "")
        if not ak or not sk:
            raise ValueError("No Kling credentials. Fill in access_key/secret_key or set KLING_ACCESS_KEY/KLING_SECRET_KEY env vars.")

        token = _generate_jwt(ak, sk)

        body = {
            "model_name": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "mode": mode,
            "cfg_scale": cfg_scale,
        }
        if negative_prompt and negative_prompt.strip():
            body["negative_prompt"] = negative_prompt.strip()
        if seed >= 0:
            body["seed"] = seed

        # Submit task
        result = _api_request(f"{BASE_URL}/v1/videos/text2video", token, body)
        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Failed to create task: {json.dumps(result)}")

        print(f"[Kling] Task submitted: {task_id}, polling...")

        # Poll for completion
        completed = _poll_task(BASE_URL, task_id, token, timeout)

        # Get video URL
        videos = completed.get("task_result", {}).get("videos", [])
        if not videos:
            raise RuntimeError("Kling returned no video")
        video_url = videos[0].get("url", "")

        # Download and extract frames
        frames = _download_video_frames(video_url)

        return (frames, video_url)


class KlingImageToVideo:
    """Generate video from image + prompt using Kling API."""

    VALIDATE_INPUTS = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "access_key": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"default": ""}),
                "model": (MODELS, {"default": "kling-v3-omni"}),
                "duration": (["5", "10"], {"default": "5"}),
                "mode": (["std", "pro"], {"default": "std"}),
            },
            "optional": {
                "negative_prompt": ("STRING", {"multiline": True, "default": "blur, distort, low quality"}),
                "cfg_scale": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "tail_image": ("IMAGE",),
                "timeout": ("INT", {"default": 600, "min": 60, "max": 1800}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("frames", "video_url")
    FUNCTION = "generate"
    CATEGORY = "kling"

    def generate(self, image, prompt, access_key, secret_key, model, duration, mode,
                 negative_prompt="blur, distort, low quality", cfg_scale=0.5,
                 seed=-1, tail_image=None, timeout=600):
        ak = access_key.strip() or os.getenv("KLING_ACCESS_KEY", "")
        sk = secret_key.strip() or os.getenv("KLING_SECRET_KEY", "")
        if not ak or not sk:
            raise ValueError("No Kling credentials. Fill in access_key/secret_key or set KLING_ACCESS_KEY/KLING_SECRET_KEY env vars.")

        token = _generate_jwt(ak, sk)

        # Convert input image to base64
        img_np = (image[0].cpu().numpy() * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_np, mode="RGB")
        image_data = _image_to_data_url(pil_img)

        body = {
            "model_name": model,
            "prompt": prompt,
            "image": image_data,
            "duration": duration,
            "mode": mode,
            "cfg_scale": cfg_scale,
        }
        if negative_prompt and negative_prompt.strip():
            body["negative_prompt"] = negative_prompt.strip()
        if seed >= 0:
            body["seed"] = seed
        if tail_image is not None:
            tail_np = (tail_image[0].cpu().numpy() * 255).astype(np.uint8)
            tail_pil = Image.fromarray(tail_np, mode="RGB")
            body["image_tail"] = _image_to_data_url(tail_pil)

        # Submit task
        result = _api_request(f"{BASE_URL}/v1/videos/image2video", token, body)
        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Failed to create task: {json.dumps(result)}")

        print(f"[Kling] I2V Task submitted: {task_id}, polling...")

        # Poll — image2video uses same task query endpoint
        url = f"{BASE_URL}/v1/videos/image2video/{task_id}"
        start = time.time()
        while time.time() - start < timeout:
            r = _api_request(url, token, method="GET")
            data = r.get("data", {})
            status = data.get("task_status", "")
            if status == "succeed":
                videos = data.get("task_result", {}).get("videos", [])
                if not videos:
                    raise RuntimeError("Kling returned no video")
                video_url = videos[0].get("url", "")
                frames = _download_video_frames(video_url)
                return (frames, video_url)
            elif status == "failed":
                raise RuntimeError(f"Kling task failed: {data.get('task_status_msg', 'Unknown')}")
            time.sleep(5)

        raise RuntimeError(f"Kling I2V task timed out after {timeout}s")


NODE_CLASS_MAPPINGS = {
    "KlingTextToVideo": KlingTextToVideo,
    "KlingImageToVideo": KlingImageToVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KlingTextToVideo": "Kling Text to Video (Own API Key)",
    "KlingImageToVideo": "Kling Image to Video (Own API Key)",
}
