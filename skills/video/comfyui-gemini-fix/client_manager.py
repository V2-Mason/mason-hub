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
            "1. Provide API key in the node's 'api_key' input, or\n"
            "2. Set GEMINI_API_KEY environment variable, or\n"
            "3. Set GOOGLE_API_KEY environment variable\n\n"
            "Get your API key at: https://aistudio.google.com/apikey"
        )
    return api_key


def create_client(api_key: str | None = None) -> genai.Client:
    resolved_key = get_api_key(api_key)
    return genai.Client(api_key=resolved_key)
