"""
Lambda: Run Single Game (Real-Time)

This Lambda runs a single game using the GameEngine.
Used for multi-agent modes (ensemble, pipeline, debate) that
require chained API calls.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

import boto3

# Add src to path for imports
sys.path.insert(0, '/opt/python')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Run a single game with full multi-agent support.
    
    Input event:
    {
        "experiment_id": "exp-001",
        "bucket": "adversarial-iac-experiments-123456",
        "game_config": {
            "game_id": "G-R001",
            "scenario": "Create an S3 bucket...",
            "red_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "blue_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "difficulty": "medium",
            "red_team_mode": "pipeline",
            "blue_team_mode": "ensemble",
            "consensus_method": "debate",
            "verification_mode": "debate",
            "language": "terraform",
            "cloud_provider": "aws"
        }
    }
    
    Output:
    {
        "game_id": "G-R001",
        "status": "completed",
        "scoring": {...},
        "duration_seconds": 65.2
    }
    """
    logger.info(f"Running game: {json.dumps(event)}")
    
    experiment_id = event['experiment_id']
    bucket = event['bucket']
    game_config = event['game_config']
    game_id = game_config['game_id']
    
    start_time = datetime.utcnow()
    
    try:
        # Import game engine (from Lambda layer)
        from src.game.engine import GameEngine, GameConfig
        from src.game.scenario import Scenario
        
        # Create game config
        config = GameConfig(
            red_model=game_config['red_model'],
            blue_model=game_config['blue_model'],
            difficulty=game_config.get('difficulty', 'medium'),
            language=game_config.get('language', 'terraform'),
            cloud_provider=game_config.get('cloud_provider', 'aws'),
            red_team_mode=game_config.get('red_team_mode', 'single'),
            blue_team_mode=game_config.get('blue_team_mode', 'single'),
            consensus_method=game_config.get('consensus_method', 'vote'),
            verification_mode=game_config.get('verification_mode', 'standard'),
            region=os.environ.get('AWS_REGION', 'us-west-2'),
        )
        
        # Create scenario
        scenario = Scenario(
            description=game_config['scenario'],
            domain='general',
            cloud_provider=config.cloud_provider,
        )
        
        # Run game (async)
        import asyncio
        engine = GameEngine()
        
        # Use asyncio.run for Lambda
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(engine.run_game(scenario, config))
        finally:
            loop.close()
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Save result to S3
        save_game_result(bucket, experiment_id, game_id, result, game_config)
        
        # Publish metrics
        publish_game_metrics(experiment_id, game_id, result, game_config)
        
        return {
            "game_id": game_id,
            "status": "completed",
            "scoring": {
                "precision": result.precision,
                "recall": result.recall,
                "f1_score": result.f1_score,
                "evasion_rate": result.evasion_rate,
            },
            "vulnerabilities_injected": len(result.red_manifest) if result.red_manifest else 0,
            "findings_detected": len(result.blue_findings) if result.blue_findings else 0,
            "duration_seconds": duration,
            "red_team_mode": config.red_team_mode,
            "blue_team_mode": config.blue_team_mode,
            "verification_mode": config.verification_mode,
        }
        
    except Exception as e:
        logger.error(f"Game {game_id} failed: {e}", exc_info=True)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Save error info
        save_game_error(bucket, experiment_id, game_id, str(e), game_config)
        
        return {
            "game_id": game_id,
            "status": "failed",
            "error": str(e),
            "duration_seconds": duration,
        }


def save_game_result(bucket: str, experiment_id: str, game_id: str, result, game_config: Dict):
    """Save game result to S3."""
    game_prefix = f"{experiment_id}/realtime-workflow/games/{game_id}"
    
    # Save metadata
    metadata = {
        "game_id": game_id,
        "timestamp": datetime.utcnow().isoformat(),
        "config": game_config,
        "scoring": {
            "precision": result.precision,
            "recall": result.recall,
            "f1_score": result.f1_score,
            "evasion_rate": result.evasion_rate,
        }
    }
    s3.put_object(
        Bucket=bucket,
        Key=f"{game_prefix}/metadata.json",
        Body=json.dumps(metadata, indent=2).encode('utf-8')
    )
    
    # Save scoring
    if result.scoring_result:
        from src.agents.judge_agent import score_results_to_dict
        scoring_dict = score_results_to_dict(result.scoring_result)
        s3.put_object(
            Bucket=bucket,
            Key=f"{game_prefix}/scoring.json",
            Body=json.dumps(scoring_dict, indent=2).encode('utf-8')
        )
    
    # Save red manifest
    if result.red_manifest:
        manifest_list = [v.to_dict() if hasattr(v, 'to_dict') else v for v in result.red_manifest]
        s3.put_object(
            Bucket=bucket,
            Key=f"{game_prefix}/red_manifest.json",
            Body=json.dumps(manifest_list, indent=2).encode('utf-8')
        )
    
    # Save blue findings
    if result.blue_findings:
        findings_list = [f.to_dict() if hasattr(f, 'to_dict') else f for f in result.blue_findings]
        s3.put_object(
            Bucket=bucket,
            Key=f"{game_prefix}/blue_findings.json",
            Body=json.dumps(findings_list, indent=2).encode('utf-8')
        )
    
    # Save code
    if result.code:
        for filename, content in result.code.items():
            s3.put_object(
                Bucket=bucket,
                Key=f"{game_prefix}/code/{filename}",
                Body=content.encode('utf-8')
            )
    
    # Save specialist findings (if ensemble)
    if result.specialist_findings:
        s3.put_object(
            Bucket=bucket,
            Key=f"{game_prefix}/specialist_findings.json",
            Body=json.dumps(result.specialist_findings, indent=2).encode('utf-8')
        )
    
    # Save debate results (if debate verification)
    if result.debate_results:
        s3.put_object(
            Bucket=bucket,
            Key=f"{game_prefix}/debate_results.json",
            Body=json.dumps(result.debate_results, indent=2).encode('utf-8')
        )


def save_game_error(bucket: str, experiment_id: str, game_id: str, error: str, game_config: Dict):
    """Save game error info to S3."""
    game_prefix = f"{experiment_id}/realtime-workflow/games/{game_id}"
    
    error_info = {
        "game_id": game_id,
        "timestamp": datetime.utcnow().isoformat(),
        "config": game_config,
        "status": "failed",
        "error": error
    }
    
    s3.put_object(
        Bucket=bucket,
        Key=f"{game_prefix}/error.json",
        Body=json.dumps(error_info, indent=2).encode('utf-8')
    )


def publish_game_metrics(experiment_id: str, game_id: str, result, game_config: Dict):
    """Publish game metrics to CloudWatch."""
    try:
        dimensions = [
            {'Name': 'ExperimentId', 'Value': experiment_id},
            {'Name': 'Difficulty', 'Value': game_config.get('difficulty', 'unknown')},
            {'Name': 'RedMode', 'Value': game_config.get('red_team_mode', 'single')},
            {'Name': 'BlueMode', 'Value': game_config.get('blue_team_mode', 'single')},
        ]
        
        cloudwatch.put_metric_data(
            Namespace='AdversarialIaC/Experiments',
            MetricData=[
                {'MetricName': 'GameCompleted', 'Value': 1, 'Unit': 'Count', 'Dimensions': dimensions},
                {'MetricName': 'Precision', 'Value': result.precision * 100, 'Unit': 'Percent', 'Dimensions': dimensions},
                {'MetricName': 'Recall', 'Value': result.recall * 100, 'Unit': 'Percent', 'Dimensions': dimensions},
                {'MetricName': 'F1Score', 'Value': result.f1_score * 100, 'Unit': 'Percent', 'Dimensions': dimensions},
                {'MetricName': 'EvasionRate', 'Value': result.evasion_rate * 100, 'Unit': 'Percent', 'Dimensions': dimensions},
            ]
        )
    except Exception as e:
        logger.warning(f"Failed to publish metrics: {e}")
