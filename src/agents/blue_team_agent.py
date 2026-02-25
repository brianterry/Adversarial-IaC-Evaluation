"""
Blue Team Agent - Detects security vulnerabilities in Infrastructure-as-Code

This agent is designed to:
1. Analyze IaC code for security misconfigurations
2. Use LLM reasoning for contextual detection
3. Integrate with static analysis tools (Trivy, Checkov)
4. Output structured findings for scoring

Part of the Adversarial IaC Evaluation framework.
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from ..prompts import AdversarialPrompts, BlueTeamStrategyPrompts


class DetectionMode(Enum):
    """Detection modes for Blue Team"""
    LLM_ONLY = "llm_only"           # Pure LLM analysis
    TOOLS_ONLY = "tools_only"       # Static tools only (Trivy/Checkov)
    HYBRID = "hybrid"               # LLM + Tools combined


@dataclass
class Finding:
    """A detected security vulnerability"""
    finding_id: str
    resource_name: str
    resource_type: str
    vulnerability_type: str
    severity: str
    title: str
    description: str
    evidence: str
    line_number_estimate: int
    confidence: float
    reasoning: str
    remediation: str
    source: str  # "llm", "trivy", "checkov", or "hybrid"


@dataclass
class BlueTeamOutput:
    """Output from Blue Team Agent"""
    findings: List[Finding]
    analysis_summary: Dict[str, Any]
    detection_stats: Dict[str, Any] = field(default_factory=dict)


class BlueTeamAgent:
    """
    Defensive agent that detects vulnerabilities in IaC code.
    
    This agent:
    1. Analyzes code using LLM reasoning
    2. Optionally runs static analysis tools
    3. Combines findings from multiple sources
    4. Outputs structured detection results
    """

    # Language configurations
    LANGUAGE_CONFIGS = {
        "terraform": {
            "extension": "tf",
            "trivy_type": "terraform",
            "checkov_framework": "terraform",
        },
        "cloudformation": {
            "extension": "yaml",
            "trivy_type": "cloudformation",
            "checkov_framework": "cloudformation",
        },
    }

    # Type definitions for targeted detection
    TYPE_DEFINITIONS = {
        "encryption": "Missing encryption at rest/in transit, weak algorithms, unmanaged keys, missing KMS",
        "iam": "Overly permissive policies, missing least privilege, wildcard permissions, admin access",
        "network": "Open security groups, exposed endpoints, missing network segmentation, public subnets",
        "logging": "Disabled audit trails, missing access logs, no monitoring, CloudTrail gaps",
        "access_control": "Public access, missing authentication, weak authorization, open ACLs",
    }

    def __init__(
        self,
        llm: BaseChatModel,
        mode: DetectionMode = DetectionMode.LLM_ONLY,
        language: str = "terraform",
        use_trivy: bool = False,
        use_checkov: bool = False,
        strategy: str = "comprehensive",
        target_type: Optional[str] = None,
        compliance_framework: Optional[str] = None,
        iterations: int = 1,
        scenario_description: str = "",
    ):
        """
        Initialize Blue Team Agent.
        
        Args:
            llm: LangChain chat model (e.g., ChatBedrock)
            mode: Detection mode (LLM only, tools only, or hybrid)
            language: IaC language (terraform, cloudformation)
            use_trivy: Whether to use Trivy scanner
            use_checkov: Whether to use Checkov scanner
            strategy: Defense strategy - "comprehensive", "targeted", "iterative", "threat_model", "compliance"
            target_type: For "targeted" strategy - "encryption", "iam", "network", "logging", "access_control"
            compliance_framework: For "compliance" strategy - "hipaa", "pci_dss", "soc2", "cis"
            iterations: For "iterative" strategy - number of analysis passes
            scenario_description: For "threat_model" strategy - scenario context
        """
        self.llm = llm
        self.mode = mode
        self.language = language
        self.use_trivy = use_trivy
        self.use_checkov = use_checkov
        self.strategy = strategy
        self.target_type = target_type
        self.compliance_framework = compliance_framework
        self.iterations = iterations
        self.scenario_description = scenario_description
        self.logger = logging.getLogger("BlueTeamAgent")
        
        # Validate strategy
        valid_strategies = ["comprehensive", "targeted", "iterative", "threat_model", "compliance"]
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{strategy}'. Valid: {valid_strategies}")
        
        # Validate target_type for targeted strategy
        if strategy == "targeted":
            valid_types = list(self.TYPE_DEFINITIONS.keys())
            if not target_type:
                raise ValueError("target_type required for 'targeted' strategy")
            if target_type not in valid_types:
                raise ValueError(f"Invalid target_type '{target_type}'. Valid: {valid_types}")
        
        # Validate compliance_framework for compliance strategy
        if strategy == "compliance":
            valid_frameworks = ["hipaa", "pci_dss", "soc2", "cis"]
            if not compliance_framework:
                raise ValueError("compliance_framework required for 'compliance' strategy")
            if compliance_framework not in valid_frameworks:
                raise ValueError(f"Invalid compliance_framework '{compliance_framework}'. Valid: {valid_frameworks}")
        
        self.lang_config = self.LANGUAGE_CONFIGS.get(
            language, self.LANGUAGE_CONFIGS["terraform"]
        )

    async def execute(self, code: Dict[str, str]) -> BlueTeamOutput:
        """
        Execute Blue Team defense: analyze code for vulnerabilities.
        
        Args:
            code: Dictionary of filename -> content
            
        Returns:
            BlueTeamOutput with findings and analysis
        """
        self.logger.info(f"Blue Team analyzing code in {self.mode.value} mode with {self.strategy} strategy")
        
        all_findings: List[Finding] = []
        strategy_metadata: Dict[str, Any] = {"strategy": self.strategy}
        
        # Step 1: Strategy-specific LLM Analysis (if enabled)
        if self.mode in [DetectionMode.LLM_ONLY, DetectionMode.HYBRID]:
            self.logger.info(f"Step 1: Running {self.strategy} LLM analysis")
            
            if self.strategy == "targeted":
                llm_findings = await self._analyze_targeted(code)
                strategy_metadata["target_type"] = self.target_type
            elif self.strategy == "iterative":
                llm_findings, iteration_data = await self._analyze_iterative(code)
                strategy_metadata["iterations"] = iteration_data
            elif self.strategy == "threat_model":
                llm_findings, threat_model = await self._analyze_threat_model(code)
                strategy_metadata["threat_model"] = threat_model
            elif self.strategy == "compliance":
                llm_findings, compliance_report = await self._analyze_compliance(code)
                strategy_metadata["compliance_report"] = compliance_report
            else:
                # Default comprehensive strategy
                llm_findings = await self._analyze_with_llm(code)
            
            all_findings.extend(llm_findings)
            self.logger.info(f"LLM found {len(llm_findings)} potential issues")
        
        # Step 2: Static Tool Analysis (if enabled)
        if self.mode in [DetectionMode.TOOLS_ONLY, DetectionMode.HYBRID]:
            self.logger.info("Step 2: Running static analysis tools")
            
            if self.use_trivy:
                trivy_findings = await self._analyze_with_trivy(code)
                all_findings.extend(trivy_findings)
                self.logger.info(f"Trivy found {len(trivy_findings)} issues")
            
            if self.use_checkov:
                checkov_findings = await self._analyze_with_checkov(code)
                all_findings.extend(checkov_findings)
                self.logger.info(f"Checkov found {len(checkov_findings)} issues")
        
        # Step 3: Deduplicate findings (for hybrid mode)
        if self.mode == DetectionMode.HYBRID:
            all_findings = self._deduplicate_findings(all_findings)
            self.logger.info(f"After deduplication: {len(all_findings)} findings")
        
        # Step 4: Compile output
        output = BlueTeamOutput(
            findings=all_findings,
            analysis_summary=self._create_summary(all_findings, code),
            detection_stats={
                "mode": self.mode.value,
                "strategy": self.strategy,
                "total_findings": len(all_findings),
                "by_source": self._count_by_source(all_findings),
                "by_severity": self._count_by_severity(all_findings),
                "strategy_metadata": strategy_metadata,
            },
        )
        
        self.logger.info(
            f"Blue Team complete: {len(all_findings)} findings, "
            f"mode={self.mode.value}, strategy={self.strategy}"
        )
        
        return output

    async def _analyze_with_llm(self, code: Dict[str, str]) -> List[Finding]:
        """Analyze code using LLM reasoning."""
        findings = []
        
        # Combine all code files for analysis
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Build detection prompt
        prompt = AdversarialPrompts.BLUE_TEAM_DETECTION.format(
            language=self.language,
            code=combined_code,
        )
        
        # Get LLM analysis
        response = await self._invoke_llm(prompt)
        
        # Parse findings
        findings = self._parse_llm_findings(response)
        
        return findings

    async def _analyze_targeted(self, code: Dict[str, str]) -> List[Finding]:
        """Analyze code with focus on a specific vulnerability type."""
        findings = []
        
        # Combine all code files for analysis
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Build targeted detection prompt
        prompt = BlueTeamStrategyPrompts.TARGETED_DETECTION.format(
            target_type=self.target_type,
            type_definition=self.TYPE_DEFINITIONS.get(self.target_type, ""),
            language=self.language,
            code=combined_code,
        )
        
        # Get LLM analysis
        response = await self._invoke_llm(prompt)
        
        # Parse findings
        findings = self._parse_llm_findings(response)
        
        # Tag findings with strategy
        for f in findings:
            f.source = f"llm_targeted_{self.target_type}"
        
        return findings

    async def _analyze_iterative(self, code: Dict[str, str]) -> tuple[List[Finding], Dict[str, Any]]:
        """Analyze code with multiple iterative passes."""
        all_findings = []
        iteration_data = {"passes": [], "refinements": []}
        previous_findings_json = "[]"
        investigation_areas_json = "[]"
        
        # Combine all code files for analysis
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        for pass_num in range(1, self.iterations + 1):
            self.logger.info(f"Iterative analysis pass {pass_num}/{self.iterations}")
            
            if pass_num == 1:
                # First pass
                prompt = BlueTeamStrategyPrompts.ITERATIVE_DETECTION_PASS1.format(
                    pass_number=pass_num,
                    total_passes=self.iterations,
                    language=self.language,
                    code=combined_code,
                )
            else:
                # Refinement passes
                prompt = BlueTeamStrategyPrompts.ITERATIVE_DETECTION_REFINE.format(
                    pass_number=pass_num,
                    total_passes=self.iterations,
                    language=self.language,
                    code=combined_code,
                    previous_findings=previous_findings_json,
                    investigation_areas=investigation_areas_json,
                )
            
            response = await self._invoke_llm(prompt)
            pass_findings = self._parse_llm_findings(response)
            
            # Extract investigation areas for next pass
            try:
                parsed = json.loads(self._extract_json(response))
                investigation_areas_json = json.dumps(
                    parsed.get("areas_for_deeper_investigation", [])
                )
            except:
                investigation_areas_json = "[]"
            
            # Store previous findings for next pass
            previous_findings_json = json.dumps([{
                "finding_id": f.finding_id,
                "resource_name": f.resource_name,
                "title": f.title,
                "severity": f.severity,
                "confidence": f.confidence,
            } for f in pass_findings])
            
            # Tag findings with pass number
            for f in pass_findings:
                f.source = f"llm_iterative_pass{pass_num}"
            
            iteration_data["passes"].append({
                "pass_number": pass_num,
                "findings_count": len(pass_findings),
            })
            
            all_findings = pass_findings  # Each pass refines, so keep latest
        
        return all_findings, iteration_data

    async def _analyze_threat_model(self, code: Dict[str, str]) -> tuple[List[Finding], Dict[str, Any]]:
        """Analyze code using threat modeling approach."""
        # Combine all code files for analysis
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Build threat model detection prompt
        prompt = BlueTeamStrategyPrompts.THREAT_MODEL_DETECTION.format(
            language=self.language,
            code=combined_code,
            scenario_description=self.scenario_description or "Infrastructure deployment",
        )
        
        # Get LLM analysis
        response = await self._invoke_llm(prompt)
        
        # Parse findings and threat model
        findings = self._parse_llm_findings(response)
        
        # Extract threat model data
        threat_model = {}
        try:
            parsed = json.loads(self._extract_json(response))
            threat_model = parsed.get("threat_model", {})
        except:
            pass
        
        # Tag findings with strategy
        for f in findings:
            f.source = "llm_threat_model"
        
        return findings, threat_model

    async def _analyze_compliance(self, code: Dict[str, str]) -> tuple[List[Finding], Dict[str, Any]]:
        """Analyze code against a specific compliance framework."""
        # Combine all code files for analysis
        combined_code = ""
        for filename, content in code.items():
            combined_code += f"\n# === {filename} ===\n{content}\n"
        
        # Get framework requirements
        framework_requirements = self._get_framework_requirements()
        
        # Build compliance detection prompt
        prompt = BlueTeamStrategyPrompts.COMPLIANCE_DETECTION.format(
            framework=self.compliance_framework.upper(),
            framework_requirements=framework_requirements,
            language=self.language,
            code=combined_code,
        )
        
        # Get LLM analysis
        response = await self._invoke_llm(prompt)
        
        # Parse findings
        findings = self._parse_llm_findings(response)
        
        # Extract compliance report
        compliance_report = {}
        try:
            parsed = json.loads(self._extract_json(response))
            compliance_report = parsed.get("compliance_summary", {})
        except:
            pass
        
        # Tag findings with framework
        for f in findings:
            f.source = f"llm_compliance_{self.compliance_framework}"
        
        return findings, compliance_report

    def _get_framework_requirements(self) -> str:
        """Get the compliance framework requirements text."""
        framework_map = {
            "hipaa": BlueTeamStrategyPrompts.HIPAA_REQUIREMENTS,
            "pci_dss": BlueTeamStrategyPrompts.PCI_DSS_REQUIREMENTS,
            "soc2": BlueTeamStrategyPrompts.SOC2_REQUIREMENTS,
            "cis": BlueTeamStrategyPrompts.CIS_REQUIREMENTS,
        }
        return framework_map.get(self.compliance_framework, "")

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response text."""
        # Try to find JSON in code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group(0)
        
        return text

    async def _analyze_with_trivy(self, code: Dict[str, str]) -> List[Finding]:
        """Analyze code using Trivy scanner."""
        findings = []
        
        # Check if trivy is available
        if not self._check_tool_available("trivy"):
            self.logger.warning("Trivy not available, skipping")
            return findings
        
        # Write code to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            for filename, content in code.items():
                filepath = Path(tmpdir) / filename
                filepath.write_text(content)
            
            try:
                # Run trivy
                result = subprocess.run(
                    [
                        "trivy", "config",
                        "--format", "json",
                        "--severity", "CRITICAL,HIGH,MEDIUM,LOW",
                        tmpdir
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                
                if result.returncode == 0 or result.stdout:
                    trivy_output = json.loads(result.stdout) if result.stdout else {}
                    findings = self._parse_trivy_findings(trivy_output)
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("Trivy scan timed out")
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse Trivy output: {e}")
            except Exception as e:
                self.logger.warning(f"Trivy scan failed: {e}")
        
        return findings

    async def _analyze_with_checkov(self, code: Dict[str, str]) -> List[Finding]:
        """Analyze code using Checkov scanner."""
        findings = []
        
        # Check if checkov is available
        if not self._check_tool_available("checkov"):
            self.logger.warning("Checkov not available, skipping")
            return findings
        
        # Write code to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            for filename, content in code.items():
                filepath = Path(tmpdir) / filename
                filepath.write_text(content)
            
            try:
                # Run checkov
                result = subprocess.run(
                    [
                        "checkov",
                        "-d", tmpdir,
                        "--framework", self.lang_config["checkov_framework"],
                        "--output", "json",
                        "--quiet",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                
                if result.stdout:
                    checkov_output = json.loads(result.stdout)
                    findings = self._parse_checkov_findings(checkov_output)
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("Checkov scan timed out")
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse Checkov output: {e}")
            except Exception as e:
                self.logger.warning(f"Checkov scan failed: {e}")
        
        return findings

    def _check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH."""
        try:
            subprocess.run(
                [tool, "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM with the given prompt."""
        try:
            self.logger.debug(f"Sending prompt ({len(prompt)} chars)")
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            self.logger.info(f"LLM response: {len(content)} chars")
            return content
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            raise

    def _parse_llm_findings(self, response: str) -> List[Finding]:
        """Parse LLM detection response into findings."""
        findings = []
        
        if not response:
            return findings
        
        # Try to extract JSON from response
        json_content = self._extract_json(response)
        if not json_content:
            self.logger.warning("Could not extract JSON from LLM response")
            return findings
        
        try:
            data = json.loads(json_content)
            detected = data.get("detected_vulnerabilities", [])
            
            for i, v in enumerate(detected):
                finding = Finding(
                    finding_id=v.get("finding_id", f"LLM-{i+1}"),
                    resource_name=v.get("resource_name", "unknown"),
                    resource_type=v.get("resource_type", "unknown"),
                    vulnerability_type=v.get("vulnerability_type", "unknown"),
                    severity=v.get("severity", "medium"),
                    title=v.get("title", "Untitled finding"),
                    description=v.get("description", ""),
                    evidence=v.get("evidence", ""),
                    line_number_estimate=v.get("line_number_estimate", 0),
                    confidence=v.get("confidence", 0.5),
                    reasoning=v.get("reasoning", ""),
                    remediation=v.get("remediation", ""),
                    source="llm",
                )
                findings.append(finding)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse LLM findings: {e}")
        
        return findings

    def _parse_trivy_findings(self, trivy_output: Dict) -> List[Finding]:
        """Parse Trivy output into findings."""
        findings = []
        
        results = trivy_output.get("Results", [])
        finding_count = 0
        
        for result in results:
            misconfigs = result.get("Misconfigurations", [])
            
            for m in misconfigs:
                finding_count += 1
                finding = Finding(
                    finding_id=f"TRIVY-{finding_count}",
                    resource_name=m.get("CauseMetadata", {}).get("Resource", "unknown"),
                    resource_type=m.get("CauseMetadata", {}).get("Provider", "unknown"),
                    vulnerability_type=m.get("Type", "misconfiguration"),
                    severity=m.get("Severity", "MEDIUM").lower(),
                    title=m.get("Title", "Untitled"),
                    description=m.get("Description", ""),
                    evidence=m.get("Message", ""),
                    line_number_estimate=m.get("CauseMetadata", {}).get("StartLine", 0),
                    confidence=0.9,  # High confidence for static tools
                    reasoning=f"Trivy rule: {m.get('ID', 'unknown')}",
                    remediation=m.get("Resolution", ""),
                    source="trivy",
                )
                findings.append(finding)
        
        return findings

    def _parse_checkov_findings(self, checkov_output: Dict) -> List[Finding]:
        """Parse Checkov output into findings."""
        findings = []
        
        # Checkov output structure can vary
        results = checkov_output.get("results", {})
        failed_checks = results.get("failed_checks", [])
        
        for i, check in enumerate(failed_checks):
            finding = Finding(
                finding_id=f"CHECKOV-{i+1}",
                resource_name=check.get("resource", "unknown"),
                resource_type=check.get("resource_type", "unknown"),
                vulnerability_type=check.get("check_type", "misconfiguration"),
                severity=self._checkov_severity(check.get("severity")),
                title=check.get("check_name", "Untitled"),
                description=check.get("guideline", ""),
                evidence=check.get("code_block", ""),
                line_number_estimate=check.get("file_line_range", [0])[0],
                confidence=0.85,  # High confidence for static tools
                reasoning=f"Checkov check: {check.get('check_id', 'unknown')}",
                remediation=check.get("guideline", ""),
                source="checkov",
            )
            findings.append(finding)
        
        return findings

    def _checkov_severity(self, severity: Optional[str]) -> str:
        """Convert Checkov severity to standard format."""
        if not severity:
            return "medium"
        severity_map = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "INFO": "low",
        }
        return severity_map.get(severity.upper(), "medium")

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text."""
        # Try multiple strategies
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
                    # Validate it's parseable
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

    def _deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Remove duplicate findings from multiple sources."""
        seen = set()
        unique = []
        
        for f in findings:
            # Create a key based on resource and issue type
            key = (
                f.resource_name.lower(),
                f.vulnerability_type.lower(),
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(f)
            else:
                # Update existing if this one has higher confidence
                for i, existing in enumerate(unique):
                    existing_key = (
                        existing.resource_name.lower(),
                        existing.vulnerability_type.lower(),
                    )
                    if existing_key == key and f.confidence > existing.confidence:
                        unique[i] = f
                        break
        
        return unique

    def _create_summary(
        self, findings: List[Finding], code: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create analysis summary."""
        total_lines = sum(len(c.split("\n")) for c in code.values())
        
        return {
            "total_resources_analyzed": self._count_resources(code),
            "total_lines": total_lines,
            "total_findings": len(findings),
            "findings_by_severity": self._count_by_severity(findings),
            "risk_assessment": self._assess_risk(findings),
            "confidence_level": self._overall_confidence(findings),
        }

    def _count_resources(self, code: Dict[str, str]) -> int:
        """Count resources in code."""
        count = 0
        for content in code.values():
            # Terraform
            count += len(re.findall(r'resource\s+"[^"]+"\s+"[^"]+"', content))
            # CloudFormation
            count += len(re.findall(r'^\s{2}[A-Z][a-zA-Z0-9]+:\s*$', content, re.MULTILINE))
        return max(count, 1)  # At least 1

    def _count_by_source(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by source."""
        counts = {"llm": 0, "trivy": 0, "checkov": 0}
        for f in findings:
            if f.source in counts:
                counts[f.source] += 1
        return counts

    def _count_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.severity.lower()
            if sev in counts:
                counts[sev] += 1
        return counts

    def _assess_risk(self, findings: List[Finding]) -> str:
        """Assess overall risk level."""
        severity_counts = self._count_by_severity(findings)
        
        if severity_counts["critical"] > 0:
            return "critical"
        elif severity_counts["high"] >= 2:
            return "high"
        elif severity_counts["high"] == 1 or severity_counts["medium"] >= 3:
            return "medium"
        elif findings:
            return "low"
        else:
            return "secure"

    def _overall_confidence(self, findings: List[Finding]) -> str:
        """Calculate overall confidence level."""
        if not findings:
            return "high"
        
        avg_confidence = sum(f.confidence for f in findings) / len(findings)
        
        if avg_confidence >= 0.8:
            return "high"
        elif avg_confidence >= 0.5:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> Dict[str, Any]:
        """Return agent configuration as dictionary."""
        return {
            "agent_type": "BlueTeamAgent",
            "mode": self.mode.value,
            "language": self.language,
            "use_trivy": self.use_trivy,
            "use_checkov": self.use_checkov,
        }


# Convenience function to create Blue Team Agent with Bedrock
def create_blue_team_agent(
    model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    region: str = "us-east-1",
    mode: str = "llm_only",
    language: str = "terraform",
    use_trivy: bool = False,
    use_checkov: bool = False,
    strategy: str = "comprehensive",
    target_type: Optional[str] = None,
    compliance_framework: Optional[str] = None,
    iterations: int = 1,
    scenario_description: str = "",
) -> BlueTeamAgent:
    """
    Create a Blue Team Agent with AWS Bedrock.
    
    Args:
        model_id: Bedrock model ID
        region: AWS region
        mode: llm_only, tools_only, or hybrid
        language: terraform or cloudformation
        use_trivy: Enable Trivy scanner
        use_checkov: Enable Checkov scanner
        strategy: Defense strategy - "comprehensive", "targeted", "iterative", "threat_model", "compliance"
        target_type: For "targeted" strategy - "encryption", "iam", "network", "logging", "access_control"
        compliance_framework: For "compliance" strategy - "hipaa", "pci_dss", "soc2", "cis"
        iterations: For "iterative" strategy - number of analysis passes
        scenario_description: For "threat_model" strategy - scenario context
        
    Returns:
        Configured BlueTeamAgent
    """
    from langchain_aws import ChatBedrock
    
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        model_kwargs={
            "temperature": 0.3,  # Lower temperature for precise analysis
            "max_tokens": 8192,
        },
    )
    
    return BlueTeamAgent(
        llm=llm,
        mode=DetectionMode(mode),
        language=language,
        use_trivy=use_trivy,
        use_checkov=use_checkov,
        strategy=strategy,
        target_type=target_type,
        compliance_framework=compliance_framework,
        iterations=iterations,
        scenario_description=scenario_description,
    )
