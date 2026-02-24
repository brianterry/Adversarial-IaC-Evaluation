# Judge Agent

The Judge matches Blue Team findings to Red Team vulnerabilities and calculates metrics.

## Matching Algorithm

```python
def match_finding_to_vulnerability(finding, vuln):
    score = 0.0
    
    # Resource similarity (40%)
    if resources_match(finding.resource, vuln.resource):
        score += 0.4
    
    # Type match (30%)
    if finding.type == vuln.type:
        score += 0.3
    
    # Semantic similarity (30%)
    score += 0.3 * semantic_similarity(
        finding.description, 
        vuln.description
    )
    
    return score > 0.5  # Match threshold
```

## Scoring Output

```json
{
  "precision": 0.80,
  "recall": 1.00,
  "f1_score": 0.89,
  "evasion_rate": 0.00,
  "matches": [
    {
      "finding_id": "F001",
      "vuln_id": "V001",
      "match_score": 0.85,
      "match_type": "true_positive"
    }
  ]
}
```
