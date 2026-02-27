# Adversarial IaC Benchmark

**An Adversarial Evaluation Framework for LLM Security in Infrastructure-as-Code**

A research benchmark where AI agents compete in Red Team vs Blue Team scenarios to evaluate LLM capabilities in cloud security. The Red Team generates infrastructure code with hidden vulnerabilities; the Blue Team tries to detect them. Standardized metrics enable reproducible comparison across models, strategies, and configurations.

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://brianterry.github.io/Adversarial-IaC-Evaluation/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What Is This?

An adversarial benchmark with three AI agents:

- **🔴 Red Team (Attacker)**: Generates legitimate-looking infrastructure code with hidden vulnerabilities
- **🔵 Blue Team (Defender)**: Analyzes the code to find the hidden security issues
- **⚖️ Judge**: Scores detection accuracy using hybrid LLM + rule-based matching

Each evaluation round produces metrics (precision, recall, F1, evasion rate) that enable rigorous comparison across models and configurations.

**New in v2.0:** Ground truth validation using static tools, multi-model consensus judge with Cohen's κ inter-rater reliability, tool-triangulated corroboration, and comparative experiment runner for publication-ready results.

## 🔬 Why This Matters

### The Research Gap

Current LLM security benchmarks have critical limitations:

| Existing Approach | Problem |
|-------------------|---------|
| **Static vulnerability datasets** | LLMs memorize known patterns; doesn't test generalization |
| **Single-agent evaluation** | Misses adversarial dynamics of real security scenarios |
| **Generic code analysis** | IaC has unique security semantics (cloud permissions, network policies) |
| **Binary pass/fail metrics** | Doesn't capture partial detection or evasion sophistication |

### What's Novel Here

1. **Adversarial Evaluation** — First benchmark where LLMs actively compete (Red Team tries to evade, Blue Team tries to detect). This measures true adversarial robustness, not just pattern matching.

2. **Dynamic Vulnerability Generation** — Red Team creates *new* vulnerable code each game, preventing memorization and testing real security reasoning.

3. **IaC-Specific Focus** — Purpose-built for Infrastructure-as-Code with 114 scenarios across healthcare (HIPAA), financial (PCI-DSS), government (FedRAMP), and cloud-native patterns.

4. **Multi-Agent Architectures** — Evaluates emerging multi-agent patterns: specialist ensembles, attack pipelines, and adversarial debate verification.

5. **Standardized Metrics** — Optimal bipartite matching (Hungarian algorithm) for fair scoring with precision, recall, F1, and evasion rate.

### Research Applications

- **Benchmark new models** — Compare LLM security capabilities with reproducible metrics
- **Study adversarial robustness** — How do detection rates change against adaptive attackers?
- **Evaluate multi-agent strategies** — Do ensembles outperform single agents? Does debate improve accuracy?
- **Compliance-specific analysis** — How well do LLMs understand HIPAA vs PCI-DSS vs FedRAMP?
- **Attack sophistication research** — Which evasion techniques are most effective?

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/brianterry/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation
python -m venv venv && source venv/bin/activate
pip install -e .
```

### Play Your First Game

```bash
adversarial-iac play
```

That's it! The interactive wizard will guide you through:

1. **Choose a scenario** - Browse 114 scenarios (healthcare, financial, infrastructure...)
2. **Pick difficulty** - Easy, Medium, or Hard
3. **Choose IaC language** - Terraform or CloudFormation
4. **Select AI models** - For Red Team and Blue Team
5. **Watch the game** - See Red vs Blue compete in real-time
6. **Understand results** - Clear explanations of who won and why

<details>
<summary>📟 Prefer command line? Click here</summary>

```bash
adversarial-iac game \
    --scenario "Create an S3 bucket for healthcare PHI data" \
    --red-model claude-3.5-sonnet \
    --blue-model nova-pro \
    --difficulty medium
```

See all options with `adversarial-iac game --help`

</details>

## 🎲 How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ADVERSARIAL EVALUATION FLOW                        │
└─────────────────────────────────────────────────────────────────────────┘

     SCENARIO: "Create S3 bucket for healthcare PHI data"
                              │
                              ▼
     ┌────────────────────────────────────────────────────────────────┐
     │  🔴 RED TEAM                                                   │
     │                                                                │
     │  "I'll create the S3 bucket... but secretly make it           │
     │   public and skip encryption. Let's see if they catch it."    │
     │                                                                │
     │  Output: main.tf (looks normal, but has 3 hidden vulns)       │
     └────────────────────────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────────────────────────┐
     │  🔵 BLUE TEAM                                                  │
     │                                                                │
     │  "Let me analyze this code... I see the bucket is public!     │
     │   And there's no encryption. Wait, is that IAM policy weak?"  │
     │                                                                │
     │  Output: Found 4 vulnerabilities                               │
     └────────────────────────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────────────────────────┐
     │  ⚖️  JUDGE                                                     │
     │                                                                │
     │  Red Team hid 3 vulnerabilities                                │
     │  Blue Team found 4 issues                                      │
     │                                                                │
     │  ✓ 2 correct matches (True Positives)                         │
     │  ✗ 1 evaded (Red wins this one)                               │
     │  ✗ 2 false alarms (Blue was wrong)                            │
     │                                                                │
     │  SCORE: Blue Team 67% Recall, Red Team 33% Evasion            │
     └────────────────────────────────────────────────────────────────┘
```

## 📚 114 Built-in Scenarios

The game includes scenarios across 4 categories and 18 domains:

```bash
# See all available scenarios
adversarial-iac scenarios

# Browse by category
adversarial-iac scenarios --category industry

# View specific domain
adversarial-iac scenarios --domain healthcare
```

| Category | Domains | Examples |
|----------|---------|----------|
| 🏗️ **Infrastructure** | storage, compute, network, iam | S3, Lambda, VPC, IAM roles |
| ☁️ **AWS Services** | secrets, containers, databases, api | KMS, EKS, RDS, API Gateway |
| 🏢 **Industry** | healthcare, financial, government | HIPAA, PCI-DSS, FedRAMP |
| 🔒 **Security** | zero_trust, disaster_recovery | Zero-trust architecture, DR |

## 🤖 Available Models

Use any Amazon Bedrock model. We've organized them into tiers:

```bash
# List all available models
adversarial-iac models
```

| Tier | Models | Use Case |
|------|--------|----------|
| 🏆 **Frontier** | Claude 3.5 Sonnet, Claude 3 Opus, Nova Premier | Final experiments |
| 💪 **Strong** | Claude 3.5 Haiku, Nova Pro, Llama 70B | Recommended |
| ⚡ **Efficient** | Nova Lite, Nova Micro, Llama 8B | Testing & development |
| 🔬 **Specialized** | DeepSeek R1, Jamba | Experimental |

```bash
# Use short names in commands
adversarial-iac game --red-model claude-3.5-sonnet --blue-model nova-pro ...
```

## ⚔️ Evaluation Modes

### Standard Game (1v1)
Single agent per team. Fast and simple.

```bash
adversarial-iac game --red-team-mode single --blue-team-mode single ...
```

### Red Team Pipeline (4-Stage Attack)
A chain of specialists create stealthier attacks:

```
Architect → Vulnerability Selector → Code Generator → Stealth Reviewer
```

```bash
adversarial-iac game --red-team-mode pipeline ...
```

### Blue Team Ensemble (Expert Panel)
Multiple specialists analyze code, then vote on findings:

```
Security Expert  ─┐
Compliance Agent ─┼→ Consensus → Unified Findings
Architecture Agent┘
```

```bash
adversarial-iac game --blue-team-mode ensemble --consensus-method debate ...
```

### Adversarial Debate Verification
Each finding is debated by prosecutor and defender agents:

```bash
adversarial-iac game --verification-mode debate ...
```

## 🎯 Attack & Defense Strategies

### Red Team Strategies
```bash
--red-strategy balanced    # Default - mix of vulnerability types
--red-strategy targeted    # Focus on specific type (--red-target-type encryption)
--red-strategy stealth     # Maximize evasion with obfuscation
--red-strategy blitz       # Many vulnerabilities, less stealth
--red-strategy chained     # Create vulnerability chains
```

### Blue Team Strategies
```bash
--blue-strategy comprehensive  # Default - check everything
--blue-strategy targeted       # Focus on specific type
--blue-strategy iterative      # Multiple analysis passes
--blue-strategy threat_model   # Threat modeling approach
--blue-strategy compliance     # Compliance-focused (--compliance-framework hipaa)
```

### Static Analysis Tools
Optionally enable industry tools alongside LLM analysis:

```bash
--use-trivy      # Enable Trivy scanner
--use-checkov    # Enable Checkov scanner
```

### Judge Configuration

```bash
--no-llm-judge          # Rule-based only (faster, less accurate)
--use-consensus-judge   # Multi-model consensus for inter-rater reliability
--consensus-models      # Comma-separated model IDs (requires 2+)
```

## 📊 Understanding the Scoring

The Judge uses **optimal bipartite matching** (Hungarian algorithm) to pair Red Team vulnerabilities with Blue Team findings for the fairest scoring:

| Metric | Meaning | Who Wins? |
|--------|---------|-----------|
| **Precision** | % of Blue's findings that were correct | High = Blue |
| **Recall** | % of Red's vulns that Blue found | High = Blue |
| **F1 Score** | Balance of precision and recall | High = Blue |
| **Evasion Rate** | % of Red's vulns that evaded detection | High = Red |

### Hybrid LLM Judge (Default)

The Judge uses a **hybrid approach** for maximum accuracy:

1. **Rule-based matching** for clear cases (score > 0.7)
2. **LLM fallback** for ambiguous cases (score 0.3-0.7) — the LLM evaluates whether findings truly match
3. **Clear misses** for low-scoring pairs (score < 0.3)

This prevents false negatives where semantically identical findings (e.g., "No secret rotation" vs "Missing rotation configuration") are incorrectly marked as missed.

```bash
# Disable LLM judge for faster (but less accurate) scoring
adversarial-iac game --no-llm-judge ...
```

### Multi-Model Consensus (Inter-Rater Reliability)

For publication-quality results, enable **multi-model consensus** judging. Multiple LLMs independently judge each ambiguous case, and Cohen's κ measures inter-rater agreement.

#### Multi-Provider Support (Strongest)

For maximum methodological rigor, use models from **different providers** (OpenAI, Google, AWS Bedrock):

```bash
# Best: 3 providers = 3 independent organizations
adversarial-iac game \
    --use-consensus-judge \
    --consensus-models "openai:gpt-4o,google:gemini-1.5-pro,bedrock:claude-3.5-sonnet" \
    --use-trivy --use-checkov ...
```

This gives you judges from **Anthropic, OpenAI, and Google** — completely independent training data, RLHF pipelines, and architectures.

#### Bedrock-Only (Simpler)

If you only have AWS credentials, use different model families via Bedrock:

```bash
# Good: 3 different organizations via Bedrock
adversarial-iac game \
    --use-consensus-judge \
    --consensus-models claude-3.5-sonnet,nova-pro,llama-3.1-70b ...
```

#### Required API Keys

| Provider | Environment Variable | Get From |
|----------|---------------------|----------|
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| Google | `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Bedrock | AWS credentials | Your AWS account |

Add to your `.env` file:
```bash
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
```

**Output metrics:**
| Metric | Description | Target |
|--------|-------------|--------|
| **Pairwise κ** | Cohen's kappa between each model pair | > 0.70 |
| **Mean κ** | Average across all pairs | > 0.70 |
| **Agreement Rate** | % of cases with unanimous agreement | Report as-is |

If all pairwise κ values exceed 0.70, you have strong evidence that the judge circularity concern is mitigated — different model architectures agree on the verdicts.

### Tool-Triangulated Matching (Corroborated Tier)

When static tools are enabled, matches can be **corroborated** — meaning the Red Team vulnerability, Blue Team finding, AND static tool all flag the same resource:

| Match Type | Confidence | Description |
|------------|------------|-------------|
| **Corroborated** | Highest | Red + Blue + Tool agree (external anchor) |
| **Exact** | High | Red + Blue match perfectly |
| **Partial** | Medium | Red + Blue semantically match |
| **Missed** | — | Blue didn't detect Red's vulnerability |

Corroborated matches provide a **non-LLM external anchor** for ground truth, directly addressing reviewer concerns about LLM circularity.

**Example scoring output:**
```json
{
  "corroborated_matches": 3,
  "corroboration_rate": 0.60,
  "inter_rater_reliability": {
    "mean_kappa": 0.78,
    "pairwise_kappa": {
      "claude_vs_nova": 0.82,
      "nova_vs_llama": 0.75,
      "claude_vs_llama": 0.77
    }
  }
}
```

### Match Types

| Match Type | Description | Example |
|------------|-------------|---------|
| **Exact** | Perfect match - same type, location | Both say "S3 bucket unencrypted at line 15" |
| **Partial** | Correct finding, different wording | Red: "missing encryption" / Blue: "no SSE" |
| **Threshold** | Related finding above similarity threshold | Similar vulnerability category |

All match types count as **True Positives** - the Blue Team successfully detected the vulnerability!

## 🔍 Ground Truth Validation

A key research concern: *who validates the validator?* The Red Team declares its own vulnerabilities — how do we know they're real?

### Manifest Validation

When static tools (Trivy/Checkov) are enabled, the framework **independently validates** Red Team's claims:

```bash
# Run game with manifest validation (default when tools enabled)
adversarial-iac game --use-trivy --use-checkov ...
```

**Output metrics:**
| Metric | Description |
|--------|-------------|
| **Manifest Accuracy** | % of claimed vulnerabilities confirmed by static tools |
| **Hallucination Rate** | % of claimed vulnerabilities NOT found by tools |
| **Confirmed Vulns** | List of independently verified vulnerabilities |

This provides an **external oracle** for ground truth, addressing the self-declaration problem.

### Example Validation Output

```json
{
  "manifest_accuracy": 0.80,
  "hallucination_rate": 0.20,
  "confirmed_vuln_ids": ["V1", "V2", "V3", "V4"],
  "unconfirmed_vuln_ids": ["V5"]
}
```

Unconfirmed vulnerabilities may be:
- **Real but tool-blind** — the vulnerability exists but tools don't detect it
- **Hallucinated** — the LLM claimed a vulnerability that doesn't exist

### Tool-Blind Vulnerabilities

Static tools (Trivy, Checkov) have known coverage gaps:
- **Logic-level IAM misconfigurations** — overly permissive policies that are syntactically valid
- **Cross-resource dependency vulnerabilities** — issues requiring multi-resource reasoning
- **Context-dependent misconfigurations** — settings that are only wrong in certain scenarios

These "tool-blind" vulnerabilities represent a **harder class of security reasoning** that static tools cannot reach. This makes LLM-based detection more interesting, not less rigorous — these are precisely the vulnerabilities where LLM judgment adds value.

Manual audit of unconfirmed vulnerabilities is recommended for publication to distinguish true hallucinations from tool-blind findings.

## 🔬 Running Research Experiments

Use the framework to generate publication-ready data with statistical rigor.

### Comparative Experiment Runner

Run systematic experiments comparing all modes:

```bash
# Full comparative study (Red modes × Blue modes × Verification modes)
python scripts/run_comparative_experiment.py --scenarios 20 --output results/

# Quick test run
python scripts/run_comparative_experiment.py --scenarios 5 --quick
```

**Outputs:**
- `full_results.json` — Raw data for analysis
- `tables.tex` — LaTeX tables ready for paper
- `results.md` — Markdown summary

### Example Paper Tables

**Table 1: Red Team Mode Comparison**
| Mode | Evasion Rate | Precision | Recall | n |
|------|--------------|-----------|--------|---|
| single | 0.25 ± 0.15 | 0.85 ± 0.10 | 0.75 ± 0.12 | 40 |
| pipeline | 0.35 ± 0.18 | 0.82 ± 0.11 | 0.68 ± 0.14 | 40 |

**Table 2: Ground Truth Validation**
| Metric | Value |
|--------|-------|
| Manifest Accuracy | 78.5% ± 12.3% |
| Hallucination Rate | 21.5% ± 12.3% |
| Corroboration Rate | 64.2% ± 15.1% |

**Table 3: Inter-Rater Reliability (Multi-Model Consensus)**
| Model Pair | Cohen's κ |
|------------|-----------|
| Claude vs Nova | 0.82 |
| Nova vs Llama | 0.75 |
| Claude vs Llama | 0.77 |
| **Mean κ** | **0.78** |

### Single Experiment
```bash
adversarial-iac experiment \
    --config config/experiment_config.yaml \
    --experiment symmetric_adversarial \
    --output experiments/exp_001
```

### Batch Experiments
Configure multiple experiments in YAML:

```yaml
experiment:
  name: "model_comparison"
  description: "Compare Claude vs Nova on healthcare scenarios"

models:
  red_team: ["claude-3.5-sonnet", "nova-pro"]
  blue_team: ["claude-3.5-sonnet", "nova-pro"]

scenarios:
  domains: ["healthcare", "financial"]
  difficulty_levels: ["medium", "hard"]

matrix:
  type: "symmetric"  # Same model attacks and defends
```

### Analyze Results
Use the included Jupyter notebooks for analysis:

```bash
jupyter notebook notebooks/03_analyze_results.ipynb
```

## 📁 Output Structure

Each evaluation creates a results folder:

```
output/games/G-20260224_143052/
├── code/
│   └── main.tf               # Red Team's generated code
├── red_team_manifest.json    # Hidden vulnerabilities (ground truth)
├── blue_team_findings.json   # Blue Team's detections
├── game_result.json          # Full game result with scores
└── game.log                  # Detailed execution log
```

## 🛠️ CLI Reference

```bash
# Start here
adversarial-iac play                    # 🎮 Interactive wizard (recommended!)

# Browse options
adversarial-iac scenarios               # List 114 scenarios by category
adversarial-iac models                  # List AI models by tier

# Direct game control
adversarial-iac game [OPTIONS]          # Run a game with CLI flags

# Research & batch
adversarial-iac experiment [OPTIONS]    # Run batch experiments

# Advanced
adversarial-iac red-team [OPTIONS]      # Run Red Team only
adversarial-iac blue-team [OPTIONS]     # Run Blue Team only
```

## 📖 Documentation

Full documentation available at: **[brianterry.github.io/Adversarial-IaC-Evaluation](https://brianterry.github.io/Adversarial-IaC-Evaluation/)**

- [Getting Started Guide](https://brianterry.github.io/Adversarial-IaC-Evaluation/getting-started/)
- [Game Mechanics](https://brianterry.github.io/Adversarial-IaC-Evaluation/game/)
- [Running Experiments](https://brianterry.github.io/Adversarial-IaC-Evaluation/experiments/)
- [API Reference](https://brianterry.github.io/Adversarial-IaC-Evaluation/api/)

## 🔧 Requirements

- **Python 3.10+**
- **AWS Account** with Bedrock model access
- **AWS CLI** configured with credentials

### Optional Tools
```bash
# For hybrid detection mode
brew install trivy        # macOS
pip install checkov
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

**Vulnerability Database:** The 142 security rules included in this benchmark are derived from [Trivy Checks](https://github.com/aquasecurity/trivy-checks) by Aqua Security. Database tooling adapted from [Vulnerable IaC Dataset Generator](https://github.com/SymbioticSec/vulnerable-iac-dataset-generator).

---

**Ready to play?** Run `adversarial-iac play` and see if your Blue Team can catch the Red Team's tricks! 🎮
