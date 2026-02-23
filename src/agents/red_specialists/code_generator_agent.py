"""
Code Generator Agent

Third stage of Red Team Pipeline.
Generates IaC code based on architecture and vulnerability specifications.
"""

import json
from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from ...prompts import RedTeamPipelinePrompts
from .base import PipelineStage


class CodeGeneratorAgent(PipelineStage):
    """
    Code generator that produces IaC with injected vulnerabilities.
    
    Takes: Architecture design + Selected vulnerabilities
    Produces: Complete IaC code files + implementation notes
    """

    LANGUAGE_EXTENSIONS = {
        "terraform": "tf",
        "cloudformation": "yaml",
    }

    def __init__(
        self,
        llm: BaseChatModel,
        cloud_provider: str = "aws",
        language: str = "terraform",
    ):
        super().__init__(llm, cloud_provider, language)

    @property
    def stage_name(self) -> str:
        return "code_generator"

    @property
    def prompt_template(self) -> str:
        return RedTeamPipelinePrompts.CODE_GENERATOR_AGENT

    def _format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Format the generator prompt with architecture and vulns."""
        # Extract architecture and vulnerabilities from pipeline input
        architecture = input_data.get("architecture", {})
        vulnerabilities = input_data.get("vulnerabilities", {})
        
        return self.prompt_template.format(
            architecture_json=json.dumps(architecture, indent=2),
            vulnerabilities_json=json.dumps(vulnerabilities.get("selected_vulnerabilities", []), indent=2),
            cloud_provider=self.cloud_provider,
            language=self.language,
            extension=self.LANGUAGE_EXTENSIONS.get(self.language, "tf"),
        )

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse generator response into code files and manifest."""
        result = {
            "code": {},
            "implementation_notes": [],
        }
        
        # Extract main file
        main_content = self._extract_between_markers(
            response,
            "MAIN_FILE_BEGINS_HERE",
            "MAIN_FILE_ENDS_HERE"
        )
        if main_content:
            ext = self.LANGUAGE_EXTENSIONS.get(self.language, "tf")
            filename = "main.tf" if self.language == "terraform" else "template.yaml"
            result["code"][filename] = main_content
        
        # Extract variables file
        vars_content = self._extract_between_markers(
            response,
            "VARIABLES_FILE_BEGINS_HERE",
            "VARIABLES_FILE_ENDS_HERE"
        )
        if vars_content:
            filename = "variables.tf" if self.language == "terraform" else "parameters.yaml"
            result["code"][filename] = vars_content
        
        # Extract implementation notes
        notes_content = self._extract_between_markers(
            response,
            "IMPLEMENTATION_NOTES_BEGINS_HERE",
            "IMPLEMENTATION_NOTES_ENDS_HERE"
        )
        if notes_content:
            try:
                notes = json.loads(notes_content)
                result["implementation_notes"] = notes.get("implementations", [])
            except json.JSONDecodeError:
                self.logger.warning("Could not parse implementation notes")
        
        return result
