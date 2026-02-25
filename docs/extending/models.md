# Available Models

The game supports **20+ AI models** via Amazon Bedrock, organized by capability tier.

## Browse Models

```bash
adversarial-iac models
```

## Tiered Model Registry

### 🏆 Frontier Tier

Best quality, highest cost. Use for final experiments and benchmarks.

| Short Name | Full Model ID |
|------------|---------------|
| `claude-3.5-sonnet` | us.anthropic.claude-3-5-sonnet-20241022-v2:0 |
| `claude-3-opus` | us.anthropic.claude-3-opus-20240229-v1:0 |
| `nova-premier` | amazon.nova-premier-v1:0 |
| `llama-3.3-70b` | us.meta.llama3-3-70b-instruct-v1:0 |
| `mistral-large-3` | mistral.mistral-large-3-675b-instruct |

### 💪 Strong Tier

Good balance of quality and cost. Recommended for most experiments.

| Short Name | Full Model ID |
|------------|---------------|
| `claude-3.5-haiku` | us.anthropic.claude-3-5-haiku-20241022-v1:0 |
| `claude-3-sonnet` | us.anthropic.claude-3-sonnet-20240229-v1:0 |
| `nova-pro` | amazon.nova-pro-v1:0 |
| `llama-3.1-70b` | us.meta.llama3-1-70b-instruct-v1:0 |
| `mistral-large` | mistral.mistral-large-2407-v1:0 |
| `command-r-plus` | cohere.command-r-plus-v1:0 |

### ⚡ Efficient Tier

Fast and cheap. Great for development and testing.

| Short Name | Full Model ID |
|------------|---------------|
| `claude-3-haiku` | us.anthropic.claude-3-haiku-20240307-v1:0 |
| `nova-lite` | amazon.nova-lite-v1:0 |
| `nova-micro` | amazon.nova-micro-v1:0 |
| `llama-3.1-8b` | us.meta.llama3-1-8b-instruct-v1:0 |
| `mistral-small` | mistral.mistral-small-2402-v1:0 |
| `ministral-8b` | mistral.ministral-3-8b-instruct |

### 🔬 Specialized Tier

Experimental or specialized models.

| Short Name | Full Model ID |
|------------|---------------|
| `deepseek-r1` | deepseek.deepseek-r1-v1:0 |
| `jamba-1.5-large` | ai21.jamba-1-5-large-v1:0 |
| `jamba-1.5-mini` | ai21.jamba-1-5-mini-v1:0 |
| `command-r` | cohere.command-r-v1:0 |

---

## Using Models

### Short Names (Recommended)

Use short names in commands for convenience:

```bash
adversarial-iac game \
    --red-model claude-3.5-sonnet \
    --blue-model nova-pro \
    --scenario "Create S3 bucket"
```

### Full Model IDs

You can also use full Bedrock model IDs directly:

```bash
adversarial-iac game \
    --red-model us.anthropic.claude-3-5-sonnet-20241022-v2:0 \
    --blue-model amazon.nova-pro-v1:0 \
    --scenario "Create S3 bucket"
```

### Interactive Mode

The interactive wizard shows models organized by tier:

```bash
adversarial-iac play
```

```
? Choose Red Team model (attacker):
❯ ⭐ claude-3.5-sonnet (Recommended - best quality)
  ⚡ claude-3.5-haiku (Fast - good balance)
  💰 nova-lite (Cheap - for testing)
  ─── More Models ───
  🏆 Frontier (best quality)
     claude-3-opus
     nova-premier
  💪 Strong (balanced)
     nova-pro
     llama-3.1-70b
  ...
```

---

## Recommendations

### For Development/Testing

Use **Efficient Tier** models:

```bash
adversarial-iac game \
    --red-model nova-lite \
    --blue-model nova-lite \
    --scenario "Create S3 bucket" \
    --difficulty easy
```

- Fast response times
- Low cost
- Good enough for debugging

### For Experiments

Use **Strong Tier** models:

```bash
adversarial-iac game \
    --red-model claude-3.5-haiku \
    --blue-model nova-pro \
    --scenario "Create healthcare API" \
    --difficulty medium
```

- Good quality
- Reasonable cost
- Reliable results

### For Final Benchmarks

Use **Frontier Tier** models:

```bash
adversarial-iac game \
    --red-model claude-3.5-sonnet \
    --blue-model claude-3.5-sonnet \
    --scenario "Create PCI-DSS payment system" \
    --difficulty hard
```

- Best quality
- Publication-ready results
- Higher cost

---

## Asymmetric Experiments

Test different model combinations:

```bash
# Strong attacker vs Efficient defender
adversarial-iac game \
    --red-model claude-3.5-sonnet \
    --blue-model nova-lite \
    --scenario "Create S3 bucket"

# Efficient attacker vs Strong defender
adversarial-iac game \
    --red-model nova-lite \
    --blue-model claude-3.5-sonnet \
    --scenario "Create S3 bucket"
```

---

## Adding Custom Models

### Use Full Model ID

Any Bedrock model can be used by its full ID:

```bash
adversarial-iac game \
    --red-model your.custom.model-id \
    --scenario "..."
```

### Add to Registry

Edit `src/models.py` to add permanent short names:

```python
MODEL_REGISTRY = {
    "frontier": {
        "my-model": "your.custom.model-id",
        # ...
    },
}
```

---

## AWS Bedrock Setup

Ensure you have:

1. **AWS credentials** configured (`aws configure`)
2. **Bedrock access** enabled in your AWS account
3. **Model access** granted for the models you want to use

```bash
# Test your setup
aws bedrock list-foundation-models --region us-east-1 | head
```
