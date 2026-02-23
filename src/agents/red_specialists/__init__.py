"""
Red Team Pipeline Specialists

Sequential pipeline of specialized agents for adversarial IaC generation:
1. ArchitectAgent - Designs infrastructure structure
2. VulnerabilitySelectorAgent - Chooses vulnerabilities to inject
3. CodeGeneratorAgent - Generates the IaC code
4. StealthReviewerAgent - Refines code to evade detection

Part of the Adversarial IaC Evaluation framework.
"""

from .base import PipelineStage, PipelineOutput
from .architect_agent import ArchitectAgent
from .vulnerability_selector_agent import VulnerabilitySelectorAgent
from .code_generator_agent import CodeGeneratorAgent
from .stealth_reviewer_agent import StealthReviewerAgent

__all__ = [
    "PipelineStage",
    "PipelineOutput",
    "ArchitectAgent",
    "VulnerabilitySelectorAgent",
    "CodeGeneratorAgent",
    "StealthReviewerAgent",
]
