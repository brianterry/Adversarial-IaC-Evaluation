"""
Command-line interface for Adversarial IaC Evaluation.

Usage:
    adversarial-iac red-team --scenario "Create S3 bucket" --difficulty medium
    adversarial-iac game --red-model claude --blue-model nova --scenario "..."
    adversarial-iac experiment --config config.yaml
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.syntax import Syntax

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.red_team_agent import RedTeamAgent, Difficulty, create_red_team_agent
from src.agents.blue_team_agent import BlueTeamAgent, DetectionMode, create_blue_team_agent
from src.game.scenarios import ScenarioGenerator

# Load environment variables
load_dotenv()

# Setup console
console = Console()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("AdversarialIaC")


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Adversarial IaC Evaluation - Red Team vs Blue Team security testing"""
    pass


@cli.command()
@click.option(
    "--scenario",
    "-s",
    required=True,
    help="Scenario description (e.g., 'Create S3 bucket for PHI data')",
)
@click.option(
    "--difficulty",
    "-d",
    type=click.Choice(["easy", "medium", "hard"]),
    default="medium",
    help="Vulnerability injection difficulty",
)
@click.option(
    "--model",
    "-m",
    default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    help="Bedrock model ID",
)
@click.option(
    "--cloud-provider",
    "-c",
    type=click.Choice(["aws", "azure", "gcp"]),
    default="aws",
    help="Target cloud provider",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["terraform", "cloudformation"]),
    default="terraform",
    help="IaC language",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="output/red-team",
    help="Output directory",
)
@click.option("--region", default="us-east-1", help="AWS region")
def red_team(
    scenario: str,
    difficulty: str,
    model: str,
    cloud_provider: str,
    language: str,
    output_dir: str,
    region: str,
):
    """
    Run Red Team Agent to generate adversarial IaC.
    
    The Red Team attempts to create plausible IaC code with hidden
    security vulnerabilities that are difficult to detect.
    """
    console.print(
        Panel.fit(
            "[bold red]🔴 RED TEAM ATTACK[/]\n"
            f"Scenario: {scenario}\n"
            f"Difficulty: {difficulty}\n"
            f"Model: {model}",
            title="Adversarial IaC Generation",
        )
    )
    
    try:
        # Run the async function
        asyncio.run(
            _run_red_team(
                scenario=scenario,
                difficulty=difficulty,
                model=model,
                cloud_provider=cloud_provider,
                language=language,
                output_dir=output_dir,
                region=region,
            )
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise click.Abort()


async def _run_red_team(
    scenario: str,
    difficulty: str,
    model: str,
    cloud_provider: str,
    language: str,
    output_dir: str,
    region: str,
):
    """Async implementation of red team command."""
    
    # Create output directory
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_path / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create scenario
    scenario_gen = ScenarioGenerator(
        cloud_providers=[cloud_provider],
        languages=[language],
    )
    test_scenario = scenario_gen.generate_single_scenario(
        description=scenario,
        cloud_provider=cloud_provider,
        language=language,
        difficulty=difficulty,
    )
    
    # Create Red Team agent
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing Red Team Agent...", total=None)
        
        agent = create_red_team_agent(
            model_id=model,
            region=region,
            difficulty=difficulty,
            cloud_provider=cloud_provider,
            language=language,
        )
        
        progress.update(task, description="Executing adversarial attack...")
        
        # Execute attack
        output = await agent.execute(test_scenario.to_dict())
        
        progress.update(task, description="Saving results...")
    
    # Display results
    console.print("\n[bold green]✓ Attack Complete[/]\n")
    
    # Show generated code
    for filename, content in output.code.items():
        console.print(f"[bold]{filename}[/]")
        syntax = Syntax(
            content[:1000] + ("..." if len(content) > 1000 else ""),
            "hcl" if language == "terraform" else "yaml",
            theme="monokai",
            line_numbers=True,
        )
        console.print(syntax)
        console.print()
        
        # Save file
        (run_dir / filename).write_text(content)
    
    # Show vulnerability manifest
    if output.manifest:
        table = Table(title="Injected Vulnerabilities (Ground Truth)")
        table.add_column("ID", style="cyan")
        table.add_column("Resource", style="magenta")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Stealth Technique")
        
        for vuln in output.manifest:
            table.add_row(
                vuln.vuln_id,
                vuln.resource_name,
                vuln.type,
                vuln.severity,
                vuln.stealth_technique[:30] + "..." if len(vuln.stealth_technique) > 30 else vuln.stealth_technique,
            )
        
        console.print(table)
        
        # Save manifest
        manifest_data = [
            {
                "vuln_id": v.vuln_id,
                "rule_id": v.rule_id,
                "title": v.title,
                "type": v.type,
                "severity": v.severity,
                "resource_name": v.resource_name,
                "resource_type": v.resource_type,
                "line_number_estimate": v.line_number_estimate,
                "vulnerable_attribute": v.vulnerable_attribute,
                "vulnerable_value": v.vulnerable_value,
                "stealth_technique": v.stealth_technique,
                "detection_hint": v.detection_hint,
            }
            for v in output.manifest
        ]
        (run_dir / "vulnerability_manifest.json").write_text(
            json.dumps(manifest_data, indent=2)
        )
    
    # Summary
    console.print(f"\n[bold]Summary:[/]")
    console.print(f"  Difficulty: {output.difficulty.value}")
    console.print(f"  Vulnerabilities Injected: {len(output.manifest)}")
    console.print(f"  Stealth Score: {'✓ Passed' if output.stealth_score else '✗ Failed'}")
    console.print(f"  Output: {run_dir}")
    
    # Save metadata
    metadata = {
        "scenario": test_scenario.to_dict(),
        "agent_config": agent.to_dict(),
        "stats": output.generation_stats,
        "stealth_score": output.stealth_score,
        "timestamp": timestamp,
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))


@cli.command()
@click.option(
    "--domains",
    "-d",
    multiple=True,
    default=["storage", "compute", "network"],
    help="Domains to generate scenarios for",
)
@click.option(
    "--count",
    "-n",
    default=2,
    help="Number of scenarios per domain",
)
def scenarios(domains: tuple, count: int):
    """List available test scenarios."""
    
    generator = ScenarioGenerator()
    
    # Get matrix
    matrix = generator.get_scenario_matrix()
    
    console.print(Panel.fit(
        f"[bold]Scenario Space[/]\n"
        f"Domains: {', '.join(matrix['domains'])}\n"
        f"Providers: {', '.join(matrix['cloud_providers'])}\n"
        f"Languages: {', '.join(matrix['languages'])}\n"
        f"Difficulties: {', '.join(matrix['difficulty_levels'])}\n"
        f"[bold]Total Combinations: {matrix['total_combinations']}[/]",
        title="Available Scenarios",
    ))
    
    # Show scenarios by domain
    from src.prompts import ScenarioTemplates
    
    for domain in domains:
        table = Table(title=f"Domain: {domain}")
        table.add_column("Index", style="cyan")
        table.add_column("Description")
        
        scenarios_list = ScenarioTemplates.SCENARIOS.get(domain, [])
        for i, desc in enumerate(scenarios_list[:count]):
            table.add_row(str(i), desc)
        
        console.print(table)
        console.print()


@cli.command()
@click.option(
    "--input-dir",
    "-i",
    type=click.Path(exists=True),
    required=True,
    help="Directory containing Red Team output (code files)",
)
@click.option(
    "--model",
    "-m",
    default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    help="Bedrock model ID for analysis",
)
@click.option(
    "--mode",
    type=click.Choice(["llm_only", "tools_only", "hybrid"]),
    default="llm_only",
    help="Detection mode",
)
@click.option(
    "--use-trivy",
    is_flag=True,
    help="Enable Trivy scanner (requires trivy installed)",
)
@click.option(
    "--use-checkov",
    is_flag=True,
    help="Enable Checkov scanner (requires checkov installed)",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["terraform", "cloudformation"]),
    default="terraform",
    help="IaC language",
)
@click.option("--region", default="us-east-1", help="AWS region")
def blue_team(
    input_dir: str,
    model: str,
    mode: str,
    use_trivy: bool,
    use_checkov: bool,
    language: str,
    region: str,
):
    """
    Run Blue Team Agent to detect vulnerabilities in IaC.
    
    The Blue Team analyzes code generated by Red Team and attempts
    to detect all security vulnerabilities.
    """
    console.print(
        Panel.fit(
            "[bold blue]🔵 BLUE TEAM DEFENSE[/]\n"
            f"Input: {input_dir}\n"
            f"Mode: {mode}\n"
            f"Model: {model}",
            title="Security Analysis",
        )
    )
    
    try:
        asyncio.run(
            _run_blue_team(
                input_dir=input_dir,
                model=model,
                mode=mode,
                use_trivy=use_trivy,
                use_checkov=use_checkov,
                language=language,
                region=region,
            )
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise click.Abort()


async def _run_blue_team(
    input_dir: str,
    model: str,
    mode: str,
    use_trivy: bool,
    use_checkov: bool,
    language: str,
    region: str,
):
    """Async implementation of blue team command."""
    
    input_path = Path(input_dir)
    
    # Read code files from input directory
    code = {}
    for ext in ["tf", "yaml", "json"]:
        for filepath in input_path.glob(f"*.{ext}"):
            if filepath.name not in ["metadata.json", "vulnerability_manifest.json"]:
                code[filepath.name] = filepath.read_text()
    
    if not code:
        console.print("[red]No code files found in input directory[/]")
        return
    
    console.print(f"[dim]Found {len(code)} code files: {list(code.keys())}[/]\n")
    
    # Create output directory
    output_path = Path("output/blue-team")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_path / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create Blue Team agent
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing Blue Team Agent...", total=None)
        
        agent = create_blue_team_agent(
            model_id=model,
            region=region,
            mode=mode,
            language=language,
            use_trivy=use_trivy,
            use_checkov=use_checkov,
        )
        
        progress.update(task, description="Analyzing code for vulnerabilities...")
        
        # Execute analysis
        output = await agent.execute(code)
        
        progress.update(task, description="Saving results...")
    
    # Display results
    console.print("\n[bold green]✓ Analysis Complete[/]\n")
    
    # Show findings
    if output.findings:
        table = Table(title="Detected Vulnerabilities")
        table.add_column("ID", style="cyan")
        table.add_column("Resource", style="magenta")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Title")
        table.add_column("Source", style="dim")
        
        for finding in output.findings:
            severity_color = {
                "critical": "bold red",
                "high": "red",
                "medium": "yellow",
                "low": "green",
            }.get(finding.severity.lower(), "white")
            
            table.add_row(
                finding.finding_id,
                finding.resource_name[:25] + "..." if len(finding.resource_name) > 25 else finding.resource_name,
                finding.vulnerability_type,
                f"[{severity_color}]{finding.severity}[/]",
                finding.title[:40] + "..." if len(finding.title) > 40 else finding.title,
                finding.source,
            )
        
        console.print(table)
        
        # Save findings
        findings_data = [
            {
                "finding_id": f.finding_id,
                "resource_name": f.resource_name,
                "resource_type": f.resource_type,
                "vulnerability_type": f.vulnerability_type,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "evidence": f.evidence,
                "line_number_estimate": f.line_number_estimate,
                "confidence": f.confidence,
                "reasoning": f.reasoning,
                "remediation": f.remediation,
                "source": f.source,
            }
            for f in output.findings
        ]
        (run_dir / "findings.json").write_text(json.dumps(findings_data, indent=2))
    else:
        console.print("[yellow]No vulnerabilities detected[/]")
    
    # Summary
    summary = output.analysis_summary
    console.print(f"\n[bold]Summary:[/]")
    console.print(f"  Mode: {mode}")
    console.print(f"  Resources Analyzed: {summary.get('total_resources_analyzed', 'N/A')}")
    console.print(f"  Total Findings: {len(output.findings)}")
    console.print(f"  Risk Assessment: {summary.get('risk_assessment', 'N/A')}")
    console.print(f"  Output: {run_dir}")
    
    # Show severity breakdown
    by_severity = output.detection_stats.get("by_severity", {})
    if any(by_severity.values()):
        console.print(f"\n[bold]By Severity:[/]")
        for sev, count in by_severity.items():
            if count > 0:
                console.print(f"  {sev.capitalize()}: {count}")
    
    # Save metadata
    metadata = {
        "input_dir": str(input_path),
        "agent_config": agent.to_dict(),
        "analysis_summary": summary,
        "detection_stats": output.detection_stats,
        "timestamp": timestamp,
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    
    # Check if ground truth exists for comparison
    manifest_path = input_path / "vulnerability_manifest.json"
    if manifest_path.exists():
        console.print(f"\n[dim]Ground truth manifest found at {manifest_path}[/]")
        console.print("[dim]Use 'adversarial-iac score' to compare findings vs ground truth[/]")


@cli.command()
@click.option(
    "--red-dir",
    "-r",
    type=click.Path(exists=True),
    required=True,
    help="Directory containing Red Team output (with vulnerability_manifest.json)",
)
@click.option(
    "--blue-dir",
    "-b",
    type=click.Path(exists=True),
    required=True,
    help="Directory containing Blue Team output (with findings.json)",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="output/scoring",
    help="Output directory for scoring results",
)
def score(red_dir: str, blue_dir: str, output_dir: str):
    """
    Score Blue Team findings against Red Team ground truth.
    
    Calculates precision, recall, F1, and evasion rate.
    """
    from src.agents.judge_agent import JudgeAgent, score_results_to_dict
    
    console.print(
        Panel.fit(
            "[bold yellow]⚖️ JUDGE SCORING[/]\n"
            f"Red Team: {red_dir}\n"
            f"Blue Team: {blue_dir}",
            title="Match Scoring",
        )
    )
    
    red_path = Path(red_dir)
    blue_path = Path(blue_dir)
    
    # Load Red Team manifest
    manifest_file = red_path / "vulnerability_manifest.json"
    if not manifest_file.exists():
        console.print("[red]Error: vulnerability_manifest.json not found in Red Team directory[/]")
        raise click.Abort()
    
    red_manifest = json.loads(manifest_file.read_text())
    
    # Load Blue Team findings
    findings_file = blue_path / "findings.json"
    if not findings_file.exists():
        console.print("[red]Error: findings.json not found in Blue Team directory[/]")
        raise click.Abort()
    
    blue_findings = json.loads(findings_file.read_text())
    
    console.print(f"[dim]Red Team vulnerabilities: {len(red_manifest)}[/]")
    console.print(f"[dim]Blue Team findings: {len(blue_findings)}[/]\n")
    
    # Run scoring
    judge = JudgeAgent()
    result = judge.score(red_manifest, blue_findings)
    
    # Display results
    console.print("[bold]Match Results:[/]\n")
    
    # Matches table
    table = Table(title="Vulnerability Matches")
    table.add_column("Red ID", style="red")
    table.add_column("Blue ID", style="blue")
    table.add_column("Match Type", style="yellow")
    table.add_column("Confidence")
    table.add_column("Explanation")
    
    for match in result.matches:
        match_color = {
            "exact": "green",
            "partial": "yellow",
            "missed": "red",
        }.get(match.match_type, "white")
        
        table.add_row(
            match.red_vuln_id,
            match.blue_finding_id or "—",
            f"[{match_color}]{match.match_type}[/]",
            f"{match.confidence:.2f}" if match.blue_finding_id else "—",
            match.explanation[:50] + "..." if len(match.explanation) > 50 else match.explanation,
        )
    
    console.print(table)
    
    # Metrics
    console.print(f"\n[bold]Metrics:[/]")
    console.print(f"  [blue]Precision:[/] {result.precision:.2%} ({len(result.true_positives)} true positives)")
    console.print(f"  [blue]Recall:[/] {result.recall:.2%} ({result.total_red_vulns - len(result.false_negatives)}/{result.total_red_vulns} detected)")
    console.print(f"  [blue]F1 Score:[/] {result.f1_score:.2%}")
    console.print(f"  [red]Evasion Rate:[/] {result.evasion_rate:.2%} ({len(result.false_negatives)} evaded)")
    
    # False positives
    if result.false_positives:
        console.print(f"\n[yellow]False Positives ({len(result.false_positives)}):[/]")
        for fp_id in result.false_positives:
            console.print(f"  • {fp_id}")
    
    # Save results
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_path / f"score_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    scoring_data = score_results_to_dict(result)
    (run_dir / "scoring_results.json").write_text(json.dumps(scoring_data, indent=2))
    
    console.print(f"\n[dim]Results saved to {run_dir}[/]")


@cli.command()
@click.option(
    "--scenario",
    "-s",
    required=True,
    help="Scenario description",
)
@click.option(
    "--red-model",
    default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    help="Model for Red Team",
)
@click.option(
    "--blue-model",
    default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    help="Model for Blue Team",
)
@click.option(
    "--difficulty",
    "-d",
    type=click.Choice(["easy", "medium", "hard"]),
    default="medium",
    help="Difficulty level",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["terraform", "cloudformation"]),
    default="terraform",
    help="IaC language",
)
@click.option(
    "--cloud-provider",
    "-c",
    type=click.Choice(["aws", "azure", "gcp"]),
    default="aws",
    help="Cloud provider",
)
@click.option("--region", default="us-east-1", help="AWS region")
def game(
    scenario: str,
    red_model: str,
    blue_model: str,
    difficulty: str,
    language: str,
    cloud_provider: str,
    region: str,
):
    """
    Run a complete Red Team vs Blue Team game.
    
    Red Team generates adversarial IaC, Blue Team detects vulnerabilities,
    Judge scores the match.
    """
    console.print(
        Panel.fit(
            "[bold magenta]🎮 ADVERSARIAL GAME[/]\n"
            f"Scenario: {scenario}\n"
            f"Red Team: {red_model.split('.')[-1][:20]}\n"
            f"Blue Team: {blue_model.split('.')[-1][:20]}\n"
            f"Difficulty: {difficulty}",
            title="Game Configuration",
        )
    )
    
    try:
        asyncio.run(
            _run_game(
                scenario=scenario,
                red_model=red_model,
                blue_model=blue_model,
                difficulty=difficulty,
                language=language,
                cloud_provider=cloud_provider,
                region=region,
            )
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise click.Abort()


async def _run_game(
    scenario: str,
    red_model: str,
    blue_model: str,
    difficulty: str,
    language: str,
    cloud_provider: str,
    region: str,
):
    """Async implementation of game command."""
    from src.game.engine import GameEngine, GameConfig
    from src.game.scenarios import ScenarioGenerator
    
    # Create scenario
    scenario_gen = ScenarioGenerator(
        cloud_providers=[cloud_provider],
        languages=[language],
    )
    test_scenario = scenario_gen.generate_single_scenario(
        description=scenario,
        cloud_provider=cloud_provider,
        language=language,
        difficulty=difficulty,
    )
    
    # Create game config
    config = GameConfig(
        red_model=red_model,
        blue_model=blue_model,
        difficulty=difficulty,
        language=language,
        cloud_provider=cloud_provider,
        detection_mode="llm_only",
        region=region,
    )
    
    # Run game
    engine = GameEngine(output_dir="output/games", region=region)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running adversarial game...", total=None)
        
        result = await engine.run_game(test_scenario, config)
        
        progress.update(task, description="Game complete!")
    
    # Display results
    console.print("\n[bold green]✓ Game Complete[/]\n")
    
    # Summary
    console.print(Panel.fit(
        f"[bold]Game ID:[/] {result.game_id}\n\n"
        f"[red]🔴 Red Team:[/]\n"
        f"  • Vulnerabilities injected: {len(result.red_output.manifest)}\n"
        f"  • Stealth: {'✓ Passed' if result.red_output.stealth_score else '✗ Failed'}\n"
        f"  • Time: {result.red_time_seconds:.1f}s\n\n"
        f"[blue]🔵 Blue Team:[/]\n"
        f"  • Findings: {len(result.blue_output.findings)}\n"
        f"  • Time: {result.blue_time_seconds:.1f}s\n\n"
        f"[yellow]⚖️ Scoring:[/]\n"
        f"  • Precision: {result.scoring.precision:.2%}\n"
        f"  • Recall: {result.scoring.recall:.2%}\n"
        f"  • F1 Score: {result.scoring.f1_score:.2%}\n"
        f"  • Evasion Rate: {result.scoring.evasion_rate:.2%}",
        title="Game Results",
    ))
    
    # Match details
    table = Table(title="Match Details")
    table.add_column("Red Vuln", style="red")
    table.add_column("Blue Finding", style="blue")
    table.add_column("Result", style="yellow")
    
    for match in result.scoring.matches:
        result_icon = {
            "exact": "[green]✓ Detected[/]",
            "partial": "[yellow]~ Partial[/]",
            "missed": "[red]✗ Evaded[/]",
        }.get(match.match_type, "?")
        
        table.add_row(
            match.red_vuln_id,
            match.blue_finding_id or "—",
            result_icon,
        )
    
    console.print(table)
    
    console.print(f"\n[dim]Full results saved to output/games/{result.game_id}[/]")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="config/experiment_config.yaml",
    help="Experiment configuration file",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be run without executing",
)
def experiment(config: str, dry_run: bool):
    """Run a full adversarial evaluation experiment."""
    
    # Load config
    with open(config) as f:
        exp_config = yaml.safe_load(f)
    
    console.print(Panel.fit(
        f"[bold]{exp_config['experiment']['name']}[/]\n"
        f"{exp_config['experiment']['description']}",
        title="Experiment Configuration",
    ))
    
    # Show models
    table = Table(title="Models to Evaluate")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Provider")
    
    for model in exp_config["models"]:
        table.add_row(model["id"], model["name"], model["provider"])
    
    console.print(table)
    
    if dry_run:
        console.print("\n[yellow]Dry run - no experiments executed[/]")
        return
    
    console.print("\n[bold red]Full experiment mode not yet implemented[/]")
    console.print("Use 'game' command to run individual games")


@cli.command("compare-tools")
@click.option(
    "--experiment",
    "-e",
    "experiment_dir",
    type=click.Path(exists=True),
    required=True,
    help="Path to experiment directory (e.g., experiments/small_test/exp_20260220_125729)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for comparison results (default: tool_comparison.json in experiment dir)",
)
def compare_tools(experiment_dir: str, output: Optional[str]):
    """
    Compare LLM, Trivy, and Checkov detection on experiment results.
    
    Runs all three detection methods on the generated IaC from a previous
    experiment and compares their effectiveness.
    """
    from src.tools.trivy_runner import TrivyRunner
    from src.tools.checkov_runner import CheckovRunner
    
    exp_path = Path(experiment_dir)
    games_dir = exp_path / "games"
    
    if not games_dir.exists():
        console.print(f"[red]No games directory found at {games_dir}[/]")
        raise click.Abort()
    
    games = sorted([d for d in games_dir.iterdir() if d.is_dir()])
    
    console.print(
        Panel.fit(
            f"[bold cyan]🔧 TOOL COMPARISON[/]\n"
            f"Experiment: {exp_path.name}\n"
            f"Games: {len(games)}",
            title="Detection Method Comparison",
        )
    )
    
    # Initialize scanners
    trivy = TrivyRunner()
    checkov = CheckovRunner()
    
    results = []
    total_gt = 0
    total_llm = 0
    total_trivy = 0
    total_checkov = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Comparing tools...", total=len(games))
        
        for game_dir in games:
            game_id = game_dir.name
            progress.update(task, description=f"Analyzing {game_id}...")
            
            # Load code files
            code_files = {}
            code_dir = game_dir / "code"
            if code_dir.exists():
                for f in code_dir.glob("*.tf"):
                    code_files[f.name] = f.read_text()
            
            if not code_files:
                progress.advance(task)
                continue
            
            # Load ground truth
            manifest_file = game_dir / "red_manifest.json"
            ground_truth = 0
            if manifest_file.exists():
                manifest = json.loads(manifest_file.read_text())
                ground_truth = len(manifest)
            
            # Load LLM findings (from previous Blue Team run)
            findings_file = game_dir / "blue_findings.json"
            llm_count = 0
            if findings_file.exists():
                llm_findings = json.loads(findings_file.read_text())
                llm_count = len(llm_findings)
            
            # Run Trivy
            trivy_findings = trivy.scan(code_files)
            trivy_count = len(trivy_findings)
            
            # Run Checkov
            checkov_findings = checkov.scan(code_files, language="terraform")
            checkov_count = len(checkov_findings)
            
            results.append({
                "game": game_id,
                "ground_truth": ground_truth,
                "llm": llm_count,
                "trivy": trivy_count,
                "checkov": checkov_count,
            })
            
            total_gt += ground_truth
            total_llm += llm_count
            total_trivy += trivy_count
            total_checkov += checkov_count
            
            progress.advance(task)
    
    # Display results
    console.print("\n[bold green]✓ Comparison Complete[/]\n")
    
    # Summary table
    games_with_vulns = [r for r in results if r["ground_truth"] > 0]
    
    table = Table(title="Detection Summary")
    table.add_column("Tool", style="cyan")
    table.add_column("Total Findings", justify="right")
    table.add_column("Games Detected", justify="right")
    table.add_column("Detection Rate", justify="right")
    table.add_column("Avg/Game", justify="right")
    
    if games_with_vulns:
        llm_detected = sum(1 for r in games_with_vulns if r["llm"] > 0)
        trivy_detected = sum(1 for r in games_with_vulns if r["trivy"] > 0)
        checkov_detected = sum(1 for r in games_with_vulns if r["checkov"] > 0)
        
        table.add_row(
            "LLM",
            str(total_llm),
            f"{llm_detected}/{len(games_with_vulns)}",
            f"{llm_detected/len(games_with_vulns)*100:.1f}%",
            f"{total_llm/len(games_with_vulns):.1f}",
        )
        table.add_row(
            "Trivy",
            str(total_trivy),
            f"{trivy_detected}/{len(games_with_vulns)}",
            f"{trivy_detected/len(games_with_vulns)*100:.1f}%",
            f"{total_trivy/len(games_with_vulns):.1f}",
        )
        table.add_row(
            "Checkov",
            str(total_checkov),
            f"{checkov_detected}/{len(games_with_vulns)}",
            f"{checkov_detected/len(games_with_vulns)*100:.1f}%",
            f"{total_checkov/len(games_with_vulns):.1f}",
        )
    
    console.print(table)
    
    # Ground truth comparison
    console.print(f"\n[bold]Ground Truth:[/] {total_gt} vulnerabilities across {len(games_with_vulns)} games")
    
    # Key insights
    console.print("\n[bold]Key Insights:[/]")
    if total_trivy == 0:
        console.print("  ⚠️  Trivy found [red]zero[/] vulnerabilities - static pattern matching missed contextual issues")
    if total_llm > total_checkov:
        console.print(f"  📊 LLM found {total_llm - total_checkov} more issues than Checkov")
    if total_llm > 0 and total_checkov > 0:
        overlap_estimate = min(total_llm, total_checkov) * 0.3  # Rough estimate
        console.print(f"  🔗 Hybrid approach (LLM + Checkov) may provide complementary coverage")
    
    # Save results
    output_file = Path(output) if output else exp_path / "tool_comparison.json"
    comparison_data = {
        "timestamp": datetime.now().isoformat(),
        "experiment": str(exp_path),
        "summary": {
            "total_games": len(results),
            "games_with_vulns": len(games_with_vulns),
            "total_ground_truth": total_gt,
            "llm_total": total_llm,
            "trivy_total": total_trivy,
            "checkov_total": total_checkov,
        },
        "per_game": results,
    }
    output_file.write_text(json.dumps(comparison_data, indent=2))
    console.print(f"\n[dim]Results saved to {output_file}[/]")


@cli.command("show")
@click.option(
    "--experiment",
    "-e",
    "experiment_dir",
    type=click.Path(exists=True),
    required=True,
    help="Path to experiment directory",
)
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed per-game results",
)
def show_results(experiment_dir: str, detailed: bool):
    """
    Display results from a completed experiment.
    
    Shows aggregate metrics, per-game breakdown, and key insights.
    """
    exp_path = Path(experiment_dir)
    
    # Load experiment summary
    summary_file = exp_path / "experiment_summary.json"
    if not summary_file.exists():
        console.print(f"[red]No experiment_summary.json found in {exp_path}[/]")
        raise click.Abort()
    
    summary = json.loads(summary_file.read_text())
    
    # Get games list (support both "results" and "games" keys)
    games = summary.get("results", summary.get("games", []))
    
    # Header
    console.print(
        Panel.fit(
            f"[bold cyan]📊 EXPERIMENT RESULTS[/]\n"
            f"Name: {summary.get('experiment_name', exp_path.name)}\n"
            f"Path: {exp_path}\n"
            f"Timestamp: {summary.get('timestamp', 'N/A')}",
            title="Experiment Summary",
        )
    )
    
    # Calculate aggregate metrics from games if not present
    total_games = summary.get("total_games", len(games))
    successful_games = summary.get("successful_games", len([g for g in games if g.get("f1_score") is not None]))
    
    if games:
        valid_games = [g for g in games if g.get("f1_score") is not None]
        avg_precision = sum(g.get("precision", 0) for g in valid_games) / len(valid_games) if valid_games else 0
        avg_recall = sum(g.get("recall", 0) for g in valid_games) / len(valid_games) if valid_games else 0
        avg_f1 = sum(g.get("f1_score", 0) for g in valid_games) / len(valid_games) if valid_games else 0
        avg_evasion = sum(g.get("evasion_rate", 0) for g in valid_games) / len(valid_games) if valid_games else 0
    else:
        avg_precision = avg_recall = avg_f1 = avg_evasion = 0
    
    console.print("\n[bold]Aggregate Metrics:[/]")
    console.print(f"  Total Games:    {total_games}")
    console.print(f"  Successful:     {successful_games}")
    console.print(f"  Avg Precision:  [blue]{avg_precision:.1%}[/]")
    console.print(f"  Avg Recall:     [blue]{avg_recall:.1%}[/]")
    console.print(f"  Avg F1 Score:   [green]{avg_f1:.1%}[/]")
    console.print(f"  Avg Evasion:    [red]{avg_evasion:.1%}[/]")
    
    # By difficulty breakdown (calculate from games)
    if games:
        difficulties = {}
        for g in games:
            diff = g.get("difficulty", "unknown")
            if diff not in difficulties:
                difficulties[diff] = {"games": [], "f1_scores": [], "evasion_rates": []}
            difficulties[diff]["games"].append(g)
            if g.get("f1_score") is not None:
                difficulties[diff]["f1_scores"].append(g["f1_score"])
                difficulties[diff]["evasion_rates"].append(g.get("evasion_rate", 0))
        
        console.print("\n[bold]By Difficulty:[/]")
        table = Table()
        table.add_column("Difficulty", style="cyan")
        table.add_column("Games", justify="right")
        table.add_column("Avg F1", justify="right", style="green")
        table.add_column("Avg Evasion", justify="right", style="red")
        
        for diff in sorted(difficulties.keys()):
            stats = difficulties[diff]
            avg_f1 = sum(stats["f1_scores"]) / len(stats["f1_scores"]) if stats["f1_scores"] else 0
            avg_ev = sum(stats["evasion_rates"]) / len(stats["evasion_rates"]) if stats["evasion_rates"] else 0
            table.add_row(diff, str(len(stats["games"])), f"{avg_f1:.1%}", f"{avg_ev:.1%}")
        console.print(table)
    
    # By model breakdown (calculate from games)
    if games:
        models = {}
        for g in games:
            # Use red_model or blue_model
            model = g.get("red_model", g.get("blue_model", "unknown"))
            # Shorten model name
            short_name = model.split(".")[-1][:25] if "." in model else model[:25]
            if short_name not in models:
                models[short_name] = {"games": [], "f1_scores": []}
            models[short_name]["games"].append(g)
            if g.get("f1_score") is not None:
                models[short_name]["f1_scores"].append(g["f1_score"])
        
        console.print("\n[bold]By Model:[/]")
        table = Table()
        table.add_column("Model", style="cyan")
        table.add_column("Games", justify="right")
        table.add_column("Avg F1", justify="right", style="green")
        
        for model_name in sorted(models.keys()):
            stats = models[model_name]
            avg_f1 = sum(stats["f1_scores"]) / len(stats["f1_scores"]) if stats["f1_scores"] else 0
            table.add_row(model_name, str(len(stats["games"])), f"{avg_f1:.1%}")
        console.print(table)
    
    # Per-game results (if detailed)
    if detailed and games:
        console.print("\n[bold]Per-Game Results:[/]")
        table = Table()
        table.add_column("Game ID", style="cyan")
        table.add_column("Domain")
        table.add_column("Difficulty")
        table.add_column("Red", justify="right")
        table.add_column("Blue", justify="right")
        table.add_column("Precision", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1", justify="right", style="green")
        table.add_column("Evasion", justify="right", style="red")
        
        for game in games[:20]:  # Show first 20
            table.add_row(
                game.get("game_id", "N/A")[-18:],
                game.get("scenario_domain", "N/A")[:8],
                game.get("difficulty", "N/A"),
                str(game.get("red_vulns", 0)),
                str(game.get("blue_findings", 0)),
                f"{game.get('precision', 0):.0%}",
                f"{game.get('recall', 0):.0%}",
                f"{game.get('f1_score', 0):.0%}",
                f"{game.get('evasion_rate', 0):.0%}",
            )
        
        if len(games) > 20:
            console.print(f"[dim]... and {len(games) - 20} more games[/]")
        
        console.print(table)
    elif games:
        console.print(f"\n[dim]Use --detailed to see {len(games)} individual game results[/]")
    
    # Check for tool comparison
    tool_comp_file = exp_path / "tool_comparison.json"
    if tool_comp_file.exists():
        tool_comp = json.loads(tool_comp_file.read_text())
        tool_summary = tool_comp.get("summary", {})
        
        console.print("\n[bold]Tool Comparison:[/]")
        console.print(f"  LLM Total:     {tool_summary.get('llm_total', 'N/A')}")
        console.print(f"  Trivy Total:   {tool_summary.get('trivy_total', 'N/A')}")
        console.print(f"  Checkov Total: {tool_summary.get('checkov_total', 'N/A')}")
    
    # Check for hybrid results
    hybrid_file = exp_path / "hybrid_results" / "hybrid_summary.json"
    if hybrid_file.exists():
        hybrid = json.loads(hybrid_file.read_text())
        hybrid_agg = hybrid.get("aggregate", {})
        
        console.print("\n[bold]Hybrid Detection:[/]")
        console.print(f"  Avg F1 Score:     [green]{hybrid_agg.get('avg_f1_score', 0):.1%}[/]")
        console.print(f"  Total Findings:   {hybrid_agg.get('total_hybrid_findings', 'N/A')}")


@cli.command("hybrid-experiment")
@click.option(
    "--experiment",
    "-e",
    "experiment_dir",
    type=click.Path(exists=True),
    required=True,
    help="Path to experiment directory with existing games",
)
@click.option(
    "--model",
    "-m",
    default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    help="Model ID for LLM analysis",
)
@click.option("--region", default="us-east-1", help="AWS region")
def hybrid_experiment(experiment_dir: str, model: str, region: str):
    """
    Run hybrid (LLM + Checkov) detection on experiment results.
    
    Combines LLM semantic analysis with Checkov policy checks
    for maximum coverage.
    """
    console.print(
        Panel.fit(
            "[bold green]🔀 HYBRID DETECTION EXPERIMENT[/]\n"
            f"Experiment: {experiment_dir}\n"
            f"LLM Model: {model}\n"
            f"Mode: LLM + Checkov",
            title="Hybrid Analysis",
        )
    )
    
    try:
        asyncio.run(
            _run_hybrid_experiment(
                experiment_dir=experiment_dir,
                model=model,
                region=region,
            )
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise click.Abort()


async def _run_hybrid_experiment(experiment_dir: str, model: str, region: str):
    """Run hybrid detection across all games in an experiment."""
    from src.agents.judge_agent import JudgeAgent
    
    exp_path = Path(experiment_dir)
    games_dir = exp_path / "games"
    games = sorted([d for d in games_dir.iterdir() if d.is_dir()])
    
    # Create output directory for hybrid results
    hybrid_dir = exp_path / "hybrid_results"
    hybrid_dir.mkdir(exist_ok=True)
    
    results = []
    judge = JudgeAgent()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running hybrid analysis...", total=len(games))
        
        for game_dir in games:
            game_id = game_dir.name
            progress.update(task, description=f"Hybrid analysis: {game_id}...")
            
            # Load code files
            code_files = {}
            code_dir = game_dir / "code"
            if code_dir.exists():
                for f in code_dir.glob("*.tf"):
                    code_files[f.name] = f.read_text()
            
            if not code_files:
                progress.advance(task)
                continue
            
            # Load ground truth
            manifest_file = game_dir / "red_manifest.json"
            if not manifest_file.exists():
                progress.advance(task)
                continue
            
            ground_truth = json.loads(manifest_file.read_text())
            
            # Create hybrid Blue Team agent
            agent = create_blue_team_agent(
                model_id=model,
                region=region,
                mode="hybrid",
                language="terraform",
                use_trivy=False,  # Trivy not useful for our vulns
                use_checkov=True,
            )
            
            # Run hybrid analysis
            output = await agent.execute(code_files)
            
            # Save hybrid findings
            game_hybrid_dir = hybrid_dir / game_id
            game_hybrid_dir.mkdir(exist_ok=True)
            
            findings_data = [
                {
                    "finding_id": f.finding_id,
                    "resource_name": f.resource_name,
                    "vulnerability_type": f.vulnerability_type,
                    "severity": f.severity,
                    "title": f.title,
                    "source": f.source,
                    "confidence": f.confidence,
                }
                for f in output.findings
            ]
            (game_hybrid_dir / "hybrid_findings.json").write_text(
                json.dumps(findings_data, indent=2)
            )
            
            # Score hybrid results
            scoring = judge.score(ground_truth, findings_data)
            
            # Count by source
            by_source = {"llm": 0, "checkov": 0}
            for f in output.findings:
                if f.source in by_source:
                    by_source[f.source] += 1
            
            results.append({
                "game": game_id,
                "ground_truth": len(ground_truth),
                "hybrid_findings": len(output.findings),
                "llm_findings": by_source["llm"],
                "checkov_findings": by_source["checkov"],
                "precision": scoring.precision,
                "recall": scoring.recall,
                "f1_score": scoring.f1_score,
                "evasion_rate": scoring.evasion_rate,
            })
            
            progress.advance(task)
    
    # Display results
    console.print("\n[bold green]✓ Hybrid Experiment Complete[/]\n")
    
    # Summary table
    table = Table(title="Hybrid Detection Results")
    table.add_column("Game", style="cyan")
    table.add_column("GT", justify="right")
    table.add_column("Hybrid", justify="right")
    table.add_column("LLM", justify="right")
    table.add_column("Checkov", justify="right")
    table.add_column("F1", justify="right", style="green")
    table.add_column("Evasion", justify="right", style="red")
    
    for r in results[:10]:  # Show first 10
        table.add_row(
            r["game"][-15:],
            str(r["ground_truth"]),
            str(r["hybrid_findings"]),
            str(r["llm_findings"]),
            str(r["checkov_findings"]),
            f"{r['f1_score']:.1%}",
            f"{r['evasion_rate']:.1%}",
        )
    
    if len(results) > 10:
        table.add_row("...", "...", "...", "...", "...", "...", "...")
    
    console.print(table)
    
    # Aggregate metrics
    if results:
        avg_f1 = sum(r["f1_score"] for r in results) / len(results)
        avg_evasion = sum(r["evasion_rate"] for r in results) / len(results)
        total_hybrid = sum(r["hybrid_findings"] for r in results)
        total_llm = sum(r["llm_findings"] for r in results)
        total_checkov = sum(r["checkov_findings"] for r in results)
        
        console.print(f"\n[bold]Aggregate Metrics:[/]")
        console.print(f"  Average F1 Score: [green]{avg_f1:.2%}[/]")
        console.print(f"  Average Evasion Rate: [red]{avg_evasion:.2%}[/]")
        console.print(f"  Total Hybrid Findings: {total_hybrid} (LLM: {total_llm}, Checkov: {total_checkov})")
    
    # Save summary
    summary_file = hybrid_dir / "hybrid_summary.json"
    summary_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "total_games": len(results),
        "aggregate": {
            "avg_f1_score": avg_f1 if results else 0,
            "avg_evasion_rate": avg_evasion if results else 0,
            "total_hybrid_findings": total_hybrid if results else 0,
        },
        "per_game": results,
    }, indent=2))
    
    console.print(f"\n[dim]Results saved to {hybrid_dir}[/]")


if __name__ == "__main__":
    cli()
