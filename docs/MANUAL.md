# Adversarial IaC Benchmark - Complete Manual

<p align="center">
  <strong>An Adversarial Evaluation Framework for LLM Security in Infrastructure-as-Code</strong>
</p>

---

**Table of Contents**

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
   - [Installation](#installation)
   - [Quick Start](#quick-start)
   - [Configuration Reference](#configuration-reference)
3. [The Game](#the-game)
   - [How It Works](#how-it-works)
   - [Red Team Agent](#red-team-agent)
   - [Blue Team Agent](#blue-team-agent)
   - [Judge & Scoring](#judge--scoring)
   - [Scoring Metrics](#scoring-metrics)
4. [Evaluation Modes & Strategies](#evaluation-modes--strategies)
   - [Overview](#modes-overview)
   - [Red Team Pipeline](#red-team-pipeline)
   - [Blue Team Ensemble](#blue-team-ensemble)
   - [Adversarial Debate](#adversarial-debate)
5. [Scenarios & Models](#scenarios--models)
   - [114 Built-in Scenarios](#114-built-in-scenarios)
   - [20+ AI Models](#20-ai-models)
6. [For Researchers](#for-researchers)
   - [Running Experiments](#running-experiments)
   - [Analyzing Results](#analyzing-results)
   - [Ground Truth Validation](#ground-truth-validation)
   - [Game Replay](#game-replay)
7. [Extending the Framework](#extending-the-framework)
   - [New Vulnerability Types](#new-vulnerability-types)
8. [API Reference](#api-reference)
   - [Game Engine](#game-engine-api)
   - [Agents](#agents-api)
   - [Prompts](#prompts-api)
9. [Research & Citation](#research--citation)
   - [Citation](#citation)
   - [Publications](#publications)
   - [Contributing](#contributing)

---

# Introduction

An **adversarial benchmark** where AI agents compete in security scenarios:

- 🔴 **Red Team (Attacker)**: Generates infrastructure code with hidden vulnerabilities
- 🔵 **Blue Team (Defender)**: Analyzes code to detect those vulnerabilities
- ⚖️ **Judge**: Scores using hybrid LLM + rule-based matching (precision, recall, F1, evasion)
- 🔍 **Validator**: Independently verifies ground truth using static analysis tools

This enables rigorous evaluation of LLM security capabilities with reproducible metrics.

## New in v2.0

- **Multi-Model Consensus Judge**: Cohen's κ inter-rater reliability across GPT-4, Claude, and Gemini
- **Tool-Triangulated Matching**: "Corroborated" tier when Red + Blue + Tool all agree (non-LLM anchor)
- **Multi-Provider Support**: Use OpenAI, Google, and AWS Bedrock models together
- **Ground Truth Validation**: Static tools (Trivy/Checkov) independently verify Red Team claims
- **Comparative Experiment Runner**: Generate publication-ready tables with statistical analysis

## New in v2.1

- **Manifest Validation Gate**: Red Team claims are verified by Trivy/Checkov *before* scoring. Phantom vulnerabilities (hallucinated by Red Team) are excluded from the scored ground truth. This is load-bearing for any recall claim.
- **Source Label Instrumentation**: Every manifest entry carries `is_novel` and `rule_source` labels, enabling per-source analysis in database/novel/mixed experiments.
- **Adjusted Recall & Phantom Concordance**: New metrics computed on tool-confirmed ground truth only. Phantom concordance measures what fraction of Blue Team "detections" match non-existent vulnerabilities.
- **Precision-Focused Blue Team** (`--blue-strategy precise`): Two-pass analysis — first detects everything, then verifies each finding against actual code evidence. Removes unverifiable findings.
- **Novel Vulnerability Specificity**: Red Team novel generation now requires concrete Terraform resource types, attributes, and insecure values — reducing hallucination rate.
- **Reasoning Model Support**: DeepSeek-R1 and Qwen3-Coder work correctly via response sanitizer that strips `<think>` blocks, reasoning content, and markdown fences.
- **Game Replay**: `adversarial-iac replay output/games/G-XXXX` re-renders completed game results.
- **Experiment Runner Improvements**: Progress bar with ETA, running manifest accuracy gate-check with configurable auto-halt threshold, deterministic seeding (`random_seed` in config), model fallback on access errors.
- **Statistical Analysis**: `python scripts/analyze_experiments.py` with t-tests, ANOVA, Cohen's d, and LaTeX table export (`--latex-file tables.tex`).
- **Cost Estimation**: Per-game cost tracking based on Bedrock pricing and token estimates.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ADVERSARIAL EVALUATION FLOW                      │
└─────────────────────────────────────────────────────────────────────┘

  SCENARIO: "Create S3 bucket for healthcare PHI data"
                            │
                            ▼
  ┌────────────────────────────────────────────────────────────────┐
  │  🔴 RED TEAM                                                   │
  │  "I'll create the bucket... but secretly make it public."      │
  └────────────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌────────────────────────────────────────────────────────────────┐
  │  🔵 BLUE TEAM                                                  │
  │  "Let me analyze this... I see the bucket is public!"          │
  └────────────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌────────────────────────────────────────────────────────────────┐
  │  ⚖️  JUDGE                                                     │
  │  Red hid 3 vulns • Blue found 2 • SCORE: Blue 67% Recall       │
  └────────────────────────────────────────────────────────────────┘
```

## Why This Matters

Current LLM security benchmarks evaluate models on **static datasets** with **known vulnerabilities**. This leads to:

- **Memorization over reasoning** — Models learn patterns, not security principles
- **Missing adversarial dynamics** — Real attackers adapt; benchmarks don't
- **Generic code focus** — IaC has unique security semantics that aren't tested

**We need benchmarks where AI actively tries to evade detection.**

### What's Novel

1. **Adversarial Evaluation**: First benchmark where LLMs **actively compete**. Red Team tries to evade, Blue Team tries to detect. Measures true adversarial robustness.

2. **Dynamic Generation**: Red Team creates **new vulnerable code each game**. No memorization possible—tests real security reasoning.

3. **IaC-Specific**: **114 scenarios** purpose-built for Infrastructure-as-Code: HIPAA, PCI-DSS, FedRAMP, and cloud-native patterns.

4. **Multi-Agent**: Evaluates emerging patterns: **specialist ensembles**, **attack pipelines**, and **adversarial debate** verification.

### Research Questions You Can Answer

| Question | How the Game Helps |
|----------|-------------------|
| How do LLMs compare at detecting IaC vulnerabilities? | Run symmetric experiments across models |
| Does multi-agent collaboration improve detection? | Compare ensemble vs single-agent modes |
| Which evasion techniques are most effective? | Analyze Red Team strategy success rates |
| How well do LLMs understand compliance frameworks? | Test HIPAA vs PCI-DSS vs FedRAMP scenarios |
| Does adversarial debate reduce false positives? | Compare standard vs debate verification |
| Is the LLM judge reliable? | Multi-model consensus with Cohen's κ > 0.70 |
| How accurate is the Red Team manifest? | Manifest accuracy & hallucination rate metrics |

## Who Is This For?

### 🔬 For Researchers
- **Benchmark new models** with standardized, reproducible metrics
- **Generate publication-ready data** with controlled experiments
- **Study adversarial robustness** against adaptive attackers

### 🛡️ For Security Teams
- **Evaluate AI security tools** before deploying them
- **Run red team exercises** with AI-generated attacks
- **Generate training data** — labeled vulnerable code samples

### 💻 For Developers
- **Learn IaC security** by seeing what AI attackers try to hide
- **Extend the game** with new scenarios, models, or strategies
- **Integrate** into CI/CD security pipelines

---

# Getting Started

## Installation

### Requirements

- Python 3.10+
- AWS credentials (for Bedrock models)
- Git

### Quick Install

```bash
# Clone the repository
git clone https://github.com/brianterry/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

### Verify Installation

```bash
adversarial-iac --help
```

You should see:

```
Usage: adversarial-iac [OPTIONS] COMMAND [ARGS]...

  Adversarial IaC Evaluation Framework

Options:
  --help  Show this message and exit.

Commands:
  game              Run a single adversarial game
  play              Interactive mode with guided setup
  replay            Re-display results from a completed game
  red-team          Run Red Team agent only
  blue-team         Run Blue Team agent only
  models            List available models by tier
  scenarios         Browse built-in scenarios
  show              Display experiment results
  hybrid-experiment Run hybrid detection on existing results
```

### AWS Configuration

The framework uses AWS Bedrock for LLM inference. Configure your credentials:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
```

#### Enable Bedrock Models

In the AWS Console:

1. Go to **Amazon Bedrock** → **Model access**
2. Enable the models you want to use:
    - Anthropic Claude (Sonnet, Haiku)
    - Amazon Nova
    - Meta Llama
    - Mistral

### Optional: Static Analysis Tools

For enhanced Blue Team capabilities, install:

**Trivy:**
```bash
# macOS
brew install trivy

# Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

**Checkov:**
```bash
pip install checkov
```

### Development Install

For contributing to the framework:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
```

---

## Quick Start

Play your first game in under 5 minutes!

### Play Now

```bash
adversarial-iac play
```

That's it! The interactive wizard guides you through everything:

```
🎮 ADVERSARIAL IAC GAME
━━━━━━━━━━━━━━━━━━━━━━━

? How would you like to choose a scenario?
❯ 🎲 Random - Let me pick something interesting
  🏗️ Infrastructure - Core AWS components
  🏢 Industry - Healthcare, Financial, Government...
  ✏️ Custom - Describe your own scenario

? Select difficulty level:
  🟢 Easy - Obvious vulnerabilities (good for learning)
❯ 🟡 Medium - Subtle issues (recommended)
  🔴 Hard - Hidden, chained vulnerabilities (expert)

? Which Infrastructure-as-Code language?
❯ 📄 Terraform (HCL) - Most popular, recommended
  ☁️  CloudFormation (YAML/JSON) - AWS native

? Choose Red Team model (attacker):
❯ ⭐ claude-3.5-sonnet (Recommended)
  ⚡ claude-3.5-haiku (Fast)
  💰 nova-lite (Cheap)
  
[Running game...]

🎮 Game Complete! Here's what happened...
```

### What Happens During a Game

1. **🔴 Red Team** creates infrastructure code with hidden vulnerabilities
2. **🔵 Blue Team** analyzes the code to find security issues  
3. **⚖️ Judge** scores who won based on what was found vs hidden

The wizard explains the results in plain English - no security expertise required!

### Command Line Mode

For scripting or direct control:

```bash
adversarial-iac game \
    --scenario "Create an S3 bucket for healthcare PHI data" \
    --red-model nova-lite \
    --blue-model nova-lite \
    --difficulty medium
```

See all options: `adversarial-iac game --help`

### Output

```
🎮 Game Complete!

┌─────────────────────────────────────────────┐
│ Match Details                               │
├──────────────────┬───────────┬──────────────┤
│ Red Team Vuln    │ Blue Find │ Match        │
├──────────────────┼───────────┼──────────────┤
│ Missing encrypt  │ No SSE    │ ✓ Partial    │
│ Public bucket    │ Public    │ ✓ Exact      │
│ Weak IAM policy  │ -         │ ✗ Evaded     │
└──────────────────┴───────────┴──────────────┘

📊 Scores
   Precision:    100.0%  (Blue's accuracy)
   Recall:        66.7%  (% of vulns found)
   F1 Score:      80.0%  (Overall Blue performance)
   Evasion Rate:  33.3%  (Red's success hiding vulns)

🏆 Blue Team wins this round!

📁 Results saved to: output/games/G-20260224_120000/
```

### Browsing Scenarios

See all 114 built-in scenarios:

```bash
# List all scenarios by category
adversarial-iac scenarios

# Filter by category
adversarial-iac scenarios --category industry

# View specific domain
adversarial-iac scenarios --domain healthcare
```

### Categories

| Category | Domains | Example Scenarios |
|----------|---------|-------------------|
| 🏗️ **Infrastructure** | storage, compute, network, iam | S3 buckets, Lambda functions, VPCs |
| ☁️ **AWS Services** | secrets, containers, databases, api | KMS, EKS, RDS, API Gateway |
| 🏢 **Industry** | healthcare, financial, government | HIPAA, PCI-DSS, FedRAMP |
| 🔒 **Security** | zero_trust, disaster_recovery | Zero-trust architecture |

### Available Models

List models organized by tier:

```bash
adversarial-iac models
```

#### Quick Reference

| Short Name | Full ID | Tier |
|------------|---------|------|
| `claude-3.5-sonnet` | us.anthropic.claude-3-5-sonnet-20241022-v2:0 | 🏆 Frontier |
| `nova-pro` | amazon.nova-pro-v1:0 | 💪 Strong *(may require inference profile)* |
| `nova-lite` | amazon.nova-lite-v1:0 | ⚡ Efficient |

Use short names in commands:
```bash
adversarial-iac game --red-model nova-lite --blue-model nova-lite ...
```

### Understanding Scores

| Metric | Who Wins? | Meaning |
|--------|-----------|---------|
| **Precision** | High = Blue | Were Blue's reports accurate? |
| **Recall** | High = Blue | Did Blue find Red's vulns? |
| **F1 Score** | High = Blue | Overall Blue performance |
| **Evasion Rate** | High = Red | Did Red successfully hide vulns? |

### Difficulty Levels

**🟢 Easy:**
```bash
adversarial-iac game --difficulty easy ...
```
- 2-3 obvious vulnerabilities
- Basic misconfiguration patterns
- Good for learning

**🟡 Medium:**
```bash
adversarial-iac game --difficulty medium ...
```
- 3-4 mixed vulnerabilities
- Some subtle patterns
- Recommended for experiments

**🔴 Hard:**
```bash
adversarial-iac game --difficulty hard ...
```
- 4-5 stealthy vulnerabilities
- Advanced evasion techniques
- Expert mode

### Game Modes

**Standard (1v1):**
```bash
adversarial-iac game --red-team-mode single --blue-team-mode single ...
```

**Red Team Pipeline:**
Multi-stage attack chain for stealthier vulnerabilities:
```bash
adversarial-iac game --red-team-mode pipeline ...
```

**Blue Team Ensemble:**
Expert panel with consensus voting:
```bash
adversarial-iac game --blue-team-mode ensemble --consensus-method vote ...
```

**Adversarial Debate:**
Verify each finding through debate:
```bash
adversarial-iac game --verification-mode debate ...
```

### Game Output Files

```
output/games/G-20260224_120000/
├── code/
│   └── main.tf                # Red Team's generated code
├── red_manifest.json          # Full manifest (all claimed vulns, with is_novel/rule_source)
├── scored_manifest.json       # Tool-confirmed vulns only (used as ground truth)
├── phantom_manifest.json      # Unconfirmed vulns (excluded from scoring)
├── blue_findings.json         # Blue Team's detections
├── scoring.json               # Match results, metrics, ground_truth_quality
├── manifest_validation.json   # Gate results (confirmed/phantom IDs, match details)
├── metadata.json              # Config, timing, summary
└── game.log                   # Detailed execution log
```

**Key distinction**: `scored_manifest.json` contains only tool-confirmed vulnerabilities and is used as the ground truth for scoring. `phantom_manifest.json` contains claimed-but-unconfirmed vulnerabilities excluded from recall calculation. Both files carry source labels (`is_novel`, `rule_source`) for per-source analysis.

---

## Configuration Reference

### CLI Options

#### Game Command

```bash
adversarial-iac game [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--scenario`, `-s` | string | ✅ | - | Scenario description |
| `--red-model` | string | ❌ | `claude-3-5-haiku` | Red Team model ID |
| `--blue-model` | string | ❌ | `claude-3-5-haiku` | Blue Team model ID |
| `--difficulty` | choice | ❌ | `medium` | `easy`, `medium`, `hard` |
| `--language` | choice | ❌ | `terraform` | `terraform`, `cloudformation` |
| `--cloud-provider` | choice | ❌ | `aws` | `aws`, `azure`, `gcp` |
| `--red-team-mode` | choice | ❌ | `single` | `single`, `pipeline` |
| `--blue-team-mode` | choice | ❌ | `single` | `single`, `ensemble` |
| `--consensus-method` | choice | ❌ | `debate` | `debate`, `vote`, `union`, `intersection` |
| `--verification-mode` | choice | ❌ | `standard` | `standard`, `debate` |
| `--no-llm-judge` | flag | ❌ | `false` | Disable LLM for ambiguous matches |
| `--use-consensus-judge` | flag | ❌ | `false` | Enable multi-model consensus judging |
| `--consensus-models` | string | ❌ | - | Comma-separated models for consensus |
| `--red-strategy` | choice | ❌ | `balanced` | `balanced`, `targeted`, `stealth`, `blitz`, `chained` |
| `--red-vuln-source` | choice | ❌ | `database` | `database`, `novel`, `mixed` |
| `--blue-strategy` | choice | ❌ | `comprehensive` | `comprehensive`, `targeted`, `iterative`, `threat_model`, `compliance`, `precise` |
| `--use-trivy` | flag | ❌ | `false` | Enable Trivy static analysis + manifest validation gate |
| `--use-checkov` | flag | ❌ | `false` | Enable Checkov static analysis + manifest validation gate |
| `--region` | string | ❌ | `us-west-2` | AWS region (respects `AWS_REGION` env var) |

#### Multi-Provider Consensus Example

```bash
# Use models from 3 different providers for inter-rater reliability
adversarial-iac game \
    --scenario "Create S3 bucket for PHI data" \
    --use-consensus-judge \
    --consensus-models "openai:gpt-4o,google:gemini-1.5-pro,bedrock:claude-3.5-sonnet" \
    --use-trivy --use-checkov
```

### Valid Values Reference

#### Difficulty Levels

| Level | Vulnerabilities | Stealth | Description |
|-------|-----------------|---------|-------------|
| `easy` | 2-3 | Low | Obvious misconfigurations |
| `medium` | 3-4 | Medium | Mixed obvious and subtle |
| `hard` | 4-5 | High | Stealthy, evasion-focused |

#### Languages

| Value | Description |
|-------|-------------|
| `terraform` | HashiCorp Terraform HCL |
| `cloudformation` | AWS CloudFormation YAML |

#### Cloud Providers

| Value | Description |
|-------|-------------|
| `aws` | Amazon Web Services |
| `azure` | Microsoft Azure |
| `gcp` | Google Cloud Platform |

> **Note:** Azure and GCP support is limited. AWS has the most complete vulnerability coverage.

#### Red Team Modes

| Mode | Agents | Description |
|------|--------|-------------|
| `single` | 1 | Single agent generates everything |
| `pipeline` | 4 | Architect → Selector → Generator → Reviewer |

#### Blue Team Modes

| Mode | Agents | Description |
|------|--------|-------------|
| `single` | 1 | Single agent analyzes code |
| `ensemble` | 3+1 | Security + Compliance + Architecture + Consensus |

#### Consensus Methods

Used when `blue_team_mode: ensemble`:

| Method | Description |
|--------|-------------|
| `debate` | LLM-based discussion to resolve conflicts |
| `vote` | Majority agreement (≥2 of 3 specialists) |
| `union` | All unique findings from all specialists |
| `intersection` | Only findings all specialists agree on |

#### Verification Modes

| Mode | Description |
|------|-------------|
| `standard` | Direct Judge scoring |
| `debate` | Prosecutor vs Defender debate per finding |

### Environment Variables

#### AWS (Required for Bedrock)

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_DEFAULT_REGION` | AWS region for Bedrock | `us-west-2` (framework default; set explicitly for your account) |
| `AWS_REGION` | Alternative region variable | Also respected by the framework |
| `AWS_ACCESS_KEY_ID` | AWS credentials | From AWS CLI |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | From AWS CLI |

#### Multi-Provider API Keys (Optional)

For multi-model consensus judging with inter-rater reliability:

| Variable | Description | Get From |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4, GPT-4o) | [platform.openai.com](https://platform.openai.com/api-keys) |
| `GOOGLE_API_KEY` | Google AI API key (for Gemini) | [aistudio.google.com](https://aistudio.google.com/app/apikey) |

Add to your `.env` file:

```bash
# AWS (always required)
AWS_DEFAULT_REGION=us-east-1

# Multi-provider consensus (optional, for publication-quality)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
```

---

# The Game

## How It Works

The Adversarial IaC Game pits two AI agents against each other in a security challenge.

### The Players

| Player | Role | Goal |
|--------|------|------|
| 🔴 **Red Team** | Attacker | Hide vulnerabilities in code |
| 🔵 **Blue Team** | Defender | Find the hidden vulnerabilities |
| ⚖️ **Judge** | Referee | Score who won |

### Game Flow

```
Scenario → Red Team → Blue Team → Judge → Final Score
```

1. **Scenario Selection**: A scenario describes what infrastructure to create (e.g., "Create an S3 bucket for storing healthcare PHI data with encryption and access logging")

2. **Red Team Turn**: Creates legitimate-looking code but injects hidden vulnerabilities

3. **Blue Team Turn**: Analyzes the code (without seeing the manifest) and reports findings

4. **Judge Scoring**: Compares what Red Team hid vs what Blue Team found

### Scoring System

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Precision** | TP / (TP + FP) | How accurate were Blue's reports? |
| **Recall** | TP / (TP + FN) | What % of Red's vulns did Blue find? |
| **F1 Score** | 2 × (P × R) / (P + R) | Overall Blue performance |
| **Evasion Rate** | FN / Total | What % of vulns did Red hide successfully? |

Where:
- **TP (True Positive)** = Blue correctly found Red's vulnerability
- **FP (False Positive)** = Blue reported something not in Red's manifest
- **FN (False Negative)** = Red's vulnerability that Blue missed

### Who Wins?

| If... | Winner |
|-------|--------|
| High Recall (>70%) | 🔵 Blue Team |
| High Evasion (>50%) | 🔴 Red Team |
| High F1 Score | 🔵 Blue Team overall |

---

## Red Team Agent

The Red Team agent's goal is to generate IaC code with **stealthy vulnerabilities** that evade detection.

### Vulnerability Source Modes

The Red Team can source vulnerabilities in three ways, controlled by `--red-vuln-source`:

| Mode | Flag | Description |
|------|------|-------------|
| **Database** | `--red-vuln-source database` | Selects from 142 known Trivy rules (default) |
| **Novel** | `--red-vuln-source novel` | LLM generates from security principles — no database shown |
| **Mixed** | `--red-vuln-source mixed` | 50% database, 50% novel — enables within-game comparison |

**Source Labels**: Every manifest entry carries `is_novel` (bool) and `rule_source` ("database" or "novel") for per-source analysis. These labels are set at vulnerability selection time and propagated through code generation, manifest validation, and scoring.

**Novel Specificity Requirement**: In novel mode, the LLM must specify the exact Terraform resource type, attribute name, and insecure value for each vulnerability. This reduces hallucination by forcing concrete implementation plans before code generation.

### Vulnerability Database

The database mode selects from real-world security issues:

- **142 Terraform AWS rules** from Trivy
- **100+ CloudFormation rules** 
- Categorized by type: encryption, access control, network, IAM, logging

### Stealth Techniques

**Easy Mode:**
- Obvious misconfigurations
- Missing encryption
- Public access enabled

**Medium Mode:**
- Overly permissive IAM policies
- Weak default configurations
- Missing logging

**Hard Mode:**
- Dynamic resource references
- Conditional misconfigurations
- Split across multiple files
- Legitimate-looking comments

### Output Format

```json
{
  "code": {
    "main.tf": "...",
    "variables.tf": "..."
  },
  "manifest": [
    {
      "vuln_id": "V001",
      "type": "encryption",
      "resource": "aws_s3_bucket.data",
      "description": "S3 bucket lacks encryption",
      "severity": "high"
    }
  ],
  "stealth_score": 0.8
}
```

---

## Blue Team Agent

The Blue Team agent's goal is to **detect all vulnerabilities** in the IaC code.

### Detection Methods

**LLM Analysis (Default):**

```python
BlueTeamAgent(
    model_id="claude-3-5-sonnet",
    detection_mode="llm_only"
)
```

**Hybrid Analysis (Optional):**

```python
BlueTeamAgent(
    detection_mode="hybrid",
    tools=["trivy", "checkov"]
)
```

### Blue Team Strategies

| Strategy | Flag | Description |
|----------|------|-------------|
| `comprehensive` | `--blue-strategy comprehensive` | Check for all vulnerability types (default) |
| `targeted` | `--blue-strategy targeted --blue-target-type encryption` | Focus on specific vulnerability type |
| `iterative` | `--blue-strategy iterative --blue-iterations 3` | Multiple analysis passes with refinement |
| `threat_model` | `--blue-strategy threat_model` | Start with threat model, then hunt for matching vulns |
| `compliance` | `--blue-strategy compliance --compliance-framework hipaa` | Check against compliance framework |
| **`precise`** | `--blue-strategy precise` | **Two-pass analysis** — detects everything, then verifies each finding against actual code. Removes unverifiable findings. Addresses the precision bottleneck. |

**Precise Strategy Details**: Pass 1 runs comprehensive detection. Pass 2 asks the LLM: "For each finding, show me the exact line of code that creates this vulnerability. If you cannot, remove it." This directly addresses the finding from E1 that precision (64-80%) is the bottleneck while recall exceeds 90%.

### Output Format

```json
{
  "findings": [
    {
      "finding_id": "F001",
      "resource_name": "aws_s3_bucket.data",
      "vulnerability_type": "encryption",
      "severity": "high",
      "title": "S3 bucket lacks server-side encryption",
      "description": "The bucket does not enable SSE...",
      "evidence": "No encryption configuration found",
      "remediation": "Add server_side_encryption_configuration block",
      "confidence": 0.95
    }
  ]
}
```

---

## Judge & Scoring

The Judge matches Blue Team findings to Red Team vulnerabilities and calculates metrics. It uses a **multi-tier approach** combining rule-based matching, LLM fallback, multi-model consensus, and tool triangulation for maximum accuracy and research rigor.

### Judging Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Rule-Based** | Fast, deterministic matching | Development, quick tests |
| **Hybrid LLM** | Rule-based + single LLM for ambiguous cases | Standard usage (default) |
| **Multi-Model Consensus** | Multiple LLMs vote on ambiguous cases | Publication-quality results |

### Hybrid Matching (Default)

The Judge uses a three-tier approach:

| Score Range | Action | Rationale |
|-------------|--------|-----------|
| **≥ 0.7** | Rule-based match | Clear match, no LLM needed |
| **0.3 - 0.7** | LLM evaluation | Ambiguous - ask the LLM |
| **< 0.3** | Clear miss | Too different to be a match |

### Multi-Model Consensus (Inter-Rater Reliability)

For publication-quality results, enable **multi-model consensus**. Multiple LLMs independently judge ambiguous cases, and Cohen's κ measures inter-rater agreement.

#### Multi-Provider Support (Strongest)

For maximum rigor, use models from **different providers**:

```bash
adversarial-iac game \
    --use-consensus-judge \
    --consensus-models "openai:gpt-4o,google:gemini-1.5-pro,bedrock:claude-3.5-sonnet" \
    ...
```

This gives you judges from **OpenAI, Google, and Anthropic** — completely independent training data and architectures.

#### Bedrock-Only (Simpler)

If you only have AWS credentials:

```bash
adversarial-iac game \
    --use-consensus-judge \
    --consensus-models "claude-3.5-sonnet,nova-pro,llama-3.1-70b" \
    ...
```

#### Required API Keys

| Provider | Environment Variable | Get From |
|----------|---------------------|----------|
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| Google | `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Bedrock | AWS credentials | Your AWS account |

#### Output Metrics

```json
{
  "inter_rater_reliability": {
    "models_used": ["openai-gpt4o", "google-gemini15pro", "bedrock-claude35sonnet"],
    "pairwise_kappa": {
      "openai-gpt4o_vs_google-gemini15pro": 0.82,
      "google-gemini15pro_vs_bedrock-claude35sonnet": 0.78,
      "openai-gpt4o_vs_bedrock-claude35sonnet": 0.85
    },
    "mean_kappa": 0.817,
    "agreement_rate": 0.89
  }
}
```

**Target:** κ > 0.70 indicates acceptable inter-rater reliability for security research.

### Tool-Triangulated Matching (Corroborated Tier)

When static tools are enabled, matches can be **corroborated** — meaning Red Team vulnerability, Blue Team finding, AND static tool all flag the same resource.

#### Match Types

| Type | Confidence | Description |
|------|------------|-------------|
| **Corroborated** | Highest | Red + Blue + Tool agree (non-LLM anchor) |
| **Exact** | High | Red + Blue match perfectly |
| **Partial** | Medium | Red + Blue semantically match |
| **Missed** | — | Blue didn't detect Red's vulnerability |

### Optimal Assignment

The Judge uses the **Hungarian algorithm** (optimal bipartite matching) to find the globally best assignment between vulnerabilities and findings.

---

## Scoring Metrics

### Core Metrics

#### Precision

$$\text{Precision} = \frac{TP}{TP + FP}$$

**Interpretation**: Of all findings reported, how many matched Red Team's manifest?

- High precision = Few false positives
- Low precision = Many false alarms

#### Adjusted Precision (Fairer Blue Team Metric)

$$\text{Adjusted Precision} = \frac{TP}{TP + TFP}$$

Where TFP = **True False Positives** (findings that neither Red's manifest nor static tools confirm)

**Interpretation**: Standard precision can unfairly penalize Blue Team for finding *real vulnerabilities* that Red didn't declare. Adjusted precision only counts findings as false positives if static tools also didn't find them.

- **Tool-Validated FPs**: Findings that don't match Red's manifest but Trivy/Checkov confirms → Not penalized
- **True False Positives**: Findings that neither manifest nor tools confirm → Penalized

**When to use**: Report adjusted precision when `--use-trivy` or `--use-checkov` is enabled. This gives a fairer assessment of Blue Team's actual accuracy.

#### Recall

$$\text{Recall} = \frac{TP}{TP + FN}$$

**Interpretation**: Of all injected vulnerabilities, how many were detected?

- High recall = Good detection coverage
- Low recall = Missing vulnerabilities

#### Adjusted Recall (v2.1)

$$\text{Adjusted Recall} = \frac{\text{Confirmed Detected}}{\text{Total Confirmed}}$$

Where "Confirmed" means tool-verified via the manifest validation gate.

**Interpretation**: Recall computed against tool-confirmed ground truth only. Phantom (hallucinated) vulnerabilities are excluded from both numerator and denominator.

**When to use**: Always report adjusted recall when `--use-trivy` or `--use-checkov` is enabled. Standard recall against unvalidated ground truth is not scientifically defensible when hallucination rates are non-trivial.

#### Phantom Concordance (v2.1)

$$\text{Phantom Concordance} = \frac{\text{Phantom Detections}}{\text{Total Detections}}$$

**Interpretation**: Fraction of Blue Team "detections" that correspond to phantom (non-existent) vulnerabilities. A high rate means Red and Blue are hallucinating the same vulnerability patterns — a shared latent vulnerability space in their training data.

**Research significance**: This metric quantifies the measurement validity threat for adversarial benchmarks without external tool validation. Any benchmark that relies on LLM-generated ground truth without tool corroboration has this problem latently.

#### F1 Score

$$F1 = 2 \cdot \frac{P \cdot R}{P + R}$$

**Interpretation**: Balanced measure of precision and recall.

#### Evasion Rate

$$\text{Evasion} = 1 - \text{Recall}$$

**Interpretation**: Fraction of vulnerabilities that evaded detection.

### Validation Metrics

#### Manifest Accuracy

$$\text{Manifest Accuracy} = \frac{\text{Confirmed Vulns}}{\text{Claimed Vulns}}$$

**Interpretation**: Percentage of Red Team claims verified by static tools.

#### Hallucination Rate

$$\text{Hallucination Rate} = 1 - \text{Manifest Accuracy}$$

**Interpretation**: Percentage of Red Team claims NOT found by static tools.

#### Corroboration Rate

$$\text{Corroboration Rate} = \frac{\text{Corroborated Matches}}{\text{Total Matches}}$$

**Interpretation**: Percentage of matches confirmed by Red + Blue + Static Tool.

### Inter-Rater Reliability (Multi-Model Consensus)

#### Cohen's Kappa (κ)

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

### Recommended Reporting

For publication, report:

| Metric | How to Report | Notes |
|--------|--------------|-------|
| Core metrics (F1, Recall, Precision) | Mean ± 95% CI | Use `analyze_experiments.py` |
| **Adjusted recall** | Mean ± 95% CI per condition | **Required** when tools enabled |
| Manifest accuracy | Mean ± std per vulnerability source | Database vs novel breakdown |
| **Phantom concordance** | Per condition | Measurement validity check |
| Evasion rate | Mean ± 95% CI | Report on confirmed vulns only |
| Corroboration rate | Mean ± std | When tool triangulation enabled |
| Inter-rater κ | Pairwise + mean | When consensus judge enabled |
| Statistical tests | t-test / ANOVA with p-values, Cohen's d | Use `analyze_experiments.py --latex` |

---

# Evaluation Modes & Strategies

## Modes Overview

| Mode | Flag | Description |
|------|------|-------------|
| **Standard** | (default) | Single agent per team |
| **Red Pipeline** | `--red-team-mode pipeline` | 4-stage attack chain |
| **Blue Ensemble** | `--blue-team-mode ensemble` | Expert panel + consensus |
| **Adversarial Debate** | `--verification-mode debate` | Verify findings through debate |

### Standard (1v1)

The simplest mode - one AI agent per team.

```bash
adversarial-iac game \
    --red-team-mode single \
    --blue-team-mode single \
    --scenario "Create S3 bucket for PHI" \
    --difficulty medium
```

---

## Red Team Pipeline

A **4-stage attack chain** where specialized agents collaborate to create stealthier vulnerabilities:

```bash
adversarial-iac game \
    --red-team-mode pipeline \
    --scenario "Create S3 bucket for PHI"
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                      RED TEAM PIPELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌──────────┐ │
│  │ Architect  │───▶│ Vuln       │───▶│ Code       │───▶│ Stealth  │ │
│  │            │    │ Selector   │    │ Generator  │    │ Reviewer │ │
│  └────────────┘    └────────────┘    └────────────┘    └──────────┘ │
│       │                 │                 │                 │        │
│   Designs          Chooses           Writes IaC        Applies      │
│   infrastructure   vulnerabilities   with vulns        evasion      │
│   blueprint        to inject         hidden            techniques   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

| Stage | Agent | Role |
|-------|-------|------|
| 1 | **Architect** | Designs infrastructure blueprint |
| 2 | **Vulnerability Selector** | Chooses which vulnerabilities to inject |
| 3 | **Code Generator** | Writes IaC code with hidden vulnerabilities |
| 4 | **Stealth Reviewer** | Applies obfuscation and evasion techniques |

---

## Blue Team Ensemble

Multiple **specialist agents** analyze code independently, then a **consensus agent** synthesizes findings:

```bash
adversarial-iac game \
    --blue-team-mode ensemble \
    --consensus-method vote \
    --scenario "Create S3 bucket for PHI"
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                      BLUE TEAM ENSEMBLE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Security   │  │  Compliance  │  │ Architecture │               │
│  │    Expert    │  │    Agent     │  │    Agent     │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                 │                        │
│         └─────────────────┼─────────────────┘                        │
│                           ▼                                          │
│                   ┌───────────────┐                                  │
│                   │   Consensus   │                                  │
│                   │     Agent     │                                  │
│                   └───────────────┘                                  │
│                           │                                          │
│                    Unified Findings                                  │
└─────────────────────────────────────────────────────────────────────┘
```

| Specialist | Focus |
|------------|-------|
| **Security Expert** | General security vulnerabilities, OWASP patterns |
| **Compliance Agent** | Regulatory compliance (HIPAA, PCI-DSS, SOC2) |
| **Architecture Agent** | Cloud best practices, AWS Well-Architected |

### Consensus Methods

| Method | Flag | Description |
|--------|------|-------------|
| **Vote** | `--consensus-method vote` | Majority voting on findings |
| **Debate** | `--consensus-method debate` | Agents debate each finding |
| **Union** | `--consensus-method union` | Include all findings |
| **Intersection** | `--consensus-method intersection` | Only findings all agree on |

---

## Adversarial Debate

Each Blue Team finding is **debated** by prosecutor and defender agents:

```bash
adversarial-iac game \
    --verification-mode debate \
    --scenario "Create S3 bucket for PHI"
```

For each Blue Team finding:

1. **Prosecutor** argues it's a real vulnerability
2. **Defender** argues it's a false positive
3. **Judge** renders final verdict

---

## Attack & Defense Strategies

### Red Team Strategies

| Strategy | Flag | Description |
|----------|------|-------------|
| **Balanced** | `--red-strategy balanced` | Mix of vulnerability types (default) |
| **Targeted** | `--red-strategy targeted` | Focus on specific type |
| **Stealth** | `--red-strategy stealth` | Maximize evasion with obfuscation |
| **Blitz** | `--red-strategy blitz` | Many vulnerabilities, less hiding |
| **Chained** | `--red-strategy chained` | Create vulnerability chains |

### Blue Team Strategies

| Strategy | Flag | Description |
|----------|------|-------------|
| **Comprehensive** | `--blue-strategy comprehensive` | Check everything (default) |
| **Targeted** | `--blue-strategy targeted` | Focus on specific vuln type |
| **Iterative** | `--blue-strategy iterative` | Multiple analysis passes |
| **Threat Model** | `--blue-strategy threat_model` | Threat modeling approach |
| **Compliance** | `--blue-strategy compliance` | Compliance framework focus |

### Combining Modes

Mix and match for advanced experiments:

```bash
# Full multi-agent game
adversarial-iac game \
    --red-team-mode pipeline \
    --red-strategy stealth \
    --blue-team-mode ensemble \
    --consensus-method debate \
    --blue-strategy comprehensive \
    --verification-mode debate \
    --use-trivy \
    --difficulty hard \
    --scenario "Create PCI-DSS compliant payment system"
```

---

# Scenarios & Models

## 114 Built-in Scenarios

The game includes **114 built-in scenarios** across 18 domains and 4 categories.

### Browse Scenarios

```bash
# List all scenarios
adversarial-iac scenarios

# Filter by category
adversarial-iac scenarios --category industry

# View specific domain
adversarial-iac scenarios --domain healthcare
```

### Categories

#### 🏗️ Infrastructure (32 scenarios)

Core AWS infrastructure patterns.

| Domain | Count | Description |
|--------|-------|-------------|
| **storage** | 6 | S3 buckets, DynamoDB tables, EFS |
| **compute** | 6 | Lambda functions, EC2 instances, ECS |
| **network** | 7 | VPCs, security groups, load balancers |
| **iam** | 7 | IAM roles, policies, cross-account access |
| **multi_service** | 6 | Data pipelines, web stacks, IoT platforms |

#### ☁️ AWS Services (36 scenarios)

Specific AWS service configurations.

| Domain | Count | Description |
|--------|-------|-------------|
| **secrets** | 6 | Secrets Manager, KMS, Parameter Store |
| **containers** | 6 | EKS, Fargate, ECR |
| **databases** | 6 | RDS, Aurora, ElastiCache, Redshift |
| **api** | 6 | API Gateway, AppSync, CloudFront |
| **messaging** | 6 | SQS, SNS, EventBridge |
| **monitoring** | 6 | CloudWatch, CloudTrail, X-Ray |

#### 🏢 Industry Verticals (36 scenarios)

Compliance-focused scenarios for regulated industries.

| Domain | Count | Description |
|--------|-------|-------------|
| **healthcare** | 8 | HIPAA-compliant systems |
| **financial** | 8 | PCI-DSS payment systems |
| **government** | 6 | FedRAMP compliance |
| **ecommerce** | 7 | Shopping cart, inventory |
| **saas** | 7 | Multi-tenant applications |

#### 🔒 Security Patterns (10 scenarios)

Security architecture patterns.

| Domain | Count | Description |
|--------|-------|-------------|
| **zero_trust** | 5 | Zero-trust architecture |
| **disaster_recovery** | 5 | DR and business continuity |

### Adding Custom Scenarios

**Option 1: Use Interactive Mode**
```bash
adversarial-iac play
# Choose "Custom - Describe your own scenario"
```

**Option 2: Use CLI**
```bash
adversarial-iac game \
    --scenario "Your custom scenario description here" \
    --red-model claude-3.5-sonnet \
    --blue-model nova-pro
```

---

## 20+ AI Models

The game supports **20+ AI models** via Amazon Bedrock, plus **OpenAI** and **Google** models for multi-provider consensus judging.

### Browse Models

```bash
adversarial-iac models
```

### Tiered Model Registry

#### 🏆 Frontier Tier

Best quality, highest cost. Use for final experiments and benchmarks.

| Short Name | Full Model ID |
|------------|---------------|
| `claude-3.5-sonnet` | us.anthropic.claude-3-5-sonnet-20241022-v2:0 |
| `claude-3-opus` | us.anthropic.claude-3-opus-20240229-v1:0 |
| `nova-premier` | amazon.nova-premier-v1:0 |
| `llama-3.3-70b` | us.meta.llama3-3-70b-instruct-v1:0 |
| `mistral-large-3` | mistral.mistral-large-3-675b-instruct |

#### 💪 Strong Tier

Good balance of quality and cost. Recommended for most experiments.

| Short Name | Full Model ID |
|------------|---------------|
| `claude-3.5-haiku` | us.anthropic.claude-3-5-haiku-20241022-v1:0 |
| `claude-3-sonnet` | us.anthropic.claude-3-sonnet-20240229-v1:0 |
| `nova-pro` | amazon.nova-pro-v1:0 |
| `llama-3.1-70b` | us.meta.llama3-1-70b-instruct-v1:0 |
| `mistral-large` | mistral.mistral-large-2407-v1:0 |
| `command-r-plus` | cohere.command-r-plus-v1:0 |

#### ⚡ Efficient Tier

Fast and cheap. Great for development and testing.

| Short Name | Full Model ID |
|------------|---------------|
| `claude-3-haiku` | us.anthropic.claude-3-haiku-20240307-v1:0 |
| `nova-lite` | amazon.nova-lite-v1:0 |
| `nova-micro` | amazon.nova-micro-v1:0 |
| `llama-3.1-8b` | us.meta.llama3-1-8b-instruct-v1:0 |
| `mistral-small` | mistral.mistral-small-2402-v1:0 |
| `ministral-8b` | mistral.ministral-3-8b-instruct |

#### 🔬 Specialized Tier

Experimental, reasoning, and code-specialized models.

| Short Name | Full Model ID | Notes |
|------------|---------------|-------|
| `deepseek-r1` | us.deepseek.r1-v1:0 | Reasoning model — requires `us.` prefix. Framework strips `<think>` blocks and reasoning content automatically. |
| `qwen3-coder` | qwen.qwen3-coder-30b-a3b-v1:0 | Code-specialized — framework strips markdown fences from output. |
| `jamba-1.5-large` | ai21.jamba-1-5-large-v1:0 | |
| `jamba-1.5-mini` | ai21.jamba-1-5-mini-v1:0 | |
| `command-r` | cohere.command-r-v1:0 | |

> **Reasoning Model Instrumentation**: DeepSeek-R1 returns responses with reasoning content blocks via the Bedrock Converse API. The framework explicitly discards these blocks — only the final text output is used for scoring. Without this, the judge would evaluate reasoning traces as if they were findings output, inflating or deflating scores unpredictably. This is handled automatically by the response sanitizer (`src/utils/response_sanitizer.py`).

### Recommendations

**For Development/Testing** - Use Efficient Tier models:
- Fast response times
- Low cost
- Good enough for debugging

**For Experiments** - Use Strong Tier models:
- Good quality
- Reasonable cost
- Reliable results

**For Final Benchmarks** - Use Frontier Tier models:
- Best quality
- Publication-ready results
- Higher cost

### Multi-Provider Models (For Consensus Judging)

For inter-rater reliability, use models from multiple providers:

#### OpenAI Models

| Model | Description |
|-------|-------------|
| `gpt-4o` | GPT-4 Omni - latest multimodal |
| `gpt-4-turbo` | GPT-4 Turbo |
| `gpt-4` | GPT-4 base |

Requires `OPENAI_API_KEY` environment variable.

#### Google Models

| Model | Description |
|-------|-------------|
| `gemini-1.5-pro` | Gemini 1.5 Pro |
| `gemini-1.5-flash` | Gemini 1.5 Flash (faster) |
| `gemini-pro` | Gemini Pro |

Requires `GOOGLE_API_KEY` environment variable.

#### Multi-Provider Consensus Example

```bash
# Use 3 providers for strongest inter-rater reliability
adversarial-iac game \
    --use-consensus-judge \
    --consensus-models "openai:gpt-4o,google:gemini-1.5-pro,bedrock:claude-3.5-sonnet" \
    --scenario "Create S3 bucket"
```

The provider prefix (`openai:`, `google:`, `bedrock:`) is optional — models are auto-detected by name.

### Multi-Provider Setup

For multi-provider consensus:

```bash
# .env file
OPENAI_API_KEY=sk-...    # From platform.openai.com
GOOGLE_API_KEY=AI...      # From aistudio.google.com
```

---

# For Researchers

## Running Experiments

### Single Games

```bash
adversarial-iac game \
    --scenario "Create an S3 bucket" \
    --difficulty medium
```

### Batch Experiments

Run multiple games with different configurations:

```bash
python scripts/run_experiment.py \
    --config experiments/config/E1_model_comparison_v2.yaml \
    --region us-east-1
```

#### Configuration Example

```yaml
name: "My Experiment"
models:
  - id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
    name: "Claude 3.5 Sonnet"
difficulties: [easy, medium, hard]
scenarios:
  - "Create an S3 bucket for logs"
  - "Create a VPC with subnets"
language: terraform
cloud_provider: aws
settings:
  repetitions: 3
  delay_between_games: 2
  save_intermediate: true
  random_seed: 42                    # Deterministic ordering (optional)
  manifest_accuracy_threshold: 0.5   # Auto-halt if accuracy drops below 50% (optional)
batch_experiments:
  enabled: true
  model_combinations:
    - red: "anthropic.claude-3-5-sonnet-20241022-v2:0"
      blue: "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

#### Experiment Runner Features

| Feature | Description |
|---------|-------------|
| **Progress Bar** | `[████████░░░░] 40% (72/180) F1=78% R=91% ETA: 2.3h` |
| **Running Gate-Check** | Reports manifest accuracy every 10 games |
| **Auto-Halt** | Stops if manifest accuracy drops below `manifest_accuracy_threshold` |
| **Deterministic Seeding** | `random_seed` in config for reproducible game ordering |
| **Cost Estimation** | Estimates per-game cost based on Bedrock pricing |
| **Intermediate Saves** | Progress saved after each game — resume-safe |

### Analyzing Results

#### Statistical Analysis Script

```bash
# Auto-detects experiment type and generates full report
python scripts/analyze_experiments.py experiments/results/exp1_stratification_v2

# With LaTeX table export
python scripts/analyze_experiments.py experiments/results/exp3_novel_v2 --latex

# Save LaTeX directly to file
python scripts/analyze_experiments.py experiments/results/exp3_novel_v2 --latex-file paper_tables.tex

# Save full report
python scripts/analyze_experiments.py experiments/results/exp1_stratification_v2 -o report.txt
```

Generates:
- Descriptive statistics with **95% confidence intervals** and standard deviations
- **T-tests** (Welch's) for pairwise comparisons with p-values and significance stars
- **ANOVA** (one-way) for multi-group comparisons with F-statistic and η²
- **Cohen's d** effect sizes with labels (negligible/small/medium/large)
- **LaTeX tables** ready to paste into papers

#### E3 Adjusted Analysis (Ground Truth Quality)

For experiments using `--use-trivy --use-checkov`:

```bash
python scripts/e3_adjusted_analysis.py
```

Produces four outputs:
1. **Adjusted recall** per condition — using only tool-confirmed vulnerabilities
2. **Phantom concordance rate** — fraction of Blue "detections" matching non-existent vulns
3. **Within-game analysis** for mixed condition — database vs novel on confirmed vulns only
4. **Paper findings summary** with ready-to-cite text

#### Paper Analysis Notebook

```bash
jupyter notebook notebooks/04_paper_analysis.ipynb
```

Auto-loads all experiments, generates publication figures (PDF + PNG), and produces LaTeX tables.

### Game Replay

Re-render completed game results without re-running:

```bash
adversarial-iac replay output/games/G-20260301_162712
```

Shows:
- Red Team vulnerabilities with source labels (novel/database)
- Scored vs phantom manifest partition
- Blue Team findings
- Scoring metrics (including adjusted recall and phantom concordance)
- Match details table

---

## Ground Truth Validation

A key research concern for adversarial benchmarks: **who validates the validator?**

### The Ground Truth Problem

In the adversarial framework:

1. Red Team generates code with "hidden vulnerabilities"
2. Red Team declares these vulnerabilities in a manifest
3. Judge scores Blue Team against this manifest

**But what if the Red Team hallucinates?** If it claims a vulnerability that doesn't exist, Blue Team gets penalized for "missing" something that was never there.

### Solution: External Validation

The framework uses **static analysis tools** (Trivy, Checkov) as an independent oracle to validate Red Team claims.

### Validation Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Manifest Accuracy** | Confirmed / Claimed | % of Red Team claims verified by tools |
| **Hallucination Rate** | Unconfirmed / Claimed | % of claims NOT found by tools |
| **Tool Coverage** | Per-tool breakdown | Which tools confirmed which vulns |

### Enabling Validation

```bash
# Enable Trivy and Checkov for validation
adversarial-iac game --use-trivy --use-checkov ...
```

### Interpreting Unconfirmed Vulnerabilities

An "unconfirmed" vulnerability could be:

1. **Tool-Blind (Real but Not Detected)**: The vulnerability exists, but static tools don't have a rule for it.

2. **Hallucinated (Doesn't Exist)**: The LLM claimed to inject a vulnerability but the code doesn't actually have it.

3. **Partially Injected**: The vulnerability was attempted but incomplete.

### Tool-Blind Vulnerabilities

Static tools (Trivy, Checkov) have known coverage gaps:

| Category | Examples | Why Tools Miss It |
|----------|----------|-------------------|
| **Logic-Level IAM** | Overly permissive policies that are syntactically valid | No semantic understanding |
| **Cross-Resource** | Vulnerabilities requiring multi-resource reasoning | Single-resource checks |
| **Context-Dependent** | Settings only wrong in certain scenarios | No scenario awareness |

These "tool-blind" vulnerabilities represent a **harder class of security reasoning** that static tools cannot reach. This makes LLM-based detection more interesting, not less rigorous.

### Research Recommendations

For publication-quality results:

1. **Report Manifest Accuracy** — Include mean ± std across all games
2. **Manual Audit Sample** — Review 10-20% of unconfirmed vulnerabilities
3. **Categorize Unconfirmed** — Tool-blind vs hallucinated vs partial
4. **Adjusted Scoring** — Optionally exclude hallucinated vulns from recall calculation

---

# Extending the Framework

## New Vulnerability Types

Add new vulnerability rules to `src/data/trivy_rules_db.json`:

```json
{
  "id": "MY-RULE-001",
  "title": "My Security Rule",
  "severity": "HIGH",
  "resource_type": "aws_s3_bucket"
}
```

---

# API Reference

## Game Engine API

The `GameEngine` class orchestrates the entire game flow.

```python
from src.game.engine import GameEngine

engine = GameEngine()
result = await engine.run_game(scenario, config)
```

### GameConfig

Configuration for a game.

```python
from src.game.engine import GameConfig

config = GameConfig(
    red_model="claude-3-5-sonnet",
    blue_model="claude-3-5-sonnet",
    difficulty="medium",
    language="terraform",
    cloud_provider="aws",
    red_team_mode="single",
    blue_team_mode="single",
    verification_mode="standard",
    region="us-west-2",
)
```

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `red_model` | str | required | Red Team model ID |
| `blue_model` | str | required | Blue Team model ID |
| `difficulty` | str | `"medium"` | `easy`, `medium`, `hard` |
| `language` | str | `"terraform"` | IaC language |
| `cloud_provider` | str | `"aws"` | Cloud provider |
| `red_team_mode` | str | `"single"` | `single`, `pipeline` |
| `blue_team_mode` | str | `"single"` | `single`, `ensemble` |
| `consensus_method` | str | `"debate"` | Ensemble consensus method |
| `verification_mode` | str | `"standard"` | `standard`, `debate` |
| `region` | str | `"us-west-2"` | AWS region |

### GameResult

Result from a completed game.

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | str | Unique game identifier |
| `scenario` | Scenario | The scenario that was run |
| `config` | GameConfig | Configuration used |
| `red_output` | RedTeamOutput | Red Team code and manifest |
| `blue_output` | BlueTeamOutput | Blue Team findings |
| `scoring` | ScoringResult | Match results and metrics |
| `red_time_seconds` | float | Red Team execution time |
| `blue_time_seconds` | float | Blue Team execution time |
| `total_time_seconds` | float | Total game time |

---

## Agents API

### RedTeamAgent

Generates IaC code with injected vulnerabilities.

```python
from src.agents.red_team_agent import RedTeamAgent

agent = RedTeamAgent(
    llm=llm,
    difficulty="medium",
    language="terraform",
    cloud_provider="aws",
)

output = await agent.execute(scenario_dict)
```

#### RedTeamOutput

| Field | Type | Description |
|-------|------|-------------|
| `code` | Dict[str, str] | Generated IaC files |
| `manifest` | List[InjectedVulnerability] | Injected vulnerabilities |
| `stealth_score` | float | Evasion likelihood (0-1) |

### BlueTeamAgent

Analyzes IaC code for security vulnerabilities.

```python
from src.agents.blue_team_agent import BlueTeamAgent

agent = BlueTeamAgent(
    llm=llm,
    language="terraform",
    detection_mode="llm_only",
)

output = await agent.execute(code_dict)
```

#### BlueTeamOutput

| Field | Type | Description |
|-------|------|-------------|
| `findings` | List[Finding] | Detected issues |

### JudgeAgent

Matches findings to vulnerabilities and calculates metrics.

```python
from src.agents.judge_agent import JudgeAgent

judge = JudgeAgent()
scoring = judge.score(red_manifest, blue_findings)
```

#### ScoringResult

| Field | Type | Description |
|-------|------|-------------|
| `precision` | float | TP / (TP + FP) |
| `adjusted_precision` | float | TP / (TP + TFP), fairer Blue metric |
| `recall` | float | TP / (TP + FN) |
| `f1_score` | float | Harmonic mean |
| `evasion_rate` | float | 1 - recall |
| `matches` | List[Match] | Matched pairs |
| `unmatched_vulns` | List | Evaded vulnerabilities |
| `unmatched_findings` | List | False positives (all) |
| `tool_validated_fps` | List | FPs confirmed by Trivy/Checkov (real issues) |
| `true_false_positives` | List | FPs not confirmed by tools (penalized) |
| `manifest_accuracy` | float/None | Confirmed / total claimed (v2.1) |
| `adjusted_recall` | float/None | Confirmed detected / confirmed total (v2.1) |
| `phantom_concordance` | float/None | Phantom detections / total detections (v2.1) |
| `confirmed_vulns_total` | int | Tool-confirmed vulnerability count (v2.1) |
| `phantom_vulns_total` | int | Unconfirmed (phantom) vulnerability count (v2.1) |

---

## Prompts API

### AdversarialPrompts

Contains all prompt templates for Red Team, Blue Team, and Judge agents.

#### Red Team Prompts

```python
from src.prompts import AdversarialPrompts

prompt = AdversarialPrompts.RED_TEAM_GENERATION.format(
    scenario=scenario_text,
    difficulty=difficulty,
    language=language,
    cloud_provider=cloud_provider,
    vulnerability_samples=samples_json,
)
```

#### Blue Team Prompts

```python
from src.prompts import AdversarialPrompts

prompt = AdversarialPrompts.BLUE_TEAM_DETECTION.format(
    language=language,
    code=code_content,
)
```

### ScenarioTemplates

Pre-defined scenario templates by domain.

```python
from src.prompts import ScenarioTemplates

# Get a random scenario for a domain
scenario = ScenarioTemplates.get_scenario("storage")

# Available domains
domains = ["storage", "compute", "network", "database", "serverless"]
```

---

# Research & Citation

## Citation

If you use the Adversarial IaC Benchmark in your research, please cite our work.

### BibTeX

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

### APA

Terry, B. (2026). *Adversarial IaC Benchmark: An Adversarial Evaluation Framework for LLM Security in Infrastructure-as-Code* [Computer software]. GitHub. https://github.com/brianterry/Adversarial-IaC-Evaluation

### Key Contributions

1. **Adversarial Evaluation Framework**: Unlike static benchmarks, our framework creates a dynamic adversarial environment.

2. **IaC-Specific Benchmark**: First comprehensive benchmark focused on Infrastructure-as-Code security with 114 scenarios across 18 domains.

3. **Multi-Agent Evaluation**: Evaluates emerging LLM architectures for security including ensembles, pipelines, and debate.

4. **Standardized Metrics**: Reproducible evaluation with Precision, Recall, F1, and Evasion Rate using the Hungarian algorithm.

5. **Ground Truth Validation Gate** (v2.1): Manifest validation via static tools is load-bearing for any recall claim. Phantom vulnerabilities are excluded from scored ground truth, and phantom concordance quantifies the measurement validity threat for adversarial benchmarks without external validation.

6. **Reasoning Model Instrumentation** (v2.1): Non-trivial instrumentation for DeepSeek-R1 and other reasoning models — reasoning blocks are explicitly discarded to prevent scoring contamination.

---

## Publications

### Papers Using AdversarialIaC-Bench

*Coming soon - be the first to publish!*

### Submit Your Paper

If you've published research using AdversarialIaC-Bench, we'd love to feature it here.

1. Open an issue on GitHub with the paper details
2. Or submit a PR adding your paper to this page

### Related Work

#### LLM Security Evaluation
- [SWE-bench](https://www.swebench.com/) - Software engineering benchmark
- [CyberSecEval](https://github.com/meta-llama/PurpleLlama) - Meta's security evaluation

#### IaC Security
- [Trivy](https://trivy.dev/) - Vulnerability scanner
- [Checkov](https://www.checkov.io/) - Policy-as-code scanner

---

## Contributing

We welcome contributions to AdversarialIaC-Bench!

### Ways to Contribute

- 🐛 **Report Issues**: Found a bug? [Open an issue](https://github.com/brianterry/Adversarial-IaC-Evaluation/issues/new).
- 📝 **Improve Documentation**: Edit files in `docs/` and submit a PR.
- 🔧 **Add Features**: Fork, branch, make changes, add tests, submit a PR.
- 🧪 **Add Scenarios**: Help expand scenario coverage (new cloud providers, IaC languages, domain-specific scenarios).
- 📊 **Share Results**: Run experiments and share findings (model comparisons, vulnerability analysis, multi-agent evaluations).

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
```

### Code Style

- Use `ruff` for linting
- Follow PEP 8
- Add type hints
- Write docstrings for public APIs

### Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Request review from maintainers

---

**Copyright © 2024-2026 Brian Terry**
