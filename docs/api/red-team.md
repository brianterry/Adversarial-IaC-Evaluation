# Red Team Agent API

The Red Team agent generates adversarial Infrastructure-as-Code with hidden vulnerabilities.

## Quick Start

```python
import asyncio
from src.agents.red_team_agent import create_red_team_agent, Difficulty

async def main():
    red_team = create_red_team_agent(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        region="us-east-1"
    )
    
    result = await red_team.generate(
        scenario="Create S3 bucket for healthcare PHI data",
        difficulty=Difficulty.MEDIUM,
        language="terraform",
        provider="aws"
    )
    
    print(f"Generated {len(result.files)} files")
    print(f"Injected {len(result.vulnerabilities)} vulnerabilities")

asyncio.run(main())
```

## Classes

### `Difficulty`

Enumeration of difficulty levels.

```python
from src.agents.red_team_agent import Difficulty

Difficulty.EASY    # 2-3 basic vulnerabilities
Difficulty.MEDIUM  # 3-4 with stealth techniques
Difficulty.HARD    # 4-5 with advanced evasion
```

### `RedTeamAgent`

Main agent class for generating adversarial IaC.

#### Constructor

```python
red_team = create_red_team_agent(
    model_id: str,        # Bedrock model ID
    region: str = "us-east-1"  # AWS region
)
```

#### Methods

##### `generate()`

Generate adversarial IaC with vulnerabilities.

```python
result = await red_team.generate(
    scenario: str,           # What to build
    difficulty: Difficulty,  # Vulnerability difficulty
    language: str = "terraform",    # IaC language
    provider: str = "aws"    # Cloud provider
) -> RedTeamResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `scenario` | `str` | Infrastructure description |
| `difficulty` | `Difficulty` | `EASY`, `MEDIUM`, or `HARD` |
| `language` | `str` | `"terraform"` or `"cloudformation"` |
| `provider` | `str` | `"aws"`, `"azure"`, or `"gcp"` |

**Returns:** `RedTeamResult`

### `RedTeamResult`

Container for generated code and vulnerabilities.

```python
@dataclass
class RedTeamResult:
    files: Dict[str, str]          # filename -> content
    vulnerabilities: List[Vulnerability]  # Injected vulns
    metadata: Dict[str, Any]       # Generation metadata
```

### `Vulnerability`

Represents an injected vulnerability.

```python
@dataclass
class Vulnerability:
    id: str              # Unique identifier
    type: str            # Category (encryption, access_control, etc.)
    resource: str        # Affected resource name
    severity: str        # HIGH, MEDIUM, LOW
    description: str     # What the vulnerability is
    technique: str       # How it was hidden
    evidence: str        # Code snippet showing the issue
```

## Usage Examples

### Basic Generation

```python
result = await red_team.generate(
    scenario="Create Lambda function for payment processing",
    difficulty=Difficulty.MEDIUM
)

# Access generated files
for filename, content in result.files.items():
    print(f"--- {filename} ---")
    print(content)
```

### Save to Directory

```python
from pathlib import Path

output_dir = Path("output/red-team/run_001")
output_dir.mkdir(parents=True, exist_ok=True)

# Save code files
for filename, content in result.files.items():
    (output_dir / filename).write_text(content)

# Save vulnerability manifest
import json
manifest = {
    "vulnerabilities": [
        {
            "id": v.id,
            "type": v.type,
            "resource": v.resource,
            "severity": v.severity,
            "description": v.description,
            "technique": v.technique
        }
        for v in result.vulnerabilities
    ]
}
(output_dir / "vulnerability_manifest.json").write_text(
    json.dumps(manifest, indent=2)
)
```

### Different Difficulty Levels

```python
# Easy: Basic misconfigurations
easy_result = await red_team.generate(
    scenario="Create S3 bucket",
    difficulty=Difficulty.EASY
)

# Medium: Subtle omissions, misleading comments
medium_result = await red_team.generate(
    scenario="Create S3 bucket",
    difficulty=Difficulty.MEDIUM
)

# Hard: Advanced evasion, chained vulnerabilities
hard_result = await red_team.generate(
    scenario="Create S3 bucket",
    difficulty=Difficulty.HARD
)
```

### Using Vulnerability Database

The Red Team uses a curated vulnerability database:

```python
from src.agents.red_team_agent import VulnerabilityDatabase

db = VulnerabilityDatabase()
sample = db.get_sample_for_prompt("aws", "terraform")

print(f"Loaded {len(sample['sample_vulnerabilities'])} vulnerability patterns")
```

## Stealth Techniques by Difficulty

### Easy
- Missing encryption configuration
- Overly permissive IAM policies
- Public access enabled

### Medium
- Misleading comments suggesting security
- Valid-looking but insecure defaults
- Subtle omissions (missing but not obviously wrong)

### Hard
- Chained vulnerabilities (A + B = exploit)
- Misdirection through compliance tags
- Security-looking code that's actually insecure
- Complex resource relationships hiding issues

## Error Handling

```python
from src.agents.red_team_agent import RedTeamError

try:
    result = await red_team.generate(
        scenario="Create infrastructure",
        difficulty=Difficulty.HARD
    )
except RedTeamError as e:
    print(f"Generation failed: {e}")
```

## Configuration

Environment variables:

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region for Bedrock |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |

## Next Steps

- [Blue Team API](blue-team.md) - Detection agent
- [Judge API](judge.md) - Scoring system
