#!/usr/bin/env python3
"""
Deploy Qwen3.5-397B-FP8 (406GB) to SageMaker using the LMI vLLM DLC.

Uses DJL/LMI container (djl_python.vllm entrypoint) — NOT the HuggingFace
vLLM DLC. These are different deployment paths with different env vars.

Pre-requisites:
    1. Download FP8 weights (406GB):
       huggingface-cli download Qwen/Qwen3.5-397B-A17B-FP8 --local-dir ./qwen35-fp8
    2. Upload to S3:
       aws s3 sync ./qwen35-fp8 s3://your-bucket/qwen35-fp8/
    3. IAM role with sagemaker:* and s3:GetObject permissions

Usage:
    python scripts/deploy_to_sagemaker.py \
        --model-s3 s3://your-bucket/qwen35-fp8/ \
        --endpoint-name qwen35-397b-fp8 \
        --instance-type ml.p4de.24xlarge \
        --region us-east-1

Instance guide for 406GB FP8 model:
    ml.p4de.24xlarge — 8x A100 80GB = 640GB VRAM — ~$32/hr  ← recommended
    ml.p5.48xlarge   — 8x H100 80GB = 640GB VRAM — ~$98/hr  (faster inference)

IMPORTANT: Validate the DLC image URI and env vars against current docs before
deploying. The URI and options below may need updating.
Ref: https://docs.aws.amazon.com/sagemaker/latest/dg/large-model-inference-vllm.html
Available images: https://github.com/aws/deep-learning-containers/blob/master/available_images.md
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
import sagemaker
from sagemaker.model import Model


def get_lmi_dlc_uri(region: str) -> str:
    """
    Returns the LMI DLC URI. VALIDATE before deploying — update to latest.
    Uses DJL/LMI container, NOT the HuggingFace vLLM DLC.
    """
    return (
        f"763104351884.dkr.ecr.{region}.amazonaws.com/"
        "djl-inference:0.31.0-lmi13.0.0-cu124"  # VERIFY: update to current version
    )


def deploy(
    model_s3: str,
    endpoint_name: str,
    instance_type: str,
    region: str,
    role_arn: str = None,
):
    session = sagemaker.Session(boto3.Session(region_name=region))
    role = role_arn or sagemaker.get_execution_role(session)

    # LMI vLLM DLC environment variables.
    # VALIDATE all OPTION_* vars against current LMI docs before deploying.
    # Specifically confirm: OPTION_ENABLE_REASONING and OPTION_REASONING_PARSER
    env = {
        "HF_MODEL_ID": "/opt/ml/model",
        "OPTION_ENGINE": "Python",
        "OPTION_ENTRYPOINT": "djl_python.vllm",
        "OPTION_MODEL_LOADING_TIMEOUT": "1800",
        "OPTION_TENSOR_PARALLEL_DEGREE": "8",
        "OPTION_MAX_MODEL_LEN": "32768",  # IaC templates are short
        "OPTION_ENABLE_REASONING": "true",  # Qwen3.5 thinking mode — verify
        "OPTION_REASONING_PARSER": "qwen3",  # Parser for <think> blocks — verify
        "SERVING_FEATURES": "vllm",
    }

    model = Model(
        image_uri=get_lmi_dlc_uri(region),
        model_data=model_s3,
        env=env,
        role=role,
        sagemaker_session=session,
    )

    model.deploy(
        initial_instance_count=1,
        instance_type=instance_type,
        endpoint_name=endpoint_name,
        container_startup_health_check_timeout=1800,  # 30 min for 406GB
    )

    print(f"\nEndpoint deployed: {endpoint_name}")
    print(f"\nUse in BackendConfig:")
    print(
        f"""
BackendConfig(
    model_id="Qwen/Qwen3.5-397B-A17B-FP8",
    region="{region}",
    extra={{"endpoint_name": "{endpoint_name}"}},
    thinking_mode=True,
    thinking_budget_tokens=8000,
)
    """
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-s3", required=True)
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--instance-type", default="ml.p4de.24xlarge")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--role-arn", default=None)
    args = parser.parse_args()
    deploy(
        args.model_s3,
        args.endpoint_name,
        args.instance_type,
        args.region,
        args.role_arn,
    )
