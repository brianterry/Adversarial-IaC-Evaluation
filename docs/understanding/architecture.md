# How It Works

The Adversarial IaC Game pits two AI agents against each other in a security challenge.

## The Players

| Player | Role | Goal |
|--------|------|------|
| Red Team | Attacker | Hide vulnerabilities in code |
| Blue Team | Defender | Find the hidden vulnerabilities |
| Judge | Referee | Score who won |

## Game Flow

```mermaid
sequenceDiagram
    participant S as Scenario
    participant R as Red Team
    participant B as Blue Team
    participant J as Judge

    S->>R: "Create S3 bucket for PHI data"
    R->>R: Generate code with hidden vulns
    R->>B: Code (vulns hidden)
    R->>J: Secret manifest
    B->>B: Analyze code
    B->>J: Findings
    J->>J: Compare manifest vs findings
    J-->>S: Scores
```

## Step by Step

### 1. Scenario

A scenario describes what infrastructure to create, e.g. "Create an S3 bucket for healthcare PHI data with encryption." 114 built-in scenarios across Healthcare, Financial, Government, and infrastructure domains.

### 2. Red Team

Receives the scenario and:

1. Creates legitimate-looking code
2. Injects hidden vulnerabilities (count depends on difficulty)
3. Documents what they hid in a manifest (ground truth)

Output: `main.tf` (or CloudFormation) and `red_team_manifest.json`.

### 3. Blue Team

Receives only the code (not the manifest):

1. Analyzes the code using LLM reasoning (and optionally Trivy/Checkov)
2. Reports findings with severity, location, evidence

Output: `blue_team_findings.json`.

### 4. Judge

Compares manifest vs findings using optimal bipartite matching. Calculates:

| Metric | Meaning |
|--------|---------|
| **Precision** | How accurate were Blue's reports? (TP / (TP + FP)) |
| **Recall** | What % of Red's vulns did Blue find? (TP / (TP + FN)) |
| **F1** | Overall Blue performance |
| **Evasion Rate** | What % of vulns did Red hide successfully? |

## Output

```
output/games/G-YYYYMMDD_HHMMSS/
├── code/main.tf
├── red_team_manifest.json
├── blue_team_findings.json
├── game_result.json
└── game.log
```
