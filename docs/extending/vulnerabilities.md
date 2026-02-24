# New Vulnerability Types

## Adding Rules

Add new vulnerability rules to `vendor/trivy_rules_db.json`:

```json
{
  "id": "MY-RULE-001",
  "title": "My Security Rule",
  "severity": "HIGH",
  "resource_type": "aws_s3_bucket"
}
```
