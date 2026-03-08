# adversarial-iac experiment

Run an experiment from a configuration file.

## Usage

```bash
adversarial-iac experiment [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config`, `-c` | path | config/experiment_config.yaml | Experiment config file |
| `--dry-run` | flag | false | Show what would run without executing |

## Examples

### With default config

```bash
adversarial-iac experiment
```

### Dry run

```bash
adversarial-iac experiment --dry-run
```

### Custom config

```bash
adversarial-iac experiment -c my_experiment.yaml
```

## Batch Experiments

For full batch experiments across model combinations and scenarios, use the experiment runner script:

```bash
python scripts/run_experiment.py --config experiments/config/E1_model_comparison_v2.yaml --region us-east-1
```

See [Batch (YAML)](../experiments/batch.md) for the YAML schema and examples.
