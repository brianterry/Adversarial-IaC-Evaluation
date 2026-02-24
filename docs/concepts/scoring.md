# Scoring System

The scoring system evaluates both Red and Blue Team performance using information retrieval metrics.

## Core Metrics

### Precision

> "Of all the vulnerabilities Blue Team reported, how many were real?"

$$
\text{Precision} = \frac{TP}{TP + FP}
$$

| Score | Interpretation |
|-------|----------------|
| 100% | Every report was a real vulnerability |
| 75% | 3 out of 4 reports were correct |
| 50% | Half were false positives |

!!! tip "High Precision = Trustworthy"
    A high-precision detector can be trusted when it raises an alert.

### Recall (Detection Rate)

> "Of all the vulnerabilities Red Team injected, how many did Blue find?"

$$
\text{Recall} = \frac{TP}{TP + FN}
$$

| Score | Interpretation |
|-------|----------------|
| 100% | Found every hidden vulnerability |
| 66% | Found 2 out of 3 |
| 33% | Missed most vulnerabilities |

!!! tip "High Recall = Thorough"
    A high-recall detector misses few vulnerabilities.

### F1 Score

> "Balanced score combining precision and recall"

$$
F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}
$$

| Score | Interpretation |
|-------|----------------|
| 80%+ | Excellent detection capability |
| 60-80% | Good, but room for improvement |
| <60% | Significant gaps |

### Evasion Rate

> "How many vulnerabilities did Red Team successfully hide?"

$$
\text{Evasion} = \frac{FN}{TP + FN} = 1 - \text{Recall}
$$

| Score | Interpretation |
|-------|----------------|
| 0% | Red Team failed—everything detected |
| 25% | 1 in 4 vulnerabilities escaped |
| 50%+ | Red Team dominated |

## Confusion Matrix

```
                    Blue Team Detection
                    ┌──────────┬──────────┐
                    │ Detected │  Missed  │
         ┌──────────┼──────────┼──────────┤
Red Team │  Exists  │    TP    │    FN    │  ← Real vulnerabilities
Injected │──────────┼──────────┼──────────┤
         │ Doesn't  │    FP    │    TN    │  ← Not a vulnerability
         └──────────┴──────────┴──────────┘
                         ↑          ↑
                    Blue claims  Blue quiet
```

### Definitions

| Symbol | Name | Meaning |
|--------|------|---------|
| **TP** | True Positive | Blue correctly found Red's vulnerability |
| **FP** | False Positive | Blue reported something that wasn't in manifest |
| **FN** | False Negative | Red's vulnerability that Blue missed |
| **TN** | True Negative | Not tracked (we focus on injected vulnerabilities) |

## Scoring Examples

### Example 1: Perfect Detection

```
Red Team injected: [No Encryption, Public Access, Weak IAM]
Blue Team found:   [No Encryption, Public Access, Weak IAM]

TP = 3, FP = 0, FN = 0
Precision = 100%, Recall = 100%, F1 = 100%, Evasion = 0%
```

### Example 2: Good Detection with False Positive

```
Red Team injected: [No Encryption, Public Access]
Blue Team found:   [No Encryption, Public Access, Missing Logging]

TP = 2, FP = 1, FN = 0
Precision = 66.7%, Recall = 100%, F1 = 80%, Evasion = 0%
```

### Example 3: Partial Detection

```
Red Team injected: [No Encryption, Public Access, Weak IAM, Debug Mode]
Blue Team found:   [No Encryption, Public Access]

TP = 2, FP = 0, FN = 2
Precision = 100%, Recall = 50%, F1 = 66.7%, Evasion = 50%
```

## Difficulty Impact

Our experiments show clear correlation between difficulty and evasion:

| Difficulty | Avg F1 | Avg Evasion |
|------------|--------|-------------|
| **Easy** | ~75% | ~10% |
| **Medium** | ~60% | ~25% |
| **Hard** | ~45% | ~40% |

!!! warning "Hard Mode"
    At hard difficulty, Red Team uses advanced stealth techniques that evade detection 4x more often than medium difficulty.

## Aggregate Metrics

For experiments with multiple games:

```python
# Per-game metrics are averaged
avg_f1 = mean([game.f1 for game in games])
avg_evasion = mean([game.evasion for game in games])

# Weighted by vulnerabilities
weighted_recall = sum(TP) / sum(TP + FN)
```

## Metric Trade-offs

### Security-First (Maximize Recall)
- Catch every vulnerability, even at cost of false positives
- High alert fatigue but safer

### Precision-First (Maximize Precision)
- Only report high-confidence findings
- Fewer alerts but might miss vulnerabilities

### Balanced (Maximize F1)
- Best overall compromise
- Used as primary metric in this research

## Next Steps

- [Judge Algorithm](judge.md) - How matches are determined
- [Research Findings](../research/findings.md) - See metrics in action
