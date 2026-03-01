"""
Manifest Validation Gate

Runs BEFORE scoring to partition Red Team's manifest into:
- confirmed: Vulnerabilities that Trivy or Checkov can find in the generated code
- phantom: Claimed vulnerabilities with no tool corroboration (excluded from ground truth)

This is the load-bearing component for ground truth validity. Without it,
recall is measured against partially hallucinated ground truth.

Fuzzy matching rules:
- Resource type match (e.g., "aws_s3_bucket" in both manifest and tool finding)
- Vulnerability category match (encryption, logging, public_access, iam, network)
- No semantic LLM matching — that reintroduces the hallucination problem
"""

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ManifestGate")


# ============================================================================
# Vulnerability category mapping for fuzzy matching
# ============================================================================

CATEGORY_KEYWORDS = {
    "encryption": [
        "encrypt", "kms", "sse", "ssl", "tls", "https", "at-rest", "in-transit",
        "server-side-encryption", "aes", "cmk", "unencrypt",
    ],
    "logging": [
        "log", "audit", "trail", "monitor", "cloudtrail", "cloudwatch",
        "access-log", "flow-log", "metric",
    ],
    "public_access": [
        "public", "acl", "open", "exposed", "0.0.0.0", "world",
        "block-public", "restrict", "unrestrict",
    ],
    "iam": [
        "iam", "role", "policy", "permission", "privilege", "assume",
        "wildcard", "star-action", "admin", "root", "least-privilege",
    ],
    "network": [
        "security-group", "firewall", "ingress", "egress", "cidr",
        "port", "vpc", "subnet", "nacl", "sg-",
    ],
    "backup": [
        "backup", "version", "retention", "lifecycle", "recovery",
        "mfa-delete", "replication", "snapshot",
    ],
    "secrets": [
        "secret", "password", "credential", "token", "rotation",
        "plaintext", "hardcoded", "ssm", "parameter-store",
    ],
}


def _categorize_text(text: str) -> Set[str]:
    """Extract vulnerability categories from a text string."""
    text_lower = text.lower().replace("_", "-").replace(" ", "-")
    categories = set()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            categories.add(category)
    return categories


def _extract_resource_type(resource_name: str) -> Optional[str]:
    """Extract the resource type from a resource name like 'aws_s3_bucket.my_bucket'."""
    if not resource_name:
        return None
    # Handle full resource address: aws_s3_bucket.my_bucket → aws_s3_bucket
    parts = resource_name.split(".")
    if len(parts) >= 2 and parts[0].startswith(("aws_", "azurerm_", "google_")):
        return parts[0]
    # Handle bare resource type
    if resource_name.startswith(("aws_", "azurerm_", "google_")):
        return resource_name
    return resource_name


# ============================================================================
# Core gate logic
# ============================================================================

@dataclass
class GateResult:
    """Result of manifest validation gate."""
    confirmed: List[Dict[str, Any]]  # Entries corroborated by tools
    phantom: List[Dict[str, Any]]    # Entries with no tool corroboration
    manifest_accuracy: float          # confirmed / total
    confirmed_count: int
    phantom_count: int
    total_count: int
    # Per-entry matching details
    match_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_accuracy": self.manifest_accuracy,
            "confirmed_count": self.confirmed_count,
            "phantom_count": self.phantom_count,
            "total_count": self.total_count,
            "confirmed_vuln_ids": [e.get("vuln_id", "?") for e in self.confirmed],
            "phantom_vuln_ids": [e.get("vuln_id", "?") for e in self.phantom],
            "match_details": self.match_details,
        }


def validate_manifest_entry(
    entry: Dict[str, Any],
    tool_findings: List[Dict[str, Any]],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a single manifest entry is corroborated by any tool finding.
    
    Matching is fuzzy:
    1. Resource type overlap (aws_s3_bucket matches aws_s3_bucket)
    2. Vulnerability category overlap (encryption keywords in both)
    
    Returns:
        (is_confirmed, matching_finding_or_None)
    """
    entry_resource = _extract_resource_type(entry.get("resource_name", ""))
    entry_resource_lower = (entry.get("resource_name", "") or "").lower()
    
    # Build category set from entry
    entry_text = " ".join([
        entry.get("title", ""),
        entry.get("type", ""),
        entry.get("vulnerable_attribute", ""),
        entry.get("detection_hint", ""),
        entry.get("description", ""),
    ])
    entry_categories = _categorize_text(entry_text)
    
    best_match = None
    best_score = 0
    
    for finding in tool_findings:
        score = 0
        
        finding_resource = (finding.get("resource_name", "") or "").lower()
        finding_resource_type = _extract_resource_type(finding_resource)
        
        # Resource type match
        if entry_resource and finding_resource_type:
            if entry_resource.lower() == finding_resource_type.lower():
                score += 2
            elif entry_resource.lower() in finding_resource.lower() or finding_resource_type.lower() in entry_resource_lower:
                score += 1
        
        # Resource name substring match (e.g., "bucket" in both)
        if entry_resource_lower and finding_resource:
            entry_base = entry_resource_lower.split(".")[-1] if "." in entry_resource_lower else entry_resource_lower
            finding_base = finding_resource.split(".")[-1] if "." in finding_resource else finding_resource
            if entry_base and finding_base and (entry_base in finding_base or finding_base in entry_base):
                score += 1
        
        # Category match
        finding_text = " ".join([
            finding.get("title", ""),
            finding.get("description", ""),
            finding.get("check_id", ""),
            finding.get("check_name", ""),
            finding.get("rule_id", ""),
        ])
        finding_categories = _categorize_text(finding_text)
        
        category_overlap = entry_categories & finding_categories
        if category_overlap:
            score += len(category_overlap)
        
        if score > best_score:
            best_score = score
            best_match = finding
    
    # Threshold: need resource match (score >= 1) AND category match (score >= 2)
    # Or strong resource match alone (score >= 2 from resource matching)
    is_confirmed = best_score >= 2
    
    return is_confirmed, best_match if is_confirmed else None


def run_manifest_gate(
    code: Dict[str, str],
    manifest: List[Dict[str, Any]],
    use_trivy: bool = True,
    use_checkov: bool = True,
    language: str = "terraform",
) -> GateResult:
    """
    Run the manifest validation gate.
    
    1. Runs Trivy and/or Checkov on generated code
    2. Cross-references each manifest entry against tool findings
    3. Partitions manifest into confirmed and phantom lists
    
    Args:
        code: Generated IaC code files (filename → content)
        manifest: Red Team's claimed vulnerabilities (list of dicts)
        use_trivy: Whether to run Trivy
        use_checkov: Whether to run Checkov
        language: IaC language (terraform, cloudformation)
    
    Returns:
        GateResult with confirmed and phantom lists
    """
    if not manifest:
        return GateResult(
            confirmed=[], phantom=[], manifest_accuracy=0.0,
            confirmed_count=0, phantom_count=0, total_count=0,
        )
    
    # Collect tool findings
    all_tool_findings: List[Dict[str, Any]] = []
    
    if use_trivy:
        try:
            from src.tools.trivy_runner import TrivyRunner
            trivy = TrivyRunner()
            trivy_findings = trivy.scan(code)
            for f in trivy_findings:
                all_tool_findings.append({
                    "resource_name": f.resource_name,
                    "title": f.title,
                    "description": f.description,
                    "check_id": getattr(f, 'reasoning', ''),
                    "tool": "trivy",
                })
            logger.info(f"Trivy found {len(trivy_findings)} issues for gate validation")
        except Exception as e:
            logger.warning(f"Trivy gate scan failed: {e}")
    
    if use_checkov:
        try:
            from src.tools.checkov_runner import CheckovRunner
            checkov = CheckovRunner()
            checkov_findings = checkov.scan(code, language)
            for f in checkov_findings:
                all_tool_findings.append({
                    "resource_name": f.resource_name,
                    "title": f.title,
                    "description": f.description,
                    "check_id": getattr(f, 'reasoning', ''),
                    "check_name": f.title,
                    "tool": "checkov",
                })
            logger.info(f"Checkov found {len(checkov_findings)} issues for gate validation")
        except Exception as e:
            logger.warning(f"Checkov gate scan failed: {e}")
    
    if not all_tool_findings:
        logger.warning("No tool findings available for manifest gate — all entries treated as phantom")
        return GateResult(
            confirmed=[], phantom=list(manifest),
            manifest_accuracy=0.0,
            confirmed_count=0, phantom_count=len(manifest), total_count=len(manifest),
        )
    
    # Validate each entry
    confirmed = []
    phantom = []
    match_details = []
    
    for entry in manifest:
        is_confirmed, matching_finding = validate_manifest_entry(entry, all_tool_findings)
        
        detail = {
            "vuln_id": entry.get("vuln_id", "?"),
            "is_novel": entry.get("is_novel", False),
            "rule_source": entry.get("rule_source", "unknown"),
            "confirmed": is_confirmed,
            "matching_tool_finding": matching_finding.get("title", "N/A") if matching_finding else None,
            "matching_tool": matching_finding.get("tool", "N/A") if matching_finding else None,
        }
        match_details.append(detail)
        
        if is_confirmed:
            confirmed.append(entry)
        else:
            phantom.append(entry)
    
    total = len(manifest)
    accuracy = len(confirmed) / total if total > 0 else 0.0
    
    logger.info(
        f"Manifest gate: {len(confirmed)}/{total} confirmed ({accuracy:.0%}), "
        f"{len(phantom)} phantom"
    )
    
    # Log per-source breakdown if mixed
    novel_total = sum(1 for e in manifest if e.get("is_novel"))
    db_total = total - novel_total
    if novel_total > 0 and db_total > 0:
        novel_confirmed = sum(1 for e in confirmed if e.get("is_novel"))
        db_confirmed = len(confirmed) - novel_confirmed
        logger.info(
            f"  Database: {db_confirmed}/{db_total} confirmed ({db_confirmed/db_total:.0%}), "
            f"Novel: {novel_confirmed}/{novel_total} confirmed ({novel_confirmed/novel_total:.0%})"
        )
    
    return GateResult(
        confirmed=confirmed,
        phantom=phantom,
        manifest_accuracy=accuracy,
        confirmed_count=len(confirmed),
        phantom_count=len(phantom),
        total_count=total,
        match_details=match_details,
    )
