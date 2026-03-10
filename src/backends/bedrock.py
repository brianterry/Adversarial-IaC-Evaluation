"""
BedrockBackend wraps ChatBedrockConverse.
Agents currently use ChatBedrock directly — after this refactor they use
the BackendChatModel adapter, which calls this backend.
Standardizing on Converse API for better reasoning model support.
"""
import logging

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.backends.base import BackendConfig, ModelBackend, ModelResponse

logger = logging.getLogger(__name__)

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

        Thinking models (Kimi K2, DeepSeek-R1, Qwen3) return a list of
        content blocks rather than a plain string. Separate reasoning
        blocks from text so downstream consumers always get a clean string.
        """
        if isinstance(raw, str):
            return raw, None
        if not isinstance(raw, list):
            return str(raw), None

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
