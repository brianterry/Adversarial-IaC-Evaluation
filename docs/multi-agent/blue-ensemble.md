# Blue Team Ensemble

Multiple specialist agents analyze code, then reach consensus.

## Specialists

| Specialist | Focus |
|------------|-------|
| **Security Expert** | General security vulnerabilities |
| **Compliance Agent** | Regulatory compliance (HIPAA, PCI-DSS) |
| **Architecture Agent** | Cloud best practices |

## Consensus Methods

- **Vote**: Majority agreement required
- **Debate**: LLM-based discussion
- **Union**: All unique findings
- **Intersection**: Only unanimous findings

## Usage

```bash
adversarial-iac game \
    --blue-team-mode ensemble \
    --consensus-method vote
```
