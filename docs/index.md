# 🎮 Adversarial IaC Game

<p align="center">
  <strong>A Red Team vs Blue Team Security Game for Infrastructure-as-Code</strong>
</p>

<p align="center">
  <a href="getting-started/installation/">Play Now</a> •
  <a href="game/how-it-works/">How It Works</a> •
  <a href="experiments/single-game/">Run Experiments</a> •
  <a href="research/citation/">Cite Us</a>
</p>

---

## What is This?

It's a **game** where two AI agents compete:

- 🔴 **Red Team (Attacker)**: Creates infrastructure code with hidden security vulnerabilities
- 🔵 **Blue Team (Defender)**: Analyzes the code to find those hidden issues
- ⚖️ **Judge**: Scores who won based on what was found vs what was hidden

Think of it like **capture the flag**, but for cloud security.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     THE ADVERSARIAL IaC GAME                        │
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

!!! abstract "The Research Gap"
    Current LLM security benchmarks evaluate models on **static datasets** with **known vulnerabilities**. This leads to:
    
    - **Memorization over reasoning** — Models learn patterns, not security principles
    - **Missing adversarial dynamics** — Real attackers adapt; benchmarks don't
    - **Generic code focus** — IaC has unique security semantics that aren't tested
    
    **We need benchmarks where AI actively tries to evade detection.**

### What's Novel

<div class="grid cards" markdown>

-   :material-sword-cross:{ .lg .middle } __Adversarial Evaluation__

    ---
    
    First benchmark where LLMs **actively compete**. Red Team tries to evade, Blue Team tries to detect. Measures true adversarial robustness.

-   :material-refresh:{ .lg .middle } __Dynamic Generation__

    ---
    
    Red Team creates **new vulnerable code each game**. No memorization possible—tests real security reasoning.

-   :material-cloud-lock:{ .lg .middle } __IaC-Specific__

    ---
    
    **114 scenarios** purpose-built for Infrastructure-as-Code: HIPAA, PCI-DSS, FedRAMP, and cloud-native patterns.

-   :material-account-group:{ .lg .middle } __Multi-Agent__

    ---
    
    Evaluates emerging patterns: **specialist ensembles**, **attack pipelines**, and **adversarial debate** verification.

</div>

### Research Questions You Can Answer

| Question | How the Game Helps |
|----------|-------------------|
| How do LLMs compare at detecting IaC vulnerabilities? | Run symmetric experiments across models |
| Does multi-agent collaboration improve detection? | Compare ensemble vs single-agent modes |
| Which evasion techniques are most effective? | Analyze Red Team strategy success rates |
| How well do LLMs understand compliance frameworks? | Test HIPAA vs PCI-DSS vs FedRAMP scenarios |
| Does adversarial debate reduce false positives? | Compare standard vs debate verification |

---

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

## Quick Start

```bash
# Install
pip install -e .

# Play!
adversarial-iac play
```

The interactive wizard guides you through scenario selection, model choices, and explains results clearly. No command-line flags to remember!

??? note "Prefer CLI? Direct command available"
    ```bash
    adversarial-iac game \
        --red-model claude-3.5-sonnet \
        --blue-model nova-pro \
        --scenario "Create an S3 bucket for healthcare PHI data" \
        --difficulty medium
    ```

## Features

<div class="grid cards" markdown>

-   :material-gamepad:{ .lg .middle } __114 Built-in Scenarios__

    ---

    Healthcare, financial, government, e-commerce, and more across 18 domains.

    [:octicons-arrow-right-24: Browse scenarios](extending/scenarios.md)

-   :material-robot:{ .lg .middle } __20+ AI Models__

    ---

    Claude, Nova, Llama, Mistral, DeepSeek via AWS Bedrock with tiered recommendations.

    [:octicons-arrow-right-24: See models](extending/models.md)

-   :material-sword-cross:{ .lg .middle } __Multiple Game Modes__

    ---

    Single agents, multi-agent pipelines, ensemble teams, and adversarial debates.

    [:octicons-arrow-right-24: Game modes](multi-agent/overview.md)

-   :material-chart-line:{ .lg .middle } __Research-Ready Metrics__

    ---

    Precision, Recall, F1, Evasion Rate with optimal bipartite matching.

    [:octicons-arrow-right-24: Scoring system](framework/metrics.md)

-   :material-strategy:{ .lg .middle } __Attack & Defense Strategies__

    ---

    Stealth attacks, targeted defenses, compliance checks, and more.

    [:octicons-arrow-right-24: Strategies](framework/red-team.md)

-   :material-flask:{ .lg .middle } __Experiment Runner__

    ---

    Run batch experiments across model combinations and generate publication-ready data.

    [:octicons-arrow-right-24: Run experiments](experiments/batch.md)

</div>

## Example Output

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
```

## Game Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Single (1v1)** | One agent per team | Fast games, baseline testing |
| **Red Pipeline** | 4-stage attack chain | Stealthier vulnerabilities |
| **Blue Ensemble** | Expert panel + voting | Better detection accuracy |
| **Debate** | Prosecutor vs Defender | Verify each finding |

## Next Steps

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __Install__

    ---

    2-minute setup with pip

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-play:{ .lg .middle } __Play__

    ---

    Run your first game

    [:octicons-arrow-right-24: Quick start](getting-started/quickstart.md)

-   :material-school:{ .lg .middle } __Learn__

    ---

    How the game works

    [:octicons-arrow-right-24: Game mechanics](framework/architecture.md)

-   :material-flask:{ .lg .middle } __Research__

    ---

    Run experiments for papers

    [:octicons-arrow-right-24: Experiments](experiments/batch.md)

</div>

## Citation

If you use this game in your research, please cite:

```bibtex
@software{adversarial_iac_game,
  title = {Adversarial IaC Game: A Red Team vs Blue Team Framework for LLM Security Evaluation},
  author = {Terry, Brian},
  year = {2026},
  url = {https://github.com/brianterry/Adversarial-IaC-Evaluation}
}
```
