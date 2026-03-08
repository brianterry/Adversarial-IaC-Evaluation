# Difficulties

Controls how many vulnerabilities Red Team injects and how stealthy they are.

## Levels

| Level | Vulns | Style |
|-------|-------|-------|
| Easy | 2-3 | Obvious misconfigs (missing encryption, public access) |
| Medium | 3-4 | Subtle issues (overly permissive IAM, weak defaults) |
| Hard | 4-5 | Stealthy (dynamic refs, conditional misconfig, chaining) |

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
| Easy | Learning, debugging, quick tests | 2–3 obvious | No | Lowest | High |
| Medium | Standard evaluation, most scenarios | 3–4 subtle | No | Medium | Medium |
| Hard | Benchmarking, publication, stress tests | 4–5 stealthy | **Yes** | Highest | Lower |

!!! note "Published results"
    Results in the paper use **hard** difficulty.
