# adversarial-iac blue-team

Run the Blue Team agent only. Analyzes code for vulnerabilities.

## Usage

```bash
adversarial-iac blue-team --input-dir <path> [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input-dir`, `-i` | path | required | Directory with Red Team output (code + manifest) |
| `--model`, `-m` | str | claude-3-5-haiku | Bedrock model ID |
| `--mode` | choice | llm_only | llm_only, tools_only, hybrid |
| `--use-trivy` | flag | false | Enable Trivy scanner |
| `--use-checkov` | flag | false | Enable Checkov scanner |
| `--language`, `-l` | choice | terraform | terraform, cloudformation |
| `--region` | str | us-east-1 | AWS region |

## Examples

### LLM only

```bash
adversarial-iac blue-team -i output/red-team
```

### With Trivy

```bash
adversarial-iac blue-team -i output/red-team --use-trivy
```

### Hybrid (LLM + Checkov)

```bash
adversarial-iac blue-team -i output/red-team --use-checkov --mode hybrid
```

## Output

Writes `blue_team_findings.json` to the input directory. Use `judge` to score against the manifest.
