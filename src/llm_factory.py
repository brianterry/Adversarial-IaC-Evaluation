"""
LLM Factory - Creates LLM instances from multiple providers.

Supports:
- Amazon Bedrock (Claude, Nova, Llama, Mistral)
- OpenAI (GPT-4, GPT-4 Turbo, GPT-4o)
- Google (Gemini Pro, Gemini 1.5)

This enables multi-provider consensus judging for stronger inter-rater reliability.
"""

import os
import logging
from typing import Optional, Tuple
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger("LLMFactory")


# Provider detection patterns
OPENAI_PATTERNS = ["gpt-4", "gpt-3.5", "o1-", "chatgpt"]
GOOGLE_PATTERNS = ["gemini", "palm"]
BEDROCK_PATTERNS = ["claude", "nova", "llama", "mistral", "titan", "cohere", "ai21", "amazon", "anthropic", "meta"]


def detect_provider(model_id: str) -> str:
    """
    Detect the provider from a model ID.
    
    Args:
        model_id: Model identifier (e.g., "gpt-4", "gemini-pro", "claude-3.5-sonnet")
        
    Returns:
        Provider name: "openai", "google", or "bedrock"
    """
    model_lower = model_id.lower()
    
    # Check OpenAI patterns
    if any(p in model_lower for p in OPENAI_PATTERNS):
        return "openai"
    
    # Check Google patterns
    if any(p in model_lower for p in GOOGLE_PATTERNS):
        return "google"
    
    # Default to Bedrock (covers Claude, Nova, Llama, Mistral, etc.)
    return "bedrock"


def create_llm(
    model_id: str,
    provider: Optional[str] = None,
    region: str = "us-east-1",
    temperature: float = 0.0,
    fallback_models: Optional[list] = None,
    backend_type: str = "bedrock",
    backend_extra: Optional[dict] = None,
) -> Tuple[BaseChatModel, str]:
    """
    Create an LLM instance from the appropriate provider.
    
    Includes automatic fallback: if the primary model fails (access errors,
    legacy gating, inference profile issues), tries fallback models in order.
    
    Args:
        model_id: Model identifier
        provider: Optional explicit provider ("openai", "google", "bedrock")
                  If not specified, auto-detected from model_id
        region: AWS region for Bedrock models
        temperature: Temperature for generation
        fallback_models: Optional list of fallback model IDs to try on failure
        backend_type: "bedrock", "direct_api", or "sagemaker" — defaults preserve existing behavior
        backend_extra: Extra config for non-Bedrock backends (base_url, endpoint_name, etc.)
        
    Returns:
        Tuple of (LLM instance, short display name)
    """
    # Non-Bedrock backends routed through abstraction layer
    if backend_type and backend_type != "bedrock":
        from src.backends import create_backend, BackendConfig
        from src.backends.adapter import BackendChatModel
        config = BackendConfig(
            model_id=model_id,
            region=region,
            temperature=temperature,
            extra=backend_extra or {},
        )
        llm = BackendChatModel(create_backend(config, backend_type))
        return llm, model_id

    # Auto-detect provider if not specified
    if provider is None:
        provider = detect_provider(model_id)
    
    provider = provider.lower()
    
    try:
        if provider == "openai":
            return _create_openai_llm(model_id, temperature)
        elif provider == "google":
            return _create_google_llm(model_id, temperature)
        else:  # bedrock
            return _create_bedrock_llm(model_id, region, temperature)
    except Exception as primary_error:
        if not fallback_models:
            raise
        
        logger.warning(f"Primary model {model_id} failed: {primary_error}")
        
        for fallback_id in fallback_models:
            try:
                logger.info(f"Trying fallback model: {fallback_id}")
                fallback_provider = detect_provider(fallback_id)
                if fallback_provider == "openai":
                    return _create_openai_llm(fallback_id, temperature)
                elif fallback_provider == "google":
                    return _create_google_llm(fallback_id, temperature)
                else:
                    return _create_bedrock_llm(fallback_id, region, temperature)
            except Exception as fallback_error:
                logger.warning(f"Fallback {fallback_id} also failed: {fallback_error}")
                continue
        
        # All fallbacks exhausted
        raise RuntimeError(
            f"Primary model {model_id} and all fallbacks {fallback_models} failed. "
            f"Primary error: {primary_error}"
        )


def _create_openai_llm(model_id: str, temperature: float) -> Tuple[BaseChatModel, str]:
    """Create OpenAI LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai not installed. Run: pip install langchain-openai"
        )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Add it to your .env file or export it."
        )
    
    # Normalize model ID
    model_name = model_id
    if not model_id.startswith("gpt-"):
        # Handle short names
        model_map = {
            "gpt4": "gpt-4",
            "gpt4-turbo": "gpt-4-turbo",
            "gpt4o": "gpt-4o",
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4o": "gpt-4o",
            "o1-preview": "o1-preview",
            "o1-mini": "o1-mini",
        }
        model_name = model_map.get(model_id.lower(), model_id)
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
    )
    
    # Create short display name
    short_name = model_name.replace("gpt-", "").replace("-", "")
    logger.info(f"Created OpenAI LLM: {model_name}")
    
    return llm, f"openai-{short_name}"


def _create_google_llm(model_id: str, temperature: float) -> Tuple[BaseChatModel, str]:
    """Create Google Gemini LLM instance."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai not installed. Run: pip install langchain-google-genai"
        )
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Add it to your .env file or export it."
        )
    
    # Normalize model ID
    model_name = model_id
    model_map = {
        "gemini": "gemini-pro",
        "gemini-pro": "gemini-pro",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-1.5-flash": "gemini-1.5-flash",
        "gemini-2.0-flash": "gemini-2.0-flash-exp",
    }
    model_name = model_map.get(model_id.lower(), model_id)
    
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
    )
    
    # Create short display name
    short_name = model_name.replace("gemini-", "").replace("-", "")
    logger.info(f"Created Google LLM: {model_name}")
    
    return llm, f"google-{short_name}"


def _create_bedrock_llm(model_id: str, region: str, temperature: float) -> Tuple[BaseChatModel, str]:
    """Create AWS Bedrock LLM instance."""
    try:
        from langchain_aws import ChatBedrockConverse
    except ImportError:
        raise ImportError(
            "langchain-aws not installed. Run: pip install langchain-aws"
        )
    
    # Import model registry for short name resolution
    from src.models import get_model_id
    
    # Resolve short name to full Bedrock model ID
    full_model_id = get_model_id(model_id)
    
    from botocore.config import Config as BotoConfig

    llm = ChatBedrockConverse(
        model=full_model_id,
        region_name=region,
        temperature=temperature,
        config=BotoConfig(read_timeout=600),
    )
    
    # Create short display name
    short_name = model_id.split("/")[-1].split(":")[0] if "/" in model_id else model_id
    short_name = short_name.replace(".", "-")
    logger.info(f"Created Bedrock LLM: {full_model_id}")
    
    return llm, f"bedrock-{short_name}"


def create_consensus_llms(
    model_specs: list,
    region: str = "us-east-1",
) -> list:
    """
    Create multiple LLMs for consensus judging.
    
    Args:
        model_specs: List of model specifications. Each can be:
            - Simple string: "gpt-4" (provider auto-detected)
            - Provider prefix: "openai:gpt-4", "google:gemini-pro", "bedrock:claude-3.5-sonnet"
        region: AWS region for Bedrock models
        
    Returns:
        List of (display_name, llm) tuples
    """
    consensus_llms = []
    
    for spec in model_specs:
        spec = spec.strip()
        
        # Check for explicit provider prefix
        if ":" in spec:
            provider, model_id = spec.split(":", 1)
        else:
            provider = None
            model_id = spec
        
        try:
            llm, display_name = create_llm(
                model_id=model_id,
                provider=provider,
                region=region,
            )
            consensus_llms.append((display_name, llm))
        except Exception as e:
            logger.error(f"Failed to create LLM for {spec}: {e}")
            raise
    
    return consensus_llms


def validate_api_keys(model_specs: list) -> dict:
    """
    Check which API keys are needed and available.
    
    Args:
        model_specs: List of model specifications
        
    Returns:
        Dict with "missing" and "available" keys
    """
    needed_providers = set()
    
    for spec in model_specs:
        spec = spec.strip()
        if ":" in spec:
            provider, _ = spec.split(":", 1)
        else:
            provider = detect_provider(spec)
        needed_providers.add(provider.lower())
    
    missing = []
    available = []
    
    if "openai" in needed_providers:
        if os.getenv("OPENAI_API_KEY"):
            available.append("openai")
        else:
            missing.append("OPENAI_API_KEY")
    
    if "google" in needed_providers:
        if os.getenv("GOOGLE_API_KEY"):
            available.append("google")
        else:
            missing.append("GOOGLE_API_KEY")
    
    if "bedrock" in needed_providers:
        # Bedrock uses AWS credentials, check if boto3 can authenticate
        try:
            import boto3
            sts = boto3.client("sts")
            sts.get_caller_identity()
            available.append("bedrock")
        except Exception:
            missing.append("AWS credentials (for Bedrock)")
    
    return {"missing": missing, "available": available}
