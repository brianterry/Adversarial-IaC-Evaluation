"""
BedrockBackend wraps ChatBedrockConverse.
Agents currently use ChatBedrock directly — after this refactor they use
the BackendChatModel adapter, which calls this backend.
Standardizing on Converse API for better reasoning model support.
"""
import logging
import re

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.backends.base import BackendConfig, ModelBackend, ModelResponse

logger = logging.getLogger(__name__)

# Matches <think>...</think> or <reasoning>...</reasoning> in plain-text responses
REASONING_TAG_PATTERN = re.compile(
    r"<think>(.*?)</think>|<reasoning>(.*?)</reasoning>",
    re.DOTALL,
)

# Reasoning models (Kimi K2, DeepSeek-R1, Qwen thinking) can take several minutes
READ_TIMEOUT_THINKING = 900  # 15 minutes


class BedrockBackend(ModelBackend):
    def __init__(self, config: BackendConfig):
        super().__init__(config)
        logger.info(
            f"BedrockBackend creating LLM: model={config.model_id}, "
            f"region={config.region}, thinking={config.thinking_mode}"
        )

        kwargs = dict(
            model=config.model_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        if config.thinking_mode:
            kwargs["additional_model_request_fields"] = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": config.thinking_budget_tokens,
                }
            }
            # Reasoning models exceed default 60s timeout; use explicit client with longer timeout
            boto_config = Config(read_timeout=READ_TIMEOUT_THINKING)
            client = boto3.client(
                "bedrock-runtime",
                region_name=config.region,
                config=boto_config,
            )
            kwargs["client"] = client
        else:
            kwargs["region_name"] = config.region

        self._llm = ChatBedrockConverse(**kwargs)

    def invoke(self, messages: list[dict], system_prompt: str = "") -> ModelResponse:
        lc_messages = self._to_langchain(messages, system_prompt)
        response = self._llm.invoke(lc_messages)
        usage = response.usage_metadata or {}
        content, thinking = self._extract_content(response.content)
        return ModelResponse(
            content=content,
            thinking=thinking,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            model_id=self.config.model_id,
            backend="bedrock",
        )

    @staticmethod
    def _extract_content(raw) -> tuple[str, str | None]:
        """Extract text and thinking from Converse API response content.

        Two formats:
        1. List of content blocks (Kimi K2, Qwen3 with thinking_mode=True)
        2. Plain string with <think>/<reasoning> tags (DeepSeek-R1, GPT-OSS)
        """
        if isinstance(raw, str):
            return BedrockBackend._strip_reasoning_tags(raw)
        if not isinstance(raw, list):
            return BedrockBackend._strip_reasoning_tags(str(raw))

        text_parts = []
        thinking_parts = []
        for block in raw:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                btype = block.get("type", "")
                if btype in ("thinking", "reasoning", "reasoningContent", "reasoning_content"):
                    inner = block.get("reasoning_content") or block.get("reasoningContent") or {}
                    thinking_parts.append(inner.get("text", "") if isinstance(inner, dict) else str(inner))
                elif "text" in block:
                    text_parts.append(block["text"])

        content = "\n".join(text_parts) if text_parts else str(raw)
        thinking = "\n".join(thinking_parts) if thinking_parts else None
        return content, thinking

    @staticmethod
    def _strip_reasoning_tags(text: str) -> tuple[str, str | None]:
        """Strip <think> or <reasoning> tags from plain-text responses."""
        match = REASONING_TAG_PATTERN.search(text)
        if match:
            thinking = (match.group(1) or match.group(2) or "").strip()
            cleaned = REASONING_TAG_PATTERN.sub("", text).strip()
            return cleaned, thinking
        return text, None

    def _to_langchain(self, messages, system_prompt):
        result = []
        if system_prompt:
            result.append(SystemMessage(content=system_prompt))
        for m in messages:
            if m["role"] == "user":
                result.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                result.append(AIMessage(content=m["content"]))
        return result
