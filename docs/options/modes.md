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

For ensemble: `debate`, `vote`, `union`, `intersection`.

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
