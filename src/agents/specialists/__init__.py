"""
Blue Team Specialist Agents for Ensemble Detection

This module provides specialized agents that work together to detect
vulnerabilities in Infrastructure-as-Code:

- SecurityExpert: Finds security vulnerabilities (access, encryption, network)
- ComplianceAgent: Checks regulatory compliance (HIPAA, PCI-DSS, SOC2)  
- ArchitectureAgent: Evaluates cloud best practices and patterns
- ConsensusAgent: Synthesizes findings from all specialists

Part of the Adversarial IaC Evaluation framework.
"""

from .base import BaseSpecialist, SpecialistFinding, SpecialistOutput
from .security_expert import SecurityExpert
from .compliance_agent import ComplianceAgent
from .architecture_agent import ArchitectureAgent
from .consensus_agent import ConsensusAgent

__all__ = [
    "BaseSpecialist",
    "SpecialistFinding",
    "SpecialistOutput",
    "SecurityExpert",
    "ComplianceAgent", 
    "ArchitectureAgent",
    "ConsensusAgent",
]
