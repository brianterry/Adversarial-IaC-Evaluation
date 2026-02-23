"""
Compliance Agent Specialist

Focuses on regulatory compliance in IaC:
- HIPAA (healthcare data protection)
- PCI-DSS (payment card data)
- SOC 2 (security controls)
- GDPR (data protection)
"""

from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from ...prompts import BlueTeamSpecialistPrompts
from .base import BaseSpecialist


class ComplianceAgent(BaseSpecialist):
    """
    Compliance specialist agent.
    
    Focuses on identifying violations of regulatory frameworks
    and compliance requirements in infrastructure code.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        language: str = "terraform",
    ):
        super().__init__(llm, language)

    @property
    def specialist_name(self) -> str:
        return "compliance_agent"

    @property
    def prompt_template(self) -> str:
        return BlueTeamSpecialistPrompts.COMPLIANCE_AGENT

    @property
    def finding_prefix(self) -> str:
        return "COMP"

    def _extract_metadata(self, finding_dict: Dict) -> Dict[str, Any]:
        """Extract compliance-specific metadata."""
        metadata = super()._extract_metadata(finding_dict)
        
        # Compliance-specific fields
        for key in ["compliance_frameworks", "control_id", "regulation_section"]:
            if key in finding_dict:
                metadata[key] = finding_dict[key]
        
        return metadata
