"""
Cloud infrastructure deployment using CloudFormation.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

STACK_NAME = "adversarial-iac"
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "cloudformation"


def deploy_infrastructure(
    region: str = "us-west-2",
    notification_email: Optional[str] = None,
    wait: bool = True,
) -> Dict[str, Any]:
    """
    Deploy the cloud infrastructure using CloudFormation.
    
    Args:
        region: AWS region to deploy to
        notification_email: Email for experiment notifications
        wait: Whether to wait for deployment to complete
        
    Returns:
        Dictionary with stack outputs
    """
    logger.info(f"Deploying infrastructure to {region}...")
    
    cf_client = boto3.client('cloudformation', region_name=region)
    
    # Load template
    template_path = TEMPLATE_DIR / "main-stack.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"CloudFormation template not found: {template_path}")
    
    template_body = template_path.read_text()
    
    # Prepare parameters
    parameters = [
        {'ParameterKey': 'EnvironmentName', 'ParameterValue': STACK_NAME},
    ]
    if notification_email:
        parameters.append({'ParameterKey': 'NotificationEmail', 'ParameterValue': notification_email})
    
    # Check if stack exists
    stack_exists = _stack_exists(cf_client, STACK_NAME)
    
    try:
        if stack_exists:
            logger.info(f"Updating existing stack: {STACK_NAME}")
            response = cf_client.update_stack(
                StackName=STACK_NAME,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_NAMED_IAM'],
            )
            waiter_name = 'stack_update_complete'
        else:
            logger.info(f"Creating new stack: {STACK_NAME}")
            response = cf_client.create_stack(
                StackName=STACK_NAME,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_NAMED_IAM'],
                OnFailure='DELETE',
            )
            waiter_name = 'stack_create_complete'
        
        stack_id = response.get('StackId', STACK_NAME)
        logger.info(f"Stack operation initiated: {stack_id}")
        
        if wait:
            logger.info("Waiting for deployment to complete...")
            waiter = cf_client.get_waiter(waiter_name)
            waiter.wait(StackName=STACK_NAME)
            logger.info("Deployment complete!")
        
        # Get outputs
        outputs = _get_stack_outputs(cf_client, STACK_NAME)
        
        # Save outputs to local config
        _save_cloud_config(region, outputs)
        
        return {
            "status": "success",
            "stack_name": STACK_NAME,
            "region": region,
            "outputs": outputs,
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'ValidationError' and 'No updates' in str(e):
            logger.info("No updates needed - stack is up to date")
            outputs = _get_stack_outputs(cf_client, STACK_NAME)
            return {
                "status": "no_changes",
                "stack_name": STACK_NAME,
                "region": region,
                "outputs": outputs,
            }
        raise


def destroy_infrastructure(region: str = "us-west-2", wait: bool = True) -> Dict[str, Any]:
    """
    Destroy the cloud infrastructure.
    
    Args:
        region: AWS region
        wait: Whether to wait for deletion to complete
        
    Returns:
        Status dictionary
    """
    logger.info(f"Destroying infrastructure in {region}...")
    
    cf_client = boto3.client('cloudformation', region_name=region)
    
    if not _stack_exists(cf_client, STACK_NAME):
        logger.info("Stack does not exist - nothing to destroy")
        return {"status": "not_found", "stack_name": STACK_NAME}
    
    # First, empty the S3 bucket (required before deletion)
    try:
        outputs = _get_stack_outputs(cf_client, STACK_NAME)
        bucket_name = outputs.get('ExperimentBucketName')
        if bucket_name:
            _empty_bucket(bucket_name, region)
    except Exception as e:
        logger.warning(f"Could not empty bucket: {e}")
    
    # Delete stack
    cf_client.delete_stack(StackName=STACK_NAME)
    logger.info("Stack deletion initiated")
    
    if wait:
        logger.info("Waiting for deletion to complete...")
        waiter = cf_client.get_waiter('stack_delete_complete')
        waiter.wait(StackName=STACK_NAME)
        logger.info("Stack deleted successfully")
    
    # Remove local config
    _remove_cloud_config()
    
    return {"status": "deleted", "stack_name": STACK_NAME}


def get_infrastructure_status(region: str = "us-west-2") -> Dict[str, Any]:
    """Get current infrastructure status."""
    cf_client = boto3.client('cloudformation', region_name=region)
    
    if not _stack_exists(cf_client, STACK_NAME):
        return {"status": "not_deployed", "stack_name": STACK_NAME}
    
    response = cf_client.describe_stacks(StackName=STACK_NAME)
    stack = response['Stacks'][0]
    
    return {
        "status": stack['StackStatus'],
        "stack_name": STACK_NAME,
        "region": region,
        "created": stack.get('CreationTime', '').isoformat() if stack.get('CreationTime') else None,
        "updated": stack.get('LastUpdatedTime', '').isoformat() if stack.get('LastUpdatedTime') else None,
        "outputs": _get_stack_outputs(cf_client, STACK_NAME),
    }


def _stack_exists(cf_client, stack_name: str) -> bool:
    """Check if a CloudFormation stack exists."""
    try:
        response = cf_client.describe_stacks(StackName=stack_name)
        stacks = response.get('Stacks', [])
        return len(stacks) > 0 and stacks[0]['StackStatus'] != 'DELETE_COMPLETE'
    except ClientError as e:
        if 'does not exist' in str(e):
            return False
        raise


def _get_stack_outputs(cf_client, stack_name: str) -> Dict[str, str]:
    """Get outputs from a CloudFormation stack."""
    response = cf_client.describe_stacks(StackName=stack_name)
    stacks = response.get('Stacks', [])
    
    if not stacks:
        return {}
    
    outputs = {}
    for output in stacks[0].get('Outputs', []):
        outputs[output['OutputKey']] = output['OutputValue']
    
    return outputs


def _empty_bucket(bucket_name: str, region: str):
    """Empty an S3 bucket before deletion."""
    s3 = boto3.resource('s3', region_name=region)
    bucket = s3.Bucket(bucket_name)
    
    logger.info(f"Emptying bucket: {bucket_name}")
    bucket.objects.all().delete()
    bucket.object_versions.all().delete()


def _save_cloud_config(region: str, outputs: Dict[str, str]):
    """Save cloud configuration to local file."""
    config_path = Path.home() / ".adversarial-iac" / "cloud-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        "region": region,
        "stack_name": STACK_NAME,
        "bucket": outputs.get('ExperimentBucketName'),
        "notification_topic": outputs.get('NotificationTopicArn'),
        "lambda_role": outputs.get('LambdaRoleArn'),
        "stepfunctions_role": outputs.get('StepFunctionsRoleArn'),
        "bedrock_batch_role": outputs.get('BedrockBatchRoleArn'),
    }
    
    config_path.write_text(json.dumps(config, indent=2))
    logger.info(f"Cloud config saved to {config_path}")


def _remove_cloud_config():
    """Remove local cloud configuration."""
    config_path = Path.home() / ".adversarial-iac" / "cloud-config.json"
    if config_path.exists():
        config_path.unlink()
        logger.info("Cloud config removed")


def load_cloud_config() -> Optional[Dict[str, str]]:
    """Load cloud configuration from local file."""
    config_path = Path.home() / ".adversarial-iac" / "cloud-config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return None
