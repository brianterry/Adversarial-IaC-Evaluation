"""
LLM Response Sanitizer

Handles model-specific output quirks:
- DeepSeek-R1: Strips <think>...</think> reasoning blocks before parsing
- Qwen3-Coder: Strips markdown code fences (```json ... ```) wrapping
- General: Normalizes whitespace, strips BOM, handles empty responses

These are applied AFTER receiving the LLM response and BEFORE any parsing
(JSON extraction, finding detection, etc.).
"""

import re
import logging

logger = logging.getLogger("ResponseSanitizer")


def sanitize_llm_response(response: str, model_id: str = "") -> str:
    """
    Sanitize an LLM response based on the model that produced it.
    
    Args:
        response: Raw LLM response text
        model_id: Bedrock model ID (used to detect model-specific quirks)
    
    Returns:
        Cleaned response text ready for parsing
    """
    if not response:
        return ""
    
    original_len = len(response)
    
    # 1. Strip <think>...</think> blocks (DeepSeek-R1, QwQ, other reasoning models)
    if _needs_think_stripping(response, model_id):
        response = strip_think_blocks(response)
    
    # 2. Strip markdown code fences (Qwen3-Coder, some other code models)
    if _needs_fence_stripping(response, model_id):
        response = strip_markdown_fences(response)
    
    # 3. General cleanup
    response = response.strip()
    
    # 4. Remove BOM if present
    response = response.lstrip('\ufeff')
    
    if len(response) != original_len:
        logger.debug(f"Sanitized response: {original_len} → {len(response)} chars")
    
    return response


def strip_think_blocks(text: str) -> str:
    """
    Remove <think>...</think> blocks from reasoning model output.
    
    DeepSeek-R1 and similar models produce:
        <think>
        Let me analyze this step by step...
        ...internal reasoning...
        </think>
        
        Here is the actual response in JSON format:
        {...}
    
    The <think> block must be removed before JSON parsing.
    """
    # Pattern: <think> ... </think> (including newlines)
    cleaned = re.sub(
        r'<think>.*?</think>\s*',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    
    if cleaned != text:
        logger.info(f"Stripped <think> block ({len(text) - len(cleaned)} chars removed)")
    
    return cleaned.strip()


def strip_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences wrapping JSON output.
    
    Some models (especially code-specialized ones like Qwen3-Coder) wrap
    their JSON output in markdown fences:
    
        ```json
        {"findings": [...]}
        ```
    
    Or sometimes:
        ```
        {"findings": [...]}
        ```
    """
    # Pattern: ```json\n...\n``` or ```\n...\n```
    # Only strip if the ENTIRE response is wrapped in a single fence
    fence_pattern = re.compile(
        r'^\s*```(?:json|JSON|terraform|hcl|yaml)?\s*\n(.*?)\n\s*```\s*$',
        re.DOTALL,
    )
    
    match = fence_pattern.match(text)
    if match:
        cleaned = match.group(1).strip()
        logger.info(f"Stripped markdown fences ({len(text)} → {len(cleaned)} chars)")
        return cleaned
    
    # Also handle multiple fenced blocks — extract content from each
    # This handles responses like: "Here is the result:\n```json\n{...}\n```"
    multi_pattern = re.compile(
        r'```(?:json|JSON|terraform|hcl|yaml)?\s*\n(.*?)\n\s*```',
        re.DOTALL,
    )
    
    blocks = multi_pattern.findall(text)
    if blocks:
        # Return the longest block (most likely the main content)
        longest = max(blocks, key=len)
        if len(longest) > len(text) * 0.3:  # Only if it's a substantial portion
            logger.info(f"Extracted content from markdown fence ({len(longest)} chars)")
            return longest.strip()
    
    return text


def _needs_think_stripping(response: str, model_id: str) -> bool:
    """Check if response contains <think> blocks that need stripping."""
    # Always check for <think> blocks regardless of model ID
    # (some models produce them unexpectedly)
    return '<think>' in response.lower()


def _needs_fence_stripping(response: str, model_id: str) -> bool:
    """Check if response has markdown fences that need stripping."""
    model_lower = model_id.lower()
    
    # Models known to produce fenced output
    fence_models = ['qwen', 'coder', 'codestral', 'starcoder']
    is_fence_model = any(m in model_lower for m in fence_models)
    
    # Also check content — if it starts with ``` it probably needs stripping
    has_fences = response.strip().startswith('```')
    
    return is_fence_model or has_fences
