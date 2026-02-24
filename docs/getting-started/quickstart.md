# Quick Start

Run your first adversarial game in under 5 minutes.

## Your First Game

```bash
adversarial-iac game \
    --red-model us.anthropic.claude-3-5-haiku-20241022-v1:0 \
    --blue-model us.anthropic.claude-3-5-haiku-20241022-v1:0 \
    --scenario "Create an S3 bucket for storing application logs" \
    --difficulty easy
```

### What Happens

1. **🔴 Red Team** receives the scenario and injects vulnerabilities into IaC code
2. **🔵 Blue Team** analyzes the code and reports findings  
3. **⚖️ Judge** matches findings to injected vulnerabilities and scores

### Output

```
🎮 Game G-20260224_120000 Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Scoring:
   Precision: 75.0%  (3/4 findings were real vulnerabilities)
   Recall:    100.0% (3/3 vulnerabilities detected)
   F1 Score:  85.7%
   Evasion:   0.0%   (0/3 vulnerabilities evaded detection)

📁 Results saved to: output/games/G-20260224_120000/
```

## Understanding Results

| Metric | Meaning | Good Score |
|--------|---------|------------|
| **Precision** | % of findings that were real vulnerabilities | Higher = fewer false positives |
| **Recall** | % of vulnerabilities detected | Higher = better detection |
| **F1 Score** | Harmonic mean of precision & recall | Higher = balanced performance |
| **Evasion Rate** | % of vulnerabilities NOT detected | Lower = better Blue Team |

## Exploring Game Output

```bash
ls output/games/G-20260224_120000/
```

```
code/
├── main.tf           # Generated IaC code
├── variables.tf      # Variables file
red_manifest.json     # Injected vulnerabilities
blue_findings.json    # Detected findings
scoring.json          # Match results
metadata.json         # Game configuration
game.log              # Detailed execution log
```

## Try Different Difficulties

=== "Easy"

    ```bash
    adversarial-iac game \
        --scenario "Create an EC2 instance" \
        --difficulty easy
    ```
    
    - 2-3 obvious vulnerabilities
    - Basic misconfiguration patterns

=== "Medium"

    ```bash
    adversarial-iac game \
        --scenario "Create an EC2 instance" \
        --difficulty medium
    ```
    
    - 3-4 mixed vulnerabilities
    - Some subtle patterns

=== "Hard"

    ```bash
    adversarial-iac game \
        --scenario "Create an EC2 instance" \
        --difficulty hard
    ```
    
    - 4-5 stealthy vulnerabilities
    - Advanced evasion techniques

## Try Multi-Agent Modes

### Blue Team Ensemble

Multiple specialists analyze the code:

```bash
adversarial-iac game \
    --scenario "Create a VPC with subnets" \
    --blue-team-mode ensemble \
    --consensus-method vote
```

### Red Team Pipeline

Specialized attack chain:

```bash
adversarial-iac game \
    --scenario "Create a VPC with subnets" \
    --red-team-mode pipeline
```

### Adversarial Debate

Verify findings through debate:

```bash
adversarial-iac game \
    --scenario "Create a VPC with subnets" \
    --verification-mode debate
```

## Next Steps

- [Configuration](configuration.md) - Customize models and settings
- [Architecture](../framework/architecture.md) - Understand how it works
- [Running Experiments](../experiments/batch.md) - Run many games
