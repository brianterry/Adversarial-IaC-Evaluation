# Scenarios

114 built-in scenarios across 18 domains and 4 categories.

## Browse

```bash
adversarial-iac scenarios
adversarial-iac scenarios --category industry
adversarial-iac scenarios --domain healthcare
```

## Categories

| Category | Domains |
|----------|---------|
| infrastructure | storage, compute, network, iam, multi_service |
| aws_service | secrets, containers, databases, api, messaging, monitoring |
| industry | healthcare, financial, government |
| security | zero_trust, disaster_recovery |

## Custom Scenarios

Use any description with `--scenario`:

```bash
adversarial-iac game -s "Create a Lambda that processes PII with encryption" -d medium
```

## Adding Scenarios

Edit `src/prompts.py` — `ScenarioTemplates.SCENARIOS` — to add domains and scenario strings.
