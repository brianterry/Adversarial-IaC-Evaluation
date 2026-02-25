"""
Lambda: Generate Red Team Prompts for Batch Inference

This Lambda generates all Red Team prompts for the experiment
and uploads them to S3 in JSONL format for Bedrock Batch.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

# Import prompts (packaged with Lambda)
from prompts import AdversarialPrompts


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Generate Red Team prompts for batch inference.
    
    Input event:
    {
        "experiment_id": "exp-001",
        "bucket": "adversarial-iac-experiments-123456",
        "config": {
            "models": ["anthropic.claude-3-5-sonnet-20241022-v2:0", ...],
            "difficulties": ["easy", "medium", "hard"],
            "scenarios": ["Create an S3 bucket...", ...],
            "repetitions": 3
        }
    }
    
    Output:
    {
        "experiment_id": "exp-001",
        "bucket": "...",
        "prompts_key": "exp-001/batch-workflow/stage1-red/input/prompts.jsonl",
        "total_prompts": 450,
        "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0"
    }
    """
    logger.info(f"Generating Red Team prompts: {json.dumps(event)}")
    
    experiment_id = event['experiment_id']
    bucket = event['bucket']
    config = event['config']
    model_id = event.get('model_id', config['models'][0])
    
    # Generate all game configurations
    games = generate_game_configs(config, model_id)
    logger.info(f"Generated {len(games)} game configurations")
    
    # Generate prompts for each game
    prompts = []
    for game in games:
        prompt = generate_red_team_prompt(game)
        prompts.append({
            "recordId": game['game_id'],
            "modelInput": {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        })
    
    # Upload prompts to S3 as JSONL
    prompts_key = f"{experiment_id}/batch-workflow/stage1-red/input/prompts.jsonl"
    jsonl_content = "\n".join(json.dumps(p) for p in prompts)
    
    s3.put_object(
        Bucket=bucket,
        Key=prompts_key,
        Body=jsonl_content.encode('utf-8'),
        ContentType='application/jsonl'
    )
    logger.info(f"Uploaded {len(prompts)} prompts to s3://{bucket}/{prompts_key}")
    
    # Save game configs for later stages
    configs_key = f"{experiment_id}/batch-workflow/game_configs.json"
    s3.put_object(
        Bucket=bucket,
        Key=configs_key,
        Body=json.dumps(games, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    # Publish metrics
    publish_metrics(experiment_id, len(prompts), 'RedTeamPromptsGenerated')
    
    return {
        "experiment_id": experiment_id,
        "bucket": bucket,
        "prompts_key": prompts_key,
        "configs_key": configs_key,
        "total_prompts": len(prompts),
        "model_id": model_id
    }


def generate_game_configs(config: Dict, model_id: str) -> List[Dict]:
    """Generate all game configurations from experiment config."""
    games = []
    game_num = 1
    
    difficulties = config.get('difficulties', ['easy', 'medium', 'hard'])
    scenarios = config.get('scenarios', [])
    repetitions = config.get('repetitions', 1)
    language = config.get('language', 'terraform')
    cloud_provider = config.get('cloud_provider', 'aws')
    
    for difficulty in difficulties:
        for scenario in scenarios:
            for rep in range(repetitions):
                game_id = f"G-B{game_num:04d}"
                games.append({
                    "game_id": game_id,
                    "scenario": scenario,
                    "difficulty": difficulty,
                    "red_model": model_id,
                    "language": language,
                    "cloud_provider": cloud_provider,
                    "repetition": rep + 1
                })
                game_num += 1
    
    return games


def generate_red_team_prompt(game: Dict) -> str:
    """Generate the Red Team prompt for a single game."""
    
    # Load vulnerability samples (simplified for Lambda)
    vuln_samples = get_vulnerability_samples(game['cloud_provider'], game['language'])
    
    prompt = AdversarialPrompts.RED_TEAM_ADVERSARIAL.format(
        scenario_description=game['scenario'],
        cloud_provider=game['cloud_provider'],
        language=game['language'],
        difficulty=game['difficulty'],
        vulnerability_samples=json.dumps(vuln_samples, indent=2),
        vuln_count=3 if game['difficulty'] == 'easy' else (4 if game['difficulty'] == 'medium' else 5)
    )
    
    return prompt


def get_vulnerability_samples(cloud_provider: str, language: str) -> List[Dict]:
    """Get sample vulnerabilities for the prompt."""
    # Simplified samples - in production, load from S3 or package with Lambda
    return [
        {"id": "AVD-AWS-0086", "title": "S3 bucket without encryption", "severity": "HIGH", "type": "encryption"},
        {"id": "AVD-AWS-0088", "title": "S3 bucket with public access", "severity": "CRITICAL", "type": "access_control"},
        {"id": "AVD-AWS-0057", "title": "IAM policy allows wildcard actions", "severity": "HIGH", "type": "iam"},
        {"id": "AVD-AWS-0089", "title": "S3 bucket without versioning", "severity": "MEDIUM", "type": "data_protection"},
        {"id": "AVD-AWS-0028", "title": "CloudTrail not enabled", "severity": "HIGH", "type": "logging"},
        {"id": "AVD-AWS-0107", "title": "Security group allows unrestricted ingress", "severity": "CRITICAL", "type": "network"},
        {"id": "AVD-AWS-0017", "title": "RDS instance without encryption", "severity": "HIGH", "type": "encryption"},
        {"id": "AVD-AWS-0104", "title": "EBS volume not encrypted", "severity": "MEDIUM", "type": "encryption"},
    ]


def publish_metrics(experiment_id: str, count: int, metric_name: str):
    """Publish metrics to CloudWatch."""
    try:
        cloudwatch.put_metric_data(
            Namespace='AdversarialIaC/Experiments',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': count,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'ExperimentId', 'Value': experiment_id}
                    ]
                }
            ]
        )
    except Exception as e:
        logger.warning(f"Failed to publish metrics: {e}")
