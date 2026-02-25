"""
Lambda: Process Blue Team Outputs and Run Judge Scoring

This Lambda processes Blue Team batch results and runs the Judge
to score each game. It aggregates all results into the final summary.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Process Blue Team outputs and run Judge scoring.
    
    Input event:
    {
        "experiment_id": "exp-001",
        "bucket": "adversarial-iac-experiments-123456",
        "blue_output_key": "exp-001/batch-workflow/stage2-blue/output/",
        "red_outputs_key": "exp-001/batch-workflow/red_outputs.json",
        "configs_key": "exp-001/batch-workflow/game_configs.json"
    }
    
    Output:
    {
        "experiment_id": "exp-001",
        "summary": {...},
        "results_key": "exp-001/results/summary.json"
    }
    """
    logger.info(f"Running Judge scoring: {json.dumps(event)}")
    
    experiment_id = event['experiment_id']
    bucket = event['bucket']
    blue_output_key = event['blue_output_key']
    red_outputs_key = event['red_outputs_key']
    configs_key = event['configs_key']
    
    # Load game configs
    configs_response = s3.get_object(Bucket=bucket, Key=configs_key)
    game_configs = json.loads(configs_response['Body'].read().decode('utf-8'))
    configs_by_id = {g['game_id']: g for g in game_configs}
    
    # Load Red outputs
    red_response = s3.get_object(Bucket=bucket, Key=red_outputs_key)
    red_outputs = json.loads(red_response['Body'].read().decode('utf-8'))
    
    # Load Blue Team batch results
    blue_results = load_batch_results(bucket, blue_output_key)
    logger.info(f"Loaded {len(blue_results)} Blue Team results")
    
    # Process each game and run Judge
    all_results = []
    metrics_summary = {
        'precision_sum': 0, 'recall_sum': 0, 'f1_sum': 0, 'evasion_sum': 0,
        'total_vulns': 0, 'total_findings': 0, 'total_tp': 0, 'total_fp': 0
    }
    
    for result in blue_results:
        game_id = result.get('recordId')
        if not game_id or game_id not in red_outputs:
            continue
        
        game_config = configs_by_id.get(game_id, {})
        red_output = red_outputs[game_id]
        
        try:
            # Extract Blue Team findings
            output_text = extract_output_text(result)
            blue_findings = parse_blue_team_output(output_text)
            
            # Run Judge scoring
            scoring = score_game(red_output['manifest'], blue_findings)
            
            # Compile game result
            game_result = {
                "game_id": game_id,
                "timestamp": datetime.utcnow().isoformat(),
                "config": game_config,
                "red_team": {
                    "vulnerabilities": len(red_output['manifest']),
                    "manifest": red_output['manifest']
                },
                "blue_team": {
                    "findings": len(blue_findings),
                    "findings_list": blue_findings
                },
                "scoring": scoring
            }
            all_results.append(game_result)
            
            # Update metrics
            metrics_summary['precision_sum'] += scoring['precision']
            metrics_summary['recall_sum'] += scoring['recall']
            metrics_summary['f1_sum'] += scoring['f1_score']
            metrics_summary['evasion_sum'] += scoring['evasion_rate']
            metrics_summary['total_vulns'] += len(red_output['manifest'])
            metrics_summary['total_findings'] += len(blue_findings)
            metrics_summary['total_tp'] += scoring['true_positives']
            metrics_summary['total_fp'] += scoring['false_positives']
            
            # Save individual game result
            save_game_result(bucket, experiment_id, game_id, game_result, red_output)
            
        except Exception as e:
            logger.error(f"Failed to process game {game_id}: {e}")
    
    # Calculate summary statistics
    n = len(all_results)
    summary = {
        "experiment_id": experiment_id,
        "total_games": n,
        "completed_at": datetime.utcnow().isoformat(),
        "metrics": {
            "avg_precision": metrics_summary['precision_sum'] / n if n > 0 else 0,
            "avg_recall": metrics_summary['recall_sum'] / n if n > 0 else 0,
            "avg_f1_score": metrics_summary['f1_sum'] / n if n > 0 else 0,
            "avg_evasion_rate": metrics_summary['evasion_sum'] / n if n > 0 else 0,
            "total_vulnerabilities": metrics_summary['total_vulns'],
            "total_findings": metrics_summary['total_findings'],
            "total_true_positives": metrics_summary['total_tp'],
            "total_false_positives": metrics_summary['total_fp'],
        },
        "by_difficulty": calculate_by_dimension(all_results, 'difficulty'),
        "by_model": calculate_by_dimension(all_results, 'red_model'),
    }
    
    # Save summary
    summary_key = f"{experiment_id}/results/summary.json"
    s3.put_object(
        Bucket=bucket,
        Key=summary_key,
        Body=json.dumps(summary, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    # Save CSV for easy analysis
    csv_key = f"{experiment_id}/results/summary.csv"
    csv_content = generate_csv(all_results)
    s3.put_object(
        Bucket=bucket,
        Key=csv_key,
        Body=csv_content.encode('utf-8'),
        ContentType='text/csv'
    )
    
    # Publish final metrics
    publish_final_metrics(experiment_id, summary)
    
    # Send completion notification
    send_notification(experiment_id, bucket, summary)
    
    return {
        "experiment_id": experiment_id,
        "bucket": bucket,
        "summary": summary,
        "results_key": summary_key,
        "csv_key": csv_key
    }


def load_batch_results(bucket: str, prefix: str) -> List[Dict]:
    """Load all batch result files from S3 prefix."""
    results = []
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
    
    if 'content' in model_output:
        content = model_output['content']
        if isinstance(content, list):
            return ''.join(c.get('text', '') for c in content if c.get('type') == 'text')
        return str(content)
    
    if 'completion' in model_output:
        return model_output['completion']
    
    return json.dumps(model_output)


def parse_blue_team_output(output: str) -> List[Dict]:
    """Parse Blue Team output to extract findings."""
    findings = []
    
    # Try to find JSON array of findings
    json_pattern = r'\[\s*\{[^}]*"finding_id"[^}]*\}.*?\]'
    json_match = re.search(json_pattern, output, re.DOTALL)
    
    if json_match:
        try:
            findings = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to find individual finding objects
    if not findings:
        finding_pattern = r'\{[^}]*"finding_id"\s*:\s*"([^"]+)"[^}]*\}'
        for match in re.finditer(finding_pattern, output):
            try:
                finding_text = match.group(0)
                # Try to parse as JSON
                finding = json.loads(finding_text)
                findings.append(finding)
            except json.JSONDecodeError:
                pass
    
    # Ensure findings have IDs
    for i, finding in enumerate(findings):
        if 'finding_id' not in finding:
            finding['finding_id'] = f'F{i+1}'
    
    return findings


def score_game(red_manifest: List[Dict], blue_findings: List[Dict]) -> Dict:
    """Run Judge scoring for a single game."""
    
    matches = []
    matched_blue_ids = set()
    matched_red_ids = set()
    
    # Find matches
    for red_vuln in red_manifest:
        best_match = find_best_match(red_vuln, blue_findings, matched_blue_ids)
        matches.append(best_match)
        
        if best_match['blue_finding_id']:
            matched_blue_ids.add(best_match['blue_finding_id'])
            matched_red_ids.add(red_vuln.get('vuln_id', ''))
    
    # Calculate metrics
    tp = sum(1 for m in matches if m['match_type'] in ['exact', 'partial'])
    fp = len(blue_findings) - len(matched_blue_ids)
    fn = len(red_manifest) - tp
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    evasion_rate = fn / len(red_manifest) if red_manifest else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "evasion_rate": evasion_rate,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "matches": matches
    }


def find_best_match(red_vuln: Dict, blue_findings: List[Dict], already_matched: set) -> Dict:
    """Find the best matching Blue Team finding for a Red Team vulnerability."""
    
    red_id = red_vuln.get('vuln_id', 'unknown')
    red_resource = red_vuln.get('resource_name', '').lower()
    red_type = red_vuln.get('type', '').lower()
    red_title = red_vuln.get('title', '').lower()
    red_attribute = red_vuln.get('vulnerable_attribute', '').lower()
    
    best_score = 0.0
    best_finding = None
    best_type = 'missed'
    
    for finding in blue_findings:
        finding_id = finding.get('finding_id', '')
        if finding_id in already_matched:
            continue
        
        score = calculate_match_score(red_vuln, finding)
        
        if score > best_score:
            best_score = score
            best_finding = finding
            best_type = 'exact' if score >= 0.7 else ('partial' if score >= 0.4 else 'missed')
    
    if best_finding and best_score >= 0.3:
        return {
            "red_vuln_id": red_id,
            "blue_finding_id": best_finding.get('finding_id', ''),
            "match_type": best_type,
            "confidence": best_score
        }
    
    return {
        "red_vuln_id": red_id,
        "blue_finding_id": None,
        "match_type": "missed",
        "confidence": 0.0
    }


def calculate_match_score(red_vuln: Dict, blue_finding: Dict) -> float:
    """Calculate match score between a vulnerability and finding."""
    score = 0.0
    
    red_resource = red_vuln.get('resource_name', '').lower()
    blue_resource = blue_finding.get('resource_name', '').lower()
    red_type = red_vuln.get('type', '').lower()
    blue_type = blue_finding.get('vulnerability_type', '').lower()
    red_attribute = red_vuln.get('vulnerable_attribute', '').lower()
    blue_evidence = blue_finding.get('evidence', '').lower()
    blue_title = blue_finding.get('title', '').lower()
    blue_description = blue_finding.get('description', '').lower()
    red_title = red_vuln.get('title', '').lower()
    
    # Resource name matching
    if red_resource and blue_resource:
        if red_resource == blue_resource:
            score += 0.4
        elif red_resource in blue_resource or blue_resource in red_resource:
            score += 0.25
        else:
            # Check base names
            red_base = red_resource.split('.')[-1]
            blue_base = blue_resource.split('.')[-1]
            if red_base == blue_base or red_base in blue_base or blue_base in red_base:
                score += 0.2
    
    # Type matching (handle unknown)
    if red_type == 'unknown' or red_type == '':
        if any(kw in blue_title or kw in blue_description for kw in ['encrypt', 'access', 'public', 'permiss', 'log', 'iam']):
            score += 0.1
    elif red_type and blue_type:
        if red_type == blue_type:
            score += 0.2
        elif are_types_related(red_type, blue_type):
            score += 0.1
    
    # Attribute matching
    if red_attribute:
        if red_attribute in blue_evidence:
            score += 0.2
        elif red_attribute in blue_title or red_attribute in blue_description:
            score += 0.15
    
    # Title keyword matching
    red_keywords = set(red_title.split())
    blue_keywords = set(blue_title.split()) | set(blue_description.split())
    if len(red_keywords & blue_keywords) >= 2:
        score += 0.1
    
    return score


def are_types_related(type1: str, type2: str) -> bool:
    """Check if two vulnerability types are related."""
    related = {
        ('encryption', 'data_protection'),
        ('access_control', 'iam'),
        ('network', 'access_control'),
        ('logging', 'monitoring'),
    }
    return (type1, type2) in related or (type2, type1) in related


def save_game_result(bucket: str, experiment_id: str, game_id: str, result: Dict, red_output: Dict):
    """Save individual game result to S3."""
    game_prefix = f"{experiment_id}/batch-workflow/games/{game_id}"
    
    # Save scoring
    s3.put_object(
        Bucket=bucket,
        Key=f"{game_prefix}/scoring.json",
        Body=json.dumps(result['scoring'], indent=2).encode('utf-8')
    )
    
    # Save code
    for filename, content in red_output.get('code', {}).items():
        s3.put_object(
            Bucket=bucket,
            Key=f"{game_prefix}/code/{filename}",
            Body=content.encode('utf-8')
        )
    
    # Save manifest
    s3.put_object(
        Bucket=bucket,
        Key=f"{game_prefix}/red_manifest.json",
        Body=json.dumps(result['red_team']['manifest'], indent=2).encode('utf-8')
    )
    
    # Save findings
    s3.put_object(
        Bucket=bucket,
        Key=f"{game_prefix}/blue_findings.json",
        Body=json.dumps(result['blue_team']['findings_list'], indent=2).encode('utf-8')
    )


def calculate_by_dimension(results: List[Dict], dimension: str) -> Dict:
    """Calculate metrics grouped by a dimension."""
    by_dim = {}
    
    for result in results:
        dim_value = result.get('config', {}).get(dimension, 'unknown')
        if dim_value not in by_dim:
            by_dim[dim_value] = {'count': 0, 'precision': 0, 'recall': 0, 'f1': 0, 'evasion': 0}
        
        by_dim[dim_value]['count'] += 1
        by_dim[dim_value]['precision'] += result['scoring']['precision']
        by_dim[dim_value]['recall'] += result['scoring']['recall']
        by_dim[dim_value]['f1'] += result['scoring']['f1_score']
        by_dim[dim_value]['evasion'] += result['scoring']['evasion_rate']
    
    # Calculate averages
    for dim_value in by_dim:
        n = by_dim[dim_value]['count']
        by_dim[dim_value]['avg_precision'] = by_dim[dim_value]['precision'] / n
        by_dim[dim_value]['avg_recall'] = by_dim[dim_value]['recall'] / n
        by_dim[dim_value]['avg_f1'] = by_dim[dim_value]['f1'] / n
        by_dim[dim_value]['avg_evasion'] = by_dim[dim_value]['evasion'] / n
    
    return by_dim


def generate_csv(results: List[Dict]) -> str:
    """Generate CSV from results."""
    headers = [
        'game_id', 'red_model', 'blue_model', 'difficulty', 'scenario',
        'vulns_injected', 'findings', 'true_positives', 'false_positives',
        'precision', 'recall', 'f1_score', 'evasion_rate'
    ]
    
    lines = [','.join(headers)]
    
    for r in results:
        config = r.get('config', {})
        scoring = r.get('scoring', {})
        line = [
            r.get('game_id', ''),
            config.get('red_model', ''),
            config.get('blue_model', ''),
            config.get('difficulty', ''),
            f'"{config.get("scenario", "")}"',
            str(r.get('red_team', {}).get('vulnerabilities', 0)),
            str(r.get('blue_team', {}).get('findings', 0)),
            str(scoring.get('true_positives', 0)),
            str(scoring.get('false_positives', 0)),
            f"{scoring.get('precision', 0):.4f}",
            f"{scoring.get('recall', 0):.4f}",
            f"{scoring.get('f1_score', 0):.4f}",
            f"{scoring.get('evasion_rate', 0):.4f}"
        ]
        lines.append(','.join(line))
    
    return '\n'.join(lines)


def publish_final_metrics(experiment_id: str, summary: Dict):
    """Publish final experiment metrics to CloudWatch."""
    metrics = summary.get('metrics', {})
    
    try:
        cloudwatch.put_metric_data(
            Namespace='AdversarialIaC/Experiments',
            MetricData=[
                {'MetricName': 'ExperimentCompleted', 'Value': 1, 'Unit': 'Count',
                 'Dimensions': [{'Name': 'ExperimentId', 'Value': experiment_id}]},
                {'MetricName': 'TotalGames', 'Value': summary.get('total_games', 0), 'Unit': 'Count',
                 'Dimensions': [{'Name': 'ExperimentId', 'Value': experiment_id}]},
                {'MetricName': 'AvgPrecision', 'Value': metrics.get('avg_precision', 0) * 100, 'Unit': 'Percent',
                 'Dimensions': [{'Name': 'ExperimentId', 'Value': experiment_id}]},
                {'MetricName': 'AvgRecall', 'Value': metrics.get('avg_recall', 0) * 100, 'Unit': 'Percent',
                 'Dimensions': [{'Name': 'ExperimentId', 'Value': experiment_id}]},
                {'MetricName': 'AvgF1Score', 'Value': metrics.get('avg_f1_score', 0) * 100, 'Unit': 'Percent',
                 'Dimensions': [{'Name': 'ExperimentId', 'Value': experiment_id}]},
                {'MetricName': 'AvgEvasionRate', 'Value': metrics.get('avg_evasion_rate', 0) * 100, 'Unit': 'Percent',
                 'Dimensions': [{'Name': 'ExperimentId', 'Value': experiment_id}]},
            ]
        )
    except Exception as e:
        logger.warning(f"Failed to publish metrics: {e}")


def send_notification(experiment_id: str, bucket: str, summary: Dict):
    """Send completion notification via SNS."""
    topic_arn = os.environ.get('NOTIFICATION_TOPIC_ARN')
    if not topic_arn:
        return
    
    metrics = summary.get('metrics', {})
    message = f"""
🔬 Experiment Complete: {experiment_id}

📊 Results Summary:
• Games: {summary.get('total_games', 0)} completed
• Avg Precision: {metrics.get('avg_precision', 0):.1%}
• Avg Recall: {metrics.get('avg_recall', 0):.1%}
• Avg F1 Score: {metrics.get('avg_f1_score', 0):.1%}
• Avg Evasion Rate: {metrics.get('avg_evasion_rate', 0):.1%}

📁 Results: s3://{bucket}/{experiment_id}/results/

Download with:
adversarial-iac cloud experiment download --id {experiment_id}
    """
    
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject=f"✅ Experiment {experiment_id} Complete",
            Message=message
        )
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
