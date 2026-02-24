# AdversarialIaC-Bench

<p align="center">
  <strong>A Framework for Evaluating LLM Security Capabilities in Infrastructure-as-Code</strong>
</p>

<p align="center">
  <a href="getting-started/installation/">Getting Started</a> •
  <a href="framework/architecture/">Architecture</a> •
  <a href="experiments/single-game/">Run Experiments</a> •
  <a href="research/citation/">Cite Us</a>
</p>

---

## What is AdversarialIaC-Bench?

**AdversarialIaC-Bench** is an open-source benchmarking framework for evaluating how well Large Language Models (LLMs) can detect—and evade detection of—security vulnerabilities in Infrastructure-as-Code (IaC).

The framework uses a **Red Team vs Blue Team** adversarial approach:

```mermaid
graph LR
    A[🔴 Red Team<br/>Injects Vulnerabilities] --> C[📄 IaC Code]
    C --> B[🔵 Blue Team<br/>Detects Vulnerabilities]
    B --> D[⚖️ Judge<br/>Scores Match]
    D --> E[📊 Metrics<br/>P, R, F1, Evasion]
```

## Key Features

<div class="grid cards" markdown>

-   :material-robot:{ .lg .middle } __Multi-Model Support__

    ---

    Evaluate any LLM: Claude, GPT-4, Llama, Mistral, or custom models via AWS Bedrock, OpenAI, or local inference.

-   :material-shield-sword:{ .lg .middle } __Adversarial Evaluation__

    ---

    Red Team agents actively try to inject stealthy vulnerabilities. Blue Team agents try to detect them. Realistic attack-defense scenarios.

-   :material-account-group:{ .lg .middle } __Multi-Agent Modes__

    ---

    Go beyond single agents with Blue Team Ensembles, Red Team Pipelines, and Adversarial Debate verification.

-   :material-chart-box:{ .lg .middle } __Standardized Metrics__

    ---

    Precision, Recall, F1 Score, and Evasion Rate provide comparable results across experiments.

-   :material-cloud:{ .lg .middle } __Cloud Ready__

    ---

    AWS CDK infrastructure for running large-scale experiments with Step Functions and Lambda.

-   :material-open-source-initiative:{ .lg .middle } __Open Source__

    ---

    MIT licensed. Extend with new models, scenarios, and vulnerability types.

</div>

## Quick Example

```bash
# Install the framework
pip install -e .

# Run a single game
adversarial-iac game \
    --red-model us.anthropic.claude-3-5-sonnet-20241022-v2:0 \
    --blue-model amazon.nova-pro-v1:0 \
    --scenario "Create an S3 bucket for healthcare PHI data" \
    --difficulty medium
```

**Output:**
```
🎮 Game G-20260224_120000 Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Scoring:
   Precision: 80.0%
   Recall:    100.0%
   F1 Score:  88.9%
   Evasion:   0.0%
```

## Use Cases

### For Researchers

- **Benchmark new models**: Compare detection capabilities across LLMs
- **Study adversarial robustness**: How well do models evade detection?
- **Publish reproducible results**: Standardized metrics and scenarios

### For Security Teams

- **Evaluate LLM security tools**: Before deploying AI-powered scanners
- **Red team exercises**: Test detection capabilities
- **Training data generation**: Create labeled vulnerability datasets

### For Developers

- **Extend the framework**: Add new models, scenarios, or metrics
- **Custom experiments**: Design studies for specific use cases
- **Integration**: Use as a library in larger security pipelines

## Supported Technologies

| Category | Options |
|----------|---------|
| **IaC Languages** | Terraform, CloudFormation |
| **Cloud Providers** | AWS, Azure, GCP |
| **LLM Providers** | AWS Bedrock, OpenAI, Anthropic, Local |
| **Vulnerability Types** | Access Control, Encryption, Network, IAM, Logging, Data Protection |

## Next Steps

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __Installation__

    ---

    Get started with pip install in 2 minutes

    [:octicons-arrow-right-24: Install now](getting-started/installation.md)

-   :material-play:{ .lg .middle } __Quick Start__

    ---

    Run your first adversarial game

    [:octicons-arrow-right-24: Quick start guide](getting-started/quickstart.md)

-   :material-book-open:{ .lg .middle } __Architecture__

    ---

    Understand how the framework works

    [:octicons-arrow-right-24: Learn more](framework/architecture.md)

</div>

## Citation

If you use AdversarialIaC-Bench in your research, please cite:

```bibtex
@software{adversarial_iac_bench,
  title = {AdversarialIaC-Bench: A Framework for Evaluating LLM Security in Infrastructure-as-Code},
  author = {Terry, Brian},
  year = {2026},
  url = {https://github.com/brianterry/Adversarial-IaC-Evaluation}
}
```
