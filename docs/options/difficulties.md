# Difficulties

Controls vulnerability complexity and stealth — not error rate or sloppiness.

!!! warning "Key design principle"
    Difficulty adjusts how hard it is for Blue Team to detect vulnerabilities. Red Team is never asked to "make mistakes." Manifests must be accurate at all difficulty levels.

## Levels

| Level | Vulns | Style |
|-------|-------|-------|
| Easy | 1-2 | Obvious misconfigs (missing encryption, public access). No stealth. |
| Medium | 2-3 | Moderate stealth. Requires basic cross-resource analysis. |
| Hard | 1-2 | High-stealth, logic-dependent. Cross-file dependencies, conditional expressions, indirect references. Focus on complexity, not quantity. |

## Examples

### Easy (learning)

```bash
adversarial-iac game -s "Create S3 bucket" -d easy
```

### Medium (default)

```bash
adversarial-iac game -s "Create S3 bucket" -d medium
```

### Hard (expert)

```bash
adversarial-iac game -s "Create VPC with subnets" -d hard
```

## When to Use

| Level | Best for | Vulnerabilities | Comparable to paper? | Token cost | Typical Blue precision |
|-------|----------|-----------------|----------------------|------------|------------------------|
| Easy | Learning, debugging, quick tests | 1–2 obvious | No | Lowest | High |
| Medium | Standard evaluation, most scenarios | 2–3 moderate stealth | No | Medium | Medium |
| Hard | Benchmarking, publication, stress tests | 1–2 high-stealth, logic-dependent | **Yes** | Highest | Lower |

!!! note "Published results"
    Results in the paper use **hard** difficulty.
