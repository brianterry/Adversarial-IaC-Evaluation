# Installation

## Requirements

- Python 3.10+
- AWS credentials (for Bedrock models)
- Git

## Quick Install

```bash
# Clone the repository
git clone https://github.com/brianterry/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Verify Installation

```bash
adversarial-iac --help
```

You should see:

```
Usage: adversarial-iac [OPTIONS] COMMAND [ARGS]...

  Adversarial IaC Evaluation Framework

Options:
  --help  Show this message and exit.

Commands:
  game        Run a single adversarial game
  red-team    Run Red Team agent only
  blue-team   Run Blue Team agent only
  judge       Score a game
```

## AWS Configuration

The framework uses AWS Bedrock for LLM inference. Configure your credentials:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
```

### Enable Bedrock Models

In the AWS Console:

1. Go to **Amazon Bedrock** → **Model access**
2. Enable the models you want to use:
    - Anthropic Claude (Sonnet, Haiku)
    - Amazon Nova
    - Meta Llama
    - Mistral

## Optional: Static Analysis Tools

For enhanced Blue Team capabilities, install:

=== "Trivy"

    ```bash
    # macOS
    brew install trivy
    
    # Linux
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    ```

=== "Checkov"

    ```bash
    pip install checkov
    ```

## Development Install

For contributing to the framework:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
```

## Docker (Coming Soon)

```bash
docker pull brianterry/adversarial-iac-bench
docker run -it adversarial-iac-bench game --help
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first game
- [Configuration](configuration.md) - Customize settings
