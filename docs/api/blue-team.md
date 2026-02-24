# Blue Team Agent API

The Blue Team agent analyzes Infrastructure-as-Code to detect security vulnerabilities.

## Quick Start

```python
import asyncio
from src.agents.blue_team_agent import create_blue_team_agent, DetectionMode

async def main():
    blue_team = create_blue_team_agent(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        region="us-east-1"
    )
    
    code = """
    resource "aws_s3_bucket" "data" {
      bucket = "my-data-bucket"
    }
    """
    
    findings = await blue_team.analyze(
        code=code,
        mode=DetectionMode.LLM_ONLY
    )
    
    for f in findings:
        print(f"[{f.severity}] {f.type}: {f.description}")

asyncio.run(main())
```

## Classes

### `DetectionMode`

Enumeration of detection modes.

```python
from src.agents.blue_team_agent import DetectionMode

DetectionMode.LLM_ONLY    # Pure LLM semantic analysis
DetectionMode.TOOLS_ONLY  # Trivy + Checkov only
DetectionMode.HYBRID      # LLM + static tools combined
```

### `BlueTeamAgent`

Main agent class for vulnerability detection.

#### Constructor

```python
blue_team = create_blue_team_agent(
    model_id: str,              # Bedrock model ID
    region: str = "us-east-1"   # AWS region
)
```

#### Methods

##### `analyze()`

Analyze code for security vulnerabilities.

```python
findings = await blue_team.analyze(
    code: str,                  # IaC code to analyze
    mode: DetectionMode = DetectionMode.LLM_ONLY,
    language: str = "terraform"  # Code language
) -> List[Finding]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | `str` | Infrastructure code to analyze |
| `mode` | `DetectionMode` | Detection strategy |
| `language` | `str` | `"terraform"` or `"cloudformation"` |

**Returns:** `List[Finding]`

##### `analyze_directory()`

Analyze all IaC files in a directory.

```python
findings = await blue_team.analyze_directory(
    input_dir: Path,            # Directory containing IaC files
    mode: DetectionMode = DetectionMode.LLM_ONLY
) -> List[Finding]
```

### `Finding`

Represents a detected vulnerability.

```python
@dataclass
class Finding:
    type: str           # Vulnerability category
    resource: str       # Affected resource
    severity: str       # HIGH, MEDIUM, LOW
    description: str    # What was found
    evidence: str       # Code snippet
    remediation: str    # How to fix
    source: str         # "llm", "trivy", or "checkov"
    confidence: float   # 0.0-1.0 confidence score
```

## Usage Examples

### LLM-Only Analysis

```python
findings = await blue_team.analyze(
    code=terraform_code,
    mode=DetectionMode.LLM_ONLY
)

for finding in findings:
    print(f"""
    Type: {finding.type}
    Resource: {finding.resource}
    Severity: {finding.severity}
    Description: {finding.description}
    Evidence: {finding.evidence}
    Fix: {finding.remediation}
    """)
```

### Hybrid Analysis

```python
# Combines LLM + Trivy + Checkov
findings = await blue_team.analyze(
    code=terraform_code,
    mode=DetectionMode.HYBRID
)

# Filter by source
llm_findings = [f for f in findings if f.source == "llm"]
tool_findings = [f for f in findings if f.source in ["trivy", "checkov"]]

print(f"LLM found: {len(llm_findings)}")
print(f"Tools found: {len(tool_findings)}")
```

### Analyze Directory

```python
from pathlib import Path

input_dir = Path("output/red-team/run_001")

findings = await blue_team.analyze_directory(
    input_dir=input_dir,
    mode=DetectionMode.LLM_ONLY
)

# Group by file
from collections import defaultdict
by_file = defaultdict(list)
for f in findings:
    by_file[f.file].append(f)

for file, file_findings in by_file.items():
    print(f"\n{file}: {len(file_findings)} issues")
```

### Save Findings

```python
import json
from pathlib import Path

output_dir = Path("output/blue-team/run_001")
output_dir.mkdir(parents=True, exist_ok=True)

findings_data = [
    {
        "type": f.type,
        "resource": f.resource,
        "severity": f.severity,
        "description": f.description,
        "evidence": f.evidence,
        "remediation": f.remediation,
        "source": f.source,
        "confidence": f.confidence
    }
    for f in findings
]

(output_dir / "findings.json").write_text(
    json.dumps(findings_data, indent=2)
)
```

## Detection Modes Comparison

### LLM_ONLY

**Pros:**
- Semantic understanding of code intent
- Catches contextual vulnerabilities
- Works on AI-generated code styles

**Cons:**
- May have false positives
- Slower than static tools
- Requires LLM API access

### TOOLS_ONLY

**Pros:**
- Fast execution
- Well-tested patterns
- No LLM costs

**Cons:**
- Pattern-based (misses semantic issues)
- May not work on AI-generated code
- Limited to known vulnerability signatures

### HYBRID

**Pros:**
- Combines semantic + pattern matching
- Higher recall

**Cons:**
- More false positives
- Requires deduplication
- Slower than either alone

## Static Tool Integration

### Trivy

```python
# Trivy is called automatically in TOOLS_ONLY and HYBRID modes
# Requires trivy CLI installed: brew install trivy
```

### Checkov

```python
# Checkov is called automatically in TOOLS_ONLY and HYBRID modes
# Requires checkov installed: pip install checkov
```

### Checking Tool Availability

```python
from src.agents.blue_team_agent import check_tools

available = check_tools()
print(f"Trivy available: {available['trivy']}")
print(f"Checkov available: {available['checkov']}")
```

## Error Handling

```python
from src.agents.blue_team_agent import BlueTeamError

try:
    findings = await blue_team.analyze(
        code=code,
        mode=DetectionMode.LLM_ONLY
    )
except BlueTeamError as e:
    print(f"Analysis failed: {e}")
```

## Configuration

Environment variables:

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region for Bedrock |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `TRIVY_PATH` | Custom path to trivy binary |
| `CHECKOV_PATH` | Custom path to checkov binary |

## Next Steps

- [Red Team API](red-team.md) - Attack generation
- [Judge API](judge.md) - Scoring system
