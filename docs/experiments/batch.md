# Batch Experiments

Run multiple games with different configurations.

## Using the Experiment Runner

```bash
python scripts/run_experiment.py \
    --config experiments/config/E1_model_comparison_v2.yaml \
    --region us-east-1
```

## Configuration

```yaml
name: "My Experiment"
models:
  - id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
    name: "Claude 3.5 Sonnet"
difficulties: [easy, medium, hard]
scenarios:
  - "Create an S3 bucket for logs"
  - "Create a VPC with subnets"
language: terraform
cloud_provider: aws
settings:
  repetitions: 3
  delay_between_games: 2
  random_seed: 42                    # Optional: deterministic ordering
  manifest_accuracy_threshold: 0.5   # Optional: auto-halt on bad quality
batch_experiments:
  enabled: true
  model_combinations:
    - red: "anthropic.claude-3-5-sonnet-20241022-v2:0"
      blue: "anthropic.claude-3-5-sonnet-20241022-v2:0"
```
