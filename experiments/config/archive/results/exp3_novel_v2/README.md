# E3: Novel vs Database Vulnerabilities (v3 — Manifest Gate)

**Experiment ID**: exp3_novel_v2
**Date**: March 1–2, 2026
**Status**: Complete (v3 with manifest validation gate)
**Config**: `experiments/config/E3_novel_vs_database_v2.yaml`

## Design

Critical experiment comparing Red Team vulnerability sources to test genuine security reasoning vs pattern matching.

| Condition | Red Vuln Source | Games |
|-----------|----------------|-------|
| Database | 142 known Trivy rules | 60 |
| Novel | LLM generates from security principles | 59 |
| Mixed | 50% database, 50% novel | 59 |

**Model**: Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`)
**Difficulty**: Medium and Hard (easy excluded — ceiling effects mask recall differences)
**Tools**: Trivy + Checkov enabled for manifest validation gate

## Why This Is v3

- **v1** (original): Manifest validation was broken — phantom vulns scored as ground truth
- **v2**: Validation ran but gate didn't exclude phantoms from scoring
- **v3** (this run): Full manifest validation gate — phantom vulns excluded from scored ground truth. `scored_manifest.json` and `phantom_manifest.json` written per game.

## Key Results

### Standard Metrics (against full manifest)

| Condition | F1 | Recall | Evasion | n |
|-----------|-----|--------|---------|---|
| Database | 85.5% | 94.0% | 6.0% | 60 |
| Novel | 69.4% | 87.9% | 10.4% | 59 |
| Mixed | 75.6% | 90.5% | 7.8% | 59 |

### Ground Truth Quality

| Condition | Manifest Accuracy | Hallucination Rate |
|-----------|------------------|-------------------|
| Database | 86.6% | 13.4% |
| Novel | 43.5% | 56.5% |
| Mixed | 64.5% | 35.5% |

### Adjusted Metrics (confirmed vulnerabilities only)

| Condition | Adjusted Recall | 95% CI | n (games with confirmed vulns) |
|-----------|----------------|--------|-------------------------------|
| Database | 95.0% | ±3.3% | 60 |
| Novel | 89.5% | ±6.8% | 50 |

**Statistical test (adjusted recall)**: t=1.41, p=0.158 (ns), Cohen's d=0.29

### Phantom Concordance

| Condition | Phantom Concordance | Phantom/Total Detections |
|-----------|-------------------|-------------------------|
| Database | 13.3% | 31/226 |
| Novel | 56.6% | 122/213 |

## Key Findings

1. **Attacker Hallucination Asymmetry**: Database manifest accuracy 86.6% vs novel 43.5%. LLMs reliably inject known patterns but hallucinate 57% of novel vulnerabilities.

2. **Adjusted Recall — Genuine Reasoning Confirmed**: On tool-confirmed ground truth, novel recall (89.5%) is statistically indistinguishable from database (95.0%), p=0.158. When the ground truth is real, Blue Team detects novel vulnerabilities at equivalent rates.

3. **Phantom Concordance**: 56.6% of Blue Team "detections" in novel mode matched non-existent vulnerabilities. Both Red and Blue hallucinate the same patterns — a shared latent vulnerability space.

4. **Manifest Validation is Load-Bearing**: Without the gate, recall would have been reported against 56% phantom ground truth. Any adversarial benchmark without external tool validation has this problem latently.

## Analysis

```bash
python scripts/e3_adjusted_analysis.py
python scripts/analyze_experiments.py experiments/results/exp3_novel_v2 --type e3 --latex
```

## Files

- `results.csv` — Per-game metrics (F1, recall, precision, evasion, manifest_accuracy)
- `summary.json` — Aggregate statistics by condition
- `progress.json` — Execution log
- `config.json` — Full experiment configuration
- Per-game: `scored_manifest.json`, `phantom_manifest.json`, `manifest_validation.json`
