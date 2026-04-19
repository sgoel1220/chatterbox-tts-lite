"""OpenRouter model pricing lookup (cents per 1M tokens)."""

from __future__ import annotations

# (input_cents_per_1M, output_cents_per_1M)
_PRICING: dict[str, tuple[int, int]] = {
    "meta-llama/llama-3.1-8b-instruct": (6, 6),
    "meta-llama/llama-3.3-70b-instruct": (57, 57),
    "anthropic/claude-3.5-sonnet": (300, 1500),
    "anthropic/claude-3-haiku": (25, 125),
    "openai/gpt-4o": (250, 1000),
    "openai/gpt-4o-mini": (15, 60),
}


def calculate_cost_cents(model: str, input_tokens: int, output_tokens: int) -> int:
    """Return estimated cost in cents for one LLM call.

    Returns 0 for unknown models (no pricing data).
    """
    in_price, out_price = _PRICING.get(model, (0, 0))
    return (in_price * input_tokens + out_price * output_tokens) // 1_000_000
