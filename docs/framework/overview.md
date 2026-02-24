# Framework Overview

Adversarial IaC Eval is a **game-theoretic evaluation framework** designed to measure LLM security capabilities through adversarial competition.

## Core Concept

Traditional security evaluation relies on static datasets with pre-labeled vulnerabilities. This approach has fundamental limitations:

| Traditional Approach | Our Framework |
|---------------------|---------------|
| Fixed vulnerability dataset | Dynamically generated vulnerabilities |
| Manual expert labeling | Automatic ground truth via Red Team |
| Limited sample diversity | Infinite scenario combinations |
| Stale data over time | Always current with model capabilities |
| Single evaluation dimension | Multi-dimensional adversarial testing |

## The Game-Theoretic Model

We model security evaluation as a **two-player game**:

```
                    ┌─────────────────────────────────────┐
                    │           GAME THEORY               │
                    │                                     │
    ┌───────────────┴───────────────┐                     │
    │                               │                     │
    ▼                               ▼                     │
┌───────┐                       ┌───────┐                 │
│ RED   │  Adversarial          │ BLUE  │                 │
│ TEAM  │◄─────────────────────►│ TEAM  │                 │
│       │  Competition          │       │                 │
└───┬───┘                       └───┬───┘                 │
    │                               │                     │
    │ Injects vulnerabilities       │ Detects issues      │
    │ Tries to evade detection      │ Reports findings    │
    │                               │                     │
    └───────────────┬───────────────┘                     │
                    │                                     │
                    ▼                                     │
              ┌───────────┐                               │
              │   JUDGE   │                               │
              │           │                               │
              │ Computes  │                               │
              │ metrics   │◄──────────────────────────────┘
              └───────────┘      Determines winner
```

### Red Team Goal
**Maximize evasion**: Generate code that looks legitimate but contains hidden vulnerabilities that Blue Team cannot detect.

### Blue Team Goal
**Maximize detection**: Find all security issues while minimizing false positives.

### Judge Role
**Compute ground truth metrics**: Compare Red Team's manifest against Blue Team's findings to determine precision, recall, and evasion rate.

## Key Innovation: Self-Generating Ground Truth

The critical insight is that **Red Team generates both code AND labels**:

```python
# Red Team output
{
    "code": "resource aws_s3_bucket...",  # The IaC code
    "manifest": {                          # Ground truth labels
        "vulnerabilities": [
            {"type": "encryption", "resource": "aws_s3_bucket.data"},
            {"type": "public_access", "resource": "aws_s3_bucket.data"}
        ]
    }
}
```

Blue Team only sees the code. The manifest serves as ground truth for scoring—**no manual labeling required**.

## Framework Properties

### Scalability
Generate unlimited test cases by varying:
- Scenarios (storage, compute, network, IAM, etc.)
- Difficulty levels (easy, medium, hard)
- Models (any LLM via Bedrock, OpenAI, etc.)
- Languages (Terraform, CloudFormation, ARM)

### Controllability
Systematically vary parameters to study specific hypotheses:
- "Does difficulty affect evasion rate?"
- "Is Sonnet better than Haiku at defense?"
- "Are IAM vulnerabilities harder to detect than encryption?"

### Reproducibility
Configuration-driven experiments with deterministic game protocols:
```yaml
experiment:
  models: [haiku, sonnet]
  difficulties: [medium, hard]
  scenarios: [storage, compute]
  replications: 5
```

### Extensibility
Every component is designed for extension:
- Custom agents with different strategies
- Custom metrics beyond precision/recall
- Custom game protocols (multi-round, collaborative, etc.)

## Evaluation Dimensions

The framework captures multiple security evaluation dimensions:

| Dimension | Measured By | Research Question |
|-----------|-------------|-------------------|
| **Detection Capability** | Recall | How many vulnerabilities can the model find? |
| **Detection Accuracy** | Precision | How many reports are real issues? |
| **Evasion Resistance** | Evasion Rate | How well does the model handle adversarial hiding? |
| **Balanced Performance** | F1 Score | What's the overall security posture? |
| **Attack Sophistication** | By Difficulty | Can harder attacks evade detection? |

## Use Cases

### Researchers
- Benchmark new models on security tasks
- Study adversarial robustness
- Compare detection methodologies

### Security Teams
- Evaluate AI code review tools
- Compare LLM vs static analysis
- Stress-test detection pipelines

### AI Safety
- Red team foundation models
- Study emergent security capabilities
- Build adversarial training datasets

## Next Steps

- [Architecture](architecture.md) - Deep dive into components
- [Game Protocol](game-protocol.md) - How games are played
- [Scoring System](scoring.md) - Understanding metrics
