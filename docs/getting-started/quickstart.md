# Quick Start

Run your first game in under 5 minutes.

## Install

```bash
git clone https://github.com/brianterry/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation
pip install -e .
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

**Requirements:** Python 3.10+, AWS credentials (for Bedrock). Enable model access in [Amazon Bedrock](https://console.aws.amazon.com/bedrock) → Model access.

## First Game

```bash
adversarial-iac play
```

The interactive wizard guides you through scenario selection, model choice, and explains results in plain English.

## Command Line Alternative

For scripting or direct control:

```bash
adversarial-iac game \
  -s "Create an S3 bucket for healthcare PHI data" \
  -d medium
```

See [CLI Reference](../cli/game.md) for all options and examples.
