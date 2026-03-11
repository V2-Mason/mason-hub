#!/usr/bin/env python3
"""测试火山方舟：豆包视觉理解 + Seedance 视频生成"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ARK_API_KEY = os.getenv("VOLC_ARK_API_KEY")
VISION_EP = os.getenv("VOLC_VISION_ENDPOINT")  # ep-20260307071326-6sl2h
VIDEO_EP = os.getenv("VOLC_VIDEO_ENDPOINT")     # ep-20260307071638-dj6cp

try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    print("ERROR: pip install 'volcengine-python-sdk[ark]'")
    sys.exit(1)


def test_vision(client):
    """测试 1: 豆包视觉理解 — 看图说话"""
    print("=== 测试 1: 豆包视觉理解 (看图) ===")
    try:
        t0 = time.time()
        resp = client.chat.completions.create(
            model=VISION_EP,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这张图片里有什么？请用中文详细描述。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png"
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        elapsed = time.time() - t0
        print(f"  回复: {resp.choices[0].message.content}")
        print(f"  耗时: {elapsed:.1f}s")
        if hasattr(resp, 'model'):
            print(f"  模型: {resp.model}")
        if hasattr(resp, 'usage') and resp.usage:
            print(f"  Token: {resp.usage}")
        return True
    except Exception as e:
        print(f"  错误: {e}")
        return False


def test_vision_video_understanding(client):
    """测试 2: 豆包视觉理解 — 看视频写分镜（核心能力验证）"""
    print("\n=== 测试 2: 豆包视觉理解 (看视频写分镜) ===")
    # 用一个公开短视频测试
    try:
        t0 = time.time()
        resp = client.chat.completions.create(
            model=VISION_EP,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """请分析这个视频的结构，按以下格式输出分镜脚本：
1. 每个镜头的时间段
2. 画面描述（景别、构图、动作）
3. 文案/口播内容（如果有）
4. 转场方式

用JSON格式输出。""",
                        },
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
                            },
                        },
                    ],
                }
            ],
            max_tokens=800,
        )
        elapsed = time.time() - t0
        print(f"  回复: {resp.choices[0].message.content[:500]}")
        print(f"  耗时: {elapsed:.1f}s")
        if hasattr(resp, 'usage') and resp.usage:
            print(f"  Token: {resp.usage}")
        return True
    except Exception as e:
        print(f"  错误: {str(e)[:300]}")
        return False


def test_seedance_video(client):
    """测试 3: Seedance 视频生成"""
    print("\n=== 测试 3: Seedance 2.0 视频生成 ===")
    # Seedance 用的是异步任务 API，不是 chat.completions
    # 先试 chat 接口看报什么错，再调整
    try:
        # 方法 1: 尝试通过 content.generations 接口
        if hasattr(client, 'content') and hasattr(client.content, 'generations'):
            t0 = time.time()
            task = client.content.generations.create(
                model=VIDEO_EP,
                content=[{"type": "text", "text": "一瓶琥珀色精华液放在白色大理石台面上，柔和的自然光从左侧窗户洒入，产品缓缓旋转"}],
            )
            print(f"  任务创建成功: {task}")
            return True
    except Exception:
        pass

    # 方法 2: 尝试 chat.completions（可能报不支持）
    try:
        resp = client.chat.completions.create(
            model=VIDEO_EP,
            messages=[
                {"role": "user", "content": "一瓶琥珀色精华液放在白色大理石台面上，柔和的自然光从左侧窗户洒入，产品缓缓旋转"}
            ],
            max_tokens=100,
        )
        print(f"  回复: {resp.choices[0].message.content[:200]}")
        return True
    except Exception as e:
        err_str = str(e)
        print(f"  chat 接口错误: {err_str[:300]}")

    # 方法 3: 直接 HTTP 调用异步任务 API
    print("\n  尝试 HTTP 异步任务 API...")
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {ARK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": VIDEO_EP,
            "content": [
                {"type": "text", "text": "一瓶琥珀色精华液放在白色大理石台面上，柔和的自然光从左侧窗户洒入，产品缓缓旋转，画面风格为高级广告片质感"}
            ],
        }
        # 创建任务
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
            headers=headers,
            json=payload,
            timeout=30,
        )
        print(f"  HTTP 状态: {resp.status_code}")
        result = resp.json()
        print(f"  响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")

        if resp.status_code == 200 and "id" in result:
            task_id = result["id"]
            print(f"  任务 ID: {task_id}")
            # 轮询状态
            for i in range(5):
                time.sleep(10)
                status_resp = requests.get(
                    f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}",
                    headers=headers,
                    timeout=30,
                )
                status = status_resp.json()
                print(f"  [{i+1}] 状态: {json.dumps(status, ensure_ascii=False)[:200]}")
                if status.get("status") in ("succeeded", "failed"):
                    break
        return True
    except Exception as e:
        print(f"  HTTP 错误: {str(e)[:200]}")
        return False


def main():
    if not ARK_API_KEY:
        print("ERROR: VOLC_ARK_API_KEY not set")
        sys.exit(1)

    print(f"API Key: {ARK_API_KEY[:12]}...")
    print(f"Vision EP: {VISION_EP}")
    print(f"Video EP:  {VIDEO_EP}")

    os.environ["ARK_API_KEY"] = ARK_API_KEY
    client = Ark(api_key=ARK_API_KEY)

    # 测试视觉理解
    if VISION_EP:
        test_vision(client)
        test_vision_video_understanding(client)

    # 测试视频生成
    if VIDEO_EP:
        test_seedance_video(client)

    print("\n=== 全部测试完成 ===")


if __name__ == "__main__":
    main()
