# E1: Model Capability Stratification (v2 — Corrected Catalog)

**Experiment ID**: exp1_stratification_v2
**Date**: March 2, 2026
**Status**: Complete (1,348 games, 2 failed)
**Config**: `experiments/config/E1_model_comparison_v2.yaml`

## Design

Core benchmark comparing model capability tiers at IaC security detection. Same model serves as both Red and Blue Team (symmetric) except Nova Premier, which runs Blue-only with Sonnet Red Team.

| Model | Tier | Configuration | Games |
|-------|------|--------------|-------|
| Claude 3.5 Sonnet | Frontier | Symmetric | 270 |
| Nova Premier | Frontier | Blue-only (Sonnet Red) | 270 |
| Nova Pro | Strong | Symmetric | 268 |
| Llama 3.3 70B | Strong | Symmetric | 270 |
| Claude 3.5 Haiku | Efficient | Symmetric | 270 |

**Difficulty**: Easy, Medium, Hard
**Scenarios**: 30 (storage, compute, database, network, IAM, healthcare, financial, government)
**Repetitions**: 3

## Changes from Original E1

1. **Nova Premier added** — Frontier Amazon Blue-only comparator (new, 270 games)
2. **Llama 3.1 → Llama 3.3** — Corrected version (re-run, 270 games)
3. **Haiku documented** — Was in original E1 but unlabeled; now formally Efficient tier

## Key Results

| Model | Tier | F1 | Recall | Precision | Evasion | n |
|-------|------|-----|--------|-----------|---------|---|
| Nova Pro | Strong | **81.1%** | 88.7% | **76.5%** | 6.1% | 268 |
| Sonnet | Frontier | **81.1%** | 95.9% | 72.5% | 4.1% | 270 |
| Haiku | Efficient | 77.9% | **97.7%** | 67.1% | **2.3%** | 270 |
| Nova Premier | Frontier (Blue) | 76.3% | 94.0% | 66.3% | 6.0% | 270 |
| Llama 3.3 70B | Strong | 71.8% | 94.4% | 60.0% | 5.6% | 270 |

## Key Findings

1. **Nova Pro ties Sonnet** (81.1% F1 each) through different strategies — Nova Pro has higher precision (76.5% vs 72.5%), Sonnet has higher recall (95.9% vs 88.7%).

2. **Nova Premier disappoints** — Amazon's frontier model (76.3%) underperforms Sonnet and Nova Pro. Scale alone doesn't determine security detection capability.

3. **Haiku is the recall champion** (97.7%) but precision-bottlenecked (67.1%). Perfect "find everything, sort later" profile.

4. **Llama 3.3 lags** (71.8%) — open-source trails proprietary at IaC security, even with version correction.

5. **Precision is the universal bottleneck** — all models >88% recall, but precision ranges 60–77%.

6. **Difficulty inversion confirmed** — F1: Easy 66.6% < Medium 78.0% < Hard 88.2% across all models.

## Failures

2 games failed (both Nova Pro) — 99.9% completion rate. Errors: one model timeout, one list parsing issue.

## Analysis

```bash
python scripts/analyze_experiments.py experiments/results/exp1_stratification_v2 --type e1 --latex
```

## Files

- `results.csv` — Per-game metrics with model names
- `summary.json` — Aggregate statistics by difficulty, condition
- `progress.json` — Execution log with per-game timing
- `config.json` — Full experiment configuration
