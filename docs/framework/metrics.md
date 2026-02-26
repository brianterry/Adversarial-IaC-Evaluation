# Scoring Metrics

## Core Metrics

### Precision

$$\text{Precision} = \frac{TP}{TP + FP}$$

**Interpretation**: Of all findings reported, how many were real vulnerabilities?

- High precision = Few false positives
- Low precision = Many false alarms

### Recall

$$\text{Recall} = \frac{TP}{TP + FN}$$

**Interpretation**: Of all injected vulnerabilities, how many were detected?

- High recall = Good detection coverage
- Low recall = Missing vulnerabilities

### F1 Score

$$F1 = 2 \cdot \frac{P \cdot R}{P + R}$$

**Interpretation**: Balanced measure of precision and recall.

### Evasion Rate

$$\text{Evasion} = 1 - \text{Recall}$$

**Interpretation**: Fraction of vulnerabilities that evaded detection.

---

## Validation Metrics

### Manifest Accuracy

$$\text{Manifest Accuracy} = \frac{\text{Confirmed Vulns}}{\text{Claimed Vulns}}$$

**Interpretation**: Percentage of Red Team claims verified by static tools.

- High accuracy = Red Team generated real vulnerabilities
- Low accuracy = Potential hallucinations

### Hallucination Rate

$$\text{Hallucination Rate} = 1 - \text{Manifest Accuracy}$$

**Interpretation**: Percentage of Red Team claims NOT found by static tools.

### Corroboration Rate

$$\text{Corroboration Rate} = \frac{\text{Corroborated Matches}}{\text{Total Matches}}$$

**Interpretation**: Percentage of matches confirmed by Red + Blue + Static Tool.

- High rate = Strong external validation
- Provides non-LLM anchor for ground truth

---

## Inter-Rater Reliability (Multi-Model Consensus)

### Cohen's Kappa (κ)

$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

Where:
- $p_o$ = observed agreement between two raters
- $p_e$ = expected agreement by chance

**Interpretation:**

| κ Range | Interpretation |
|---------|---------------|
| < 0.20 | Poor |
| 0.21 - 0.40 | Fair |
| 0.41 - 0.60 | Moderate |
| 0.61 - 0.80 | Substantial |
| 0.81 - 1.00 | Almost Perfect |

**Target:** κ > 0.70 for publication-quality results.

### Pairwise Kappa

When using 3 models (e.g., GPT-4, Claude, Gemini), compute κ for each pair:

```json
{
  "pairwise_kappa": {
    "gpt4_vs_claude": 0.82,
    "claude_vs_gemini": 0.78,
    "gpt4_vs_gemini": 0.85
  },
  "mean_kappa": 0.817
}
```

### Agreement Rate

$$\text{Agreement Rate} = \frac{\text{Unanimous Judgments}}{\text{Total Judgments}}$$

Simple percentage of cases where all models agree.

---

## Aggregation

For experiments with multiple games:

```python
# Macro average (per-game)
avg_precision = mean([game.precision for game in games])

# Micro average (per-vulnerability)
total_tp = sum([game.true_positives for game in games])
total_fp = sum([game.false_positives for game in games])
micro_precision = total_tp / (total_tp + total_fp)
```

## Recommended Reporting

For publication, report:

| Metric | How to Report |
|--------|--------------|
| Core metrics | Mean ± std across games |
| Manifest accuracy | Mean ± std |
| Corroboration rate | Mean ± std |
| Inter-rater κ | Pairwise + mean |
