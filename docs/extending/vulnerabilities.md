# Vulnerabilities

Red Team selects from 142 Trivy-based vulnerability patterns or generates novel ones.

## Vulnerability Source

| Source | Description |
|--------|-------------|
| database | Trivy rules (default) |
| novel | LLM generates from principles |
| mixed | 50% database, 50% novel |

```bash
adversarial-iac game -s "Create S3 bucket" --red-vuln-source novel
```

## Adding Rules

Add to `src/data/trivy_rules_db.json`:

```json
{
  "id": "MY-RULE-001",
  "title": "My Security Rule",
  "severity": "HIGH",
  "resource_type": "aws_s3_bucket"
}
```

## Updating Trivy Database

```bash
python scripts/update_trivy_rules.py
```
