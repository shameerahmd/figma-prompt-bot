"""
Export formatters for different target platforms/use cases.
"""
import json
from typing import Dict, Any


def export_json(result: Dict[str, Any]) -> str:
    """Export full result as pretty-printed JSON."""
    return json.dumps(result, indent=2, ensure_ascii=False)


def export_markdown(result: Dict[str, Any]) -> str:
    """Export as Markdown documentation."""
    md = []
    md.append("# Figma AI Prompt Optimization Result\n")
    md.append(f"**Device:** {result.get('device', 'N/A')}\n")
    md.append(f"**Style:** {result.get('style', 'N/A')}\n")
    md.append(f"**Model:** {result.get('model_used', 'N/A')}\n")
    md.append(f"**Provider:** {result.get('provider', 'nvidia')}\n\n")

    metrics = result.get('metrics', {})
    md.append("## Metrics\n")
    md.append(f"- **Token Reduction:** {metrics.get('reduction_percentage', 0)}%\n")
    md.append(f"- **Tokens Saved:** {metrics.get('tokens_saved', 0)}\n")
    md.append(f"- **Output Size:** {metrics.get('optimized_prompt_tokens', 0)} tokens\n")
    md.append(f"- **Latency:** {metrics.get('latency_ms', 0)} ms\n\n")

    md.append("## Raw Input\n")
    md.append(f"```\n{result.get('raw_input', '')}\n```\n\n")

    md.append("## Optimized Prompt\n")
    md.append(f"```\n{result.get('optimized_prompt', '')}\n```\n\n")

    md.append("## Figma-Formatted Output\n")
    md.append(f"```\n{result.get('figma_formatted', '')}\n```\n")

    return "".join(md)


def export_figma_plugin(result: Dict[str, Any]) -> str:
    """
    Export as Figma Plugin API script (paste into Figma console).
    Generates createFrame/setLayoutMode calls from the prompt structure.
    """
    prompt = result.get('optimized_prompt', '')

    script = []
    script.append("// Figma Plugin Script - Paste into Figma Console (Cmd+Option+J / Ctrl+Shift+J)\n")
    script.append("// This script creates frames based on your optimized prompt\n\n")
    script.append("(function() {\n")
    script.append("  const page = figma.currentPage;\n")
    script.append("  const frame = figma.createFrame();\n")
    script.append("  frame.name = 'Generated Frame';\n\n")

    # Parse device/viewport from prompt
    if "[Frame:" in prompt:
        script.append("  // Frame configuration\n")
        if "Desktop" in prompt or "1440" in prompt:
            script.append("  frame.resize(1440, 900);\n")
        elif "Mobile" in prompt or "375" in prompt:
            script.append("  frame.resize(375, 812);\n")
        elif "Tablet" in prompt or "834" in prompt:
            script.append("  frame.resize(834, 1194);\n")
        else:
            script.append("  frame.resize(1280, 720);\n")

    # Parse layout direction
    if "Vertical" in prompt:
        script.append("  frame.layoutMode = 'VERTICAL';\n")
    elif "Horizontal" in prompt:
        script.append("  frame.layoutMode = 'HORIZONTAL';\n")

    # Parse padding/spacing
    if "padding" in prompt.lower():
        script.append("  frame.paddingLeft = 24;\n")
        script.append("  frame.paddingRight = 24;\n")
        script.append("  frame.paddingTop = 24;\n")
        script.append("  frame.paddingBottom = 24;\n")

    if "gap" in prompt.lower() or "spacing" in prompt.lower():
        script.append("  frame.itemSpacing = 16;\n")

    # Parse background color
    if "#FFFFFF" in prompt:
        script.append("  frame.fills = [{ type: 'SOLID', color: { r: 1, g: 1, b: 1 } }];\n")
    elif "#000000" in prompt or "Dark" in prompt:
        script.append("  frame.fills = [{ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }];\n")

    script.append("\n  // Add to page\n")
    script.append("  page.appendChild(frame);\n")
    script.append("  figma.viewport.scrollAndZoomIntoView([frame]);\n")
    script.append("  figma.closePlugin('Frame created! Add components manually.');\n")
    script.append("})();\n")

    return "".join(script)


def export_plain_text(result: Dict[str, Any]) -> str:
    """Export only the optimized prompt as plain text."""
    return result.get('optimized_prompt', '')
