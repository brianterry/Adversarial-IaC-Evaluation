"""
Blue Team Ensemble - Multi-Agent Collaborative Detection

Orchestrates multiple specialist agents to detect vulnerabilities:
1. SecurityExpert - Finds security vulnerabilities
2. ComplianceAgent - Checks regulatory compliance  
3. ArchitectureAgent - Evaluates best practices
4. ConsensusAgent - Synthesizes findings through debate/voting

Part of the Adversarial IaC Evaluation framework.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from .blue_team_agent import BlueTeamOutput, Finding
from .specialists import (
    SecurityExpert,
    ComplianceAgent,
    ArchitectureAgent,
    ConsensusAgent,
    SpecialistFinding,
    SpecialistOutput,
)


@dataclass
class EnsembleOutput(BlueTeamOutput):
    """Extended output from Blue Team Ensemble"""
    # Inherit findings, analysis_summary, detection_stats from BlueTeamOutput
    
    # Ensemble-specific fields
    specialist_findings: Dict[str, List[Dict]] = field(default_factory=dict)
    consensus_method: str = "debate"
    consensus_stats: Dict[str, Any] = field(default_factory=dict)
    debate_notes: str = ""


class BlueTeamEnsemble:
    """
    Multi-agent ensemble for vulnerability detection.
    
    Coordinates multiple specialist agents and synthesizes their
    findings through configurable consensus methods:
    - debate: LLM-based synthesis with reasoning
    - vote: Majority voting (2+ specialists agree)
    - union: Include all unique findings
    - intersection: Only unanimous findings
    """

    AVAILABLE_SPECIALISTS = ["security", "compliance", "architecture"]
    CONSENSUS_METHODS = ["debate", "vote", "union", "intersection"]

    def __init__(
        self,
        llm: BaseChatModel,
        language: str = "terraform",
        specialists: Optional[List[str]] = None,
        consensus_method: str = "debate",
        run_parallel: bool = True,
    ):
        """
        Initialize Blue Team Ensemble.
        
        Args:
            llm: LangChain chat model for all agents
            language: IaC language (terraform, cloudformation)
            specialists: Which specialists to use (default: all)
            consensus_method: How to synthesize findings
            run_parallel: Whether to run specialists concurrently
        """
        self.llm = llm
        self.language = language
        self.specialists_config = specialists or self.AVAILABLE_SPECIALISTS
        self.consensus_method = consensus_method
        self.run_parallel = run_parallel
        self.logger = logging.getLogger("BlueTeamEnsemble")
        
        # Validate inputs
        if consensus_method not in self.CONSENSUS_METHODS:
            raise ValueError(f"Invalid consensus method. Choose from: {self.CONSENSUS_METHODS}")
        
        for spec in self.specialists_config:
            if spec not in self.AVAILABLE_SPECIALISTS:
                raise ValueError(f"Unknown specialist: {spec}. Choose from: {self.AVAILABLE_SPECIALISTS}")
        
        # Initialize specialists
        self._init_specialists()
        
        # Initialize consensus agent
        self.consensus_agent = ConsensusAgent(
            llm=llm if consensus_method == "debate" else None,
            method=consensus_method,
        )

    def _init_specialists(self):
        """Initialize the specialist agents."""
        self.specialists: Dict[str, Any] = {}
        
        if "security" in self.specialists_config:
            self.specialists["security_expert"] = SecurityExpert(
                llm=self.llm,
                language=self.language,
            )
        
        if "compliance" in self.specialists_config:
            self.specialists["compliance_agent"] = ComplianceAgent(
                llm=self.llm,
                language=self.language,
            )
        
        if "architecture" in self.specialists_config:
            self.specialists["architecture_agent"] = ArchitectureAgent(
                llm=self.llm,
                language=self.language,
            )
        
        self.logger.info(f"Initialized {len(self.specialists)} specialists: {list(self.specialists.keys())}")

    async def execute(self, code: Dict[str, str]) -> EnsembleOutput:
        """
        Execute ensemble detection on IaC code.
        
        Args:
            code: Dictionary of filename -> content
            
        Returns:
            EnsembleOutput with synthesized findings
        """
        self.logger.info(f"Ensemble analyzing code with {len(self.specialists)} specialists")
        
        # Step 1: Run all specialists
        if self.run_parallel:
            specialist_outputs = await self._run_specialists_parallel(code)
        else:
            specialist_outputs = await self._run_specialists_sequential(code)
        
        self.logger.info(f"All specialists complete. Running {self.consensus_method} consensus...")
        
        # Step 2: Consensus synthesis
        consensus_result = await self.consensus_agent.synthesize(specialist_outputs)
        
        # Step 3: Convert to BlueTeamOutput-compatible format
        findings = self._convert_to_findings(consensus_result.findings)
        
        # Step 4: Build specialist findings dict for analysis
        specialist_findings = {}
        for output in specialist_outputs:
            specialist_findings[output.specialist] = [
                {
                    "finding_id": f.finding_id,
                    "resource_name": f.resource_name,
                    "vulnerability_type": f.vulnerability_type,
                    "severity": f.severity,
                    "title": f.title,
                    "confidence": f.confidence,
                }
                for f in output.findings
            ]
        
        # Step 5: Compile output
        output = EnsembleOutput(
            findings=findings,
            analysis_summary=self._create_summary(findings, code, consensus_result),
            detection_stats={
                "mode": "ensemble",
                "consensus_method": self.consensus_method,
                "total_findings": len(findings),
                "by_source": {"ensemble": len(findings)},
                "by_severity": self._count_by_severity(findings),
                "specialists_used": list(self.specialists.keys()),
            },
            specialist_findings=specialist_findings,
            consensus_method=self.consensus_method,
            consensus_stats={
                "unanimous": consensus_result.unanimous_count,
                "majority": consensus_result.majority_count,
                "specialist_only": consensus_result.specialist_only_count,
                "conflicts_resolved": consensus_result.conflicts_resolved,
                "specialist_counts": consensus_result.specialist_counts,
            },
            debate_notes=consensus_result.debate_notes,
        )
        
        self.logger.info(
            f"Ensemble complete: {len(findings)} consensus findings "
            f"(unanimous={consensus_result.unanimous_count}, "
            f"majority={consensus_result.majority_count})"
        )
        
        return output

    async def _run_specialists_parallel(
        self,
        code: Dict[str, str],
    ) -> List[SpecialistOutput]:
        """Run all specialists concurrently."""
        tasks = []
        for name, specialist in self.specialists.items():
            self.logger.debug(f"Starting {name} analysis...")
            tasks.append(specialist.analyze(code))
        
        outputs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        valid_outputs = []
        for i, output in enumerate(outputs):
            specialist_name = list(self.specialists.keys())[i]
            if isinstance(output, Exception):
                self.logger.error(f"{specialist_name} failed: {output}")
                # Create empty output for failed specialist
                valid_outputs.append(SpecialistOutput(
                    specialist=specialist_name,
                    findings=[],
                    summary=f"Analysis failed: {output}",
                ))
            else:
                valid_outputs.append(output)
        
        return valid_outputs

    async def _run_specialists_sequential(
        self,
        code: Dict[str, str],
    ) -> List[SpecialistOutput]:
        """Run specialists one at a time."""
        outputs = []
        
        for name, specialist in self.specialists.items():
            self.logger.info(f"Running {name}...")
            try:
                output = await specialist.analyze(code)
                outputs.append(output)
            except Exception as e:
                self.logger.error(f"{name} failed: {e}")
                outputs.append(SpecialistOutput(
                    specialist=name,
                    findings=[],
                    summary=f"Analysis failed: {e}",
                ))
        
        return outputs

    def _convert_to_findings(
        self,
        specialist_findings: List[SpecialistFinding],
    ) -> List[Finding]:
        """Convert SpecialistFinding to Finding for compatibility."""
        findings = []
        
        for sf in specialist_findings:
            finding = Finding(
                finding_id=sf.finding_id,
                resource_name=sf.resource_name,
                resource_type=sf.resource_type,
                vulnerability_type=sf.vulnerability_type,
                severity=sf.severity,
                title=sf.title,
                description=sf.description,
                evidence=sf.evidence,
                line_number_estimate=0,  # Not available from specialists
                confidence=sf.confidence,
                reasoning=sf.reasoning,
                remediation="",  # Not available from specialists
                source="ensemble",
            )
            findings.append(finding)
        
        return findings

    def _create_summary(
        self,
        findings: List[Finding],
        code: Dict[str, str],
        consensus_result,
    ) -> Dict[str, Any]:
        """Create analysis summary."""
        import re
        
        total_lines = sum(len(c.split("\n")) for c in code.values())
        
        # Count resources
        resource_count = 0
        for content in code.values():
            resource_count += len(re.findall(r'resource\s+"[^"]+"\s+"[^"]+"', content))
            resource_count += len(re.findall(r'^\s{2}[A-Z][a-zA-Z0-9]+:\s*$', content, re.MULTILINE))
        
        return {
            "total_resources_analyzed": max(resource_count, 1),
            "total_lines": total_lines,
            "total_findings": len(findings),
            "findings_by_severity": self._count_by_severity(findings),
            "risk_assessment": self._assess_risk(findings),
            "confidence_level": self._overall_confidence(findings),
            "ensemble_stats": {
                "specialists_used": len(self.specialists),
                "consensus_method": self.consensus_method,
                "unanimous_findings": consensus_result.unanimous_count,
                "majority_findings": consensus_result.majority_count,
            },
        }

    def _count_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.severity.lower()
            if sev in counts:
                counts[sev] += 1
        return counts

    def _assess_risk(self, findings: List[Finding]) -> str:
        """Assess overall risk level."""
        severity_counts = self._count_by_severity(findings)
        
        if severity_counts["critical"] > 0:
            return "critical"
        elif severity_counts["high"] >= 2:
            return "high"
        elif severity_counts["high"] == 1 or severity_counts["medium"] >= 3:
            return "medium"
        elif findings:
            return "low"
        else:
            return "secure"

    def _overall_confidence(self, findings: List[Finding]) -> str:
        """Calculate overall confidence level."""
        if not findings:
            return "high"
        
        avg_confidence = sum(f.confidence for f in findings) / len(findings)
        
        if avg_confidence >= 0.8:
            return "high"
        elif avg_confidence >= 0.5:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> Dict[str, Any]:
        """Return ensemble configuration as dictionary."""
        return {
            "agent_type": "BlueTeamEnsemble",
            "mode": "ensemble",
            "language": self.language,
            "specialists": self.specialists_config,
            "consensus_method": self.consensus_method,
            "run_parallel": self.run_parallel,
        }


def create_blue_team_ensemble(
    model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    region: str = "us-east-1",
    language: str = "terraform",
    specialists: Optional[List[str]] = None,
    consensus_method: str = "debate",
    run_parallel: bool = True,
) -> BlueTeamEnsemble:
    """
    Create a Blue Team Ensemble with AWS Bedrock.
    
    Args:
        model_id: Bedrock model ID
        region: AWS region
        language: terraform or cloudformation
        specialists: Which specialists to use (default: all)
        consensus_method: debate, vote, union, or intersection
        run_parallel: Run specialists concurrently
        
    Returns:
        Configured BlueTeamEnsemble
    """
    from langchain_aws import ChatBedrock
    
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        model_kwargs={
            "temperature": 0.3,
            "max_tokens": 8192,
        },
    )
    
    return BlueTeamEnsemble(
        llm=llm,
        language=language,
        specialists=specialists,
        consensus_method=consensus_method,
        run_parallel=run_parallel,
    )
