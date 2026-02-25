#!/usr/bin/env python3
"""
Comparative Experiment Runner - Generates data for publication

This script runs systematic experiments comparing:
1. Single vs Pipeline Red Team (evasion rates)
2. Single vs Ensemble Blue Team (detection rates)
3. Standard vs Debate verification (false positive rates)
4. Ground truth validation metrics (manifest accuracy)

Output: Statistical tables suitable for academic papers

Usage:
    python scripts/run_comparative_experiment.py --scenarios 20 --output results/
    
    # Quick test run
    python scripts/run_comparative_experiment.py --scenarios 5 --quick
"""

import argparse
import asyncio
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.game.engine import GameEngine, GameConfig
from src.game.scenarios import Scenario, ScenarioGenerator


@dataclass
class ExperimentConfig:
    """Configuration for a comparative experiment."""
    name: str
    description: str
    
    # Variables to compare
    red_team_modes: List[str] = field(default_factory=lambda: ["single", "pipeline"])
    blue_team_modes: List[str] = field(default_factory=lambda: ["single", "ensemble"])
    verification_modes: List[str] = field(default_factory=lambda: ["standard", "debate"])
    
    # Fixed settings
    red_model: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    blue_model: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    difficulty: str = "medium"
    language: str = "terraform"
    cloud_provider: str = "aws"
    
    # Experiment parameters
    scenarios_per_condition: int = 10
    use_static_tools: bool = True  # For manifest validation


@dataclass 
class ExperimentResults:
    """Results from a comparative experiment."""
    config: ExperimentConfig
    timestamp: str
    
    # Raw results
    all_games: List[Dict[str, Any]] = field(default_factory=list)
    
    # Aggregated by condition
    by_red_mode: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))
    by_blue_mode: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))
    by_verification: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))
    
    # Statistical summaries
    summary_tables: Dict[str, Any] = field(default_factory=dict)


class ComparativeExperiment:
    """
    Runs comparative experiments for publication-quality results.
    
    Produces:
    - Tables comparing modes (for paper)
    - Statistical significance tests
    - Ground truth validation metrics
    """
    
    def __init__(
        self,
        config: ExperimentConfig,
        output_dir: str = "results/experiments",
        region: str = "us-east-1",
    ):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.region = region
        self.logger = logging.getLogger("ComparativeExperiment")
        
        # Initialize engine
        self.engine = GameEngine(
            output_dir=str(self.output_dir / "games"),
            region=region,
        )
        
        # Generate scenarios
        self.scenario_gen = ScenarioGenerator()
    
    async def run(self) -> ExperimentResults:
        """Run the full comparative experiment."""
        self.logger.info(f"Starting experiment: {self.config.name}")
        self.logger.info(f"Conditions: {len(self._get_all_conditions())} configurations")
        self.logger.info(f"Scenarios per condition: {self.config.scenarios_per_condition}")
        
        results = ExperimentResults(
            config=self.config,
            timestamp=datetime.now().isoformat(),
        )
        
        # Get scenarios
        scenarios = self._select_scenarios()
        self.logger.info(f"Selected {len(scenarios)} scenarios")
        
        # Run all conditions
        conditions = self._get_all_conditions()
        total_games = len(conditions) * len(scenarios)
        
        self.logger.info(f"Total games to run: {total_games}")
        
        game_num = 0
        for condition in conditions:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Condition: {condition['name']}")
            self.logger.info(f"  Red: {condition['red_team_mode']}, Blue: {condition['blue_team_mode']}")
            self.logger.info(f"  Verification: {condition['verification_mode']}")
            self.logger.info(f"{'='*60}")
            
            for scenario in scenarios:
                game_num += 1
                self.logger.info(f"\nGame {game_num}/{total_games}: {scenario.description[:50]}...")
                
                try:
                    game_result = await self._run_single_game(condition, scenario)
                    
                    # Store results
                    results.all_games.append(game_result)
                    results.by_red_mode[condition["red_team_mode"]].append(game_result)
                    results.by_blue_mode[condition["blue_team_mode"]].append(game_result)
                    results.by_verification[condition["verification_mode"]].append(game_result)
                    
                    self.logger.info(
                        f"  Result: P={game_result['precision']:.2f}, "
                        f"R={game_result['recall']:.2f}, "
                        f"Evasion={game_result['evasion_rate']:.2f}"
                    )
                    
                except Exception as e:
                    self.logger.error(f"  Game failed: {e}")
                    continue
        
        # Generate summary tables
        results.summary_tables = self._generate_summary_tables(results)
        
        # Save results
        self._save_results(results)
        
        return results
    
    def _get_all_conditions(self) -> List[Dict[str, str]]:
        """Generate all experimental conditions."""
        conditions = []
        
        for red_mode in self.config.red_team_modes:
            for blue_mode in self.config.blue_team_modes:
                for verification in self.config.verification_modes:
                    conditions.append({
                        "name": f"{red_mode}_{blue_mode}_{verification}",
                        "red_team_mode": red_mode,
                        "blue_team_mode": blue_mode,
                        "verification_mode": verification,
                    })
        
        return conditions
    
    def _select_scenarios(self) -> List[Scenario]:
        """Select diverse scenarios for the experiment."""
        all_scenarios = self.scenario_gen.get_all_scenarios()
        
        # Limit to configured count
        n = min(self.config.scenarios_per_condition, len(all_scenarios))
        
        # Try to get diverse scenarios across domains
        selected = []
        domains_used = set()
        
        for scenario in all_scenarios:
            if len(selected) >= n:
                break
            
            # Prefer scenarios from new domains
            if scenario.domain not in domains_used or len(selected) < n // 2:
                selected.append(scenario)
                domains_used.add(scenario.domain)
        
        # Fill remaining slots
        for scenario in all_scenarios:
            if len(selected) >= n:
                break
            if scenario not in selected:
                selected.append(scenario)
        
        return selected[:n]
    
    async def _run_single_game(
        self,
        condition: Dict[str, str],
        scenario: Scenario,
    ) -> Dict[str, Any]:
        """Run a single game and extract metrics."""
        
        config = GameConfig(
            red_model=self.config.red_model,
            blue_model=self.config.blue_model,
            difficulty=self.config.difficulty,
            language=self.config.language,
            cloud_provider=self.config.cloud_provider,
            detection_mode="hybrid" if self.config.use_static_tools else "llm_only",
            use_trivy=self.config.use_static_tools,
            use_checkov=self.config.use_static_tools,
            region=self.region,
            red_team_mode=condition["red_team_mode"],
            blue_team_mode=condition["blue_team_mode"],
            verification_mode=condition["verification_mode"],
            use_llm_judge=True,
        )
        
        result = await self.engine.run_game(scenario, config)
        
        # Extract metrics
        metrics = {
            "game_id": result.game_id,
            "scenario": scenario.description,
            "scenario_domain": scenario.domain,
            "condition": condition["name"],
            "red_team_mode": condition["red_team_mode"],
            "blue_team_mode": condition["blue_team_mode"],
            "verification_mode": condition["verification_mode"],
            
            # Scoring metrics
            "precision": result.scoring.precision,
            "recall": result.scoring.recall,
            "f1_score": result.scoring.f1_score,
            "evasion_rate": result.scoring.evasion_rate,
            
            # Counts
            "vulns_injected": result.scoring.total_red_vulns,
            "findings_reported": result.scoring.total_blue_findings,
            "true_positives": len(result.scoring.true_positives),
            "false_positives": len(result.scoring.false_positives),
            "false_negatives": len(result.scoring.false_negatives),
            
            # Timing
            "red_time": result.red_time_seconds,
            "blue_time": result.blue_time_seconds,
            "total_time": result.total_time_seconds,
        }
        
        # Add manifest validation if available
        if result.manifest_validation:
            metrics["manifest_accuracy"] = result.manifest_validation["metrics"]["manifest_accuracy"]
            metrics["hallucination_rate"] = result.manifest_validation["metrics"]["hallucination_rate"]
            metrics["confirmed_vulns"] = result.manifest_validation["metrics"]["total_confirmed"]
        
        return metrics
    
    def _generate_summary_tables(self, results: ExperimentResults) -> Dict[str, Any]:
        """Generate statistical summary tables for the paper."""
        tables = {}
        
        # Table 1: Red Team Mode Comparison
        tables["red_team_comparison"] = self._summarize_by_group(
            results.by_red_mode,
            "Red Team Mode",
            primary_metric="evasion_rate",
        )
        
        # Table 2: Blue Team Mode Comparison
        tables["blue_team_comparison"] = self._summarize_by_group(
            results.by_blue_mode,
            "Blue Team Mode",
            primary_metric="f1_score",
        )
        
        # Table 3: Verification Mode Comparison
        tables["verification_comparison"] = self._summarize_by_group(
            results.by_verification,
            "Verification Mode",
            primary_metric="precision",
        )
        
        # Table 4: Ground Truth Validation
        tables["ground_truth_validation"] = self._summarize_manifest_validation(results)
        
        # Table 5: Overall Statistics
        tables["overall_statistics"] = self._compute_overall_statistics(results)
        
        return tables
    
    def _summarize_by_group(
        self,
        grouped_results: Dict[str, List[Dict]],
        group_name: str,
        primary_metric: str,
    ) -> Dict[str, Any]:
        """Create summary statistics for a grouping variable."""
        summary = {
            "group_name": group_name,
            "groups": {},
        }
        
        for group_key, games in grouped_results.items():
            if not games:
                continue
            
            metrics = {
                "n": len(games),
                "precision": self._compute_stats([g["precision"] for g in games]),
                "recall": self._compute_stats([g["recall"] for g in games]),
                "f1_score": self._compute_stats([g["f1_score"] for g in games]),
                "evasion_rate": self._compute_stats([g["evasion_rate"] for g in games]),
            }
            
            # Add manifest validation if available
            manifest_vals = [g["manifest_accuracy"] for g in games if "manifest_accuracy" in g]
            if manifest_vals:
                metrics["manifest_accuracy"] = self._compute_stats(manifest_vals)
            
            summary["groups"][group_key] = metrics
        
        return summary
    
    def _compute_stats(self, values: List[float]) -> Dict[str, float]:
        """Compute summary statistics for a list of values."""
        if not values:
            return {"mean": 0, "std": 0, "min": 0, "max": 0, "n": 0}
        
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "n": len(values),
        }
    
    def _summarize_manifest_validation(self, results: ExperimentResults) -> Dict[str, Any]:
        """Summarize ground truth validation metrics."""
        accuracies = []
        hallucinations = []
        confirmed_counts = []
        
        for game in results.all_games:
            if "manifest_accuracy" in game:
                accuracies.append(game["manifest_accuracy"])
            if "hallucination_rate" in game:
                hallucinations.append(game["hallucination_rate"])
            if "confirmed_vulns" in game:
                confirmed_counts.append(game["confirmed_vulns"])
        
        return {
            "manifest_accuracy": self._compute_stats(accuracies),
            "hallucination_rate": self._compute_stats(hallucinations),
            "confirmed_vulns_per_game": self._compute_stats(confirmed_counts),
            "games_with_validation": len(accuracies),
            "total_games": len(results.all_games),
        }
    
    def _compute_overall_statistics(self, results: ExperimentResults) -> Dict[str, Any]:
        """Compute overall experiment statistics."""
        all_games = results.all_games
        
        return {
            "total_games": len(all_games),
            "total_vulnerabilities_injected": sum(g["vulns_injected"] for g in all_games),
            "total_findings_reported": sum(g["findings_reported"] for g in all_games),
            "overall_precision": self._compute_stats([g["precision"] for g in all_games]),
            "overall_recall": self._compute_stats([g["recall"] for g in all_games]),
            "overall_f1": self._compute_stats([g["f1_score"] for g in all_games]),
            "overall_evasion": self._compute_stats([g["evasion_rate"] for g in all_games]),
            "avg_game_time_seconds": np.mean([g["total_time"] for g in all_games]),
        }
    
    def _save_results(self, results: ExperimentResults) -> None:
        """Save experiment results to files."""
        experiment_dir = self.output_dir / f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # Save full results
        (experiment_dir / "full_results.json").write_text(
            json.dumps({
                "config": {
                    "name": results.config.name,
                    "description": results.config.description,
                    "red_team_modes": results.config.red_team_modes,
                    "blue_team_modes": results.config.blue_team_modes,
                    "verification_modes": results.config.verification_modes,
                    "scenarios_per_condition": results.config.scenarios_per_condition,
                },
                "timestamp": results.timestamp,
                "all_games": results.all_games,
                "summary_tables": results.summary_tables,
            }, indent=2)
        )
        
        # Save paper-ready tables
        self._save_latex_tables(results, experiment_dir)
        self._save_markdown_tables(results, experiment_dir)
        
        self.logger.info(f"Results saved to: {experiment_dir}")
    
    def _save_latex_tables(self, results: ExperimentResults, output_dir: Path) -> None:
        """Save tables in LaTeX format for papers."""
        latex_content = []
        
        # Table 1: Red Team Comparison
        latex_content.append("% Table 1: Red Team Mode Comparison")
        latex_content.append("\\begin{table}[h]")
        latex_content.append("\\centering")
        latex_content.append("\\caption{Red Team Mode Comparison}")
        latex_content.append("\\begin{tabular}{lcccc}")
        latex_content.append("\\hline")
        latex_content.append("Mode & Evasion Rate & Precision & Recall & n \\\\")
        latex_content.append("\\hline")
        
        for mode, stats in results.summary_tables["red_team_comparison"]["groups"].items():
            latex_content.append(
                f"{mode} & "
                f"{stats['evasion_rate']['mean']:.2f} $\\pm$ {stats['evasion_rate']['std']:.2f} & "
                f"{stats['precision']['mean']:.2f} $\\pm$ {stats['precision']['std']:.2f} & "
                f"{stats['recall']['mean']:.2f} $\\pm$ {stats['recall']['std']:.2f} & "
                f"{stats['n']} \\\\"
            )
        
        latex_content.append("\\hline")
        latex_content.append("\\end{tabular}")
        latex_content.append("\\end{table}")
        latex_content.append("")
        
        # Table 2: Blue Team Comparison
        latex_content.append("% Table 2: Blue Team Mode Comparison")
        latex_content.append("\\begin{table}[h]")
        latex_content.append("\\centering")
        latex_content.append("\\caption{Blue Team Mode Comparison}")
        latex_content.append("\\begin{tabular}{lcccc}")
        latex_content.append("\\hline")
        latex_content.append("Mode & F1 Score & Precision & Recall & n \\\\")
        latex_content.append("\\hline")
        
        for mode, stats in results.summary_tables["blue_team_comparison"]["groups"].items():
            latex_content.append(
                f"{mode} & "
                f"{stats['f1_score']['mean']:.2f} $\\pm$ {stats['f1_score']['std']:.2f} & "
                f"{stats['precision']['mean']:.2f} $\\pm$ {stats['precision']['std']:.2f} & "
                f"{stats['recall']['mean']:.2f} $\\pm$ {stats['recall']['std']:.2f} & "
                f"{stats['n']} \\\\"
            )
        
        latex_content.append("\\hline")
        latex_content.append("\\end{tabular}")
        latex_content.append("\\end{table}")
        latex_content.append("")
        
        # Table 3: Ground Truth Validation
        gt = results.summary_tables["ground_truth_validation"]
        latex_content.append("% Table 3: Ground Truth Validation")
        latex_content.append("\\begin{table}[h]")
        latex_content.append("\\centering")
        latex_content.append("\\caption{Ground Truth Validation (Red Team Manifest Accuracy)}")
        latex_content.append("\\begin{tabular}{lc}")
        latex_content.append("\\hline")
        latex_content.append("Metric & Value \\\\")
        latex_content.append("\\hline")
        latex_content.append(f"Manifest Accuracy & {gt['manifest_accuracy']['mean']:.1%} $\\pm$ {gt['manifest_accuracy']['std']:.1%} \\\\")
        latex_content.append(f"Hallucination Rate & {gt['hallucination_rate']['mean']:.1%} $\\pm$ {gt['hallucination_rate']['std']:.1%} \\\\")
        latex_content.append(f"Games with Validation & {gt['games_with_validation']} / {gt['total_games']} \\\\")
        latex_content.append("\\hline")
        latex_content.append("\\end{tabular}")
        latex_content.append("\\end{table}")
        
        (output_dir / "tables.tex").write_text("\n".join(latex_content))
    
    def _save_markdown_tables(self, results: ExperimentResults, output_dir: Path) -> None:
        """Save tables in Markdown format for README/documentation."""
        md_content = []
        
        md_content.append("# Experiment Results\n")
        md_content.append(f"Generated: {results.timestamp}\n")
        
        # Table 1: Red Team Comparison
        md_content.append("## Red Team Mode Comparison\n")
        md_content.append("| Mode | Evasion Rate | Precision | Recall | n |")
        md_content.append("|------|--------------|-----------|--------|---|")
        
        for mode, stats in results.summary_tables["red_team_comparison"]["groups"].items():
            md_content.append(
                f"| {mode} | "
                f"{stats['evasion_rate']['mean']:.2f} ± {stats['evasion_rate']['std']:.2f} | "
                f"{stats['precision']['mean']:.2f} ± {stats['precision']['std']:.2f} | "
                f"{stats['recall']['mean']:.2f} ± {stats['recall']['std']:.2f} | "
                f"{stats['n']} |"
            )
        
        md_content.append("")
        
        # Table 2: Blue Team Comparison
        md_content.append("## Blue Team Mode Comparison\n")
        md_content.append("| Mode | F1 Score | Precision | Recall | n |")
        md_content.append("|------|----------|-----------|--------|---|")
        
        for mode, stats in results.summary_tables["blue_team_comparison"]["groups"].items():
            md_content.append(
                f"| {mode} | "
                f"{stats['f1_score']['mean']:.2f} ± {stats['f1_score']['std']:.2f} | "
                f"{stats['precision']['mean']:.2f} ± {stats['precision']['std']:.2f} | "
                f"{stats['recall']['mean']:.2f} ± {stats['recall']['std']:.2f} | "
                f"{stats['n']} |"
            )
        
        md_content.append("")
        
        # Table 3: Ground Truth Validation  
        gt = results.summary_tables["ground_truth_validation"]
        md_content.append("## Ground Truth Validation\n")
        md_content.append("| Metric | Value |")
        md_content.append("|--------|-------|")
        md_content.append(f"| Manifest Accuracy | {gt['manifest_accuracy']['mean']:.1%} ± {gt['manifest_accuracy']['std']:.1%} |")
        md_content.append(f"| Hallucination Rate | {gt['hallucination_rate']['mean']:.1%} ± {gt['hallucination_rate']['std']:.1%} |")
        md_content.append(f"| Games with Validation | {gt['games_with_validation']} / {gt['total_games']} |")
        
        (output_dir / "results.md").write_text("\n".join(md_content))


def main():
    parser = argparse.ArgumentParser(
        description="Run comparative experiments for adversarial IaC evaluation"
    )
    parser.add_argument(
        "--scenarios", "-n",
        type=int,
        default=10,
        help="Number of scenarios per condition (default: 10)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="results/experiments",
        help="Output directory for results"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test mode (fewer conditions)"
    )
    parser.add_argument(
        "--red-model",
        type=str,
        default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        help="Model for Red Team"
    )
    parser.add_argument(
        "--blue-model",
        type=str,
        default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        help="Model for Blue Team"
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable static tools (Trivy/Checkov)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Build experiment config
    if args.quick:
        # Quick test: fewer conditions
        config = ExperimentConfig(
            name="quick_test",
            description="Quick test run with reduced conditions",
            red_team_modes=["single"],
            blue_team_modes=["single"],
            verification_modes=["standard"],
            scenarios_per_condition=args.scenarios,
            red_model=args.red_model,
            blue_model=args.blue_model,
            use_static_tools=not args.no_tools,
        )
    else:
        # Full comparative experiment
        config = ExperimentConfig(
            name="comparative_study",
            description="Full comparative study of Red/Blue team modes",
            red_team_modes=["single", "pipeline"],
            blue_team_modes=["single", "ensemble"],
            verification_modes=["standard", "debate"],
            scenarios_per_condition=args.scenarios,
            red_model=args.red_model,
            blue_model=args.blue_model,
            use_static_tools=not args.no_tools,
        )
    
    # Run experiment
    experiment = ComparativeExperiment(config, output_dir=args.output)
    
    print(f"\n{'='*60}")
    print(f"ADVERSARIAL IAC COMPARATIVE EXPERIMENT")
    print(f"{'='*60}")
    print(f"Experiment: {config.name}")
    print(f"Red Team modes: {config.red_team_modes}")
    print(f"Blue Team modes: {config.blue_team_modes}")
    print(f"Verification modes: {config.verification_modes}")
    print(f"Scenarios per condition: {config.scenarios_per_condition}")
    print(f"Static tools: {'enabled' if config.use_static_tools else 'disabled'}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")
    
    results = asyncio.run(experiment.run())
    
    # Print summary
    print(f"\n{'='*60}")
    print("EXPERIMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Total games: {len(results.all_games)}")
    
    overall = results.summary_tables["overall_statistics"]
    print(f"Overall F1: {overall['overall_f1']['mean']:.2f} ± {overall['overall_f1']['std']:.2f}")
    print(f"Overall Evasion: {overall['overall_evasion']['mean']:.2f} ± {overall['overall_evasion']['std']:.2f}")
    
    gt = results.summary_tables["ground_truth_validation"]
    if gt["games_with_validation"] > 0:
        print(f"Manifest Accuracy: {gt['manifest_accuracy']['mean']:.1%} ± {gt['manifest_accuracy']['std']:.1%}")
    
    print(f"\nResults saved to: {args.output}")
    print("  - full_results.json (raw data)")
    print("  - tables.tex (LaTeX for paper)")
    print("  - results.md (Markdown summary)")


if __name__ == "__main__":
    main()
