# Running Experiments

Guide to running batch experiments and analyzing results.

## Experiment Workflow

```
1. Create config → 2. Run experiment → 3. View results → 4. Analyze
```

## Step 1: Create Configuration

Create a YAML file in `configs/`:

```yaml
# configs/my_experiment.yaml
experiment:
  name: "model_comparison"
  description: "Compare Haiku vs Sonnet security detection"

models:
  - id: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    name: "Haiku"
  - id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    name: "Sonnet"

difficulties:
  - "medium"
  - "hard"

languages:
  - name: "terraform"
    provider: "aws"

scenarios:
  - domain: "storage"
    description: "Create S3 bucket for healthcare PHI data"
  - domain: "compute"
    description: "Create Lambda function processing payments"
```

**This creates: 4 models × 2 difficulties × 2 scenarios = 16 games**

## Step 2: Run Experiment

```bash
python -m src.cli experiment \
    --config configs/my_experiment.yaml \
    --output-dir experiments/model_comparison
```

### Progress Output

```
╭─────────── Running Experiment ───────────╮
│ Name: model_comparison                   │
│ Total Games: 16                          │
│ Config: configs/my_experiment.yaml       │
╰──────────────────────────────────────────╯

[1/16] storage | medium | Haiku vs Haiku
  🔴 Red Team generating... done (4.2s)
  🔵 Blue Team analyzing... done (3.8s)
  ⚖️ Scoring... F1: 75.0%

[2/16] storage | medium | Haiku vs Sonnet
  🔴 Red Team generating... done (4.1s)
  🔵 Blue Team analyzing... done (5.2s)
  ⚖️ Scoring... F1: 83.3%

...

✅ Experiment complete: 16/16 games successful
📁 Results saved to: experiments/model_comparison/exp_20260220_130000
```

## Step 3: View Results

### Quick Summary

```bash
python -m src.cli show \
    --experiment experiments/model_comparison/exp_20260220_130000
```

### Detailed Results

```bash
python -m src.cli show \
    --experiment experiments/model_comparison/exp_20260220_130000 \
    --detailed
```

### Output Structure

```
experiments/model_comparison/exp_20260220_130000/
├── experiment_summary.json    # Aggregate metrics
├── tool_comparison.json       # LLM vs Trivy vs Checkov
├── games/                     # Individual game results
│   ├── game_001/
│   │   ├── red_team/
│   │   │   ├── main.tf
│   │   │   └── vulnerability_manifest.json
│   │   ├── blue_team/
│   │   │   └── findings.json
│   │   └── scores.json
│   ├── game_002/
│   └── ...
└── hybrid_results/            # If hybrid mode enabled
    └── hybrid_summary.json
```

## Analyzing Results

### Using Python

```python
import json
import pandas as pd

# Load results
with open('experiments/model_comparison/exp_20260220_130000/experiment_summary.json') as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data['results'])

# Analyze by difficulty
print(df.groupby('difficulty')[['f1_score', 'evasion_rate']].mean())

# Analyze by model
print(df.groupby('red_model')['evasion_rate'].mean())
print(df.groupby('blue_model')['recall'].mean())
```

### Using Jupyter

See `notebooks/02_run_experiment.ipynb` for interactive analysis:

```bash
jupyter notebook notebooks/02_run_experiment.ipynb
```

## Experiment Strategies

### Baseline Comparison

Test same model as both Red and Blue:

```yaml
models:
  - id: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    name: "Haiku"
```

*Question: Can a model find its own vulnerabilities?*

### Model vs Model

Test different models:

```yaml
models:
  - id: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    name: "Haiku"
  - id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    name: "Sonnet"
```

*Question: Does model capability affect security detection?*

### Difficulty Scaling

Test all difficulty levels:

```yaml
difficulties:
  - "easy"
  - "medium"
  - "hard"
```

*Question: How does difficulty affect evasion rate?*

### Domain Coverage

Test multiple infrastructure domains:

```yaml
scenarios:
  - domain: "storage"
    description: "S3 bucket"
  - domain: "compute"
    description: "Lambda function"
  - domain: "network"
    description: "VPC"
  - domain: "iam"
    description: "IAM roles"
  - domain: "database"
    description: "RDS instance"
```

*Question: Are some domains harder to secure?*

## Cost Estimation

Approximate costs per game (using Claude Haiku):

| Phase | Tokens | Cost |
|-------|--------|------|
| Red Team | ~2,000 | $0.002 |
| Blue Team | ~3,000 | $0.003 |
| **Total** | ~5,000 | **$0.005** |

**Example experiment costs:**
- 16 games: ~$0.08
- 100 games: ~$0.50
- 500 games: ~$2.50

!!! tip "Cost Control"
    Use Haiku for large experiments. Reserve Sonnet for targeted comparisons.

## Reproducibility

### Seed Results

For reproducible experiments:

```bash
# Record environment
pip freeze > experiment_requirements.txt

# Record configuration
cp configs/my_experiment.yaml experiments/run_001/config_used.yaml
```

### Git Integration

```bash
# Tag experiment
git tag -a "exp-model-comparison-v1" -m "Model comparison experiment"
git push origin --tags
```

## Troubleshooting

### Game Failures

```bash
# Check failed games
cat experiments/exp_xxx/experiment_summary.json | jq '.failed_games'

# Rerun specific scenario
python -m src.cli game \
    --scenario "Create S3 bucket..." \
    --difficulty hard
```

### Memory Issues

For large experiments:

```bash
# Run sequentially instead of parallel
python -m src.cli experiment \
    --config configs/large.yaml \
    --parallel 1
```

### Rate Limits

If hitting Bedrock rate limits:

```python
# Add delay between games (in experiment config)
experiment:
  delay_between_games: 2  # seconds
```

## Next Steps

- [CLI Reference](cli.md) - All commands
- [Research Findings](../research/findings.md) - What we discovered
