"""
Red Team Manifest Validator - Validates ground truth claims

This module addresses a key research concern: who validates the validator?

The Red Team generates a manifest claiming certain vulnerabilities exist.
This validator uses external static analysis tools (Trivy, Checkov) to 
corroborate these claims, providing an independent ground truth check.

Key metrics:
- manifest_accuracy: % of claimed vulns confirmed by tools
- hallucination_rate: % of claimed vulns not found by any tool
- tool_coverage: which tools found which vulns

Part of the Adversarial IaC Evaluation framework.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.tools.trivy_runner import TrivyRunner
from src.tools.checkov_runner import CheckovRunner
from src.agents.blue_team_agent import Finding


@dataclass
class ManifestValidation:
    """Results of validating Red Team's manifest against static tools."""
    
    # Core metrics
    total_claimed: int
    total_confirmed: int
    total_unconfirmed: int
    manifest_accuracy: float  # confirmed / claimed
    hallucination_rate: float  # unconfirmed / claimed
    
    # Detailed breakdown
    confirmed_vulns: List[Dict[str, Any]]  # Vulns found by tools
    unconfirmed_vulns: List[Dict[str, Any]]  # Potential hallucinations
    tool_findings: List[Finding]  # Raw tool output
    
    # Per-vulnerability details
    vuln_validation: List[Dict[str, Any]]  # Each vuln with its validation status
    
    # Tool coverage
    trivy_confirmed: int
    checkov_confirmed: int
    both_confirmed: int
    
    # For paper reporting
    validation_summary: Dict[str, Any] = field(default_factory=dict)


class ManifestValidator:
    """
    Validates Red Team manifest claims using external static analysis tools.
    
    This provides independent verification that claimed vulnerabilities 
    actually exist in the generated code, addressing the ground truth
    validation concern.
    """
    
    # Mapping from Red Team vuln types to static tool check patterns
    VULN_TYPE_PATTERNS = {
        # Encryption related
        "encryption": ["encrypt", "kms", "sse", "tls", "ssl"],
        "data_protection": ["encrypt", "kms", "rotation", "secret"],
        
        # Access control
        "access_control": ["public", "acl", "policy", "permission", "access"],
        "iam": ["iam", "policy", "role", "permission", "wildcard", "admin"],
        
        # Network
        "network": ["security_group", "ingress", "egress", "cidr", "0.0.0.0", "public"],
        
        # Logging/Monitoring
        "logging": ["logging", "log", "cloudtrail", "audit", "monitor"],
        "monitoring": ["logging", "log", "cloudtrail", "audit", "monitor"],
        
        # General patterns for unknown types
        "unknown": ["public", "encrypt", "log", "permission", "access"],
    }
    
    def __init__(
        self,
        use_trivy: bool = True,
        use_checkov: bool = True,
        language: str = "terraform",
    ):
        """
        Initialize manifest validator.
        
        Args:
            use_trivy: Whether to use Trivy for validation
            use_checkov: Whether to use Checkov for validation
            language: IaC language (terraform/cloudformation)
        """
        self.use_trivy = use_trivy
        self.use_checkov = use_checkov
        self.language = language
        self.logger = logging.getLogger("ManifestValidator")
        
        # Initialize runners
        self.trivy_runner = TrivyRunner() if use_trivy else None
        self.checkov_runner = CheckovRunner() if use_checkov else None
        
        if not use_trivy and not use_checkov:
            self.logger.warning(
                "No static tools enabled for validation. "
                "Enable at least one for ground truth verification."
            )
    
    def validate(
        self,
        code: Dict[str, str],
        manifest: List[Dict[str, Any]],
    ) -> ManifestValidation:
        """
        Validate Red Team manifest against static tool findings.
        
        Args:
            code: Generated IaC code files
            manifest: Red Team's claimed vulnerabilities
            
        Returns:
            ManifestValidation with accuracy metrics and details
        """
        self.logger.info(f"Validating manifest with {len(manifest)} claimed vulnerabilities")
        
        # Step 1: Run static tools on the code
        tool_findings: List[Finding] = []
        trivy_findings: List[Finding] = []
        checkov_findings: List[Finding] = []
        
        if self.trivy_runner:
            try:
                trivy_findings = self.trivy_runner.scan(code)
                tool_findings.extend(trivy_findings)
                self.logger.info(f"Trivy found {len(trivy_findings)} issues")
            except Exception as e:
                self.logger.warning(f"Trivy scan failed: {e}")
        
        if self.checkov_runner:
            try:
                checkov_findings = self.checkov_runner.scan(code, self.language)
                tool_findings.extend(checkov_findings)
                self.logger.info(f"Checkov found {len(checkov_findings)} issues")
            except Exception as e:
                self.logger.warning(f"Checkov scan failed: {e}")
        
        # Step 2: Match manifest claims to tool findings
        vuln_validation = []
        confirmed_vulns = []
        unconfirmed_vulns = []
        
        trivy_confirmed = 0
        checkov_confirmed = 0
        both_confirmed = 0
        
        for vuln in manifest:
            validation = self._validate_vulnerability(
                vuln, trivy_findings, checkov_findings
            )
            vuln_validation.append(validation)
            
            if validation["confirmed"]:
                confirmed_vulns.append(vuln)
                if validation["confirmed_by_trivy"]:
                    trivy_confirmed += 1
                if validation["confirmed_by_checkov"]:
                    checkov_confirmed += 1
                if validation["confirmed_by_trivy"] and validation["confirmed_by_checkov"]:
                    both_confirmed += 1
            else:
                unconfirmed_vulns.append(vuln)
        
        # Step 3: Calculate metrics
        total_claimed = len(manifest)
        total_confirmed = len(confirmed_vulns)
        total_unconfirmed = len(unconfirmed_vulns)
        
        manifest_accuracy = total_confirmed / total_claimed if total_claimed > 0 else 0.0
        hallucination_rate = total_unconfirmed / total_claimed if total_claimed > 0 else 0.0
        
        # Step 4: Build summary for paper
        validation_summary = {
            "manifest_accuracy_pct": round(manifest_accuracy * 100, 1),
            "hallucination_rate_pct": round(hallucination_rate * 100, 1),
            "claimed_vulnerabilities": total_claimed,
            "confirmed_vulnerabilities": total_confirmed,
            "unconfirmed_vulnerabilities": total_unconfirmed,
            "tool_coverage": {
                "trivy_confirmed": trivy_confirmed,
                "checkov_confirmed": checkov_confirmed,
                "both_confirmed": both_confirmed,
                "trivy_total_findings": len(trivy_findings),
                "checkov_total_findings": len(checkov_findings),
            },
            "unconfirmed_vuln_ids": [v.get("vuln_id", "unknown") for v in unconfirmed_vulns],
        }
        
        self.logger.info(
            f"Manifest validation complete: {manifest_accuracy:.1%} accuracy, "
            f"{total_confirmed}/{total_claimed} confirmed"
        )
        
        return ManifestValidation(
            total_claimed=total_claimed,
            total_confirmed=total_confirmed,
            total_unconfirmed=total_unconfirmed,
            manifest_accuracy=manifest_accuracy,
            hallucination_rate=hallucination_rate,
            confirmed_vulns=confirmed_vulns,
            unconfirmed_vulns=unconfirmed_vulns,
            tool_findings=tool_findings,
            vuln_validation=vuln_validation,
            trivy_confirmed=trivy_confirmed,
            checkov_confirmed=checkov_confirmed,
            both_confirmed=both_confirmed,
            validation_summary=validation_summary,
        )
    
    def _validate_vulnerability(
        self,
        vuln: Dict[str, Any],
        trivy_findings: List[Finding],
        checkov_findings: List[Finding],
    ) -> Dict[str, Any]:
        """
        Check if a claimed vulnerability is confirmed by static tools.
        
        Matching logic:
        1. Same resource name (exact or partial match)
        2. Related vulnerability type/pattern
        3. Similar evidence/attribute
        """
        vuln_id = vuln.get("vuln_id", "unknown")
        resource_name = vuln.get("resource_name", "").lower()
        vuln_type = vuln.get("type", "unknown").lower()
        attribute = vuln.get("vulnerable_attribute", "").lower()
        title = vuln.get("title", "").lower()
        
        # Get patterns for this vuln type
        patterns = self.VULN_TYPE_PATTERNS.get(vuln_type, self.VULN_TYPE_PATTERNS["unknown"])
        
        # Check Trivy findings
        trivy_matches = []
        for finding in trivy_findings:
            if self._finding_matches_vuln(finding, resource_name, patterns, attribute, title):
                trivy_matches.append({
                    "finding_id": finding.finding_id,
                    "title": finding.title,
                    "resource": finding.resource_name,
                })
        
        # Check Checkov findings
        checkov_matches = []
        for finding in checkov_findings:
            if self._finding_matches_vuln(finding, resource_name, patterns, attribute, title):
                checkov_matches.append({
                    "finding_id": finding.finding_id,
                    "title": finding.title,
                    "resource": finding.resource_name,
                })
        
        confirmed = len(trivy_matches) > 0 or len(checkov_matches) > 0
        
        return {
            "vuln_id": vuln_id,
            "resource_name": resource_name,
            "vuln_type": vuln_type,
            "confirmed": confirmed,
            "confirmed_by_trivy": len(trivy_matches) > 0,
            "confirmed_by_checkov": len(checkov_matches) > 0,
            "trivy_matches": trivy_matches,
            "checkov_matches": checkov_matches,
            "confidence": self._calculate_confidence(trivy_matches, checkov_matches),
        }
    
    def _finding_matches_vuln(
        self,
        finding: Finding,
        resource_name: str,
        patterns: List[str],
        attribute: str,
        title: str,
    ) -> bool:
        """Check if a tool finding matches a claimed vulnerability."""
        finding_resource = finding.resource_name.lower()
        finding_title = finding.title.lower()
        finding_desc = finding.description.lower() if finding.description else ""
        finding_evidence = finding.evidence.lower() if finding.evidence else ""
        
        # Check resource name match (partial is OK)
        resource_match = (
            resource_name in finding_resource or 
            finding_resource in resource_name or
            self._extract_base_name(resource_name) == self._extract_base_name(finding_resource)
        )
        
        if not resource_match:
            return False
        
        # Check if finding relates to the vulnerability type
        combined_text = f"{finding_title} {finding_desc} {finding_evidence}"
        pattern_match = any(p in combined_text for p in patterns)
        
        # Check attribute match
        attribute_match = attribute and (
            attribute.replace("_", " ") in combined_text or
            attribute in combined_text
        )
        
        # Check title similarity
        title_words = set(title.split())
        finding_words = set(combined_text.split())
        title_overlap = len(title_words & finding_words) >= 2
        
        return pattern_match or attribute_match or title_overlap
    
    def _extract_base_name(self, resource: str) -> str:
        """Extract base resource name from full path."""
        parts = resource.split(".")
        return parts[-1] if parts else resource
    
    def _calculate_confidence(
        self,
        trivy_matches: List[Dict],
        checkov_matches: List[Dict],
    ) -> float:
        """Calculate confidence in the validation."""
        if trivy_matches and checkov_matches:
            return 0.95  # High confidence - both tools agree
        elif trivy_matches or checkov_matches:
            return 0.75  # Medium confidence - one tool confirms
        else:
            return 0.0  # No confirmation


def validation_to_dict(validation: ManifestValidation) -> Dict[str, Any]:
    """Convert ManifestValidation to dictionary for JSON serialization."""
    return {
        "metrics": {
            "manifest_accuracy": validation.manifest_accuracy,
            "hallucination_rate": validation.hallucination_rate,
            "total_claimed": validation.total_claimed,
            "total_confirmed": validation.total_confirmed,
            "total_unconfirmed": validation.total_unconfirmed,
        },
        "tool_coverage": {
            "trivy_confirmed": validation.trivy_confirmed,
            "checkov_confirmed": validation.checkov_confirmed,
            "both_confirmed": validation.both_confirmed,
        },
        "confirmed_vuln_ids": [v.get("vuln_id", "unknown") for v in validation.confirmed_vulns],
        "unconfirmed_vuln_ids": [v.get("vuln_id", "unknown") for v in validation.unconfirmed_vulns],
        "vuln_validation": validation.vuln_validation,
        "summary": validation.validation_summary,
    }
