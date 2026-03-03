# Experiments

Adversarial IaC Benchmark — Experiment Registry

**Region**: us-east-1 | **Target venue**: Computers & Security / IEEE SecDev | **All models via Amazon Bedrock**

## Experiment Overview

| ID | Name | Games | Model(s) | Key Question | Status |
|----|------|-------|----------|-------------|--------|
| **E1** | Model Capability Stratification | 1,348 | Sonnet, Nova Premier, Nova Pro, Llama 3.3, Haiku | How do different LLMs compare at IaC security detection? | Complete (v2) |
| **E2** | Multi-Agent Ablation | 189 | Haiku (all conditions) | Do multi-agent architectures improve attack/defense? | Complete (original) |
| **E3** | Novel vs Database Vulnerabilities | 178 | Sonnet | Genuine security reasoning or pattern matching? | Complete (v3, with manifest gate) |
| **E4** | Difficulty Scaling | 90 | Llama 3.3 (new) + reuse Sonnet/Nova Pro/Haiku | Does difficulty produce expected evasion gradients? | Complete (v2) |
| **E5** | Debate Verification | 116 | Haiku (both conditions) | Does adversarial debate improve verification? | Complete (original) |
| **E1-S** | DeepSeek-R1 Supplementary | 90 | DeepSeek-R1 Blue, Sonnet Red | Does reasoning specialization improve detection? | Complete |
| **E1-S-Q** | Qwen3-Coder Supplementary | 90 | Qwen3-Coder Blue, Sonnet Red | Does code specialization improve detection? | Complete |

**Total: ~2,101 games across 7 experiments**

## Canonical Model Catalog

| Tier | Short Name | Bedrock Model ID | Role | Experiments |
|------|-----------|-----------------|------|-------------|
| Frontier | Sonnet 3.5 | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Red + Blue | E1, E2, E3 |
| Frontier | Nova Premier | `us.amazon.nova-premier-v1:0` | Blue only | E1 |
| Strong | Nova Pro | `amazon.nova-pro-v1:0` | Red + Blue | E1, E4 |
| Strong | Llama 3.3 70B | `us.meta.llama3-3-70b-instruct-v1:0` | Red + Blue | E1, E4 |
| Efficient | Haiku 3.5 | `anthropic.claude-3-5-haiku-20241022-v1:0` | Red + Blue | E2, E4, E5 |
| Reasoning | DeepSeek-R1 | `us.deepseek.r1-v1:0` | Blue only | E1-S |
| Code-Spec | Qwen3-Coder | `qwen.qwen3-coder-30b-a3b-v1:0` | Blue only | E1-S-Q |

## Results Directory

```
experiments/results/
├── exp-20260228_060523/       # E2: Multi-Agent Ablation (original, valid)
├── exp-20260228_142503/       # E5: Debate Verification (original, valid)
├── exp3_novel_v2/             # E3: Novel vs Database (v3, manifest gate)
├── exp1_stratification_v2/    # E1: Model Stratification (v2, corrected catalog)
├── exp4_difficulty_v2/        # E4: Difficulty Scaling (v2, Llama 3.3)
├── exp1s_deepseek_r1/         # E1-S: DeepSeek-R1 Supplementary
└── exp1s_qwen3_coder/         # E1-S-Q: Qwen3-Coder Supplementary
```

Each result folder contains its own README with experiment details, key findings, and methodology notes.

## Execution History

### Round 1 (Original, Feb 27–28 2026)
- 1,107 games across E1–E5
- Issues discovered: wrong Llama version (3.1 vs 3.3), Nova Premier never ran, manifest validation bug in E3, Haiku undocumented in catalog

### Round 2 (Re-run, Mar 1–3 2026)
- Corrected model catalog per [rerun_plan.pdf](../rerun_plan.pdf)
- E3 re-run with manifest validation gate (mandatory)
- E1 re-run with Nova Premier + Llama 3.3 correction
- E4 re-run with Llama 3.3 only (Sonnet/Nova Pro/Haiku reused from round 1)
- E2, E5 kept from round 1 (findings valid, no model change needed)
- E1-S and E1-S-Q added as new supplementary experiments

### Framework Fixes Applied
- **Manifest Validation Gate**: Trivy/Checkov verify Red Team claims before scoring
- **Source Label Instrumentation**: `is_novel`/`rule_source` on every manifest entry
- **DeepSeek-R1 Support**: Reasoning block filtering in all agents
- **Response Sanitizer**: `<think>` block stripping, markdown fence removal

## Config Files

```
experiments/config/
├── E1_model_comparison_v2.yaml     # 450 games, 5 model combos
├── E2_multiagent_ablation.yaml     # 189 games, 4 conditions
├── E3_novel_vs_database_v2.yaml    # 180 games, 3 source conditions
├── E4_difficulty_scaling_v2.yaml   # 90 games, Llama 3.3 only
├── E5_debate_verification.yaml     # 116 games, 2 conditions
├── E1S_deepseek_r1.yaml            # 90 games, hard only
├── E1S_qwen3_coder.yaml            # 90 games, hard only
└── archive/                        # Superseded v1 configs
```

## Analysis

```bash
# Statistical analysis for any experiment
python scripts/analyze_experiments.py experiments/results/exp1_stratification_v2 --latex

# E3 adjusted analysis (ground truth quality)
python scripts/e3_adjusted_analysis.py

# Paper analysis notebook
jupyter notebook notebooks/04_paper_analysis.ipynb
```

## Key Findings (Summary)

1. **E3**: Novel vuln adjusted recall (89.5%) is statistically indistinguishable from database (95.0%), p=0.158 — genuine security reasoning confirmed. But 56.3% of novel claims are phantom (hallucinated), making manifest validation load-bearing.

2. **E1**: Nova Pro ties Sonnet (81.1% F1) despite being Strong tier. Precision (64–89%) is the bottleneck, not recall (>88%).

3. **E1-S**: DeepSeek-R1 achieves highest F1 (91.5%) and precision (89.0%) of any model — reasoning specialization resolves the precision bottleneck.

4. **E4**: Difficulty inversion confirmed across all models — F1 increases with difficulty (easy 66.8% → hard 88.2%).

5. **E2**: Multi-agent arms race — full multi-agent evasion (31.7%) is 4× baseline (8.2%).

6. **E5**: Debate verification hurts — evasion 5× higher (10.3% vs 2.2%).
