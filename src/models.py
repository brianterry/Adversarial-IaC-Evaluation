"""
Model Registry for Adversarial IaC Evaluation Framework

Organizes AWS Bedrock models by capability tier for research comparisons.
Based on: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
"""

from typing import Dict, List, Optional, Tuple


# Model Registry organized by capability tier
MODEL_REGISTRY: Dict[str, Dict[str, str]] = {
    # Tier 1: Frontier Models (best quality, highest cost)
    "frontier": {
        "claude-3.5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "nova-premier": "us.amazon.nova-premier-v1:0",
        "llama-3.3-70b": "us.meta.llama3-3-70b-instruct-v1:0",
        "mistral-large-3": "mistral.mistral-large-3-675b-instruct",
    },
    
    # Tier 2: Strong Models (good balance of quality and cost)
    "strong": {
        "claude-3.5-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "nova-pro": "amazon.nova-pro-v1:0",
        "llama-3.1-70b": "us.meta.llama3-1-70b-instruct-v1:0",
        "mistral-large": "mistral.mistral-large-2407-v1:0",
        "command-r-plus": "cohere.command-r-plus-v1:0",
    },
    
    # Tier 3: Efficient Models (fast and cheap, good for development)
    "efficient": {
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "nova-lite": "amazon.nova-lite-v1:0",
        "nova-micro": "amazon.nova-micro-v1:0",
        "llama-3.1-8b": "us.meta.llama3-1-8b-instruct-v1:0",
        "mistral-small": "mistral.mistral-small-2402-v1:0",
        "ministral-8b": "mistral.ministral-3-8b-instruct",
    },
    
    # Tier 4: Specialized/Experimental Models
    "specialized": {
        "deepseek-r1": "us.deepseek.r1-v1:0",
        "qwen3-coder": "qwen.qwen3-coder-30b-a3b-v1:0",
        "jamba-1.5-large": "ai21.jamba-1-5-large-v1:0",
        "jamba-1.5-mini": "ai21.jamba-1-5-mini-v1:0",
        "command-r": "cohere.command-r-v1:0",
    },
}

# Tier metadata for display
TIER_INFO = {
    "frontier": {
        "name": "Frontier",
        "emoji": "🏆",
        "description": "Best quality, highest cost - for final experiments",
    },
    "strong": {
        "name": "Strong", 
        "emoji": "💪",
        "description": "Good balance of quality and cost - recommended",
    },
    "efficient": {
        "name": "Efficient",
        "emoji": "⚡",
        "description": "Fast and cheap - for development and testing",
    },
    "specialized": {
        "name": "Specialized",
        "emoji": "🔬",
        "description": "Experimental or specialized models",
    },
}

# Default models for quick selection
DEFAULT_MODELS = {
    "recommended": ("claude-3.5-sonnet", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    "fast": ("claude-3.5-haiku", "anthropic.claude-3-5-haiku-20241022-v1:0"),
    "cheap": ("nova-lite", "amazon.nova-lite-v1:0"),
}


def get_model_id(model_name: str) -> Optional[str]:
    """
    Get the full Bedrock model ID from a short name.
    
    Args:
        model_name: Short model name (e.g., "claude-3.5-sonnet") or full ID
        
    Returns:
        Full Bedrock model ID, or the input if already a full ID
    """
    # Check if it's already a full model ID
    if "." in model_name and (":" in model_name or "-v" in model_name):
        return model_name
    
    # Search through registry
    for tier_models in MODEL_REGISTRY.values():
        if model_name in tier_models:
            return tier_models[model_name]
    
    # Return as-is (might be a custom/new model ID)
    return model_name


def get_model_tier(model_name: str) -> Optional[str]:
    """Get the tier of a model by its short name."""
    for tier, models in MODEL_REGISTRY.items():
        if model_name in models:
            return tier
    return None


def list_models_by_tier(tier: str) -> Dict[str, str]:
    """Get all models in a specific tier."""
    return MODEL_REGISTRY.get(tier, {})


def list_all_models() -> List[Tuple[str, str, str]]:
    """
    List all models with their tier and full ID.
    
    Returns:
        List of (short_name, tier, full_id) tuples
    """
    result = []
    for tier, models in MODEL_REGISTRY.items():
        for short_name, full_id in models.items():
            result.append((short_name, tier, full_id))
    return result


def get_model_choices_for_cli() -> List[str]:
    """Get model short names for CLI choices."""
    choices = []
    for models in MODEL_REGISTRY.values():
        choices.extend(models.keys())
    return sorted(choices)


def format_model_for_display(short_name: str) -> str:
    """Format a model name for user-friendly display."""
    tier = get_model_tier(short_name)
    if tier:
        emoji = TIER_INFO[tier]["emoji"]
        return f"{emoji} {short_name}"
    return short_name


def get_interactive_model_choices() -> List[Tuple[str, str]]:
    """
    Get model choices formatted for interactive selection.
    
    Returns:
        List of (display_name, model_id) tuples organized by tier
    """
    choices = []
    
    for tier, info in TIER_INFO.items():
        models = MODEL_REGISTRY.get(tier, {})
        for short_name, full_id in models.items():
            display = f"{info['emoji']} {short_name} ({info['name']})"
            choices.append((display, full_id))
    
    return choices
