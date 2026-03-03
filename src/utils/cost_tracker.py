"""
Cost Tracker for Adversarial IaC Games

Estimates per-game cost based on model pricing and approximate token counts.
Token counts are estimated from character counts (1 token ≈ 4 characters for English).

Pricing is based on Amazon Bedrock on-demand pricing as of 2025.
Update PRICING dict when prices change.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("CostTracker")

# Bedrock on-demand pricing per 1K tokens (input/output)
# Source: https://aws.amazon.com/bedrock/pricing/
PRICING: Dict[str, Dict[str, float]] = {
    # Anthropic
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku": {"input": 0.001, "output": 0.005},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    # Amazon Nova
    "nova-premier": {"input": 0.0025, "output": 0.0125},
    "nova-pro": {"input": 0.0008, "output": 0.0032},
    "nova-lite": {"input": 0.00006, "output": 0.00024},
    "nova-micro": {"input": 0.000035, "output": 0.00014},
    # Meta Llama
    "llama-3.3-70b": {"input": 0.00072, "output": 0.00072},
    "llama-3.1-70b": {"input": 0.00072, "output": 0.00072},
    "llama-3.1-8b": {"input": 0.00022, "output": 0.00022},
    # DeepSeek
    "deepseek-r1": {"input": 0.00135, "output": 0.00540},
    # Qwen
    "qwen3-coder": {"input": 0.00020, "output": 0.00060},
    # Mistral
    "mistral-large": {"input": 0.004, "output": 0.012},
    "mistral-small": {"input": 0.001, "output": 0.003},
    # Default fallback
    "default": {"input": 0.002, "output": 0.008},
}

# Approximate characters per token
CHARS_PER_TOKEN = 4


def _identify_model(model_id: str) -> str:
    """Map a full model ID to a pricing key."""
    model_lower = model_id.lower()
    for key in PRICING:
        if key != "default" and key.replace("-", "").replace(".", "") in model_lower.replace("-", "").replace(".", ""):
            return key
    return "default"


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_game_cost(
    red_model: str,
    blue_model: str,
    red_output_chars: int = 0,
    blue_output_chars: int = 0,
    red_input_chars: int = 0,
    blue_input_chars: int = 0,
    judge_model: Optional[str] = None,
    judge_chars: int = 0,
) -> Dict[str, Any]:
    """
    Estimate the cost of a single game.
    
    Args:
        red_model: Red Team model ID
        blue_model: Blue Team model ID
        red_output_chars: Total characters in Red Team LLM output
        blue_output_chars: Total characters in Blue Team LLM output
        red_input_chars: Total characters in Red Team prompts
        blue_input_chars: Total characters in Blue Team prompts
        judge_model: Judge model ID (if LLM judge used)
        judge_chars: Total characters in judge LLM calls
    
    Returns:
        Cost breakdown dict with total_usd
    """
    red_key = _identify_model(red_model)
    blue_key = _identify_model(blue_model)
    
    red_pricing = PRICING.get(red_key, PRICING["default"])
    blue_pricing = PRICING.get(blue_key, PRICING["default"])
    
    # Estimate tokens
    red_input_tokens = estimate_tokens("x" * red_input_chars) if red_input_chars else 2000  # Default estimate
    red_output_tokens = estimate_tokens("x" * red_output_chars) if red_output_chars else 3000
    blue_input_tokens = estimate_tokens("x" * blue_input_chars) if blue_input_chars else 2000
    blue_output_tokens = estimate_tokens("x" * blue_output_chars) if blue_output_chars else 2000
    
    # Red Team cost (typically 2 LLM calls: selection + generation)
    red_cost = (
        (red_input_tokens / 1000) * red_pricing["input"] +
        (red_output_tokens / 1000) * red_pricing["output"]
    ) * 2  # Two calls
    
    # Blue Team cost (1-2 calls depending on strategy)
    blue_cost = (
        (blue_input_tokens / 1000) * blue_pricing["input"] +
        (blue_output_tokens / 1000) * blue_pricing["output"]
    )
    
    # Judge cost (if LLM judge)
    judge_cost = 0.0
    if judge_model:
        judge_key = _identify_model(judge_model)
        judge_pricing = PRICING.get(judge_key, PRICING["default"])
        judge_tokens = estimate_tokens("x" * judge_chars) if judge_chars else 1000
        judge_cost = (judge_tokens / 1000) * (judge_pricing["input"] + judge_pricing["output"])
    
    total = red_cost + blue_cost + judge_cost
    
    return {
        "red_cost_usd": round(red_cost, 4),
        "blue_cost_usd": round(blue_cost, 4),
        "judge_cost_usd": round(judge_cost, 4),
        "total_usd": round(total, 4),
        "red_model": red_key,
        "blue_model": blue_key,
        "estimated_tokens": {
            "red_input": red_input_tokens * 2,
            "red_output": red_output_tokens * 2,
            "blue_input": blue_input_tokens,
            "blue_output": blue_output_tokens,
        },
    }
