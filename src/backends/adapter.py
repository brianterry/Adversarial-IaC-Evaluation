"""
BackendChatModel wraps any ModelBackend as a LangChain BaseChatModel.
Agents call `await self.llm.ainvoke(messages)` — unchanged.
The adapter converts LangChain messages to backend format and
bridges async callers to sync backends via asyncio.to_thread.
"""
import asyncio
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from src.backends.base import ModelBackend


class BackendChatModel(BaseChatModel):
    _backend: ModelBackend

    def __init__(self, backend: ModelBackend, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "_backend", backend)

    @property
    def _llm_type(self) -> str:
        return f"backend-{self._backend.config.model_id}"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        """Sync path — used when agents call invoke() directly."""
        converted, system_prompt = self._convert_messages(messages)
        response = self._backend.invoke(converted, system_prompt)
        return self._to_chat_result(response)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Async path — used when agents call await llm.ainvoke().
        Wraps sync backend.invoke() in asyncio.to_thread so we don't
        block the event loop.
        """
        converted, system_prompt = self._convert_messages(messages)
        response = await asyncio.to_thread(
            self._backend.invoke, converted, system_prompt
        )
        return self._to_chat_result(response)

    def _to_chat_result(self, response) -> ChatResult:
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=response.content))],
            llm_output={
                "thinking": response.thinking,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "backend": response.backend,
            },
        )

    def _convert_messages(
        self, messages: List[BaseMessage]
    ) -> tuple[list[dict], str]:
        system_prompt = ""
        converted = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
        return converted, system_prompt
