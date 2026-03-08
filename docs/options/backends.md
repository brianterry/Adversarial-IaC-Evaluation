# Models & Backends

The framework supports multiple LLM backends for Red and Blue teams.

## Backend Types

| Backend | Use Case |
|---------|----------|
| `bedrock` | AWS Bedrock (default) |
| `direct_api` | OpenAI-compatible APIs (DashScope, OpenAI, etc.) |
| `sagemaker` | SageMaker endpoints |

## Bedrock (Default)

Uses AWS Bedrock. Requires AWS credentials and model access.

```bash
adversarial-iac game -s "Create S3 bucket" --blue-model claude-3.5-haiku
```

## Direct API (OpenAI-Compatible)

For DashScope, OpenAI, or any OpenAI-compatible endpoint. Use `--blue-backend-extra` with JSON:

```bash
adversarial-iac game -s "Create S3 bucket" \
  --blue-backend-type direct_api \
  --blue-model qwen3.5-plus \
  --blue-backend-extra '{"base_url":"https://dashscope.aliyuncs.com/compatible-mode/v1","api_key_env":"DASHSCOPE_API_KEY"}'
```

Common `backend_extra` keys:

| Key | Description |
|-----|-------------|
| `base_url` | API base URL (required for direct_api) |
| `api_key_env` | Environment variable name for API key |

Set the API key before running:

```bash
export DASHSCOPE_API_KEY=sk-...
adversarial-iac game ...
```

## SageMaker

For self-hosted models on SageMaker:

```bash
adversarial-iac game -s "Create S3 bucket" \
  --blue-backend-type sagemaker \
  --blue-model my-endpoint \
  --blue-backend-extra '{"endpoint_name":"my-llm-endpoint"}'
```

## Thinking Mode

For reasoning models (DeepSeek-R1, Qwen3.5, etc.) that support extended thinking:

```bash
adversarial-iac game -s "Create S3 bucket" --blue-thinking-mode
```

Enables `<think>` block extraction and passes thinking budget to the model.

## Red vs Blue

Backend options apply separately to each team:

```bash
adversarial-iac game -s "Create S3 bucket" \
  --red-model claude-3-5-sonnet \
  --blue-backend-type direct_api \
  --blue-model qwen3.5-plus \
  --blue-backend-extra '{"base_url":"...","api_key_env":"DASHSCOPE_API_KEY"}'
```
