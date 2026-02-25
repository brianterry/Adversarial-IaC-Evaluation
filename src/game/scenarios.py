"""
Scenario generation for adversarial IaC evaluation.

Scenarios define the test cases that Red Team and Blue Team compete on.
"""

import random
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..prompts import ScenarioTemplates


@dataclass
class Scenario:
    """A test scenario for adversarial evaluation"""
    
    id: str
    domain: str
    description: str
    cloud_provider: str
    language: str
    difficulty: str
    requirements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary"""
        return {
            "id": self.id,
            "domain": self.domain,
            "description": self.description,
            "cloud_provider": self.cloud_provider,
            "language": self.language,
            "difficulty": self.difficulty,
            "requirements": self.requirements,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        """Create scenario from dictionary"""
        return cls(
            id=data["id"],
            domain=data["domain"],
            description=data["description"],
            cloud_provider=data["cloud_provider"],
            language=data["language"],
            difficulty=data["difficulty"],
            requirements=data.get("requirements", []),
            metadata=data.get("metadata", {}),
        )


class ScenarioGenerator:
    """Generates test scenarios for adversarial evaluation"""
    
    def __init__(
        self,
        cloud_providers: List[str] = None,
        languages: List[str] = None,
        difficulty_levels: List[str] = None,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize scenario generator.
        
        Args:
            cloud_providers: List of cloud providers (aws, azure, gcp)
            languages: List of IaC languages (terraform, cloudformation)
            difficulty_levels: List of difficulties (easy, medium, hard)
            random_seed: Random seed for reproducibility
        """
        self.cloud_providers = cloud_providers or ["aws"]
        self.languages = languages or ["terraform"]
        self.difficulty_levels = difficulty_levels or ["easy", "medium", "hard"]
        
        if random_seed is not None:
            random.seed(random_seed)
    
    def generate_scenarios(
        self,
        domains: List[str] = None,
        scenarios_per_domain: int = 2,
    ) -> List[Scenario]:
        """
        Generate a set of test scenarios.
        
        Args:
            domains: List of domains (see ScenarioTemplates.SCENARIOS for all available)
            scenarios_per_domain: Number of scenarios per domain
            
        Returns:
            List of Scenario objects
        """
        if domains is None:
            # Use all available domains by default
            domains = list(ScenarioTemplates.SCENARIOS.keys())
        
        scenarios = []
        
        for domain in domains:
            domain_scenarios = ScenarioTemplates.SCENARIOS.get(domain, [])
            
            # Select scenarios for this domain
            selected = domain_scenarios[:scenarios_per_domain]
            
            for description in selected:
                # Generate combinations
                for provider in self.cloud_providers:
                    for language in self.languages:
                        for difficulty in self.difficulty_levels:
                            scenario = Scenario(
                                id=f"S-{uuid.uuid4().hex[:8]}",
                                domain=domain,
                                description=description,
                                cloud_provider=provider,
                                language=language,
                                difficulty=difficulty,
                                requirements=self._get_requirements(domain, provider),
                                metadata={
                                    "generator_version": "1.0.0",
                                },
                            )
                            scenarios.append(scenario)
        
        return scenarios
    
    def generate_single_scenario(
        self,
        description: str,
        domain: str = "storage",
        cloud_provider: str = "aws",
        language: str = "terraform",
        difficulty: str = "medium",
    ) -> Scenario:
        """
        Generate a single scenario with specified parameters.
        
        Args:
            description: Scenario description
            domain: Domain category
            cloud_provider: Cloud provider
            language: IaC language
            difficulty: Difficulty level
            
        Returns:
            Scenario object
        """
        return Scenario(
            id=f"S-{uuid.uuid4().hex[:8]}",
            domain=domain,
            description=description,
            cloud_provider=cloud_provider,
            language=language,
            difficulty=difficulty,
            requirements=self._get_requirements(domain, cloud_provider),
            metadata={
                "generator_version": "1.0.0",
                "custom": True,
            },
        )
    
    def _get_requirements(self, domain: str, cloud_provider: str) -> List[str]:
        """Get security requirements for a domain and provider."""
        base_requirements = {
            # Infrastructure domains
            "storage": [
                "Encryption at rest",
                "Access logging",
                "Versioning",
                "Public access controls",
            ],
            "compute": [
                "Instance metadata protection",
                "Security group configuration",
                "Key pair management",
                "IAM role attachment",
            ],
            "network": [
                "VPC configuration",
                "Subnet isolation",
                "Network ACLs",
                "Flow logs",
            ],
            "iam": [
                "Least privilege",
                "MFA enforcement",
                "Password policies",
                "Role boundaries",
            ],
            "multi_service": [
                "Cross-service encryption",
                "Service-to-service authentication",
                "Audit logging",
                "Network isolation",
            ],
            # AWS service domains
            "secrets": [
                "Secret rotation",
                "Access policies",
                "Encryption with KMS",
                "Audit logging",
            ],
            "containers": [
                "Pod security policies",
                "Image scanning",
                "Network policies",
                "Secrets management",
            ],
            "databases": [
                "Encryption at rest",
                "Encryption in transit",
                "Backup retention",
                "Public accessibility disabled",
            ],
            "api": [
                "Authentication",
                "Authorization",
                "Rate limiting",
                "Input validation",
            ],
            "messaging": [
                "Encryption in transit",
                "Dead-letter queues",
                "Access policies",
                "Message retention",
            ],
            "monitoring": [
                "Log retention",
                "Alert configuration",
                "Access controls",
                "Cross-account logging",
            ],
            # Industry verticals
            "healthcare": [
                "HIPAA compliance",
                "PHI encryption",
                "Audit trails",
                "Access controls",
                "Data retention policies",
            ],
            "financial": [
                "PCI-DSS compliance",
                "Data encryption",
                "Transaction logging",
                "Segregation of duties",
                "Key management",
            ],
            "government": [
                "FedRAMP compliance",
                "NIST 800-53 controls",
                "Data sovereignty",
                "Audit logging",
            ],
            "ecommerce": [
                "PCI compliance",
                "Customer data protection",
                "Session management",
                "Rate limiting",
            ],
            "saas": [
                "Tenant isolation",
                "Data segregation",
                "API security",
                "Multi-tenancy controls",
            ],
            # Security patterns
            "zero_trust": [
                "Continuous verification",
                "Microsegmentation",
                "Least privilege access",
                "Identity-based access",
            ],
            "disaster_recovery": [
                "Cross-region replication",
                "Backup encryption",
                "Recovery testing",
                "Failover automation",
            ],
        }
        
        provider_additions = {
            "aws": ["S3 bucket policies", "KMS key rotation"],
            "azure": ["Storage account firewall", "Key Vault integration"],
            "gcp": ["Cloud IAM bindings", "CMEK configuration"],
        }
        
        requirements = base_requirements.get(domain, ["Security best practices"])
        requirements.extend(provider_additions.get(cloud_provider, []))
        
        return requirements
    
    def get_scenario_matrix(self) -> List[Dict[str, Any]]:
        """
        Get the full scenario matrix as a summary.
        
        Returns:
            List of dictionaries describing the scenario space
        """
        domains = list(ScenarioTemplates.SCENARIOS.keys())
        total_base = sum(len(v) for v in ScenarioTemplates.SCENARIOS.values())
        
        return {
            "domains": domains,
            "cloud_providers": self.cloud_providers,
            "languages": self.languages,
            "difficulty_levels": self.difficulty_levels,
            "base_scenarios": total_base,
            "total_combinations": (
                total_base
                * len(self.cloud_providers)
                * len(self.languages)
                * len(self.difficulty_levels)
            ),
        }
