# E5: Debate Verification

**Experiment ID**: exp-20260228_142503
**Date**: February 28, 2026
**Status**: Complete (original run, valid — no re-run needed)

## Design

Tests whether adversarial debate verification improves finding quality.

| Condition | Verification Mode | Games |
|-----------|------------------|-------|
| Standard | Direct judge scoring | 58 |
| Debate | Prosecutor vs Defender per finding | 58 |

**Model**: Claude 3.5 Haiku (both conditions)

**Difficulty**: Medium and Hard

## Key Results

| Condition | F1 | Evasion Rate |
|-----------|-----|-------------|
| Standard | 81.1% | 2.2% |
| Debate | 79.3% | 10.3% |

## Key Finding: Debate Hurts Performance

Adversarial debate verification **increases evasion 5x** (10.3% vs 2.2%). The debate process over-corrects — the Defender agent argues valid findings away as false positives. Adding verification complexity does not monotonically improve performance.

This mirrors the E2 finding: multi-agent defense can introduce coordination costs that exceed the benefits.

## Why Not Re-Run

- Haiku is consistent across both conditions — no model ID errors
- The finding is internally valid and surprising (counter-hypothesis)
- Re-running introduces no new information

## Files

- `results.csv` — Per-game metrics
- `summary.json` — Aggregate statistics
- `progress.json` — Execution log
- `config.json` — Full experiment configuration
