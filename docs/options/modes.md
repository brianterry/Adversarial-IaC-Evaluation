# Game Modes

Single vs multi-agent configurations for Red and Blue teams.

## Red Team Mode

| Mode | Description |
|------|-------------|
| single | One agent generates code (default) |
| pipeline | 4-stage chain: Architect → Selector → Generator → Reviewer |

### Pipeline (stealthier attacks)

```bash
adversarial-iac game -s "Create S3 bucket" --red-team-mode pipeline
```

## Blue Team Mode

| Mode | Description |
|------|-------------|
| single | One agent analyzes (default) |
| ensemble | 3 specialists (security, compliance, architecture) + consensus |

### Ensemble (better detection)

```bash
adversarial-iac game -s "Create S3 bucket" --blue-team-mode ensemble --consensus-method vote
```

### Consensus Methods

| Method | Description |
|--------|-------------|
| `vote` | Majority wins |
| `union` | Combine all findings (higher recall, lower precision) |
| `intersection` | Only findings all agents agree on (higher precision, lower recall) |
| `debate` | Agents argue until consensus |

!!! note "Two different \"debate\" options"
    `--consensus-method debate` controls how Blue Team ensemble agents agree on findings.
    `--verification-mode debate` controls how the Judge verifies findings (Prosecutor vs Defender).
    They are independent and can be used together.

### When to Use Multi-Agent

Use pipeline + ensemble when you want to stress-test models with stealthier attacks and collaborative detection. Single agents are faster and sufficient for quick experiments.

## Verification Mode

| Mode | Description |
|------|-------------|
| standard | Direct matching (default) |
| debate | Adversarial debate (Prosecutor vs Defender) |

### Debate verification

```bash
adversarial-iac game -s "Create S3 bucket" --verification-mode debate
```

## Full Multi-Agent Example

```bash
adversarial-iac game -s "Create VPC with subnets" \
  --red-team-mode pipeline \
  --blue-team-mode ensemble \
  --consensus-method debate \
  --verification-mode debate
```
