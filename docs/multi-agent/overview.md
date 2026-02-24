# Multi-Agent Modes

AdversarialIaC-Bench supports advanced multi-agent configurations for both attack and defense.

## Available Modes

| Mode | Team | Description |
|------|------|-------------|
| **Blue Team Ensemble** | Defense | Multiple specialists + consensus |
| **Red Team Pipeline** | Attack | Specialized attack chain |
| **Adversarial Debate** | Verification | Debate-based finding validation |

## Blue Team Ensemble

```
┌─────────────────────────────────────────────────────┐
│                  Blue Team Ensemble                  │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Security │  │Compliance│  │Architect │          │
│  │  Expert  │  │  Agent   │  │  Agent   │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │             │             │                 │
│       └─────────────┼─────────────┘                 │
│                     ▼                               │
│              ┌───────────┐                          │
│              │ Consensus │                          │
│              │   Agent   │                          │
│              └───────────┘                          │
└─────────────────────────────────────────────────────┘
```

## Red Team Pipeline

```
Architect → Vulnerability Selector → Code Generator → Stealth Reviewer
```

## Adversarial Debate

```
For each finding:
  Prosecutor: "This is a real vulnerability because..."
  Defender: "This is a false positive because..."
  Judge: Renders verdict (TP/FP)
```
