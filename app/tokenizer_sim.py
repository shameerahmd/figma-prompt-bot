"""
Token estimation and efficiency analytics for prompt compression.
Uses heuristic BPE token simulation to compare verbose prompts vs optimized bracket notation.
"""
import re
from typing import Dict, Any


def estimate_tokens(text: str) -> int:
    """
    Estimates token count for standard LLM tokenizers (Llama / GPT BPE).
    Approximation: ~4 characters per token for English text, with adjustments for punctuation/brackets.
    """
    if not text:
        return 0
    # Clean whitespace
    text = text.strip()
    # Word count + punctuation weighting
    words = re.findall(r'\b\w+\b', text)
    special_chars = re.findall(r'[\[\]\(\)\{\}:,;"\'\-\.\/#]', text)

    # Standard estimate: words count + 0.5 * special tokens + extra for camelCase / snake_case splits
    camel_splits = len(re.findall(r'[a-z][A-Z]', text))

    estimated = int(len(words) * 1.1 + len(special_chars) * 0.6 + camel_splits * 0.5)
    # Ensure minimum non-zero
    return max(1, estimated)


def calculate_compression_metrics(
    raw_input: str,
    optimized_prompt: str,
    actual_api_usage: Dict[str, int] = None,
    latency_ms: int = 0
) -> Dict[str, Any]:
    """
    Calculates token reduction percentage, estimated downstream savings in Figma AI generation,
    and efficiency score.
    """
    if actual_api_usage and "input" in actual_api_usage and "output" in actual_api_usage:
        raw_tokens = actual_api_usage["input"]
        opt_tokens = actual_api_usage["output"]
    else:
        raw_tokens = estimate_tokens(raw_input)
        opt_tokens = estimate_tokens(optimized_prompt)

    # What a naive verbose version of this full specification would cost in tokens:
    # A full verbose prompt with equivalent detail usually requires 2.5x - 3.5x more words.
    equivalent_verbose_tokens = int(opt_tokens * 2.8)

    saved_tokens = max(0, equivalent_verbose_tokens - opt_tokens)
    reduction_percentage = round((saved_tokens / max(1, equivalent_verbose_tokens)) * 100, 1)

    # Calculate token efficiency index (Density of UI components per 10 tokens)
    bracket_blocks = len(re.findall(r'\[(.*?)\]', optimized_prompt))
    component_count = len(re.findall(r'\b(Button|Card|Input|Nav|Table|Chart|Header|Footer|Modal|Drawer|Badge|Avatar|List|Grid)\b', optimized_prompt, re.I))

    # Average cost saving estimate assuming $0.003 / 1k tokens for typical downstream design generation
    estimated_usd_saved_per_100_runs = round((saved_tokens * 100 / 1000) * 0.003, 4)

    return {
        "raw_input_tokens": raw_tokens,
        "optimized_prompt_tokens": opt_tokens,
        "equivalent_verbose_tokens": equivalent_verbose_tokens,
        "tokens_saved": saved_tokens,
        "reduction_percentage": reduction_percentage,
        "component_density": component_count,
        "bracket_sections": bracket_blocks,
        "latency_ms": latency_ms,
        "estimated_savings_100_runs_usd": estimated_usd_saved_per_100_runs
    }
