# Evaluation Modes

The Adversarial IaC Benchmark supports multiple modes for both attack and defense, from simple 1v1 evaluations to sophisticated multi-agent collaborations.

## Quick Reference

| Mode | Flag | Description |
|------|------|-------------|
| **Standard** | (default) | Single agent per team |
| **Red Pipeline** | `--red-team-mode pipeline` | 4-stage attack chain |
| **Blue Ensemble** | `--blue-team-mode ensemble` | Expert panel + consensus |
| **Adversarial Debate** | `--verification-mode debate` | Verify findings through debate |

---

## Team Modes

### Standard (1v1)

The simplest mode - one AI agent per team.

```bash
adversarial-iac game \
    --red-team-mode single \
    --blue-team-mode single \
    --scenario "Create S3 bucket for PHI" \
    --difficulty medium
```

```
Red Team Agent  ──────►  Blue Team Agent  ──────►  Judge
```

### Red Team Pipeline

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

### Blue Team Ensemble

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

#### Consensus Methods

| Method | Flag | Description |
|--------|------|-------------|
| **Vote** | `--consensus-method vote` | Majority voting on findings |
| **Debate** | `--consensus-method debate` | Agents debate each finding |
| **Union** | `--consensus-method union` | Include all findings |
| **Intersection** | `--consensus-method intersection` | Only findings all agree on |

### Adversarial Debate Verification

Each Blue Team finding is **debated** by prosecutor and defender agents:

```bash
adversarial-iac game \
    --verification-mode debate \
    --scenario "Create S3 bucket for PHI"
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ADVERSARIAL DEBATE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  For each Blue Team finding:                                         │
│                                                                      │
│  ┌──────────────┐                      ┌──────────────┐              │
│  │  Prosecutor  │ ◄─── Debates ───►    │   Defender   │              │
│  │              │                      │              │              │
│  │ "This IS a   │                      │ "This is a   │              │
│  │ vulnerability│                      │ FALSE        │              │
│  │ because..."  │                      │ POSITIVE..." │              │
│  └──────────────┘                      └──────────────┘              │
│         │                                     │                      │
│         └──────────────┬──────────────────────┘                      │
│                        ▼                                             │
│                ┌───────────────┐                                     │
│                │     Judge     │                                     │
│                │               │                                     │
│                │  VERDICT:     │                                     │
│                │  ✓ True Pos   │                                     │
│                │  ✗ False Pos  │                                     │
│                └───────────────┘                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Attack & Defense Strategies

### Red Team Strategies

Control how the Red Team selects and hides vulnerabilities:

| Strategy | Flag | Description |
|----------|------|-------------|
| **Balanced** | `--red-strategy balanced` | Mix of vulnerability types (default) |
| **Targeted** | `--red-strategy targeted` | Focus on specific type |
| **Stealth** | `--red-strategy stealth` | Maximize evasion with obfuscation |
| **Blitz** | `--red-strategy blitz` | Many vulnerabilities, less hiding |
| **Chained** | `--red-strategy chained` | Create vulnerability chains |

```bash
# Targeted attack on encryption
adversarial-iac game \
    --red-strategy targeted \
    --red-target-type encryption \
    --scenario "Create RDS database"

# Stealth attack
adversarial-iac game \
    --red-strategy stealth \
    --scenario "Create S3 bucket"

# Blitz attack (many vulns)
adversarial-iac game \
    --red-strategy blitz \
    --difficulty hard \
    --scenario "Create VPC"
```

### Blue Team Strategies

Control how the Blue Team analyzes code:

| Strategy | Flag | Description |
|----------|------|-------------|
| **Comprehensive** | `--blue-strategy comprehensive` | Check everything (default) |
| **Targeted** | `--blue-strategy targeted` | Focus on specific vuln type |
| **Iterative** | `--blue-strategy iterative` | Multiple analysis passes |
| **Threat Model** | `--blue-strategy threat_model` | Threat modeling approach |
| **Compliance** | `--blue-strategy compliance` | Compliance framework focus |

```bash
# Targeted defense
adversarial-iac game \
    --blue-strategy targeted \
    --blue-target-type iam \
    --scenario "Create IAM roles"

# Compliance-focused (HIPAA)
adversarial-iac game \
    --blue-strategy compliance \
    --compliance-framework hipaa \
    --scenario "Create healthcare API"

# Iterative analysis (3 passes)
adversarial-iac game \
    --blue-strategy iterative \
    --blue-iterations 3 \
    --scenario "Create Lambda function"
```

---

## Static Analysis Tools

Enable industry tools alongside LLM analysis:

```bash
# Enable Trivy
adversarial-iac game --use-trivy ...

# Enable Checkov
adversarial-iac game --use-checkov ...

# Both tools
adversarial-iac game --use-trivy --use-checkov ...
```

!!! note "Tool Installation"
    ```bash
    # Install Trivy (macOS)
    brew install trivy
    
    # Install Checkov
    pip install checkov
    ```
    
    Tools are optional - the game runs without them (LLM-only mode).

---

## Combining Modes

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

## Interactive Mode

All modes are available in the interactive wizard:

```bash
adversarial-iac play
```

The wizard guides you through selecting:

- Scenario
- Difficulty  
- Models
- Red Team mode and strategy
- Blue Team mode and strategy
- Static analysis tools
- Verification mode
