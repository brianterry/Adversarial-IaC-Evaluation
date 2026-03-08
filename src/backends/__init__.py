"""
Backend abstraction for LLM inference.
Supports Bedrock, DirectAPI (OpenAI-compatible), and SageMaker.
"""
from src.backends.base import BackendConfig, ModelBackend, ModelResponse
from src.backends.bedrock import BedrockBackend
from src.backends.direct_api import DirectAPIBackend
from src.backends.sagemaker import SageMakerBackend


def create_backend(config: BackendConfig, backend_type: str = "bedrock") -> ModelBackend:
    backends = {
        "bedrock": BedrockBackend,
        "direct_api": DirectAPIBackend,
        "sagemaker": SageMakerBackend,
    }
    if backend_type not in backends:
        raise ValueError(
            f"Unknown backend '{backend_type}'. Options: {list(backends)}"
        )
    return backends[backend_type](config)


__all__ = [
    "BackendConfig",
    "ModelBackend",
    "ModelResponse",
    "BedrockBackend",
    "DirectAPIBackend",
    "SageMakerBackend",
    "create_backend",
]
