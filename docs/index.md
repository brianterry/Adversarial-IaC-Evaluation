# Adversarial IaC Benchmark

**Red Team vs Blue Team security evaluation for Infrastructure-as-Code.**

## What This Is For

This benchmark is for **LLM evaluators**, **multi-agent researchers**, and **AWS practitioners** who want to measure how well models reason about security in Infrastructure-as-Code—not just memorize patterns.

!!! quote "Key differentiator"
    This measures genuine security reasoning, not pattern memorization.

## How It Works

```mermaid
flowchart LR
    S[Scenario] --> R[Red Team]
    R --> V[Validator]
    V --> B[Blue Team]
    B --> J[Judge]
    J --> S2[Scores]
```

1. **Scenario** — "Create an S3 bucket for healthcare PHI data"
2. **Red Team** — Generates code with hidden vulnerabilities
3. **Validator** — Trivy/Checkov corroborate Red Team claims; unconfirmed entries are excluded from scoring (phantom concordance mitigation)
4. **Blue Team** — Analyzes code to find them; precision verification filter removes unsubstantiated findings
5. **Judge** — Scores precision, recall, F1, evasion rate using cross-provider consensus for novel vulnerabilities

## Get Started

```bash
adversarial-iac play
```

The interactive wizard guides you through scenario selection, model choice, and explains results.

## Next Steps

- [Quick Start](getting-started/quickstart.md) — Install and run your first game
- [CLI Reference](cli/game.md) — All commands and options with examples
- [Experiments](experiments/batch.md) — Batch runs with YAML config
