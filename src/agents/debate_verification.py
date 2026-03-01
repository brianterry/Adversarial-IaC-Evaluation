"""
Adversarial Debate Verification

Two agents debate each finding to verify accuracy:
- Prosecutor: Argues the finding is valid
- Defender: Argues the finding is a false positive
- Judge: Renders final verdict

Part of the Adversarial IaC Evaluation framework.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from .blue_team_agent import Finding
from .judge_agent import ScoringResult, Match
from ..prompts import AdversarialDebatePrompts


@dataclass
class DebateResult:
    """Result of a single finding debate"""
    finding_id: str
    prosecution_argument: Dict[str, Any]
    defense_argument: Dict[str, Any]
    verdict: str  # TRUE_POSITIVE, FALSE_POSITIVE, PARTIAL_MATCH, etc.
    verdict_confidence: float
    verdict_reasoning: Dict[str, Any]
    final_severity: str


@dataclass
class DebateVerificationOutput:
    """Output from debate verification process"""
    debate_results: List[DebateResult]
    verified_findings: List[Finding]
    rejected_findings: List[Finding]
    scoring: ScoringResult
    debate_stats: Dict[str, Any]


class DebateVerificationAgent:
    """
    Adversarial debate verification system.
    
    For each Blue Team finding:
    1. Prosecutor argues it's a real vulnerability
    2. Defender argues it's a false positive
    3. Judge renders final verdict
    
    This helps reduce false positives through adversarial verification.
    """

    VERDICTS = ["TRUE_POSITIVE", "FALSE_POSITIVE", "PARTIAL_MATCH", "DUPLICATE", "INCONCLUSIVE"]

    def __init__(
        self,
        llm: BaseChatModel,
        language: str = "terraform",
        run_parallel: bool = True,
    ):
        """
        Initialize Debate Verification Agent.
        
        Args:
            llm: LangChain chat model for all debate agents
            language: IaC language
            run_parallel: Whether to run debates concurrently
        """
        self.llm = llm
        self.language = language
        self.run_parallel = run_parallel
        self.logger = logging.getLogger("DebateVerification")

    async def verify(
        self,
        findings: List[Finding],
        code: Dict[str, str],
        manifest: List[Dict[str, Any]],
    ) -> DebateVerificationOutput:
        """
        Verify findings through adversarial debate.
        
        Args:
            findings: Blue Team findings to verify
            code: IaC code that was analyzed
            manifest: Red Team vulnerability manifest (ground truth)
            
        Returns:
            DebateVerificationOutput with verified/rejected findings
        """
        self.logger.info(f"Starting adversarial debate for {len(findings)} findings")
        
        # Combine code for prompts
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Run debates
        if self.run_parallel:
            debate_results = await self._run_debates_parallel(
                findings, combined_code, manifest
            )
        else:
            debate_results = await self._run_debates_sequential(
                findings, combined_code, manifest
            )
        
        # Separate verified and rejected findings
        verified_findings = []
        rejected_findings = []
        
        for finding, result in zip(findings, debate_results):
            if result.verdict in ["TRUE_POSITIVE", "PARTIAL_MATCH"]:
                # Update finding with debate-verified severity
                verified_finding = Finding(
                    finding_id=finding.finding_id,
                    resource_name=finding.resource_name,
                    resource_type=finding.resource_type,
                    vulnerability_type=finding.vulnerability_type,
                    severity=result.final_severity or finding.severity,
                    title=finding.title,
                    description=finding.description,
                    evidence=finding.evidence,
                    line_number_estimate=finding.line_number_estimate,
                    confidence=result.verdict_confidence,
                    reasoning=f"Debate verified: {result.verdict}",
                    remediation=finding.remediation,
                    source="debate_verified",
                )
                verified_findings.append(verified_finding)
            else:
                rejected_findings.append(finding)
        
        self.logger.info(
            f"Debate complete: {len(verified_findings)} verified, "
            f"{len(rejected_findings)} rejected"
        )
        
        # Calculate scoring with verified findings only
        scoring = self._calculate_scoring(verified_findings, manifest)
        
        # Compile stats
        debate_stats = {
            "total_findings_debated": len(findings),
            "verified_count": len(verified_findings),
            "rejected_count": len(rejected_findings),
            "verdicts": {
                verdict: sum(1 for r in debate_results if r.verdict == verdict)
                for verdict in self.VERDICTS
            },
            "avg_verdict_confidence": (
                sum(r.verdict_confidence for r in debate_results) / len(debate_results)
                if debate_results else 0
            ),
        }
        
        return DebateVerificationOutput(
            debate_results=debate_results,
            verified_findings=verified_findings,
            rejected_findings=rejected_findings,
            scoring=scoring,
            debate_stats=debate_stats,
        )

    async def _run_debates_parallel(
        self,
        findings: List[Finding],
        code: str,
        manifest: List[Dict],
    ) -> List[DebateResult]:
        """Run all debates concurrently."""
        tasks = [
            self._debate_finding(finding, code, manifest)
            for finding in findings
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        debate_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Debate failed for {findings[i].finding_id}: {result}")
                # Create inconclusive result
                debate_results.append(DebateResult(
                    finding_id=findings[i].finding_id,
                    prosecution_argument={},
                    defense_argument={},
                    verdict="INCONCLUSIVE",
                    verdict_confidence=0.0,
                    verdict_reasoning={"error": str(result)},
                    final_severity=findings[i].severity,
                ))
            else:
                debate_results.append(result)
        
        return debate_results

    async def _run_debates_sequential(
        self,
        findings: List[Finding],
        code: str,
        manifest: List[Dict],
    ) -> List[DebateResult]:
        """Run debates one at a time."""
        results = []
        for finding in findings:
            try:
                result = await self._debate_finding(finding, code, manifest)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Debate failed for {finding.finding_id}: {e}")
                results.append(DebateResult(
                    finding_id=finding.finding_id,
                    prosecution_argument={},
                    defense_argument={},
                    verdict="INCONCLUSIVE",
                    verdict_confidence=0.0,
                    verdict_reasoning={"error": str(e)},
                    final_severity=finding.severity,
                ))
        return results

    async def _debate_finding(
        self,
        finding: Finding,
        code: str,
        manifest: List[Dict],
    ) -> DebateResult:
        """
        Conduct adversarial debate for a single finding.
        
        Steps:
        1. Prosecutor argues finding is valid
        2. Defender argues finding is false positive
        3. Judge renders verdict
        """
        finding_json = json.dumps({
            "finding_id": finding.finding_id,
            "resource_name": finding.resource_name,
            "resource_type": finding.resource_type,
            "vulnerability_type": finding.vulnerability_type,
            "severity": finding.severity,
            "title": finding.title,
            "description": finding.description,
            "evidence": finding.evidence,
            "confidence": finding.confidence,
        }, indent=2)
        
        manifest_json = json.dumps(manifest, indent=2)
        
        # Get prosecution argument
        prosecution_prompt = AdversarialDebatePrompts.PROSECUTOR_AGENT.format(
            finding_json=finding_json,
            language=self.language,
            code=code,
            manifest_json=manifest_json,
        )
        prosecution_response = await self._invoke_llm(prosecution_prompt)
        prosecution_argument = self._parse_argument(prosecution_response)
        
        # Get defense argument
        defense_prompt = AdversarialDebatePrompts.DEFENDER_AGENT.format(
            finding_json=finding_json,
            language=self.language,
            code=code,
            manifest_json=manifest_json,
        )
        defense_response = await self._invoke_llm(defense_prompt)
        defense_argument = self._parse_argument(defense_response)
        
        # Get judge verdict
        verdict_prompt = AdversarialDebatePrompts.JUDGE_VERDICT_AGENT.format(
            finding_json=finding_json,
            prosecution_json=json.dumps(prosecution_argument, indent=2),
            defense_json=json.dumps(defense_argument, indent=2),
            manifest_json=manifest_json,
        )
        verdict_response = await self._invoke_llm(verdict_prompt)
        verdict_data = self._parse_verdict(verdict_response)
        
        return DebateResult(
            finding_id=finding.finding_id,
            prosecution_argument=prosecution_argument,
            defense_argument=defense_argument,
            verdict=verdict_data.get("verdict", "INCONCLUSIVE"),
            verdict_confidence=verdict_data.get("confidence", 0.5),
            verdict_reasoning=verdict_data.get("reasoning", {}),
            final_severity=verdict_data.get("final_severity", finding.severity),
        )

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM with the given prompt."""
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            raise

    def _parse_argument(self, response: str) -> Dict[str, Any]:
        """Parse prosecution or defense argument."""
        json_content = self._extract_json(response)
        if json_content:
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                pass
        return {"raw_response": response}

    def _parse_verdict(self, response: str) -> Dict[str, Any]:
        """Parse judge verdict."""
        json_content = self._extract_json(response)
        if json_content:
            try:
                data = json.loads(json_content)
                return {
                    "verdict": data.get("verdict", "INCONCLUSIVE"),
                    "confidence": data.get("confidence", 0.5),
                    "reasoning": data.get("reasoning", {}),
                    "final_severity": data.get("final_severity", "medium"),
                }
            except json.JSONDecodeError:
                pass
        return {"verdict": "INCONCLUSIVE", "confidence": 0.0}

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text."""
        strategies = [
            lambda t: t.split("```json")[1].split("```")[0] if "```json" in t else None,
            lambda t: t.split("```")[1].split("```")[0] if t.count("```") >= 2 else None,
            lambda t: self._find_json_object(t),
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

    def _calculate_scoring(
        self,
        verified_findings: List[Finding],
        manifest: List[Dict],
    ) -> ScoringResult:
        """Calculate scoring using verified findings."""
        from .judge_agent import JudgeAgent
        
        judge = JudgeAgent()
        
        # Convert findings to dict format
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
            for f in verified_findings
        ]
        
        return judge.score(manifest, findings_dicts)

    def to_dict(self) -> Dict[str, Any]:
        """Return agent configuration as dictionary."""
        return {
            "agent_type": "DebateVerificationAgent",
            "mode": "debate",
            "language": self.language,
            "run_parallel": self.run_parallel,
        }


def create_debate_verification_agent(
    model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    region: str = "us-east-1",
    language: str = "terraform",
    run_parallel: bool = True,
) -> DebateVerificationAgent:
    """
    Create a Debate Verification Agent with AWS Bedrock.
    
    Args:
        model_id: Bedrock model ID
        region: AWS region
        language: terraform or cloudformation
        run_parallel: Run debates concurrently
        
    Returns:
        Configured DebateVerificationAgent
    """
    from langchain_aws import ChatBedrock
    
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        model_kwargs={
            "temperature": 0.3,
            "max_tokens": 4096,
        },
    )
    
    return DebateVerificationAgent(
        llm=llm,
        language=language,
        run_parallel=run_parallel,
    )
