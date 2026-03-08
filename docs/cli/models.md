# adversarial-iac models

List available Bedrock models organized by capability tier.

## Usage

```bash
adversarial-iac models [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--tier`, `-t` | choice | all | frontier, strong, efficient, specialized, all |

## Tiers

| Tier | Description |
|------|-------------|
| frontier | Best quality, highest cost |
| strong | Good balance |
| efficient | Fast and cheap |
| specialized | Experimental (DeepSeek, Jamba) |

## Examples

### All models

```bash
adversarial-iac models
```

### Frontier tier only

```bash
adversarial-iac models --tier frontier
```

### Efficient tier (for testing)

```bash
adversarial-iac models -t efficient
```

## Output

Models are shown in tables by tier with short name and full Bedrock ID. Use short names in `--red-model` and `--blue-model`:

```bash
adversarial-iac game --red-model claude-3.5-sonnet --blue-model nova-pro -s "..."
```
