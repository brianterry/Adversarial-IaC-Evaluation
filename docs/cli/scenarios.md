# adversarial-iac scenarios

List available test scenarios organized by category and domain.

## Usage

```bash
adversarial-iac scenarios [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--category`, `-c` | choice | all | infrastructure, aws_service, industry, security, all |
| `--domain`, `-d` | str | - | Show scenarios for a specific domain |

## Categories

| Category | Domains |
|----------|---------|
| infrastructure | storage, compute, network, iam |
| aws_service | secrets, containers, databases, api |
| industry | healthcare, financial, government |
| security | zero_trust, disaster_recovery |

## Examples

### All scenarios by category

```bash
adversarial-iac scenarios
```

### Industry scenarios only

```bash
adversarial-iac scenarios --category industry
```

### Healthcare domain

```bash
adversarial-iac scenarios --domain healthcare
```

### Use a scenario in a game

```bash
adversarial-iac game -s "Create an S3 bucket for healthcare PHI data with HIPAA compliance" -d medium
```
