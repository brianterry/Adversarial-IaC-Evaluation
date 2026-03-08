# Batch Experiments

Run multiple games across model combinations and scenarios using YAML config.

## Usage

```bash
python scripts/run_experiment.py --config experiments/config/E1_model_comparison_v2.yaml --region us-east-1
```

## Minimal Config

```yaml
name: "My Experiment"
region: "us-east-1"
language: terraform
cloud_provider: aws

difficulties: [easy, medium, hard]
scenarios:
  - "Create an S3 bucket for logs"
  - "Create a VPC with subnets"

red_settings:
  red_team_mode: single
  red_strategy: balanced
  red_vuln_source: database

blue_settings:
  blue_team_mode: single
  blue_strategy: comprehensive
  detection_mode: llm_only

judge_settings:
  use_llm_judge: true
  use_trivy: false
  use_checkov: false

settings:
  repetitions: 3
  delay_between_games: 2
  output_dir: "experiments/results/my_exp"

batch_experiments:
  enabled: true
  model_combinations:
    - red: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
      blue: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
```

## Full Example (with Backends)

```yaml
name: "E1-S2: Qwen3.5 Thinking Mode"
region: "us-east-1"
language: terraform
cloud_provider: aws

difficulties: [hard]
scenarios:
  - "Create an S3 bucket for healthcare PHI data with HIPAA compliance"
  - "Create a VPC with public and private subnets"

red_settings:
  red_team_mode: single
  red_strategy: balanced
  red_vuln_source: database

blue_settings:
  blue_team_mode: single
  blue_strategy: comprehensive
  detection_mode: llm_only

judge_settings:
  use_llm_judge: true
  use_trivy: true
  use_checkov: true

settings:
  repetitions: 3
  output_dir: "experiments/results/E1S2"
  delay_between_games: 2
  save_intermediate: true

batch_experiments:
  enabled: true
  model_combinations:
    - name: "qwen35_thinking"
      red: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
      blue: "qwen3.5-plus"
      blue_backend_type: direct_api
      blue_thinking_mode: true
      blue_backend_extra:
        base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
        api_key_env: "DASHSCOPE_API_KEY"
```

## Model Combination Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `red` | str | - | Red Team model ID |
| `blue` | str | - | Blue Team model ID |
| `name` | str | - | Label for this combo |
| `blue_backend_type` | str | bedrock | bedrock, direct_api, sagemaker |
| `blue_thinking_mode` | bool | false | Enable reasoning mode |
| `blue_backend_extra` | dict | {} | Backend config (base_url, api_key_env, etc.) |
| `red_backend_type` | str | bedrock | Same options as blue |
| `red_thinking_mode` | bool | false | Enable reasoning for Red |
| `red_backend_extra` | dict | {} | Red Team backend config |

## Script Options

```bash
python scripts/run_experiment.py --config my_config.yaml --region us-east-1 [--output dir] [--delay 2] [--upload-to-s3]
```
