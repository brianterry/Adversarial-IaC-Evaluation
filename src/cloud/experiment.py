"""
Cloud experiment management - start, monitor, and download results.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import yaml
from botocore.exceptions import ClientError

from .deploy import load_cloud_config

logger = logging.getLogger(__name__)


def start_experiment(
    config_path: str,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Start a cloud experiment using Step Functions.
    
    Args:
        config_path: Path to experiment configuration YAML
        region: AWS region (uses saved config if not specified)
        
    Returns:
        Experiment info including ID and execution ARN
    """
    # Load cloud config
    cloud_config = load_cloud_config()
    if not cloud_config:
        raise RuntimeError("Cloud infrastructure not deployed. Run 'adversarial-iac cloud deploy' first.")
    
    region = region or cloud_config.get('region', 'us-west-2')
    bucket = cloud_config.get('bucket')
    
    if not bucket:
        raise RuntimeError("S3 bucket not configured. Redeploy infrastructure.")
    
    # Load experiment config
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path) as f:
        experiment_config = yaml.safe_load(f)
    
    # Generate experiment ID
    experiment_id = f"exp-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Prepare experiment input
    experiment_input = prepare_experiment_input(experiment_id, bucket, experiment_config)
    
    # Upload config to S3
    s3 = boto3.client('s3', region_name=region)
    s3.put_object(
        Bucket=bucket,
        Key=f"{experiment_id}/config.json",
        Body=json.dumps(experiment_input, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    # Start Step Functions execution
    sfn = boto3.client('stepfunctions', region_name=region)
    
    # Get state machine ARN (assumes it's been deployed)
    state_machine_arn = get_state_machine_arn(sfn, 'adversarial-iac-experiment')
    
    if not state_machine_arn:
        raise RuntimeError("Step Functions state machine not found. Deploy Lambda stack first.")
    
    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=experiment_id,
        input=json.dumps(experiment_input)
    )
    
    execution_arn = response['executionArn']
    logger.info(f"Experiment started: {experiment_id}")
    logger.info(f"Execution ARN: {execution_arn}")
    
    # Save experiment info locally
    save_experiment_info(experiment_id, execution_arn, region, bucket, experiment_config)
    
    return {
        "experiment_id": experiment_id,
        "execution_arn": execution_arn,
        "bucket": bucket,
        "region": region,
        "status": "RUNNING",
    }


def get_experiment_status(experiment_id: str, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Get status of a running experiment.
    
    Args:
        experiment_id: Experiment ID
        region: AWS region
        
    Returns:
        Status information
    """
    # Load saved experiment info
    exp_info = load_experiment_info(experiment_id)
    if not exp_info:
        # Try to find in cloud config
        cloud_config = load_cloud_config()
        if not cloud_config:
            raise RuntimeError("No experiment info found and cloud not configured")
        region = region or cloud_config.get('region')
        bucket = cloud_config.get('bucket')
    else:
        region = region or exp_info.get('region')
        bucket = exp_info.get('bucket')
        execution_arn = exp_info.get('execution_arn')
    
    # Get Step Functions status
    sfn = boto3.client('stepfunctions', region_name=region)
    
    if exp_info and exp_info.get('execution_arn'):
        try:
            response = sfn.describe_execution(executionArn=exp_info['execution_arn'])
            sfn_status = response['status']
            
            status = {
                "experiment_id": experiment_id,
                "status": sfn_status,
                "started": response.get('startDate', '').isoformat() if response.get('startDate') else None,
                "stopped": response.get('stopDate', '').isoformat() if response.get('stopDate') else None,
                "region": region,
                "bucket": bucket,
            }
            
            # If completed, get summary from S3
            if sfn_status == 'SUCCEEDED':
                status['summary'] = get_experiment_summary(bucket, experiment_id, region)
            
            return status
            
        except ClientError as e:
            logger.warning(f"Could not get Step Functions status: {e}")
    
    # Fallback: check S3 for results
    s3 = boto3.client('s3', region_name=region)
    
    try:
        response = s3.head_object(Bucket=bucket, Key=f"{experiment_id}/results/summary.json")
        return {
            "experiment_id": experiment_id,
            "status": "COMPLETED",
            "region": region,
            "bucket": bucket,
            "summary": get_experiment_summary(bucket, experiment_id, region),
        }
    except ClientError:
        pass
    
    return {
        "experiment_id": experiment_id,
        "status": "UNKNOWN",
        "region": region,
        "bucket": bucket,
    }


def download_results(
    experiment_id: str,
    output_dir: str,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Download experiment results from S3.
    
    Args:
        experiment_id: Experiment ID
        output_dir: Local directory to save results
        region: AWS region
        
    Returns:
        Download status
    """
    # Load cloud config
    cloud_config = load_cloud_config()
    exp_info = load_experiment_info(experiment_id)
    
    region = region or (exp_info or {}).get('region') or (cloud_config or {}).get('region', 'us-west-2')
    bucket = (exp_info or {}).get('bucket') or (cloud_config or {}).get('bucket')
    
    if not bucket:
        raise RuntimeError("Cannot determine S3 bucket. Check cloud configuration.")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    s3 = boto3.client('s3', region_name=region)
    
    # List all objects for this experiment
    paginator = s3.get_paginator('list_objects_v2')
    downloaded = []
    
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{experiment_id}/"):
        for obj in page.get('Contents', []):
            key = obj['Key']
            
            # Create local path
            relative_path = key[len(experiment_id)+1:]  # Remove experiment_id prefix
            local_path = output_path / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            logger.info(f"Downloading: {key}")
            s3.download_file(bucket, key, str(local_path))
            downloaded.append(str(local_path))
    
    logger.info(f"Downloaded {len(downloaded)} files to {output_path}")
    
    return {
        "experiment_id": experiment_id,
        "output_dir": str(output_path),
        "files_downloaded": len(downloaded),
        "files": downloaded,
    }


def list_experiments(region: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all experiments in S3."""
    cloud_config = load_cloud_config()
    if not cloud_config:
        return []
    
    region = region or cloud_config.get('region', 'us-west-2')
    bucket = cloud_config.get('bucket')
    
    if not bucket:
        return []
    
    s3 = boto3.client('s3', region_name=region)
    
    experiments = []
    paginator = s3.get_paginator('list_objects_v2')
    
    # List top-level prefixes (experiment IDs)
    for page in paginator.paginate(Bucket=bucket, Delimiter='/'):
        for prefix in page.get('CommonPrefixes', []):
            exp_id = prefix['Prefix'].rstrip('/')
            if exp_id.startswith('exp-'):
                # Check if it has results
                try:
                    s3.head_object(Bucket=bucket, Key=f"{exp_id}/results/summary.json")
                    status = "COMPLETED"
                except ClientError:
                    status = "IN_PROGRESS"
                
                experiments.append({
                    "experiment_id": exp_id,
                    "status": status,
                    "bucket": bucket,
                })
    
    return experiments


def prepare_experiment_input(
    experiment_id: str,
    bucket: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Prepare the input for Step Functions execution."""
    
    # Separate batch and realtime configs
    batch_config = None
    realtime_config = None
    
    models = config.get('models', [])
    difficulties = config.get('difficulties', ['easy', 'medium', 'hard'])
    scenarios = config.get('scenarios', [])
    
    # Check for batch experiments (single-agent modes)
    batch_modes = config.get('batch_experiments', {})
    if batch_modes or any(m.get('red') == 'single' and m.get('blue') == 'single' 
                         for m in config.get('modes', [])):
        batch_config = {
            "models": models,
            "difficulties": difficulties,
            "scenarios": scenarios,
            "repetitions": config.get('settings', {}).get('repetitions', 1),
            "language": config.get('language', 'terraform'),
            "cloud_provider": config.get('cloud_provider', 'aws'),
        }
    
    # Check for realtime experiments (multi-agent modes)
    realtime_modes = config.get('realtime_experiments', {})
    multi_agent_modes = [m for m in config.get('modes', []) 
                        if m.get('red') != 'single' or m.get('blue') != 'single' or m.get('verify') == 'debate']
    
    if realtime_modes or multi_agent_modes:
        realtime_config = {
            "models": models,
            "difficulties": difficulties,
            "scenarios": scenarios,
            "modes": multi_agent_modes or [
                {"red": "single", "blue": "ensemble", "verify": "standard"},
                {"red": "pipeline", "blue": "single", "verify": "standard"},
                {"red": "single", "blue": "single", "verify": "debate"},
            ],
            "repetitions": config.get('settings', {}).get('repetitions', 1),
            "language": config.get('language', 'terraform'),
            "cloud_provider": config.get('cloud_provider', 'aws'),
        }
    
    return {
        "experiment_id": experiment_id,
        "bucket": bucket,
        "config": config,
        "batch_config": batch_config,
        "realtime_config": realtime_config,
        "has_batch": batch_config is not None,
        "has_realtime": realtime_config is not None,
    }


def get_state_machine_arn(sfn_client, name_prefix: str) -> Optional[str]:
    """Find state machine ARN by name prefix."""
    paginator = sfn_client.get_paginator('list_state_machines')
    
    for page in paginator.paginate():
        for sm in page.get('stateMachines', []):
            if sm['name'].startswith(name_prefix):
                return sm['stateMachineArn']
    
    return None


def get_experiment_summary(bucket: str, experiment_id: str, region: str) -> Optional[Dict]:
    """Load experiment summary from S3."""
    s3 = boto3.client('s3', region_name=region)
    
    try:
        response = s3.get_object(Bucket=bucket, Key=f"{experiment_id}/results/summary.json")
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError:
        return None


def save_experiment_info(
    experiment_id: str,
    execution_arn: str,
    region: str,
    bucket: str,
    config: Dict,
):
    """Save experiment info locally for tracking."""
    exp_dir = Path.home() / ".adversarial-iac" / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    info = {
        "experiment_id": experiment_id,
        "execution_arn": execution_arn,
        "region": region,
        "bucket": bucket,
        "started": datetime.utcnow().isoformat(),
        "config": config,
    }
    
    (exp_dir / f"{experiment_id}.json").write_text(json.dumps(info, indent=2))


def load_experiment_info(experiment_id: str) -> Optional[Dict]:
    """Load saved experiment info."""
    exp_path = Path.home() / ".adversarial-iac" / "experiments" / f"{experiment_id}.json"
    if exp_path.exists():
        return json.loads(exp_path.read_text())
    return None
