# Judge Algorithm

The Judge determines whether Blue Team findings match Red Team's injected vulnerabilities.

## The Challenge

The core difficulty is **semantic matching**. Red Team and Blue Team describe vulnerabilities differently:

| Red Team Manifest | Blue Team Finding | Are they the same? |
|-------------------|-------------------|-------------------|
| "s3_encryption_disabled" | "Missing server-side encryption" | ✅ Yes |
| "public_read_acl" | "Bucket allows public access" | ✅ Yes |
| "weak_iam_policy" | "Overly permissive IAM" | ✅ Yes |
| "no_versioning" | "Missing MFA delete" | ❌ No (related but different) |

## Matching Algorithm

```python
def score_match(red_vuln, blue_finding) -> float:
    """Score how well a finding matches a vulnerability (0.0-1.0)"""
    
    score = 0.0
    weights = {
        'category': 0.30,    # Vulnerability type
        'resource': 0.25,    # Same resource affected
        'keywords': 0.25,    # Semantic overlap
        'severity': 0.20     # Same severity level
    }
    
    # 1. Category matching
    if categories_match(red_vuln.type, blue_finding.type):
        score += weights['category']
    
    # 2. Resource matching
    if resources_overlap(red_vuln.resources, blue_finding.resource):
        score += weights['resource']
    
    # 3. Keyword matching
    keyword_overlap = jaccard_similarity(
        red_vuln.keywords, 
        blue_finding.keywords
    )
    score += weights['keywords'] * keyword_overlap
    
    # 4. Severity matching
    if red_vuln.severity == blue_finding.severity:
        score += weights['severity']
    
    return score
```

## Category Mapping

Blue Team descriptions are mapped to standardized categories:

```python
CATEGORY_PATTERNS = {
    'encryption': [
        'encryption', 'encrypted', 'sse', 'kms', 
        'in transit', 'at rest', 'tls', 'ssl'
    ],
    'access_control': [
        'public', 'acl', 'policy', 'permission', 
        'access', 'exposed', 'open'
    ],
    'iam': [
        'iam', 'role', 'assume', 'principal', 
        'trust', 'privilege', '*'
    ],
    'network': [
        'security group', 'cidr', '0.0.0.0', 
        'ingress', 'egress', 'port'
    ],
    'logging': [
        'logging', 'audit', 'cloudtrail', 
        'monitoring', 'log'
    ]
}
```

## Match Types

| Type | Score Range | Counted As |
|------|-------------|------------|
| **Exact** | ≥ 0.70 | True Positive |
| **Partial** | 0.40 - 0.69 | True Positive |
| **Unmatched** | < 0.40 | Miss (FN for Red, FP for Blue) |

## Matching Process

```
Step 1: Build all possible pairs
┌─────────────────────────────────────────────────────────┐
│  Red Vulns: [V1, V2, V3]                                │
│  Blue Findings: [F1, F2, F3, F4]                        │
│                                                         │
│  Pairs: V1-F1, V1-F2, V1-F3, V1-F4,                    │
│         V2-F1, V2-F2, V2-F3, V2-F4,                    │
│         V3-F1, V3-F2, V3-F3, V3-F4                     │
└─────────────────────────────────────────────────────────┘

Step 2: Score each pair
┌─────────────────────────────────────────────────────────┐
│  V1-F1: 0.85 ⭐ (best for V1)                           │
│  V1-F2: 0.20                                            │
│  V2-F2: 0.72 ⭐ (best for V2)                           │
│  V2-F3: 0.45                                            │
│  V3-F1: 0.30                                            │
│  V3-F4: 0.15                                            │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘

Step 3: Greedy assignment (highest scores first)
┌─────────────────────────────────────────────────────────┐
│  ✓ V1 → F1 (0.85) - Matched                            │
│  ✓ V2 → F2 (0.72) - Matched                            │
│  ✗ V3 → None (best was 0.30) - EVADED                  │
│  ✗ F3 → None - FALSE POSITIVE                          │
│  ✗ F4 → None - FALSE POSITIVE                          │
└─────────────────────────────────────────────────────────┘

Result: TP=2, FP=2, FN=1
```

## Code Example

```python
from src.agents.judge_agent import JudgeAgent

judge = JudgeAgent()

results = judge.score(
    red_manifest={
        "vulnerabilities": [
            {"id": "v1", "type": "encryption", "resource": "aws_s3_bucket.data"},
            {"id": "v2", "type": "access_control", "resource": "aws_s3_bucket.data"},
        ]
    },
    blue_findings=[
        {"type": "encryption", "resource": "aws_s3_bucket.data", "severity": "HIGH"},
        {"type": "network", "resource": "aws_security_group.web", "severity": "MEDIUM"},
    ]
)

print(f"Precision: {results.precision:.1%}")  # 50% (1 TP, 1 FP)
print(f"Recall: {results.recall:.1%}")        # 50% (1 TP, 1 FN)
print(f"Matches: {results.matches}")          # [('v1', 'f1', 0.82)]
```

## Edge Cases

### Multiple Findings for One Vulnerability

If Blue Team reports multiple findings that could match one vulnerability:

```
Red: [No Encryption]
Blue: [Missing SSE-S3, Missing SSE-KMS, No encryption at rest]

→ Best match is selected (highest score)
→ Other findings become False Positives
```

### Chained Vulnerabilities

When Red Team uses chained vulnerabilities (hard mode):

```
Red: [IAM allows S3 write + S3 bucket public = data exfil]

→ If Blue finds either component, it's a partial match
→ Full credit requires finding the chain
```

## Limitations

!!! note "Known Limitations"
    1. **Semantic gap**: Different wording can reduce match scores
    2. **Partial overlaps**: Related but different issues may partially match
    3. **Context loss**: Judge doesn't see the actual code context

## Next Steps

- [Scoring System](scoring.md) - How scores become metrics
- [Research Findings](../research/findings.md) - Real experiment results
