# Quick Start

Get up and running with your first adversarial game in 5 minutes.

## Run a Single Game

```bash
python -m src.cli game \
    --scenario "Create an S3 bucket for healthcare PHI data" \
    --red-model us.anthropic.claude-3-5-haiku-20241022-v1:0 \
    --blue-model us.anthropic.claude-3-5-haiku-20241022-v1:0 \
    --difficulty medium
```

This will:

1. 🔴 **Red Team** generates vulnerable Terraform code
2. 🔵 **Blue Team** analyzes the code for vulnerabilities  
3. ⚖️ **Judge** scores the match

## Understanding the Output

```
╭─────────────── Game Results ───────────────╮
│ Game ID: G-20260220_125729                 │
│                                            │
│ 🔴 Red Team:                               │
│   • Vulnerabilities injected: 3            │
│   • Stealth: ✓ Passed                      │
│                                            │
│ 🔵 Blue Team:                              │
│   • Findings: 4                            │
│                                            │
│ ⚖️ Scoring:                                │
│   • Precision: 75.00%                      │
│   • Recall: 100.00%                        │
│   • F1 Score: 85.71%                       │
│   • Evasion Rate: 0.00%                    │
╰────────────────────────────────────────────╯
```

## Run Red Team Only

Generate adversarial IaC without running detection:

```bash
python -m src.cli red-team \
    --scenario "Create Lambda function processing payments" \
    --difficulty hard \
    --output-dir output/red-team
```

## Run Blue Team on Existing Code

Analyze previously generated code:

```bash
python -m src.cli blue-team \
    --input-dir output/red-team/run_xxx \
    --mode llm_only
```

## View Experiment Results

```bash
python -m src.cli show \
    --experiment experiments/small_test/exp_20260220_125729 \
    --detailed
```

## Use Jupyter Notebooks

For interactive exploration:

1. **Single Game**: `notebooks/01_single_game.ipynb`
2. **Batch Experiments**: `notebooks/02_run_experiment.ipynb`

```bash
jupyter notebook notebooks/
```

## Next Steps

- [Game Flow](../concepts/game-flow.md) - Understand how games work
- [Scoring System](../concepts/scoring.md) - Learn about metrics
- [Running Experiments](../guide/experiments.md) - Run batch evaluations
