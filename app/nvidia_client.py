"""
NVIDIA NIM API Client for LLM Inference.
Handles authentication, model routing, error management, and offline simulation fallback.
"""
import os
import time
import json
import random
from typing import Dict, Any, List, Optional, Generator
import requests

# Load .env for local development (harmless no-op on Vercel, which uses env vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Recommended fast & efficient models from NVIDIA catalog
SUPPORTED_MODELS = [
    {
        "id": "meta/llama-3.1-8b-instruct",
        "name": "Llama 3.1 8B Instruct (Recommended - Fast & Compact)",
        "provider": "Meta / NVIDIA",
        "context_length": 128000,
        "default": True
    },
    {
        "id": "mistralai/mixtral-8x7b-instruct-v0.1",
        "name": "Mixtral 8x7B Instruct (High UI Precision)",
        "provider": "Mistral AI",
        "context_length": 32768,
        "default": False
    },
    {
        "id": "nvidia/nemotron-mini-4b-instruct",
        "name": "Nemotron Mini 4B (Ultra-low Latency)",
        "provider": "NVIDIA",
        "context_length": 4096,
        "default": False
    },
    {
        "id": "google/gemma-2-9b-it",
        "name": "Gemma 2 9B IT (Balanced)",
        "provider": "Google",
        "context_length": 8192,
        "default": False
    }
]

# Per-model generation tuning: larger max_tokens for high-fidelity models, and
# routing weights so the engine can pick the best model for a given job.
MODEL_PROFILES = {
    "meta/llama-3.1-8b-instruct": {
        "max_tokens": 500, "temperature": 0.2,
        "route_weight": 50, "tag": "balanced",
    },
    "mistralai/mixtral-8x7b-instruct-v0.1": {
        "max_tokens": 700, "temperature": 0.1,
        "route_weight": 100, "tag": "high-fidelity",
    },
    "nvidia/nemotron-mini-4b-instruct": {
        "max_tokens": 400, "temperature": 0.1,
        "route_weight": 40, "tag": "fast",
    },
    "google/gemma-2-9b-it": {
        "max_tokens": 500, "temperature": 0.2,
        "route_weight": 60, "tag": "balanced",
    },
}

DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2

# Shared session for HTTP keep-alive / connection reuse within a single
# function invocation. In a serverless function each call is a fresh process,
# but within one request this avoids re-opening sockets for each retry.
_session = requests.Session()
_session.headers.update({"Connection": "keep-alive"})


class NvidiaNIMClient:
    def __init__(self, api_key: Optional[str] = None, max_retries: int = _MAX_RETRIES):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "").strip()
        self.max_retries = max_retries
        self.session = _session

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("nvapi-"))

    def get_available_models(self) -> List[Dict[str, Any]]:
        return SUPPORTED_MODELS

    @staticmethod
    def resolve_defaults(model_id: str) -> dict:
        """Return tuned max_tokens/temperature for a model, with a safe fallback."""
        return MODEL_PROFILES.get(model_id, {"max_tokens": 500, "temperature": 0.2})

    @staticmethod
    def _backoff(attempt: int) -> float:
        """Exponential backoff with a small jitter (0.4s, 0.8s)."""
        return min(0.4 * (2 ** attempt), 1.6) + random.random() * 0.15

    def _post_retry(self, url, headers, payload, timeout):
        """
        POST with retry only on transient status codes / network errors.
        Hard 4xx auth errors are NOT retried.
        """
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.post(url, headers=headers, json=payload, timeout=timeout)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < self.max_retries:
                    time.sleep(self._backoff(attempt))
                    continue
                raise
            except requests.exceptions.RequestException:
                # Re-raise non-transient request exceptions (SSL, invalid URL, etc.)
                raise

            if resp.status_code in TRANSIENT_STATUS_CODES and attempt < self.max_retries:
                resp.close()
                time.sleep(self._backoff(attempt))
                continue
            return resp

        # Unreachable; kept defensively.
        raise requests.exceptions.ConnectionError("request failed after retries")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sends generation request to NVIDIA NIM API with per-model tuning and
        transient retry. Falls back to local heuristic synthesis if no API key
        is provided or offline.
        """
        if not self.is_configured():
            return self._mock_offline_optimization(user_prompt)

        defaults = self.resolve_defaults(model)
        temperature = defaults["temperature"] if temperature is None else temperature
        max_tokens = defaults["max_tokens"] if max_tokens is None else max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "stream": False
        }

        start_time = time.time()
        try:
            response = self._post_retry(
                NVIDIA_API_URL, headers=headers, payload=payload, timeout=30
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {
                    "prompt_tokens": len(user_prompt.split()),
                    "completion_tokens": len(content.split()),
                    "total_tokens": len(user_prompt.split()) + len(content.split())
                })
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
                    "mode": "nvidia_nim_live"
                }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error_code": "AUTH_ERROR",
                    "message": "Invalid NVIDIA API Key. Please verify your nvapi-... key.",
                    "fallback": self._mock_offline_optimization(user_prompt)
                }
            else:
                error_detail = response.text
                return {
                    "status": "error",
                    "error_code": f"HTTP_{response.status_code}",
                    "message": f"NVIDIA API Error ({response.status_code}): {error_detail[:200]}",
                    "fallback": self._mock_offline_optimization(user_prompt)
                }

        except requests.exceptions.RequestException as e:
            # Network issue or timeout (handled after retries)
            return {
                "status": "warning",
                "error_code": "NETWORK_UNAVAILABLE",
                "message": f"Could not reach NVIDIA endpoint: {str(e)}. Using offline heuristic optimizer.",
                "fallback": self._mock_offline_optimization(user_prompt)
            }

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streaming generation via NVIDIA NIM (SSE). Yields two event shapes:
          - {"type": "token", "text": "<delta>"}   (partial tokens as they arrive)
          - {"type": "done", ...full result...}    (final, including fallback)

        This keeps the FIRST byte flowing back to Vercel almost immediately, so
        a slow generation does not trip Vercel's hard serverless timeout.
        """
        if not self.is_configured():
            fb = self._mock_offline_optimization(user_prompt)
            yield {
                "type": "done",
                "text": fb["text"],
                "latency_ms": fb.get("latency_ms", 45),
                "usage": fb.get("usage", {}),
                "model": fb.get("model"),
                "mode": fb.get("mode"),
                "notice": None
            }
            return

        defaults = self.resolve_defaults(model)
        temperature = defaults["temperature"] if temperature is None else temperature
        max_tokens = defaults["max_tokens"] if max_tokens is None else max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "stream": True
        }

        start_time = time.time()
        try:
            with self.session.post(
                NVIDIA_API_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(10, 60)
            ) as resp:
                if resp.status_code == 200:
                    full = []
                    for raw in resp.iter_lines(decode_unicode=True):
                        if not raw:
                            continue
                        line = raw.strip(" \r")
                        if line.startswith("data:"):
                            data = line[len("data:"):].strip()
                            if data in ("[DONE]", "data: [DONE]"):
                                break
                            try:
                                obj = json.loads(data)
                                delta = obj["choices"][0]["delta"].get("content", "")
                            except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                                continue
                            if delta:
                                full.append(delta)
                                yield {"type": "token", "text": delta}

                    text = "".join(full).strip()
                    latency_ms = int((time.time() - start_time) * 1000)

                    # A 200 with zero content is still a failed generation; fall back.
                    if not text:
                        fb = self._mock_offline_optimization(user_prompt)
                        yield {
                            "type": "done",
                            "text": fb["text"],
                            "latency_ms": fb.get("latency_ms", 45),
                            "usage": fb.get("usage", {}),
                            "model": fb.get("model"),
                            "mode": "offline_fallback",
                            "notice": "NVIDIA stream returned empty output. Using offline heuristic optimizer.",
                            "error_code": "EMPTY_STREAM"
                        }
                        return

                    usage = {
                        "input": len(user_prompt.split()),
                        "output": len(text.split()),
                        "total": len(user_prompt.split()) + len(text.split())
                    }
                    yield {
                        "type": "done",
                        "text": text,
                        "latency_ms": latency_ms,
                        "usage": usage,
                        "model": model,
                        "mode": "nvidia_nim_stream",
                        "notice": None
                    }
                else:
                    error_code = "AUTH_ERROR" if resp.status_code == 401 else f"HTTP_{resp.status_code}"
                    message = (
                        "Invalid NVIDIA API Key. Please verify your nvapi-... key."
                        if resp.status_code == 401
                        else f"NVIDIA API Error ({resp.status_code})"
                    )
                    fb = self._mock_offline_optimization(user_prompt)
                    yield {
                        "type": "done",
                        "text": fb["text"],
                        "latency_ms": fb.get("latency_ms", 45),
                        "usage": fb.get("usage", {}),
                        "model": fb.get("model"),
                        "mode": "offline_fallback",
                        "notice": f"{message} Using offline heuristic optimizer.",
                        "error_code": error_code
                    }

        except requests.exceptions.RequestException as e:
            fb = self._mock_offline_optimization(user_prompt)
            yield {
                "type": "done",
                "text": fb["text"],
                "latency_ms": fb.get("latency_ms", 45),
                "usage": fb.get("usage", {}),
                "model": fb.get("model"),
                "mode": "offline_fallback",
                "notice": f"Could not reach NVIDIA endpoint: {str(e)}. Using offline heuristic optimizer.",
                "error_code": "NETWORK_UNAVAILABLE"
            }

    def _mock_offline_optimization(self, user_prompt: str) -> Dict[str, Any]:
        """
        Deterministic, local rule-based optimizer for offline demonstration & testing.
        Analyzes keywords and produces valid bracket-tokenized Figma AI prompts
        using real Figma Community design patterns and tokens.
        """
        text_lower = user_prompt.lower()

        # Detect target device
        if "mobile" in text_lower or "app" in text_lower or "phone" in text_lower or "ios" in text_lower or "android" in text_lower:
            frame = "Mobile iOS 375px, SafeArea Top/Bottom, #FFFFFF"
        elif "tablet" in text_lower or "ipad" in text_lower:
            frame = "Tablet iPad 834px, DualPane, #F9FAFB"
        elif "watch" in text_lower:
            frame = "AppleWatch 390px, OLED #000000"
        else:
            frame = "Desktop 1440px, #FFFFFF"

        # Detect theme / style (using design system tokens)
        if "light" in text_lower or "clean" in text_lower:
            bg = "#FFFFFF"
            surface = "#F9FAFB"
            border = "#E5E7EB"
            primary = "#4F46E5"
            text = "#111827"
            radius = "8px"
            shadow = "0px 1px 3px 0px rgba(0,0,0,0.1)"
        elif "brutalis" in text_lower or "brutal" in text_lower:
            bg = "#FFE600"
            surface = "#FFFFFF"
            border = "#000000"
            primary = "#000000"
            text = "#000000"
            radius = "0px"
            shadow = "4px 4px 0px #000000"
        elif "glass" in text_lower:
            bg = "rgba(255,255,255,0.08)"
            surface = "rgba(255,255,255,0.12)"
            border = "rgba(255,255,255,0.16)"
            primary = "#06B6D4"
            text = "#F9FAFB"
            radius = "16px"
            shadow = "0px 10px 15px -3px rgba(0,0,0,0.1)"
        else:
            bg = "#0F172A"
            surface = "#1E293B"
            border = "#334155"
            primary = "#6366F1"
            text = "#F1F5F9"
            radius = "8px"
            shadow = "0px 4px 6px -1px rgba(0,0,0,0.1)"

        # Detect UI sections & components (using Figma Community patterns)
        sections = []
        if "dashboard" in text_lower or "analytic" in text_lower or "metric" in text_lower:
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: Horizontal, SidebarNav(240px, Fixed, bg {surface}) + MainContent(Vertical, 24px gap, 32px padding)]",
                f"[Header: TopBar(Height 64px, SearchInput(width 320px, placeholder 'Search...'), NotificationBell(Badge='3'), UserAvatar('AM', size 40px))]",
                f"[Hero: MetricCardsGrid(4 cols, 16px gap, Card: 12px padding, {radius} radius, bg {surface}, border 1px {border}, shadow {shadow})]",
                f"[Sections: Section('Performance Trends'): AreaChart(height 280px, stroke {primary}, fill gradient {primary}@30%), Section('Activity'): DataTable(header bg {surface}, row hover {border}, striped)]",
                f"[Data: Columns(Timestamp, User, Action, Status[Badge], Amount[Bold])]",
                f"[Tokens: Typography(Inter SemiBold 16px headings, Inter Regular 14px body), Colors(Primary {primary}, Surface {surface}, Border {border}, Text {text}), Spacing(8px Grid), Radius({radius}), Shadow({shadow})]"
            ]
        elif "login" in text_lower or "auth" in text_lower or "signup" in text_lower or "register" in text_lower:
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: Centered Modal(Width 420px, Vertical Auto-layout, 32px padding, {radius} radius, shadow {shadow})]",
                f"[Header: BrandLogo(Centered, 48px height), Title('Welcome Back', Inter SemiBold 24px, {text}), Subtitle('Sign in to continue', Inter Regular 14px, opacity 0.7)]",
                f"[Inputs: Input(Email, height 44px, 12px padding, {radius} radius, border 1px {border}, placeholder 'user@domain.com'), Input(Password, EyeToggle, type password, same styling)]",
                f"[Controls: Horizontal(Checkbox('Remember me', 16px), Link('Forgot Password?', {primary}, 14px))]",
                f"[Actions: PrimaryButton('Sign In', width full, height 44px, bg {primary}, text #FFFFFF, {radius} radius, hover darken 10%), DividerText('or continue with', 12px, margin 24px 0px), OAuthGrid(2 cols, GoogleBtn(icon+text, border 1px {border}), GitHubBtn(icon+text, border 1px {border}))]",
                f"[Footer: FooterText('Don't have an account? ', 14px, Link('Sign up', {primary}))]",
                f"[Tokens: Typography(Inter), Focus(Ring 2px {primary}, offset 2px), States(Hover, Active, Disabled opacity 0.5), Spacing(12px field gap, 8px label-input)]"
            ]
        elif "shop" in text_lower or "ecommerce" in text_lower or "product" in text_lower or "store" in text_lower:
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: Vertical Auto-layout, 16px Gutters, 24px Frame Padding]",
                f"[Header: TopBar(Height 56px, BackArrow(IconButton 40x40px), Title('Product Details', Inter SemiBold 18px, centered), CartIcon(Badge='2', {primary} bg))]",
                f"[Hero: ImageCarousel(AspectRatio 1:1, Thumbnails bottom 8px gap, DiscountBadge('-25%', {primary} bg, top-right absolute), HeartIcon(top-right, toggle favorite))]",
                f"[Sections: Section('Details'): PriceRow(CurrentPrice('$129.00', Inter Bold 28px, {text}), OriginalPrice('$172.00', strike, opacity 0.5)), RatingStars(4.8/5, 210 reviews link), Section('Options'): ColorPills(3 variants, 40x40px, border 2px {primary} when selected, {radius} radius full), SizeChips('S','M','L','XL', min 48x48px touch target, selected bg {primary} text #FFFFFF)]",
                f"[Controls: QuantityStepper(ButtonGroup, -/+ IconButtons 40x40px, NumberDisplay centered 60px width)]",
                f"[StickyFooter: BottomBar(Height 72px, 16px padding, shadow top, PrimaryCTA('Add to Cart', height 48px, {radius} radius, bg {primary}, CartIcon, width flex-1))]",
                f"[Tokens: TouchTarget(min 48x48px), Spacing(8px Grid, 16px section gap, 24px page padding), Typography(Inter), Colors(Primary {primary}, Success #10B981, Surface {surface}), Radius({radius}), Elevation({shadow})]"
            ]
        else:
            # Generic structured modern UI with Figma Community best practices
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: Vertical Auto-layout, 24px Spacing, 32px Frame Padding, max-width 1280px centered]",
                f"[Header: TopBar(Height 64px, 24px horizontal padding, BrandIcon(32px), Breadcrumbs(Inter 14px, separator '/'), ActionButtons('Export', 'New Item', height 36px, 12px padding, {radius} radius))]",
                f"[Hero: HeroBanner(48px padding, Heading('Overview', Inter Bold 36px, {text}), Subtext(Inter Regular 16px, opacity 0.7, max-width 600px), SegmentedControl('All', 'Active', 'Archived', bg {surface}, {radius} radius, selected bg {primary} text #FFFFFF))]",
                f"[Content: BentoGrid(2x2, 24px gap, Card: 24px padding, {radius} radius, bg {surface}, border 1px {border}, shadow {shadow}, Components: MetricCard(Icon 48px, Value Inter Bold 32px, Label 14px, Trend indicator), ActivityStream(Avatar 32px, Text 14px, Timestamp opacity 0.6), QuickActions(IconButtons 56x56px, label below))]",
                f"[Footer: PaginationBar(Height 56px, 24px padding, PageIndicator(Inter 14px, current {primary}), PrevNext(IconButtons 36x36px, disabled opacity 0.3))]",
                f"[Tokens: Typography(Inter, Display 36px/44px Bold, Heading 24px/32px SemiBold, Body 16px/24px Regular, Caption 12px/16px), Colors(Primary {primary}, Surface {surface}, Border {border}, Text {text}, Success #10B981, Warning #F59E0B, Danger #EF4444), Spacing(4/8/12/16/24/32/48px scale), Radius({radius} cards, 6px inputs, 9999px pills), Shadow({shadow}), Grid(8px base)]"
            ]

        simulated_text = "\n".join(sections)

        return {
            "status": "success",
            "text": simulated_text,
            "model": "offline-rule-synthesizer",
            "latency_ms": 45,
            "usage": {
                "input": len(user_prompt.split()),
                "output": len(simulated_text.split()),
                "total": len(user_prompt.split()) + len(simulated_text.split())
            },
            "mode": "offline_demonstration"
        }
