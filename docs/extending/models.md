# Models

20+ models via Bedrock, plus Direct API and SageMaker for non-Bedrock models.

## Browse

```bash
adversarial-iac models
adversarial-iac models --tier frontier
```

## Tiered Registry (Bedrock)

| Tier | Examples |
|------|----------|
| frontier | claude-3.5-sonnet, nova-premier, llama-3.3-70b |
| strong | claude-3.5-haiku, nova-pro, mistral-large |
| efficient | nova-lite, llama-3.1-8b, mistral-small |
| specialized | deepseek-r1, jamba-1.5-large |

## Short Names

Use short names in commands:

```bash
adversarial-iac game --red-model claude-3.5-sonnet --blue-model nova-pro -s "..."
```

## Backends

See [Models & Backends](../options/backends.md) for:

- Bedrock (default)
- Direct API (DashScope, OpenAI-compatible)
- SageMaker endpoints
- Thinking mode for reasoning models

## Adding Models

Edit `src/models.py` — `MODEL_REGISTRY` — to add short names. Full Bedrock IDs work without registration.
