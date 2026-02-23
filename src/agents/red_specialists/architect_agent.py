"""
Architect Agent

First stage of Red Team Pipeline.
Designs the infrastructure structure based on the scenario.
"""

import json
from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from ...prompts import RedTeamPipelinePrompts
from .base import PipelineStage


class ArchitectAgent(PipelineStage):
    """
    Architect agent that designs infrastructure layout.
    
    Takes: Scenario description
    Produces: Infrastructure design with components and data flows
    """

    def __init__(
        self,
        llm: BaseChatModel,
        cloud_provider: str = "aws",
        language: str = "terraform",
    ):
        super().__init__(llm, cloud_provider, language)

    @property
    def stage_name(self) -> str:
        return "architect"

    @property
    def prompt_template(self) -> str:
        return RedTeamPipelinePrompts.ARCHITECT_AGENT

    def _format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Format the architect prompt with scenario data."""
        return self.prompt_template.format(
            scenario_description=input_data.get("description", ""),
            cloud_provider=self.cloud_provider,
            language=self.language,
        )

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse architect response into infrastructure design."""
        json_content = self._extract_json(response)
        
        if not json_content:
            self.logger.warning("Could not extract JSON from architect response")
            return {"components": [], "data_flows": []}
        
        try:
            data = json.loads(json_content)
            return {
                "architecture_name": data.get("architecture_name", "unnamed"),
                "description": data.get("description", ""),
                "components": data.get("components", []),
                "data_flows": data.get("data_flows", []),
                "security_boundaries": data.get("security_boundaries", []),
                "compliance_requirements": data.get("compliance_requirements", []),
                "recommended_vuln_injection_points": data.get("recommended_vuln_injection_points", []),
            }
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse architect response: {e}")
            return {"components": [], "data_flows": []}
