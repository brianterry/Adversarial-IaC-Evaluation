# Configuration Reference

This page documents all configuration options for AdversarialIaC-Bench.

## CLI Options

### Game Command

```bash
adversarial-iac game [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--scenario`, `-s` | string | ✅ | - | Scenario description |
| `--red-model` | string | ❌ | `claude-3-5-haiku` | Red Team model ID |
| `--blue-model` | string | ❌ | `claude-3-5-haiku` | Blue Team model ID |
| `--difficulty` | choice | ❌ | `medium` | `easy`, `medium`, `hard` |
| `--language` | choice | ❌ | `terraform` | `terraform`, `cloudformation` |
| `--cloud-provider` | choice | ❌ | `aws` | `aws`, `azure`, `gcp` |
| `--red-team-mode` | choice | ❌ | `single` | `single`, `pipeline` |
| `--blue-team-mode` | choice | ❌ | `single` | `single`, `ensemble` |
| `--consensus-method` | choice | ❌ | `debate` | `debate`, `vote`, `union`, `intersection` |
| `--verification-mode` | choice | ❌ | `standard` | `standard`, `debate` |
| `--region` | string | ❌ | `us-west-2` | AWS region |

---

## Experiment Configuration (YAML)

Create experiment configs in `experiments/config/`.

### Full Example

```yaml
# experiments/config/my_experiment.yaml

name: "My Research Experiment"
description: "Comparing model performance across difficulties"

# Models to evaluate
models:
  - id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    name: "Claude 3.5 Sonnet"
    role: both  # Can be: red, blue, or both
  - id: "amazon.nova-pro-v1:0"
    name: "Amazon Nova Pro"
    role: blue

# Difficulty levels to test
difficulties:
  - easy
  - medium
  - hard

# Scenarios to run
scenarios:
  - "Create an S3 bucket for storing application logs"
  - "Create an EC2 instance for a web server"
  - "Create a VPC with public and private subnets"
  - "Create an RDS database for user data"
  - "Create a Lambda function with API Gateway"

# IaC settings
language: terraform        # terraform | cloudformation
cloud_provider: aws        # aws | azure | gcp

# Experiment settings
settings:
  repetitions: 3           # Run each config N times
  delay_between_games: 2   # Seconds between games (rate limiting)
  save_intermediate: true  # Save progress after each game

# Batch experiments (single-agent mode)
batch_experiments:
  enabled: true
  model_combinations:
    - red: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
      blue: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    - red: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
      blue: "amazon.nova-pro-v1:0"
    - red: "amazon.nova-pro-v1:0"
      blue: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# Multi-agent experiments
realtime_experiments:
  enabled: true
  modes:
    - name: "blue_ensemble_vote"
      red_mode: single
      blue_mode: ensemble
      consensus_method: vote
      model: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    - name: "red_pipeline"
      red_mode: pipeline
      blue_mode: single
      model: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    - name: "adversarial_debate"
      red_mode: single
      blue_mode: single
      verification_mode: debate
      model: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

---

## Valid Values Reference

### Models

#### AWS Bedrock Models

| Model ID | Name | Notes |
|----------|------|-------|
| `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Claude 3.5 Sonnet | Best quality |
| `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Claude 3.5 Haiku | Fast, cost-effective |
| `anthropic.claude-3-5-sonnet-20241022-v2:0` | Claude 3.5 Sonnet | Non-cross-region |
| `anthropic.claude-3-5-haiku-20241022-v1:0` | Claude 3.5 Haiku | Non-cross-region |
| `amazon.nova-pro-v1:0` | Amazon Nova Pro | Good balance |
| `amazon.nova-lite-v1:0` | Amazon Nova Lite | Fast |
| `amazon.nova-micro-v1:0` | Amazon Nova Micro | Fastest |
| `us.meta.llama3-2-90b-instruct-v1:0` | Llama 3.2 90B | Open source |
| `us.meta.llama3-2-11b-instruct-v1:0` | Llama 3.2 11B | Smaller Llama |
| `mistral.mistral-large-2407-v1:0` | Mistral Large | Mistral's best |

!!! tip "Cross-Region Inference"
    Models prefixed with `us.` use cross-region inference and have higher availability.

### Difficulty Levels

| Level | Vulnerabilities | Stealth | Description |
|-------|-----------------|---------|-------------|
| `easy` | 2-3 | Low | Obvious misconfigurations |
| `medium` | 3-4 | Medium | Mixed obvious and subtle |
| `hard` | 4-5 | High | Stealthy, evasion-focused |

### Languages

| Value | Description |
|-------|-------------|
| `terraform` | HashiCorp Terraform HCL |
| `cloudformation` | AWS CloudFormation YAML |

### Cloud Providers

| Value | Description |
|-------|-------------|
| `aws` | Amazon Web Services |
| `azure` | Microsoft Azure |
| `gcp` | Google Cloud Platform |

!!! note
    Azure and GCP support is limited. AWS has the most complete vulnerability coverage.

### Red Team Modes

| Mode | Agents | Description |
|------|--------|-------------|
| `single` | 1 | Single agent generates everything |
| `pipeline` | 4 | Architect → Selector → Generator → Reviewer |

### Blue Team Modes

| Mode | Agents | Description |
|------|--------|-------------|
| `single` | 1 | Single agent analyzes code |
| `ensemble` | 3+1 | Security + Compliance + Architecture + Consensus |

### Consensus Methods

Used when `blue_team_mode: ensemble`:

| Method | Description |
|--------|-------------|
| `debate` | LLM-based discussion to resolve conflicts |
| `vote` | Majority agreement (≥2 of 3 specialists) |
| `union` | All unique findings from all specialists |
| `intersection` | Only findings all specialists agree on |

### Verification Modes

| Mode | Description |
|------|-------------|
| `standard` | Direct Judge scoring |
| `debate` | Prosecutor vs Defender debate per finding |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_DEFAULT_REGION` | AWS region for Bedrock | `us-west-2` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | From AWS CLI |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | From AWS CLI |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## Example Configurations

### Quick Test (9 games)

```yaml
name: "Quick Test"
models:
  - id: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    role: both
difficulties: [easy, medium, hard]
scenarios:
  - "Create an S3 bucket"
  - "Create an EC2 instance"
  - "Create a VPC"
settings:
  repetitions: 1
batch_experiments:
  enabled: true
  model_combinations:
    - red: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
      blue: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
realtime_experiments:
  enabled: false
```

### Model Comparison (54 games)

```yaml
name: "Model Comparison"
models:
  - id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
  - id: "amazon.nova-pro-v1:0"
  - id: "us.meta.llama3-2-90b-instruct-v1:0"
difficulties: [easy, medium, hard]
scenarios:
  - "Create an S3 bucket for healthcare PHI"
  - "Create a VPC with security groups"
settings:
  repetitions: 3
batch_experiments:
  enabled: true
  model_combinations:
    # Same model Red vs Blue
    - red: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
      blue: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    - red: "amazon.nova-pro-v1:0"
      blue: "amazon.nova-pro-v1:0"
    - red: "us.meta.llama3-2-90b-instruct-v1:0"
      blue: "us.meta.llama3-2-90b-instruct-v1:0"
```

### Multi-Agent Study (27 games)

```yaml
name: "Multi-Agent Modes"
models:
  - id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
difficulties: [medium]
scenarios:
  - "Create an S3 bucket"
  - "Create a VPC"
  - "Create an RDS database"
settings:
  repetitions: 3
batch_experiments:
  enabled: false
realtime_experiments:
  enabled: true
  modes:
    - name: "baseline"
      red_mode: single
      blue_mode: single
    - name: "ensemble_vote"
      red_mode: single
      blue_mode: ensemble
      consensus_method: vote
    - name: "pipeline_attack"
      red_mode: pipeline
      blue_mode: single
```
