"""
Architecture Agent Specialist

Focuses on cloud architecture best practices:
- Well-Architected Framework principles
- High availability and disaster recovery
- Resource tagging and organization
- Operational excellence
"""

from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from ...prompts import BlueTeamSpecialistPrompts
from .base import BaseSpecialist


class ArchitectureAgent(BaseSpecialist):
    """
    Architecture specialist agent.
    
    Focuses on identifying architectural anti-patterns and
    deviations from cloud best practices.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        language: str = "terraform",
    ):
        super().__init__(llm, language)

    @property
    def specialist_name(self) -> str:
        return "architecture_agent"

    @property
    def prompt_template(self) -> str:
        return BlueTeamSpecialistPrompts.ARCHITECTURE_AGENT

    @property
    def finding_prefix(self) -> str:
        return "ARCH"

    def _extract_metadata(self, finding_dict: Dict) -> Dict[str, Any]:
        """Extract architecture-specific metadata."""
        metadata = super()._extract_metadata(finding_dict)
        
        # Architecture-specific fields
        for key in ["well_architected_pillar", "design_pattern", "cloud_provider"]:
            if key in finding_dict:
                metadata[key] = finding_dict[key]
        
        return metadata
