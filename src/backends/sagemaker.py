"""
SageMaker backend — invokes a SageMaker endpoint serving OpenAI-compatible API.

Supported containers: LMI vLLM DLC, TGI, LMI with OpenAI mode.

NOTE: The extra_body field in the payload is passed as-is to the container.
Whether this field is recognized depends on the container's API schema.
Validate payload structure against the specific DLC's API spec:
https://docs.aws.amazon.com/sagemaker/latest/dg/large-model-inference-vllm.html

BackendConfig.extra:
    endpoint_name (str): SageMaker endpoint name — required
    content_type (str): default "application/json"
"""
import json
import re
import boto3
from src.backends.base import BackendConfig, ModelBackend, ModelResponse

THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)


class SageMakerBackend(ModelBackend):
    def __init__(self, config: BackendConfig):
        super().__init__(config)
        self._endpoint_name = config.extra.get("endpoint_name")
        if not self._endpoint_name:
            raise ValueError(
                "SageMakerBackend requires extra={'endpoint_name': '<name>'}"
            )
        self._content_type = config.extra.get("content_type", "application/json")
        self._runtime = boto3.client(
            "sagemaker-runtime", region_name=config.region
        )

    @property
    def supports_thinking(self) -> bool:
        return True

    def invoke(self, messages: list[dict], system_prompt: str = "") -> ModelResponse:
        payload = self._build_payload(messages, system_prompt)
        response = self._runtime.invoke_endpoint(
            EndpointName=self._endpoint_name,
            ContentType=self._content_type,
            Body=json.dumps(payload),
        )
        result = json.loads(response["Body"].read().decode())
        raw = result["choices"][0]["message"]["content"]
        thinking, content = self._extract_thinking(raw)
        usage = result.get("usage", {})
        return ModelResponse(
            content=content,
            thinking=thinking,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model_id=self.config.model_id,
            backend="sagemaker",
        )

    def _build_payload(self, messages, system_prompt):
        """
        Builds OpenAI-compatible payload.
        The extra_body field structure may need adjustment depending on
        the LMI/vLLM DLC version — validate against container API docs.
        """
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        formatted.extend(messages)
        payload = {
            "model": self.config.model_id,
            "messages": formatted,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if self.config.thinking_mode:
            # Validate this structure against the DLC's API before using
            payload["extra_body"] = {
                "enable_thinking": True,
                "thinking_budget": self.config.thinking_budget_tokens,
            }
        return payload

    def _extract_thinking(self, raw: str) -> tuple[str | None, str]:
        match = THINK_PATTERN.search(raw)
        if match:
            return match.group(1).strip(), THINK_PATTERN.sub("", raw).strip()
        return None, raw.strip()
