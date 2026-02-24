# Blue Team Agent

The Blue Team agent's goal is to **detect all vulnerabilities** in the IaC code.

## Detection Methods

### LLM Analysis (Default)

Uses the configured LLM to analyze code for security issues:

```python
BlueTeamAgent(
    model_id="claude-3-5-sonnet",
    detection_mode="llm_only"
)
```

### Hybrid Analysis (Optional)

Combines LLM with static analysis tools:

```python
BlueTeamAgent(
    detection_mode="hybrid",
    tools=["trivy", "checkov"]
)
```

## Output Format

```json
{
  "findings": [
    {
      "finding_id": "F001",
      "resource_name": "aws_s3_bucket.data",
      "vulnerability_type": "encryption",
      "severity": "high",
      "title": "S3 bucket lacks server-side encryption",
      "description": "The bucket does not enable SSE...",
      "evidence": "No encryption configuration found",
      "remediation": "Add server_side_encryption_configuration block",
      "confidence": 0.95
    }
  ]
}
```

## Evaluation

Blue Team performance is measured by:

- **Precision**: Are findings real vulnerabilities?
- **Recall**: Are all vulnerabilities found?
- **False Positive Rate**: How many spurious findings?
