# adversarial-iac game

Run a complete Red Team vs Blue Team game.

## Usage

```bash
adversarial-iac game --scenario "..." [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scenario`, `-s` | str | required | Scenario description |
| `--red-model` | str | claude-3-5-haiku | Red Team model (short name or full ID) |
| `--blue-model` | str | claude-3-5-haiku | Blue Team model |
| `--difficulty`, `-d` | choice | medium | easy, medium, hard |
| `--language`, `-l` | choice | terraform | terraform, cloudformation |
| `--cloud-provider`, `-c` | choice | aws | aws, azure, gcp |
| `--red-team-mode` | choice | single | single, pipeline |
| `--blue-team-mode` | choice | single | single, ensemble |
| `--consensus-method` | choice | debate | debate, vote, union, intersection |
| `--verification-mode` | choice | standard | standard, debate |
| `--no-llm-judge` | flag | false | Disable LLM for ambiguous matches |
| `--use-consensus-judge` | flag | false | Multi-model consensus judging |
| `--consensus-models` | str | - | Comma-separated model IDs |
| `--red-strategy` | choice | balanced | balanced, targeted, stealth, blitz, chained |
| `--red-target-type` | choice | - | encryption, iam, network, logging, access_control |
| `--red-vuln-source` | choice | database | database, novel, mixed |
| `--blue-team-profile` | choice | - | llm_only, tool_augmented, ensemble |
| `--blue-strategy` | choice | comprehensive | comprehensive, targeted, iterative, threat_model, compliance |
| `--blue-target-type` | choice | - | encryption, iam, network, logging, access_control |
| `--compliance-framework` | choice | - | hipaa, pci_dss, soc2, cis |
| `--blue-iterations` | int | 1 | Passes for iterative strategy |
| `--use-trivy` | flag | false | Enable Trivy scanner |
| `--use-checkov` | flag | false | Enable Checkov scanner |
| `--blue-backend-type` | choice | bedrock | bedrock, direct_api, sagemaker |
| `--blue-thinking-mode` | flag | false | Enable reasoning mode for Blue |
| `--blue-backend-extra` | JSON | - | Backend extras (base_url, api_key_env, etc.) |
| `--red-backend-type` | choice | bedrock | bedrock, direct_api, sagemaker |
| `--red-thinking-mode` | flag | false | Enable reasoning mode for Red |
| `--red-backend-extra` | JSON | - | Red Team backend extras |
| `--region` | str | us-east-1 | AWS region |

## Examples

### Basic (Bedrock)

```bash
adversarial-iac game -s "Create an S3 bucket for healthcare PHI data" -d medium
```

### Direct API (DashScope)

```bash
adversarial-iac game -s "Create S3 bucket" \
  --blue-backend-type direct_api \
  --blue-model qwen3.5-plus \
  --blue-backend-extra '{"base_url":"https://dashscope.aliyuncs.com/compatible-mode/v1","api_key_env":"DASHSCOPE_API_KEY"}'
```

### With thinking mode

```bash
adversarial-iac game -s "Create S3 bucket" --blue-thinking-mode
```

### Red pipeline, Blue ensemble

```bash
adversarial-iac game -s "Create VPC with subnets" \
  --red-team-mode pipeline \
  --blue-team-mode ensemble \
  --consensus-method vote
```

### Static analysis tools

```bash
adversarial-iac game -s "Create S3 bucket" --use-trivy --use-checkov
```
