"""
BedrockBackend wraps ChatBedrockConverse.
Agents currently use ChatBedrock directly — after this refactor they use
the BackendChatModel adapter, which calls this backend.
Standardizing on Converse API for better reasoning model support.
"""
import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.backends.base import BackendConfig, ModelBackend, ModelResponse

logger = logging.getLogger(__name__)


class BedrockBackend(ModelBackend):
    def __init__(self, config: BackendConfig):
        super().__init__(config)
        logger.info(
            f"BedrockBackend creating LLM: model={config.model_id}, "
            f"region={config.region}, thinking={config.thinking_mode}"
        )

        kwargs = dict(
            model=config.model_id,
            region_name=config.region,
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

        self._llm = ChatBedrockConverse(**kwargs)

    def invoke(self, messages: list[dict], system_prompt: str = "") -> ModelResponse:
        lc_messages = self._to_langchain(messages, system_prompt)
        response = self._llm.invoke(lc_messages)
        usage = response.usage_metadata or {}
        return ModelResponse(
            content=response.content,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            model_id=self.config.model_id,
            backend="bedrock",
        )

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
