"""
Prompt Optimization Engine for Figma AI.
Coordinates system instructions, user constraints, token reduction, and NVIDIA LLM execution.
"""
from typing import Dict, Any, Optional
from app.nvidia_client import NvidiaNIMClient
from app.presets import DEVICE_PRESETS, STYLE_PRESETS, ARCHETYPE_TEMPLATES
from app.tokenizer_sim import calculate_compression_metrics


SYSTEM_PROMPT = """You are a Figma AI UI/UX Prompt Compressor and Design Architect.
Your task is to convert raw, messy, or conversational user requirements into ultra-dense, token-efficient declarative prompts optimized for Figma AI.

### CORE OBJECTIVES:
1. Strip all conversational filler, pleasantries, and redundant adjectives.
2. Structure output using declarative bracket-notation tokens: [Category: Key(Value)].
3. Apply standard UI/UX taxonomy (Atomic Design, Auto Layout, standard design systems).
4. Specify visual hierarchy: Frame -> Header -> Main/Hero -> Content Sections -> Footer/Sticky CTA.
5. Keep the total output compact while maximizing structural fidelity.

### SYNTAX GRAMMAR:
- [Frame: <Device/Resolution>, <Background/Theme>]
- [Layout: <Auto-layout direction>, <Padding/Spacing in 4/8px grid>, <Alignment>]
- [Header: <Components>]
- [Hero / Section: <Components with states, badges, text>]
- [Form / Inputs: <InputType(Placeholder/Label)>]
- [Controls: <Chips, Toggles, Selectors>]
- [Footer / Action: <Buttons, Sticky Bars, Links>]
- [Tokens: <Color accents, Border radius, Typography weight>]

### RULES:
- Never include conversational markdown, greetings, or explanations.
- Output ONLY the bracketed prompt block.
- Use explicit component nomenclature: Breadcrumbs, SegmentedControl, AvatarGroup, MetricCard, DataGrid, Toast, BottomSheet, PillTag.
- Enforce layout clarity: indicate auto-layout direction (Vertical/Horizontal) and nesting.
"""


class PromptOptimizationEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.client = NvidiaNIMClient(api_key=api_key)

    def optimize(
        self,
        user_input: str,
        device_id: Optional[str] = "desktop",
        style_id: Optional[str] = "saas_modern",
        archetype_id: Optional[str] = None,
        custom_components: Optional[list] = None,
        model_id: Optional[str] = "meta/llama-3.1-8b-instruct",
        temperature: float = 0.1,
        api_key_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes prompt compression and optimization.
        """
        if not user_input or not user_input.strip():
            raise ValueError("User prompt cannot be empty.")

        # If a temporary API key is provided per-request from web UI
        if api_key_override:
            active_client = NvidiaNIMClient(api_key=api_key_override)
        else:
            active_client = self.client

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
        elif "fallback" in gen_result:
            # Offline heuristic fallback (auth/network errors while a key is present)
            fallback = gen_result["fallback"]
            optimized_text = fallback["text"]
            latency_ms = fallback.get("latency_ms", 0)
            usage = fallback.get("usage", {})
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
            "notice": gen_result.get("message") if gen_result.get("status") == "warning" else None
        }

    def _format_for_figma(self, prompt_text: str) -> str:
        """
        Formats the bracket-notated prompt into a clean string ready for Figma AI / First Draft.
        """
        lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]
        return " ".join(lines)
