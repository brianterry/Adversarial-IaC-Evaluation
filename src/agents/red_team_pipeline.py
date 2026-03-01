"""
Red Team Pipeline - Multi-Agent Attack Chain

Orchestrates specialized agents for adversarial IaC generation:
1. Architect - Designs infrastructure structure
2. Vulnerability Selector - Chooses vulnerabilities to inject
3. Code Generator - Writes the IaC code
4. Stealth Reviewer - Refines to evade detection

Part of the Adversarial IaC Evaluation framework.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from .red_team_agent import RedTeamOutput, Difficulty, VulnerabilityManifest
from .red_specialists import (
    ArchitectAgent,
    VulnerabilitySelectorAgent,
    CodeGeneratorAgent,
    StealthReviewerAgent,
    PipelineOutput,
)


@dataclass
class PipelineRedTeamOutput(RedTeamOutput):
    """Extended output from Red Team Pipeline"""
    # Inherit code, manifest, difficulty, stealth_score, generation_stats
    
    # Pipeline-specific fields
    pipeline_stages: Dict[str, PipelineOutput] = field(default_factory=dict)
    architecture_design: Dict[str, Any] = field(default_factory=dict)
    stealth_report: Dict[str, Any] = field(default_factory=dict)


class RedTeamPipeline:
    """
    Multi-agent pipeline for adversarial IaC generation.
    
    Sequential pipeline:
    Scenario → Architect → Selector → Generator → Reviewer → Output
    
    Each stage builds on the previous, enabling specialization
    and iterative refinement.
    """

    PIPELINE_STAGES = ["architect", "vulnerability_selector", "code_generator", "stealth_reviewer"]

    def __init__(
        self,
        llm: BaseChatModel,
        cloud_provider: str = "aws",
        language: str = "terraform",
        difficulty: str = "medium",
        vuln_count: int = 5,
    ):
        """
        Initialize Red Team Pipeline.
        
        Args:
            llm: LangChain chat model for all agents
            cloud_provider: Target cloud provider
            language: IaC language
            difficulty: Vulnerability difficulty level
            vuln_count: Number of vulnerabilities to inject
        """
        self.llm = llm
        self.cloud_provider = cloud_provider
        self.language = language
        self.difficulty = difficulty
        self.vuln_count = vuln_count
        self.logger = logging.getLogger("RedTeamPipeline")
        
        # Initialize pipeline stages
        self._init_stages()

    def _init_stages(self):
        """Initialize all pipeline stages."""
        self.architect = ArchitectAgent(
            llm=self.llm,
            cloud_provider=self.cloud_provider,
            language=self.language,
        )
        
        self.selector = VulnerabilitySelectorAgent(
            llm=self.llm,
            cloud_provider=self.cloud_provider,
            language=self.language,
            difficulty=self.difficulty,
            vuln_count=self.vuln_count,
        )
        
        self.generator = CodeGeneratorAgent(
            llm=self.llm,
            cloud_provider=self.cloud_provider,
            language=self.language,
        )
        
        self.reviewer = StealthReviewerAgent(
            llm=self.llm,
            cloud_provider=self.cloud_provider,
            language=self.language,
            difficulty=self.difficulty,
        )
        
        self.logger.info(f"Initialized {len(self.PIPELINE_STAGES)} pipeline stages")

    async def execute(self, scenario: Dict[str, Any]) -> PipelineRedTeamOutput:
        """
        Execute the full Red Team pipeline.
        
        Args:
            scenario: Scenario dictionary with description, etc.
            
        Returns:
            PipelineRedTeamOutput with code, manifest, and pipeline data
        """
        self.logger.info("Starting Red Team Pipeline execution")
        
        pipeline_outputs: Dict[str, PipelineOutput] = {}
        
        # Stage 1: Architect
        self.logger.info("Stage 1/4: Architect designing infrastructure...")
        architect_output = await self.architect.execute(scenario)
        pipeline_outputs["architect"] = architect_output
        
        if not architect_output.success:
            self.logger.error("Architect stage failed")
            return self._create_error_output(pipeline_outputs, "Architect failed")
        
        architecture = architect_output.data
        self.logger.info(f"Architecture designed: {len(architecture.get('components', []))} components")
        
        # Stage 2: Vulnerability Selector
        self.logger.info("Stage 2/4: Selecting vulnerabilities...")
        selector_output = await self.selector.execute(architecture)
        pipeline_outputs["vulnerability_selector"] = selector_output
        
        if not selector_output.success:
            self.logger.error("Vulnerability selector stage failed")
            return self._create_error_output(pipeline_outputs, "Selector failed")
        
        vulnerabilities = selector_output.data
        self.logger.info(f"Selected {len(vulnerabilities.get('selected_vulnerabilities', []))} vulnerabilities")
        
        # Stage 3: Code Generator
        self.logger.info("Stage 3/4: Generating IaC code...")
        generator_input = {
            "architecture": architecture,
            "vulnerabilities": vulnerabilities,
        }
        generator_output = await self.generator.execute(generator_input)
        pipeline_outputs["code_generator"] = generator_output
        
        if not generator_output.success:
            self.logger.error("Code generator stage failed")
            return self._create_error_output(pipeline_outputs, "Generator failed")
        
        code = generator_output.data.get("code", {})
        implementation_notes = generator_output.data.get("implementation_notes", [])
        self.logger.info(f"Generated {len(code)} code files")
        
        # Stage 4: Stealth Reviewer
        self.logger.info("Stage 4/4: Applying stealth refinements...")
        reviewer_input = {
            "code": code,
            "vulnerabilities": vulnerabilities,
            "implementation_notes": implementation_notes,
        }
        reviewer_output = await self.reviewer.execute(reviewer_input)
        pipeline_outputs["stealth_reviewer"] = reviewer_output
        
        if not reviewer_output.success:
            self.logger.warning("Stealth reviewer failed, using original code")
            final_code = code
            stealth_report = {}
        else:
            final_code = reviewer_output.data.get("code", code)
            stealth_report = reviewer_output.data.get("stealth_report", {})
            
            # If reviewer didn't return code, use original
            if not final_code:
                final_code = code
        
        self.logger.info(f"Stealth score: {stealth_report.get('overall_stealth_score', 'N/A')}")
        
        # Create final manifest
        manifest = self.reviewer.create_final_manifest(
            vulnerabilities=vulnerabilities,
            implementation_notes=implementation_notes,
            stealth_report=stealth_report,
        )
        
        # Convert to VulnerabilityManifest objects
        manifest_objects = [
            VulnerabilityManifest(
                vuln_id=v.get("vuln_id", ""),
                rule_id=v.get("rule_id", ""),
                title=v.get("title", ""),
                type=v.get("type", ""),
                severity=v.get("severity", "medium"),
                resource_name=v.get("resource_name", ""),
                resource_type=v.get("resource_type", ""),
                line_number_estimate=v.get("line_number_estimate", 0),
                vulnerable_attribute=v.get("vulnerable_attribute", ""),
                vulnerable_value=v.get("vulnerable_value", ""),
                stealth_technique=v.get("stealth_technique", ""),
                detection_hint=v.get("detection_hint", ""),
            )
            for v in manifest
        ]
        
        # Compile final output
        output = PipelineRedTeamOutput(
            code=final_code,
            manifest=manifest_objects,
            difficulty=Difficulty(self.difficulty),
            stealth_score=stealth_report.get("overall_stealth_score", 0.5) > 0.5,
            generation_stats={
                "pipeline_mode": True,
                "stages_completed": len([p for p in pipeline_outputs.values() if p.success]),
                "total_stages": len(self.PIPELINE_STAGES),
                "architecture_components": len(architecture.get("components", [])),
                "vulnerabilities_selected": len(vulnerabilities.get("selected_vulnerabilities", [])),
                "code_files_generated": len(final_code),
            },
            pipeline_stages=pipeline_outputs,
            architecture_design=architecture,
            stealth_report=stealth_report,
        )
        
        self.logger.info(
            f"Pipeline complete: {len(manifest_objects)} vulns, "
            f"{len(final_code)} files, stealth={output.stealth_score}"
        )
        
        return output

    def _create_error_output(
        self,
        pipeline_outputs: Dict[str, PipelineOutput],
        error_msg: str,
    ) -> PipelineRedTeamOutput:
        """Create an error output when pipeline fails."""
        return PipelineRedTeamOutput(
            code={},
            manifest=[],
            difficulty=Difficulty(self.difficulty),
            stealth_score=False,
            generation_stats={
                "pipeline_mode": True,
                "error": error_msg,
                "stages_completed": len([p for p in pipeline_outputs.values() if p.success]),
                "total_stages": len(self.PIPELINE_STAGES),
            },
            pipeline_stages=pipeline_outputs,
            architecture_design={},
            stealth_report={},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return pipeline configuration as dictionary."""
        return {
            "agent_type": "RedTeamPipeline",
            "mode": "pipeline",
            "cloud_provider": self.cloud_provider,
            "language": self.language,
            "difficulty": self.difficulty,
            "vuln_count": self.vuln_count,
            "stages": self.PIPELINE_STAGES,
        }


def create_red_team_pipeline(
    model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    region: str = "us-east-1",
    cloud_provider: str = "aws",
    language: str = "terraform",
    difficulty: str = "medium",
    vuln_count: int = 5,
) -> RedTeamPipeline:
    """
    Create a Red Team Pipeline with AWS Bedrock.
    
    Args:
        model_id: Bedrock model ID
        region: AWS region
        cloud_provider: Target cloud provider
        language: terraform or cloudformation
        difficulty: easy, medium, or hard
        vuln_count: Number of vulnerabilities to inject
        
    Returns:
        Configured RedTeamPipeline
    """
    from langchain_aws import ChatBedrock
    
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        model_kwargs={
            "temperature": 0.7,  # Higher for creative attack generation
            "max_tokens": 8192,
        },
    )
    
    return RedTeamPipeline(
        llm=llm,
        cloud_provider=cloud_provider,
        language=language,
        difficulty=difficulty,
        vuln_count=vuln_count,
    )
