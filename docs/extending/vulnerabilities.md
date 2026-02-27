# New Vulnerability Types

## Adding Rules

Add new vulnerability rules to `src/data/trivy_rules_db.json`:

```json
{
  "id": "MY-RULE-001",
  "title": "My Security Rule",
  "severity": "HIGH",
  "resource_type": "aws_s3_bucket"
}
```

## Updating the Database

To update the database with the latest Trivy rules:

```bash
python scripts/update_trivy_rules.py
```

The database contains 142 real-world vulnerability patterns from [Trivy Checks](https://github.com/aquasecurity/trivy-checks).
