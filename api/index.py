"""
Vercel Serverless Function Entry Point for Figma AI Prompt Optimizer.
Handles all API routes: /api/optimize, /api/health, /api/presets
"""
import os
import sys
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine import PromptOptimizationEngine
from app.presets import DEVICE_PRESETS, STYLE_PRESETS, ARCHETYPE_TEMPLATES
from app.nvidia_client import SUPPORTED_MODELS, NvidiaNIMClient

# Initialize engine
engine = PromptOptimizationEngine()


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health" or path == "/api":
            client = NvidiaNIMClient()
            self._send_json(200, {
                "status": "healthy",
                "service": "Figma AI Prompt Optimizer",
                "version": "1.0.0",
                "nvidia_key_configured": client.is_configured()
            })
            return

        elif path == "/api/presets":
            self._send_json(200, {
                "devices": list(DEVICE_PRESETS.values()),
                "styles": list(STYLE_PRESETS.values()),
                "archetypes": [
                    {"id": k, **v} for k, v in ARCHETYPE_TEMPLATES.items()
                ],
                "models": SUPPORTED_MODELS
            })
            return

        self._send_json(404, {"success": False, "error": "Endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/optimize":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_json(400, {"success": False, "error": f"Invalid JSON: {str(e)}"})
                return

            user_input = data.get("prompt", "").strip()
            if not user_input:
                self._send_json(400, {"success": False, "error": "Field 'prompt' is required"})
                return

            device_id = data.get("device", "desktop")
            style_id = data.get("style", "saas_modern")
            archetype_id = data.get("archetype")
            custom_components = data.get("components", [])
            model_id = data.get("model", "meta/llama-3.1-8b-instruct")
            temperature = float(data.get("temperature", 0.1))
            api_key = data.get("api_key") or os.environ.get("NVIDIA_API_KEY")

            try:
                result = engine.optimize(
                    user_input=user_input,
                    device_id=device_id,
                    style_id=style_id,
                    archetype_id=archetype_id,
                    custom_components=custom_components,
                    model_id=model_id,
                    temperature=temperature,
                    api_key_override=api_key
                )
                self._send_json(200, result)

            except Exception as e:
                self._send_json(500, {"success": False, "error": f"Optimization failed: {str(e)}"})
            return

        self._send_json(404, {"success": False, "error": "Endpoint not found"})
