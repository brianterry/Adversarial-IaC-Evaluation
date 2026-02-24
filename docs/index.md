# Adversarial IaC Evaluation

**Red Team vs Blue Team evaluation framework for LLM security in Infrastructure-as-Code**

<div class="grid cards" markdown>

-   :material-sword:{ .lg .middle } **Red Team Agent**

    ---

    Generates plausible but vulnerable IaC that attempts to evade detection

    [:octicons-arrow-right-24: Learn more](concepts/game-flow.md)

-   :material-shield:{ .lg .middle } **Blue Team Agent**

    ---

    Detects vulnerabilities using LLM reasoning and static analysis tools

    [:octicons-arrow-right-24: Learn more](concepts/game-flow.md)

-   :material-scale-balance:{ .lg .middle } **Judge System**

    ---

    Scores matches between injected vulnerabilities and detections

    [:octicons-arrow-right-24: Scoring details](concepts/scoring.md)

-   :material-chart-line:{ .lg .middle } **Research Insights**

    ---

    Discover findings from our adversarial evaluation experiments

    [:octicons-arrow-right-24: View findings](research/findings.md)

</div>

## Research Question

> *How well can LLMs generate and detect security vulnerabilities in Infrastructure-as-Code?*

This project implements a game-theoretic evaluation framework where:

1. **Red Team** (attacker) generates Terraform code with hidden vulnerabilities
2. **Blue Team** (defender) attempts to detect all security flaws
3. **Judge** scores the match using precision, recall, and F1 metrics

## Key Findings

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Avg F1 Score** | 58.6% | Moderate detection effectiveness |
| **Avg Evasion Rate** | 23.8% | ~1 in 4 vulnerabilities escape detection |
| **Trivy Detection** | 0% | Static tools miss LLM-generated vulnerabilities |

!!! warning "Critical Finding"
    **Trivy found zero vulnerabilities** in LLM-generated code, while LLMs achieved 59% detection—demonstrating a fundamental semantic gap between pattern-matching and reasoning-based security analysis.

## Quick Start

```bash
# Clone with submodule
git clone --recursive https://github.com/brianterry/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation

# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run a game
python -m src.cli game \
    --scenario "Create S3 bucket for PHI data" \
    --difficulty medium
```

[:material-rocket-launch: Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[:material-github: View on GitHub](https://github.com/brianterry/Adversarial-IaC-Evaluation){ .md-button }

## Why This Research Matters

This work introduces the **first adversarial game-theoretic framework** for evaluating LLM security capabilities in Infrastructure-as-Code. Unlike existing benchmarks that rely on static vulnerability datasets, our approach **generates its own ground truth** through Red Team manifests—solving the critical problem of labeled data scarcity in IaC security research.

## Citation

```bibtex
@inproceedings{terry2025adversarial,
  title={Adversarial Evaluation of Multi-Agent LLM Systems 
         for Secure Infrastructure-as-Code},
  author={Terry, Brian},
  year={2025}
}
```
