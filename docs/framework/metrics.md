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
