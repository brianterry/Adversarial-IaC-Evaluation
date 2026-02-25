"""
Judge Agent - Scores Red Team vs Blue Team matches

This agent:
1. Compares Blue Team findings against Red Team ground truth
2. Calculates precision, recall, and F1 scores
3. Identifies true positives, false positives, and false negatives
4. Provides detailed match explanations

Uses optimal bipartite matching (Hungarian algorithm) to find the best
global assignment between vulnerabilities and findings.

Supports multiple validation modes:
- Rule-based matching for clear cases
- LLM fallback for ambiguous matches (hybrid mode)
- Multi-model consensus for inter-rater reliability
- Tool triangulation for corroborated matches

Part of the Adversarial IaC Evaluation framework.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set

import numpy as np
from scipy.optimize import linear_sum_assignment

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.prompts import JudgeLLMPrompts


@dataclass
class Match:
    """A match between a Red Team vulnerability and Blue Team finding"""
    red_vuln_id: str
    blue_finding_id: Optional[str]
    match_type: str  # "exact", "partial", "missed", "corroborated"
    confidence: float
    explanation: str
    # New fields for reliability tracking
    corroborated_by_tool: bool = False  # Whether static tool also flagged this
    model_agreement: Optional[Dict[str, str]] = None  # Per-model verdicts if multi-model


@dataclass
class InterRaterReliability:
    """Inter-rater reliability metrics for multi-model consensus"""
    models_used: List[str]
    pairwise_kappa: Dict[str, float]  # e.g., {"gpt4_claude": 0.85, "claude_gemini": 0.78}
    mean_kappa: float
    kappa_range: Tuple[float, float]  # (min, max)
    total_judgments: int
    agreement_rate: float  # Simple % agreement across all models
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "models_used": self.models_used,
            "pairwise_kappa": self.pairwise_kappa,
            "mean_kappa": round(self.mean_kappa, 3),
            "kappa_range": [round(self.kappa_range[0], 3), round(self.kappa_range[1], 3)],
            "total_judgments": self.total_judgments,
            "agreement_rate": round(self.agreement_rate, 3),
        }


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
    
    # New: Corroboration metrics (tool triangulation)
    corroborated_matches: int = 0  # Matches confirmed by static tools
    corroboration_rate: float = 0.0  # % of matches that are corroborated
    
    # New: Inter-rater reliability (multi-model consensus)
    inter_rater_reliability: Optional[InterRaterReliability] = None


class JudgeAgent:
    """
    Impartial judge that scores Red Team vs Blue Team matches.
    
    Matching is done using:
    1. Resource name similarity
    2. Vulnerability type matching
    3. Attribute/evidence matching
    4. Optional LLM-based semantic matching
    5. Optional multi-model consensus for reliability
    6. Optional tool triangulation for corroboration
    """

    # Thresholds for hybrid matching
    CLEAR_MATCH_THRESHOLD = 0.7  # Above this = clear match, no LLM needed
    AMBIGUOUS_LOWER = 0.3  # Below this = clear miss
    AMBIGUOUS_UPPER = 0.7  # Between lower and upper = ambiguous, use LLM
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        use_llm_matching: bool = False,
        consensus_llms: Optional[List[Tuple[str, BaseChatModel]]] = None,
    ):
        """
        Initialize Judge Agent.
        
        Args:
            llm: Optional LLM for semantic matching (single model mode)
            use_llm_matching: Whether to use LLM for ambiguous matches
            consensus_llms: Optional list of (name, llm) tuples for multi-model consensus
        """
        self.llm = llm
        self.use_llm_matching = use_llm_matching and llm is not None
        self.consensus_llms = consensus_llms
        self.use_consensus = consensus_llms is not None and len(consensus_llms) >= 2
        self.logger = logging.getLogger("JudgeAgent")
        
        if self.use_consensus:
            model_names = [name for name, _ in consensus_llms]
            self.logger.info(f"Multi-model consensus enabled with: {model_names}")
        elif self.use_llm_matching:
            self.logger.info("LLM matching enabled for ambiguous cases")

    def score(
        self,
        red_manifest: List[Dict[str, Any]],
        blue_findings: List[Dict[str, Any]],
        tool_findings: Optional[List[Dict[str, Any]]] = None,
    ) -> ScoringResult:
        """
        Score Blue Team findings against Red Team ground truth.
        
        Uses optimal bipartite matching (Hungarian algorithm) to find the
        globally optimal assignment between vulnerabilities and findings.
        
        Args:
            red_manifest: List of vulnerabilities injected by Red Team
            blue_findings: List of findings detected by Blue Team
            tool_findings: Optional list of static tool findings for corroboration
            
        Returns:
            ScoringResult with all metrics
        """
        self.logger.info(
            f"Judging: {len(red_manifest)} red vulns vs {len(blue_findings)} blue findings"
        )
        
        # Build set of tool-flagged resources for corroboration
        tool_flagged_resources: Set[str] = set()
        if tool_findings:
            for tf in tool_findings:
                resource = tf.get("resource_name", "").lower()
                if resource:
                    tool_flagged_resources.add(resource)
                    base_name = resource.split(".")[-1] if "." in resource else resource
                    tool_flagged_resources.add(base_name)
        
        matches: List[Match] = []
        matched_blue_ids = set()
        matched_red_ids = set()
        
        # Collect all model judgments for consensus reliability calculation
        all_model_judgments: List[Dict[str, str]] = []
        
        # Step 1: Build cost matrix for optimal matching
        n_red = len(red_manifest)
        n_blue = len(blue_findings)
        
        if n_red == 0 or n_blue == 0:
            for red_vuln in red_manifest:
                matches.append(Match(
                    red_vuln_id=red_vuln.get("vuln_id", "unknown"),
                    blue_finding_id=None,
                    match_type="missed",
                    confidence=0.0,
                    explanation=f"No findings to match against: {red_vuln.get('title', '')}",
                ))
        else:
            score_matrix = np.zeros((n_red, n_blue))
            match_type_matrix = [[None] * n_blue for _ in range(n_red)]
            explanation_matrix = [[None] * n_blue for _ in range(n_red)]
            model_agreement_matrix = [[None] * n_blue for _ in range(n_red)]
            
            ambiguous_pairs = []
            
            for i, red_vuln in enumerate(red_manifest):
                for j, blue_finding in enumerate(blue_findings):
                    score, match_type = self._calculate_match_score(red_vuln, blue_finding)
                    score_matrix[i, j] = score
                    match_type_matrix[i][j] = match_type
                    explanation_matrix[i][j] = None
                    
                    if (self.use_llm_matching or self.use_consensus) and \
                       self.AMBIGUOUS_LOWER <= score < self.AMBIGUOUS_UPPER:
                        ambiguous_pairs.append((i, j, red_vuln, blue_finding))
            
            # Multi-model consensus for ambiguous matches
            if self.use_consensus and ambiguous_pairs:
                self.logger.info(f"Using multi-model consensus for {len(ambiguous_pairs)} ambiguous pairs")
                for i, j, red_vuln, blue_finding in ambiguous_pairs:
                    consensus_result = self._evaluate_with_consensus(red_vuln, blue_finding)
                    
                    score_matrix[i, j] = consensus_result["score"]
                    match_type_matrix[i][j] = consensus_result["match_type"]
                    explanation_matrix[i][j] = consensus_result["explanation"]
                    model_agreement_matrix[i][j] = consensus_result["model_verdicts"]
                    
                    all_model_judgments.append(consensus_result["model_verdicts"])
            
            elif self.use_llm_matching and ambiguous_pairs:
                self.logger.info(f"Using LLM to evaluate {len(ambiguous_pairs)} ambiguous pairs")
                for i, j, red_vuln, blue_finding in ambiguous_pairs:
                    llm_score, llm_type, llm_explanation = self._evaluate_with_llm(red_vuln, blue_finding)
                    score_matrix[i, j] = llm_score
                    match_type_matrix[i][j] = llm_type
                    explanation_matrix[i][j] = llm_explanation
            
            cost_matrix = -score_matrix
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            
            assigned_reds = set()
            assigned_blues = set()
            
            for i, j in zip(row_ind, col_ind):
                red_vuln = red_manifest[i]
                blue_finding = blue_findings[j]
                score = score_matrix[i, j]
                match_type = match_type_matrix[i][j]
                
                red_id = red_vuln.get("vuln_id", "unknown")
                blue_id = blue_finding.get("finding_id", "")
                
                explanation = explanation_matrix[i][j]
                if explanation is None:
                    explanation = self._generate_explanation(red_vuln, blue_finding, match_type)
                
                # Check tool corroboration
                red_resource = red_vuln.get("resource_name", "").lower()
                blue_resource = blue_finding.get("resource_name", "").lower()
                red_base = red_resource.split(".")[-1] if "." in red_resource else red_resource
                blue_base = blue_resource.split(".")[-1] if "." in blue_resource else blue_resource
                
                corroborated = bool(tool_findings) and (
                    red_resource in tool_flagged_resources or
                    red_base in tool_flagged_resources or
                    blue_resource in tool_flagged_resources or
                    blue_base in tool_flagged_resources
                )
                
                if corroborated and score >= 0.3:
                    if match_type in ["exact", "partial"]:
                        match_type = "corroborated"
                        explanation = f"[TOOL CORROBORATED] {explanation}"
                
                if score >= 0.3:
                    matches.append(Match(
                        red_vuln_id=red_id,
                        blue_finding_id=blue_id,
                        match_type=match_type,
                        confidence=score,
                        explanation=explanation,
                        corroborated_by_tool=corroborated,
                        model_agreement=model_agreement_matrix[i][j],
                    ))
                    matched_blue_ids.add(blue_id)
                    matched_red_ids.add(red_id)
                    assigned_reds.add(i)
                    assigned_blues.add(j)
                else:
                    matches.append(Match(
                        red_vuln_id=red_id,
                        blue_finding_id=None,
                        match_type="missed",
                        confidence=0.0,
                        explanation=f"No matching finding for vulnerability: {red_vuln.get('title', red_id)}",
                    ))
                    assigned_reds.add(i)
            
            for i, red_vuln in enumerate(red_manifest):
                if i not in assigned_reds:
                    matches.append(Match(
                        red_vuln_id=red_vuln.get("vuln_id", "unknown"),
                        blue_finding_id=None,
                        match_type="missed",
                        confidence=0.0,
                        explanation=f"No matching finding for vulnerability: {red_vuln.get('title', '')}",
                    ))
        
        # Step 2: Identify true positives, false positives, false negatives
        true_positives = []
        false_positives = []
        false_negatives = []
        exact_matches = 0
        partial_matches = 0
        corroborated_matches = 0
        
        for match in matches:
            if match.match_type == "exact":
                true_positives.append(match.blue_finding_id)
                exact_matches += 1
            elif match.match_type == "partial":
                true_positives.append(match.blue_finding_id)
                partial_matches += 1
            elif match.match_type == "corroborated":
                true_positives.append(match.blue_finding_id)
                corroborated_matches += 1
            elif match.match_type == "missed":
                false_negatives.append(match.red_vuln_id)
        
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
        
        total_valid_matches = exact_matches + partial_matches + corroborated_matches
        corroboration_rate = corroborated_matches / total_valid_matches if total_valid_matches > 0 else 0.0
        
        # Step 4: Calculate inter-rater reliability if using consensus
        inter_rater = None
        if self.use_consensus and all_model_judgments:
            inter_rater = self._calculate_inter_rater_reliability(all_model_judgments)
        
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
            corroborated_matches=corroborated_matches,
            corroboration_rate=corroboration_rate,
            inter_rater_reliability=inter_rater,
        )
        
        self.logger.info(
            f"Scoring complete: P={precision:.2f}, R={recall:.2f}, F1={f1_score:.2f}"
        )
        if corroborated_matches > 0:
            self.logger.info(f"Corroborated matches: {corroborated_matches} ({corroboration_rate:.1%})")
        if inter_rater:
            self.logger.info(f"Inter-rater kappa: {inter_rater.mean_kappa:.3f} (range: {inter_rater.kappa_range})")
        
        return result

    def _evaluate_with_consensus(
        self,
        red_vuln: Dict[str, Any],
        blue_finding: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use multiple LLMs to evaluate a match and return consensus."""
        model_verdicts: Dict[str, str] = {}
        model_confidences: Dict[str, float] = {}
        model_explanations: Dict[str, str] = {}
        
        for model_name, llm in self.consensus_llms:
            try:
                score, match_type, explanation = self._evaluate_with_specific_llm(
                    llm, red_vuln, blue_finding
                )
                model_verdicts[model_name] = match_type
                model_confidences[model_name] = score
                model_explanations[model_name] = explanation
            except Exception as e:
                self.logger.warning(f"Model {model_name} failed: {e}")
                model_verdicts[model_name] = "error"
                model_confidences[model_name] = 0.0
        
        valid_verdicts = [v for v in model_verdicts.values() if v != "error"]
        if not valid_verdicts:
            return {
                "score": 0.0,
                "match_type": "missed",
                "explanation": "All models failed",
                "model_verdicts": model_verdicts,
            }
        
        votes = {}
        for verdict in valid_verdicts:
            votes[verdict] = votes.get(verdict, 0) + 1
        
        consensus_type = max(votes.keys(), key=lambda k: votes[k])
        agreement_count = votes[consensus_type]
        
        relevant_confidences = [
            model_confidences[m] for m, v in model_verdicts.items() 
            if v == consensus_type
        ]
        avg_confidence = sum(relevant_confidences) / len(relevant_confidences) if relevant_confidences else 0.0
        
        if consensus_type == "exact":
            final_score = max(0.8, avg_confidence)
        elif consensus_type == "partial":
            final_score = max(0.5, min(0.79, avg_confidence))
        else:
            final_score = min(0.29, avg_confidence)
        
        explanation = (
            f"Multi-model consensus ({agreement_count}/{len(valid_verdicts)} agree): {consensus_type}. "
            f"Models: {model_verdicts}"
        )
        
        return {
            "score": final_score,
            "match_type": consensus_type,
            "explanation": explanation,
            "model_verdicts": model_verdicts,
        }

    def _calculate_inter_rater_reliability(
        self,
        all_judgments: List[Dict[str, str]],
    ) -> InterRaterReliability:
        """Calculate Cohen's kappa for all model pairs."""
        if not self.consensus_llms or len(all_judgments) == 0:
            return None
        
        model_names = [name for name, _ in self.consensus_llms]
        
        model_verdicts: Dict[str, List[str]] = {name: [] for name in model_names}
        for judgment in all_judgments:
            for name in model_names:
                verdict = judgment.get(name, "error")
                model_verdicts[name].append(verdict)
        
        pairwise_kappa = {}
        kappa_values = []
        
        for i, name1 in enumerate(model_names):
            for name2 in model_names[i+1:]:
                verdicts1 = model_verdicts[name1]
                verdicts2 = model_verdicts[name2]
                
                valid_pairs = [
                    (v1, v2) for v1, v2 in zip(verdicts1, verdicts2)
                    if v1 != "error" and v2 != "error"
                ]
                
                if len(valid_pairs) >= 2:
                    kappa = self._cohens_kappa(
                        [p[0] for p in valid_pairs],
                        [p[1] for p in valid_pairs]
                    )
                    pair_key = f"{name1}_vs_{name2}"
                    pairwise_kappa[pair_key] = round(kappa, 3)
                    kappa_values.append(kappa)
        
        total_agreements = 0
        total_comparisons = 0
        for judgment in all_judgments:
            valid_verdicts = [v for v in judgment.values() if v != "error"]
            if len(valid_verdicts) >= 2:
                if len(set(valid_verdicts)) == 1:
                    total_agreements += 1
                total_comparisons += 1
        
        agreement_rate = total_agreements / total_comparisons if total_comparisons > 0 else 0.0
        mean_kappa = sum(kappa_values) / len(kappa_values) if kappa_values else 0.0
        kappa_range = (min(kappa_values), max(kappa_values)) if kappa_values else (0.0, 0.0)
        
        return InterRaterReliability(
            models_used=model_names,
            pairwise_kappa=pairwise_kappa,
            mean_kappa=mean_kappa,
            kappa_range=kappa_range,
            total_judgments=len(all_judgments),
            agreement_rate=agreement_rate,
        )

    def _cohens_kappa(self, rater1: List[str], rater2: List[str]) -> float:
        """Calculate Cohen's kappa for two raters."""
        if len(rater1) != len(rater2) or len(rater1) == 0:
            return 0.0
        
        n = len(rater1)
        categories = list(set(rater1) | set(rater2))
        
        agreements = sum(1 for r1, r2 in zip(rater1, rater2) if r1 == r2)
        p_o = agreements / n
        
        p_e = 0.0
        for cat in categories:
            p1 = sum(1 for r in rater1 if r == cat) / n
            p2 = sum(1 for r in rater2 if r == cat) / n
            p_e += p1 * p2
        
        if p_e == 1.0:
            return 1.0 if p_o == 1.0 else 0.0
        
        kappa = (p_o - p_e) / (1 - p_e)
        return kappa

    def _calculate_match_score(
        self,
        red_vuln: Dict[str, Any],
        blue_finding: Dict[str, Any],
    ) -> Tuple[float, str]:
        """Calculate match score between a vulnerability and a finding."""
        score = 0.0
        
        red_resource = red_vuln.get("resource_name", "").lower()
        blue_resource = blue_finding.get("resource_name", "").lower()
        
        red_type = red_vuln.get("type", "").lower()
        blue_type = blue_finding.get("vulnerability_type", "").lower()
        
        red_attribute = red_vuln.get("vulnerable_attribute", "").lower()
        blue_evidence = blue_finding.get("evidence", "").lower()
        blue_title = blue_finding.get("title", "").lower()
        blue_description = blue_finding.get("description", "").lower()
        
        red_title = red_vuln.get("title", "").lower()
        
        if red_resource and blue_resource:
            if red_resource == blue_resource:
                score += 0.4
            elif self._resources_similar(red_resource, blue_resource):
                score += 0.25
        
        security_keywords = [
            "encrypt", "access", "public", "permiss", "log", "iam",
            "rotation", "secret", "credential", "key", "password", "token",
            "exposed", "unencrypt", "wildcard", "unrestrict", "sensitive"
        ]
        if red_type == "unknown" or red_type == "":
            if any(kw in blue_title or kw in blue_description for kw in security_keywords):
                score += 0.1
        elif red_type and blue_type:
            if red_type == blue_type:
                score += 0.2
            elif self._types_related(red_type, blue_type):
                score += 0.1
        
        if red_attribute:
            red_attr_normalized = red_attribute.replace("_", " ").replace("-", " ")
            blue_evidence_normalized = blue_evidence.replace("_", " ").replace("-", " ")
            blue_title_normalized = blue_title.replace("_", " ").replace("-", " ")
            blue_desc_normalized = blue_description.replace("_", " ").replace("-", " ")
            
            if red_attr_normalized in blue_evidence_normalized or red_attribute in blue_evidence:
                score += 0.2
            elif red_attr_normalized in blue_title_normalized or red_attr_normalized in blue_desc_normalized:
                score += 0.15
            elif red_attribute in blue_title or red_attribute in blue_description:
                score += 0.15
        
        red_keywords = set(red_title.split())
        blue_keywords = set(blue_title.split()) | set(blue_description.split())
        
        common_keywords = red_keywords & blue_keywords
        if len(common_keywords) >= 2:
            score += 0.1
        
        if score >= 0.7:
            match_type = "exact"
        elif score >= 0.4:
            match_type = "partial"
        else:
            match_type = "missed"
        
        return score, match_type

    def _resources_similar(self, res1: str, res2: str) -> bool:
        """Check if two resource names are similar."""
        parts1 = res1.split(".")
        parts2 = res2.split(".")
        
        if len(parts1) >= 2 and len(parts2) >= 2:
            if parts1[0] == parts2[0]:
                return True
        
        if res1 in res2 or res2 in res1:
            return True
        
        base1 = parts1[-1] if parts1 else res1
        base2 = parts2[-1] if parts2 else res2
        
        if base1 == base2:
            return True
        if base1 in base2 or base2 in base1:
            return True
        
        common_prefix = self._common_prefix(base1, base2)
        if len(common_prefix) >= 3:
            return True
        
        return False

    def _common_prefix(self, s1: str, s2: str) -> str:
        """Find common prefix between two strings."""
        prefix = ""
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                prefix += c1
            else:
                break
        return prefix

    def _types_related(self, type1: str, type2: str) -> bool:
        """Check if two vulnerability types are related."""
        related_types = {
            ("encryption", "data_protection"),
            ("access_control", "iam"),
            ("network", "access_control"),
            ("logging", "monitoring"),
            ("data_protection", "iam"),
            ("data_protection", "access_control"),
            ("encryption", "access_control"),
            ("unknown", "data_protection"),
            ("unknown", "encryption"),
            ("unknown", "access_control"),
            ("unknown", "iam"),
            ("unknown", "network"),
            ("unknown", "logging"),
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
        elif match_type == "corroborated":
            return (
                f"Corroborated match: Red Team's '{red_title}' on {red_resource} "
                f"was detected as '{blue_title}' on {blue_resource} (confirmed by static tools)"
            )
        else:
            return f"Missed: Red Team's '{red_title}' on {red_resource} was not detected"

    def _evaluate_with_llm(
        self,
        red_vuln: Dict[str, Any],
        blue_finding: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        """Use LLM to evaluate if a vulnerability and finding match."""
        return self._evaluate_with_specific_llm(self.llm, red_vuln, blue_finding)

    def _evaluate_with_specific_llm(
        self,
        llm: BaseChatModel,
        red_vuln: Dict[str, Any],
        blue_finding: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        """Use a specific LLM to evaluate if a vulnerability and finding match."""
        if not llm:
            return 0.0, "missed", "LLM not available"
        
        prompt = JudgeLLMPrompts.SINGLE_PAIR_MATCH.format(
            red_id=red_vuln.get("vuln_id", "unknown"),
            red_title=red_vuln.get("title", ""),
            red_resource=red_vuln.get("resource_name", ""),
            red_resource_type=red_vuln.get("resource_type", ""),
            red_type=red_vuln.get("type", "unknown"),
            red_attribute=red_vuln.get("vulnerable_attribute", ""),
            red_description=red_vuln.get("title", ""),
            blue_id=blue_finding.get("finding_id", ""),
            blue_title=blue_finding.get("title", ""),
            blue_resource=blue_finding.get("resource_name", ""),
            blue_resource_type=blue_finding.get("resource_type", ""),
            blue_type=blue_finding.get("vulnerability_type", ""),
            blue_evidence=blue_finding.get("evidence", ""),
            blue_description=blue_finding.get("description", ""),
        )
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            result = self._parse_llm_response(response_text)
            
            match_type = result.get("match_type", "none").lower()
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            if match_type == "exact":
                score = max(0.8, confidence)
                final_type = "exact"
            elif match_type == "partial":
                score = max(0.5, min(0.79, confidence))
                final_type = "partial"
            else:
                score = min(0.29, confidence)
                final_type = "missed"
            
            self.logger.debug(
                f"LLM evaluation: {red_vuln.get('vuln_id')} vs {blue_finding.get('finding_id')} "
                f"-> {final_type} (confidence={confidence:.2f})"
            )
            
            explanation = f"LLM verified: {reasoning}" if reasoning else f"LLM match: {final_type}"
            return score, final_type, explanation
            
        except Exception as e:
            self.logger.warning(f"LLM evaluation failed: {e}")
            return 0.0, "missed", f"LLM evaluation failed: {str(e)}"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling various formats."""
        response = response.strip()
        
        if response.startswith("```"):
            lines = response.split("\n")
            start = 1 if lines[0].startswith("```") else 0
            end = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            response = "\n".join(lines[start:end])
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return {"match_type": "none", "confidence": 0.0, "reasoning": "Failed to parse LLM response"}

    def to_dict(self) -> Dict[str, Any]:
        """Return agent configuration as dictionary."""
        config = {
            "agent_type": "JudgeAgent",
            "use_llm_matching": self.use_llm_matching,
            "use_consensus": self.use_consensus,
        }
        if self.use_consensus:
            config["consensus_models"] = [name for name, _ in self.consensus_llms]
        return config


def score_results_to_dict(result: ScoringResult) -> Dict[str, Any]:
    """Convert ScoringResult to dictionary for JSON serialization."""
    output = {
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
            "corroborated_matches": result.corroborated_matches,
        },
        "corroboration": {
            "corroborated_matches": result.corroborated_matches,
            "corroboration_rate": result.corroboration_rate,
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
                "corroborated_by_tool": m.corroborated_by_tool,
                "model_agreement": m.model_agreement,
            }
            for m in result.matches
        ],
    }
    
    if result.inter_rater_reliability:
        output["inter_rater_reliability"] = result.inter_rater_reliability.to_dict()
    
    return output
