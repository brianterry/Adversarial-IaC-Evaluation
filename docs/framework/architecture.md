# How the Game Works

The Adversarial IaC Game pits two AI agents against each other in a security challenge.

## The Players

| Player | Role | Goal |
|--------|------|------|
| 🔴 **Red Team** | Attacker | Hide vulnerabilities in code |
| 🔵 **Blue Team** | Defender | Find the hidden vulnerabilities |
| ⚖️ **Judge** | Referee | Score who won |

## Game Flow

```mermaid
sequenceDiagram
    participant S as 📋 Scenario
    participant R as 🔴 Red Team
    participant B as 🔵 Blue Team
    participant J as ⚖️ Judge

    S->>R: "Create S3 bucket for PHI data"
    R->>R: Generate code with hidden vulns
    R->>B: Here's the code (vulns hidden)
    R->>J: Secret list of what I hid
    B->>B: Analyze code for issues
    B->>J: Here's what I found
    J->>J: Compare findings vs hidden vulns
    J-->>S: 📊 Final Score: Blue wins 67%
```

## Step by Step

### 1️⃣ Scenario Selection

A scenario describes what infrastructure to create:

```
"Create an S3 bucket for storing healthcare PHI data
 with encryption and access logging"
```

You can choose from 114 built-in scenarios across domains like:
- Healthcare (HIPAA)
- Financial (PCI-DSS)
- Government (FedRAMP)
- Standard infrastructure (VPC, IAM, compute)

### 2️⃣ Red Team Turn

The Red Team receives the scenario and must:

1. **Create legitimate-looking code** - The infrastructure should work
2. **Inject hidden vulnerabilities** - Based on difficulty level
3. **Document what they hid** - This becomes the "ground truth"

```
┌─────────────────────────────────────────────────────────────┐
│  🔴 RED TEAM THINKING...                                    │
│                                                             │
│  "OK, I need to create an S3 bucket for PHI data.          │
│   But I'll secretly:                                        │
│   • Skip server-side encryption                             │
│   • Make the bucket publicly accessible                     │
│   • Use an overly permissive bucket policy                  │
│                                                             │
│   Let's see if Blue Team catches these!"                    │
└─────────────────────────────────────────────────────────────┘
```

**Output:**
- `main.tf` - Terraform code (looks normal)
- `manifest.json` - Secret list of hidden vulnerabilities

### 3️⃣ Blue Team Turn

The Blue Team receives ONLY the code (not the manifest):

1. **Analyze the code** - Using LLM reasoning and optionally static tools
2. **Report findings** - Each issue with severity, location, evidence
3. **No cheating** - They don't know what Red Team actually hid

```
┌─────────────────────────────────────────────────────────────┐
│  🔵 BLUE TEAM THINKING...                                   │
│                                                             │
│  "Let me analyze this S3 configuration...                  │
│                                                             │
│   🔍 Finding 1: No server-side encryption configured        │
│   🔍 Finding 2: Bucket is publicly accessible               │
│   🔍 Finding 3: Missing access logging                      │
│   🔍 Finding 4: Bucket policy allows any IAM principal"     │
└─────────────────────────────────────────────────────────────┘
```

**Output:**
- List of findings with evidence and remediation

### 4️⃣ Judge Scoring

The Judge compares what Red Team hid vs what Blue Team found:

```
┌─────────────────────────────────────────────────────────────┐
│  ⚖️  JUDGE COMPARING...                                     │
│                                                             │
│  Red Team Manifest         Blue Team Findings               │
│  ─────────────────         ─────────────────                │
│  ✓ No encryption     ◀───▶  ✓ No SSE configured            │
│  ✓ Public bucket     ◀───▶  ✓ Publicly accessible          │
│  ✗ Weak IAM policy   ◀───▶  (not found - evaded!)          │
│                                                             │
│  Extra Blue Finding:        Missing access logging          │
│  (False positive - not a real vuln in the manifest)        │
└─────────────────────────────────────────────────────────────┘
```

## Scoring System

The Judge calculates four key metrics:

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

## Who Wins?

| If... | Winner |
|-------|--------|
| High Recall (>70%) | 🔵 Blue Team |
| High Evasion (>50%) | 🔴 Red Team |
| High F1 Score | 🔵 Blue Team overall |

## Difficulty Levels

The difficulty controls how hard Red Team tries to hide vulnerabilities:

| Level | Vulns | Techniques |
|-------|-------|------------|
| 🟢 **Easy** | 2-3 | Obvious misconfigs (missing encryption, public access) |
| 🟡 **Medium** | 3-4 | Subtle issues (overly permissive IAM, weak defaults) |
| 🔴 **Hard** | 4-5 | Stealthy (dynamic refs, conditional misconfig, chaining) |

## Game Output

Each game creates a folder with all artifacts:

```
output/games/G-20260224_143052/
├── code/
│   └── main.tf                # Red Team's generated code
├── red_team_manifest.json     # Hidden vulnerabilities (ground truth)
├── blue_team_findings.json    # Blue Team's detections
├── game_result.json           # Full results with scores
└── game.log                   # Detailed execution log
```

## Next Steps

- [🔴 Red Team](red-team.md) - How the attacker agent works
- [🔵 Blue Team](blue-team.md) - How the defender agent works  
- [⚖️ Judge & Scoring](judge.md) - Detailed scoring algorithm
- [Game Modes](../multi-agent/overview.md) - Multi-agent team strategies
