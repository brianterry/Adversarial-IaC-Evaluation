"""
Judge Agent - Scores Red Team vs Blue Team matches

This agent:
1. Compares Blue Team findings against Red Team ground truth
2. Calculates precision, recall, and F1 scores
3. Identifies true positives, false positives, and false negatives
4. Provides detailed match explanations

Part of the Adversarial IaC Evaluation framework.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage


@dataclass
class Match:
    """A match between a Red Team vulnerability and Blue Team finding"""
    red_vuln_id: str
    blue_finding_id: Optional[str]
    match_type: str  # "exact", "partial", "missed"
    confidence: float
    explanation: str


@dataclass
class ScoringResult:
    """Complete scoring results for a game"""
    matches: List[Match]
    true_positives: List[str]  # Blue finding IDs
    false_positives: List[str]  # Blue finding IDs
    false_negatives: List[str]  # Red vuln IDs
    
    # Metrics
    precision: float
    recall: float
    f1_score: float
    
    # Red Team metrics
    evasion_rate: float  # % of vulns that evaded detection
    
    # Additional stats
    total_red_vulns: int
    total_blue_findings: int
    exact_matches: int
    partial_matches: int


class JudgeAgent:
    """
    Impartial judge that scores Red Team vs Blue Team matches.
    
    Matching is done using:
    1. Resource name similarity
    2. Vulnerability type matching
    3. Attribute/evidence matching
    4. Optional LLM-based semantic matching
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        use_llm_matching: bool = False,
    ):
        """
        Initialize Judge Agent.
        
        Args:
            llm: Optional LLM for semantic matching
            use_llm_matching: Whether to use LLM for ambiguous matches
        """
        self.llm = llm
        self.use_llm_matching = use_llm_matching and llm is not None
        self.logger = logging.getLogger("JudgeAgent")

    def score(
        self,
        red_manifest: List[Dict[str, Any]],
        blue_findings: List[Dict[str, Any]],
    ) -> ScoringResult:
        """
        Score Blue Team findings against Red Team ground truth.
        
        Args:
            red_manifest: List of vulnerabilities injected by Red Team
            blue_findings: List of findings detected by Blue Team
            
        Returns:
            ScoringResult with all metrics
        """
        self.logger.info(
            f"Judging: {len(red_manifest)} red vulns vs {len(blue_findings)} blue findings"
        )
        
        matches: List[Match] = []
        matched_blue_ids = set()
        matched_red_ids = set()
        
        # Step 1: Find matches for each Red Team vulnerability
        for red_vuln in red_manifest:
            best_match = self._find_best_match(red_vuln, blue_findings, matched_blue_ids)
            matches.append(best_match)
            
            if best_match.blue_finding_id:
                matched_blue_ids.add(best_match.blue_finding_id)
                matched_red_ids.add(red_vuln.get("vuln_id", ""))
        
        # Step 2: Identify true positives, false positives, false negatives
        true_positives = []
        false_positives = []
        false_negatives = []
        exact_matches = 0
        partial_matches = 0
        
        for match in matches:
            if match.match_type == "exact":
                true_positives.append(match.blue_finding_id)
                exact_matches += 1
            elif match.match_type == "partial":
                true_positives.append(match.blue_finding_id)
                partial_matches += 1
            elif match.match_type == "missed":
                false_negatives.append(match.red_vuln_id)
        
        # Blue findings that didn't match any red vuln = false positives
        for finding in blue_findings:
            finding_id = finding.get("finding_id", "")
            if finding_id not in matched_blue_ids:
                false_positives.append(finding_id)
        
        # Step 3: Calculate metrics
        tp = len(true_positives)
        fp = len(false_positives)
        fn = len(false_negatives)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        
        evasion_rate = fn / len(red_manifest) if red_manifest else 0.0
        
        result = ScoringResult(
            matches=matches,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            evasion_rate=evasion_rate,
            total_red_vulns=len(red_manifest),
            total_blue_findings=len(blue_findings),
            exact_matches=exact_matches,
            partial_matches=partial_matches,
        )
        
        self.logger.info(
            f"Scoring complete: P={precision:.2f}, R={recall:.2f}, F1={f1_score:.2f}"
        )
        
        return result

    def _find_best_match(
        self,
        red_vuln: Dict[str, Any],
        blue_findings: List[Dict[str, Any]],
        already_matched: set,
    ) -> Match:
        """Find the best matching Blue Team finding for a Red Team vulnerability."""
        
        red_id = red_vuln.get("vuln_id", "unknown")
        red_resource = red_vuln.get("resource_name", "").lower()
        red_type = red_vuln.get("type", "").lower()
        red_attribute = red_vuln.get("vulnerable_attribute", "").lower()
        red_title = red_vuln.get("title", "").lower()
        
        best_score = 0.0
        best_finding = None
        best_type = "missed"
        
        for finding in blue_findings:
            finding_id = finding.get("finding_id", "")
            
            # Skip already matched findings
            if finding_id in already_matched:
                continue
            
            # Calculate match score
            score, match_type = self._calculate_match_score(
                red_vuln, finding
            )
            
            if score > best_score:
                best_score = score
                best_finding = finding
                best_type = match_type
        
        if best_finding and best_score >= 0.3:  # Minimum threshold
            return Match(
                red_vuln_id=red_id,
                blue_finding_id=best_finding.get("finding_id", ""),
                match_type=best_type,
                confidence=best_score,
                explanation=self._generate_explanation(red_vuln, best_finding, best_type),
            )
        else:
            return Match(
                red_vuln_id=red_id,
                blue_finding_id=None,
                match_type="missed",
                confidence=0.0,
                explanation=f"No matching finding for vulnerability: {red_vuln.get('title', red_id)}",
            )

    def _calculate_match_score(
        self,
        red_vuln: Dict[str, Any],
        blue_finding: Dict[str, Any],
    ) -> Tuple[float, str]:
        """
        Calculate match score between a vulnerability and a finding.
        
        Returns:
            Tuple of (score, match_type)
        """
        score = 0.0
        
        # Extract fields
        red_resource = red_vuln.get("resource_name", "").lower()
        blue_resource = blue_finding.get("resource_name", "").lower()
        
        red_type = red_vuln.get("type", "").lower()
        blue_type = blue_finding.get("vulnerability_type", "").lower()
        
        red_attribute = red_vuln.get("vulnerable_attribute", "").lower()
        blue_evidence = blue_finding.get("evidence", "").lower()
        blue_title = blue_finding.get("title", "").lower()
        blue_description = blue_finding.get("description", "").lower()
        
        red_title = red_vuln.get("title", "").lower()
        
        # Resource name matching (highest weight)
        if red_resource and blue_resource:
            if red_resource == blue_resource:
                score += 0.4
            elif self._resources_similar(red_resource, blue_resource):
                score += 0.25
        
        # Vulnerability type matching
        if red_type and blue_type:
            if red_type == blue_type:
                score += 0.2
            elif self._types_related(red_type, blue_type):
                score += 0.1
        
        # Attribute/evidence matching
        if red_attribute:
            if red_attribute in blue_evidence:
                score += 0.2
            elif red_attribute in blue_title or red_attribute in blue_description:
                score += 0.15
        
        # Title/description keyword matching
        red_keywords = set(red_title.split())
        blue_keywords = set(blue_title.split()) | set(blue_description.split())
        
        common_keywords = red_keywords & blue_keywords
        if len(common_keywords) >= 2:
            score += 0.1
        
        # Determine match type
        if score >= 0.7:
            match_type = "exact"
        elif score >= 0.4:
            match_type = "partial"
        else:
            match_type = "missed"
        
        return score, match_type

    def _resources_similar(self, res1: str, res2: str) -> bool:
        """Check if two resource names are similar."""
        # Extract resource type and name parts
        parts1 = res1.split(".")
        parts2 = res2.split(".")
        
        # Same resource type
        if len(parts1) >= 2 and len(parts2) >= 2:
            if parts1[0] == parts2[0]:  # Same provider/type
                return True
        
        # One contains the other
        if res1 in res2 or res2 in res1:
            return True
        
        return False

    def _types_related(self, type1: str, type2: str) -> bool:
        """Check if two vulnerability types are related."""
        related_types = {
            ("encryption", "data_protection"),
            ("access_control", "iam"),
            ("network", "access_control"),
            ("logging", "monitoring"),
        }
        
        pair = (type1, type2)
        reverse_pair = (type2, type1)
        
        return pair in related_types or reverse_pair in related_types

    def _generate_explanation(
        self,
        red_vuln: Dict[str, Any],
        blue_finding: Dict[str, Any],
        match_type: str,
    ) -> str:
        """Generate explanation for a match."""
        red_title = red_vuln.get("title", "Unknown vulnerability")
        blue_title = blue_finding.get("title", "Unknown finding")
        red_resource = red_vuln.get("resource_name", "unknown")
        blue_resource = blue_finding.get("resource_name", "unknown")
        
        if match_type == "exact":
            return (
                f"Exact match: Red Team's '{red_title}' on {red_resource} "
                f"was detected as '{blue_title}' on {blue_resource}"
            )
        elif match_type == "partial":
            return (
                f"Partial match: Red Team's '{red_title}' on {red_resource} "
                f"was partially detected as '{blue_title}' on {blue_resource}"
            )
        else:
            return f"Missed: Red Team's '{red_title}' on {red_resource} was not detected"

    def to_dict(self) -> Dict[str, Any]:
        """Return agent configuration as dictionary."""
        return {
            "agent_type": "JudgeAgent",
            "use_llm_matching": self.use_llm_matching,
        }


def score_results_to_dict(result: ScoringResult) -> Dict[str, Any]:
    """Convert ScoringResult to dictionary for JSON serialization."""
    return {
        "metrics": {
            "precision": result.precision,
            "recall": result.recall,
            "f1_score": result.f1_score,
            "evasion_rate": result.evasion_rate,
        },
        "counts": {
            "total_red_vulns": result.total_red_vulns,
            "total_blue_findings": result.total_blue_findings,
            "true_positives": len(result.true_positives),
            "false_positives": len(result.false_positives),
            "false_negatives": len(result.false_negatives),
            "exact_matches": result.exact_matches,
            "partial_matches": result.partial_matches,
        },
        "details": {
            "true_positive_ids": result.true_positives,
            "false_positive_ids": result.false_positives,
            "false_negative_ids": result.false_negatives,
        },
        "matches": [
            {
                "red_vuln_id": m.red_vuln_id,
                "blue_finding_id": m.blue_finding_id,
                "match_type": m.match_type,
                "confidence": m.confidence,
                "explanation": m.explanation,
            }
            for m in result.matches
        ],
    }
