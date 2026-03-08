"""
DirectAPI backend — OpenAI-compatible API endpoint.

PRIMARY USE: Alibaba DashScope for Qwen3.5-397B-A17B.

VERIFY BEFORE RUNNING (see verification steps at end of prompt):
1. Correct model identifier from DashScope
2. Thinking mode parameter names

BackendConfig.extra:
    base_url (str): API endpoint URL — required
    api_key_env (str): env var name for API key
                      Default: OPENAI_API_KEY
                      Use "NONE" for local no-auth endpoints
"""
import os
import re
from openai import OpenAI
from src.backends.base import BackendConfig, ModelBackend, ModelResponse

THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)


class DirectAPIBackend(ModelBackend):
    def __init__(self, config: BackendConfig):
        super().__init__(config)
        base_url = config.extra.get("base_url")
        if not base_url:
            raise ValueError(
                "DirectAPIBackend requires extra={'base_url': '<endpoint_url>'}"
            )
        api_key_env = config.extra.get("api_key_env", "OPENAI_API_KEY")

        if api_key_env == "NONE":
            api_key = "sk-placeholder"
        else:
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise ValueError(
                    f"API key not found. Set environment variable: {api_key_env}"
                )

        self._client = OpenAI(base_url=base_url, api_key=api_key)

    @property
    def supports_thinking(self) -> bool:
        return True

    def invoke(self, messages: list[dict], system_prompt: str = "") -> ModelResponse:
        formatted = self._format(messages, system_prompt)
        extra_body = {}
        if self.config.thinking_mode:
            # Verify these param names against DashScope docs before running.
            # Ref: https://help.aliyun.com/zh/model-studio/qwen-thinking-mode
            extra_body = {
                "enable_thinking": True,
                "thinking_budget": self.config.thinking_budget_tokens,
            }

        response = self._client.chat.completions.create(
            model=self.config.model_id,
            messages=formatted,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            **({"extra_body": extra_body} if extra_body else {}),
        )

        raw = response.choices[0].message.content or ""
        thinking, content = self._extract_thinking(raw)

        return ModelResponse(
            content=content,
            thinking=thinking,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model_id=self.config.model_id,
            backend="direct_api",
        )

    def _format(self, messages, system_prompt):
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.extend(messages)
        return result

    def _extract_thinking(self, raw: str) -> tuple[str | None, str]:
        """
        Extract <think>...</think> block.
        Backend owns think-tag extraction.
        response_sanitizer.py handles markdown fences separately — no overlap.
        """
        match = THINK_PATTERN.search(raw)
        if match:
            return match.group(1).strip(), THINK_PATTERN.sub("", raw).strip()
        return None, raw.strip()
