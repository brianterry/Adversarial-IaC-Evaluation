#!/usr/bin/env python3
"""
Local Experiment Runner with S3 Storage

This script runs experiments locally but stores results in S3.
Much simpler than full Lambda deployment, with the same results!

Usage:
    python scripts/run_experiment.py --config experiments/config/quick_test.yaml
    python scripts/run_experiment.py --config experiments/config/full_experiment.yaml --upload-to-s3
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.game.engine import GameEngine, GameConfig
from src.game.scenarios import Scenario

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Run experiments locally with optional S3 storage."""
    
    def __init__(
        self,
        config_path: str,
        output_dir: str = "experiments/results",
        upload_to_s3: bool = False,
        region: str = None,
        delay_between_games: float = None,
    ):
        self.config_path = Path(config_path)
        self.upload_to_s3 = upload_to_s3
        
        # Load config
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        
        # YAML config overrides for settings (CLI args take precedence if set)
        yaml_settings = self.config.get('settings', {})
        yaml_output_dir = yaml_settings.get('output_dir')
        yaml_delay = yaml_settings.get('delay_between_games')
        yaml_region = self.config.get('region')
        
        # Resolve region: CLI > YAML > env > default
        default_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        self.region = region or yaml_region or default_region
        
        # Resolve delay: CLI > YAML > default
        self.delay_between_games = delay_between_games if delay_between_games is not None else (yaml_delay or 2.0)
        
        # Resolve output_dir: YAML output_dir creates exact path, else timestamped
        if yaml_output_dir:
            self.output_dir = Path(yaml_output_dir)
            self.experiment_id = Path(yaml_output_dir).name
            self.experiment_dir = self.output_dir
        else:
            self.output_dir = Path(output_dir)
            self.experiment_id = f"exp-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.experiment_dir = self.output_dir / self.experiment_id
        
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # S3 client (lazy init)
        self._s3 = None
        self._bucket = None
        
        # Results tracking
        self.results: List[Dict] = []
        self.failed_games: List[Dict] = []
        
    @property
    def s3(self):
        if self._s3 is None:
            import boto3
            self._s3 = boto3.client('s3', region_name=self.region)
        return self._s3
    
    @property
    def bucket(self):
        if self._bucket is None:
            config_path = Path.home() / ".adversarial-iac" / "cloud-config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                self._bucket = config.get('bucket')
            if not self._bucket:
                logger.warning("S3 bucket not configured. Results won't be uploaded.")
        return self._bucket
    
    def generate_game_configs(self) -> List[Dict]:
        """Generate all game configurations from experiment config."""
        games = []
        game_num = 1
        
        models = self.config.get('models', [])
        difficulties = self.config.get('difficulties', ['easy', 'medium', 'hard'])
        scenarios = self.config.get('scenarios', [])
        repetitions = self.config.get('settings', {}).get('repetitions', 1)
        language = self.config.get('language', 'terraform')
        cloud_provider = self.config.get('cloud_provider', 'aws')
        
        # Get global settings from config sections
        red_settings = self.config.get('red_settings', {})
        blue_settings = self.config.get('blue_settings', {})
        judge_settings = self.config.get('judge_settings', {})
        
        # Get model IDs
        model_ids = [m['id'] if isinstance(m, dict) else m for m in models]
        if not model_ids:
            model_ids = ["us.anthropic.claude-3-5-haiku-20241022-v1:0"]
        
        # Batch experiments (single-agent)
        batch_config = self.config.get('batch_experiments', {})
        if batch_config.get('enabled', True):
            model_combos = batch_config.get('model_combinations', [])
            if not model_combos:
                # Default: same model for red and blue
                model_combos = [{'red': model_ids[0], 'blue': model_ids[0]}]
            
            for combo in model_combos:
                for difficulty in difficulties:
                    for scenario in scenarios:
                        for rep in range(repetitions):
                            games.append({
                                "game_id": f"G-{game_num:04d}",
                                "scenario": scenario,
                                "difficulty": difficulty,
                                "red_model": combo['red'],
                                "blue_model": combo['blue'],
                                "red_team_mode": red_settings.get('red_team_mode', 'single'),
                                "blue_team_mode": blue_settings.get('blue_team_mode', 'single'),
                                "verification_mode": self.config.get('verification_mode', 'standard'),
                                "language": language,
                                "cloud_provider": cloud_provider,
                                "repetition": rep + 1,
                                "experiment_type": "batch",
                                # New Red Team parameters
                                "red_strategy": red_settings.get('red_strategy', 'balanced'),
                                "red_vuln_source": red_settings.get('red_vuln_source', 'database'),
                                "blue_team_profile": red_settings.get('blue_team_profile'),
                                # New Blue Team parameters
                                "blue_strategy": blue_settings.get('blue_strategy', 'comprehensive'),
                                "detection_mode": blue_settings.get('detection_mode', 'llm_only'),
                                # New Judge parameters
                                "use_llm_judge": judge_settings.get('use_llm_judge', True),
                                "use_consensus_judge": judge_settings.get('use_consensus_judge', False),
                                "use_trivy": judge_settings.get('use_trivy', False),
                                "use_checkov": judge_settings.get('use_checkov', False),
                            })
                            game_num += 1
        
        # Realtime experiments (multi-agent)
        realtime_config = self.config.get('realtime_experiments', {})
        if realtime_config.get('enabled', False):
            modes = realtime_config.get('modes', [])
            
            for mode in modes:
                model_id = mode.get('model', model_ids[0])
                for difficulty in difficulties:
                    for scenario in scenarios:
                        for rep in range(repetitions):
                            games.append({
                                "game_id": f"G-{game_num:04d}",
                                "scenario": scenario,
                                "difficulty": difficulty,
                                "red_model": model_id,
                                "blue_model": model_id,
                                "red_team_mode": mode.get('red_mode', 'single'),
                                "blue_team_mode": mode.get('blue_mode', 'single'),
                                "consensus_method": mode.get('consensus_method', 'vote'),
                                "verification_mode": mode.get('verification_mode', 'standard'),
                                "language": language,
                                "cloud_provider": cloud_provider,
                                "repetition": rep + 1,
                                "experiment_type": "realtime",
                                "mode_name": mode.get('name', 'unknown'),
                                "condition": mode.get('condition', 'unknown'),
                                # Mode-specific Red Team parameters (override globals)
                                "red_strategy": mode.get('red_strategy', red_settings.get('red_strategy', 'balanced')),
                                "red_vuln_source": mode.get('red_vuln_source', red_settings.get('red_vuln_source', 'database')),
                                "blue_team_profile": mode.get('blue_team_profile', red_settings.get('blue_team_profile')),
                                # Mode-specific Blue Team parameters
                                "blue_strategy": mode.get('blue_strategy', blue_settings.get('blue_strategy', 'comprehensive')),
                                "detection_mode": mode.get('detection_mode', blue_settings.get('detection_mode', 'llm_only')),
                                # Mode-specific Judge parameters
                                "use_llm_judge": mode.get('use_llm_judge', judge_settings.get('use_llm_judge', True)),
                                "use_consensus_judge": mode.get('use_consensus_judge', judge_settings.get('use_consensus_judge', False)),
                                "use_trivy": mode.get('use_trivy', judge_settings.get('use_trivy', False)),
                                "use_checkov": mode.get('use_checkov', judge_settings.get('use_checkov', False)),
                            })
                            game_num += 1
        
        return games
    
    async def run_single_game(self, game_config: Dict) -> Dict:
        """Run a single game and return results."""
        game_id = game_config['game_id']
        logger.info(f"Running game {game_id}: {game_config['scenario'][:50]}...")
        
        start_time = datetime.utcnow()
        
        try:
            # Create engine config with all supported parameters
            config = GameConfig(
                red_model=game_config['red_model'],
                blue_model=game_config['blue_model'],
                difficulty=game_config['difficulty'],
                language=game_config.get('language', 'terraform'),
                cloud_provider=game_config.get('cloud_provider', 'aws'),
                red_team_mode=game_config.get('red_team_mode', 'single'),
                blue_team_mode=game_config.get('blue_team_mode', 'single'),
                consensus_method=game_config.get('consensus_method', 'vote'),
                verification_mode=game_config.get('verification_mode', 'standard'),
                region=self.region,
                # Red Team parameters
                red_strategy=game_config.get('red_strategy', 'balanced'),
                red_vuln_source=game_config.get('red_vuln_source', 'database'),
                blue_team_profile=game_config.get('blue_team_profile'),
                # Blue Team parameters
                blue_strategy=game_config.get('blue_strategy', 'comprehensive'),
                detection_mode=game_config.get('detection_mode', 'llm_only'),
                # Judge parameters
                use_llm_judge=game_config.get('use_llm_judge', True),
                use_consensus_judge=game_config.get('use_consensus_judge', False),
                use_trivy=game_config.get('use_trivy', False),
                use_checkov=game_config.get('use_checkov', False),
            )
            
            # Create scenario
            scenario = Scenario(
                id=game_config['game_id'],
                description=game_config['scenario'],
                domain='general',
                cloud_provider=config.cloud_provider,
                language=config.language,
                difficulty=config.difficulty,
            )
            
            # Run game
            engine = GameEngine()
            result = await engine.run_game(scenario, config)
            
            # Save result
            engine._save_game_result(result)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Extract scoring from result
            scoring = result.scoring
            
            # Extract manifest validation if available
            mv = getattr(result, 'manifest_validation', None)
            manifest_metrics = {}
            if mv and isinstance(mv, dict) and 'metrics' in mv:
                manifest_metrics = {
                    "manifest_accuracy": mv['metrics'].get('manifest_accuracy', None),
                    "total_claimed": mv['metrics'].get('total_claimed', 0),
                    "total_confirmed": mv['metrics'].get('total_confirmed', 0),
                    "hallucination_rate": mv['metrics'].get('hallucination_rate', None),
                }
            
            # Also capture ground truth quality from scoring (computed in engine)
            manifest_metrics["adjusted_recall"] = getattr(scoring, 'adjusted_recall', None)
            manifest_metrics["phantom_concordance"] = getattr(scoring, 'phantom_concordance', None)
            # Use scoring's manifest_accuracy if not already set from validation dict
            if manifest_metrics.get("manifest_accuracy") is None:
                manifest_metrics["manifest_accuracy"] = getattr(scoring, 'manifest_accuracy', None)
            
            game_result = {
                "game_id": game_id,
                "status": "completed",
                "config": game_config,
                "scoring": {
                    "precision": scoring.precision,
                    "adjusted_precision": getattr(scoring, 'adjusted_precision', scoring.precision),
                    "recall": scoring.recall,
                    "f1_score": scoring.f1_score,
                    "evasion_rate": scoring.evasion_rate,
                    "tool_validated_fps": len(getattr(scoring, 'tool_validated_fps', [])),
                    "true_false_positives": len(getattr(scoring, 'true_false_positives', [])),
                },
                "manifest_validation": manifest_metrics,
                "vulnerabilities_injected": len(result.red_output.manifest) if result.red_output else 0,
                "findings_detected": len(result.blue_output.findings) if result.blue_output else 0,
                "duration_seconds": duration,
                "timestamp": end_time.isoformat(),
                "output_dir": result.game_id,
            }
            
            adj_p = getattr(scoring, 'adjusted_precision', scoring.precision)
            tool_fps = len(getattr(scoring, 'tool_validated_fps', []))
            log_msg = f"  ✓ {game_id}: P={scoring.precision:.0%}"
            if adj_p != scoring.precision:
                log_msg += f" (adj:{adj_p:.0%}, {tool_fps} tool-validated)"
            log_msg += f" R={scoring.recall:.0%} F1={scoring.f1_score:.0%} Evasion={scoring.evasion_rate:.0%}"
            if manifest_metrics.get('manifest_accuracy') is not None:
                log_msg += f" ManifestAcc={manifest_metrics['manifest_accuracy']:.0%}"
            logger.info(log_msg)
            
            return game_result
            
        except Exception as e:
            logger.error(f"  ✗ {game_id} failed: {e}")
            return {
                "game_id": game_id,
                "status": "failed",
                "config": game_config,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def run(self):
        """Run the full experiment."""
        logger.info(f"=" * 60)
        logger.info(f"Starting Experiment: {self.experiment_id}")
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Output: {self.experiment_dir}")
        logger.info(f"=" * 60)
        
        # Generate game configs
        games = self.generate_game_configs()
        logger.info(f"Generated {len(games)} game configurations")
        
        # Save config
        (self.experiment_dir / "config.json").write_text(
            json.dumps({
                "experiment_id": self.experiment_id,
                "config": self.config,
                "games": games,
                "started": datetime.utcnow().isoformat(),
            }, indent=2)
        )
        
        # Run games sequentially
        for i, game_config in enumerate(games):
            logger.info(f"\n[{i+1}/{len(games)}] Game {game_config['game_id']}")
            
            result = await self.run_single_game(game_config)
            
            if result['status'] == 'completed':
                self.results.append(result)
            else:
                self.failed_games.append(result)
            
            # Save progress after each game
            self._save_progress()
            
            # Rate limiting delay (except for last game)
            if i < len(games) - 1 and self.delay_between_games > 0:
                logger.info(f"  Waiting {self.delay_between_games}s before next game...")
                await asyncio.sleep(self.delay_between_games)
        
        # Generate summary
        summary = self._generate_summary()
        
        # Upload to S3 if enabled
        if self.upload_to_s3 and self.bucket:
            self._upload_to_s3()
        
        return summary
    
    def _save_progress(self):
        """Save current progress to disk."""
        progress = {
            "experiment_id": self.experiment_id,
            "completed_games": len(self.results),
            "failed_games": len(self.failed_games),
            "results": self.results,
            "failures": self.failed_games,
            "last_updated": datetime.utcnow().isoformat(),
        }
        (self.experiment_dir / "progress.json").write_text(json.dumps(progress, indent=2))
    
    @staticmethod
    def _std(values):
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        m = sum(values) / len(values)
        return (sum((x - m) ** 2 for x in values) / (len(values) - 1)) ** 0.5

    def _generate_summary(self) -> Dict:
        """Generate experiment summary."""
        if not self.results:
            return {"status": "no_results", "experiment_id": self.experiment_id}
        
        # Calculate aggregate metrics
        n = len(self.results)
        p_vals = [r['scoring']['precision'] for r in self.results]
        r_vals = [r['scoring']['recall'] for r in self.results]
        f_vals = [r['scoring']['f1_score'] for r in self.results]
        e_vals = [r['scoring']['evasion_rate'] for r in self.results]
        
        metrics = {
            "avg_precision": sum(p_vals) / n,
            "std_precision": self._std(p_vals),
            "avg_recall": sum(r_vals) / n,
            "std_recall": self._std(r_vals),
            "avg_f1_score": sum(f_vals) / n,
            "std_f1_score": self._std(f_vals),
            "avg_evasion_rate": sum(e_vals) / n,
            "std_evasion_rate": self._std(e_vals),
            "total_vulnerabilities": sum(r['vulnerabilities_injected'] for r in self.results),
            "total_findings": sum(r['findings_detected'] for r in self.results),
        }
        
        # Calculate by difficulty
        by_difficulty = {}
        for r in self.results:
            diff = r['config']['difficulty']
            if diff not in by_difficulty:
                by_difficulty[diff] = {'count': 0, 'precision': 0, 'recall': 0, 'f1': 0, 'evasion': 0}
            by_difficulty[diff]['count'] += 1
            by_difficulty[diff]['precision'] += r['scoring']['precision']
            by_difficulty[diff]['recall'] += r['scoring']['recall']
            by_difficulty[diff]['f1'] += r['scoring']['f1_score']
            by_difficulty[diff]['evasion'] += r['scoring']['evasion_rate']
        
        for diff in by_difficulty:
            count = by_difficulty[diff]['count']
            by_difficulty[diff]['avg_precision'] = by_difficulty[diff]['precision'] / count
            by_difficulty[diff]['avg_recall'] = by_difficulty[diff]['recall'] / count
            by_difficulty[diff]['avg_f1'] = by_difficulty[diff]['f1'] / count
            by_difficulty[diff]['avg_evasion'] = by_difficulty[diff]['evasion'] / count
        
        # Calculate by condition (for ablation experiments)
        by_condition = {}
        for r in self.results:
            cond = r['config'].get('condition', r['config'].get('mode_name', 'batch'))
            if cond not in by_condition:
                by_condition[cond] = {'count': 0, 'precision': 0, 'recall': 0, 'f1': 0, 'evasion': 0}
            by_condition[cond]['count'] += 1
            by_condition[cond]['precision'] += r['scoring']['precision']
            by_condition[cond]['recall'] += r['scoring']['recall']
            by_condition[cond]['f1'] += r['scoring']['f1_score']
            by_condition[cond]['evasion'] += r['scoring']['evasion_rate']
        
        for cond in by_condition:
            count = by_condition[cond]['count']
            by_condition[cond]['avg_precision'] = by_condition[cond]['precision'] / count
            by_condition[cond]['avg_recall'] = by_condition[cond]['recall'] / count
            by_condition[cond]['avg_f1'] = by_condition[cond]['f1'] / count
            by_condition[cond]['avg_evasion'] = by_condition[cond]['evasion'] / count
        
        # Calculate by vuln_source (for E3 experiment)
        by_vuln_source = {}
        for r in self.results:
            src = r['config'].get('red_vuln_source', 'database')
            if src not in by_vuln_source:
                by_vuln_source[src] = {'count': 0, 'precision': 0, 'recall': 0, 'f1': 0, 'evasion': 0}
            by_vuln_source[src]['count'] += 1
            by_vuln_source[src]['precision'] += r['scoring']['precision']
            by_vuln_source[src]['recall'] += r['scoring']['recall']
            by_vuln_source[src]['f1'] += r['scoring']['f1_score']
            by_vuln_source[src]['evasion'] += r['scoring']['evasion_rate']
        
        for src in by_vuln_source:
            count = by_vuln_source[src]['count']
            by_vuln_source[src]['avg_precision'] = by_vuln_source[src]['precision'] / count
            by_vuln_source[src]['avg_recall'] = by_vuln_source[src]['recall'] / count
            by_vuln_source[src]['avg_f1'] = by_vuln_source[src]['f1'] / count
            by_vuln_source[src]['avg_evasion'] = by_vuln_source[src]['evasion'] / count
        
        summary = {
            "experiment_id": self.experiment_id,
            "total_games": len(self.results) + len(self.failed_games),
            "completed_games": len(self.results),
            "failed_games": len(self.failed_games),
            "metrics": metrics,
            "by_difficulty": by_difficulty,
            "by_condition": by_condition,
            "by_vuln_source": by_vuln_source,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        # Save summary
        (self.experiment_dir / "summary.json").write_text(json.dumps(summary, indent=2))
        
        # Generate CSV
        self._generate_csv()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("EXPERIMENT COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Experiment ID: {self.experiment_id}")
        logger.info(f"Total Games: {summary['total_games']} ({summary['completed_games']} completed, {summary['failed_games']} failed)")
        logger.info(f"\nAggregate Metrics:")
        logger.info(f"  Avg Precision:    {metrics['avg_precision']:.1%} ± {metrics['std_precision']:.1%}")
        logger.info(f"  Avg Recall:       {metrics['avg_recall']:.1%} ± {metrics['std_recall']:.1%}")
        logger.info(f"  Avg F1 Score:     {metrics['avg_f1_score']:.1%} ± {metrics['std_f1_score']:.1%}")
        logger.info(f"  Avg Evasion Rate: {metrics['avg_evasion_rate']:.1%} ± {metrics['std_evasion_rate']:.1%}")
        
        # Report manifest validation if available
        mv_results = [r.get('manifest_validation', {}).get('manifest_accuracy') 
                      for r in self.results if r.get('manifest_validation', {}).get('manifest_accuracy') is not None]
        if mv_results:
            avg_mv = sum(mv_results) / len(mv_results)
            logger.info(f"  Manifest Accuracy: {avg_mv:.1%} ({len(mv_results)}/{len(self.results)} games validated)")
        logger.info(f"\nBy Difficulty:")
        for diff, data in by_difficulty.items():
            logger.info(f"  {diff}: F1={data['avg_f1']:.1%}, Evasion={data['avg_evasion']:.1%} (n={data['count']})")
        
        if len(by_condition) > 1:
            logger.info(f"\nBy Condition:")
            for cond, data in by_condition.items():
                logger.info(f"  {cond}: F1={data['avg_f1']:.1%}, Evasion={data['avg_evasion']:.1%} (n={data['count']})")
        
        if len(by_vuln_source) > 1:
            logger.info(f"\nBy Vulnerability Source:")
            for src, data in by_vuln_source.items():
                logger.info(f"  {src}: F1={data['avg_f1']:.1%}, Recall={data['avg_recall']:.1%} (n={data['count']})")
        
        logger.info(f"\nResults saved to: {self.experiment_dir}")
        
        return summary
    
    def _generate_csv(self):
        """Generate CSV file for easy analysis."""
        headers = [
            'game_id', 'condition', 'difficulty', 'red_model', 'blue_model', 
            'red_mode', 'blue_mode', 'red_vuln_source', 'red_strategy',
            'verification_mode', 'scenario', 'vulns_injected', 'findings', 
            'precision', 'adjusted_precision', 'tool_validated_fps', 'true_fps',
            'recall', 'f1_score', 'evasion_rate',
            'manifest_accuracy', 'adjusted_recall', 'phantom_concordance',
            'manifest_confirmed', 'manifest_claimed'
        ]
        
        lines = [','.join(headers)]
        for r in self.results:
            config = r['config']
            scoring = r['scoring']
            line = [
                r['game_id'],
                config.get('condition', config.get('mode_name', 'batch')),
                config['difficulty'],
                config['red_model'].split('.')[-1][:20],  # Shorten model name
                config['blue_model'].split('.')[-1][:20],
                config.get('red_team_mode', 'single'),
                config.get('blue_team_mode', 'single'),
                config.get('red_vuln_source', 'database'),
                config.get('red_strategy', 'balanced'),
                config.get('verification_mode', 'standard'),
                f'"{config["scenario"][:50]}"',
                str(r['vulnerabilities_injected']),
                str(r['findings_detected']),
                f"{scoring['precision']:.4f}",
                f"{scoring.get('adjusted_precision', scoring['precision']):.4f}",
                str(scoring.get('tool_validated_fps', 0)),
                str(scoring.get('true_false_positives', 0)),
                f"{scoring['recall']:.4f}",
                f"{scoring['f1_score']:.4f}",
                f"{scoring['evasion_rate']:.4f}",
                # Manifest validation & ground truth quality
                f"{mv_acc:.4f}" if (mv_acc := r.get('manifest_validation', {}).get('manifest_accuracy')) is not None else "",
                f"{adj_r:.4f}" if (adj_r := r.get('manifest_validation', {}).get('adjusted_recall')) is not None else "",
                f"{pc:.4f}" if (pc := r.get('manifest_validation', {}).get('phantom_concordance')) is not None else "",
                str(r.get('manifest_validation', {}).get('total_confirmed', '')),
                str(r.get('manifest_validation', {}).get('total_claimed', '')),
            ]
            lines.append(','.join(line))
        
        (self.experiment_dir / "results.csv").write_text('\n'.join(lines))
    
    def _upload_to_s3(self):
        """Upload results to S3."""
        if not self.bucket:
            logger.warning("No S3 bucket configured, skipping upload")
            return
        
        logger.info(f"Uploading results to s3://{self.bucket}/{self.experiment_id}/")
        
        for file_path in self.experiment_dir.glob("**/*"):
            if file_path.is_file():
                key = f"{self.experiment_id}/{file_path.relative_to(self.experiment_dir)}"
                logger.info(f"  Uploading: {key}")
                self.s3.upload_file(str(file_path), self.bucket, key)
        
        logger.info("Upload complete!")


def main():
    parser = argparse.ArgumentParser(description="Run Adversarial IaC Experiment")
    parser.add_argument("--config", "-c", required=True, help="Experiment config YAML")
    parser.add_argument("--output", "-o", default="experiments/results", help="Output directory")
    parser.add_argument("--upload-to-s3", action="store_true", help="Upload results to S3")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between games (seconds)")
    
    args = parser.parse_args()
    
    runner = ExperimentRunner(
        config_path=args.config,
        output_dir=args.output,
        upload_to_s3=args.upload_to_s3,
        region=args.region,
        delay_between_games=args.delay,
    )
    
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
