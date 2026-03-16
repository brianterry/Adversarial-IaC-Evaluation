# E4: Difficulty Scaling (v2 — Llama 3.3 Correction)

**Experiment ID**: exp4_difficulty_v2
**Date**: March 2, 2026
**Status**: Complete (90 games, 0 failures)
**Config**: `experiments/config/E4_difficulty_scaling_v2.yaml`

## Design

Validates that difficulty levels produce consistent recall gradients across models. This run adds Llama 3.3 70B only — Sonnet, Nova Pro, and Haiku results reused from original E4 (round 1).

| Model | Source | Games |
|-------|--------|-------|
| Llama 3.3 70B | **New (this run)** | 90 |
| Sonnet | Reused from round 1 | (original data) |
| Nova Pro | Reused from round 1 | (original data) |
| Haiku | Reused from round 1 | (original data) |

**Difficulty**: Easy, Medium, Hard (30 games each)
**Scenarios**: 10

## Change from Original E4

Llama 3.1 70B replaced with Llama 3.3 70B (`us.meta.llama3-3-70b-instruct-v1:0`). All other models correct and reused.

## Key Results (Llama 3.3 70B)

| Difficulty | F1 | Evasion |
|-----------|-----|---------|
| Easy | 59.5% | 3.3% |
| Medium | 71.3% | 7.8% |
| Hard | 84.1% | 8.7% |

## Combined Results (All 4 Models)

| Model | Easy F1 | Medium F1 | Hard F1 |
|-------|---------|-----------|---------|
| Sonnet | 68.2% | 78.8% | 91.3% |
| Nova Pro | 65.5% | 84.9% | 86.6% |
| Haiku | 66.7% | 76.4% | 83.9% |
| Llama 3.3 | 59.5% | 71.3% | 84.1% |

## Key Finding: Difficulty Inversion is Universal

The inversion (F1 increases with difficulty) holds for **all 4 models** including the corrected Llama 3.3. Evasion rates remain flat (~3–9%) while F1 rises, confirming that difficulty modulates code complexity and false positive rates, not detection difficulty.

This is a structural property of the benchmark, not a model-specific artifact.

## Analysis

```bash
python scripts/analyze_experiments.py experiments/results/exp4_difficulty_v2 --type e4 --latex
```

## Files

- `results.csv` — Per-game metrics (Llama 3.3 only)
- `summary.json` — Aggregate statistics
- `progress.json` — Execution log
- `config.json` — Full experiment configuration

**Note**: To produce the full 4-model E4 table, merge this CSV with the original E4 Sonnet/Nova Pro/Haiku data.
