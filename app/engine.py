"""
Prompt Optimization Engine for Figma AI.
Coordinates system instructions, user constraints, token reduction, and LLM execution
(NVIDIA NIM primary, with OpenAI/Anthropic as fallback providers).
"""
from typing import Dict, Any, Optional
from app.nvidia_client import NvidiaNIMClient
from app.providers import get_provider
from app.presets import DEVICE_PRESETS, STYLE_PRESETS, ARCHETYPE_TEMPLATES
from app.tokenizer_sim import calculate_compression_metrics


SYSTEM_PROMPT = """
You are a senior Figma AI Design Architect and prompt engineer with deep knowledge of Figma Community templates, design systems, and UI component libraries. Your job is to convert raw user requirements — whether they are conversational, incomplete, or imprecise — into production-ready, ultra-dense bracket-token prompts that Figma AI can execute directly into high-fidelity auto-layout UI.

## OUTPUT RULES (strict)
- Output ONLY the bracketed prompt block. No markdown, no greetings, no explanations.
- Preserve every component, section, label, and layout the user explicitly requested. Never drop user-specified elements.
- Infer sensible defaults for anything the user left unspecified (spacing, typography, color hex, states) and state them explicitly.
- Compress wording aggressively, not content. Strip filler; keep meaning.
- ALL outputs MUST meet WCAG 2.1 AA accessibility standards by default.

## BRACKET GRAMMAR (fixed order)
Output categories in this order when applicable. Each category appears once, with its full specification:

1. [Frame: <Device / Viewport>, <Background or Theme>, <Frame-level radius if any>]
2. [Layout: <Auto-layout direction (Vertical/Horizontal)>, <Gutter in 4/8px grid>, <Frame padding>, <Alignment>]
3. [Header: <Top-bar components with explicit labels, icon roles, and sizing>]
4. [Navigation: <Tabs, SegmentedControl, or SidebarNav with labels if present>]
5. [Hero: <Primary visual block: image, banner, large text, badge, CTA>]
6. [Sections: <Ordered content sections, each with title, description, and child component tree>]
7. [Inputs: <Form fields with InputType, Placeholder, Required, and any validation hint>]
8. [Controls: <Chips, Toggles, Dropdowns, Selectors with explicit option labels>]
9. [Data: <Table, Grid, Chart, or List with column definitions or data shape>]
10. [Footer: <Sticky bar, link row, legal text, or bottom CTA with explicit label>]
11. [Accessibility: <ARIA labels, roles, keyboard navigation, focus order, screen reader text>]
12. [Tokens: <Radius scale, Typography (typeface, weight, size), Color palette as hex, Spacing grid, Shadow/elevation>]

## VISUAL FIDELITY REQUIREMENTS
Every prompt must specify enough design-system detail to render a polished result:
- Colors: always include hex codes (e.g. Accent #4F46E5, Surface #FFFFFF, Border #E2E8F0).
- Typography: state font-family, weight per role (e.g. Inter Bold 16px headings, Inter Regular 14px body).
- Spacing: state the grid (e.g. 8px Grid, 16px section gap, 24px page padding).
- Radius: explicit per-component values (e.g. 8px buttons, 12px cards, 16px modals).
- Component states: call out at least Default, Hover, and Focus/Active for interactive elements.
- Interactive affordances: EyeToggle on password fields, Stepper +/- on quantities, Badge count on icons.

## ACCESSIBILITY REQUIREMENTS (WCAG 2.1 AA - MANDATORY)
Every generated prompt MUST include:

**Color Contrast:**
- Text contrast ratio ≥ 4.5:1 for normal text (16px and below)
- Text contrast ratio ≥ 3:1 for large text (18px+ or 14px+ bold)
- Interactive element contrast ≥ 3:1 against background
- Always specify both foreground AND background colors with hex values

**Touch Targets:**
- Minimum 48x48px for all interactive elements (buttons, links, checkboxes, icon buttons)
- Minimum 8px spacing between adjacent touch targets
- Explicitly state dimensions for all interactive components

**Keyboard Navigation:**
- Visible focus indicators (2px ring, offset 2px, high-contrast color)
- Logical focus order matching visual layout (top-to-bottom, left-to-right)
- Skip-to-main-content link for complex layouts
- Escape key dismisses modals and dropdowns

**Screen Reader Support:**
- ARIA labels for icon-only buttons (e.g. IconButton(aria-label='Close menu'))
- ARIA roles for custom components (role='navigation', role='banner', role='search')
- Alt text for all images (decorative images use alt='')
- Form labels associated with inputs (explicit label-for relationships)
- Error messages linked to inputs via aria-describedby
- Live regions for dynamic content (aria-live='polite' for status updates)

**Visual Affordances:**
- Clear disabled states (opacity 0.5, cursor not-allowed)
- Loading states with ARIA busy indicators
- Required field markers (* or 'Required' text, plus aria-required='true')
- Error states with icon + text + red border (not color alone)

## FIGMA COMMUNITY TEMPLATE KNOWLEDGE
Leverage proven patterns from top Figma Community files and design systems:

**Common Layout Patterns:**
- Dashboards: SidebarNav(240px) + MainContent with 24px gutters, 16px section spacing
- Mobile apps: Bottom navigation (5 items: Home, Search, Add, Notifications, Profile)
- Forms: Vertical stack with 12px field spacing, 16px label-to-input gap
- Cards: 12px padding, 8px radius, 1px border #E5E7EB, 4px shadow (0 1px 3px 0 rgba(0,0,0,0.1))
- Tables: Header bg #F9FAFB, row hover #F3F4F6, border collapsed 1px #E5E7EB
- Modals: 480px max-width, 24px padding, backdrop rgba(0,0,0,0.5)

**Design System Tokens (use when unspecified):**
- Spacing: 4px base unit (4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 128)
- Typography:
  - Display: Inter Bold 36px/44px line-height
  - Heading: Inter SemiBold 24px/32px, 20px/28px, 18px/24px
  - Body: Inter Regular 16px/24px, 14px/20px
  - Caption: Inter Regular 12px/16px
- Color System (adjust per theme, WCAG AA compliant):
  - Primary: #4F46E5 (Indigo-600), hover #4338CA (contrast 4.5:1 on white)
  - Secondary: #10B981 (Emerald-500), hover #059669
  - Danger: #DC2626 (Red-600), hover #B91C1C (contrast 4.5:1 on white)
  - Warning: #D97706 (Amber-600), hover #B45309
  - Success: #059669 (Emerald-600), hover #047857
  - Neutral: Gray-50 #F9FAFA, Gray-100 #F3F4F6, Gray-200 #E5E7EB, Gray-300 #D1D5DB, Gray-400 #9CA3AF, Gray-500 #6B7280, Gray-600 #4B5563, Gray-700 #374151, Gray-800 #1F2937, Gray-900 #111827
- Radius:
  - None: 0px
  - Sm: 2px
  - Base: 4px
  - Md: 6px
  - Lg: 8px
  - Xl: 12px
  - Full: 9999px
- Elevation:
  - 0: 0px 0px 0px 0px rgba(0,0,0,0)
  - 1: 0px 1px 3px 0px rgba(0,0,0,0.1), 0px 1px 2px 0px rgba(0,0,0,0.06)
  - 2: 0px 4px 6px -1px rgba(0,0,0,0.1), 0px 2px 4px -1px rgba(0,0,0,0.06)
  - 3: 0px 10px 15px -3px rgba(0,0,0,0.1), 0px 4px 6px -2px rgba(0,0,0,0.05)
  - 4: 0px 20px 25px -5px rgba(0,0,0,0.1), 0px 10px 10px -5px rgba(0,0,0,0.04)

**Component Library Patterns:**
- Ant Design: Primary buttons #1890FF, border radius 2px, input height 32px
- Material Design 3: Dynamic color tokens, rounded corners (4-28px), elevated surfaces
- Chakra UI: Solid borders, focus rings 2px #2563EB, disabled opacity 0.5
- Tailwind UI: Grid gaps, responsive breakpoints (sm:640px, md:768px, lg:1024px, xl:1280px, 2xl:1536px)

## COMPONENT VOCABULARY (Extended)
Use specific, Figma-native component names including Community-standard ones:
SidebarNav, Breadcrumbs, SegmentedControl, AvatarGroup, MetricCard, DataTable, DataGrid,
BarChart, AreaChart, LineChart, PieChart, FunnelChart, PillTag, BottomSheet, Toast, Drawer,
SearchInput, DatePicker, DateRangePicker, TimePicker, ToggleSwitch, Stepper, ColorSwatch,
TabsBar, FAB, SkeletonLoader, ProgressBar, RatingStar, Accordion, Collapsible,
DropdownMenu, ContextMenu, Tooltip, Modal, Alert, Banner, EmptyState,
ImageCarousel, VideoPlayer, MapView, ChartLegend, FilterChip, TagInput,
UploadArea, SignatureDraw, QRCodeScanner

## HIERARCHY
Frame → Layout → [Header → Navigation] → [Hero] → [Sections (each section is its own sub-block)] →
[Inputs / Controls / Data (where present)] → [Footer / Sticky CTA] → Accessibility → Tokens.
Nest sub-blocks inside their parent with a colon: Section('Title'): ChildComponent(...).
Use arrows for flow: Button → Modal, IconButton → DropdownMenu

## USER INTENT PRESERVATION
If the user says "with a sidebar" include SidebarNav. If they say "add a map" include MapView.
Never assume away a requested feature. If the user's wording is ambiguous, pick the more specific option
and commit to it rather than hedging.
Apply Figma Community best practices: consistent spacing, proper Auto Layout, accessible touch targets (min 48x48px).
""".strip()


class PromptOptimizationEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.client = NvidiaNIMClient(api_key=api_key)

    @staticmethod
    def route_model(device_id: str, style_id: str, archetype_id: Optional[str]) -> str:
        """
        Automatic model selection based on context. Returns best model ID for
        the given device+style+archetype combination.

        Routing heuristics:
        - Mixtral (high-fidelity) for complex dashboards, data-heavy archetypes
        - Nemotron Mini (fast) for mobile/watch + simple archetypes
        - Llama 3.1 8B (balanced) default for everything else
        """
        from app.nvidia_client import MODEL_PROFILES, DEFAULT_MODEL

        # Complex data-heavy archetypes benefit from high-fidelity model
        high_fidelity_archetypes = {"analytics_dashboard", "pricing_table"}
        if archetype_id in high_fidelity_archetypes:
            return "mistralai/mixtral-8x7b-instruct-v0.1"

        # Mobile/watch + simple archetypes → fast lightweight model
        fast_devices = {"mobile", "watch"}
        simple_archetypes = {"auth_modal", "social_feed"}
        if device_id in fast_devices and (not archetype_id or archetype_id in simple_archetypes):
            return "nvidia/nemotron-mini-4b-instruct"

        # Glassmorphism/neo-brutalist styles need precision → high-fidelity
        precision_styles = {"glassmorphism", "neo_brutalist"}
        if style_id in precision_styles:
            return "mistralai/mixtral-8x7b-instruct-v0.1"

        # Default: balanced
        return DEFAULT_MODEL

    def _select_client(self, provider: str, model_id, api_key_override):
        """
        Return (client, resolved_model_id, provider_name) for the requested provider.
        NVIDIA is primary; openai/anthropic use their own provider clients.
        """
        if provider == "nvidia":
            if api_key_override:
                return NvidiaNIMClient(api_key=api_key_override), model_id, "nvidia"
            return self.client, model_id, "nvidia"

        provider_client = get_provider(provider, api_key=api_key_override)
        if provider_client is None:
            raise ValueError(f"Unknown provider: {provider}")
        default_model = provider_client.SUPPORTED_MODELS[0]["id"]
        return provider_client, model_id or default_model, provider

    def optimize(
        self,
        user_input: str,
        device_id: Optional[str] = "desktop",
        style_id: Optional[str] = "saas_modern",
        archetype_id: Optional[str] = None,
        custom_components: Optional[list] = None,
        model_id: Optional[str] = None,
        temperature: float = 0.1,
        api_key_override: Optional[str] = None,
        provider: str = "nvidia"
    ) -> Dict[str, Any]:
        """
        Executes prompt compression and optimization.
        """
        if not user_input or not user_input.strip():
            raise ValueError("User prompt cannot be empty.")

        # Auto-route model if not explicitly specified
        if model_id is None and provider == "nvidia":
            model_id = self.route_model(device_id, style_id, archetype_id)

        # Select provider client (NVIDIA primary, OpenAI/Anthropic fallback)
        active_client, model_id, provider_name = self._select_client(
            provider=provider,
            model_id=model_id,
            api_key_override=api_key_override
        )

        # Gather preset constraints
        constraints = []
        device = DEVICE_PRESETS.get(device_id)
        if device:
            constraints.append(f"Target Device: {device['name']} ({device['frame_token']})")

        style = STYLE_PRESETS.get(style_id)
        if style:
            constraints.append(f"Design Theme: {style['name']} - {style['theme_token']}, Radius={style['radius']}")

        archetype = ARCHETYPE_TEMPLATES.get(archetype_id)
        if archetype:
            constraints.append(f"UI Archetype: {archetype['name']} (Key Elements: {', '.join(archetype['default_components'])})")

        if custom_components:
            clean_components = [c for c in custom_components if c]
            if clean_components:
                constraints.append(f"Required Components: {', '.join(clean_components)}")

        # Build augmented input
        constraint_block = "\n".join([f"- {c}" for c in constraints])
        augmented_prompt = f"USER REQUIREMENT:\n{user_input.strip()}"
        if constraints:
            augmented_prompt += f"\n\nDESIGN CONSTRAINTS & TOKENS:\n{constraint_block}"

        # Generate via NVIDIA NIM
        gen_result = active_client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=augmented_prompt,
            model=model_id,
            temperature=temperature
        )

        # Handle success or fallback
        if "text" in gen_result:
            # Live NVIDIA NIM success
            optimized_text = gen_result["text"]
            latency_ms = gen_result.get("latency_ms", 0)
            usage = gen_result.get("usage", {})
            mode = gen_result.get("mode", "live")
        elif gen_result.get("fallback"):
            # Offline heuristic fallback (auth/network errors while a key is present)
            fallback = gen_result["fallback"]
            optimized_text = fallback["text"]
            latency_ms = fallback.get("latency_ms", 0)
            usage = fallback.get("usage", {})
            mode = "offline_fallback"
        elif gen_result.get("status") == "error":
            # Provider returned a hard error with no usable fallback (e.g. a
            # missing API key for an OpenAI/Anthropic-backed request). Gracefully
            # degrade to the offline heuristic optimizer so the request succeeds.
            fb = NvidiaNIMClient()._mock_offline_optimization(augmented_prompt)
            optimized_text = fb["text"]
            latency_ms = fb.get("latency_ms", 0)
            usage = fb.get("usage", {})
            mode = "offline_fallback"
        else:
            raise RuntimeError(gen_result.get("message", "Generation failed."))

        # Calculate compression metrics
        metrics = calculate_compression_metrics(
            raw_input=user_input,
            optimized_prompt=optimized_text,
            actual_api_usage=usage,
            latency_ms=latency_ms
        )

        # Generate Figma 1-Click Prompt
        figma_formatted = self._format_for_figma(optimized_text)

        return {
            "success": True,
            "raw_input": user_input,
            "optimized_prompt": optimized_text,
            "figma_formatted": figma_formatted,
            "metrics": metrics,
            "mode": mode,
            "model_used": gen_result.get("model", model_id),
            "device": device_id,
            "style": style_id,
            "provider": provider_name,
            "notice": gen_result.get("message") if gen_result.get("status") == "warning" else None
        }

    def _build_augmented_prompt(
        self,
        user_input: str,
        device_id: str,
        style_id: str,
        archetype_id: Optional[str],
        custom_components: Optional[list]
    ) -> str:
        constraints = []
        device = DEVICE_PRESETS.get(device_id)
        if device:
            constraints.append(f"Target Device: {device['name']} ({device['frame_token']})")

        style = STYLE_PRESETS.get(style_id)
        if style:
            constraints.append(f"Design Theme: {style['name']} - {style['theme_token']}, Radius={style['radius']}")

        archetype = ARCHETYPE_TEMPLATES.get(archetype_id)
        if archetype:
            constraints.append(f"UI Archetype: {archetype['name']} (Key Elements: {', '.join(archetype['default_components'])})")

        if custom_components:
            clean_components = [c for c in custom_components if c]
            if clean_components:
                constraints.append(f"Required Components: {', '.join(clean_components)}")

        constraint_block = "\n".join([f"- {c}" for c in constraints])
        augmented_prompt = f"USER REQUIREMENT:\n{user_input.strip()}"
        if constraints:
            augmented_prompt += f"\n\nDESIGN CONSTRAINTS & TOKENS:\n{constraint_block}"
        return augmented_prompt

    def optimize_stream(
        self,
        user_input: str,
        device_id: str = "desktop",
        style_id: str = "saas_modern",
        archetype_id: Optional[str] = None,
        custom_components: Optional[list] = None,
        model_id: Optional[str] = None,
        temperature: float = 0.1,
        api_key_override: Optional[str] = None
    ):
        """
        Generator streaming tokens as they arrive from NVIDIA and ultimately a
        single "result" event with the full optimized prompt + metrics. Yields:
          {"type": "token", "text": "<delta>"}
          {"type": "result", ...same shape as optimize()...}
        """
        # Auto-route model if not explicitly specified
        if model_id is None:
            model_id = self.route_model(device_id, style_id, archetype_id)

        active_client = (
            NvidiaNIMClient(api_key=api_key_override)
            if api_key_override
            else self.client
        )
        augmented_prompt = self._build_augmented_prompt(
            user_input=user_input,
            device_id=device_id,
            style_id=style_id,
            archetype_id=archetype_id,
            custom_components=custom_components
        )

        for evt in active_client.generate_stream(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=augmented_prompt,
            model=model_id,
            temperature=temperature
        ):
            if evt.get("type") == "token":
                yield {"type": "token", "text": evt["text"]}
                continue

            if evt.get("type") == "done":
                optimized_text = evt.get("text", "")
                metrics = calculate_compression_metrics(
                    raw_input=user_input,
                    optimized_prompt=optimized_text,
                    actual_api_usage=evt.get("usage", {}),
                    latency_ms=evt.get("latency_ms", 0)
                )
                yield {
                    "type": "result",
                    "success": True,
                    "raw_input": user_input,
                    "optimized_prompt": optimized_text,
                    "figma_formatted": self._format_for_figma(optimized_text),
                    "metrics": metrics,
                    "mode": evt.get("mode", "live"),
                    "model_used": evt.get("model", model_id),
                    "device": device_id,
                    "style": style_id,
                    "notice": evt.get("notice")
                }
                return

    def _format_for_figma(self, prompt_text: str) -> str:
        """
        Formats the bracket-notated prompt into a clean string ready for Figma AI / First Draft.
        """
        lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]
        return " ".join(lines)

    def optimize_responsive(
        self,
        user_input: str,
        style_id: str = "saas_modern",
        archetype_id: Optional[str] = None,
        custom_components: Optional[list] = None,
        model_id: Optional[str] = None,
        temperature: float = 0.1,
        api_key_override: Optional[str] = None,
        variants: list = None
    ) -> Dict[str, Any]:
        """
        Generate responsive variants (desktop, mobile, tablet) in one request.
        Returns optimized prompts for each variant with shared design tokens.
        """
        if variants is None:
            variants = ["desktop", "mobile", "tablet"]

        results = {}
        shared_tokens = None

        for device_id in variants:
            result = self.optimize(
                user_input=user_input,
                device_id=device_id,
                style_id=style_id,
                archetype_id=archetype_id,
                custom_components=custom_components,
                model_id=model_id,
                temperature=temperature,
                api_key_override=api_key_override
            )
            results[device_id] = result

            # Extract shared tokens from first variant
            if shared_tokens is None and "optimized_prompt" in result:
                shared_tokens = self._extract_tokens(result["optimized_prompt"])

        return {
            "success": True,
            "variants": results,
            "shared_tokens": shared_tokens,
            "raw_input": user_input,
            "style": style_id,
            "archetype": archetype_id
        }

    def optimize_batch(
        self,
        requirements: list,
        device_id: str = "desktop",
        style_id: str = "saas_modern",
        model_id: Optional[str] = None,
        temperature: float = 0.1,
        api_key_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process multiple requirements in batch. Each item in the list generates
        a separate optimized prompt. Returns aggregated metrics.
        """
        if not requirements or not isinstance(requirements, list):
            raise ValueError("requirements must be a non-empty list")

        results = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_saved_tokens = 0
        total_latency = 0

        for idx, req in enumerate(requirements):
            if isinstance(req, dict):
                prompt = req.get("prompt", "")
                device = req.get("device", device_id)
                style = req.get("style", style_id)
            else:
                prompt = str(req)
                device = device_id
                style = style_id

            if not prompt.strip():
                continue

            result = self.optimize(
                user_input=prompt,
                device_id=device,
                style_id=style,
                model_id=model_id,
                temperature=temperature,
                api_key_override=api_key_override
            )

            results.append({
                "index": idx,
                "raw_input": prompt,
                "result": result
            })

            metrics = result.get("metrics", {})
            total_input_tokens += metrics.get("equivalent_verbose_tokens", 0)
            total_output_tokens += metrics.get("optimized_prompt_tokens", 0)
            total_saved_tokens += metrics.get("tokens_saved", 0)
            total_latency += metrics.get("latency_ms", 0)

        avg_reduction = (total_saved_tokens / total_input_tokens * 100) if total_input_tokens > 0 else 0

        return {
            "success": True,
            "batch_size": len(results),
            "results": results,
            "aggregated_metrics": {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens_saved": total_saved_tokens,
                "average_reduction_percentage": round(avg_reduction, 1),
                "total_latency_ms": total_latency,
                "average_latency_ms": round(total_latency / len(results), 0) if results else 0
            }
        }

    def refine(
        self,
        existing_prompt: str,
        modification_instruction: str,
        device_id: str = "desktop",
        style_id: str = "saas_modern",
        model_id: Optional[str] = None,
        temperature: float = 0.1,
        api_key_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refine an existing prompt based on modification instruction.
        Examples: "make it darker", "add animations", "increase spacing"
        """
        if not existing_prompt or not existing_prompt.strip():
            raise ValueError("existing_prompt cannot be empty")
        if not modification_instruction or not modification_instruction.strip():
            raise ValueError("modification_instruction cannot be empty")

        # Build refinement prompt
        refinement_prompt = f"""EXISTING PROMPT:
{existing_prompt}

MODIFICATION REQUEST:
{modification_instruction}

Apply the requested modification while preserving the bracket-token structure and all existing components. Only change what's needed to fulfill the modification request."""

        return self.optimize(
            user_input=refinement_prompt,
            device_id=device_id,
            style_id=style_id,
            model_id=model_id,
            temperature=temperature,
            api_key_override=api_key_override
        )

    def _extract_tokens(self, prompt_text: str) -> Dict[str, str]:
        """Extract design tokens section from a prompt for sharing across variants."""
        if "[Tokens:" in prompt_text:
            start = prompt_text.find("[Tokens:")
            end = prompt_text.find("]", start)
            if end > start:
                return {"tokens_section": prompt_text[start:end+1]}
        return {}
