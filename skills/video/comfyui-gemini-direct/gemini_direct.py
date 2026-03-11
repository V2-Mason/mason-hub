"""
Gemini Direct API node for ComfyUI — drop-in replacement for Nano Banana Pro template nodes.
Single file, no extra dependencies beyond google-genai (already installed with ComfyUI).

Usage: Copy this entire folder into ComfyUI/custom_nodes/ and restart.
"""
import os
import torch
import numpy as np
from io import BytesIO
from PIL import Image

from google import genai
from google.genai import types


class GeminiDirectPro:
    """Drop-in replacement for Nano Banana Pro that uses your own Gemini API key."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "model": (["gemini-3-pro-image-preview"],),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**63 - 1}),
                "aspect_ratio": (["auto", "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"], {"default": "1:1"}),
                "resolution": (["1K", "2K", "4K"], {"default": "2K"}),
                "response_modalities": (["IMAGE", "IMAGE+TEXT"], {"default": "IMAGE"}),
            },
            "optional": {
                "images": ("IMAGE",),
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "gemini"

    def generate(self, prompt, api_key, model, seed, aspect_ratio, resolution,
                 response_modalities, images=None, system_prompt=""):
        # Resolve API key
        key = api_key.strip() if api_key.strip() else os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("No API key. Fill in api_key or set GEMINI_API_KEY env var.")

        client = genai.Client(api_key=key)

        # Build contents
        contents = []
        if images is not None:
            batch_size = images.shape[0]
            for i in range(min(batch_size, 14)):
                img_np = (images[i].cpu().numpy() * 255).astype(np.uint8)
                pil_img = Image.fromarray(img_np, mode="RGB")
                buf = BytesIO()
                pil_img.save(buf, format="PNG")
                contents.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"))
        contents.append(prompt)

        # Build config
        modalities = ["IMAGE"] if response_modalities == "IMAGE" else ["IMAGE", "TEXT"]
        config = types.GenerateContentConfig(
            response_modalities=modalities,
            image_config=types.ImageConfig(image_size=resolution.lower()),
            seed=seed,
        )
        if aspect_ratio != "auto":
            config.image_config.aspect_ratio = aspect_ratio
        if system_prompt and system_prompt.strip():
            config.system_instruction = system_prompt.strip()

        # Call API
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        # Extract image
        if not response.candidates:
            raise RuntimeError("No response from Gemini API")

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type and "image" in part.inline_data.mime_type:
                data = part.inline_data.data
                if isinstance(data, str):
                    import base64
                    data = base64.b64decode(data)
                pil_img = Image.open(BytesIO(data)).convert("RGB")
                img_np = np.array(pil_img).astype(np.float32) / 255.0
                tensor = torch.from_numpy(img_np).unsqueeze(0)
                return (tensor,)

        raise RuntimeError("Gemini returned no image. Try a different prompt.")


NODE_CLASS_MAPPINGS = {
    "GeminiDirectPro": GeminiDirectPro,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiDirectPro": "Gemini Direct Pro (Own API Key)",
}
