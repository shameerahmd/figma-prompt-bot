"""
Multi-provider LLM clients for the Figma AI Prompt Optimizer.
Supports NVIDIA NIM (primary), OpenAI, and Anthropic (fallbacks).
Each provider implements the same get_available_models() interface and
generate() signature so the engine can fail over transparently.
"""
import os
import time
import json
from typing import Dict, Any, List, Optional
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Provider priority order for automatic failover.
# "nvidia" uses the existing NvidiaNIMClient; openai/anthropic require their
# own API keys set as env vars or passed in per-request.
PROVIDER_PRIORITY = ["nvidia", "openai", "anthropic"]


class OpenAIProvider:
    """Minimal OpenAI-compatible client. Uses OPENAI_API_KEY env / per-request key."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    SUPPORTED_MODELS = [
        {"id": "gpt-4o-mini", "name": "GPT-4o mini (Fast)", "provider": "OpenAI", "context_length": 128000, "default": True},
        {"id": "gpt-4o", "name": "GPT-4o (High Quality)", "provider": "OpenAI", "context_length": 128000, "default": False},
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-"))

    def get_available_models(self):
        return self.SUPPORTED_MODELS

    def generate(self, system_prompt, user_prompt, model="gpt-4o-mini",
                 temperature=0.2, max_tokens=None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "error", "error_code": "AUTH_ERROR",
                    "message": "OpenAI API key not configured", "fallback": None}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens or 500
        }
        start = time.time()
        try:
            resp = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
            latency_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                return {
                    "status": "success",
                    "text": content,
                    "model": model,
                    "latency_ms": latency_ms,
                    "usage": {
                        "input": usage.get("prompt_tokens", 0),
                        "output": usage.get("completion_tokens", 0),
                        "total": usage.get("total_tokens", 0)
                    },
                    "mode": "openai_live"
                }
            return {"status": "error", "error_code": f"HTTP_{resp.status_code}",
                    "message": f"OpenAI API Error ({resp.status_code}): {resp.text[:200]}",
                    "fallback": None}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error_code": "NETWORK_UNAVAILABLE",
                    "message": f"Could not reach OpenAI endpoint: {str(e)}", "fallback": None}


class AnthropicProvider:
    """Minimal Anthropic client. Uses ANTHROPIC_API_KEY env / per-request key."""

    API_URL = "https://api.anthropic.com/v1/messages"

    SUPPORTED_MODELS = [
        {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku (Fast)", "provider": "Anthropic", "context_length": 200000, "default": True},
        {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet (High Quality)", "provider": "Anthropic", "context_length": 200000, "default": False},
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))

    def get_available_models(self):
        return self.SUPPORTED_MODELS

    def generate(self, system_prompt, user_prompt, model="claude-3-5-haiku-latest",
                 temperature=0.2, max_tokens=None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "error", "error_code": "AUTH_ERROR",
                    "message": "Anthropic API key not configured", "fallback": None}
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens or 500,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }
        start = time.time()
        try:
            resp = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
            latency_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                content = "".join(
                    block.get("text", "") for block in data.get("content", [])
                    if block.get("type") == "text"
                ).strip()
                usage = data.get("usage", {})
                return {
                    "status": "success",
                    "text": content,
                    "model": model,
                    "latency_ms": latency_ms,
                    "usage": {
                        "input": usage.get("input_tokens", 0),
                        "output": usage.get("output_tokens", 0),
                        "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    },
                    "mode": "anthropic_live"
                }
            return {"status": "error", "error_code": f"HTTP_{resp.status_code}",
                    "message": f"Anthropic API Error ({resp.status_code}): {resp.text[:200]}",
                    "fallback": None}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error_code": "NETWORK_UNAVAILABLE",
                    "message": f"Could not reach Anthropic endpoint: {str(e)}", "fallback": None}


def get_provider(provider_id: str, api_key: Optional[str] = None):
    """Factory returning the requested provider client."""
    if provider_id == "openai":
        return OpenAIProvider(api_key=api_key)
    if provider_id == "anthropic":
        return AnthropicProvider(api_key=api_key)
    return None  # nvidia handled by NvidiaNIMClient
