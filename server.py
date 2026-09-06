#!/usr/bin/env python3
"""
Figma AI Prompt Generator - High Performance Web Server.
Zero external framework dependencies (uses Python 3 standard library http.server / socketserver).
Can be deployed anywhere with Python 3.10+.
"""
import os
import sys
import json
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.engine import PromptOptimizationEngine
from app.presets import DEVICE_PRESETS, STYLE_PRESETS, ARCHETYPE_TEMPLATES
from app.nvidia_client import SUPPORTED_MODELS, NvidiaNIMClient


PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

engine = PromptOptimizationEngine()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class RequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            client = NvidiaNIMClient()
            resp = {
                "status": "healthy",
                "service": "Figma AI Prompt Generator",
                "version": "1.0.0",
                "nvidia_key_configured": client.is_configured()
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        elif path == "/api/presets":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "devices": list(DEVICE_PRESETS.values()),
                "styles": list(STYLE_PRESETS.values()),
                "archetypes": [
                    {"id": k, **v} for k, v in ARCHETYPE_TEMPLATES.items()
                ],
                "models": SUPPORTED_MODELS
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # Serve static files from public/
        self.serve_static_file(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/optimize":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                self.send_error_json(400, f"Invalid JSON payload: {str(e)}")
                return

            user_input = data.get("prompt", "").strip()
            if not user_input:
                self.send_error_json(400, "Field 'prompt' is required and cannot be empty.")
                return

            device_id = data.get("device", "desktop")
            style_id = data.get("style", "saas_modern")
            archetype_id = data.get("archetype")
            custom_components = data.get("components", [])
            model_id = data.get("model", "meta/llama-3.1-8b-instruct")
            temperature = float(data.get("temperature", 0.1))
            api_key = data.get("api_key")

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

                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))

            except Exception as e:
                self.send_error_json(500, f"Optimization failed: {str(e)}")
            return

        self.send_error_json(404, "Endpoint not found.")

    def send_error_json(self, status_code: int, message: str):
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": message}).encode("utf-8"))

    def serve_static_file(self, req_path: str):
        if req_path == "/" or req_path == "":
            req_path = "/index.html"

        # Sanitize path to prevent directory traversal
        clean_path = os.path.normpath(req_path).lstrip("/")
        full_path = os.path.join(PUBLIC_DIR, clean_path)

        if not os.path.exists(full_path) or os.path.isdir(full_path):
            full_path = os.path.join(PUBLIC_DIR, "index.html")

        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type is None:
            mime_type = "text/plain"

        try:
            with open(full_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(500, f"Error reading file: {str(e)}")


def run_server():
    server_address = (HOST, PORT)
    httpd = ThreadedHTTPServer(server_address, RequestHandler)
    print(f"============================================================")
    print(f" Figma AI Prompt Generator Server running at:")
    print(f" http://localhost:{PORT}")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
