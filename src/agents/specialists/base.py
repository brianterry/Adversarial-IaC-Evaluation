"""
Base Specialist Agent

Abstract base class for all Blue Team specialist agents.
Each specialist focuses on a specific domain of security analysis.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage


@dataclass
class SpecialistFinding:
    """A finding from a specialist agent"""
    finding_id: str
    resource_name: str
    resource_type: str
    vulnerability_type: str
    severity: str
    title: str
    description: str
    evidence: str
    confidence: float
    reasoning: str
    specialist: str  # Which specialist found this
    metadata: Dict[str, Any] = field(default_factory=dict)  # Specialist-specific data


@dataclass
class SpecialistOutput:
    """Output from a specialist agent"""
    specialist: str
    findings: List[SpecialistFinding]
    summary: str
    raw_response: str = ""


class BaseSpecialist(ABC):
    """
    Abstract base class for specialist agents.
    
    Each specialist:
    1. Has a specific domain expertise
    2. Uses a specialized prompt
    3. Returns structured findings
    """

    def __init__(
        self,
        llm: BaseChatModel,
        language: str = "terraform",
    ):
        """
        Initialize specialist agent.
        
        Args:
            llm: LangChain chat model
            language: IaC language (terraform, cloudformation)
        """
        self.llm = llm
        self.language = language
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def specialist_name(self) -> str:
        """Return the name of this specialist"""
        pass

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return the prompt template for this specialist"""
        pass

    @property
    def finding_prefix(self) -> str:
        """Return the prefix for finding IDs (e.g., 'SEC', 'COMP', 'ARCH')"""
        return self.specialist_name[:3].upper()

    async def analyze(self, code: Dict[str, str]) -> SpecialistOutput:
        """
        Analyze code for issues in this specialist's domain.
        
        Args:
            code: Dictionary of filename -> content
            
        Returns:
            SpecialistOutput with findings
        """
        self.logger.info(f"{self.specialist_name} analyzing code...")
        
        # Combine code files
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Build prompt
        prompt = self.prompt_template.format(
            language=self.language,
            code=combined_code,
        )
        
        # Get LLM response
        response = await self._invoke_llm(prompt)
        
        # Parse findings
        findings = self._parse_findings(response)
        
        # Extract summary
        summary = self._extract_summary(response)
        
        self.logger.info(f"{self.specialist_name} found {len(findings)} issues")
        
        return SpecialistOutput(
            specialist=self.specialist_name,
            findings=findings,
            summary=summary,
            raw_response=response,
        )

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

    def _parse_findings(self, response: str) -> List[SpecialistFinding]:
        """Parse LLM response into findings."""
        findings = []
        
        json_content = self._extract_json(response)
        if not json_content:
            self.logger.warning(f"Could not extract JSON from {self.specialist_name} response")
            return findings
        
        try:
            data = json.loads(json_content)
            raw_findings = data.get("findings", [])
            
            for i, f in enumerate(raw_findings):
                finding = SpecialistFinding(
                    finding_id=f.get("finding_id", f"{self.finding_prefix}-{i+1}"),
                    resource_name=f.get("resource_name", "unknown"),
                    resource_type=f.get("resource_type", "unknown"),
                    vulnerability_type=f.get("vulnerability_type", "unknown"),
                    severity=f.get("severity", "medium"),
                    title=f.get("title", "Untitled"),
                    description=f.get("description", ""),
                    evidence=f.get("evidence", ""),
                    confidence=f.get("confidence", 0.5),
                    reasoning=f.get("reasoning", ""),
                    specialist=self.specialist_name,
                    metadata=self._extract_metadata(f),
                )
                findings.append(finding)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse {self.specialist_name} findings: {e}")
        
        return findings

    def _extract_metadata(self, finding_dict: Dict) -> Dict[str, Any]:
        """Extract specialist-specific metadata from finding."""
        # Subclasses can override to extract specific fields
        metadata = {}
        
        # Common metadata fields
        for key in ["compliance_frameworks", "well_architected_pillar", "cve_ids"]:
            if key in finding_dict:
                metadata[key] = finding_dict[key]
        
        return metadata

    def _extract_summary(self, response: str) -> str:
        """Extract summary from response."""
        json_content = self._extract_json(response)
        if json_content:
            try:
                data = json.loads(json_content)
                return data.get("summary", "")
            except json.JSONDecodeError:
                pass
        return ""

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
        """Return specialist configuration as dictionary."""
        return {
            "specialist_type": self.__class__.__name__,
            "specialist_name": self.specialist_name,
            "language": self.language,
        }
