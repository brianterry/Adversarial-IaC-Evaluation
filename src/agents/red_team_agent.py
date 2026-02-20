"""
Red Team Agent - Generates plausible but vulnerable Infrastructure-as-Code

This agent is designed to create IaC that:
1. Passes syntax validation
2. Looks production-quality
3. Contains hidden security vulnerabilities
4. Challenges detection systems

Part of the Adversarial IaC Evaluation framework.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

# Import VulnerabilityDatabase from the vendored submodule
# The submodule: vendor/vulnerable-iac-generator (https://github.com/SymbioticSec/vulnerable-iac-dataset-generator)
from pathlib import Path
import importlib.util

# Paths to vendor submodule
_vendor_path = Path(__file__).resolve().parent.parent.parent / "vendor" / "vulnerable-iac-generator"
_vuln_db_module_path = _vendor_path / "src" / "utils" / "vulnerability_db.py"
_vuln_db_data_path = _vendor_path / "data" / "trivy_rules_db.json"

# Load the VulnerabilityDatabase from vendored submodule (REQUIRED)
if not _vendor_path.exists():
    raise ImportError(
        f"Vulnerability database submodule not found at: {_vendor_path}\n"
        "Please initialize the submodule:\n"
        "  git submodule update --init --recursive\n"
        "Or clone with --recursive:\n"
        "  git clone --recursive <repo-url>"
    )

if not _vuln_db_module_path.exists():
    raise ImportError(
        f"Vulnerability database module not found at: {_vuln_db_module_path}\n"
        "The submodule may be corrupted. Try:\n"
        "  git submodule update --init --recursive"
    )

# Load the module directly to avoid namespace conflicts with our own src/
_spec = importlib.util.spec_from_file_location("vulnerability_db", _vuln_db_module_path)
_vuln_db_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vuln_db_module)
_VulnerabilityDatabaseClass = _vuln_db_module.VulnerabilityDatabase


class VulnerabilityDatabase:
    """Wrapper for vendored VulnerabilityDatabase with proper data path"""
    def __init__(self):
        # Pass explicit path to avoid data file lookup issues
        self._db = _VulnerabilityDatabaseClass(db_path=str(_vuln_db_data_path))
    
    def get_sample_for_prompt(self, provider, language):
        return self._db.get_sample_for_prompt(provider, language)

from ..prompts import AdversarialPrompts, ScenarioTemplates


class Difficulty(Enum):
    """Difficulty levels for vulnerability injection"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class DifficultyConfig:
    """Configuration for each difficulty level"""
    vuln_count: int
    subtlety: str
    stealth_techniques: List[str]
    evasion_target: float  # Target evasion rate


@dataclass
class VulnerabilityManifest:
    """Ground truth manifest of injected vulnerabilities"""
    vuln_id: str
    rule_id: str
    title: str
    type: str
    severity: str
    resource_name: str
    resource_type: str
    line_number_estimate: int
    vulnerable_attribute: str
    vulnerable_value: str
    stealth_technique: str
    detection_hint: str


@dataclass
class RedTeamOutput:
    """Output from Red Team Agent"""
    code: Dict[str, str]  # filename -> content
    manifest: List[VulnerabilityManifest]
    difficulty: Difficulty
    stealth_score: int  # 0 or 1 (passes syntax validation)
    generation_stats: Dict[str, Any] = field(default_factory=dict)


class RedTeamAgent:
    """
    Adversarial agent that generates plausible but vulnerable IaC.
    
    This agent:
    1. Selects vulnerabilities optimized for evasion
    2. Generates IaC code with hidden vulnerabilities
    3. Creates ground truth manifest for scoring
    4. Validates stealth (syntax validation)
    """

    # Difficulty configurations
    DIFFICULTY_CONFIGS = {
        Difficulty.EASY: DifficultyConfig(
            vuln_count=2,
            subtlety="obvious",
            stealth_techniques=["missing_config", "disabled_flag"],
            evasion_target=0.2,
        ),
        Difficulty.MEDIUM: DifficultyConfig(
            vuln_count=3,
            subtlety="moderate",
            stealth_techniques=[
                "variable_indirection",
                "misleading_comments",
                "reasonable_defaults",
            ],
            evasion_target=0.5,
        ),
        Difficulty.HARD: DifficultyConfig(
            vuln_count=5,
            subtlety="hidden",
            stealth_techniques=[
                "chain_vulnerabilities",
                "misleading_naming",
                "secure_looking_configs",
                "split_across_resources",
            ],
            evasion_target=0.7,
        ),
    }

    # Language configurations
    LANGUAGE_CONFIGS = {
        "terraform": {
            "extension": "tf",
            "main_file": "main.tf",
            "vars_file": "variables.tf",
        },
        "cloudformation": {
            "extension": "yaml",
            "main_file": "template.yaml",
            "vars_file": "parameters.yaml",
        },
    }

    def __init__(
        self,
        llm: BaseChatModel,
        difficulty: Difficulty = Difficulty.MEDIUM,
        cloud_provider: str = "aws",
        language: str = "terraform",
    ):
        """
        Initialize Red Team Agent.
        
        Args:
            llm: LangChain chat model (e.g., ChatBedrock)
            difficulty: Vulnerability injection difficulty
            cloud_provider: Target cloud provider (aws, azure, gcp)
            language: IaC language (terraform, cloudformation)
        """
        self.llm = llm
        self.difficulty = difficulty
        self.cloud_provider = cloud_provider
        self.language = language
        self.logger = logging.getLogger("RedTeamAgent")
        
        # Load Trivy vulnerability database from generator
        self.vulnerability_db = VulnerabilityDatabase()
        
        # Get configuration
        self.config = self.DIFFICULTY_CONFIGS[difficulty]
        self.lang_config = self.LANGUAGE_CONFIGS.get(
            language, self.LANGUAGE_CONFIGS["terraform"]
        )

    async def execute(self, scenario: Dict[str, Any]) -> RedTeamOutput:
        """
        Execute Red Team attack: generate vulnerable IaC.
        
        Args:
            scenario: Test scenario with description, requirements, etc.
            
        Returns:
            RedTeamOutput with code, manifest, and metadata
        """
        self.logger.info(f"Red Team executing {self.difficulty.value} difficulty attack")
        
        # Step 1: Select vulnerabilities optimized for evasion
        self.logger.info("Step 1: Selecting adversarial vulnerabilities")
        selected_vulns = await self._select_adversarial_vulnerabilities(scenario)
        
        # Step 2: Generate IaC with hidden vulnerabilities
        self.logger.info("Step 2: Generating stealthy IaC code")
        code, manifest = await self._generate_vulnerable_iac(scenario, selected_vulns)
        
        # Step 3: Validate stealth (syntax check)
        self.logger.info("Step 3: Validating stealth")
        stealth_score = await self._verify_stealth(code)
        
        # Step 4: Compile output
        output = RedTeamOutput(
            code=code,
            manifest=manifest,
            difficulty=self.difficulty,
            stealth_score=stealth_score,
            generation_stats={
                "vuln_count": len(manifest),
                "file_count": len(code),
                "difficulty": self.difficulty.value,
            },
        )
        
        self.logger.info(
            f"Red Team complete: {len(manifest)} vulns, "
            f"stealth={stealth_score}, files={list(code.keys())}"
        )
        
        return output

    async def _select_adversarial_vulnerabilities(
        self, scenario: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Select vulnerabilities optimized for evasion.
        
        Uses the Trivy database from the generator but selects
        vulnerabilities that are harder to detect.
        """
        # Get vulnerability samples from Trivy database
        db_sample = self.vulnerability_db.get_sample_for_prompt(
            self.cloud_provider, self.language
        )
        
        # Build adversarial selection prompt
        prompt = AdversarialPrompts.RED_TEAM_VULNERABILITY_SELECTION.format(
            scenario_json=json.dumps(scenario, indent=2),
            vulnerability_samples=json.dumps(
                db_sample.get("sample_vulnerabilities", [])[:10],
                indent=2,
            ),
            difficulty=self.difficulty.value,
            vuln_count=self.config.vuln_count,
        )
        
        # Get LLM selection
        response = await self._invoke_llm(prompt)
        
        # Parse response
        selected = self._parse_vulnerability_selection(response)
        
        self.logger.info(f"Selected {len(selected)} adversarial vulnerabilities")
        return selected

    async def _generate_vulnerable_iac(
        self,
        scenario: Dict[str, Any],
        vulnerabilities: List[Dict[str, Any]],
    ) -> tuple[Dict[str, str], List[VulnerabilityManifest]]:
        """
        Generate IaC code with hidden vulnerabilities.
        """
        # Build generation prompt
        prompt = AdversarialPrompts.RED_TEAM_CODE_GENERATION.format(
            scenario_description=scenario.get("description", ""),
            cloud_provider=self.cloud_provider,
            language=self.language,
            vulnerabilities_json=json.dumps(vulnerabilities, indent=2),
            difficulty=self.difficulty.value,
            extension=self.lang_config["extension"],
        )
        
        # Generate code
        response = await self._invoke_llm(prompt)
        
        # Parse response into files and manifest
        code, manifest = self._parse_code_response(response)
        
        return code, manifest

    async def _verify_stealth(self, code: Dict[str, str]) -> int:
        """
        Verify that generated code passes syntax validation.
        
        Returns:
            1 if code passes validation, 0 if it fails
        """
        # For now, basic validation - check for common syntax issues
        main_file = code.get(
            self.lang_config["main_file"],
            code.get("main.tf", code.get("template.yaml", "")),
        )
        
        if not main_file:
            return 0
        
        # Basic checks
        if self.language == "terraform":
            # Check for basic Terraform structure
            if "resource" not in main_file and "data" not in main_file:
                return 0
            # Check for unclosed braces
            if main_file.count("{") != main_file.count("}"):
                return 0
        elif self.language == "cloudformation":
            # Check for basic CloudFormation structure
            if "Resources:" not in main_file and "AWSTemplateFormatVersion" not in main_file:
                return 0
        
        return 1

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM with the given prompt."""
        try:
            self.logger.debug(f"Sending prompt ({len(prompt)} chars)")
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            # Handle different response types
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            self.logger.info(f"LLM response: {len(content)} chars")
            self.logger.debug(f"Response preview: {content[:500] if content else 'EMPTY'}")
            
            return content
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise

    def _parse_vulnerability_selection(
        self, response: str
    ) -> List[Dict[str, Any]]:
        """Parse vulnerability selection response from LLM."""
        if not response:
            self.logger.warning("Empty response from LLM")
            return []
        
        # Log first 500 chars for debugging
        self.logger.debug(f"Raw response (first 500 chars): {response[:500]}")
        
        content = response.strip()
        
        # Try multiple extraction strategies
        strategies = [
            # Strategy 1: JSON in code block
            lambda c: c.split("```json")[1].split("```")[0] if "```json" in c else None,
            # Strategy 2: Generic code block
            lambda c: c.split("```")[1].split("```")[0] if c.count("```") >= 2 else None,
            # Strategy 3: Find JSON object with regex
            lambda c: self._extract_json_object(c),
            # Strategy 4: Raw content is JSON
            lambda c: c if c.startswith("{") else None,
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                extracted = strategy(content)
                if extracted:
                    data = json.loads(extracted.strip())
                    vulns = data.get("selected_vulnerabilities", [])
                    if vulns:
                        self.logger.info(f"Parsed {len(vulns)} vulns using strategy {i+1}")
                        return vulns
            except (json.JSONDecodeError, IndexError, TypeError):
                continue
        
        self.logger.warning(f"Failed to parse vulnerability selection from response")
        self.logger.warning(f"Full response: {response[:1000]}")
        return []
    
    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract JSON object from text using brace matching."""
        # Find the first { and match to closing }
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

    def _parse_code_response(
        self, response: str
    ) -> tuple[Dict[str, str], List[VulnerabilityManifest]]:
        """Parse code generation response into files and manifest."""
        code = {}
        manifest = []
        
        if not response:
            self.logger.warning("Empty response from code generation")
            return code, manifest
        
        self.logger.debug(f"Code response length: {len(response)} chars")
        
        # Try multiple patterns for main file extraction
        main_patterns = [
            r"MAIN_FILE_BEGINS_HERE\s*(.*?)\s*MAIN_FILE_ENDS_HERE",
            r"```(?:hcl|terraform|tf)\s*(.*?)\s*```",  # HCL/Terraform code block
            r"```(?:yaml|cloudformation)\s*(.*?)\s*```",  # YAML/CF code block
        ]
        
        for pattern in main_patterns:
            main_match = re.search(pattern, response, re.DOTALL)
            if main_match:
                content = main_match.group(1).strip()
                if content and len(content) > 50:  # Reasonable minimum
                    code[self.lang_config["main_file"]] = content
                    self.logger.info(f"Extracted main file with {len(content)} chars")
                    break
        
        # If still no main file, try to find any substantial code block
        if not code:
            # Look for resource definitions (Terraform) or Resources: (CF)
            if self.language == "terraform":
                tf_match = re.search(r'(resource\s+"[^"]+"\s+"[^"]+"\s*\{.*)', response, re.DOTALL)
                if tf_match:
                    code[self.lang_config["main_file"]] = tf_match.group(1).strip()
            elif self.language == "cloudformation":
                cf_match = re.search(r'(AWSTemplateFormatVersion.*)', response, re.DOTALL)
                if cf_match:
                    code[self.lang_config["main_file"]] = cf_match.group(1).strip()
        
        # Extract variables file
        vars_match = re.search(
            r"VARIABLES_FILE_BEGINS_HERE\s*(.*?)\s*VARIABLES_FILE_ENDS_HERE",
            response,
            re.DOTALL,
        )
        if vars_match:
            code[self.lang_config["vars_file"]] = vars_match.group(1).strip()
        
        # Extract vulnerability manifest - try multiple strategies
        manifest = self._extract_manifest(response, code)
        
        return code, manifest
    
    def _extract_manifest(
        self, response: str, code: Dict[str, str]
    ) -> List[VulnerabilityManifest]:
        """
        Extract vulnerability manifest using multiple fallback strategies.
        
        Strategies:
        1. Look for explicit VULNERABILITY_MANIFEST markers
        2. Look for JSON with injected_vulnerabilities key
        3. Parse vulnerability comments from code (# VULNERABILITY V1: ...)
        """
        manifest = []
        
        # Strategy 1: Explicit markers (preferred)
        manifest_match = re.search(
            r"VULNERABILITY_MANIFEST_BEGINS_HERE\s*(.*?)\s*VULNERABILITY_MANIFEST_ENDS_HERE",
            response,
            re.DOTALL,
        )
        if manifest_match:
            manifest = self._parse_manifest_json(manifest_match.group(1).strip())
            if manifest:
                self.logger.info(f"Extracted {len(manifest)} vulns using manifest markers")
                return manifest
        
        # Strategy 2: Look for JSON with injected_vulnerabilities anywhere in response
        json_patterns = [
            r'\{[^{}]*"injected_vulnerabilities"\s*:\s*\[[^\]]*\][^{}]*\}',
            r'```json\s*(\{.*?"injected_vulnerabilities".*?\})\s*```',
        ]
        for pattern in json_patterns:
            json_match = re.search(pattern, response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                manifest = self._parse_manifest_json(json_str)
                if manifest:
                    self.logger.info(f"Extracted {len(manifest)} vulns using JSON pattern")
                    return manifest
        
        # Strategy 3: Parse vulnerability comments from generated code
        main_code = code.get(self.lang_config["main_file"], "")
        if main_code:
            manifest = self._extract_vulns_from_comments(main_code)
            if manifest:
                self.logger.info(f"Extracted {len(manifest)} vulns from code comments (fallback)")
                return manifest
        
        self.logger.warning("Could not extract vulnerability manifest from response")
        return []
    
    def _parse_manifest_json(self, json_str: str) -> List[VulnerabilityManifest]:
        """Parse manifest from JSON string."""
        manifest = []
        try:
            data = json.loads(json_str)
            for v in data.get("injected_vulnerabilities", []):
                manifest.append(
                    VulnerabilityManifest(
                        vuln_id=v.get("vuln_id", ""),
                        rule_id=v.get("rule_id", ""),
                        title=v.get("title", v.get("why_vulnerable", "")),
                        type=v.get("type", "unknown"),
                        severity=v.get("severity", "medium"),
                        resource_name=v.get("resource_name", ""),
                        resource_type=v.get("resource_type", ""),
                        line_number_estimate=v.get("line_number_estimate", 0),
                        vulnerable_attribute=v.get("vulnerable_attribute", ""),
                        vulnerable_value=str(v.get("vulnerable_value", "")),
                        stealth_technique=v.get("stealth_technique_used", ""),
                        detection_hint=v.get("detection_hint", ""),
                    )
                )
        except json.JSONDecodeError as e:
            self.logger.debug(f"JSON parsing failed: {e}")
        return manifest
    
    def _extract_vulns_from_comments(self, code: str) -> List[VulnerabilityManifest]:
        """
        Extract vulnerabilities from code comments as fallback.
        
        Looks for patterns like:
        - # VULNERABILITY V1: Missing encryption
        - # (V2) Permissive access
        - # Intentionally vulnerable: no logging
        """
        manifest = []
        
        # Pattern: # VULNERABILITY V1: description or # (V1) description
        vuln_patterns = [
            r'#\s*VULNERABILITY\s+(V\d+):\s*(.+)',
            r'#\s*\(V(\d+)\)\s*(.+)',
            r'#\s*Intentionally\s+(?:Insecure|vulnerable)[:\s]+(.+)',
        ]
        
        seen_vulns = set()
        for pattern in vuln_patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                if len(match.groups()) >= 2:
                    vuln_id = f"V{match.group(1)}" if match.group(1).isdigit() else match.group(1)
                    description = match.group(2).strip()
                else:
                    vuln_id = f"V{len(manifest) + 1}"
                    description = match.group(1).strip() if match.groups() else "Unknown"
                
                if vuln_id not in seen_vulns:
                    seen_vulns.add(vuln_id)
                    
                    # Try to determine vulnerability type from description
                    vuln_type = self._infer_vuln_type(description)
                    
                    manifest.append(
                        VulnerabilityManifest(
                            vuln_id=vuln_id,
                            rule_id="",
                            title=description[:100],
                            type=vuln_type,
                            severity="medium",
                            resource_name="",
                            resource_type="",
                            line_number_estimate=0,
                            vulnerable_attribute="",
                            vulnerable_value="",
                            stealth_technique="Extracted from code comment",
                            detection_hint=description,
                        )
                    )
        
        return manifest
    
    def _infer_vuln_type(self, description: str) -> str:
        """Infer vulnerability type from description."""
        desc_lower = description.lower()
        
        if any(kw in desc_lower for kw in ["encrypt", "kms", "ssl", "tls"]):
            return "encryption"
        elif any(kw in desc_lower for kw in ["public", "access", "acl", "permission"]):
            return "access_control"
        elif any(kw in desc_lower for kw in ["security group", "firewall", "ingress", "egress", "cidr"]):
            return "network"
        elif any(kw in desc_lower for kw in ["iam", "role", "policy", "privilege"]):
            return "iam"
        elif any(kw in desc_lower for kw in ["log", "audit", "monitor", "trail"]):
            return "logging"
        else:
            return "configuration"

    def to_dict(self) -> Dict[str, Any]:
        """Return agent configuration as dictionary."""
        return {
            "agent_type": "RedTeamAgent",
            "difficulty": self.difficulty.value,
            "cloud_provider": self.cloud_provider,
            "language": self.language,
            "config": {
                "vuln_count": self.config.vuln_count,
                "subtlety": self.config.subtlety,
                "evasion_target": self.config.evasion_target,
            },
        }


# Convenience function to create Red Team Agent with Bedrock
def create_red_team_agent(
    model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    region: str = "us-east-1",
    difficulty: str = "medium",
    cloud_provider: str = "aws",
    language: str = "terraform",
) -> RedTeamAgent:
    """
    Create a Red Team Agent with AWS Bedrock.
    
    Args:
        model_id: Bedrock model ID
        region: AWS region
        difficulty: easy, medium, or hard
        cloud_provider: aws, azure, or gcp
        language: terraform or cloudformation
        
    Returns:
        Configured RedTeamAgent
    """
    from langchain_aws import ChatBedrock
    
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        model_kwargs={
            "temperature": 0.7,  # More creative for adversarial
            "max_tokens": 8192,  # Enough for detailed JSON responses
        },
    )
    
    return RedTeamAgent(
        llm=llm,
        difficulty=Difficulty(difficulty),
        cloud_provider=cloud_provider,
        language=language,
    )
