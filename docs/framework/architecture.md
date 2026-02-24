# Architecture

The framework consists of four core components that work together to run adversarial evaluations.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GAME ENGINE                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Orchestration Layer                           │    │
│  │  • Loads configuration       • Manages game state                   │    │
│  │  • Coordinates agents        • Collects results                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         │                          │                          │             │
│         ▼                          ▼                          ▼             │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐        │
│  │  RED TEAM   │           │  BLUE TEAM  │           │    JUDGE    │        │
│  │   AGENT     │           │    AGENT    │           │    AGENT    │        │
│  │             │           │             │           │             │        │
│  │ ┌─────────┐ │  Code     │ ┌─────────┐ │ Findings  │ ┌─────────┐ │        │
│  │ │   LLM   │─┼──────────►│ │   LLM   │─┼─────────►│ │ Matcher │ │        │
│  │ └─────────┘ │           │ └─────────┘ │           │ └─────────┘ │        │
│  │ ┌─────────┐ │           │ ┌─────────┐ │           │ ┌─────────┐ │        │
│  │ │  Vuln   │ │  Manifest │ │  Tools  │ │           │ │ Metrics │ │        │
│  │ │   DB    │─┼─ ─ ─ ─ ─ ─│ │(optional)│           │ │ Engine  │ │        │
│  │ └─────────┘ │  (secret) │ └─────────┘ │           │ └─────────┘ │        │
│  └─────────────┘           └─────────────┘           └─────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    RESULTS      │
                          │  • Metrics      │
                          │  • Artifacts    │
                          │  • Analysis     │
                          └─────────────────┘
```

## Component Details

### 1. Game Engine

The orchestration layer that coordinates all components.

**Responsibilities:**
- Load experiment configuration
- Initialize agents with specified models
- Execute game protocol (Red → Blue → Judge)
- Manage artifacts and results
- Support batch experiments

**Key Classes:**
```python
class GameEngine:
    """Orchestrates adversarial games"""
    
    def __init__(self, config: GameConfig):
        self.red_team = RedTeamAgent(config.red_model)
        self.blue_team = BlueTeamAgent(config.blue_model)
        self.judge = JudgeAgent()
    
    async def play(self, scenario: str) -> GameResult:
        # 1. Red Team generates adversarial code
        red_output = await self.red_team.generate(scenario)
        
        # 2. Blue Team analyzes (only sees code, not manifest)
        blue_findings = await self.blue_team.analyze(red_output.code)
        
        # 3. Judge scores the match
        scores = self.judge.score(red_output.manifest, blue_findings)
        
        return GameResult(red_output, blue_findings, scores)
```

### 2. Red Team Agent

Generates adversarial Infrastructure-as-Code with hidden vulnerabilities.

**Responsibilities:**
- Generate legitimate-looking IaC code
- Inject vulnerabilities using stealth techniques
- Produce ground truth manifest
- Adapt strategy based on difficulty

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│                  RED TEAM AGENT                      │
│                                                      │
│  ┌──────────────┐    ┌──────────────┐               │
│  │   Scenario   │───►│    Prompt    │               │
│  │    Input     │    │   Builder    │               │
│  └──────────────┘    └──────┬───────┘               │
│                             │                        │
│  ┌──────────────┐           ▼                        │
│  │ Vulnerability│    ┌──────────────┐               │
│  │   Database   │───►│     LLM      │               │
│  │  (142 rules) │    │   Generator  │               │
│  └──────────────┘    └──────┬───────┘               │
│                             │                        │
│  ┌──────────────┐           ▼                        │
│  │  Difficulty  │    ┌──────────────┐               │
│  │   Settings   │───►│   Output     │───► Code +    │
│  │              │    │   Parser     │     Manifest  │
│  └──────────────┘    └──────────────┘               │
└─────────────────────────────────────────────────────┘
```

**Stealth Techniques by Difficulty:**

| Difficulty | Techniques |
|------------|------------|
| Easy | Basic misconfigurations (missing encryption, public access) |
| Medium | Misleading comments, subtle omissions, valid-looking defaults |
| Hard | Chained vulnerabilities, misdirection, security-looking insecure code |

### 3. Blue Team Agent

Analyzes code to detect security vulnerabilities.

**Responsibilities:**
- Parse and understand IaC code
- Identify security issues
- Report findings with evidence
- Support multiple detection modes

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│                  BLUE TEAM AGENT                     │
│                                                      │
│  ┌──────────────┐                                    │
│  │  Code Input  │                                    │
│  └──────┬───────┘                                    │
│         │                                            │
│         ▼                                            │
│  ┌──────────────────────────────────────────┐       │
│  │           Detection Pipeline              │       │
│  │                                           │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │       │
│  │  │   LLM   │  │  Trivy  │  │ Checkov │  │       │
│  │  │ Analysis│  │  Scan   │  │  Scan   │  │       │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  │       │
│  │       │            │            │        │       │
│  │       └────────────┼────────────┘        │       │
│  │                    ▼                     │       │
│  │            ┌─────────────┐               │       │
│  │            │   Merger/   │               │       │
│  │            │ Deduplicator│               │       │
│  │            └──────┬──────┘               │       │
│  └───────────────────┼──────────────────────┘       │
│                      ▼                               │
│               ┌─────────────┐                        │
│               │  Findings   │                        │
│               └─────────────┘                        │
└─────────────────────────────────────────────────────┘
```

**Detection Modes:**

| Mode | Components | Use Case |
|------|------------|----------|
| `llm_only` | LLM semantic analysis | Research on LLM capabilities |
| `tools_only` | Trivy + Checkov | Baseline static analysis |
| `hybrid` | LLM + Tools | Combined detection study |

### 4. Judge Agent

Scores matches between ground truth and detections.

**Responsibilities:**
- Compare Red Team manifest to Blue Team findings
- Compute matching scores
- Calculate metrics (precision, recall, F1, evasion)
- Handle partial matches

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│                    JUDGE AGENT                       │
│                                                      │
│  ┌──────────────┐       ┌──────────────┐            │
│  │ Red Manifest │       │ Blue Findings│            │
│  │ (Ground Truth)       │ (Detections) │            │
│  └──────┬───────┘       └──────┬───────┘            │
│         │                      │                     │
│         └──────────┬───────────┘                     │
│                    ▼                                 │
│         ┌─────────────────────┐                      │
│         │   Matching Engine   │                      │
│         │                     │                      │
│         │ • Category matching │                      │
│         │ • Resource matching │                      │
│         │ • Keyword similarity│                      │
│         │ • Severity matching │                      │
│         └──────────┬──────────┘                      │
│                    │                                 │
│                    ▼                                 │
│         ┌─────────────────────┐                      │
│         │   Greedy Assignment │                      │
│         │                     │                      │
│         │ Match highest scores│                      │
│         │ first, no duplicates│                      │
│         └──────────┬──────────┘                      │
│                    │                                 │
│                    ▼                                 │
│         ┌─────────────────────┐                      │
│         │   Metrics Engine    │                      │
│         │                     │                      │
│         │ TP, FP, FN → P, R, F1                     │
│         └─────────────────────┘                      │
└─────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Configuration
   ├── Scenario: "Create S3 bucket for PHI data"
   ├── Red Model: claude-3-5-sonnet
   ├── Blue Model: claude-3-5-haiku
   └── Difficulty: hard

2. Red Team Output
   ├── main.tf (Terraform code)
   └── manifest.json
       └── vulnerabilities: [
             {id: "v1", type: "encryption", resource: "aws_s3_bucket.data"},
             {id: "v2", type: "public_access", resource: "aws_s3_bucket.data"}
           ]

3. Blue Team Input (code only, no manifest)
   └── main.tf

4. Blue Team Output
   └── findings: [
         {type: "encryption", resource: "aws_s3_bucket.data", severity: "HIGH"},
         {type: "logging", resource: "aws_s3_bucket.data", severity: "MEDIUM"}
       ]

5. Judge Scoring
   ├── Match: v1 ↔ finding[0] (score: 0.85) ✓
   ├── Miss: v2 (no match above threshold) ✗
   └── False Positive: finding[1] (not in manifest)

6. Results
   ├── TP: 1, FP: 1, FN: 1
   ├── Precision: 50%, Recall: 50%, F1: 50%
   └── Evasion Rate: 50%
```

## Extensibility Points

Each component exposes interfaces for customization:

| Component | Extension Interface | Example |
|-----------|---------------------|---------|
| Red Team | `RedTeamStrategy` | Custom vulnerability injection |
| Blue Team | `DetectionPipeline` | Add new analysis tools |
| Judge | `MatchingAlgorithm` | Semantic embedding matching |
| Game Engine | `GameProtocol` | Multi-round games |

## Next Steps

- [Game Protocol](game-protocol.md) - Detailed game flow
- [Scoring System](scoring.md) - Metrics deep dive
- [Extending](../extending/overview.md) - Build custom components
