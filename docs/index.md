# Adversarial IaC Eval

<p style="font-size: 1.3em; color: #888;">
A game-theoretic framework for evaluating LLM security capabilities in Infrastructure-as-Code
</p>

---

## The Problem

Evaluating LLM security capabilities faces a fundamental challenge: **the labeled data problem**.

- Vulnerable code samples are hard to collect ethically
- Ground truth labels require expensive expert annotation
- Static datasets become stale and don't reflect real-world complexity
- No standardized methodology for adversarial security evaluation

## Our Solution

**Adversarial IaC Eval** introduces a game-theoretic framework where LLMs compete against each other, automatically generating both vulnerable code and ground truth labels.

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  🔴 RED TEAM │ ──────► │  🔵 BLUE TEAM │ ──────► │  ⚖️ JUDGE    │
│   (Attack)   │  Code   │   (Defend)   │ Results │   (Score)    │
│              │         │              │         │              │
│ • Generates  │         │ • Analyzes   │         │ • Compares   │
│   vulnerable │         │   code for   │         │   findings   │
│   IaC code   │         │   security   │         │   to ground  │
│ • Provides   │         │   issues     │         │   truth      │
│   ground     │         │              │         │ • Computes   │
│   truth      │         │              │         │   metrics    │
└──────────────┘         └──────────────┘         └──────────────┘
```

## Why Use This Framework?

<div class="grid cards" markdown>

-   :material-infinity:{ .lg .middle } **Infinite Scalability**

    ---

    Generate unlimited test cases without manual labeling. Each game produces new vulnerable code with automatic ground truth.

-   :material-target:{ .lg .middle } **True Adversarial Testing**

    ---

    Red Team actively tries to evade detection, stress-testing security capabilities under realistic attack conditions.

-   :material-swap-horizontal:{ .lg .middle } **Model Comparison**

    ---

    Compare any LLM against any other. Test if models can find their own vulnerabilities or defend against different attackers.

-   :material-puzzle:{ .lg .middle } **Extensible Design**

    ---

    Plug in custom scenarios, models, metrics, and agents. Build on the framework for your own research.

</div>

## Framework Components

| Component | Role | Extensible |
|-----------|------|------------|
| **Red Team Agent** | Generates adversarial IaC with hidden vulnerabilities | ✅ Custom attack strategies |
| **Blue Team Agent** | Detects security issues in code | ✅ Custom detection modes |
| **Judge Agent** | Scores matches between ground truth and findings | ✅ Custom matching algorithms |
| **Game Engine** | Orchestrates games and experiments | ✅ Custom game protocols |
| **Scenario Generator** | Creates infrastructure scenarios | ✅ Custom domains |

## Quick Example

```python
from adversarial_iac_eval import Game, Difficulty

# Run a single game
game = Game(
    red_model="claude-3-5-sonnet",
    blue_model="claude-3-5-haiku",
    difficulty=Difficulty.HARD
)

results = await game.play(
    scenario="Create S3 bucket for healthcare PHI data"
)

print(f"Red injected: {results.vulnerabilities_injected}")
print(f"Blue detected: {results.vulnerabilities_found}")
print(f"Evasion rate: {results.evasion_rate:.1%}")
```

## Research Applications

This framework enables multiple research directions:

- **Model Capability Studies**: Which models are better at attack vs defense?
- **Difficulty Scaling**: How does stealth technique sophistication affect detection?
- **Tool Comparison**: How do LLMs compare to static analysis tools?
- **Multi-Agent Systems**: Can agent collaboration improve security?
- **Cross-Domain Analysis**: Are some infrastructure domains harder to secure?

## Get Started

<div class="grid cards" markdown>

-   [:material-download: **Installation**](getting-started/installation.md)

    Set up the framework in 5 minutes

-   [:material-rocket-launch: **Quick Start**](getting-started/quickstart.md)

    Run your first adversarial game

-   [:material-cog: **Architecture**](framework/architecture.md)

    Understand how components work together

-   [:material-puzzle-plus: **Extending**](extending/overview.md)

    Build on the framework for your research

</div>

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{terry2026adversarial_iac_eval,
  author = {Terry, Brian},
  title = {Adversarial IaC Eval: A Game-Theoretic Framework for 
           Evaluating LLM Security in Infrastructure-as-Code},
  year = {2026},
  url = {https://github.com/brianterry/Adversarial-IaC-Evaluation}
}
```

## License

MIT License - Use freely for research and commercial applications.
