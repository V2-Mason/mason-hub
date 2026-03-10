"""
Scout v2 — 共享 LLM 客户端

统一调用 DashScope (DeepSeek/Qwen) 和 Gemini，全部走 OpenAI 兼容接口。
内置 retry + exponential backoff + JSON 修复。
"""

import base64
import json
import logging
import mimetypes
import os
import re
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

_config_cache: dict | None = None


def load_config() -> dict:
    """加载 config.yaml，结果缓存。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)

    return _config_cache


def _load_env() -> None:
    """加载项目根目录 .env 文件。"""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


# 模块加载时自动读 .env
_load_env()

# ---------------------------------------------------------------------------
# 错误分类
# ---------------------------------------------------------------------------

_RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)

_NON_RETRYABLE_EXCEPTIONS = (
    AuthenticationError,
    BadRequestError,
)

# ---------------------------------------------------------------------------
# OpenAI 客户端池（按 model name 缓存）
# ---------------------------------------------------------------------------

_client_cache: dict[str, OpenAI] = {}


def _get_client(model_name: str = "default") -> tuple[OpenAI, dict]:
    """返回 (OpenAI client, model_config) 元组。"""
    cfg = load_config()
    models = cfg["llm"]["models"]

    if model_name not in models:
        raise ValueError(
            f"Unknown model '{model_name}'. Available: {list(models.keys())}"
        )

    mcfg = models[model_name]
    api_key_env = mcfg["api_key_env"]
    api_key = os.environ.get(api_key_env)

    if not api_key:
        logger.warning(
            "API key env '%s' not set for model '%s'. Calls will fail.",
            api_key_env,
            model_name,
        )
        api_key = "MISSING_KEY"

    cache_key = f"{model_name}:{api_key_env}"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = OpenAI(
            api_key=api_key,
            base_url=mcfg["base_url"],
            timeout=60.0,
        )

    return _client_cache[cache_key], mcfg


# ---------------------------------------------------------------------------
# JSON 修复
# ---------------------------------------------------------------------------


def _repair_json(text: str) -> dict:
    """尽力从 LLM 返回的文本中提取有效 JSON。

    常见问题：
    - 包裹在 ```json ... ``` 代码块中
    - 尾部多余逗号 (trailing comma)
    - 单引号代替双引号
    - 注释 (// ...)
    """
    # 1. 去掉 markdown 代码块
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1)

    # 2. 去掉行注释
    text = re.sub(r"//[^\n]*", "", text)

    # 3. 先尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. 去尾逗号 (}, ] 前面的逗号)
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # 5. 单引号 → 双引号（简单替换，不处理嵌套引号）
    try:
        return json.loads(text.replace("'", '"'))
    except json.JSONDecodeError:
        pass

    # 6. 尝试找第一个 { 或 [ 到最后一个 } 或 ]
    start = -1
    end = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    for i in range(len(text) - 1, -1, -1):
        if text[i] in "}]":
            end = i + 1
            break

    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(
        f"Failed to repair JSON from LLM response (first 200 chars): {text[:200]}",
        text,
        0,
    )


# ---------------------------------------------------------------------------
# 核心调用
# ---------------------------------------------------------------------------


def call_llm(
    prompt: str,
    model: str = "default",
    system: str | None = None,
    temperature: float | None = None,
) -> str:
    """调用 LLM 返回纯文本。内置 retry + exponential backoff。"""
    client, mcfg = _get_client(model)
    cfg = load_config()
    retry_cfg = cfg["llm"]["retry"]

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    temp = temperature if temperature is not None else mcfg.get("temperature", 0.3)

    last_exc: Exception | None = None
    for attempt in range(retry_cfg["max_retries"] + 1):
        try:
            resp = client.chat.completions.create(
                model=mcfg["model"],
                messages=messages,
                max_tokens=mcfg.get("max_tokens", 4096),
                temperature=temp,
            )
            return resp.choices[0].message.content or ""

        except _NON_RETRYABLE_EXCEPTIONS as e:
            logger.error("Non-retryable error calling %s: %s", model, e)
            raise

        except _RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            if attempt < retry_cfg["max_retries"]:
                delay = retry_cfg["retry_delay"] * (
                    retry_cfg["backoff_multiplier"] ** attempt
                )
                logger.warning(
                    "Retryable error calling %s (attempt %d/%d), retrying in %.1fs: %s",
                    model,
                    attempt + 1,
                    retry_cfg["max_retries"],
                    delay,
                    e,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "All %d retries exhausted for model %s: %s",
                    retry_cfg["max_retries"],
                    model,
                    e,
                )

    raise last_exc  # type: ignore[misc]


def call_llm_json(
    prompt: str,
    model: str = "default",
    system: str | None = None,
) -> dict:
    """调用 LLM 并解析返回的 JSON。自动修复常见格式问题。"""
    if system is None:
        system = "You are a helpful assistant. Always respond with valid JSON only, no markdown formatting."
    elif "json" not in system.lower():
        system += "\nIMPORTANT: Respond with valid JSON only."

    raw = call_llm(prompt, model=model, system=system, temperature=0.1)
    return _repair_json(raw)


def call_llm_with_images(
    prompt: str,
    image_paths: list[str],
    model: str = "gemini",
) -> str:
    """调用多模态 LLM（默认 Gemini）发送图片 + 文本。"""
    client, mcfg = _get_client(model)
    cfg = load_config()
    retry_cfg = cfg["llm"]["retry"]

    content_parts: list[dict] = []

    for img_path in image_paths:
        p = Path(img_path).expanduser().resolve()
        if not p.exists():
            logger.warning("Image not found, skipping: %s", p)
            continue
        mime_type = mimetypes.guess_type(str(p))[0] or "image/png"
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content_parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            }
        )

    content_parts.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": content_parts}]

    last_exc: Exception | None = None
    for attempt in range(retry_cfg["max_retries"] + 1):
        try:
            resp = client.chat.completions.create(
                model=mcfg["model"],
                messages=messages,
                max_tokens=mcfg.get("max_tokens", 4096),
                temperature=mcfg.get("temperature", 0.3),
            )
            return resp.choices[0].message.content or ""

        except _NON_RETRYABLE_EXCEPTIONS as e:
            logger.error("Non-retryable error calling %s: %s", model, e)
            raise

        except _RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            if attempt < retry_cfg["max_retries"]:
                delay = retry_cfg["retry_delay"] * (
                    retry_cfg["backoff_multiplier"] ** attempt
                )
                logger.warning(
                    "Retryable error calling %s with images (attempt %d/%d), "
                    "retrying in %.1fs: %s",
                    model,
                    attempt + 1,
                    retry_cfg["max_retries"],
                    delay,
                    e,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "All %d retries exhausted for model %s: %s",
                    retry_cfg["max_retries"],
                    model,
                    e,
                )

    raise last_exc  # type: ignore[misc]
