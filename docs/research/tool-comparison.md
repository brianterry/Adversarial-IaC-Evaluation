# Tool Comparison

Detailed comparison of LLM detection vs. static analysis tools.

## Overview

We compared three approaches for detecting vulnerabilities in LLM-generated IaC:

| Tool | Type | Approach |
|------|------|----------|
| **LLM** | Semantic | Reasoning about code meaning |
| **Trivy** | Static | Pattern/regex matching |
| **Checkov** | Static | Policy-as-Code rules |

## Results Summary

```
Detection Comparison (16 games, 58 injected vulnerabilities)
═══════════════════════════════════════════════════════════════
LLM      ████████████████████████████████████████████████ 59
Checkov  ██████████████████████████████████████          45
Trivy                                                     0
═══════════════════════════════════════════════════════════════
         0                                              60
```

| Tool | Total Findings | True Positives | Precision |
|------|---------------|----------------|-----------|
| **LLM** | 59 | 44 | 74.6% |
| **Checkov** | 45 | 19 | 42.2% |
| **Trivy** | 0 | 0 | N/A |

## Why Trivy Found Nothing

Trivy relies on regex patterns designed for common human-written patterns:

### Pattern Mismatch Example

**Trivy expects:**
```hcl
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
  acl    = "public-read"  # ← Trivy pattern matches this
}
```

**LLM generates:**
```hcl
resource "aws_s3_bucket" "data_store" {
  bucket = "healthcare-phi-${var.environment}"
  
  tags = {
    Name        = "PHI Data Store"
    Environment = var.environment
    HIPAA       = "true"  # Misleading tag
  }
}

resource "aws_s3_bucket_acl" "data_store_acl" {
  bucket = aws_s3_bucket.data_store.id
  acl    = "public-read"  # ← Same vulnerability, different location
}
```

**Issues:**
1. ACL in separate resource (Terraform 4.0+ pattern)
2. Variable interpolation in bucket name
3. Misleading HIPAA tag suggests compliance

## Checkov's Partial Success

Checkov performed better because it uses policy-as-code rules that check resource properties:

```python
# Checkov rule example
class S3BucketPublicAccessBlock(BaseResourceCheck):
    def __init__(self):
        name = "Ensure S3 bucket has public access block"
        id = "CKV_AWS_21"
        
    def scan_resource_conf(self, conf):
        # Checks for public_access_block resource
        return CheckResult.PASSED if self._has_block(conf) else CheckResult.FAILED
```

**Why Checkov still missed many:**
1. LLM creates valid-looking configurations
2. Comments suggest intentional decisions
3. Some checks don't cover all code patterns

## LLM Semantic Analysis

LLMs detected vulnerabilities through reasoning:

### Example LLM Analysis

```
Analyzing: aws_s3_bucket.data_store

Observations:
1. Bucket name suggests PHI data storage
2. No server-side encryption configured
3. No bucket policy restricting access
4. HIPAA tag present but compliance not enforced

Vulnerability Found:
- Type: encryption
- Severity: HIGH
- Evidence: Missing aws_s3_bucket_server_side_encryption_configuration
- Impact: PHI data may be stored unencrypted, violating HIPAA
```

## Detection Overlap

Venn diagram of detections:

```
           ┌─────────────────────────┐
           │         LLM (59)        │
           │                         │
           │    ┌───────────┐        │
           │    │ Both (15) │        │
           │    │           │        │
      ┌────┼────┤           ├────────┤
      │    │    └───────────┘        │
      │    │                         │
      │    └─────────────────────────┘
      │    
      │    Checkov (45)
      │    └─ LLM missed: 30
      │    └─ Overlap: 15
      │    └─ False positives: ~26
      │
      Trivy (0)
```

## By Vulnerability Type

| Type | LLM | Checkov | Trivy |
|------|-----|---------|-------|
| Encryption | 18 | 12 | 0 |
| Access Control | 15 | 18 | 0 |
| IAM | 12 | 8 | 0 |
| Network | 8 | 4 | 0 |
| Logging | 6 | 3 | 0 |

**Key observations:**
- LLM best at encryption (semantic understanding)
- Checkov competitive on access control (well-defined policies)
- Both weak on network (complex relationships)

## Hybrid Detection

We tested combining approaches:

### Union Strategy
```python
# Combine all findings
hybrid_findings = llm_findings | checkov_findings
```

| Metric | LLM Only | Checkov Only | Hybrid |
|--------|----------|--------------|--------|
| Recall | 76.2% | 32.8% | 81.4% |
| Precision | 71.4% | 42.2% | 52.3% |
| F1 | 58.6% | 36.7% | 63.7% |

**Result:** Higher recall, but lower precision due to Checkov's false positives.

### Weighted Strategy (Future Work)

```python
# Proposed: weight by confidence
def hybrid_score(finding):
    if finding.source == "LLM" and finding.confidence > 0.8:
        return 1.0
    elif finding.source == "Checkov":
        return 0.7 if finding.severity == "HIGH" else 0.5
    return 0.3
```

## Recommendations

### For Security Teams

1. **Use LLM analysis** for AI-generated IaC
2. **Don't disable Checkov** but weight findings appropriately
3. **Update Trivy patterns** or use alternatives

### For Tool Selection

| Use Case | Recommended |
|----------|-------------|
| Human-written IaC | Trivy + Checkov |
| AI-generated IaC | LLM + Checkov |
| Mixed codebase | LLM primary, tools secondary |

### For Future Research

1. **Smarter fusion** algorithms for hybrid detection
2. **Confidence calibration** for LLM findings
3. **Pattern updates** for AI code styles

## Running Tool Comparison

```bash
# After running an experiment, compare tools:
python -m src.cli experiment \
    --config configs/small_test.yaml

# Results in:
# experiments/xxx/tool_comparison.json
```

## Next Steps

- [Research Findings](findings.md) - Full experimental results
- [Novelty](novelty.md) - Research contributions
