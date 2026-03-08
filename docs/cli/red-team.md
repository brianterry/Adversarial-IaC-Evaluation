# adversarial-iac red-team

Run the Red Team agent only. Generates infrastructure code with hidden vulnerabilities.

## Usage

```bash
adversarial-iac red-team --scenario "..." [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scenario`, `-s` | str | required | Scenario description |
| `--difficulty`, `-d` | choice | medium | easy, medium, hard |
| `--model`, `-m` | str | claude-3-5-haiku | Bedrock model ID |
| `--cloud-provider`, `-c` | choice | aws | aws, azure, gcp |
| `--language`, `-l` | choice | terraform | terraform, cloudformation |
| `--output-dir`, `-o` | path | output/red-team | Output directory |
| `--region` | str | us-east-1 | AWS region |

## Examples

### Basic

```bash
adversarial-iac red-team -s "Create an S3 bucket for logs" -d easy
```

### Hard difficulty

```bash
adversarial-iac red-team -s "Create VPC with subnets" -d hard -o output/my-red
```

### CloudFormation

```bash
adversarial-iac red-team -s "Create EC2 instance" -l cloudformation
```

## Output

Creates `output/red-team/` (or `--output-dir`) with:

- `main.tf` or CloudFormation template
- `red_team_manifest.json` — hidden vulnerabilities (ground truth)
- Supporting files (variables, etc.)

Use with `blue-team` and `judge` for a manual game flow.
