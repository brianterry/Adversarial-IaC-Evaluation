"""
Game Engine - Orchestrates Red Team vs Blue Team matches

This engine:
1. Runs complete adversarial games (Red generates, Blue detects, Judge scores)
2. Supports different model configurations
3. Tracks game history and statistics
4. Generates comprehensive reports

Part of the Adversarial IaC Evaluation framework.
"""

import asyncio
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..agents.red_team_agent import RedTeamAgent, RedTeamOutput, Difficulty, create_red_team_agent
from ..agents.red_team_pipeline import RedTeamPipeline, PipelineRedTeamOutput, create_red_team_pipeline
from ..agents.blue_team_agent import BlueTeamAgent, BlueTeamOutput, DetectionMode, create_blue_team_agent
from ..agents.blue_team_ensemble import BlueTeamEnsemble, EnsembleOutput, create_blue_team_ensemble
from ..agents.debate_verification import DebateVerificationAgent, DebateVerificationOutput, create_debate_verification_agent
from ..agents.judge_agent import JudgeAgent, ScoringResult, score_results_to_dict
from .scenarios import Scenario, ScenarioGenerator


@dataclass
class GameConfig:
    """Configuration for a game"""
    red_model: str
    blue_model: str
    difficulty: str
    language: str
    cloud_provider: str
    detection_mode: str = "llm_only"
    use_trivy: bool = False
    use_checkov: bool = False
    region: str = "us-east-1"
    
    # Red Team mode configuration
    red_team_mode: str = "single"  # "single" or "pipeline"
    
    # Red Team attack strategy
    red_strategy: str = "balanced"  # Attack strategy options:
    # - "balanced": Standard mix of vulnerability types and stealth (default)
    # - "targeted": Focus on specific vulnerability type (use red_target_type)
    # - "stealth": Fewer vulns but maximum evasion techniques
    # - "blitz": Maximum vulnerabilities, less stealth
    # - "chained": Vulnerabilities that exploit each other in sequence
    red_target_type: Optional[str] = None  # For "targeted" strategy: "encryption", "iam", "network", "logging", "access_control"
    
    # Blue Team mode configuration
    blue_team_mode: str = "single"  # "single" or "ensemble"
    ensemble_specialists: Optional[List[str]] = None  # ["security", "compliance", "architecture"]
    consensus_method: str = "debate"  # "debate", "vote", "union", "intersection"
    
    # Blue Team defense strategy
    blue_strategy: str = "comprehensive"  # Defense strategy options:
    # - "comprehensive": Check for all vulnerability types (default)
    # - "targeted": Focus on specific vulnerability type (use blue_target_type)
    # - "iterative": Multiple analysis passes with refinement
    # - "threat_model": Start with threat model, then hunt for matching vulns
    # - "compliance": Check against compliance framework (use compliance_framework)
    blue_target_type: Optional[str] = None  # For "targeted" strategy
    compliance_framework: Optional[str] = None  # For "compliance" strategy: "hipaa", "pci_dss", "soc2", "cis"
    blue_iterations: int = 1  # For "iterative" strategy: number of passes
    
    # Verification mode configuration
    verification_mode: str = "standard"  # "standard" or "debate"


@dataclass
class GameResult:
    """Complete result from a single game"""
    game_id: str
    scenario: Scenario
    config: GameConfig
    
    # Outputs
    red_output: RedTeamOutput
    blue_output: BlueTeamOutput
    scoring: ScoringResult
    
    # Timing
    red_time_seconds: float
    blue_time_seconds: float
    total_time_seconds: float
    
    # Metadata
    timestamp: str
    
    # Log content (captured during game execution)
    log_content: str = ""
    
    # Mode tracking
    red_team_mode: str = "single"
    blue_team_mode: str = "single"
    verification_mode: str = "standard"
    
    # Red Team Pipeline fields (populated when red_team_mode="pipeline")
    pipeline_stages: Optional[Dict[str, Any]] = None
    architecture_design: Optional[Dict[str, Any]] = None
    
    # Blue Team Ensemble fields (populated when blue_team_mode="ensemble")
    specialist_findings: Optional[Dict[str, List[Dict]]] = None
    consensus_stats: Optional[Dict[str, Any]] = None
    
    # Debate Verification fields (populated when verification_mode="debate")
    debate_results: Optional[List[Dict[str, Any]]] = None
    verified_findings: Optional[List[Dict[str, Any]]] = None
    rejected_findings: Optional[List[Dict[str, Any]]] = None


class GameEngine:
    """
    Orchestrates adversarial IaC security games.
    
    A game consists of:
    1. Red Team generates vulnerable IaC from a scenario
    2. Blue Team analyzes the code for vulnerabilities
    3. Judge scores the match (precision, recall, F1)
    """

    def __init__(
        self,
        output_dir: str = "output/games",
        region: str = "us-east-1",
    ):
        """
        Initialize Game Engine.
        
        Args:
            output_dir: Directory to save game results
            region: AWS region for Bedrock
        """
        self.output_dir = Path(output_dir)
        self.region = region
        self.logger = logging.getLogger("GameEngine")
        self.judge = JudgeAgent()
        self._game_log_buffer: Optional[io.StringIO] = None
        self._game_log_handler: Optional[logging.Handler] = None

    def _start_game_logging(self, game_id: str) -> None:
        """
        Start capturing logs for the current game.
        
        Creates a StringIO buffer and attaches a handler to the root logger
        to capture all log output during the game.
        """
        # Create a string buffer to capture logs
        self._game_log_buffer = io.StringIO()
        
        # Create a handler that writes to the buffer
        self._game_log_handler = logging.StreamHandler(self._game_log_buffer)
        self._game_log_handler.setLevel(logging.DEBUG)
        
        # Use a detailed format for the log file
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._game_log_handler.setFormatter(formatter)
        
        # Attach to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(self._game_log_handler)
        
        # Write header to log
        self._game_log_buffer.write(f"{'='*80}\n")
        self._game_log_buffer.write(f"ADVERSARIAL IAC GAME LOG\n")
        self._game_log_buffer.write(f"Game ID: {game_id}\n")
        self._game_log_buffer.write(f"Started: {datetime.now().isoformat()}\n")
        self._game_log_buffer.write(f"{'='*80}\n\n")

    def _stop_game_logging(self) -> str:
        """
        Stop capturing logs and return the captured log content.
        
        Returns:
            The complete log content as a string
        """
        log_content = ""
        
        if self._game_log_handler:
            # Remove handler from root logger
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._game_log_handler)
            self._game_log_handler.close()
            self._game_log_handler = None
        
        if self._game_log_buffer:
            # Add footer and get content
            self._game_log_buffer.write(f"\n{'='*80}\n")
            self._game_log_buffer.write(f"Game completed: {datetime.now().isoformat()}\n")
            self._game_log_buffer.write(f"{'='*80}\n")
            
            log_content = self._game_log_buffer.getvalue()
            self._game_log_buffer.close()
            self._game_log_buffer = None
        
        return log_content

    async def run_game(
        self,
        scenario: Scenario,
        config: GameConfig,
    ) -> GameResult:
        """
        Run a complete adversarial game.
        
        Args:
            scenario: Test scenario
            config: Game configuration
            
        Returns:
            GameResult with all outputs and scores
        """
        game_id = f"G-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start capturing logs for this game
        self._start_game_logging(game_id)
        
        self.logger.info(f"Starting game {game_id}: {scenario.description[:50]}...")
        self.logger.info(f"Configuration: red_model={config.red_model}, blue_model={config.blue_model}")
        self.logger.info(f"Settings: difficulty={config.difficulty}, language={config.language}, provider={config.cloud_provider}")
        
        start_time = datetime.now()
        
        # Phase 1: Red Team Attack
        self.logger.info(f"Phase 1: Red Team generating adversarial IaC (mode={config.red_team_mode})")
        red_start = datetime.now()
        
        # Track pipeline-specific data
        pipeline_stages = None
        architecture_design = None
        
        if config.red_team_mode == "pipeline":
            self.logger.info("Using multi-agent pipeline attack")
            red_agent = create_red_team_pipeline(
                model_id=config.red_model,
                region=config.region,
                cloud_provider=config.cloud_provider,
                language=config.language,
                difficulty=config.difficulty,
            )
            
            pipeline_output = await red_agent.execute(scenario.to_dict())
            red_output = pipeline_output  # PipelineRedTeamOutput extends RedTeamOutput
            
            # Extract pipeline-specific data
            if isinstance(pipeline_output, PipelineRedTeamOutput):
                pipeline_stages = {
                    name: {"success": stage.success, "data_keys": list(stage.data.keys()) if stage.data else []}
                    for name, stage in pipeline_output.pipeline_stages.items()
                }
                architecture_design = pipeline_output.architecture_design
        else:
            red_agent = create_red_team_agent(
                model_id=config.red_model,
                region=config.region,
                difficulty=config.difficulty,
                cloud_provider=config.cloud_provider,
                language=config.language,
                strategy=config.red_strategy,
                target_type=config.red_target_type,
            )
            
            red_output = await red_agent.execute(scenario.to_dict())
        
        red_time = (datetime.now() - red_start).total_seconds()
        
        self.logger.info(
            f"Red Team complete: {len(red_output.manifest)} vulns, "
            f"mode={config.red_team_mode}, stealth={red_output.stealth_score}, time={red_time:.1f}s"
        )
        
        # Phase 2: Blue Team Defense
        self.logger.info(f"Phase 2: Blue Team analyzing code (mode={config.blue_team_mode})")
        blue_start = datetime.now()
        
        # Choose between single agent and ensemble
        specialist_findings = None
        consensus_stats = None
        
        if config.blue_team_mode == "ensemble":
            self.logger.info("Using multi-agent ensemble detection")
            blue_agent = create_blue_team_ensemble(
                model_id=config.blue_model,
                region=config.region,
                language=config.language,
                specialists=config.ensemble_specialists,
                consensus_method=config.consensus_method,
            )
            
            ensemble_output = await blue_agent.execute(red_output.code)
            blue_output = ensemble_output  # EnsembleOutput extends BlueTeamOutput
            
            # Extract ensemble-specific data
            if isinstance(ensemble_output, EnsembleOutput):
                specialist_findings = ensemble_output.specialist_findings
                consensus_stats = ensemble_output.consensus_stats
        else:
            blue_agent = create_blue_team_agent(
                model_id=config.blue_model,
                region=config.region,
                mode=config.detection_mode,
                language=config.language,
                use_trivy=config.use_trivy,
                use_checkov=config.use_checkov,
                strategy=config.blue_strategy,
                target_type=config.blue_target_type,
                compliance_framework=config.compliance_framework,
                iterations=config.blue_iterations,
                scenario_description=scenario.description,
            )
            
            blue_output = await blue_agent.execute(red_output.code)
        
        blue_time = (datetime.now() - blue_start).total_seconds()
        
        self.logger.info(
            f"Blue Team complete: {len(blue_output.findings)} findings, "
            f"mode={config.blue_team_mode}, time={blue_time:.1f}s"
        )
        
        # Convert manifest to dict format for judge
        manifest_dicts = [
            {
                "vuln_id": v.vuln_id,
                "rule_id": v.rule_id,
                "title": v.title,
                "type": v.type,
                "severity": v.severity,
                "resource_name": v.resource_name,
                "resource_type": v.resource_type,
                "vulnerable_attribute": v.vulnerable_attribute,
            }
            for v in red_output.manifest
        ]
        
        findings_dicts = [
            {
                "finding_id": f.finding_id,
                "resource_name": f.resource_name,
                "resource_type": f.resource_type,
                "vulnerability_type": f.vulnerability_type,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "evidence": f.evidence,
            }
            for f in blue_output.findings
        ]
        
        # Phase 3: Verification and Scoring
        debate_results = None
        verified_findings = None
        rejected_findings = None
        
        if config.verification_mode == "debate":
            # Phase 3a: Adversarial Debate Verification
            self.logger.info("Phase 3: Adversarial debate verification")
            
            debate_agent = create_debate_verification_agent(
                model_id=config.blue_model,  # Use Blue Team model for verification
                region=config.region,
                language=config.language,
            )
            
            debate_output = await debate_agent.verify(
                findings=blue_output.findings,
                code=red_output.code,
                manifest=manifest_dicts,
            )
            
            scoring = debate_output.scoring
            
            # Extract debate-specific data
            debate_results = [
                {
                    "finding_id": r.finding_id,
                    "verdict": r.verdict,
                    "confidence": r.verdict_confidence,
                    "final_severity": r.final_severity,
                }
                for r in debate_output.debate_results
            ]
            verified_findings = [
                {"finding_id": f.finding_id, "title": f.title, "severity": f.severity}
                for f in debate_output.verified_findings
            ]
            rejected_findings = [
                {"finding_id": f.finding_id, "title": f.title, "severity": f.severity}
                for f in debate_output.rejected_findings
            ]
            
            self.logger.info(
                f"Debate complete: {len(debate_output.verified_findings)} verified, "
                f"{len(debate_output.rejected_findings)} rejected"
            )
        else:
            # Phase 3b: Standard Judge Scoring
            self.logger.info("Phase 3: Judge scoring match")
            scoring = self.judge.score(manifest_dicts, findings_dicts)
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(
            f"Game {game_id} complete: "
            f"P={scoring.precision:.2f}, R={scoring.recall:.2f}, F1={scoring.f1_score:.2f}, "
            f"time={total_time:.1f}s"
        )
        
        # Log summary of results
        self.logger.info(f"Summary: {len(red_output.manifest)} vulnerabilities injected, {len(blue_output.findings)} findings detected")
        self.logger.info(f"Evasion rate: {scoring.evasion_rate:.2%} ({len(scoring.false_negatives)} evaded)")
        
        # Stop capturing logs and get content
        log_content = self._stop_game_logging()
        
        # Compile result
        result = GameResult(
            game_id=game_id,
            scenario=scenario,
            config=config,
            red_output=red_output,
            blue_output=blue_output,
            scoring=scoring,
            red_time_seconds=red_time,
            blue_time_seconds=blue_time,
            total_time_seconds=total_time,
            timestamp=datetime.now().isoformat(),
            log_content=log_content,
            red_team_mode=config.red_team_mode,
            blue_team_mode=config.blue_team_mode,
            verification_mode=config.verification_mode,
            pipeline_stages=pipeline_stages,
            architecture_design=architecture_design,
            specialist_findings=specialist_findings,
            consensus_stats=consensus_stats,
            debate_results=debate_results,
            verified_findings=verified_findings,
            rejected_findings=rejected_findings,
        )
        
        return result

    async def run_experiment(
        self,
        scenarios: List[Scenario],
        configs: List[GameConfig],
        save_results: bool = True,
    ) -> List[GameResult]:
        """
        Run multiple games as an experiment.
        
        Args:
            scenarios: List of scenarios to test
            configs: List of configurations (will run all scenarios with each config)
            save_results: Whether to save results to disk
            
        Returns:
            List of all GameResults
        """
        results = []
        total_games = len(scenarios) * len(configs)
        
        self.logger.info(f"Starting experiment: {total_games} games")
        
        game_num = 0
        for config in configs:
            for scenario in scenarios:
                game_num += 1
                self.logger.info(f"Game {game_num}/{total_games}")
                
                try:
                    result = await self.run_game(scenario, config)
                    results.append(result)
                    
                    if save_results:
                        self._save_game_result(result)
                        
                except Exception as e:
                    self.logger.error(f"Game failed: {e}")
                    continue
        
        # Save experiment summary
        if save_results and results:
            self._save_experiment_summary(results)
        
        return results

    def _save_game_result(self, result: GameResult) -> Path:
        """Save a single game result to disk."""
        game_dir = self.output_dir / result.game_id
        game_dir.mkdir(parents=True, exist_ok=True)
        
        # Save code files
        code_dir = game_dir / "code"
        code_dir.mkdir(exist_ok=True)
        for filename, content in result.red_output.code.items():
            (code_dir / filename).write_text(content)
        
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
            }
            for v in result.red_output.manifest
        ]
        (game_dir / "red_manifest.json").write_text(json.dumps(manifest_data, indent=2))
        
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
                "source": f.source,
            }
            for f in result.blue_output.findings
        ]
        (game_dir / "blue_findings.json").write_text(json.dumps(findings_data, indent=2))
        
        # Save scoring
        scoring_data = score_results_to_dict(result.scoring)
        (game_dir / "scoring.json").write_text(json.dumps(scoring_data, indent=2))
        
        # Save game metadata
        metadata = {
            "game_id": result.game_id,
            "scenario": result.scenario.to_dict(),
            "config": {
                "red_model": result.config.red_model,
                "blue_model": result.config.blue_model,
                "difficulty": result.config.difficulty,
                "language": result.config.language,
                "cloud_provider": result.config.cloud_provider,
                "detection_mode": result.config.detection_mode,
                "red_team_mode": result.config.red_team_mode,
                "blue_team_mode": result.config.blue_team_mode,
                "verification_mode": result.config.verification_mode,
            },
            "timing": {
                "red_time_seconds": result.red_time_seconds,
                "blue_time_seconds": result.blue_time_seconds,
                "total_time_seconds": result.total_time_seconds,
            },
            "summary": {
                "red_vulns": len(result.red_output.manifest),
                "blue_findings": len(result.blue_output.findings),
                "precision": result.scoring.precision,
                "recall": result.scoring.recall,
                "f1_score": result.scoring.f1_score,
                "evasion_rate": result.scoring.evasion_rate,
            },
            "timestamp": result.timestamp,
        }
        
        # Add Red Team Pipeline data if applicable
        if result.red_team_mode == "pipeline":
            metadata["pipeline"] = {
                "stages": result.pipeline_stages,
                "architecture_design": result.architecture_design,
            }
            # Save architecture design separately
            if result.architecture_design:
                (game_dir / "architecture_design.json").write_text(
                    json.dumps(result.architecture_design, indent=2)
                )
        
        # Add Blue Team Ensemble data if applicable
        if result.blue_team_mode == "ensemble":
            metadata["ensemble"] = {
                "consensus_method": result.config.consensus_method,
                "specialists": result.config.ensemble_specialists or ["security", "compliance", "architecture"],
                "consensus_stats": result.consensus_stats,
            }
        
        # Add Debate Verification data if applicable
        if result.verification_mode == "debate":
            metadata["debate"] = {
                "verified_count": len(result.verified_findings) if result.verified_findings else 0,
                "rejected_count": len(result.rejected_findings) if result.rejected_findings else 0,
            }
            # Save debate results separately
            if result.debate_results:
                (game_dir / "debate_results.json").write_text(
                    json.dumps(result.debate_results, indent=2)
                )
        
        (game_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        
        # Save specialist findings if ensemble mode
        if result.specialist_findings:
            (game_dir / "specialist_findings.json").write_text(
                json.dumps(result.specialist_findings, indent=2)
            )
        
        # Save game log
        if result.log_content:
            (game_dir / "game.log").write_text(result.log_content)
        
        self.logger.info(f"Saved game result to {game_dir}")
        return game_dir

    def _save_experiment_summary(self, results: List[GameResult]) -> Path:
        """Save experiment summary with aggregate statistics."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = self.output_dir / f"experiment_summary_{timestamp}.json"
        
        # Aggregate metrics
        precisions = [r.scoring.precision for r in results]
        recalls = [r.scoring.recall for r in results]
        f1_scores = [r.scoring.f1_score for r in results]
        evasion_rates = [r.scoring.evasion_rate for r in results]
        
        summary = {
            "experiment_timestamp": timestamp,
            "total_games": len(results),
            "aggregate_metrics": {
                "precision": {
                    "mean": sum(precisions) / len(precisions),
                    "min": min(precisions),
                    "max": max(precisions),
                },
                "recall": {
                    "mean": sum(recalls) / len(recalls),
                    "min": min(recalls),
                    "max": max(recalls),
                },
                "f1_score": {
                    "mean": sum(f1_scores) / len(f1_scores),
                    "min": min(f1_scores),
                    "max": max(f1_scores),
                },
                "evasion_rate": {
                    "mean": sum(evasion_rates) / len(evasion_rates),
                    "min": min(evasion_rates),
                    "max": max(evasion_rates),
                },
            },
            "games": [
                {
                    "game_id": r.game_id,
                    "scenario": r.scenario.description[:50],
                    "difficulty": r.config.difficulty,
                    "precision": r.scoring.precision,
                    "recall": r.scoring.recall,
                    "f1_score": r.scoring.f1_score,
                }
                for r in results
            ],
        }
        
        summary_path.write_text(json.dumps(summary, indent=2))
        self.logger.info(f"Saved experiment summary to {summary_path}")
        
        return summary_path
