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
from src.models import (
    MODEL_REGISTRY, TIER_INFO, DEFAULT_MODELS,
    get_model_id, get_model_tier, list_all_models,
    get_interactive_model_choices,
)

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
@click.option("--tier", "-t", type=click.Choice(["frontier", "strong", "efficient", "specialized", "all"]), default="all", help="Filter by tier")
def models(tier: str):
    """
    List available Bedrock models organized by capability tier.
    
    Tiers:
    - frontier: Best quality, highest cost (Claude 3 Opus, Nova Premier)
    - strong: Good balance (Claude 3.5 Haiku, Nova Pro, Llama 70B)
    - efficient: Fast and cheap (Nova Lite, Llama 8B, Mistral Small)
    - specialized: Experimental models (DeepSeek, Jamba)
    """
    console.print(Panel.fit(
        "[bold cyan]Available Bedrock Models[/]\n"
        "[dim]Use short names with --red-model or --blue-model[/]",
        title="Model Registry",
    ))
    console.print()
    
    tiers_to_show = [tier] if tier != "all" else TIER_INFO.keys()
    
    for tier_name in tiers_to_show:
        info = TIER_INFO[tier_name]
        tier_models = MODEL_REGISTRY.get(tier_name, {})
        
        table = Table(title=f"{info['emoji']} {info['name']} Tier - {info['description']}")
        table.add_column("Short Name", style="cyan")
        table.add_column("Full Model ID", style="dim")
        
        for short_name, full_id in tier_models.items():
            table.add_row(short_name, full_id)
        
        console.print(table)
        console.print()
    
    # Show usage examples
    console.print("[bold]Usage Examples:[/]")
    console.print("  [cyan]adversarial-iac game --red-model claude-3.5-sonnet --blue-model nova-pro ...[/]")
    console.print("  [cyan]adversarial-iac game --red-model mistral-large --blue-model llama-3.1-70b ...[/]")
    console.print()
    console.print("[dim]You can also use full model IDs directly for newer/custom models.[/]")


@cli.command()
@click.option("--category", "-c", type=click.Choice(["infrastructure", "aws_service", "industry", "security", "all"]), default="all", help="Filter by category")
@click.option("--domain", "-d", help="Show scenarios for a specific domain")
def scenarios(category: str, domain: str):
    """
    List available test scenarios organized by category and domain.
    
    Categories:
    - infrastructure: Core AWS infrastructure (storage, compute, network, iam)
    - aws_service: Specific AWS services (secrets, containers, databases, api)
    - industry: Industry-specific compliance (healthcare, financial, government)
    - security: Security-focused patterns (zero_trust, disaster_recovery)
    """
    from src.prompts import ScenarioTemplates
    
    counts = ScenarioTemplates.get_scenario_count()
    
    console.print(Panel.fit(
        f"[bold cyan]Infrastructure Scenarios[/]\n"
        f"[dim]{counts['total']} scenarios across {len(counts['by_domain'])} domains[/]",
        title="Scenario Library",
    ))
    console.print()
    
    # If specific domain requested, show its scenarios
    if domain:
        if domain not in ScenarioTemplates.SCENARIOS:
            console.print(f"[red]Error:[/] Unknown domain '{domain}'")
            console.print(f"[dim]Valid domains: {', '.join(ScenarioTemplates.SCENARIOS.keys())}[/]")
            return
        
        info = ScenarioTemplates.DOMAIN_INFO.get(domain, {})
        scenarios_list = ScenarioTemplates.SCENARIOS[domain]
        
        table = Table(title=f"{info.get('icon', '📋')} {domain.replace('_', ' ').title()} - {info.get('description', '')}")
        table.add_column("#", style="dim", width=3)
        table.add_column("Scenario Description", style="white")
        
        for i, scenario in enumerate(scenarios_list):
            table.add_row(str(i), scenario)
        
        console.print(table)
        console.print()
        console.print(f"[dim]Use: adversarial-iac game --scenario \"{scenarios_list[0][:50]}...\"[/]")
        return
    
    # Show domains by category
    domains = ScenarioTemplates.list_domains()
    
    category_names = {
        "infrastructure": "🏗️  Infrastructure Domains",
        "aws_service": "☁️  AWS Service Domains",
        "industry": "🏢  Industry Verticals",
        "security": "🔒  Security Patterns",
    }
    
    categories_to_show = [category] if category != "all" else ["infrastructure", "aws_service", "industry", "security"]
    
    for cat in categories_to_show:
        cat_domains = [d for d in domains if d["category"] == cat]
        if not cat_domains:
            continue
            
        table = Table(title=category_names.get(cat, cat))
        table.add_column("Domain", style="cyan", width=18)
        table.add_column("Icon", width=4)
        table.add_column("Description", style="dim")
        table.add_column("Count", justify="right", style="green")
        
        for d in cat_domains:
            table.add_row(d["name"], d["icon"], d["description"], str(d["count"]))
        
        console.print(table)
        console.print()
    
    # Summary
    console.print("[bold]Category Summary:[/]")
    for cat, count in counts["by_category"].items():
        emoji = {"infrastructure": "🏗️", "aws_service": "☁️", "industry": "🏢", "security": "🔒"}.get(cat, "📋")
        console.print(f"  {emoji} {cat}: {count} scenarios")
    console.print(f"  [bold]Total: {counts['total']} scenarios[/]")
    console.print()
    console.print("[dim]Use --domain <name> to see specific scenarios (e.g., --domain healthcare)[/]")


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
@click.option(
    "--red-team-mode",
    type=click.Choice(["single", "pipeline"]),
    default="single",
    help="Red Team mode: single agent or multi-agent pipeline",
)
@click.option(
    "--blue-team-mode",
    type=click.Choice(["single", "ensemble"]),
    default="single",
    help="Blue Team mode: single agent or multi-agent ensemble",
)
@click.option(
    "--consensus-method",
    type=click.Choice(["debate", "vote", "union", "intersection"]),
    default="debate",
    help="Consensus method for ensemble mode",
)
@click.option(
    "--verification-mode",
    type=click.Choice(["standard", "debate"]),
    default="standard",
    help="Verification mode: standard judge or adversarial debate",
)
@click.option(
    "--no-llm-judge",
    is_flag=True,
    default=False,
    help="Disable LLM for ambiguous matches (faster but less accurate)",
)
@click.option(
    "--red-strategy",
    type=click.Choice(["balanced", "targeted", "stealth", "blitz", "chained"]),
    default="balanced",
    help="Red Team attack strategy",
)
@click.option(
    "--red-target-type",
    type=click.Choice(["encryption", "iam", "network", "logging", "access_control"]),
    default=None,
    help="Target vuln type for 'targeted' red strategy",
)
@click.option(
    "--blue-strategy",
    type=click.Choice(["comprehensive", "targeted", "iterative", "threat_model", "compliance"]),
    default="comprehensive",
    help="Blue Team defense strategy",
)
@click.option(
    "--blue-target-type",
    type=click.Choice(["encryption", "iam", "network", "logging", "access_control"]),
    default=None,
    help="Target vuln type for 'targeted' blue strategy",
)
@click.option(
    "--compliance-framework",
    type=click.Choice(["hipaa", "pci_dss", "soc2", "cis"]),
    default=None,
    help="Compliance framework for 'compliance' blue strategy",
)
@click.option(
    "--blue-iterations",
    type=int,
    default=1,
    help="Number of passes for 'iterative' blue strategy",
)
@click.option(
    "--use-trivy",
    is_flag=True,
    default=False,
    help="Enable Trivy static analysis for Blue Team",
)
@click.option(
    "--use-checkov",
    is_flag=True,
    default=False,
    help="Enable Checkov static analysis for Blue Team",
)
@click.option("--region", default="us-east-1", help="AWS region")
def game(
    scenario: str,
    red_model: str,
    blue_model: str,
    difficulty: str,
    language: str,
    cloud_provider: str,
    red_team_mode: str,
    blue_team_mode: str,
    consensus_method: str,
    verification_mode: str,
    no_llm_judge: bool,
    red_strategy: str,
    red_target_type: str,
    blue_strategy: str,
    blue_target_type: str,
    compliance_framework: str,
    blue_iterations: int,
    use_trivy: bool,
    use_checkov: bool,
    region: str,
):
    """
    Run a complete Red Team vs Blue Team game.
    
    Red Team generates adversarial IaC, Blue Team detects vulnerabilities,
    Judge scores the match.
    
    Multi-Agent Modes:
    - --red-team-mode pipeline: Multi-agent attack chain (Architect→Selector→Generator→Reviewer)
    - --blue-team-mode ensemble: Multi-agent defense (Security+Compliance+Architecture→Consensus)
    - --verification-mode debate: Adversarial debate verification (Prosecutor vs Defender)
    
    Attack Strategies (--red-strategy):
    - balanced: Standard mix of vulnerability types and stealth
    - targeted: Focus on specific vulnerability type (use --red-target-type)
    - stealth: Fewer vulns but maximum evasion techniques
    - blitz: Maximum vulnerabilities, less stealth
    - chained: Vulnerabilities that exploit each other in sequence
    
    Defense Strategies (--blue-strategy):
    - comprehensive: Check for all vulnerability types
    - targeted: Focus on specific vulnerability type (use --blue-target-type)
    - iterative: Multiple analysis passes with refinement (use --blue-iterations)
    - threat_model: Start with threat model, then hunt for matching vulns
    - compliance: Check against compliance framework (use --compliance-framework)
    
    Static Analysis Tools:
    - --use-trivy: Enable Trivy IaC scanner (must be installed)
    - --use-checkov: Enable Checkov scanner (must be installed)
    """
    # Build mode display strings
    red_display = f"{red_team_mode}" + (" (4-stage)" if red_team_mode == "pipeline" else "")
    red_strategy_display = red_strategy
    if red_strategy == "targeted" and red_target_type:
        red_strategy_display = f"targeted:{red_target_type}"
    
    blue_display = f"{blue_team_mode}" + (f" ({consensus_method})" if blue_team_mode == "ensemble" else "")
    blue_strategy_display = blue_strategy
    if blue_strategy == "targeted" and blue_target_type:
        blue_strategy_display = f"targeted:{blue_target_type}"
    elif blue_strategy == "compliance" and compliance_framework:
        blue_strategy_display = f"compliance:{compliance_framework}"
    elif blue_strategy == "iterative":
        blue_strategy_display = f"iterative:{blue_iterations}x"
    
    # Static tools display
    tools_display = []
    if use_trivy:
        tools_display.append("Trivy")
    if use_checkov:
        tools_display.append("Checkov")
    tools_str = ", ".join(tools_display) if tools_display else "None"
    
    verify_display = verification_mode
    
    console.print(
        Panel.fit(
            "[bold magenta]🎮 ADVERSARIAL GAME[/]\n"
            f"Scenario: {scenario}\n"
            f"Red Team: {red_model.split('.')[-1][:20]} ({red_display})\n"
            f"  Strategy: {red_strategy_display}\n"
            f"Blue Team: {blue_model.split('.')[-1][:20]} ({blue_display})\n"
            f"  Strategy: {blue_strategy_display}\n"
            f"  Static Tools: {tools_str}\n"
            f"Difficulty: {difficulty}\n"
            f"Verification: {verify_display}",
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
                red_team_mode=red_team_mode,
                blue_team_mode=blue_team_mode,
                consensus_method=consensus_method,
                verification_mode=verification_mode,
                use_llm_judge=not no_llm_judge,
                red_strategy=red_strategy,
                red_target_type=red_target_type,
                blue_strategy=blue_strategy,
                blue_target_type=blue_target_type,
                compliance_framework=compliance_framework,
                blue_iterations=blue_iterations,
                use_trivy=use_trivy,
                use_checkov=use_checkov,
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
    red_team_mode: str,
    blue_team_mode: str,
    consensus_method: str,
    verification_mode: str,
    use_llm_judge: bool = False,
    red_strategy: str = "balanced",
    red_target_type: str = None,
    blue_strategy: str = "comprehensive",
    blue_target_type: str = None,
    compliance_framework: str = None,
    blue_iterations: int = 1,
    use_trivy: bool = False,
    use_checkov: bool = False,
    region: str = "us-east-1",
):
    """Async implementation of game command."""
    from src.game.engine import GameEngine, GameConfig
    from src.game.scenarios import ScenarioGenerator
    
    # Resolve model short names to full IDs
    red_model_id = get_model_id(red_model)
    blue_model_id = get_model_id(blue_model)
    
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
    
    # Determine detection mode based on tools
    if use_trivy or use_checkov:
        detection_mode = "hybrid"  # LLM + tools
    else:
        detection_mode = "llm_only"
    
    # Create game config
    config = GameConfig(
        red_model=red_model_id,
        blue_model=blue_model_id,
        difficulty=difficulty,
        language=language,
        cloud_provider=cloud_provider,
        detection_mode=detection_mode,
        use_trivy=use_trivy,
        use_checkov=use_checkov,
        region=region,
        red_team_mode=red_team_mode,
        red_strategy=red_strategy,
        red_target_type=red_target_type,
        blue_team_mode=blue_team_mode,
        ensemble_specialists=["security", "compliance", "architecture"] if blue_team_mode == "ensemble" else None,
        consensus_method=consensus_method,
        blue_strategy=blue_strategy,
        blue_target_type=blue_target_type,
        compliance_framework=compliance_framework,
        blue_iterations=blue_iterations,
        verification_mode=verification_mode,
        use_llm_judge=use_llm_judge,
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
        
        progress.update(task, description="Saving results...")
        
        # Save results to disk
        engine._save_game_result(result)
        
        progress.update(task, description="Game complete!")
    
    # Display results
    console.print("\n[bold green]✓ Game Complete[/]\n")
    
    # Build Red Team section based on mode
    red_team_section = f"[red]🔴 Red Team:[/]\n"
    red_team_section += f"  • Mode: {result.red_team_mode}\n"
    red_team_section += f"  • Vulnerabilities injected: {len(result.red_output.manifest)}\n"
    
    # Add pipeline-specific info
    if result.red_team_mode == "pipeline" and result.pipeline_stages:
        stages_completed = sum(1 for s in result.pipeline_stages.values() if s.get("success", False))
        red_team_section += f"  • Pipeline stages: {stages_completed}/4 completed\n"
        if result.architecture_design:
            components = len(result.architecture_design.get("components", []))
            red_team_section += f"  • Architecture: {components} components designed\n"
    
    red_team_section += f"  • Stealth: {'✓ Passed' if result.red_output.stealth_score else '✗ Failed'}\n"
    red_team_section += f"  • Time: {result.red_time_seconds:.1f}s"
    
    # Build Blue Team section based on mode
    blue_team_section = f"[blue]🔵 Blue Team:[/]\n"
    blue_team_section += f"  • Mode: {result.blue_team_mode}\n"
    blue_team_section += f"  • Findings: {len(result.blue_output.findings)}\n"
    
    # Add ensemble-specific info
    if result.blue_team_mode == "ensemble" and result.consensus_stats:
        stats = result.consensus_stats
        blue_team_section += f"  • Consensus: {config.consensus_method}\n"
        blue_team_section += f"  • Unanimous: {stats.get('unanimous', 0)}, Majority: {stats.get('majority', 0)}\n"
        if result.specialist_findings:
            specialist_counts = ", ".join(
                f"{k.replace('_', ' ').title()}: {len(v)}"
                for k, v in result.specialist_findings.items()
            )
            blue_team_section += f"  • Per-specialist: {specialist_counts}\n"
    
    blue_team_section += f"  • Time: {result.blue_time_seconds:.1f}s"
    
    # Build Verification section based on mode
    verification_section = f"[yellow]⚖️ Verification ({result.verification_mode}):[/]\n"
    
    if result.verification_mode == "debate" and result.debate_results:
        verified = len(result.verified_findings) if result.verified_findings else 0
        rejected = len(result.rejected_findings) if result.rejected_findings else 0
        verification_section += f"  • Findings verified: {verified}\n"
        verification_section += f"  • Findings rejected: {rejected}\n"
    
    verification_section += f"  • Precision: {result.scoring.precision:.2%}\n"
    verification_section += f"  • Recall: {result.scoring.recall:.2%}\n"
    verification_section += f"  • F1 Score: {result.scoring.f1_score:.2%}\n"
    verification_section += f"  • Evasion Rate: {result.scoring.evasion_rate:.2%}"
    
    # Summary
    console.print(Panel.fit(
        f"[bold]Game ID:[/] {result.game_id}\n\n"
        f"{red_team_section}\n\n"
        f"{blue_team_section}\n\n"
        f"{verification_section}",
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
def play():
    """
    🎮 Interactive mode - guided game setup with explanations.
    
    This wizard walks you through setting up and running an adversarial
    game, then explains the results in detail.
    """
    import questionary
    from questionary import Style
    
    # Custom style for the wizard
    custom_style = Style([
        ('qmark', 'fg:#673ab7 bold'),
        ('question', 'bold'),
        ('answer', 'fg:#2196f3 bold'),
        ('pointer', 'fg:#673ab7 bold'),
        ('highlighted', 'fg:#673ab7 bold'),
        ('selected', 'fg:#2196f3'),
        ('separator', 'fg:#cc5454'),
        ('instruction', 'fg:#808080'),
    ])
    
    console.print(Panel.fit(
        "[bold magenta]🎮 ADVERSARIAL IAC EVALUATION[/]\n"
        "[dim]Interactive Mode - Let's set up a security game![/]\n\n"
        "Red Team will try to hide vulnerabilities in infrastructure code.\n"
        "Blue Team will try to find them. Let's see who wins!",
        title="Welcome",
        border_style="magenta",
    ))
    console.print()
    
    # Import scenario templates
    from src.prompts import ScenarioTemplates
    
    # First, ask how user wants to select scenario
    scenario_method = questionary.select(
        "How would you like to choose a scenario?",
        choices=[
            questionary.Choice("🎲 Random - Let me pick something interesting", "random"),
            questionary.Choice("🏗️  Infrastructure - Core AWS components", "infrastructure"),
            questionary.Choice("☁️  AWS Services - Specific services (containers, databases...)", "aws_service"),
            questionary.Choice("🏢 Industry - Healthcare, Financial, Government...", "industry"),
            questionary.Choice("🔒 Security - Zero-trust, disaster recovery...", "security"),
            questionary.Choice("✏️  Custom - Describe your own scenario", "custom"),
        ],
        style=custom_style,
    ).ask()
    
    if scenario_method is None:
        console.print("[dim]Cancelled.[/]")
        return
    
    scenario = None
    
    if scenario_method == "random":
        # Get a random scenario
        random_scenario = ScenarioTemplates.get_random_scenario()
        info = ScenarioTemplates.DOMAIN_INFO.get(random_scenario["domain"], {})
        scenario = random_scenario["description"]
        console.print(f"\n[bold green]Selected:[/] {info.get('icon', '📋')} {random_scenario['domain'].replace('_', ' ').title()}")
        console.print(f"[dim]{scenario}[/]\n")
        
    elif scenario_method == "custom":
        scenario = questionary.text(
            "Describe your custom scenario:",
            style=custom_style,
        ).ask()
        if not scenario:
            console.print("[dim]Cancelled.[/]")
            return
            
    else:
        # Browse category
        domains = [d for d in ScenarioTemplates.list_domains() if d["category"] == scenario_method]
        
        domain_choices = [
            questionary.Choice(f"{d['icon']} {d['name'].replace('_', ' ').title()} ({d['count']} scenarios)", d["name"])
            for d in domains
        ]
        
        selected_domain = questionary.select(
            "Select a domain:",
            choices=domain_choices,
            style=custom_style,
        ).ask()
        
        if selected_domain is None:
            console.print("[dim]Cancelled.[/]")
            return
        
        # Show scenarios from that domain
        domain_scenarios = ScenarioTemplates.SCENARIOS[selected_domain]
        scenario_choices = [
            questionary.Choice(f"{s[:70]}..." if len(s) > 70 else s, s)
            for s in domain_scenarios
        ]
        
        scenario = questionary.select(
            f"Select a {selected_domain.replace('_', ' ')} scenario:",
            choices=scenario_choices,
            style=custom_style,
        ).ask()
        
        if scenario is None:
            console.print("[dim]Cancelled.[/]")
            return
    
    console.print()
    
    # Difficulty selection with explanations
    difficulty_choices = [
        questionary.Choice(
            "🟢 Easy - Obvious vulnerabilities (good for learning)",
            "easy"
        ),
        questionary.Choice(
            "🟡 Medium - Subtle issues requiring context (recommended)", 
            "medium"
        ),
        questionary.Choice(
            "🔴 Hard - Hidden, chained vulnerabilities (expert mode)",
            "hard"
        ),
    ]
    
    difficulty = questionary.select(
        "Select difficulty level:",
        choices=difficulty_choices,
        style=custom_style,
        instruction="(Use arrow keys)",
    ).ask()
    
    if difficulty is None:
        console.print("[dim]Cancelled.[/]")
        return
    
    console.print()
    
    # IaC Language selection
    language_choices = [
        questionary.Choice(
            "📄 Terraform (HCL) - Most popular, recommended",
            "terraform"
        ),
        questionary.Choice(
            "☁️  CloudFormation (YAML/JSON) - AWS native",
            "cloudformation"
        ),
    ]
    
    language = questionary.select(
        "Which Infrastructure-as-Code language?",
        choices=language_choices,
        style=custom_style,
    ).ask()
    
    if language is None:
        console.print("[dim]Cancelled.[/]")
        return
    
    console.print()
    
    # Model selection - organized by tier
    def build_model_choices():
        """Build model choices organized by tier."""
        choices = []
        
        # Quick picks at the top
        choices.append(questionary.Choice(
            "⭐ claude-3.5-sonnet (Recommended - best quality)",
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        ))
        choices.append(questionary.Choice(
            "⚡ claude-3.5-haiku (Fast - good balance)",
            "us.anthropic.claude-3-5-haiku-20241022-v1:0"
        ))
        choices.append(questionary.Choice(
            "💰 nova-lite (Cheap - for testing)",
            "amazon.nova-lite-v1:0"
        ))
        choices.append(questionary.Separator("─── More Models ───"))
        
        # Frontier tier
        choices.append(questionary.Separator("🏆 Frontier (best quality)"))
        for name, model_id in MODEL_REGISTRY.get("frontier", {}).items():
            if name not in ["claude-3.5-sonnet"]:  # Skip already shown
                choices.append(questionary.Choice(f"   {name}", model_id))
        
        # Strong tier
        choices.append(questionary.Separator("💪 Strong (balanced)"))
        for name, model_id in MODEL_REGISTRY.get("strong", {}).items():
            if name not in ["claude-3.5-haiku"]:  # Skip already shown
                choices.append(questionary.Choice(f"   {name}", model_id))
        
        # Efficient tier
        choices.append(questionary.Separator("⚡ Efficient (fast/cheap)"))
        for name, model_id in MODEL_REGISTRY.get("efficient", {}).items():
            if name not in ["nova-lite"]:  # Skip already shown
                choices.append(questionary.Choice(f"   {name}", model_id))
        
        # Specialized tier
        choices.append(questionary.Separator("🔬 Specialized"))
        for name, model_id in MODEL_REGISTRY.get("specialized", {}).items():
            choices.append(questionary.Choice(f"   {name}", model_id))
        
        # Custom option
        choices.append(questionary.Separator("───────────────"))
        choices.append(questionary.Choice("✏️  Enter custom model ID...", "custom"))
        
        return choices
    
    model_choices = build_model_choices()
    
    red_model = questionary.select(
        "Choose Red Team model (attacker):",
        choices=model_choices,
        style=custom_style,
    ).ask()
    
    if red_model is None:
        console.print("[dim]Cancelled.[/]")
        return
    
    if red_model == "custom":
        console.print("[dim]Tip: Run 'adversarial-iac models' to see all available models[/]")
        red_model = questionary.text(
            "Enter Red Team model ID (short name or full ID):",
            style=custom_style,
        ).ask()
        if not red_model:
            console.print("[dim]Cancelled.[/]")
            return
        red_model = get_model_id(red_model)  # Resolve short name
    
    console.print()
    
    # Blue Team model
    blue_same = questionary.confirm(
        "Use the same model for Blue Team (defender)?",
        default=True,
        style=custom_style,
    ).ask()
    
    if blue_same is None:
        console.print("[dim]Cancelled.[/]")
        return
    
    if blue_same:
        blue_model = red_model
    else:
        blue_model = questionary.select(
            "Choose Blue Team model (defender):",
            choices=model_choices,
            style=custom_style,
        ).ask()
        
        if blue_model is None:
            console.print("[dim]Cancelled.[/]")
            return
        
        if blue_model == "custom":
            blue_model = questionary.text(
                "Enter Blue Team model ID (short name or full ID):",
                style=custom_style,
            ).ask()
            if not blue_model:
                console.print("[dim]Cancelled.[/]")
                return
            blue_model = get_model_id(blue_model)  # Resolve short name
    
    console.print()
    
    # Advanced options
    use_advanced = questionary.confirm(
        "Configure advanced options? (strategies, multi-agent modes)",
        default=False,
        style=custom_style,
    ).ask()
    
    red_team_mode = "single"
    blue_team_mode = "single"
    consensus_method = "debate"
    verification_mode = "standard"
    use_llm_judge = True  # Default to hybrid mode for better accuracy
    red_strategy = "balanced"
    red_target_type = None
    blue_strategy = "comprehensive"
    blue_target_type = None
    compliance_framework = None
    blue_iterations = 1
    use_trivy = False
    use_checkov = False
    
    if use_advanced:
        console.print()
        
        # Red Team configuration
        console.print("[bold red]🔴 Red Team Configuration[/]")
        
        red_team_mode = questionary.select(
            "Red Team mode:",
            choices=[
                questionary.Choice("Single agent (standard)", "single"),
                questionary.Choice("Pipeline (4-stage attack chain)", "pipeline"),
            ],
            style=custom_style,
        ).ask() or "single"
        
        red_strategy = questionary.select(
            "Red Team attack strategy:",
            choices=[
                questionary.Choice("Balanced - Standard mix of vulnerabilities", "balanced"),
                questionary.Choice("Targeted - Focus on specific vulnerability type", "targeted"),
                questionary.Choice("Stealth - Fewer but harder to detect", "stealth"),
                questionary.Choice("Blitz - Maximum vulnerabilities", "blitz"),
                questionary.Choice("Chained - Vulnerabilities that work together", "chained"),
            ],
            style=custom_style,
        ).ask() or "balanced"
        
        if red_strategy == "targeted":
            red_target_type = questionary.select(
                "Target vulnerability type:",
                choices=[
                    questionary.Choice("🔐 Encryption", "encryption"),
                    questionary.Choice("👤 IAM/Permissions", "iam"),
                    questionary.Choice("🌐 Network", "network"),
                    questionary.Choice("📝 Logging/Monitoring", "logging"),
                    questionary.Choice("🚪 Access Control", "access_control"),
                ],
                style=custom_style,
            ).ask() or "encryption"
        
        console.print()
        
        # Blue Team configuration
        console.print("[bold blue]🔵 Blue Team Configuration[/]")
        
        blue_team_mode = questionary.select(
            "Blue Team mode:",
            choices=[
                questionary.Choice("Single agent (standard)", "single"),
                questionary.Choice("Ensemble (3 specialists + consensus)", "ensemble"),
            ],
            style=custom_style,
        ).ask() or "single"
        
        if blue_team_mode == "ensemble":
            consensus_method = questionary.select(
                "Consensus method for ensemble:",
                choices=[
                    questionary.Choice("Debate (agents discuss findings)", "debate"),
                    questionary.Choice("Vote (majority wins)", "vote"),
                    questionary.Choice("Union (all unique findings)", "union"),
                    questionary.Choice("Intersection (only agreed findings)", "intersection"),
                ],
                style=custom_style,
            ).ask() or "debate"
        else:
            # Single agent can use strategies
            blue_strategy = questionary.select(
                "Blue Team defense strategy:",
                choices=[
                    questionary.Choice("Comprehensive - Check all vulnerability types", "comprehensive"),
                    questionary.Choice("Targeted - Focus on specific vulnerability type", "targeted"),
                    questionary.Choice("Iterative - Multiple analysis passes", "iterative"),
                    questionary.Choice("Threat Model - STRIDE-based analysis", "threat_model"),
                    questionary.Choice("Compliance - Framework-specific audit", "compliance"),
                ],
                style=custom_style,
            ).ask() or "comprehensive"
            
            if blue_strategy == "targeted":
                blue_target_type = questionary.select(
                    "Target vulnerability type:",
                    choices=[
                        questionary.Choice("🔐 Encryption", "encryption"),
                        questionary.Choice("👤 IAM/Permissions", "iam"),
                        questionary.Choice("🌐 Network", "network"),
                        questionary.Choice("📝 Logging/Monitoring", "logging"),
                        questionary.Choice("🚪 Access Control", "access_control"),
                    ],
                    style=custom_style,
                ).ask() or "encryption"
            elif blue_strategy == "iterative":
                blue_iterations = questionary.select(
                    "Number of analysis passes:",
                    choices=[
                        questionary.Choice("2 passes (quick refinement)", 2),
                        questionary.Choice("3 passes (thorough)", 3),
                        questionary.Choice("5 passes (exhaustive)", 5),
                    ],
                    style=custom_style,
                ).ask() or 2
            elif blue_strategy == "compliance":
                compliance_framework = questionary.select(
                    "Compliance framework:",
                    choices=[
                        questionary.Choice("🏥 HIPAA (Healthcare)", "hipaa"),
                        questionary.Choice("💳 PCI-DSS (Payment)", "pci_dss"),
                        questionary.Choice("📋 SOC 2 (Service Org)", "soc2"),
                        questionary.Choice("🔒 CIS Benchmarks", "cis"),
                    ],
                    style=custom_style,
                ).ask() or "hipaa"
        
        console.print()
        
        # Static Analysis Tools
        console.print("[bold green]🔧 Static Analysis Tools[/]")
        console.print("[dim]These tools must be installed separately (trivy, checkov)[/]")
        
        static_tools = questionary.checkbox(
            "Enable static analysis tools (in addition to LLM):",
            choices=[
                questionary.Choice("Trivy (IaC security scanner)", "trivy"),
                questionary.Choice("Checkov (policy-as-code scanner)", "checkov"),
            ],
            style=custom_style,
        ).ask() or []
        
        use_trivy = "trivy" in static_tools
        use_checkov = "checkov" in static_tools
        
        console.print()
        
        # Verification mode
        console.print("[bold yellow]⚖️ Verification Configuration[/]")
        
        verification_mode = questionary.select(
            "Verification mode:",
            choices=[
                questionary.Choice("Standard (direct matching)", "standard"),
                questionary.Choice("Adversarial Debate (prosecutor vs defender)", "debate"),
            ],
            style=custom_style,
        ).ask() or "standard"
        
        # LLM Judge option (only for standard mode, enabled by default)
        use_llm_judge = True  # Default to hybrid mode
        if verification_mode == "standard":
            disable_llm_judge = questionary.confirm(
                "Disable LLM for ambiguous matches? (faster but less accurate)",
                default=False,
                style=custom_style,
            ).ask() or False
            use_llm_judge = not disable_llm_judge
    
    console.print()
    
    # Build strategy display strings
    red_strategy_display = red_strategy
    if red_strategy == "targeted" and red_target_type:
        red_strategy_display = f"targeted:{red_target_type}"
    
    blue_strategy_display = blue_strategy
    if blue_strategy == "targeted" and blue_target_type:
        blue_strategy_display = f"targeted:{blue_target_type}"
    elif blue_strategy == "compliance" and compliance_framework:
        blue_strategy_display = f"compliance:{compliance_framework}"
    elif blue_strategy == "iterative":
        blue_strategy_display = f"iterative:{blue_iterations}x"
    
    # Static tools display
    tools_list = []
    if use_trivy:
        tools_list.append("Trivy")
    if use_checkov:
        tools_list.append("Checkov")
    tools_display = ", ".join(tools_list) if tools_list else "None"
    
    # Language display
    language_display = "Terraform (HCL)" if language == "terraform" else "CloudFormation (YAML)"
    
    # Build verification display
    verification_display = verification_mode
    if use_llm_judge:
        verification_display += " (hybrid)"
    else:
        verification_display += " (rule-based only)"
    
    # Confirmation
    console.print(Panel.fit(
        f"[bold]Scenario:[/] {scenario[:60]}{'...' if len(scenario) > 60 else ''}\n"
        f"[bold]Language:[/] {language_display}\n"
        f"[bold]Difficulty:[/] {difficulty}\n"
        f"[bold]Red Team:[/] {red_model.split('.')[-1][:30]} ({red_team_mode}, {red_strategy_display})\n"
        f"[bold]Blue Team:[/] {blue_model.split('.')[-1][:30]} ({blue_team_mode}, {blue_strategy_display})\n"
        f"[bold]Static Tools:[/] {tools_display}\n"
        f"[bold]Verification:[/] {verification_display}",
        title="Game Configuration",
        border_style="cyan",
    ))
    
    console.print()
    
    ready = questionary.confirm(
        "Ready to start the game?",
        default=True,
        style=custom_style,
    ).ask()
    
    if not ready:
        console.print("[dim]Cancelled.[/]")
        return
    
    console.print()
    
    # Run the game
    try:
        result = asyncio.run(
            _run_interactive_game(
                scenario=scenario,
                red_model=red_model,
                blue_model=blue_model,
                difficulty=difficulty,
                language=language,
                red_team_mode=red_team_mode,
                blue_team_mode=blue_team_mode,
                consensus_method=consensus_method,
                verification_mode=verification_mode,
                red_strategy=red_strategy,
                red_target_type=red_target_type,
                blue_strategy=blue_strategy,
                blue_target_type=blue_target_type,
                compliance_framework=compliance_framework,
                blue_iterations=blue_iterations,
                use_trivy=use_trivy,
                use_checkov=use_checkov,
            )
        )
        
        # Show explained results
        _display_explained_results(result)
        
        # Ask what to do next
        console.print()
        next_action = questionary.select(
            "What would you like to do next?",
            choices=[
                questionary.Choice("🎮 Play another game", "play"),
                questionary.Choice("📂 Open results folder", "open"),
                questionary.Choice("📊 View detailed match analysis", "details"),
                questionary.Choice("👋 Exit", "exit"),
            ],
            style=custom_style,
        ).ask()
        
        if next_action == "play":
            play()  # Recursive call for another game
        elif next_action == "open":
            import subprocess
            subprocess.run(["open", f"output/games/{result.game_id}"])
        elif next_action == "details":
            _display_detailed_analysis(result)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")


async def _run_interactive_game(
    scenario: str,
    red_model: str,
    blue_model: str,
    difficulty: str,
    language: str = "terraform",
    red_team_mode: str = "single",
    blue_team_mode: str = "single",
    consensus_method: str = "debate",
    verification_mode: str = "standard",
    red_strategy: str = "balanced",
    red_target_type: str = None,
    blue_strategy: str = "comprehensive",
    blue_target_type: str = None,
    compliance_framework: str = None,
    blue_iterations: int = 1,
    use_trivy: bool = False,
    use_checkov: bool = False,
):
    """Run the game with nice progress display."""
    from src.game.engine import GameEngine, GameConfig
    from src.game.scenarios import ScenarioGenerator
    
    # Resolve model short names to full IDs
    red_model_id = get_model_id(red_model)
    blue_model_id = get_model_id(blue_model)
    
    # Create scenario
    scenario_gen = ScenarioGenerator(
        cloud_providers=["aws"],
        languages=[language],
    )
    test_scenario = scenario_gen.generate_single_scenario(
        description=scenario,
        cloud_provider="aws",
        language=language,
        difficulty=difficulty,
    )
    
    # Determine detection mode based on tools
    if use_trivy or use_checkov:
        detection_mode = "hybrid"  # LLM + tools
    else:
        detection_mode = "llm_only"
    
    # Create game config
    config = GameConfig(
        red_model=red_model_id,
        blue_model=blue_model_id,
        difficulty=difficulty,
        language=language,
        cloud_provider="aws",
        detection_mode=detection_mode,
        use_trivy=use_trivy,
        use_checkov=use_checkov,
        region="us-east-1",
        red_team_mode=red_team_mode,
        red_strategy=red_strategy,
        red_target_type=red_target_type,
        blue_team_mode=blue_team_mode,
        ensemble_specialists=["security", "compliance", "architecture"] if blue_team_mode == "ensemble" else None,
        consensus_method=consensus_method,
        blue_strategy=blue_strategy,
        blue_target_type=blue_target_type,
        compliance_framework=compliance_framework,
        blue_iterations=blue_iterations,
        verification_mode=verification_mode,
        use_llm_judge=use_llm_judge,
    )
    
    # Run game with progress
    engine = GameEngine(output_dir="output/games", region="us-east-1")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Phase 1: Red Team generating code with hidden vulnerabilities...", total=None)
        
        result = await engine.run_game(test_scenario, config)
        
        progress.update(task, description="[green]Saving results...")
        engine._save_game_result(result)
    
    return result


def _display_explained_results(result):
    """Display game results with plain-English explanations."""
    
    console.print()
    console.print(Panel.fit(
        "[bold green]🎉 GAME COMPLETE![/]",
        border_style="green",
    ))
    console.print()
    
    # What Red Team did
    red_vulns = result.red_output.manifest
    console.print("[bold red]🔴 RED TEAM (Attacker)[/]")
    console.print(f"   Red Team hid [bold]{len(red_vulns)} vulnerabilities[/] in the code:\n")
    
    for i, vuln in enumerate(red_vulns, 1):
        title = vuln.title if hasattr(vuln, 'title') else str(vuln.get('title', 'Unknown'))
        resource = vuln.resource_name if hasattr(vuln, 'resource_name') else str(vuln.get('resource_name', 'Unknown'))
        console.print(f"   • V{i}: [yellow]{title[:50]}{'...' if len(title) > 50 else ''}[/]")
        console.print(f"         [dim]Resource: {resource}[/]")
    
    console.print()
    
    # What Blue Team found
    blue_findings = result.blue_output.findings
    console.print("[bold blue]🔵 BLUE TEAM (Defender)[/]")
    console.print(f"   Blue Team reported [bold]{len(blue_findings)} potential issues[/]:\n")
    
    for i, finding in enumerate(blue_findings, 1):
        title = finding.title if hasattr(finding, 'title') else str(finding.get('title', 'Unknown'))
        resource = finding.resource_name if hasattr(finding, 'resource_name') else str(finding.get('resource_name', 'Unknown'))
        console.print(f"   • F{i}: [cyan]{title[:50]}{'...' if len(title) > 50 else ''}[/]")
        console.print(f"         [dim]Resource: {resource}[/]")
    
    console.print()
    
    # The verdict
    scoring = result.scoring
    console.print("[bold yellow]⚖️ THE VERDICT[/]\n")
    
    # Build match explanation
    console.print("   [bold]Match Results:[/]")
    for match in scoring.matches:
        if match.match_type == "exact":
            icon = "✅"
            desc = "Detected (exact match)"
            color = "green"
        elif match.match_type == "partial":
            icon = "✅"
            desc = "Detected"
            color = "green"
        else:
            icon = "❌"
            desc = "EVADED - Blue Team missed this!"
            color = "red"
        
        console.print(f"   {icon} {match.red_vuln_id} → {match.blue_finding_id or '—'} [{color}]{desc}[/]")
    
    console.print()
    
    # Metrics explained
    console.print("   [bold]What the numbers mean:[/]\n")
    
    # Precision
    precision_pct = scoring.precision * 100
    if precision_pct >= 80:
        precision_verdict = "Excellent - Most reports were real issues"
        precision_color = "green"
    elif precision_pct >= 50:
        precision_verdict = "Good - More hits than false alarms"
        precision_color = "yellow"
    else:
        precision_verdict = "Needs work - Many false alarms"
        precision_color = "red"
    
    console.print(f"   📊 [bold]Precision: [{precision_color}]{precision_pct:.0f}%[/][/]")
    console.print(f"      {precision_verdict}")
    console.print(f"      [dim]({len(scoring.true_positives)} correct out of {len(blue_findings)} reported)[/]\n")
    
    # Recall
    recall_pct = scoring.recall * 100
    if recall_pct >= 80:
        recall_verdict = "Excellent - Found most vulnerabilities"
        recall_color = "green"
    elif recall_pct >= 50:
        recall_verdict = "Good - Caught over half"
        recall_color = "yellow"
    else:
        recall_verdict = "Needs work - Many vulnerabilities escaped"
        recall_color = "red"
    
    console.print(f"   🎯 [bold]Recall: [{recall_color}]{recall_pct:.0f}%[/][/]")
    console.print(f"      {recall_verdict}")
    console.print(f"      [dim]({len(red_vulns) - len(scoring.false_negatives)} found out of {len(red_vulns)} hidden)[/]\n")
    
    # F1 Score
    f1_pct = scoring.f1_score * 100
    if f1_pct >= 80:
        f1_emoji = "🏆"
        f1_verdict = "Blue Team dominated!"
    elif f1_pct >= 60:
        f1_emoji = "👍"
        f1_verdict = "Solid performance"
    elif f1_pct >= 40:
        f1_emoji = "🤝"
        f1_verdict = "Close match"
    else:
        f1_emoji = "😈"
        f1_verdict = "Red Team won this round!"
    
    console.print(f"   {f1_emoji} [bold]Overall Score: {f1_pct:.0f}%[/]")
    console.print(f"      {f1_verdict}\n")
    
    # Evasion rate
    evasion_pct = scoring.evasion_rate * 100
    evaded_count = len(scoring.false_negatives)
    
    if evasion_pct == 0:
        evasion_verdict = "🛡️ Perfect defense - nothing escaped!"
    elif evasion_pct <= 20:
        evasion_verdict = "🛡️ Strong defense - minimal evasion"
    elif evasion_pct <= 50:
        evasion_verdict = "⚔️ Balanced match - some got through"
    else:
        evasion_verdict = "🎭 Red Team's stealth techniques worked!"
    
    console.print(f"   [bold]Evasion Rate: [red]{evasion_pct:.0f}%[/][/] ({evaded_count} vulnerability(ies) escaped)")
    console.print(f"      {evasion_verdict}")
    
    # Key insight
    console.print()
    console.print(Panel.fit(
        _generate_insight(result),
        title="💡 Key Insight",
        border_style="cyan",
    ))
    
    # Model summary
    console.print()
    red_model_name = result.config.red_model.split(".")[-1] if "." in result.config.red_model else result.config.red_model
    blue_model_name = result.config.blue_model.split(".")[-1] if "." in result.config.blue_model else result.config.blue_model
    
    if red_model_name == blue_model_name:
        model_summary = f"Both teams used [bold]{red_model_name}[/]"
    else:
        model_summary = f"Red Team: [bold]{red_model_name}[/] vs Blue Team: [bold]{blue_model_name}[/]"
    
    console.print(Panel.fit(
        f"[bold]Models:[/] {model_summary}\n"
        f"[bold]Difficulty:[/] {result.config.difficulty}\n"
        f"[bold]Red Team Mode:[/] {result.red_team_mode}\n"
        f"[bold]Blue Team Mode:[/] {result.blue_team_mode}\n"
        f"[bold]Game ID:[/] {result.game_id}",
        title="🤖 Game Configuration",
        border_style="dim",
    ))
    
    console.print(f"\n[dim]Full results saved to: output/games/{result.game_id}[/]")


def _generate_insight(result) -> str:
    """Generate a contextual insight based on the game results."""
    scoring = result.scoring
    
    # Check for different scenarios
    if scoring.evasion_rate == 0 and scoring.precision == 1.0:
        return "Perfect game for Blue Team! All vulnerabilities were found with no false positives. This is rare - the defender performed exceptionally well."
    
    if scoring.evasion_rate > 0.5:
        # Most vulns evaded
        evaded = [m for m in scoring.matches if m.match_type == "missed"]
        if evaded:
            return f"Red Team successfully hid {len(evaded)} vulnerabilities using stealth techniques. LLM detectors often miss subtle contextual issues like missing configurations that 'look' normal."
    
    if scoring.precision < 0.5 and len(scoring.false_positives) > 0:
        return f"Blue Team reported {len(scoring.false_positives)} false positives. This is common with LLM-based detection - they can be overly cautious and flag non-issues."
    
    if scoring.f1_score >= 0.8:
        return "Excellent detection performance! The Blue Team model shows strong security analysis capabilities for this type of infrastructure."
    
    if result.config.difficulty == "hard" and scoring.evasion_rate > 0.3:
        return "Hard difficulty creates sophisticated vulnerabilities using techniques like variable indirection and misleading comments. Even skilled defenders struggle with these."
    
    # Default insight
    return f"This game tested {result.config.difficulty} difficulty vulnerabilities. The balance between detection rate ({scoring.recall:.0%}) and accuracy ({scoring.precision:.0%}) shows the challenge of automated security analysis."


def _display_detailed_analysis(result):
    """Show detailed match-by-match analysis."""
    console.print()
    console.print("[bold]Detailed Match Analysis[/]\n")
    
    for match in result.scoring.matches:
        # Find the corresponding vuln and finding
        vuln = next(
            (v for v in result.red_output.manifest 
             if (v.vuln_id if hasattr(v, 'vuln_id') else v.get('vuln_id')) == match.red_vuln_id),
            None
        )
        
        finding = None
        if match.blue_finding_id:
            finding = next(
                (f for f in result.blue_output.findings 
                 if (f.finding_id if hasattr(f, 'finding_id') else f.get('finding_id')) == match.blue_finding_id),
                None
            )
        
        # Display match details - both exact and partial are successful detections
        match_color = {"exact": "green", "partial": "green", "missed": "red"}.get(match.match_type, "white")
        
        console.print(Panel.fit(
            f"[bold]Red Team ({match.red_vuln_id}):[/]\n"
            f"  {vuln.title if vuln and hasattr(vuln, 'title') else 'Unknown'}\n"
            f"  Resource: {vuln.resource_name if vuln and hasattr(vuln, 'resource_name') else 'Unknown'}\n\n"
            f"[bold]Blue Team ({match.blue_finding_id or 'No match'}):[/]\n"
            f"  {finding.title if finding and hasattr(finding, 'title') else 'Not detected'}\n"
            f"  Resource: {finding.resource_name if finding and hasattr(finding, 'resource_name') else 'N/A'}\n\n"
            f"[bold]Verdict:[/] [{match_color}]{match.match_type.upper()}[/] (confidence: {match.confidence:.0%})\n"
            f"[dim]{match.explanation}[/]",
            title=f"Match: {match.red_vuln_id} → {match.blue_finding_id or '—'}",
            border_style=match_color,
        ))
        console.print()


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
