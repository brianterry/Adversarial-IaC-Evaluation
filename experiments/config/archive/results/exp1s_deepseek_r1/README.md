# E1-S: DeepSeek-R1 Supplementary

**Experiment ID**: exp1s_deepseek_r1
**Date**: March 3, 2026
**Status**: Complete (90 games, 0 failures)
**Config**: `experiments/config/E1S_deepseek_r1.yaml`

## Design

Tests whether reasoning-specialized architecture improves Blue Team detection at hard difficulty. Blue Team only — Red Team fixed to Sonnet for cross-condition comparability.

| Component | Model |
|-----------|-------|
| Red Team | Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`) |
| Blue Team | DeepSeek-R1 (`us.deepseek.r1-v1:0`) |

**Difficulty**: Hard only (where reasoning matters most)
**Scenarios**: 30 (same as E1)
**Repetitions**: 3

## Instrumentation Notes

DeepSeek-R1 required non-trivial instrumentation:

1. **Reasoning block filtering**: DeepSeek-R1 returns `reasoningContent` blocks via the Bedrock Converse API. These are explicitly discarded — only final text output is scored. Without this, the judge would evaluate reasoning traces as findings, contaminating scores.

2. **SDK upgrade**: Required boto3 1.42+ (from 1.35) for `reasoningContent` support in the Converse API response parser.

3. **Response sanitizer**: `<think>` block stripping as fallback for any reasoning content that leaks through as embedded text.

These are documented as methodological details — evidence that supplementary conditions require non-trivial work beyond invoking a different model ID.

## Key Results

| Metric | DeepSeek-R1 |
|--------|-------------|
| F1 | **91.5%** |
| Recall | 95.7% |
| Precision | **89.0%** |
| Evasion | 4.3% |
| n | 90 |

## Comparison (Hard Difficulty Only)

| Model | Tier | Hard F1 | Hard Precision | Hard Recall |
|-------|------|---------|---------------|-------------|
| **DeepSeek-R1** | **Reasoning** | **91.5%** | **89.0%** | 95.7% |
| Sonnet | Frontier | ~88% | ~72% | ~96% |
| Nova Pro | Strong | ~86% | ~77% | ~89% |
| Haiku | Efficient | ~84% | ~67% | ~98% |
| Llama 3.3 | Strong | 84.1% | ~60% | ~93% |

*Sonnet/Nova Pro/Haiku/Llama estimates from E1 hard-difficulty subset.*

## Key Finding: Reasoning Resolves the Precision Bottleneck

DeepSeek-R1 achieves the **highest F1 (91.5%) and highest precision (89.0%)** of any model tested. The reasoning specialization helps not just at catching vulnerabilities (recall is comparable) but at **not crying wolf** — 89% precision vs 60–77% for other models.

This directly addresses the E1 finding that precision is the universal bottleneck. Explicit chain-of-thought reasoning enables self-verification during analysis, reducing false positive rates.

## Paper Placement

Reported in a subsidiary table in §4.1 alongside Qwen3-Coder results. Not in the primary capability tier table (asymmetric design — Blue-only).

## Files

- `results.csv` — Per-game metrics
- `summary.json` — Aggregate statistics
- `progress.json` — Execution log
- `config.json` — Full experiment configuration
