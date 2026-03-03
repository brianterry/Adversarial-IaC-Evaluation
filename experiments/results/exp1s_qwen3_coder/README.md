# E1-S-Q: Qwen3-Coder Supplementary

**Experiment ID**: exp1s_qwen3_coder
**Date**: March 3, 2026
**Status**: Complete
**Config**: `experiments/config/E1S_qwen3_coder.yaml`

## Design

Tests whether code-specialized pretraining improves Blue Team detection at hard difficulty. Parallel structure to E1-S (DeepSeek-R1). Blue Team only — Red Team fixed to Sonnet.

| Component | Model |
|-----------|-------|
| Red Team | Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`) |
| Blue Team | Qwen3-Coder-30B (`qwen.qwen3-coder-30b-a3b-v1:0`) |

**Difficulty**: Hard only
**Scenarios**: 30 (same as E1 and E1-S)
**Repetitions**: 3

## Instrumentation Notes

Qwen3-Coder required markdown fence stripping — the model wraps JSON output in ` ```json ... ``` ` fences. The response sanitizer handles this automatically. No other special handling required (unlike DeepSeek-R1 which needed reasoning block filtering).

## Hypothesis

Qwen3-Coder's code-focused pretraining may improve detection of syntactic and structural misconfigurations (misconfigured resource attributes, missing encryption flags, incorrect policy syntax) but may underperform on semantic reasoning tasks (cross-resource IAM implications, compliance-level policy analysis) where general reasoning matters more.

## Comparison Table (Subsidiary — §4.1)

All models at hard difficulty, Blue Team only (Red Team = Sonnet):

| Model | Tier | Hard F1 | Hard Precision | Hard Recall |
|-------|------|---------|---------------|-------------|
| DeepSeek-R1 | Reasoning | 91.5% | 89.0% | 95.7% |
| Sonnet 3.5 | Frontier | ~88% | ~72% | ~96% |
| Qwen3-Coder | Code-Spec | TBD | TBD | TBD |

*Update with actual Qwen3-Coder results from this experiment.*

## Interpretation Guide

- **If Qwen3-Coder ≈ Sonnet**: Code specialization provides no detection advantage
- **If Qwen3-Coder > Sonnet**: Syntactic code understanding aids IaC detection
- **Compare Qwen vs DeepSeek**: Does syntactic or reasoning specialization help more?

## Paper Placement

Reported in the same subsidiary table as DeepSeek-R1 in §4.1. Not in the primary capability tier table.

## Files

- `results.csv` — Per-game metrics
- `summary.json` — Aggregate statistics
- `progress.json` — Execution log
- `config.json` — Full experiment configuration
