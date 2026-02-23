"""
Consensus Agent

Synthesizes findings from all specialist agents through debate/voting.
Resolves conflicts, removes duplicates, and produces final findings.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from ...prompts import BlueTeamSpecialistPrompts
from .base import SpecialistFinding, SpecialistOutput


@dataclass
class ConsensusResult:
    """Result from consensus process"""
    findings: List[SpecialistFinding]
    specialist_counts: Dict[str, int]
    unanimous_count: int
    majority_count: int
    specialist_only_count: int
    conflicts_resolved: int
    debate_notes: str
    raw_response: str = ""


class ConsensusAgent:
    """
    Consensus agent that synthesizes findings from multiple specialists.
    
    Supports multiple consensus methods:
    - debate: LLM reviews all findings and synthesizes
    - vote: Majority voting (2+ specialists agree)
    - union: Include all findings from all specialists
    - intersection: Only include findings all specialists agree on
    """

    CONSENSUS_METHODS = ["debate", "vote", "union", "intersection"]

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        method: str = "debate",
    ):
        """
        Initialize consensus agent.
        
        Args:
            llm: LangChain chat model (required for 'debate' method)
            method: Consensus method to use
        """
        if method not in self.CONSENSUS_METHODS:
            raise ValueError(f"Invalid method. Choose from: {self.CONSENSUS_METHODS}")
        
        self.llm = llm
        self.method = method
        self.logger = logging.getLogger("ConsensusAgent")
        
        if method == "debate" and llm is None:
            raise ValueError("LLM is required for 'debate' consensus method")

    async def synthesize(
        self,
        specialist_outputs: List[SpecialistOutput],
    ) -> ConsensusResult:
        """
        Synthesize findings from multiple specialists.
        
        Args:
            specialist_outputs: Outputs from all specialist agents
            
        Returns:
            ConsensusResult with synthesized findings
        """
        self.logger.info(f"Synthesizing findings using '{self.method}' method")
        
        if self.method == "debate":
            return await self._debate_consensus(specialist_outputs)
        elif self.method == "vote":
            return self._vote_consensus(specialist_outputs)
        elif self.method == "union":
            return self._union_consensus(specialist_outputs)
        elif self.method == "intersection":
            return self._intersection_consensus(specialist_outputs)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    async def _debate_consensus(
        self,
        specialist_outputs: List[SpecialistOutput],
    ) -> ConsensusResult:
        """Use LLM to debate and synthesize findings."""
        
        # Format specialist findings for the prompt
        security_findings = self._format_findings(
            self._get_specialist_output(specialist_outputs, "security_expert")
        )
        compliance_findings = self._format_findings(
            self._get_specialist_output(specialist_outputs, "compliance_agent")
        )
        architecture_findings = self._format_findings(
            self._get_specialist_output(specialist_outputs, "architecture_agent")
        )
        
        # Build consensus prompt
        prompt = BlueTeamSpecialistPrompts.CONSENSUS_AGENT.format(
            security_findings=security_findings,
            compliance_findings=compliance_findings,
            architecture_findings=architecture_findings,
        )
        
        # Get LLM response
        response = await self._invoke_llm(prompt)
        
        # Parse consensus findings
        findings, stats = self._parse_consensus_response(response)
        
        # Count specialist findings
        specialist_counts = {
            so.specialist: len(so.findings)
            for so in specialist_outputs
        }
        
        self.logger.info(f"Consensus reached: {len(findings)} final findings")
        
        return ConsensusResult(
            findings=findings,
            specialist_counts=specialist_counts,
            unanimous_count=stats.get("unanimous", 0),
            majority_count=stats.get("majority", 0),
            specialist_only_count=stats.get("specialist_only", 0),
            conflicts_resolved=stats.get("conflicts_resolved", 0),
            debate_notes=stats.get("debate_notes", ""),
            raw_response=response,
        )

    def _vote_consensus(
        self,
        specialist_outputs: List[SpecialistOutput],
    ) -> ConsensusResult:
        """Use majority voting for consensus."""
        
        # Group findings by resource and issue type
        finding_groups: Dict[str, List[SpecialistFinding]] = {}
        
        for output in specialist_outputs:
            for finding in output.findings:
                key = self._get_finding_key(finding)
                if key not in finding_groups:
                    finding_groups[key] = []
                finding_groups[key].append(finding)
        
        # Filter by vote threshold (2+ specialists)
        consensus_findings = []
        unanimous = 0
        majority = 0
        
        for key, group in finding_groups.items():
            specialists = set(f.specialist for f in group)
            
            if len(specialists) >= 2:
                # Take the finding with highest confidence
                best_finding = max(group, key=lambda f: f.confidence)
                
                # Create consensus finding
                consensus_finding = SpecialistFinding(
                    finding_id=f"F{len(consensus_findings) + 1}",
                    resource_name=best_finding.resource_name,
                    resource_type=best_finding.resource_type,
                    vulnerability_type=best_finding.vulnerability_type,
                    severity=max(f.severity for f in group),  # Highest severity
                    title=best_finding.title,
                    description=best_finding.description,
                    evidence=best_finding.evidence,
                    confidence=min(0.95, best_finding.confidence + 0.1),  # Boost confidence
                    reasoning=f"Found by {len(specialists)} specialists: {', '.join(specialists)}",
                    specialist="ensemble",
                    metadata={"specialist_agreement": list(specialists)},
                )
                consensus_findings.append(consensus_finding)
                
                if len(specialists) == len(specialist_outputs):
                    unanimous += 1
                else:
                    majority += 1
        
        specialist_counts = {
            so.specialist: len(so.findings)
            for so in specialist_outputs
        }
        
        return ConsensusResult(
            findings=consensus_findings,
            specialist_counts=specialist_counts,
            unanimous_count=unanimous,
            majority_count=majority,
            specialist_only_count=0,  # Not included in vote consensus
            conflicts_resolved=0,
            debate_notes="Majority voting: findings with 2+ specialist agreement included",
        )

    def _union_consensus(
        self,
        specialist_outputs: List[SpecialistOutput],
    ) -> ConsensusResult:
        """Include all findings from all specialists (with deduplication)."""
        
        seen_keys = set()
        consensus_findings = []
        
        for output in specialist_outputs:
            for finding in output.findings:
                key = self._get_finding_key(finding)
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    
                    # Renumber finding
                    new_finding = SpecialistFinding(
                        finding_id=f"F{len(consensus_findings) + 1}",
                        resource_name=finding.resource_name,
                        resource_type=finding.resource_type,
                        vulnerability_type=finding.vulnerability_type,
                        severity=finding.severity,
                        title=finding.title,
                        description=finding.description,
                        evidence=finding.evidence,
                        confidence=finding.confidence,
                        reasoning=finding.reasoning,
                        specialist=finding.specialist,
                        metadata=finding.metadata,
                    )
                    consensus_findings.append(new_finding)
        
        specialist_counts = {
            so.specialist: len(so.findings)
            for so in specialist_outputs
        }
        
        return ConsensusResult(
            findings=consensus_findings,
            specialist_counts=specialist_counts,
            unanimous_count=0,
            majority_count=0,
            specialist_only_count=len(consensus_findings),
            conflicts_resolved=0,
            debate_notes="Union: all unique findings included",
        )

    def _intersection_consensus(
        self,
        specialist_outputs: List[SpecialistOutput],
    ) -> ConsensusResult:
        """Only include findings all specialists agree on."""
        
        # Group findings by resource and issue type
        finding_groups: Dict[str, List[SpecialistFinding]] = {}
        
        for output in specialist_outputs:
            for finding in output.findings:
                key = self._get_finding_key(finding)
                if key not in finding_groups:
                    finding_groups[key] = []
                finding_groups[key].append(finding)
        
        # Filter by unanimous agreement
        consensus_findings = []
        total_specialists = len(specialist_outputs)
        
        for key, group in finding_groups.items():
            specialists = set(f.specialist for f in group)
            
            if len(specialists) == total_specialists:
                # All specialists agree
                best_finding = max(group, key=lambda f: f.confidence)
                
                consensus_finding = SpecialistFinding(
                    finding_id=f"F{len(consensus_findings) + 1}",
                    resource_name=best_finding.resource_name,
                    resource_type=best_finding.resource_type,
                    vulnerability_type=best_finding.vulnerability_type,
                    severity=max(f.severity for f in group),
                    title=best_finding.title,
                    description=best_finding.description,
                    evidence=best_finding.evidence,
                    confidence=0.99,  # High confidence for unanimous
                    reasoning="Unanimous agreement across all specialists",
                    specialist="ensemble",
                    metadata={"specialist_agreement": list(specialists)},
                )
                consensus_findings.append(consensus_finding)
        
        specialist_counts = {
            so.specialist: len(so.findings)
            for so in specialist_outputs
        }
        
        return ConsensusResult(
            findings=consensus_findings,
            specialist_counts=specialist_counts,
            unanimous_count=len(consensus_findings),
            majority_count=0,
            specialist_only_count=0,
            conflicts_resolved=0,
            debate_notes="Intersection: only unanimous findings included",
        )

    def _get_finding_key(self, finding: SpecialistFinding) -> str:
        """Create a key for grouping similar findings."""
        return f"{finding.resource_name.lower()}:{finding.vulnerability_type.lower()}"

    def _get_specialist_output(
        self,
        outputs: List[SpecialistOutput],
        specialist_name: str,
    ) -> Optional[SpecialistOutput]:
        """Get output for a specific specialist."""
        for output in outputs:
            if output.specialist == specialist_name:
                return output
        return None

    def _format_findings(self, output: Optional[SpecialistOutput]) -> str:
        """Format specialist output for the consensus prompt."""
        if output is None or not output.findings:
            return "No findings reported."
        
        findings_list = []
        for f in output.findings:
            findings_list.append({
                "finding_id": f.finding_id,
                "resource_name": f.resource_name,
                "vulnerability_type": f.vulnerability_type,
                "severity": f.severity,
                "title": f.title,
                "confidence": f.confidence,
                "reasoning": f.reasoning,
            })
        
        return json.dumps(findings_list, indent=2)

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM with the given prompt."""
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            return content
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            raise

    def _parse_consensus_response(
        self,
        response: str,
    ) -> tuple[List[SpecialistFinding], Dict[str, Any]]:
        """Parse consensus LLM response."""
        findings = []
        stats = {}
        
        json_content = self._extract_json(response)
        if not json_content:
            self.logger.warning("Could not extract JSON from consensus response")
            return findings, stats
        
        try:
            data = json.loads(json_content)
            
            # Parse findings
            for i, f in enumerate(data.get("findings", [])):
                finding = SpecialistFinding(
                    finding_id=f.get("finding_id", f"F{i+1}"),
                    resource_name=f.get("resource_name", "unknown"),
                    resource_type=f.get("resource_type", "unknown"),
                    vulnerability_type=f.get("vulnerability_type", "unknown"),
                    severity=f.get("severity", "medium"),
                    title=f.get("title", "Untitled"),
                    description=f.get("description", ""),
                    evidence=f.get("evidence", ""),
                    confidence=f.get("confidence", 0.8),
                    reasoning=f.get("reasoning", ""),
                    specialist="ensemble",
                    metadata={
                        "specialist_agreement": f.get("specialist_agreement", []),
                    },
                )
                findings.append(finding)
            
            # Parse stats
            consensus_summary = data.get("consensus_summary", {})
            stats = {
                "unanimous": consensus_summary.get("unanimous_findings", 0),
                "majority": consensus_summary.get("majority_findings", 0),
                "specialist_only": consensus_summary.get("specialist_only_findings", 0),
                "conflicts_resolved": consensus_summary.get("conflicts_resolved", 0),
                "debate_notes": data.get("debate_notes", ""),
            }
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse consensus response: {e}")
        
        return findings, stats

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text."""
        strategies = [
            lambda t: t.split("```json")[1].split("```")[0] if "```json" in t else None,
            lambda t: t.split("```")[1].split("```")[0] if t.count("```") >= 2 else None,
            lambda t: self._find_json_object(t),
            lambda t: t if t.strip().startswith("{") else None,
        ]
        
        for strategy in strategies:
            try:
                result = strategy(text)
                if result:
                    json.loads(result.strip())
                    return result.strip()
            except (json.JSONDecodeError, IndexError, TypeError):
                continue
        
        return None

    def _find_json_object(self, text: str) -> Optional[str]:
        """Find JSON object using brace matching."""
        start = text.find("{")
        if start == -1:
            return None
        
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Return agent configuration as dictionary."""
        return {
            "agent_type": "ConsensusAgent",
            "method": self.method,
        }
