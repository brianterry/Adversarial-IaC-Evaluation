# Research Novelty

Why this work represents a novel contribution to security and AI research.

## The Core Innovation

This research introduces the **first adversarial game-theoretic framework** for evaluating LLM security capabilities in Infrastructure-as-Code—solving the fundamental "labeled data problem" that has limited prior research.

## The Problem We Solve

### The Labeled Data Paradox

Traditional security evaluation requires:
1. **Vulnerable code samples** (hard to collect ethically)
2. **Ground truth labels** (expensive expert annotation)
3. **Diverse scenarios** (limited public datasets)

!!! failure "Prior Approaches"
    - **Static datasets**: Outdated, not IaC-specific
    - **Manual labeling**: Expensive, doesn't scale
    - **Synthetic benchmarks**: Don't reflect real-world complexity

### Our Solution: Self-Generating Ground Truth

```
┌─────────────────────────────────────────────────────────┐
│  Traditional Approach          Our Approach             │
│  ─────────────────────         ────────────────         │
│  Dataset → Model → Evaluate    Red Team generates code  │
│     ↑                          Red Team provides labels │
│     │                          Blue Team detects        │
│  Expensive labeling            Judge scores match       │
│  Limited samples               ∞ samples possible       │
│  Stale data                    Always current           │
└─────────────────────────────────────────────────────────┘
```

## Novel Contributions

### 1. Adversarial Evaluation Framework

**First application** of game-theoretic adversarial testing to LLM security capabilities.

| Existing Work | Our Work |
|---------------|----------|
| LLMs generating code | LLMs generating *adversarial* code |
| LLMs detecting vulnerabilities | LLMs detecting *hidden* vulnerabilities |
| Static benchmarks | Dynamic Red vs Blue competition |

### 2. Self-Labeling Through Adversarial Generation

The Red Team's vulnerability manifest serves as **automatically-generated ground truth**:

```json
{
  "vulnerabilities": [
    {
      "id": "v1",
      "type": "encryption",
      "resource": "aws_s3_bucket.data",
      "technique": "Misleading HIPAA tag suggests compliance"
    }
  ]
}
```

**Benefits:**
- No manual labeling required
- Infinite scalable sample generation
- Labels reflect actual injected vulnerabilities

### 3. Controlled Difficulty Scaling

Systematic study of **how difficulty affects detection**:

| Difficulty | Evasion Rate | Research Value |
|------------|--------------|----------------|
| Easy | ~10% | Baseline capability |
| Medium | ~25% | Production-realistic |
| Hard | ~40% | Adversarial stress test |

### 4. LLM vs. Static Tools Comparison

**First empirical comparison** of LLM detection vs. Trivy/Checkov on AI-generated code.

!!! quote "Key Finding"
    "Trivy found zero vulnerabilities in LLM-generated IaC, while LLMs achieved 59% detection—revealing a semantic gap that existing tools cannot bridge."

### 5. Multi-Model Competition

Cross-model evaluation reveals **model-specific security characteristics**:

```
Can Claude find vulnerabilities it created?
Can Sonnet defend against Haiku's attacks?
Which model is the better attacker? Defender?
```

## Comparison to Prior Work

### LLM Code Security (Prior)
- Focus: Can LLMs write secure code?
- Method: Static analysis of generated code
- Limitation: No adversarial pressure

### Our Work
- Focus: Can LLMs detect hidden vulnerabilities?
- Method: Red Team actively tries to evade
- Advantage: Tests actual detection capability under attack

### IaC Security Research (Prior)
- Focus: Scanning existing infrastructure
- Method: Pattern matching (Trivy, Checkov)
- Limitation: Patterns designed for human code

### Our Work
- Focus: AI-generated infrastructure
- Method: Semantic LLM analysis + tool comparison
- Discovery: Static tools fail on AI code styles

### Adversarial ML (Prior)
- Focus: Input perturbations, model attacks
- Method: Gradient-based adversarial examples
- Domain: Images, NLP classification

### Our Work
- Focus: Security domain knowledge
- Method: Task-based adversarial generation
- Domain: Infrastructure code generation

## Research Impact

### For Security Research

1. **New evaluation methodology** for AI security tools
2. **Scalable benchmark generation** without manual labeling
3. **Quantitative metrics** for security capability

### For AI Safety

1. **Adversarial testing framework** for foundation models
2. **Capability evaluation** beyond standard benchmarks
3. **Red teaming methodology** for production AI

### For Industry

1. **Evidence that static tools need updates** for AI code
2. **Guidance for hybrid human-AI security review**
3. **Metrics for comparing security tools**

## Publications & Extensions

This work builds on:
- IEEE CARS 2025: "IaC Correctness Evaluation" (prior paper)

Planned extensions:
- Multi-agent collaboration for defense
- Cross-cloud generalization study
- Temporal evolution of vulnerabilities

## Cite This Work

```bibtex
@inproceedings{terry2026adversarial,
  title={Adversarial Evaluation of Multi-Agent LLM Systems 
         for Secure Infrastructure-as-Code},
  author={Terry, Brian},
  booktitle={Proceedings of [Conference]},
  year={2026}
}
```

## Next Steps

- [Research Findings](findings.md) - Detailed experimental results
- [Tool Comparison](tool-comparison.md) - LLM vs static tools
- [Getting Started](../getting-started/installation.md) - Run your own experiments
