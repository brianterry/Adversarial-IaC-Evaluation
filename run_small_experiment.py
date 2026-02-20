#!/usr/bin/env python3
"""
Run the small experiment configuration.

This script runs ~20 adversarial games and generates results for analysis.

Usage:
    python run_small_experiment.py
    python run_small_experiment.py --dry-run
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.game.engine import GameEngine, GameConfig, GameResult
from src.game.scenarios import Scenario, ScenarioGenerator

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Experiment")


def load_config(config_path: str = "config/experiment_small.yaml") -> dict:
    """Load experiment configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def generate_game_configs(config: dict) -> list:
    """Generate all game configurations from experiment config."""
    games = []
    
    models = config["models"]
    difficulties = config["difficulty_levels"]
    languages = config["languages"]
    cloud_providers = config["cloud_providers"]
    scenarios_config = config["scenarios"]
    experiments = config["experiments"]
    
    # Get scenarios
    scenarios = []
    if "specific_scenarios" in scenarios_config:
        for s in scenarios_config["specific_scenarios"]:
            scenarios.append(Scenario(
                id=f"S-{len(scenarios)+1}",
                domain=s["domain"],
                description=s["description"],
                cloud_provider=cloud_providers[0],
                language=languages[0],
                difficulty="medium",  # Will be overridden
                requirements=[],
                metadata={},
            ))
    
    # Symmetric experiments (same model attacks and defends)
    if experiments.get("symmetric", {}).get("enabled", False):
        for model in models:
            for scenario in scenarios:
                for difficulty in difficulties:
                    for language in languages:
                        games.append({
                            "type": "symmetric",
                            "red_model": model["id"],
                            "blue_model": model["id"],
                            "model_name": model["name"],
                            "scenario": scenario,
                            "difficulty": difficulty,
                            "language": language,
                            "cloud_provider": cloud_providers[0],
                        })
    
    # Asymmetric experiments (different models)
    if experiments.get("asymmetric", {}).get("enabled", False):
        for pair in experiments["asymmetric"].get("model_pairs", []):
            red_model = pair["red"]
            blue_model = pair["blue"]
            
            # Find model names
            red_name = next((m["name"] for m in models if m["id"] == red_model), "Unknown")
            blue_name = next((m["name"] for m in models if m["id"] == blue_model), "Unknown")
            
            for scenario in scenarios:
                for difficulty in difficulties:
                    for language in languages:
                        games.append({
                            "type": "asymmetric",
                            "red_model": red_model,
                            "blue_model": blue_model,
                            "red_name": red_name,
                            "blue_name": blue_name,
                            "scenario": scenario,
                            "difficulty": difficulty,
                            "language": language,
                            "cloud_provider": cloud_providers[0],
                        })
    
    return games


@click.command()
@click.option("--config", "-c", default="config/experiment_small.yaml", help="Config file")
@click.option("--dry-run", is_flag=True, help="Show what would run without executing")
@click.option("--limit", "-n", type=int, default=None, help="Limit number of games")
def main(config: str, dry_run: bool, limit: int):
    """Run the adversarial IaC evaluation experiment."""
    
    # Load config
    exp_config = load_config(config)
    
    console.print(Panel.fit(
        f"[bold]{exp_config['experiment']['name']}[/]\n"
        f"{exp_config['experiment']['description']}",
        title="🧪 Experiment Configuration",
    ))
    
    # Generate game configs
    games = generate_game_configs(exp_config)
    
    if limit:
        games = games[:limit]
    
    # Show summary
    console.print(f"\n[bold]Total games to run:[/] {len(games)}")
    
    # Group by type
    symmetric = [g for g in games if g["type"] == "symmetric"]
    asymmetric = [g for g in games if g["type"] == "asymmetric"]
    
    table = Table(title="Experiment Matrix")
    table.add_column("Type")
    table.add_column("Games")
    table.add_column("Description")
    
    table.add_row("Symmetric", str(len(symmetric)), "Same model attacks and defends")
    table.add_row("Asymmetric", str(len(asymmetric)), "Different models compete")
    table.add_row("[bold]Total[/]", f"[bold]{len(games)}[/]", "")
    
    console.print(table)
    
    # Estimate time
    est_time_per_game = 50  # seconds
    est_total_time = len(games) * est_time_per_game
    console.print(f"\n[dim]Estimated time: {est_total_time // 60} minutes[/]")
    
    if dry_run:
        console.print("\n[yellow]Dry run - showing first 5 games:[/]")
        for i, game in enumerate(games[:5]):
            console.print(f"  {i+1}. {game['type']}: {game.get('model_name', game.get('red_name', 'Unknown'))} "
                         f"vs {game.get('model_name', game.get('blue_name', 'Unknown'))} "
                         f"| {game['difficulty']} | {game['scenario'].domain}")
        if len(games) > 5:
            console.print(f"  ... and {len(games) - 5} more")
        return
    
    # Run experiment
    console.print("\n[bold green]Starting experiment...[/]\n")
    
    asyncio.run(run_experiment(games, exp_config))


async def run_experiment(games: list, config: dict):
    """Run all games in the experiment."""
    
    output_dir = Path(config["experiment"]["output_dir"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = output_dir / f"exp_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    engine = GameEngine(output_dir=str(exp_dir / "games"))
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running games...", total=len(games))
        
        for i, game_spec in enumerate(games):
            # Update scenario difficulty
            scenario = game_spec["scenario"]
            scenario.difficulty = game_spec["difficulty"]
            scenario.language = game_spec["language"]
            
            # Create game config
            game_config = GameConfig(
                red_model=game_spec["red_model"],
                blue_model=game_spec["blue_model"],
                difficulty=game_spec["difficulty"],
                language=game_spec["language"],
                cloud_provider=game_spec["cloud_provider"],
                detection_mode="llm_only",
            )
            
            progress.update(task, description=f"Game {i+1}/{len(games)}: {scenario.domain} ({game_spec['difficulty']})")
            
            try:
                result = await engine.run_game(scenario, game_config)
                results.append({
                    "game_id": result.game_id,
                    "type": game_spec["type"],
                    "red_model": game_spec["red_model"],
                    "blue_model": game_spec["blue_model"],
                    "scenario_domain": scenario.domain,
                    "difficulty": game_spec["difficulty"],
                    "precision": result.scoring.precision,
                    "recall": result.scoring.recall,
                    "f1_score": result.scoring.f1_score,
                    "evasion_rate": result.scoring.evasion_rate,
                    "red_vulns": len(result.red_output.manifest),
                    "blue_findings": len(result.blue_output.findings),
                    "red_time": result.red_time_seconds,
                    "blue_time": result.blue_time_seconds,
                })
                
                # Save individual result
                engine._save_game_result(result)
                
            except Exception as e:
                logger.error(f"Game {i+1} failed: {e}")
                results.append({
                    "game_id": f"FAILED-{i+1}",
                    "type": game_spec["type"],
                    "error": str(e),
                })
            
            progress.advance(task)
    
    # Save experiment summary
    summary = {
        "experiment_name": config["experiment"]["name"],
        "timestamp": timestamp,
        "total_games": len(games),
        "successful_games": len([r for r in results if "error" not in r]),
        "failed_games": len([r for r in results if "error" in r]),
        "results": results,
    }
    
    # Calculate aggregate metrics
    successful = [r for r in results if "error" not in r]
    if successful:
        summary["aggregate_metrics"] = {
            "mean_precision": sum(r["precision"] for r in successful) / len(successful),
            "mean_recall": sum(r["recall"] for r in successful) / len(successful),
            "mean_f1": sum(r["f1_score"] for r in successful) / len(successful),
            "mean_evasion_rate": sum(r["evasion_rate"] for r in successful) / len(successful),
        }
    
    (exp_dir / "experiment_summary.json").write_text(json.dumps(summary, indent=2))
    
    # Display results
    console.print("\n[bold green]✓ Experiment Complete![/]\n")
    
    # Results table
    table = Table(title="Game Results")
    table.add_column("Game", style="cyan")
    table.add_column("Type")
    table.add_column("Domain")
    table.add_column("Difficulty")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1", justify="right")
    table.add_column("Evasion", justify="right")
    
    for r in successful[:10]:  # Show first 10
        table.add_row(
            r["game_id"],
            r["type"][:3],
            r["scenario_domain"][:8],
            r["difficulty"],
            f"{r['precision']:.0%}",
            f"{r['recall']:.0%}",
            f"{r['f1_score']:.0%}",
            f"{r['evasion_rate']:.0%}",
        )
    
    if len(successful) > 10:
        table.add_row("...", "", "", "", "", "", "", "")
    
    console.print(table)
    
    # Aggregate metrics
    if "aggregate_metrics" in summary:
        metrics = summary["aggregate_metrics"]
        console.print(f"\n[bold]Aggregate Metrics:[/]")
        console.print(f"  Mean Precision: {metrics['mean_precision']:.2%}")
        console.print(f"  Mean Recall: {metrics['mean_recall']:.2%}")
        console.print(f"  Mean F1 Score: {metrics['mean_f1']:.2%}")
        console.print(f"  Mean Evasion Rate: {metrics['mean_evasion_rate']:.2%}")
    
    console.print(f"\n[dim]Results saved to {exp_dir}[/]")


if __name__ == "__main__":
    main()
