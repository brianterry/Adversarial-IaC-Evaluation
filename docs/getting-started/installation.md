# Installation

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access
- Git

## Quick Install

```bash
# Clone with submodule (recommended)
git clone --recursive https://github.com/brianterry/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## If You Already Cloned (without --recursive)

```bash
# Initialize the vulnerability database submodule
git submodule update --init --recursive
```

## Verify Installation

```bash
python -c "from src.agents.red_team_agent import VulnerabilityDatabase; \
  db = VulnerabilityDatabase(); \
  print(f'✓ Loaded {len(db.get_sample_for_prompt(\"aws\", \"terraform\").get(\"sample_vulnerabilities\", []))} vulnerability rules')"
```

Expected output:
```
✓ Loaded 20 vulnerability rules
```

## What the Submodule Provides

The `vendor/vulnerable-iac-generator` submodule contains:

- **142 Trivy vulnerability rules** for AWS, Azure, and GCP
- **Real-world misconfiguration patterns** from security research
- **Multi-cloud support**: Terraform (AWS, Azure, GCP), CloudFormation, ARM templates

!!! warning "Required"
    The submodule is **required**. The system will fail with a clear error message if not initialized.

## Optional: Install Static Analysis Tools

For hybrid detection mode (LLM + static tools):

=== "macOS"
    ```bash
    # Install Trivy
    brew install trivy
    
    # Install Checkov
    pip install checkov
    ```

=== "Linux"
    ```bash
    # Install Trivy
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    
    # Install Checkov
    pip install checkov
    ```

=== "Windows"
    ```powershell
    # Install Trivy via Chocolatey
    choco install trivy
    
    # Install Checkov
    pip install checkov
    ```

## Environment Variables

Create a `.env` file in the project root:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
# Or use AWS_PROFILE for credential profiles
```

!!! tip "AWS Credentials"
    You can also configure credentials using `aws configure` or environment variables.

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first game
- [CLI Reference](../guide/cli.md) - All available commands
- [Configuration](../guide/configuration.md) - Customize experiments
