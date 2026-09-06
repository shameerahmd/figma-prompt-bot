"""
Vercel Serverless Function Entry Point for Figma AI Prompt Optimizer.
Handles all API routes: /api/optimize, /api/health, /api/presets
"""
import os
import sys
import json
import uuid
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine import PromptOptimizationEngine
from app.presets import DEVICE_PRESETS, STYLE_PRESETS, ARCHETYPE_TEMPLATES
from app.nvidia_client import SUPPORTED_MODELS, NvidiaNIMClient
from app.providers import OpenAIProvider, AnthropicProvider
from app.export_formats import export_json, export_markdown, export_figma_plugin, export_plain_text

# Provider registry for multi-provider support
PROVIDERS = {
    "nvidia": {"name": "NVIDIA NIM", "models": SUPPORTED_MODELS, "key_env": "NVIDIA_API_KEY"},
    "openai": {"name": "OpenAI", "models": OpenAIProvider.SUPPORTED_MODELS, "key_env": "OPENAI_API_KEY"},
    "anthropic": {"name": "Anthropic", "models": AnthropicProvider.SUPPORTED_MODELS, "key_env": "ANTHROPIC_API_KEY"},
}

# Initialize engine
engine = PromptOptimizationEngine()

# Machine-readable error codes
ERROR_CODES = {
    "INVALID_JSON": {"status": 400, "message": "Request body is not valid JSON"},
    "MISSING_FIELD": {"status": 400, "message": "Required field is missing"},
    "INVALID_DEVICE": {"status": 400, "message": "Invalid device preset ID"},
    "INVALID_STYLE": {"status": 400, "message": "Invalid style preset ID"},
    "INVALID_MODEL": {"status": 400, "message": "Unsupported model ID"},
    "EMPTY_PROMPT": {"status": 400, "message": "Prompt cannot be empty"},
    "PROMPT_TOO_LONG": {"status": 400, "message": "Prompt exceeds maximum length (10000 characters)"},
    "BATCH_TOO_LARGE": {"status": 400, "message": "Batch exceeds maximum size (50 requirements)"},
    "OPTIMIZATION_FAILED": {"status": 500, "message": "Optimization engine failed"},
    "NOT_FOUND": {"status": 404, "message": "Endpoint not found"}
}


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict, request_id: str = None):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_error(self, error_code: str, request_id: str, details: str = None):
        """Send structured error response with machine-readable code."""
        err_spec = ERROR_CODES.get(error_code, ERROR_CODES["OPTIMIZATION_FAILED"])
        payload = {
            "success": False,
            "error_code": error_code,
            "error": err_spec["message"],
            "request_id": request_id
        }
        if details:
            payload["details"] = details
        self._send_json(err_spec["status"], payload, request_id)

    def _resolve_provider_key(self, provider: str, data: dict) -> Optional[str]:
        """
        Resolve the API key for a given provider from request payload or env.
        """
        provider_info = PROVIDERS.get(provider)
        if not provider_info:
            return data.get("api_key")

        key_env = provider_info["key_env"]
        return data.get("api_key") or os.environ.get(key_env)

    def _validate_payload(self, data: dict, request_id: str) -> tuple:
        """
        Validate optimization request payload. Returns (is_valid, error_code, details).
        """
        user_input = data.get("prompt", "").strip()
        if not user_input:
            return (False, "EMPTY_PROMPT", None)
        if len(user_input) > 10000:
            return (False, "PROMPT_TOO_LONG", f"Length: {len(user_input)} characters")

        device_id = data.get("device", "desktop")
        if device_id not in DEVICE_PRESETS:
            return (False, "INVALID_DEVICE", f"Unknown device: {device_id}")

        style_id = data.get("style", "saas_modern")
        if style_id not in STYLE_PRESETS:
            return (False, "INVALID_STYLE", f"Unknown style: {style_id}")

        model_id = data.get("model")
        if model_id:
            valid_models = {m["id"] for m in SUPPORTED_MODELS}
            if model_id not in valid_models:
                return (False, "INVALID_MODEL", f"Unknown model: {model_id}")

        return (True, None, None)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        request_id = str(uuid.uuid4())

        if path == "/api/health" or path == "/api":
            client = NvidiaNIMClient()
            self._send_json(200, {
                "status": "healthy",
                "service": "Figma AI Prompt Optimizer",
                "version": "1.0.0",
                "nvidia_key_configured": client.is_configured(),
                "request_id": request_id
            }, request_id)
            return

        elif path == "/api/presets":
            self._send_json(200, {
                "devices": list(DEVICE_PRESETS.values()),
                "styles": list(STYLE_PRESETS.values()),
                "archetypes": [
                    {"id": k, **v} for k, v in ARCHETYPE_TEMPLATES.items()
                ],
                "models": SUPPORTED_MODELS,
                "providers": [
                    {"id": pid, "name": pinfo["name"], "models": pinfo["models"]}
                    for pid, pinfo in PROVIDERS.items()
                ],
                "request_id": request_id
            }, request_id)
            return

        self._send_error("NOT_FOUND", request_id)

    def _send_sse(self, data: dict, request_id: str = None):
        """Write one Server-Sent Event frame and flush it to the client."""
        if request_id and "request_id" not in data:
            data["request_id"] = request_id
        payload = f"data: {json.dumps(data)}\n\n".encode("utf-8")
        self.wfile.write(payload)
        self.wfile.flush()

    def _open_sse_stream(self, request_id: str):
        """Send SSE headers so buffering is disabled and tokens stream live."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.flush()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        request_id = str(uuid.uuid4())

        if path == "/api/optimize/stream":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_error("INVALID_JSON", request_id, str(e))
                return

            # Validate request payload
            is_valid, error_code, details = self._validate_payload(data, request_id)
            if not is_valid:
                self._send_error(error_code, request_id, details)
                return

            user_input = data.get("prompt", "").strip()
            device_id = data.get("device", "desktop")
            style_id = data.get("style", "saas_modern")
            archetype_id = data.get("archetype")
            custom_components = data.get("components", [])
            model_id = data.get("model")  # None = auto-route
            temperature = float(data.get("temperature", 0.1))
            api_key = data.get("api_key") or os.environ.get("NVIDIA_API_KEY")

            try:
                self._open_sse_stream(request_id)
                for evt in engine.optimize_stream(
                    user_input=user_input,
                    device_id=device_id,
                    style_id=style_id,
                    archetype_id=archetype_id,
                    custom_components=custom_components,
                    model_id=model_id,
                    temperature=temperature,
                    api_key_override=api_key
                ):
                    self._send_sse(evt, request_id)
                self._send_sse({"type": "done_stream"}, request_id)
            except Exception as e:
                self._send_sse({
                    "type": "error",
                    "success": False,
                    "error_code": "OPTIMIZATION_FAILED",
                    "error": f"Optimization failed: {str(e)}"
                }, request_id)
            finally:
                self.wfile.flush()
            return

        # --- Batch optimization: multiple requirements in one request ---
        if path == "/api/optimize/batch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_error("INVALID_JSON", request_id, str(e))
                return

            requirements = data.get("requirements", [])
            if not isinstance(requirements, list) or len(requirements) == 0:
                self._send_error("MISSING_FIELD", request_id, "Field 'requirements' must be a non-empty array")
                return
            if len(requirements) > 50:
                self._send_error("BATCH_TOO_LARGE", request_id, "Maximum 50 requirements per batch")
                return

            device_id = data.get("device", "desktop")
            style_id = data.get("style", "saas_modern")
            model_id = data.get("model")  # None = auto-route
            temperature = float(data.get("temperature", 0.1))
            api_key = data.get("api_key") or os.environ.get("NVIDIA_API_KEY")

            try:
                result = engine.optimize_batch(
                    requirements=requirements,
                    device_id=device_id,
                    style_id=style_id,
                    model_id=model_id,
                    temperature=temperature,
                    api_key_override=api_key
                )
                result["request_id"] = request_id
                self._send_json(200, result, request_id)
            except Exception as e:
                self._send_error("OPTIMIZATION_FAILED", request_id, str(e))
            return

        # --- Responsive variants: desktop + mobile + tablet in one request ---
        if path == "/api/optimize/responsive":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_error("INVALID_JSON", request_id, str(e))
                return

            user_input = data.get("prompt", "").strip()
            if not user_input:
                self._send_error("EMPTY_PROMPT", request_id)
                return

            style_id = data.get("style", "saas_modern")
            archetype_id = data.get("archetype")
            custom_components = data.get("components", [])
            model_id = data.get("model")  # None = auto-route
            temperature = float(data.get("temperature", 0.1))
            variants = data.get("variants", ["desktop", "mobile", "tablet"])
            api_key = data.get("api_key") or os.environ.get("NVIDIA_API_KEY")

            try:
                result = engine.optimize_responsive(
                    user_input=user_input,
                    style_id=style_id,
                    archetype_id=archetype_id,
                    custom_components=custom_components,
                    model_id=model_id,
                    temperature=temperature,
                    api_key_override=api_key,
                    variants=variants
                )
                result["request_id"] = request_id
                self._send_json(200, result, request_id)
            except Exception as e:
                self._send_error("OPTIMIZATION_FAILED", request_id, str(e))
            return

        # --- Refine: modify an existing prompt ---
        if path == "/api/refine":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_error("INVALID_JSON", request_id, str(e))
                return

            existing_prompt = data.get("existing_prompt", "").strip()
            modification = data.get("modification", "").strip()

            if not existing_prompt:
                self._send_error("EMPTY_PROMPT", request_id, "Field 'existing_prompt' is required")
                return
            if not modification:
                self._send_error("MISSING_FIELD", request_id, "Field 'modification' is required")
                return

            device_id = data.get("device", "desktop")
            style_id = data.get("style", "saas_modern")
            model_id = data.get("model")  # None = auto-route
            temperature = float(data.get("temperature", 0.1))
            api_key = data.get("api_key") or os.environ.get("NVIDIA_API_KEY")

            try:
                result = engine.refine(
                    existing_prompt=existing_prompt,
                    modification_instruction=modification,
                    device_id=device_id,
                    style_id=style_id,
                    model_id=model_id,
                    temperature=temperature,
                    api_key_override=api_key
                )
                result["request_id"] = request_id
                self._send_json(200, result, request_id)
            except Exception as e:
                self._send_error("OPTIMIZATION_FAILED", request_id, str(e))
            return

        if path == "/api/optimize":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_error("INVALID_JSON", request_id, str(e))
                return

            # Validate request payload
            is_valid, error_code, details = self._validate_payload(data, request_id)
            if not is_valid:
                self._send_error(error_code, request_id, details)
                return

            user_input = data.get("prompt", "").strip()
            device_id = data.get("device", "desktop")
            style_id = data.get("style", "saas_modern")
            archetype_id = data.get("archetype")
            custom_components = data.get("components", [])
            model_id = data.get("model")  # None = auto-route
            temperature = float(data.get("temperature", 0.1))
            provider = data.get("provider", "nvidia")
            api_key = data.get("api_key") or os.environ.get("NVIDIA_API_KEY")

            try:
                # Provider-specific key resolution
                api_key_override = self._resolve_provider_key(provider, data)
                result = engine.optimize(
                    user_input=user_input,
                    device_id=device_id,
                    style_id=style_id,
                    archetype_id=archetype_id,
                    custom_components=custom_components,
                    model_id=model_id,
                    temperature=temperature,
                    api_key_override=api_key_override,
                    provider=provider
                )
                result["request_id"] = request_id
                self._send_json(200, result, request_id)
            except Exception as e:
                self._send_error("OPTIMIZATION_FAILED", request_id, str(e))
            return

        # --- Export: convert a recent/stored result into another format ---
        if path == "/api/export":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_error("INVALID_JSON", request_id, str(e))
                return

            fmt = data.get("format", "json")
            result = data.get("result", {})

            # Export needs at minimum an optimized_prompt to be useful
            if not result.get("optimized_prompt"):
                self._send_error("MISSING_FIELD", request_id, "Field 'result.optimized_prompt' is required")
                return

            try:
                if fmt == "json":
                    content = export_json(result)
                    mime = "application/json"
                elif fmt == "markdown":
                    content = export_markdown(result)
                    mime = "text/markdown"
                elif fmt == "figma_plugin":
                    content = export_figma_plugin(result)
                    mime = "application/javascript"
                elif fmt == "plain_text":
                    content = export_plain_text(result)
                    mime = "text/plain"
                else:
                    self._send_error("MISSING_FIELD", request_id, f"Unknown export format: {fmt}")
                    return

                self._send_json(200, {
                    "success": True,
                    "format": fmt,
                    "content": content,
                    "request_id": request_id
                }, request_id)
            except Exception as e:
                self._send_error("OPTIMIZATION_FAILED", request_id, str(e))
            return

        self._send_error("NOT_FOUND", request_id)
