# Research Findings

Key findings from adversarial evaluation experiments.

## Executive Summary

| Finding | Impact |
|---------|--------|
| LLMs achieve **59% F1** detection rate | Moderate but imperfect security |
| Hard difficulty increases evasion **4×** | Red Team can evade with effort |
| **Trivy found 0 vulnerabilities** | Static tools fail on AI-generated code |
| Hybrid detection **underperforms** LLM-only | False positive noise hurts precision |

## Finding 1: Moderate Detection Capability

**LLMs can detect vulnerabilities, but not reliably.**

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Avg Precision | 71.4% | ~30% false positive rate |
| Avg Recall | 76.2% | ~24% vulnerabilities missed |
| Avg F1 Score | 58.6% | Moderate overall performance |
| Avg Evasion Rate | 23.8% | ~1 in 4 vulns escape detection |

!!! warning "Security Gap"
    Nearly 1 in 4 intentionally injected vulnerabilities evaded LLM detection—a significant gap for production security.

## Finding 2: Difficulty Dramatically Affects Evasion

**Hard mode evasion is 4× higher than medium.**

| Difficulty | Games | Avg F1 | Avg Evasion |
|------------|-------|--------|-------------|
| Medium | 8 | 67.9% | 9.7% |
| Hard | 8 | 49.4% | 37.9% |

```
Evasion Rate by Difficulty
═══════════════════════════════════════════════
Medium ████████▒ 9.7%
Hard   ████████████████████████████████████▒ 37.9%
═══════════════════════════════════════════════
                                          40%
```

**Why does hard mode evade detection?**

Hard mode uses advanced stealth techniques:
- Misleading comments that suggest security
- Chained vulnerabilities (A + B = exploit)
- Subtle omissions rather than obvious misconfigs
- Security-looking code that's actually insecure

## Finding 3: Static Tools Fail on AI-Generated Code

**Trivy found exactly zero vulnerabilities in LLM-generated code.**

| Tool | Findings | Explanation |
|------|----------|-------------|
| **LLM** | 59 | Semantic analysis works |
| **Checkov** | 45 | Pattern matching partially works |
| **Trivy** | 0 | Patterns don't match AI code |

!!! danger "Critical Implication"
    Organizations relying solely on Trivy for IaC security may have blind spots when reviewing AI-generated infrastructure code.

**Why did Trivy fail?**

Trivy uses regex patterns designed for human-written code:
```hcl
# Trivy expects
aws_s3_bucket "example" {
  acl = "public-read"  # Matches pattern!
}

# LLM generates
resource "aws_s3_bucket" "data_store" {
  # Secure bucket for data storage
  tags = { Environment = "production" }
}
resource "aws_s3_bucket_acl" "data_store_acl" {
  bucket = aws_s3_bucket.data_store.id
  acl    = "public-read"  # Same issue, different structure
}
```

## Finding 4: Hybrid Detection Disappoints

**LLM + Checkov performed worse than LLM alone.**

| Mode | Precision | Recall | F1 |
|------|-----------|--------|-----|
| LLM Only | 71.4% | 76.2% | 58.6% |
| Checkov Only | 45.0% | 32.1% | 37.5% |
| Hybrid | 52.3% | 81.4% | 63.7% |

**Why hybrid underperformed:**

1. Checkov added false positives (flagged non-issues)
2. Union strategy boosted recall but hurt precision
3. No intelligent merging of overlapping findings

!!! tip "Future Work"
    Smarter hybrid strategies (weighted voting, confidence thresholds) may improve results.

## Finding 5: Domain Variations

**Some infrastructure domains are harder to secure.**

| Domain | Games | Avg F1 | Avg Evasion |
|--------|-------|--------|-------------|
| Storage | 4 | 62.5% | 20.0% |
| Compute | 4 | 55.0% | 28.3% |
| IAM | 4 | 58.3% | 25.0% |
| Network | 4 | 58.8% | 21.8% |

**Observations:**
- Storage (S3) has most established patterns—easiest to detect
- Compute (Lambda) vulnerabilities are more contextual
- IAM and Network show similar detection difficulty

## Detailed Results by Model

When different models compete:

| Red Team | Blue Team | F1 Score |
|----------|-----------|----------|
| Haiku | Haiku | 58.6% |
| Sonnet | Sonnet | 62.3% |
| Haiku | Sonnet | 68.5% |
| Sonnet | Haiku | 45.2% |

**Key insight:** Stronger Blue Team model (Sonnet defending against Haiku attacks) performs best.

## Implications

### For Security Teams

1. **Don't rely solely on static analysis** for AI-generated IaC
2. **LLM-based review** catches semantic issues tools miss
3. **Hard vulnerabilities escape** even LLM detection

### For AI/ML Researchers

1. **Adversarial evaluation** reveals model limitations
2. **Difficulty scaling** provides controlled benchmarks
3. **Ground truth generation** solves labeled data problem

### For Tool Developers

1. **Update patterns** for AI-generated code styles
2. **Semantic analysis** complements pattern matching
3. **Hybrid approaches** need smarter fusion

## Raw Data

Full experiment data available at:
```
experiments/small_test/exp_20260220_125729/
```

Download individual game results:
```bash
cat experiments/small_test/exp_20260220_125729/experiment_summary.json | jq '.results'
```

## Next Steps

- [Tool Comparison](tool-comparison.md) - Detailed LLM vs Trivy vs Checkov
- [Novelty](novelty.md) - Why this research matters
