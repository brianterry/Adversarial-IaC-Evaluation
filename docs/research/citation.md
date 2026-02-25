# Citation & Research

If you use the Adversarial IaC Benchmark in your research, please cite our work.

## Key Contributions

This benchmark introduces several novel contributions to LLM security evaluation:

### 1. Adversarial Evaluation Framework

Unlike static benchmarks where models are tested on fixed datasets, our framework creates a **dynamic adversarial environment**:

- Red Team LLM actively tries to **evade detection**
- Blue Team LLM must detect **previously unseen** vulnerabilities  
- Judge uses **optimal bipartite matching** for fair scoring

This measures true security reasoning, not pattern memorization.

### 2. IaC-Specific Benchmark

First comprehensive benchmark focused on Infrastructure-as-Code security:

- **114 scenarios** across 18 domains
- **Industry compliance**: HIPAA, PCI-DSS, FedRAMP, SOC 2
- **Cloud-native patterns**: AWS, multi-service architectures
- **Terraform and CloudFormation** support

### 3. Multi-Agent Evaluation

Evaluates emerging LLM architectures for security:

- **Blue Team Ensemble**: Specialist agents + consensus voting
- **Red Team Pipeline**: Multi-stage attack generation
- **Adversarial Debate**: Finding verification through argumentation

### 4. Standardized Metrics

Reproducible evaluation with:

- **Precision, Recall, F1** for detection quality
- **Evasion Rate** for attack effectiveness
- **Hungarian algorithm** for optimal vulnerability-to-finding matching

---

## BibTeX

```bibtex
@software{adversarial_iac_bench_2026,
  author = {Terry, Brian},
  title = {Adversarial IaC Benchmark: An Adversarial Evaluation Framework for LLM Security in Infrastructure-as-Code},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/brianterry/Adversarial-IaC-Evaluation},
  note = {Open-source adversarial benchmark for evaluating LLM security capabilities in Infrastructure-as-Code}
}
```

## APA

Terry, B. (2026). *Adversarial IaC Benchmark: An Adversarial Evaluation Framework for LLM Security in Infrastructure-as-Code* [Computer software]. GitHub. https://github.com/brianterry/Adversarial-IaC-Evaluation

---

## Research Questions

The game enables investigation of:

| Research Area | Example Questions |
|--------------|-------------------|
| **Model Comparison** | How does Claude compare to GPT-4 at detecting IaC vulnerabilities? |
| **Adversarial Robustness** | Which models are most resistant to evasion techniques? |
| **Multi-Agent Systems** | Does ensemble consensus improve detection accuracy? |
| **Compliance Understanding** | Do LLMs understand HIPAA differently than PCI-DSS? |
| **Attack Strategies** | Which Red Team strategies achieve highest evasion rates? |
| **Defense Strategies** | Does iterative analysis improve recall? |
| **Tool Comparison** | How do LLMs compare to Trivy/Checkov for IaC scanning? |

---

## What to Include When Citing

When using the benchmark in research, please specify:

1. **Benchmark version**: Include commit hash or release version
2. **Models tested**: Which LLMs for Red and Blue teams
3. **Scenarios used**: Domains, count, and difficulty levels
4. **Evaluation modes**: Single, pipeline, ensemble, or debate
5. **Strategies**: Attack and defense strategies used
6. **Metrics reported**: Precision, recall, F1, evasion rate

## Example Usage in Papers

### Methods Section

> We evaluated LLM security capabilities using the Adversarial IaC Game v1.0 (Terry, 2026). 
> Our experiments ran 200 games with Claude 3.5 Sonnet (Red Team) vs Nova Pro (Blue Team)
> across healthcare and financial domains at medium difficulty (3-4 vulnerabilities per game). 
> We used Blue Team Ensemble mode with debate consensus. The Judge employed the Hungarian 
> algorithm for optimal vulnerability-to-finding matching.

### Results Section

> Table 1 shows detection performance across models. Claude 3.5 Sonnet achieved the highest
> recall (78%) but lower precision (71%) compared to Nova Pro (recall: 65%, precision: 89%).
> The Red Team achieved an average evasion rate of 28% across all experiments.

---

## Data Outputs

Each evaluation produces structured data suitable for analysis:

| Output | Format | Contents |
|--------|--------|----------|
| `red_team_manifest.json` | JSON | Ground truth vulnerabilities with types, locations |
| `blue_team_findings.json` | JSON | Detected issues with confidence, evidence |
| `game_result.json` | JSON | Scores, matches, timing, configuration |
| `code/*.tf` | HCL/YAML | Generated infrastructure code |
| `game.log` | Text | Full execution trace |

### Statistical Analysis

Results can be aggregated for statistical testing:

```python
import pandas as pd
from pathlib import Path
import json

# Load all game results
results = []
for game_dir in Path("output/games").iterdir():
    with open(game_dir / "game_result.json") as f:
        results.append(json.load(f))

df = pd.DataFrame(results)

# Compare models
df.groupby("blue_model")["recall"].agg(["mean", "std"])
```

---

## Related Work

This benchmark builds on and differs from:

- **SecBench** — Static security question answering (we use dynamic generation)
- **CyberSecEval** — Multi-domain security (we focus on IaC specifically)
- **VulnGen** — Vulnerability injection (we add adversarial detection evaluation)
- **SVEN** — Static vulnerability datasets (we generate new vulnerabilities each game)

Our key differentiation is the **adversarial game format** where both attack and defense are AI-powered.
