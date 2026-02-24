# Batch Experiments

Run multiple games with different configurations.

## Using the Experiment Runner

```bash
python scripts/run_experiment.py \
    --config experiments/config/quick_test.yaml
```

## Configuration

```yaml
name: "My Experiment"
models:
  - id: "claude-3-5-haiku"
difficulties: [easy, medium, hard]
scenarios:
  - "Create an S3 bucket"
  - "Create a VPC"
settings:
  repetitions: 3
```
