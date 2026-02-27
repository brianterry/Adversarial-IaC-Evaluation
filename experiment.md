# Paper Experiment Plan

## Experiments Created

| ID | Config File | Purpose | Games | Runtime |
|----|-------------|---------|-------|---------|
| E0 | `E0_validation.yaml` | Smoke test | 6 | ~15 min |
| E1 | `E1_model_comparison.yaml` | Core LLM benchmark | 360 | 6-8 hrs |
| E2 | `E2_multiagent_ablation.yaml` | Multi-agent study | 200 | 4-6 hrs |
| E3 | `E3_novel_vs_database.yaml` | **Reasoning vs memorization** | 180 | 4-5 hrs |
| E4 | `E4_difficulty_scaling.yaml` | Difficulty validation | 270 | 5-6 hrs |
| E5 | `E5_debate_verification.yaml` | Debate evaluation | 120 | 3-4 hrs |

## Execution Commands

```bash
# 1. Validate setup
python scripts/run_experiment.py --config experiments/config/E0_validation.yaml

# 2. KEY EXPERIMENT - Run this first
python scripts/run_experiment.py --config experiments/config/E3_novel_vs_database.yaml

# 3. Core benchmark
python scripts/run_experiment.py --config experiments/config/E1_model_comparison.yaml

# 4. Remaining experiments
python scripts/run_experiment.py --config experiments/config/E4_difficulty_scaling.yaml
python scripts/run_experiment.py --config experiments/config/E2_multiagent_ablation.yaml
python scripts/run_experiment.py --config experiments/config/E5_debate_verification.yaml
```

## Paper Mapping

| Paper Section | Experiment | Key Finding |
|---------------|------------|-------------|
| Table 1: Model Comparison | E1 | Precision/Recall/F1 by model |
| Table 2: Multi-Agent Ablation | E2 | Pipeline vs Ensemble effects |
| Section 4.2: Reasoning vs Memorization | **E3** | Novel ≈ Database detection rates |
| Figure: Difficulty Scaling | E4 | Easy > Medium > Hard gradient |
| Section 4.4: Debate Verification | E5 | Precision gain from debate |

## Priority

1. **E3 is the key experiment** - addresses the "pattern memorization" reviewer concern
2. E1 provides core benchmark numbers
3. E4 validates the difficulty parameter works
4. E2/E5 support multi-agent architecture claims

## Analysis

After experiments complete:
```bash
jupyter notebook notebooks/03_analyze_results.ipynb
```

Includes:
- Stealth score correlation (Section 7)
- Lines of context analysis (Section 8)
- Statistical tests
