#!/usr/bin/env python3
"""
AWS CDK App for Adversarial IaC Evaluation Infrastructure

Usage:
    cd infrastructure/cdk
    pip install -r requirements.txt
    cdk bootstrap  # first time only
    cdk deploy
"""

import os
import aws_cdk as cdk

from stacks.experiment_stack import ExperimentStack

# Environment configuration
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-west-2"),
)

app = cdk.App()

# Get configuration from context
environment_name = app.node.try_get_context("environment_name") or "adversarial-iac"
notification_email = app.node.try_get_context("notification_email")

# Deploy all infrastructure in a single stack
ExperimentStack(
    app, 
    f"{environment_name}",
    environment_name=environment_name,
    notification_email=notification_email,
    env=env,
    description="Adversarial IaC Evaluation - Complete Infrastructure",
)

app.synth()
