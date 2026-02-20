"""
Checkov IaC Scanner Integration

Checkov is a policy-as-code tool that scans cloud infrastructure
configurations for security and compliance issues.

Installation:
    pip install checkov
    # or see: https://www.checkov.io/1.Welcome/Quick%20Start.html
"""

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import Finding from blue_team_agent to reuse the same data structure
from src.agents.blue_team_agent import Finding


@dataclass
class CheckovConfig:
    """Configuration for Checkov scanner."""
    framework: List[str] = None  # e.g., ["terraform", "cloudformation"]
    check_types: List[str] = None  # e.g., ["CKV_AWS_*"]
    skip_checks: List[str] = None
    severity_filter: List[str] = None  # e.g., ["CRITICAL", "HIGH"]
    timeout: int = 120  # seconds
    
    def __post_init__(self):
        if self.framework is None:
            self.framework = ["terraform", "cloudformation"]
        if self.check_types is None:
            self.check_types = []
        if self.skip_checks is None:
            self.skip_checks = []
        if self.severity_filter is None:
            self.severity_filter = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


class CheckovRunner:
    """
    Runs Checkov scanner on IaC code files and converts results to Findings.
    
    Usage:
        runner = CheckovRunner()
        findings = runner.scan(code_files, language="terraform")
    """
    
    def __init__(self, config: Optional[CheckovConfig] = None):
        self.config = config or CheckovConfig()
        self.logger = logging.getLogger("CheckovRunner")
        self._check_checkov_installed()
    
    def _check_checkov_installed(self) -> bool:
        """Check if Checkov is installed and accessible."""
        try:
            result = subprocess.run(
                ["checkov", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"Checkov detected: {version}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        self.logger.warning(
            "Checkov not found. Install with: pip install checkov "
            "or see https://www.checkov.io/1.Welcome/Quick%20Start.html"
        )
        return False
    
    def scan(
        self, 
        code_files: Dict[str, str], 
        language: str = "terraform"
    ) -> List[Finding]:
        """
        Scan IaC code files with Checkov.
        
        Args:
            code_files: Dict mapping filename to file content
            language: IaC language ("terraform" or "cloudformation")
            
        Returns:
            List of Finding objects from Checkov scan
        """
        findings = []
        
        # Map language to Checkov framework
        framework_map = {
            "terraform": "terraform",
            "cloudformation": "cloudformation",
        }
        framework = framework_map.get(language, "terraform")
        
        # Create temporary directory with code files
        with tempfile.TemporaryDirectory(prefix="checkov_scan_") as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write code files to temp directory
            for filename, content in code_files.items():
                filepath = tmppath / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)
                self.logger.debug(f"Wrote {filename} ({len(content)} chars)")
            
            # Run Checkov scan
            try:
                findings = self._run_checkov_scan(tmppath, framework)
            except Exception as e:
                self.logger.error(f"Checkov scan failed: {e}")
        
        return findings
    
    def _run_checkov_scan(self, scan_path: Path, framework: str) -> List[Finding]:
        """Execute Checkov and parse results."""
        
        # Build Checkov command
        cmd = [
            "checkov",
            "--directory", str(scan_path),
            "--framework", framework,
            "--output", "json",
            "--quiet",  # Suppress banner and progress
            "--compact",  # Compact output
        ]
        
        # Add check filters if specified
        if self.config.check_types:
            for check in self.config.check_types:
                cmd.extend(["--check", check])
        
        # Add skip checks if specified
        if self.config.skip_checks:
            for skip in self.config.skip_checks:
                cmd.extend(["--skip-check", skip])
        
        self.logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            
            # Checkov returns 1 if issues found, 0 if clean
            if result.returncode not in [0, 1]:
                self.logger.error(f"Checkov error: {result.stderr}")
                return []
            
            # Parse JSON output
            if not result.stdout.strip():
                self.logger.info("Checkov returned no results")
                return []
            
            return self._parse_checkov_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Checkov scan timed out after {self.config.timeout}s")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Checkov JSON output: {e}")
            return []
    
    def _parse_checkov_output(self, json_output: str) -> List[Finding]:
        """Convert Checkov JSON output to Finding objects."""
        findings = []
        
        try:
            # Checkov can return multiple JSON objects, one per framework
            # We need to handle both single object and array cases
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from Checkov: {e}")
            return []
        
        # Handle both single result and array of results
        results = data if isinstance(data, list) else [data]
        
        finding_id = 1
        for result in results:
            # Check for failed checks
            check_results = result.get("results", {})
            failed_checks = check_results.get("failed_checks", [])
            
            for check in failed_checks:
                finding = self._convert_check_to_finding(check, finding_id)
                if finding:
                    # Apply severity filter
                    if finding.severity.upper() in [s.upper() for s in self.config.severity_filter]:
                        findings.append(finding)
                        finding_id += 1
        
        self.logger.info(f"Checkov found {len(findings)} issues")
        return findings
    
    def _convert_check_to_finding(
        self, check: Dict[str, Any], finding_id: int
    ) -> Optional[Finding]:
        """Convert a single Checkov failed check to a Finding."""
        
        try:
            # Map Checkov severity to our severity
            severity = self._determine_severity(check)
            
            # Infer vulnerability type from check ID and guideline
            vuln_type = self._infer_vuln_type(
                check.get("check_id") or "",
                check.get("check_name") or "",
                check.get("guideline") or ""
            )
            
            # Get resource info
            resource = check.get("resource") or "unknown"
            
            # Handle file location
            file_path = check.get("file_path") or ""
            file_line = check.get("file_line_range") or [0, 0]
            start_line = file_line[0] if isinstance(file_line, list) and file_line else 0
            
            return Finding(
                finding_id=f"CKV-{finding_id}",
                resource_name=resource,
                resource_type=check.get("resource_type") or "unknown",
                vulnerability_type=vuln_type,
                severity=severity,
                title=check.get("check_name") or "Unknown Check",
                description=check.get("guideline") or "",
                evidence=f"Resource: {resource} in {file_path}",
                line_number_estimate=start_line,
                confidence=0.95,  # Static analysis tools are high confidence
                reasoning=f"Checkov check: {check.get('check_id') or 'unknown'}",
                remediation=check.get("guideline") or "See Checkov documentation",
                source="checkov",
            )
        except Exception as e:
            self.logger.warning(f"Failed to convert Checkov finding: {e}")
            return None
    
    def _determine_severity(self, check: Dict[str, Any]) -> str:
        """Determine severity from Checkov check."""
        # Checkov doesn't always provide severity, so we infer from check ID
        check_id = (check.get("check_id") or "").upper()
        check_name = (check.get("check_name") or "").lower()
        
        # Critical patterns
        if any(kw in check_name for kw in ["public", "unencrypted", "wildcard", "0.0.0.0"]):
            return "high"
        
        # High severity checks (common patterns)
        if any(prefix in check_id for prefix in ["CKV_AWS_19", "CKV_AWS_20", "CKV_AWS_21"]):
            return "high"
        
        # Check if severity is provided
        if "severity" in check:
            return check["severity"].lower()
        
        # Default to medium
        return "medium"
    
    def _infer_vuln_type(self, check_id: str, check_name: str, guideline: str) -> str:
        """Infer vulnerability type from Checkov check details."""
        # Handle None values safely
        check_id = check_id or ""
        check_name = check_name or ""
        guideline = guideline or ""
        text = f"{check_id} {check_name} {guideline}".lower()
        
        if any(kw in text for kw in ["encrypt", "kms", "ssl", "tls", "https"]):
            return "encryption"
        elif any(kw in text for kw in ["public", "acl", "access", "exposed", "open"]):
            return "access_control"
        elif any(kw in text for kw in ["security group", "firewall", "ingress", "egress", "cidr", "port", "vpc"]):
            return "network"
        elif any(kw in text for kw in ["iam", "role", "policy", "permission", "privilege", "assume"]):
            return "iam"
        elif any(kw in text for kw in ["log", "audit", "monitor", "trail", "metric", "cloudwatch"]):
            return "logging"
        elif any(kw in text for kw in ["backup", "version", "retention", "lifecycle", "recovery"]):
            return "data_protection"
        else:
            return "configuration"
    
    def get_stats(self) -> Dict[str, Any]:
        """Return scanner statistics."""
        return {
            "tool": "checkov",
            "config": {
                "framework": self.config.framework,
                "severity_filter": self.config.severity_filter,
                "timeout": self.config.timeout,
            }
        }
