# Agents API

## RedTeamAgent

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

### RedTeamOutput

| Field | Type | Description |
|-------|------|-------------|
| `code` | Dict[str, str] | Generated IaC files |
| `manifest` | List[InjectedVulnerability] | Injected vulnerabilities |
| `stealth_score` | float | Evasion likelihood (0-1) |

### InjectedVulnerability

| Field | Type | Description |
|-------|------|-------------|
| `vuln_id` | str | Unique vulnerability ID |
| `type` | str | Vulnerability type |
| `resource` | str | Affected resource |
| `description` | str | What's wrong |
| `severity` | str | high, medium, low |

---

## BlueTeamAgent

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

### BlueTeamOutput

| Field | Type | Description |
|-------|------|-------------|
| `findings` | List[Finding] | Detected issues |

### Finding

| Field | Type | Description |
|-------|------|-------------|
| `finding_id` | str | Unique finding ID |
| `resource_name` | str | Affected resource |
| `vulnerability_type` | str | Type of issue |
| `severity` | str | high, medium, low |
| `title` | str | Short description |
| `description` | str | Detailed explanation |
| `evidence` | str | Code evidence |
| `remediation` | str | How to fix |
| `confidence` | float | Detection confidence (0-1) |

---

## JudgeAgent

Matches findings to vulnerabilities and calculates metrics.

```python
from src.agents.judge_agent import JudgeAgent

judge = JudgeAgent()
scoring = judge.score(red_manifest, blue_findings)
```

### ScoringResult

| Field | Type | Description |
|-------|------|-------------|
| `precision` | float | TP / (TP + FP) |
| `recall` | float | TP / (TP + FN) |
| `f1_score` | float | Harmonic mean |
| `evasion_rate` | float | 1 - recall |
| `matches` | List[Match] | Matched pairs |
| `unmatched_vulns` | List | Evaded vulnerabilities |
| `unmatched_findings` | List | False positives |
