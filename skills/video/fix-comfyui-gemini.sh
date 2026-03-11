#!/bin/bash
# Fix ComfyUI-Gemini plugin on GPU instance
# Run on the GPU instance (not inside Docker)
# Usage: bash fix-comfyui-gemini.sh

set -e

CONTAINER=$(sudo docker ps -q | head -1)
if [ -z "$CONTAINER" ]; then
    echo "ERROR: No running Docker container found"
    exit 1
fi
echo "Container: $CONTAINER"

# Step 1: Re-install plugin (in case restart wiped it)
echo "=== Installing NakanoSanku/ComfyUI-Gemini ==="
sudo docker exec "$CONTAINER" bash -c '
cd /root/ComfyUI/custom_nodes
if [ -d ComfyUI-Gemini ]; then
    echo "Plugin dir exists, removing broken copy..."
    rm -rf ComfyUI-Gemini
fi
git clone https://github.com/NakanoSanku/ComfyUI-Gemini.git
cd ComfyUI-Gemini
pip install -r requirements.txt
echo "Plugin installed OK"
'

# Step 2: Fix the proxy bug in client_manager.py
echo "=== Fixing client_manager.py (removing third-party proxy) ==="
sudo docker exec "$CONTAINER" bash -c 'cat > /root/ComfyUI/custom_nodes/ComfyUI-Gemini/helpers/client_manager.py << '"'"'HEREDOC'"'"'
"""
Client creation and API key management for Google Gemini API.
"""
import os

from google import genai


def get_api_key(node_api_key: str | None = None) -> str:
    if node_api_key and node_api_key.strip():
        return node_api_key.strip()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "No Gemini API key found. Please either:\n"
            "1. Provide API key in the node input, or\n"
            "2. Set GEMINI_API_KEY environment variable, or\n"
            "3. Set GOOGLE_API_KEY environment variable\n\n"
            "Get your API key at: https://aistudio.google.com/apikey"
        )
    return api_key


def create_client(api_key: str | None = None) -> genai.Client:
    resolved_key = get_api_key(api_key)
    return genai.Client(api_key=resolved_key)
HEREDOC'

# Step 3: Fix missing response_modalities in nodes.py
echo "=== Fixing nodes.py (adding response_modalities) ==="
sudo docker exec "$CONTAINER" python3 -c "
import re
path = '/root/ComfyUI/custom_nodes/ComfyUI-Gemini/nodes.py'
with open(path) as f:
    content = f.read()

# Add response_modalities after image_size line
target = 'config.image_config.image_size = image_size'
if 'config.response_modalities' not in content:
    content = content.replace(
        target,
        target + '\n            config.response_modalities = [\"IMAGE\"]'
    )
    with open(path, 'w') as f:
        f.write(content)
    print('Added response_modalities to config')
else:
    print('response_modalities already present')

# Verify syntax
import py_compile
py_compile.compile(path, doraise=True)
print('Syntax check passed')
"

# Step 4: Restart ComfyUI
echo "=== Restarting ComfyUI ==="
sudo docker restart "$CONTAINER"
echo "Done! Wait ~20s then check http://[IP]:8188"
