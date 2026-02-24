# Prompts API

## AdversarialPrompts

Contains all prompt templates for Red Team, Blue Team, and Judge agents.

### Red Team Prompts

```python
from src.prompts import AdversarialPrompts

# Main generation prompt
prompt = AdversarialPrompts.RED_TEAM_GENERATION.format(
    scenario=scenario_text,
    difficulty=difficulty,
    language=language,
    cloud_provider=cloud_provider,
    vulnerability_samples=samples_json,
)
```

### Blue Team Prompts

```python
from src.prompts import AdversarialPrompts

# Detection prompt
prompt = AdversarialPrompts.BLUE_TEAM_DETECTION.format(
    language=language,
    code=code_content,
)
```

### Specialist Prompts (Ensemble Mode)

```python
# Security Expert
AdversarialPrompts.BLUE_TEAM_SECURITY_EXPERT_ANALYSIS

# Compliance Agent
AdversarialPrompts.BLUE_TEAM_COMPLIANCE_AGENT_ANALYSIS

# Architecture Agent
AdversarialPrompts.BLUE_TEAM_ARCHITECTURE_AGENT_ANALYSIS

# Consensus
AdversarialPrompts.BLUE_TEAM_CONSENSUS_DEBATE
```

---

## ScenarioTemplates

Pre-defined scenario templates by domain.

```python
from src.prompts import ScenarioTemplates

# Get a random scenario for a domain
scenario = ScenarioTemplates.get_scenario("storage")
# Returns: "Create an S3 bucket for storing application logs"

# Available domains
domains = ["storage", "compute", "network", "database", "serverless"]
```

### Available Domains

| Domain | Example Scenarios |
|--------|-------------------|
| `storage` | S3 buckets, EFS, backup |
| `compute` | EC2 instances, ASG |
| `network` | VPC, subnets, security groups |
| `database` | RDS, DynamoDB |
| `serverless` | Lambda, API Gateway |

---

## RedTeamPipelinePrompts

Prompts for multi-agent Red Team pipeline.

```python
from src.prompts import RedTeamPipelinePrompts

# Stage 1: Architecture design
RedTeamPipelinePrompts.ARCHITECT_AGENT

# Stage 2: Vulnerability selection
RedTeamPipelinePrompts.VULNERABILITY_SELECTION

# Stage 3: Code generation
RedTeamPipelinePrompts.CODE_GENERATION

# Stage 4: Stealth refinement
RedTeamPipelinePrompts.STEALTH_REFINEMENT
```

---

## AdversarialDebatePrompts

Prompts for debate-based verification.

```python
from src.prompts import AdversarialDebatePrompts

# Prosecutor argues finding is real
AdversarialDebatePrompts.PROSECUTOR_AGENT

# Defender argues finding is false positive
AdversarialDebatePrompts.DEFENDER_AGENT

# Judge renders verdict
AdversarialDebatePrompts.JUDGE_VERDICT
```
