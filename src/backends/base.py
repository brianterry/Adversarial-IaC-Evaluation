"""
Abstract model backend interface.
Backends are SYNC. The adapter handles async via asyncio.to_thread.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackendConfig:
    model_id: str
    region: str = "us-east-1"
    temperature: float = 0.7
    max_tokens: int = 4096
    thinking_mode: bool = False
    thinking_budget_tokens: int = 8000
    extra: dict = field(default_factory=dict)  # field() avoids mutable default bug


@dataclass
class ModelResponse:
    content: str
    thinking: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    model_id: str = ""
    backend: str = ""


class ModelBackend(ABC):
    def __init__(self, config: BackendConfig):
        self.config = config

    @abstractmethod
    def invoke(self, messages: list[dict], system_prompt: str = "") -> ModelResponse:
        """
        Sync invocation.
        messages: [{"role": "user"/"assistant", "content": str}]
        system_prompt: extracted separately — do not include in messages list.
        """
        ...

    @property
    def model_id(self) -> str:
        return self.config.model_id

    @property
    def supports_thinking(self) -> bool:
        return False
