"""
Stealth Reviewer Agent

Fourth (final) stage of Red Team Pipeline.
Reviews and refines code to make vulnerabilities harder to detect.
"""

import json
from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel

from ...prompts import RedTeamPipelinePrompts
from .base import PipelineStage


class StealthReviewerAgent(PipelineStage):
    """
    Stealth reviewer that refines code to evade detection.
    
    Takes: Generated code + Vulnerability manifest
    Produces: Refined code with stealth techniques applied
    """

    def __init__(
        self,
        llm: BaseChatModel,
        cloud_provider: str = "aws",
        language: str = "terraform",
        difficulty: str = "medium",
    ):
        super().__init__(llm, cloud_provider, language)
        self.difficulty = difficulty

    @property
    def stage_name(self) -> str:
        return "stealth_reviewer"

    @property
    def prompt_template(self) -> str:
        return RedTeamPipelinePrompts.STEALTH_REVIEWER_AGENT

    def _format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Format the reviewer prompt with code and manifest."""
        # Combine all code files
        code = input_data.get("code", {})
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Get vulnerability info
        vulnerabilities = input_data.get("vulnerabilities", {})
        implementation_notes = input_data.get("implementation_notes", [])
        
        # Create manifest from vulnerabilities and notes
        manifest = {
            "selected_vulnerabilities": vulnerabilities.get("selected_vulnerabilities", []),
            "implementations": implementation_notes,
        }
        
        return self.prompt_template.format(
            language=self.language,
            code=combined_code,
            manifest_json=json.dumps(manifest, indent=2),
            difficulty=self.difficulty,
        )

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse reviewer response into refined code and stealth report."""
        result = {
            "code": {},
            "stealth_report": {},
        }
        
        # Extract refined main file
        main_content = self._extract_between_markers(
            response,
            "REFINED_MAIN_FILE_BEGINS_HERE",
            "REFINED_MAIN_FILE_ENDS_HERE"
        )
        if main_content:
            filename = "main.tf" if self.language == "terraform" else "template.yaml"
            result["code"][filename] = main_content
        
        # Extract refined variables file
        vars_content = self._extract_between_markers(
            response,
            "REFINED_VARIABLES_FILE_BEGINS_HERE",
            "REFINED_VARIABLES_FILE_ENDS_HERE"
        )
        if vars_content:
            filename = "variables.tf" if self.language == "terraform" else "parameters.yaml"
            result["code"][filename] = vars_content
        
        # Extract stealth report
        report_content = self._extract_between_markers(
            response,
            "STEALTH_REPORT_BEGINS_HERE",
            "STEALTH_REPORT_ENDS_HERE"
        )
        if report_content:
            try:
                result["stealth_report"] = json.loads(report_content)
            except json.JSONDecodeError:
                self.logger.warning("Could not parse stealth report")
        
        return result

    def create_final_manifest(
        self,
        vulnerabilities: Dict[str, Any],
        implementation_notes: List[Dict],
        stealth_report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Create the final vulnerability manifest for scoring.
        
        Combines vulnerability selections, implementation notes, and stealth report
        into the format expected by the Judge.
        """
        manifest = []
        
        vulns = vulnerabilities.get("selected_vulnerabilities", [])
        reviewed_vulns = stealth_report.get("vulnerabilities_reviewed", [])
        
        # Create lookup for stealth info
        stealth_lookup = {v["vuln_id"]: v for v in reviewed_vulns}
        notes_lookup = {n["vuln_id"]: n for n in implementation_notes}
        
        for vuln in vulns:
            vuln_id = vuln.get("vuln_id", "")
            notes = notes_lookup.get(vuln_id, {})
            stealth = stealth_lookup.get(vuln_id, {})
            
            manifest_entry = {
                "vuln_id": vuln_id,
                "rule_id": vuln.get("rule_id", ""),
                "title": vuln.get("title", ""),
                "type": vuln.get("vulnerability_type", ""),
                "severity": vuln.get("severity", "medium"),
                "resource_name": notes.get("resource_name", vuln.get("target_component", "")),
                "resource_type": vuln.get("injection_point", {}).get("resource_type", ""),
                "line_number_estimate": notes.get("line_number_estimate", 0),
                "vulnerable_attribute": vuln.get("injection_point", {}).get("attribute", ""),
                "vulnerable_value": vuln.get("injection_point", {}).get("vulnerable_value", ""),
                "stealth_technique": ", ".join(stealth.get("techniques_applied", [])),
                "detection_hint": vuln.get("detection_hints", ""),
            }
            manifest.append(manifest_entry)
        
        return manifest
