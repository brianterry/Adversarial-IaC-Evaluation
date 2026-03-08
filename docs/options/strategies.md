# Strategies

Red and Blue teams can use different strategies.

## Red Team Strategies

| Strategy | Description |
|----------|-------------|
| balanced | Standard mix of vulnerabilities and stealth (default) |
| targeted | Focus on specific type (use `--red-target-type`) |
| stealth | Fewer vulns, maximum evasion |
| blitz | Maximum vulnerabilities, less stealth |
| chained | Vulns that exploit each other in sequence |

### Examples

```bash
# Balanced (default)
adversarial-iac game -s "Create S3 bucket" --red-strategy balanced

# Targeted at encryption
adversarial-iac game -s "Create S3 bucket" --red-strategy targeted --red-target-type encryption

# Stealth mode
adversarial-iac game -s "Create S3 bucket" --red-strategy stealth
```

## Blue Team Strategies

| Strategy | Description |
|----------|-------------|
| comprehensive | Check all vulnerability types (default) |
| targeted | Focus on specific type (use `--blue-target-type`) |
| iterative | Multiple analysis passes (use `--blue-iterations`) |
| threat_model | STRIDE-based analysis |
| compliance | Framework-specific audit (use `--compliance-framework`) |

### Examples

```bash
# Comprehensive (default)
adversarial-iac game -s "Create S3 bucket" --blue-strategy comprehensive

# Targeted at IAM
adversarial-iac game -s "Create S3 bucket" --blue-strategy targeted --blue-target-type iam

# Compliance (HIPAA)
adversarial-iac game -s "Create healthcare API" --blue-strategy compliance --compliance-framework hipaa

# Iterative (3 passes)
adversarial-iac game -s "Create S3 bucket" --blue-strategy iterative --blue-iterations 3
```

## Target Types

For `targeted` strategy: `encryption`, `iam`, `network`, `logging`, `access_control`.

## Vulnerability Source (Red)

| Source | Description |
|--------|-------------|
| database | Select from Trivy rule database (default) |
| novel | LLM generates from security principles |
| mixed | 50% database, 50% novel |

```bash
adversarial-iac game -s "Create S3 bucket" --red-vuln-source novel
```
