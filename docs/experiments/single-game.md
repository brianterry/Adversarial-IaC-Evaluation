# Single Game

Run one adversarial game from the command line.

## Basic

```bash
adversarial-iac game -s "Create an S3 bucket for healthcare PHI data" -d medium
```

## Full Example

```bash
adversarial-iac game \
  -s "Create an S3 bucket for healthcare PHI data with HIPAA compliance" \
  --red-model claude-3.5-sonnet \
  --blue-model nova-pro \
  -d hard \
  -l terraform \
  --red-strategy stealth \
  --blue-strategy comprehensive \
  --use-trivy
```

## Output

Results are saved to `output/games/G-YYYYMMDD_HHMMSS/`:

- `code/main.tf` — Red Team's generated code
- `red_team_manifest.json` — Hidden vulnerabilities
- `blue_team_findings.json` — Blue Team's detections
- `game_result.json` — Scores (precision, recall, F1, evasion)
- `game.log` — Execution log

## Replay Results

```bash
adversarial-iac replay output/games/G-YYYYMMDD_HHMMSS
```

See [CLI Reference](../cli/game.md) for all options.
