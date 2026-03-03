# E2: Multi-Agent Ablation

**Experiment ID**: exp-20260228_060523
**Date**: February 28, 2026
**Status**: Complete (original run, valid — no re-run needed)

## Design

Tests whether multi-agent architectures improve attack and defense performance.

| Condition | Red Team Mode | Blue Team Mode | Games |
|-----------|--------------|----------------|-------|
| Baseline | Single | Single | ~47 |
| Red Pipeline | Pipeline (4-stage) | Single | ~47 |
| Blue Ensemble | Single | Ensemble (3 specialists) | ~47 |
| Full Multi-Agent | Pipeline | Ensemble | ~47 |

**Model**: Claude 3.5 Haiku (all conditions) — deliberate cost-control choice that preserves within-experiment comparability.

**Difficulty**: Medium and Hard

## Key Results

| Condition | F1 | Evasion Rate |
|-----------|-----|-------------|
| Baseline | 77.9% | 8.2% |
| Red Pipeline | 82.7% | 12.9% |
| Blue Ensemble | 84.9% | 5.2% |
| Full Multi-Agent | 68.3% | 31.7% |

## Key Finding: Arms Race Asymmetry

When both teams scale to multi-agent, **Red Team dominates** — evasion explodes from 8.2% to 31.7% (4x increase). Attack coordination scales more effectively than defense coordination. Blue ensemble alone reduces evasion (5.2%), but the benefit is overwhelmed when Red also scales up.

## Why Not Re-Run

- Haiku is consistent across all four conditions — no model ID errors
- The arms race finding is internally valid and directionally clear
- Re-running introduces no new information
- Haiku as cost-control model is a defensible experimental design choice (document in §3.7)

## Files

- `results.csv` — Per-game metrics
- `summary.json` — Aggregate statistics
- `progress.json` — Execution log
- `config.json` — Full experiment configuration
