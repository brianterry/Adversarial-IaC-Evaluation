"""
Security Expert Specialist

Focuses on finding security vulnerabilities in IaC:
- Access control misconfigurations
- Encryption issues
- Network security
- Authentication/Authorization flaws
- Secrets management
"""

from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from ...prompts import BlueTeamSpecialistPrompts
from .base import BaseSpecialist


class SecurityExpert(BaseSpecialist):
    """
    Security Expert specialist agent.
    
    Focuses on identifying security vulnerabilities that could
    lead to data breaches, unauthorized access, or system compromise.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        language: str = "terraform",
    ):
        super().__init__(llm, language)

    @property
    def specialist_name(self) -> str:
        return "security_expert"

    @property
    def prompt_template(self) -> str:
        return BlueTeamSpecialistPrompts.SECURITY_EXPERT

    @property
    def finding_prefix(self) -> str:
        return "SEC"

    def _extract_metadata(self, finding_dict: Dict) -> Dict[str, Any]:
        """Extract security-specific metadata."""
        metadata = super()._extract_metadata(finding_dict)
        
        # Security-specific fields
        for key in ["cve_ids", "attack_vector", "impact"]:
            if key in finding_dict:
                metadata[key] = finding_dict[key]
        
        return metadata
