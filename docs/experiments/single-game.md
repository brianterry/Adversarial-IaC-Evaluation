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
  --blue-strategy precise \
  --red-vuln-source mixed \
  --precision-strategy precise \
  --use-trivy \
  --use-checkov \
  --use-cross-provider-judge
```

## v2.3 Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--precision-strategy` | precise | `standard` or `precise` (two-pass verification) |
| `--red-vuln-source` | mixed | `database`, `novel`, or `mixed` |
| `--use-cross-provider-judge` | enabled | Cross-provider consensus for novel vulns |
| `--blue-specialists N` | 4 | Number of Blue ensemble specialists |

## Output

Results are saved to `output/games/G-YYYYMMDD_HHMMSS/`:

- `code/main.tf` — Red Team's generated code
- `red_team_manifest.json` — Hidden vulnerabilities
- `scored_manifest.json` — Tool-confirmed entries used for scoring (v2.3)
- `phantom_manifest.json` — Unconfirmed entries excluded from scoring (v2.3)
- `blue_team_findings.json` — Blue Team's verified detections
- `game_result.json` — Scores (precision, recall, F1, evasion, phantom concordance rate)
- `game.log` — Execution log

## Replay Results

```bash
adversarial-iac replay output/games/G-YYYYMMDD_HHMMSS
```

See [CLI Reference](../cli/game.md) for all options.
