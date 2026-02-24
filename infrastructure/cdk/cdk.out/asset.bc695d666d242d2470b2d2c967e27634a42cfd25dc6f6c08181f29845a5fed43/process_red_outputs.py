"""
Lambda: Process Red Team Outputs and Generate Blue Team Prompts

This Lambda processes the results from Red Team batch inference,
extracts the generated code, and creates Blue Team prompts.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

# Import prompts (packaged with Lambda)
from prompts import AdversarialPrompts


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Process Red Team batch results and generate Blue Team prompts.
    
    Input event:
    {
        "experiment_id": "exp-001",
        "bucket": "adversarial-iac-experiments-123456",
        "red_output_key": "exp-001/batch-workflow/stage1-red/output/",
        "configs_key": "exp-001/batch-workflow/game_configs.json",
        "blue_model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0"
    }
    
    Output:
    {
        "experiment_id": "exp-001",
        "bucket": "...",
        "prompts_key": "exp-001/batch-workflow/stage2-blue/input/prompts.jsonl",
        "total_prompts": 450,
        "processed_games": 450,
        "failed_games": 0
    }
    """
    logger.info(f"Processing Red Team outputs: {json.dumps(event)}")
    
    experiment_id = event['experiment_id']
    bucket = event['bucket']
    red_output_key = event['red_output_key']
    configs_key = event['configs_key']
    blue_model_id = event.get('blue_model_id')
    
    # Load game configs
    configs_response = s3.get_object(Bucket=bucket, Key=configs_key)
    game_configs = json.loads(configs_response['Body'].read().decode('utf-8'))
    configs_by_id = {g['game_id']: g for g in game_configs}
    
    # Load Red Team batch results
    red_results = load_batch_results(bucket, red_output_key)
    logger.info(f"Loaded {len(red_results)} Red Team results")
    
    # Process each result and generate Blue Team prompts
    blue_prompts = []
    red_outputs = {}
    failed_games = []
    
    for result in red_results:
        game_id = result.get('recordId')
        if not game_id:
            continue
        
        game_config = configs_by_id.get(game_id, {})
        
        try:
            # Extract code and manifest from Red Team output
            output_text = extract_output_text(result)
            code, manifest = parse_red_team_output(output_text, game_config.get('language', 'terraform'))
            
            # Store Red output for later
            red_outputs[game_id] = {
                "code": code,
                "manifest": manifest,
                "raw_output": output_text[:5000]  # Truncate for storage
            }
            
            # Generate Blue Team prompt
            prompt = generate_blue_team_prompt(code, game_config)
            blue_prompts.append({
                "recordId": game_id,
                "modelInput": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 8000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to process game {game_id}: {e}")
            failed_games.append({"game_id": game_id, "error": str(e)})
    
    # Upload Blue Team prompts to S3
    prompts_key = f"{experiment_id}/batch-workflow/stage2-blue/input/prompts.jsonl"
    jsonl_content = "\n".join(json.dumps(p) for p in blue_prompts)
    
    s3.put_object(
        Bucket=bucket,
        Key=prompts_key,
        Body=jsonl_content.encode('utf-8'),
        ContentType='application/jsonl'
    )
    
    # Save Red outputs for Judge stage
    red_outputs_key = f"{experiment_id}/batch-workflow/red_outputs.json"
    s3.put_object(
        Bucket=bucket,
        Key=red_outputs_key,
        Body=json.dumps(red_outputs, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    # Publish metrics
    publish_metrics(experiment_id, len(blue_prompts), 'BlueTeamPromptsGenerated')
    publish_metrics(experiment_id, len(failed_games), 'RedTeamProcessingFailed')
    
    return {
        "experiment_id": experiment_id,
        "bucket": bucket,
        "prompts_key": prompts_key,
        "red_outputs_key": red_outputs_key,
        "total_prompts": len(blue_prompts),
        "processed_games": len(red_outputs),
        "failed_games": len(failed_games),
        "model_id": blue_model_id
    }


def load_batch_results(bucket: str, prefix: str) -> List[Dict]:
    """Load all batch result files from S3 prefix."""
    results = []
    
    # List all result files
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.jsonl'):
                response = s3.get_object(Bucket=bucket, Key=obj['Key'])
                content = response['Body'].read().decode('utf-8')
                for line in content.strip().split('\n'):
                    if line:
                        results.append(json.loads(line))
    
    return results


def extract_output_text(result: Dict) -> str:
    """Extract the output text from a batch result."""
    model_output = result.get('modelOutput', {})
    
    # Handle different response formats
    if 'content' in model_output:
        # Anthropic format
        content = model_output['content']
        if isinstance(content, list):
            return ''.join(c.get('text', '') for c in content if c.get('type') == 'text')
        return str(content)
    
    if 'completion' in model_output:
        return model_output['completion']
    
    return json.dumps(model_output)


def parse_red_team_output(output: str, language: str) -> tuple:
    """Parse Red Team output to extract code and vulnerability manifest."""
    
    code = {}
    manifest = []
    
    # Extract code blocks
    if language == 'terraform':
        main_pattern = r'```(?:hcl|terraform)?\s*([\s\S]*?)```'
    else:
        main_pattern = r'```(?:yaml|cloudformation)?\s*([\s\S]*?)```'
    
    code_matches = re.findall(main_pattern, output, re.IGNORECASE)
    if code_matches:
        # Use the largest code block as main file
        main_code = max(code_matches, key=len)
        filename = 'main.tf' if language == 'terraform' else 'template.yaml'
        code[filename] = main_code.strip()
    
    # Extract vulnerability manifest
    manifest_pattern = r'VULNERABILITY_MANIFEST[:\s]*```(?:json)?\s*([\s\S]*?)```'
    manifest_match = re.search(manifest_pattern, output, re.IGNORECASE)
    
    if manifest_match:
        try:
            manifest = json.loads(manifest_match.group(1))
            if isinstance(manifest, dict):
                manifest = manifest.get('vulnerabilities', [])
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to find JSON array of vulnerabilities
    if not manifest:
        json_pattern = r'\[\s*\{[^}]*"vuln_id"[^}]*\}.*?\]'
        json_match = re.search(json_pattern, output, re.DOTALL)
        if json_match:
            try:
                manifest = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
    
    # Ensure manifest items have required fields
    for i, vuln in enumerate(manifest):
        if 'vuln_id' not in vuln:
            vuln['vuln_id'] = f'V{i+1}'
    
    return code, manifest


def generate_blue_team_prompt(code: Dict[str, str], game_config: Dict) -> str:
    """Generate Blue Team analysis prompt."""
    
    # Combine code files
    combined_code = "\n\n".join(
        f"# File: {filename}\n{content}"
        for filename, content in code.items()
    )
    
    language = game_config.get('language', 'terraform')
    
    prompt = AdversarialPrompts.BLUE_TEAM_DETECTION.format(
        language=language,
        code=combined_code
    )
    
    return prompt


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
