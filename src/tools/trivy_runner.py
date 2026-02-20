"""
Trivy IaC Scanner Integration

Trivy is an open-source vulnerability scanner that can detect
misconfigurations in Terraform, CloudFormation, and other IaC formats.

Installation:
    brew install trivy  # macOS
    # or see: https://aquasecurity.github.io/trivy/latest/getting-started/installation/
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
class TrivyConfig:
    """Configuration for Trivy scanner."""
    severity_filter: List[str] = None  # e.g., ["CRITICAL", "HIGH", "MEDIUM"]
    skip_dirs: List[str] = None
    timeout: int = 120  # seconds
    
    def __post_init__(self):
        if self.severity_filter is None:
            self.severity_filter = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        if self.skip_dirs is None:
            self.skip_dirs = []


class TrivyRunner:
    """
    Runs Trivy IaC scanner on code files and converts results to Findings.
    
    Usage:
        runner = TrivyRunner()
        findings = runner.scan(code_files)
    """
    
    def __init__(self, config: Optional[TrivyConfig] = None):
        self.config = config or TrivyConfig()
        self.logger = logging.getLogger("TrivyRunner")
        self._check_trivy_installed()
    
    def _check_trivy_installed(self) -> bool:
        """Check if Trivy is installed and accessible."""
        try:
            result = subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
                self.logger.info(f"Trivy detected: {version}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        self.logger.warning(
            "Trivy not found. Install with: brew install trivy (macOS) "
            "or see https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
        )
        return False
    
    def scan(self, code_files: Dict[str, str]) -> List[Finding]:
        """
        Scan IaC code files with Trivy.
        
        Args:
            code_files: Dict mapping filename to file content
            
        Returns:
            List of Finding objects from Trivy scan
        """
        findings = []
        
        # Create temporary directory with code files
        with tempfile.TemporaryDirectory(prefix="trivy_scan_") as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write code files to temp directory
            for filename, content in code_files.items():
                filepath = tmppath / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)
                self.logger.debug(f"Wrote {filename} ({len(content)} chars)")
            
            # Run Trivy scan
            try:
                findings = self._run_trivy_scan(tmppath)
            except Exception as e:
                self.logger.error(f"Trivy scan failed: {e}")
        
        return findings
    
    def _run_trivy_scan(self, scan_path: Path) -> List[Finding]:
        """Execute Trivy and parse results."""
        
        # Build Trivy command
        cmd = [
            "trivy",
            "config",  # IaC scanning mode
            "--format", "json",
            "--severity", ",".join(self.config.severity_filter),
            "--quiet",  # Suppress progress output
            str(scan_path)
        ]
        
        self.logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            
            if result.returncode not in [0, 1]:  # 1 means vulnerabilities found
                self.logger.error(f"Trivy error: {result.stderr}")
                return []
            
            # Parse JSON output
            if not result.stdout.strip():
                self.logger.info("Trivy returned no results")
                return []
            
            return self._parse_trivy_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Trivy scan timed out after {self.config.timeout}s")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Trivy JSON output: {e}")
            return []
    
    def _parse_trivy_output(self, json_output: str) -> List[Finding]:
        """Convert Trivy JSON output to Finding objects."""
        findings = []
        
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from Trivy: {e}")
            return []
        
        # Handle both single result and array of results
        results = data if isinstance(data, list) else [data]
        
        finding_id = 1
        for result in results:
            # Trivy returns results grouped by target (file)
            target = result.get("Target", "unknown")
            misconfigs = result.get("Misconfigurations", []) or []
            
            for misconfig in misconfigs:
                finding = self._convert_misconfig_to_finding(
                    misconfig, target, finding_id
                )
                if finding:
                    findings.append(finding)
                    finding_id += 1
        
        self.logger.info(f"Trivy found {len(findings)} issues")
        return findings
    
    def _convert_misconfig_to_finding(
        self, misconfig: Dict[str, Any], target: str, finding_id: int
    ) -> Optional[Finding]:
        """Convert a single Trivy misconfiguration to a Finding."""
        
        try:
            # Map Trivy severity to our severity
            severity_map = {
                "CRITICAL": "critical",
                "HIGH": "high",
                "MEDIUM": "medium",
                "LOW": "low",
            }
            
            # Map Trivy type to our vulnerability type
            vuln_type = self._infer_vuln_type(
                misconfig.get("Type", ""),
                misconfig.get("Title", ""),
                misconfig.get("Description", "")
            )
            
            # Extract resource info from cause metadata
            cause = misconfig.get("CauseMetadata", {})
            resource_name = cause.get("Resource", "")
            
            # Handle line numbers - can be StartLine or a range
            start_line = cause.get("StartLine", 0)
            
            return Finding(
                finding_id=f"TRIVY-{finding_id}",
                resource_name=resource_name or target,
                resource_type=cause.get("Provider", "unknown"),
                vulnerability_type=vuln_type,
                severity=severity_map.get(misconfig.get("Severity", "MEDIUM"), "medium"),
                title=misconfig.get("Title", "Unknown Issue"),
                description=misconfig.get("Description", ""),
                evidence=misconfig.get("Message", ""),
                line_number_estimate=start_line,
                confidence=0.95,  # Static analysis tools are high confidence
                reasoning=f"Trivy rule: {misconfig.get('ID', 'unknown')}",
                remediation=misconfig.get("Resolution", ""),
                source="trivy",
            )
        except Exception as e:
            self.logger.warning(f"Failed to convert Trivy finding: {e}")
            return None
    
    def _infer_vuln_type(self, trivy_type: str, title: str, description: str) -> str:
        """Infer vulnerability type from Trivy output."""
        text = f"{trivy_type} {title} {description}".lower()
        
        if any(kw in text for kw in ["encrypt", "kms", "ssl", "tls", "https"]):
            return "encryption"
        elif any(kw in text for kw in ["public", "acl", "access", "exposed"]):
            return "access_control"
        elif any(kw in text for kw in ["security group", "firewall", "ingress", "egress", "cidr", "port"]):
            return "network"
        elif any(kw in text for kw in ["iam", "role", "policy", "permission", "privilege"]):
            return "iam"
        elif any(kw in text for kw in ["log", "audit", "monitor", "trail", "metric"]):
            return "logging"
        elif any(kw in text for kw in ["backup", "version", "retention", "lifecycle"]):
            return "data_protection"
        else:
            return "configuration"
    
    def get_stats(self) -> Dict[str, Any]:
        """Return scanner statistics."""
        return {
            "tool": "trivy",
            "config": {
                "severity_filter": self.config.severity_filter,
                "timeout": self.config.timeout,
            }
        }
