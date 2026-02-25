# Cloud Infrastructure (AWS CDK)

This directory contains AWS CDK infrastructure for running large-scale Adversarial IaC experiments.

## Quick Start

```bash
# Install CDK dependencies
cd infrastructure/cdk
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy
cdk deploy

# Deploy with email notifications
cdk deploy -c notification_email=your@email.com
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Step Functions                           │
│                    (Experiment Orchestration)                    │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │  Run Game   │──▶│  Run Game   │──▶│  Run Game   │──▶ ...     │
│  │  (Lambda)   │   │  (Lambda)   │   │  (Lambda)   │            │
│  └─────────────┘   └─────────────┘   └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          S3 Bucket                              │
│              (Experiment configs, results, logs)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CloudWatch Dashboard                         │
│        (Precision, Recall, Evasion Rate, Game Count)           │
└─────────────────────────────────────────────────────────────────┘
```

## Resources Created

| Resource | Name | Description |
|----------|------|-------------|
| **S3 Bucket** | `adversarial-iac-experiments-{account}` | Stores experiment data |
| **Step Functions** | `adversarial-iac-experiment` | Orchestrates game execution |
| **Lambda** | `adversarial-iac-run-game` | Runs individual games |
| **Lambda** | `adversarial-iac-generate-red-prompts` | Batch prompt generation |
| **Lambda** | `adversarial-iac-process-red-outputs` | Process batch outputs |
| **Lambda** | `adversarial-iac-run-judge` | Score games |
| **CloudWatch Dashboard** | `adversarial-iac-experiments` | Monitoring |
| **SNS Topic** | `adversarial-iac-notifications` | Experiment notifications |

## Directory Structure

```
infrastructure/
├── cdk/
│   ├── app.py                 # CDK app entry point
│   ├── cdk.json               # CDK configuration
│   ├── requirements.txt       # Python dependencies
│   └── stacks/
│       ├── __init__.py
│       └── experiment_stack.py  # All infrastructure in one stack
├── lambda/
│   ├── batch/                 # Lambda code for batch operations
│   │   ├── generate_red_prompts.py
│   │   ├── process_red_outputs.py
│   │   └── run_judge.py
│   └── realtime/              # Lambda code for realtime games
│       └── run_game.py
└── README.md
```

## Commands

```bash
# Deploy infrastructure
cdk deploy

# View what will be deployed (diff)
cdk diff

# Synthesize CloudFormation template
cdk synth

# Destroy infrastructure
cdk destroy

# List all stacks
cdk list
```

## Configuration

You can customize the deployment using CDK context:

```bash
# Custom environment name
cdk deploy -c environment_name=my-experiment

# Add notification email
cdk deploy -c notification_email=researcher@university.edu
```

## Costs

Estimated costs for running experiments:

| Service | Estimate | Notes |
|---------|----------|-------|
| Lambda | ~$0.01 per game | 15min max execution |
| S3 | ~$0.02/GB/month | Results storage |
| Step Functions | ~$0.025 per 1000 executions | Orchestration |
| CloudWatch | ~$0.30/dashboard/month | Monitoring |
| **Bedrock** | Variable | Depends on model and tokens |

## Troubleshooting

### Bootstrap Required
```
Has the environment been bootstrapped?
```
Run: `cdk bootstrap`

### Stack Already Exists
```
Resource already exists
```
Delete the old stack first: `aws cloudformation delete-stack --stack-name adversarial-iac`

### IAM Permission Issues
Ensure your AWS credentials have permissions for:
- CloudFormation
- IAM (create roles)
- Lambda
- Step Functions
- S3
- CloudWatch
- SNS
- Bedrock
