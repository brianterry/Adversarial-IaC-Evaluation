#!/usr/bin/env python3
"""
Run a full-scale experiment for paper publication.

This script runs multiple games across:
- Multiple models (as Red and Blue team)
- Multiple difficulty levels
- Multiple scenario domains
- Multiple repetitions (for statistical significance)

Usage:
    python scripts/run_full_experiment.py --dry-run  # Preview what will run
    python scripts/run_full_experiment.py            # Run full experiment
    python scripts/run_full_experiment.py --limit 10 # Run limited games
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from itertools import product

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.game.engine import GameEngine, GameConfig
from src.game.scenarios import ScenarioGenerator

# =============================================================================
# EXPERIMENT CONFIGURATION - Modify for your paper
# =============================================================================

# Models to evaluate (must be available in your Bedrock region)
MODELS = [
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "amazon.nova-pro-v1:0",
    # Add more models as needed:
    # "amazon.nova-lite-v1:0",
    # "meta.llama3-70b-instruct-v1:0",
]

# Difficulty levels
DIFFICULTIES = ["easy", "medium", "hard"]

# Scenario domains to test
DOMAINS = ["storage", "compute", "network", "iam", "multi_service"]

# Number of scenarios per domain
SCENARIOS_PER_DOMAIN = 2

# Number of repetitions per configuration (for variance estimation)
REPETITIONS = 3

# Experiment types
RUN_SYMMETRIC = True      # Same model attacks and defends
RUN_ASYMMETRIC = True     # Different models attack vs defend

# Output settings
OUTPUT_DIR = project_root / "experiments" / f"full_exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
AWS_REGION = "us-east-1"

# =============================================================================


def estimate_experiment_size():
    """Calculate how many games will be run."""
    n_scenarios = len(DOMAINS) * SCENARIOS_PER_DOMAIN
    
    symmetric_games = 0
    if RUN_SYMMETRIC:
        symmetric_games = len(MODELS) * len(DIFFICULTIES) * n_scenarios * REPETITIONS
    
    asymmetric_games = 0
    if RUN_ASYMMETRIC:
        # All model pairs (excluding same-model which is symmetric)
        n_pairs = len(MODELS) * (len(MODELS) - 1)
        asymmetric_games = n_pairs * len(DIFFICULTIES) * n_scenarios * REPETITIONS
    
    total = symmetric_games + asymmetric_games
    
    return {
        "n_models": len(MODELS),
        "n_difficulties": len(DIFFICULTIES),
        "n_scenarios": n_scenarios,
        "n_repetitions": REPETITIONS,
        "symmetric_games": symmetric_games,
        "asymmetric_games": asymmetric_games,
        "total_games": total,
        "estimated_time_hours": total * 1.5 / 60,  # ~1.5 min per game
        "estimated_cost_usd": total * 0.15,  # ~$0.15 per game
    }


def generate_experiment_configs():
    """Generate all game configurations for the experiment."""
    configs = []
    
    # Generate scenarios
    scenario_gen = ScenarioGenerator(
        cloud_providers=["aws"],
        languages=["terraform"],
    )
    scenarios = scenario_gen.generate_scenarios(
        domains=DOMAINS,
        scenarios_per_domain=SCENARIOS_PER_DOMAIN,
    )
    
    # Symmetric experiments (same model attacks and defends)
    if RUN_SYMMETRIC:
        for model in MODELS:
            for difficulty in DIFFICULTIES:
                for scenario in scenarios:
                    for rep in range(REPETITIONS):
                        configs.append({
                            "type": "symmetric",
                            "red_model": model,
                            "blue_model": model,
                            "difficulty": difficulty,
                            "scenario": scenario,
                            "repetition": rep + 1,
                        })
    
    # Asymmetric experiments (different models)
    if RUN_ASYMMETRIC:
        for red_model, blue_model in product(MODELS, MODELS):
            if red_model == blue_model:
                continue  # Skip symmetric (already covered)
            for difficulty in DIFFICULTIES:
                for scenario in scenarios:
                    for rep in range(REPETITIONS):
                        configs.append({
                            "type": "asymmetric",
                            "red_model": red_model,
                            "blue_model": blue_model,
                            "difficulty": difficulty,
                            "scenario": scenario,
                            "repetition": rep + 1,
                        })
    
    return configs


async def run_experiment(configs: list, limit: int = None):
    """Run the full experiment."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save experiment config
    exp_config = {
        "start_time": datetime.now().isoformat(),
        "models": MODELS,
        "difficulties": DIFFICULTIES,
        "domains": DOMAINS,
        "total_configs": len(configs),
        "limit": limit,
    }
    (OUTPUT_DIR / "experiment_config.json").write_text(json.dumps(exp_config, indent=2))
    
    # Initialize engine
    engine = GameEngine(output_dir=str(OUTPUT_DIR / "games"), region=AWS_REGION)
    
    results = []
    configs_to_run = configs[:limit] if limit else configs
    
    print(f"\n{'='*60}")
    print(f"RUNNING EXPERIMENT: {len(configs_to_run)} games")
    print(f"Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")
    
    for i, config in enumerate(configs_to_run, 1):
        print(f"\n[{i}/{len(configs_to_run)}] {config['type'].upper()}")
        print(f"  Red:  {config['red_model'].split('.')[-1][:25]}")
        print(f"  Blue: {config['blue_model'].split('.')[-1][:25]}")
        print(f"  Difficulty: {config['difficulty']}, Rep: {config['repetition']}")
        
        try:
            game_config = GameConfig(
                red_model=config["red_model"],
                blue_model=config["blue_model"],
                difficulty=config["difficulty"],
                language="terraform",
                cloud_provider="aws",
                detection_mode="llm_only",
                region=AWS_REGION,
            )
            
            result = await engine.run_game(config["scenario"], game_config)
            engine._save_game_result(result)
            
            results.append({
                "game_id": result.game_id,
                "type": config["type"],
                "red_model": config["red_model"],
                "blue_model": config["blue_model"],
                "difficulty": config["difficulty"],
                "domain": config["scenario"].domain,
                "repetition": config["repetition"],
                "precision": result.scoring.precision,
                "recall": result.scoring.recall,
                "f1_score": result.scoring.f1_score,
                "evasion_rate": result.scoring.evasion_rate,
                "red_vulns": len(result.red_output.manifest),
                "blue_findings": len(result.blue_output.findings),
            })
            
            print(f"  ✓ F1={result.scoring.f1_score:.2%}, Evasion={result.scoring.evasion_rate:.2%}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "game_id": None,
                "type": config["type"],
                "error": str(e),
            })
        
        # Save intermediate results
        if i % 10 == 0:
            (OUTPUT_DIR / "results_partial.json").write_text(json.dumps(results, indent=2))
    
    # Save final results
    exp_config["end_time"] = datetime.now().isoformat()
    exp_config["completed_games"] = len([r for r in results if r.get("game_id")])
    (OUTPUT_DIR / "experiment_config.json").write_text(json.dumps(exp_config, indent=2))
    
    (OUTPUT_DIR / "experiment_summary.json").write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_games": len(results),
        "successful_games": len([r for r in results if r.get("game_id")]),
        "results": results,
    }, indent=2))
    
    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Results saved to: {OUTPUT_DIR}")
    print(f"{'='*60}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Run full-scale adversarial IaC experiment")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")
    parser.add_argument("--limit", type=int, help="Limit number of games to run")
    args = parser.parse_args()
    
    # Show experiment size
    stats = estimate_experiment_size()
    print("\n" + "="*60)
    print("EXPERIMENT CONFIGURATION")
    print("="*60)
    print(f"Models: {stats['n_models']}")
    print(f"Difficulties: {stats['n_difficulties']}")
    print(f"Scenarios: {stats['n_scenarios']}")
    print(f"Repetitions: {stats['n_repetitions']}")
    print(f"\nSymmetric games: {stats['symmetric_games']}")
    print(f"Asymmetric games: {stats['asymmetric_games']}")
    print(f"TOTAL GAMES: {stats['total_games']}")
    print(f"\nEstimated time: {stats['estimated_time_hours']:.1f} hours")
    print(f"Estimated cost: ${stats['estimated_cost_usd']:.2f}")
    print("="*60)
    
    if args.dry_run:
        print("\n[DRY RUN] No games will be executed.")
        configs = generate_experiment_configs()
        print(f"\nGenerated {len(configs)} configurations.")
        print("\nFirst 5 configs:")
        for c in configs[:5]:
            print(f"  - {c['type']}: {c['difficulty']}, {c['scenario'].domain}")
        return
    
    # Confirm before running
    if not args.limit:
        confirm = input(f"\nRun {stats['total_games']} games? This will take ~{stats['estimated_time_hours']:.1f} hours. [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
    
    # Run experiment
    configs = generate_experiment_configs()
    asyncio.run(run_experiment(configs, limit=args.limit))


if __name__ == "__main__":
    main()
