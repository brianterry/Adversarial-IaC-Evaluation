# Judge Agent API

The Judge agent scores matches between Red Team vulnerabilities and Blue Team findings.

## Quick Start

```python
from src.agents.judge_agent import JudgeAgent, score_results_to_dict

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

print(f"Precision: {results.precision:.1%}")
print(f"Recall: {results.recall:.1%}")
print(f"F1 Score: {results.f1_score:.1%}")
print(f"Evasion Rate: {results.evasion_rate:.1%}")
```

## Classes

### `JudgeAgent`

Main class for scoring Red vs Blue matches.

#### Constructor

```python
judge = JudgeAgent(
    match_threshold: float = 0.4,  # Minimum score for a match
    exact_threshold: float = 0.7   # Score for exact match
)
```

#### Methods

##### `score()`

Score a game between Red and Blue teams.

```python
results = judge.score(
    red_manifest: Dict,      # Red Team vulnerability manifest
    blue_findings: List[Dict]  # Blue Team findings
) -> ScoreResults
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `red_manifest` | `Dict` | Red Team's vulnerability manifest |
| `blue_findings` | `List[Dict]` | Blue Team's detected findings |

**Returns:** `ScoreResults`

### `ScoreResults`

Container for scoring metrics.

```python
@dataclass
class ScoreResults:
    true_positives: int    # Correctly matched vulnerabilities
    false_positives: int   # Blue findings with no match
    false_negatives: int   # Red vulns that evaded detection
    
    precision: float       # TP / (TP + FP)
    recall: float          # TP / (TP + FN)
    f1_score: float        # Harmonic mean of P and R
    evasion_rate: float    # FN / (TP + FN)
    
    matches: List[Match]   # Detailed match information
    evaded: List[str]      # IDs of evaded vulnerabilities
    false_alarms: List[int]  # Indices of false positive findings
```

### `Match`

Represents a matched vulnerability-finding pair.

```python
@dataclass
class Match:
    vulnerability_id: str   # Red Team vuln ID
    finding_index: int      # Blue Team finding index
    score: float           # Match score (0.0-1.0)
    match_type: str        # "exact" or "partial"
```

## Usage Examples

### Basic Scoring

```python
import json
from pathlib import Path

# Load Red Team manifest
red_manifest = json.loads(
    Path("output/red-team/run_001/vulnerability_manifest.json").read_text()
)

# Load Blue Team findings
blue_findings = json.loads(
    Path("output/blue-team/run_001/findings.json").read_text()
)

# Score the match
judge = JudgeAgent()
results = judge.score(red_manifest, blue_findings)

print(f"""
Game Results:
  True Positives:  {results.true_positives}
  False Positives: {results.false_positives}
  False Negatives: {results.false_negatives}
  
  Precision:    {results.precision:.1%}
  Recall:       {results.recall:.1%}
  F1 Score:     {results.f1_score:.1%}
  Evasion Rate: {results.evasion_rate:.1%}
""")
```

### Analyzing Matches

```python
results = judge.score(red_manifest, blue_findings)

# Show exact matches
print("Exact Matches:")
for match in results.matches:
    if match.match_type == "exact":
        print(f"  {match.vulnerability_id} → finding[{match.finding_index}] ({match.score:.2f})")

# Show partial matches
print("\nPartial Matches:")
for match in results.matches:
    if match.match_type == "partial":
        print(f"  {match.vulnerability_id} → finding[{match.finding_index}] ({match.score:.2f})")

# Show evaded vulnerabilities
print("\nEvaded (Red Team wins):")
for vuln_id in results.evaded:
    print(f"  {vuln_id}")

# Show false positives
print("\nFalse Positives (Blue Team errors):")
for idx in results.false_alarms:
    finding = blue_findings[idx]
    print(f"  finding[{idx}]: {finding['type']} on {finding['resource']}")
```

### Custom Thresholds

```python
# Stricter matching (fewer matches)
strict_judge = JudgeAgent(
    match_threshold=0.6,   # Higher bar for match
    exact_threshold=0.85   # Higher bar for exact
)

# Lenient matching (more matches)
lenient_judge = JudgeAgent(
    match_threshold=0.3,
    exact_threshold=0.5
)
```

### Convert to Dictionary

```python
from src.agents.judge_agent import score_results_to_dict

results = judge.score(red_manifest, blue_findings)
results_dict = score_results_to_dict(results)

# Save to file
import json
with open("scores.json", "w") as f:
    json.dump(results_dict, f, indent=2)
```

## Matching Algorithm

The judge uses a multi-factor scoring algorithm:

### Score Calculation

```python
def calculate_match_score(vulnerability, finding):
    score = 0.0
    
    # Category match (30% weight)
    if categories_match(vulnerability.type, finding.type):
        score += 0.30
    
    # Resource match (25% weight)
    if resources_match(vulnerability.resource, finding.resource):
        score += 0.25
    
    # Keyword similarity (25% weight)
    keyword_score = jaccard_similarity(
        extract_keywords(vulnerability),
        extract_keywords(finding)
    )
    score += 0.25 * keyword_score
    
    # Severity match (20% weight)
    if vulnerability.severity == finding.severity:
        score += 0.20
    
    return score
```

### Category Mapping

```python
CATEGORY_PATTERNS = {
    'encryption': ['encryption', 'sse', 'kms', 'tls'],
    'access_control': ['public', 'acl', 'permission', 'access'],
    'iam': ['iam', 'role', 'policy', 'privilege'],
    'network': ['security group', 'cidr', 'ingress', 'egress'],
    'logging': ['logging', 'audit', 'cloudtrail', 'monitoring']
}
```

### Match Thresholds

| Score Range | Classification |
|-------------|----------------|
| ≥ 0.70 | Exact match (TP) |
| 0.40 - 0.69 | Partial match (TP) |
| < 0.40 | No match |

## Error Handling

```python
from src.agents.judge_agent import JudgeError

try:
    results = judge.score(red_manifest, blue_findings)
except JudgeError as e:
    print(f"Scoring failed: {e}")
```

## Metrics Formulas

```python
# Precision: How accurate were Blue's reports?
precision = TP / (TP + FP)

# Recall: How many vulns did Blue find?
recall = TP / (TP + FN)

# F1 Score: Balanced measure
f1_score = 2 * (precision * recall) / (precision + recall)

# Evasion Rate: How many vulns did Red hide?
evasion_rate = FN / (TP + FN)
```

## Aggregate Scoring

For experiments with multiple games:

```python
def aggregate_results(all_results: List[ScoreResults]) -> Dict:
    return {
        "total_games": len(all_results),
        "avg_precision": mean([r.precision for r in all_results]),
        "avg_recall": mean([r.recall for r in all_results]),
        "avg_f1": mean([r.f1_score for r in all_results]),
        "avg_evasion": mean([r.evasion_rate for r in all_results]),
        "total_tp": sum([r.true_positives for r in all_results]),
        "total_fp": sum([r.false_positives for r in all_results]),
        "total_fn": sum([r.false_negatives for r in all_results]),
    }
```

## Next Steps

- [Red Team API](red-team.md) - Attack generation
- [Blue Team API](blue-team.md) - Detection agent
- [Scoring System](../concepts/scoring.md) - Understanding metrics
