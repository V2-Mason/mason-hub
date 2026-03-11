"""
Fixed nodes.py — added response_modalities=["IMAGE"] to config.
Only the GeminiImageGenerationProNode execute method needs this patch.
"""
# This is the patched section of the execute method.
# The line `config.response_modalities = ["IMAGE"]` must appear after
# `config.image_config.image_size = image_size`
#
# Full sed command to apply:
# sed -i '/config.image_config.image_size = image_size/a\        config.response_modalities = ["IMAGE"]' nodes.py
