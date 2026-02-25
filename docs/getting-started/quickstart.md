# Quick Start

Play your first game in under 5 minutes!

## Play Now

```bash
adversarial-iac play
```

That's it! The interactive wizard guides you through everything:

```
🎮 ADVERSARIAL IAC GAME
━━━━━━━━━━━━━━━━━━━━━━━

? How would you like to choose a scenario?
❯ 🎲 Random - Let me pick something interesting
  🏗️ Infrastructure - Core AWS components
  🏢 Industry - Healthcare, Financial, Government...
  ✏️ Custom - Describe your own scenario

? Select difficulty level:
  🟢 Easy - Obvious vulnerabilities (good for learning)
❯ 🟡 Medium - Subtle issues (recommended)
  🔴 Hard - Hidden, chained vulnerabilities (expert)

? Which Infrastructure-as-Code language?
❯ 📄 Terraform (HCL) - Most popular, recommended
  ☁️  CloudFormation (YAML/JSON) - AWS native

? Choose Red Team model (attacker):
❯ ⭐ claude-3.5-sonnet (Recommended)
  ⚡ claude-3.5-haiku (Fast)
  💰 nova-lite (Cheap)
  
[Running game...]

🎮 Game Complete! Here's what happened...
```

## What Happens During a Game

1. **🔴 Red Team** creates infrastructure code with hidden vulnerabilities
2. **🔵 Blue Team** analyzes the code to find security issues  
3. **⚖️ Judge** scores who won based on what was found vs hidden

The wizard explains the results in plain English - no security expertise required!

---

??? note "📟 Command Line Mode"
    For scripting or direct control:
    
    ```bash
    adversarial-iac game \
        --scenario "Create an S3 bucket for healthcare PHI data" \
        --red-model claude-3.5-sonnet \
        --blue-model nova-pro \
        --difficulty medium
    ```
    
    See all options: `adversarial-iac game --help`

### What Happens

1. **🔴 Red Team** creates infrastructure code with hidden vulnerabilities
2. **🔵 Blue Team** analyzes the code to find security issues  
3. **⚖️ Judge** scores who won based on what was found vs hidden

### Output

```
🎮 Game Complete!

┌─────────────────────────────────────────────┐
│ Match Details                               │
├──────────────────┬───────────┬──────────────┤
│ Red Team Vuln    │ Blue Find │ Match        │
├──────────────────┼───────────┼──────────────┤
│ Missing encrypt  │ No SSE    │ ✓ Partial    │
│ Public bucket    │ Public    │ ✓ Exact      │
│ Weak IAM policy  │ -         │ ✗ Evaded     │
└──────────────────┴───────────┴──────────────┘

📊 Scores
   Precision:    100.0%  (Blue's accuracy)
   Recall:        66.7%  (% of vulns found)
   F1 Score:      80.0%  (Overall Blue performance)
   Evasion Rate:  33.3%  (Red's success hiding vulns)

🏆 Blue Team wins this round!

📁 Results saved to: output/games/G-20260224_120000/
```

## Browsing Scenarios

See all 114 built-in scenarios:

```bash
# List all scenarios by category
adversarial-iac scenarios

# Filter by category
adversarial-iac scenarios --category industry

# View specific domain
adversarial-iac scenarios --domain healthcare
```

### Categories

| Category | Domains | Example Scenarios |
|----------|---------|-------------------|
| 🏗️ **Infrastructure** | storage, compute, network, iam | S3 buckets, Lambda functions, VPCs |
| ☁️ **AWS Services** | secrets, containers, databases, api | KMS, EKS, RDS, API Gateway |
| 🏢 **Industry** | healthcare, financial, government | HIPAA, PCI-DSS, FedRAMP |
| 🔒 **Security** | zero_trust, disaster_recovery | Zero-trust architecture |

## Available Models

List models organized by tier:

```bash
adversarial-iac models
```

### Quick Reference

| Short Name | Full ID | Tier |
|------------|---------|------|
| `claude-3.5-sonnet` | us.anthropic.claude-3-5-sonnet-20241022-v2:0 | 🏆 Frontier |
| `nova-pro` | amazon.nova-pro-v1:0 | 💪 Strong |
| `nova-lite` | amazon.nova-lite-v1:0 | ⚡ Efficient |

Use short names in commands:
```bash
adversarial-iac game --red-model claude-3.5-sonnet --blue-model nova-pro ...
```

## Understanding Scores

| Metric | Who Wins? | Meaning |
|--------|-----------|---------|
| **Precision** | High = Blue | Were Blue's reports accurate? |
| **Recall** | High = Blue | Did Blue find Red's vulns? |
| **F1 Score** | High = Blue | Overall Blue performance |
| **Evasion Rate** | High = Red | Did Red successfully hide vulns? |

## Difficulty Levels

=== "🟢 Easy"

    ```bash
    adversarial-iac game --difficulty easy ...
    ```
    
    - 2-3 obvious vulnerabilities
    - Basic misconfiguration patterns
    - Good for learning

=== "🟡 Medium"

    ```bash
    adversarial-iac game --difficulty medium ...
    ```
    
    - 3-4 mixed vulnerabilities
    - Some subtle patterns
    - Recommended for experiments

=== "🔴 Hard"

    ```bash
    adversarial-iac game --difficulty hard ...
    ```
    
    - 4-5 stealthy vulnerabilities
    - Advanced evasion techniques
    - Expert mode

## Game Modes

### Standard (1v1)
```bash
adversarial-iac game --red-team-mode single --blue-team-mode single ...
```

### Red Team Pipeline
Multi-stage attack chain for stealthier vulnerabilities:
```bash
adversarial-iac game --red-team-mode pipeline ...
```

### Blue Team Ensemble
Expert panel with consensus voting:
```bash
adversarial-iac game --blue-team-mode ensemble --consensus-method vote ...
```

### Adversarial Debate
Verify each finding through debate:
```bash
adversarial-iac game --verification-mode debate ...
```

## Game Output Files

```
output/games/G-20260224_120000/
├── code/
│   └── main.tf              # Red Team's generated code
├── red_team_manifest.json   # Hidden vulnerabilities (ground truth)
├── blue_team_findings.json  # Blue Team's detections
├── game_result.json         # Full results with scores
└── game.log                 # Detailed execution log
```

## Next Steps

- [Configuration](configuration.md) - Customize models and settings
- [How the Game Works](../framework/architecture.md) - Understand the mechanics
- [Game Modes](../multi-agent/overview.md) - Multi-agent team strategies
- [Running Experiments](../experiments/batch.md) - Run many games for research
