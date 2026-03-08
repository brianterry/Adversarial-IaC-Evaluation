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

| Use easy when... | Use medium when... | Use hard when... |
|-----------------|--------------------|------------------|
| Learning the framework | Running experiments | Benchmarking |
| Quick debugging | Standard evaluation | Publication data |
| Testing new models | Most scenarios | Stress testing Blue |
