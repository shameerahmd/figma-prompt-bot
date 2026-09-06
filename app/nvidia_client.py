"""
NVIDIA NIM API Client for LLM Inference.
Handles authentication, model routing, error management, and offline simulation fallback.
"""
import os
import time
import json
from typing import Dict, Any, List, Optional
import requests


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


class NvidiaNIMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "").strip()

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("nvapi-"))

    def get_available_models(self) -> List[Dict[str, Any]]:
        return SUPPORTED_MODELS

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "meta/llama-3.1-8b-instruct",
        temperature: float = 0.1,
        max_tokens: int = 350
    ) -> Dict[str, Any]:
        """
        Sends generation request to NVIDIA NIM API.
        Falls back to local heuristic synthesis if no API key is provided or offline.
        """
        if not self.is_configured():
            return self._mock_offline_optimization(user_prompt)

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
            response = requests.post(
                NVIDIA_API_URL,
                headers=headers,
                json=payload,
                timeout=30
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
            # Network issue or timeout
            return {
                "status": "warning",
                "error_code": "NETWORK_UNAVAILABLE",
                "message": f"Could not reach NVIDIA endpoint: {str(e)}. Using offline heuristic optimizer.",
                "fallback": self._mock_offline_optimization(user_prompt)
            }

    def _mock_offline_optimization(self, user_prompt: str) -> Dict[str, Any]:
        """
        Deterministic, local rule-based optimizer for offline demonstration & testing.
        Analyzes keywords and produces valid bracket-tokenized Figma AI prompts.
        """
        text_lower = user_prompt.lower()

        # Detect target device
        if "mobile" in text_lower or "app" in text_lower or "phone" in text_lower or "ios" in text_lower or "android" in text_lower:
            frame = "Mobile iOS 375px, Status & HomeBar"
        elif "tablet" in text_lower or "ipad" in text_lower:
            frame = "Tablet iPad 834px, DualPane"
        elif "watch" in text_lower:
            frame = "AppleWatch 390px, OLED Black"
        else:
            frame = "Desktop 1440px, DarkMode #0B0F17"

        # Detect theme / style
        if "light" in text_lower or "clean" in text_lower:
            theme = "Clean Minimal Light #FFFFFF, Border #E2E8F0, Accent #2563EB"
            radius = "8px"
        elif "brutalis" in text_lower:
            theme = "Neo-Brutalist #FFE600, Black 2px Borders, Hard Shadows"
            radius = "0px"
        elif "glass" in text_lower:
            theme = "Frosted Glassmorphism rgba(255,255,255,0.06), Glow Accent #06B6D4"
            radius = "16px"
        else:
            theme = "Dark OLED Slate #09090B, Card #18181B, Accent #6366F1"
            radius = "10px"

        # Detect UI sections & components
        sections = []
        if "dashboard" in text_lower or "analytic" in text_lower or "metric" in text_lower:
            layout = "SidebarNav(240px Fixed) + MainContent(Vertical Auto-layout, 24px gap)"
            header = "HeaderBar(SearchInput, NotificationBell, UserAvatar('Alex M.'))"
            hero = "MetricCardsRow(4 Cols: Revenue, ActiveUsers, ConversionRate, Churn)"
            content = "Section('Trends', AreaChart(CryptoBlue), BarChart(WeeklyActivity))"
            data = "Section('Transactions', DataTable(Cols: ID, Customer, Date, StatusBadge, Amount, Actions))"
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: {layout}]",
                f"[Header: {header}]",
                f"[Hero: {hero}]",
                f"[Charts: {content}]",
                f"[Data: {data}]",
                f"[Tokens: Radius={radius}, {theme}, Inter Regular/SemiBold, 8px Grid]"
            ]
        elif "login" in text_lower or "auth" in text_lower or "signup" in text_lower or "register" in text_lower:
            layout = "Centered Modal Frame(Width 420px, Auto-layout Vertical, 32px padding)"
            header = "BrandLogo(Centered), Title('Welcome Back'), Subtitle('Sign in to continue')"
            form = "FormInputs(Input(Email, placeholder='user@domain.com'), Input(Password, type='password', EyeToggle))"
            actions = "Controls(Checkbox('Remember me'), Link('Forgot Password?'))"
            cta = "ButtonGroup(PrimaryButton('Sign In', Width=Full), DividerText('or continue with'), OAuthGroup(GoogleBtn, GitHubBtn))"
            footer = "FooterText('Don\\'t have an account? ', Link('Sign up'))"
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: {layout}]",
                f"[Header: {header}]",
                f"[Inputs: {form}]",
                f"[Controls: {actions}]",
                f"[Actions: {cta}]",
                f"[Footer: {footer}]",
                f"[Tokens: Radius={radius}, {theme}, High-Contrast Focus States]"
            ]
        elif "shop" in text_lower or "ecommerce" in text_lower or "product" in text_lower or "store" in text_lower:
            layout = "Vertical Auto-layout, 16px Gutters, 24px Section Margin"
            header = "Header(BackArrow, Title('Product Details'), CartIcon(Badge=2))"
            hero = "HeroGallery(CarouselThumbnails, DiscountBadge('-25%'), HeartWishlistIcon)"
            controls = "SelectorBlock(PriceTag('$129.00'), RatingStars('4.8 (210 reviews)'), ColorPills(3), SizeChips('S','M','L','XL'))"
            cta = "StickyBottomBar(QtyStepper(1-10), PrimaryCTA('Add to Cart', CartIcon))"
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: {layout}]",
                f"[Header: {header}]",
                f"[Hero: {hero}]",
                f"[Controls: {controls}]",
                f"[StickyFooter: {cta}]",
                f"[Tokens: Radius={radius}, {theme}, 8px Spacing Grid]"
            ]
        else:
            # Generic structured modern UI
            sections = [
                f"[Frame: {frame}]",
                f"[Layout: Auto-layout Vertical, 20px Spacing, 24px Frame Padding]",
                f"[Header: TopBar(BrandIcon, Breadcrumbs, ActionButtons('Export', 'New Item'))]",
                f"[Hero: HeroBanner(Heading('Overview'), Subtext, SegmentedControl('All', 'Active', 'Archived'))]",
                f"[Content: BentoGrid(2x2 Cards: MetricCard, VisualSummary, ActivityStream, QuickActions))]",
                f"[Footer: PaginationBar(PageIndicator, PrevNextButtons)]",
                f"[Tokens: Radius={radius}, {theme}, Inter Sans, 8px Grid Base]"
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
