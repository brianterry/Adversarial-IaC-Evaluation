# adversarial-iac play

Interactive mode with guided game setup and explanations.

## Usage

```bash
adversarial-iac play
```

No options. The wizard prompts you for everything.

## When to Use

| Use play when... | Use game when... |
|------------------|------------------|
| Learning the framework | Scripting or automation |
| Exploring scenarios | CI/CD integration |
| Want step-by-step guidance | Need specific flags |
| First time running | Batch experiments |

## What the Wizard Does

1. **Scenario** — Random, by category, or custom description
2. **Difficulty** — Easy, medium, or hard
3. **Language** — Terraform or CloudFormation
4. **Models** — Red and Blue Team model selection by tier
5. **Advanced** (optional) — Strategies, modes, static tools, backend config
6. **Run** — Executes the game and explains results

## Example Flow

```
? How would you like to choose a scenario?
  Random - Let me pick something interesting
  Infrastructure - Core AWS components
  Industry - Healthcare, Financial, Government...
  Custom - Describe your own scenario

? Select difficulty level:
  Easy - Obvious vulnerabilities
  Medium - Subtle issues (recommended)
  Hard - Hidden, chained vulnerabilities

? Choose Red Team model (attacker):
  claude-3.5-sonnet (Recommended)
  claude-3.5-haiku (Fast)
  nova-lite (Cheap)
  ...
```
