# 🎮 Adversarial IaC Game

**A Red Team vs Blue Team Security Game for Infrastructure-as-Code**

An adversarial game framework where AI agents compete to hide and find security vulnerabilities in cloud infrastructure code. Use it to benchmark LLM security capabilities, run research experiments, or learn about IaC security.

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://brianterry.github.io/Adversarial-IaC-Evaluation/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What Is This?

It's a game where two AI agents compete:

- **🔴 Red Team (Attacker)**: Generates legitimate-looking infrastructure code with hidden vulnerabilities
- **🔵 Blue Team (Defender)**: Analyzes the code to find the hidden security issues
- **⚖️ Judge**: Scores who won based on what was found vs what was hidden

Think of it like **capture the flag**, but for cloud security.

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
git clone --recursive https://github.com/brianterry/Adversarial-IaC-Evaluation.git
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

## 🎲 How the Game Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         THE ADVERSARIAL IaC GAME                        │
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

## ⚔️ Game Modes

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

## 📊 Understanding the Scoring

The Judge uses **optimal bipartite matching** (Hungarian algorithm) to pair Red Team vulnerabilities with Blue Team findings for the fairest scoring:

| Metric | Meaning | Who Wins? |
|--------|---------|-----------|
| **Precision** | % of Blue's findings that were correct | High = Blue |
| **Recall** | % of Red's vulns that Blue found | High = Blue |
| **F1 Score** | Balance of precision and recall | High = Blue |
| **Evasion Rate** | % of Red's vulns that evaded detection | High = Red |

### Match Types

| Match Type | Description | Example |
|------------|-------------|---------|
| **Exact** | Perfect match - same type, location | Both say "S3 bucket unencrypted at line 15" |
| **Partial** | Correct finding, different wording | Red: "missing encryption" / Blue: "no SSE" |
| **Threshold** | Related finding above similarity threshold | Similar vulnerability category |

All match types count as **True Positives** - the Blue Team successfully detected the vulnerability!

## 🔬 Running Research Experiments

Use the game to generate data for academic papers:

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

## 📁 Game Output Structure

Each game creates a results folder:

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

Built upon the [Vulnerable IaC Dataset Generator](https://github.com/SymbioticSec/vulnerable-iac-dataset-generator) which provides 142 real-world vulnerability patterns.

---

**Ready to play?** Run `adversarial-iac play` and see if your Blue Team can catch the Red Team's tricks! 🎮
