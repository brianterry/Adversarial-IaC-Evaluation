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
  red_vuln_source: mixed        # v2.3: test novel reasoning
  novel_ratio: 0.5               # 50% novel vulnerabilities

blue_settings:
  blue_team_mode: single
  blue_strategy: comprehensive
  detection_mode: llm_only
  precision_strategy: "precise"  # v2.3: verification filter

judge_settings:
  use_llm_judge: true
  use_trivy: true                # v2.3: manifest validation
  use_checkov: true
  use_cross_provider_judge: true # v2.3: phantom concordance mitigation

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
  red_vuln_source: mixed          # v2.3: test novel reasoning
  novel_ratio: 0.5

blue_settings:
  blue_team_mode: single
  blue_strategy: comprehensive
  detection_mode: llm_only
  precision_strategy: "precise"   # v2.3: verification filter

judge_settings:
  use_llm_judge: true
  use_trivy: true
  use_checkov: true
  use_cross_provider_judge: true  # v2.3: phantom concordance mitigation

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

## v2.3 Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `red_vuln_source` | str | mixed | `database`, `novel`, or `mixed` |
| `novel_ratio` | float | 0.5 | Fraction of novel vulnerabilities when `mixed` |
| `precision_strategy` | str | precise | `standard` or `precise` (two-pass verification) |
| `use_cross_provider_judge` | bool | true | Require cross-provider consensus for novel vulns |
| `blue_specialists` | int | 4 | Number of Blue ensemble specialists (auto-matches Red pipeline) |

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
