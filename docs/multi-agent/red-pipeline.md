# Red Team Pipeline

Specialized agents work in sequence to create stealthy vulnerabilities.

## Pipeline Stages

1. **Architect Agent**: Designs infrastructure
2. **Vulnerability Selector**: Chooses what to inject
3. **Code Generator**: Creates IaC with vulnerabilities
4. **Stealth Reviewer**: Refines for evasion

## Usage

```bash
adversarial-iac game \
    --red-team-mode pipeline
```
