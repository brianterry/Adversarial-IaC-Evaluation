# CLI Reference

Complete reference for all command-line interface commands.

## Global Options

```bash
python -m src.cli [OPTIONS] COMMAND [ARGS]
```

| Option | Description |
|--------|-------------|
| `--help` | Show help message |
| `--version` | Show version |

## Commands

### `game` - Run a Single Game

Run a complete Red vs Blue game.

```bash
python -m src.cli game [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--scenario` | ✅ | - | Infrastructure scenario description |
| `--red-model` | | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Red Team model ID |
| `--blue-model` | | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Blue Team model ID |
| `--difficulty` | | `medium` | `easy`, `medium`, or `hard` |
| `--mode` | | `llm_only` | Blue Team mode: `llm_only`, `tools_only`, `hybrid` |
| `--output-dir` | | `output/` | Output directory |

**Example:**
```bash
python -m src.cli game \
    --scenario "Create S3 bucket for PHI data with encryption" \
    --difficulty hard \
    --mode hybrid \
    --output-dir experiments/test_run
```

---

### `red-team` - Run Red Team Only

Generate adversarial IaC without Blue Team analysis.

```bash
python -m src.cli red-team [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--scenario` | ✅ | - | Infrastructure scenario |
| `--model` | | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Model ID |
| `--difficulty` | | `medium` | Difficulty level |
| `--language` | | `terraform` | `terraform` or `cloudformation` |
| `--provider` | | `aws` | Cloud provider |
| `--output-dir` | | `output/red-team/` | Output directory |

**Example:**
```bash
python -m src.cli red-team \
    --scenario "Lambda function with API Gateway" \
    --difficulty hard \
    --output-dir output/red-team
```

**Output Structure:**
```
output/red-team/run_20260220_130000/
├── main.tf              # Generated IaC
├── variables.tf         # Variables (if any)
├── vulnerability_manifest.json  # Secret list
└── metadata.json        # Run metadata
```

---

### `blue-team` - Run Blue Team Only

Analyze existing code for vulnerabilities.

```bash
python -m src.cli blue-team [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--input-dir` | ✅ | - | Directory containing IaC files |
| `--model` | | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Model ID |
| `--mode` | | `llm_only` | Detection mode |
| `--output-dir` | | `output/blue-team/` | Output directory |

**Example:**
```bash
python -m src.cli blue-team \
    --input-dir output/red-team/run_20260220_130000 \
    --mode hybrid \
    --output-dir output/blue-team
```

**Detection Modes:**

| Mode | Description |
|------|-------------|
| `llm_only` | Pure LLM semantic analysis |
| `tools_only` | Trivy + Checkov only |
| `hybrid` | LLM + static tools combined |

---

### `score` - Score a Game

Calculate metrics for a completed game.

```bash
python -m src.cli score [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--red-dir` | ✅ | - | Red Team output directory |
| `--blue-dir` | ✅ | - | Blue Team output directory |
| `--output-file` | | `scores.json` | Output file for scores |

**Example:**
```bash
python -m src.cli score \
    --red-dir output/red-team/run_20260220_130000 \
    --blue-dir output/blue-team/run_20260220_130500
```

---

### `experiment` - Run Batch Experiment

Run multiple games from a configuration file.

```bash
python -m src.cli experiment [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--config` | ✅ | - | YAML configuration file |
| `--output-dir` | | `experiments/` | Output directory |
| `--parallel` | | `1` | Parallel game execution |

**Example:**
```bash
python -m src.cli experiment \
    --config configs/small_test.yaml \
    --output-dir experiments/my_experiment \
    --parallel 2
```

---

### `show` - Display Experiment Results

View results from a completed experiment.

```bash
python -m src.cli show [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-e`, `--experiment` | ✅ | - | Path to experiment directory |
| `--detailed` | | `false` | Show per-game breakdown |

**Example:**
```bash
python -m src.cli show \
    --experiment experiments/my_experiment/exp_20260220_125729 \
    --detailed
```

**Output:**
```
╭─────────────── Experiment Summary ───────────────╮
│ Name: my_experiment                              │
│ Timestamp: 2026-02-20T12:57:29                   │
╰──────────────────────────────────────────────────╯

Aggregate Metrics:
  Total Games:    16
  Successful:     16
  Avg Precision:  71.4%
  Avg Recall:     76.2%
  Avg F1 Score:   58.6%
  Avg Evasion:    23.8%

By Difficulty:
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Difficulty  ┃ Games  ┃ Avg F1  ┃ Avg Evasion┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ medium      │ 8      │ 67.9%   │ 9.7%       │
│ hard        │ 8      │ 49.4%   │ 37.9%      │
└─────────────┴────────┴─────────┴────────────┘
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region for Bedrock |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_PROFILE` | AWS credential profile |

## Model IDs

Available Amazon Bedrock models:

| Short Name | Full Model ID |
|------------|---------------|
| Haiku | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| Sonnet | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |

## Next Steps

- [Configuration](configuration.md) - YAML config format
- [Running Experiments](experiments.md) - Batch evaluation guide
