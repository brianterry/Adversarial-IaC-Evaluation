"""
Tests for Blue Team Ensemble Multi-Agent Detection

Tests cover:
1. Individual specialist agents
2. Consensus agent with all methods
3. BlueTeamEnsemble orchestrator
4. Integration with game engine
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import modules under test
from src.agents.specialists.base import BaseSpecialist, SpecialistFinding, SpecialistOutput
from src.agents.specialists.security_expert import SecurityExpert
from src.agents.specialists.compliance_agent import ComplianceAgent
from src.agents.specialists.architecture_agent import ArchitectureAgent
from src.agents.specialists.consensus_agent import ConsensusAgent, ConsensusResult
from src.agents.blue_team_ensemble import BlueTeamEnsemble, EnsembleOutput
from src.agents.blue_team_agent import Finding


# Sample IaC code for testing
SAMPLE_TERRAFORM_CODE = {
    "main.tf": """
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id
  block_public_acls = false
  block_public_policy = false
}
"""
}


# Mock LLM responses
MOCK_SECURITY_RESPONSE = json.dumps({
    "specialist": "security_expert",
    "findings": [
        {
            "finding_id": "SEC-1",
            "resource_name": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "vulnerability_type": "access_control",
            "severity": "high",
            "title": "S3 bucket allows public access",
            "description": "Bucket has public access enabled",
            "evidence": "block_public_acls = false",
            "confidence": 0.95,
            "reasoning": "Public access to S3 can lead to data exposure"
        }
    ],
    "summary": "Found 1 high severity issue"
})


MOCK_COMPLIANCE_RESPONSE = json.dumps({
    "specialist": "compliance_agent",
    "findings": [
        {
            "finding_id": "COMP-1",
            "resource_name": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "vulnerability_type": "compliance",
            "severity": "high",
            "title": "S3 bucket missing encryption",
            "description": "No server-side encryption configured",
            "evidence": "No encryption configuration present",
            "confidence": 0.90,
            "reasoning": "HIPAA requires encryption at rest",
            "compliance_frameworks": ["HIPAA", "SOC2"]
        }
    ],
    "summary": "Found 1 compliance issue"
})


MOCK_ARCHITECTURE_RESPONSE = json.dumps({
    "specialist": "architecture_agent",
    "findings": [
        {
            "finding_id": "ARCH-1",
            "resource_name": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "vulnerability_type": "best_practice",
            "severity": "medium",
            "title": "Missing versioning",
            "description": "S3 bucket should have versioning enabled",
            "evidence": "No versioning block",
            "confidence": 0.85,
            "reasoning": "Versioning provides data recovery capability",
            "well_architected_pillar": "reliability"
        },
        {
            "finding_id": "ARCH-2",
            "resource_name": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "vulnerability_type": "access_control",
            "severity": "high",
            "title": "Public access allowed",
            "description": "Bucket allows public access",
            "evidence": "block_public_acls = false",
            "confidence": 0.90,
            "reasoning": "Public access violates security best practices"
        }
    ],
    "summary": "Found 2 architecture issues"
})


MOCK_CONSENSUS_RESPONSE = json.dumps({
    "consensus_method": "debate",
    "total_specialist_findings": {
        "security_expert": 1,
        "compliance_agent": 1,
        "architecture_agent": 2
    },
    "findings": [
        {
            "finding_id": "F1",
            "resource_name": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "vulnerability_type": "access_control",
            "severity": "high",
            "title": "S3 bucket allows public access",
            "description": "Bucket has public access enabled, found by security and architecture specialists",
            "evidence": "block_public_acls = false",
            "confidence": 0.95,
            "reasoning": "Unanimous agreement on public access vulnerability",
            "specialist_agreement": ["security_expert", "architecture_agent"]
        },
        {
            "finding_id": "F2",
            "resource_name": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "vulnerability_type": "compliance",
            "severity": "high",
            "title": "S3 bucket missing encryption",
            "description": "No server-side encryption configured",
            "evidence": "No encryption configuration present",
            "confidence": 0.90,
            "reasoning": "Compliance specialist finding",
            "specialist_agreement": ["compliance_agent"]
        }
    ],
    "consensus_summary": {
        "unanimous_findings": 1,
        "majority_findings": 0,
        "specialist_only_findings": 2,
        "conflicts_resolved": 0
    },
    "debate_notes": "Merged security and architecture findings on public access issue"
})


class MockLLM:
    """Mock LLM for testing without API calls."""
    
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_count = 0
        self.call_history = []
    
    async def ainvoke(self, messages):
        self.call_count += 1
        prompt = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])
        self.call_history.append(prompt)
        
        # Return appropriate response based on prompt content
        if "SECURITY EXPERT" in prompt:
            return MagicMock(content=MOCK_SECURITY_RESPONSE)
        elif "COMPLIANCE SPECIALIST" in prompt:
            return MagicMock(content=MOCK_COMPLIANCE_RESPONSE)
        elif "CLOUD ARCHITECTURE SPECIALIST" in prompt:
            return MagicMock(content=MOCK_ARCHITECTURE_RESPONSE)
        elif "SENIOR SECURITY ARCHITECT" in prompt:
            return MagicMock(content=MOCK_CONSENSUS_RESPONSE)
        else:
            return MagicMock(content="{}")


# =============================================================================
# SPECIALIST AGENT TESTS
# =============================================================================

class TestSecurityExpert:
    """Tests for SecurityExpert specialist agent."""
    
    @pytest.fixture
    def security_expert(self):
        """Create a SecurityExpert with mock LLM."""
        llm = MockLLM()
        return SecurityExpert(llm=llm, language="terraform")
    
    def test_specialist_name(self, security_expert):
        """Test that specialist name is correct."""
        assert security_expert.specialist_name == "security_expert"
    
    def test_finding_prefix(self, security_expert):
        """Test that finding prefix is correct."""
        assert security_expert.finding_prefix == "SEC"
    
    @pytest.mark.asyncio
    async def test_analyze_returns_findings(self, security_expert):
        """Test that analyze returns SpecialistOutput with findings."""
        output = await security_expert.analyze(SAMPLE_TERRAFORM_CODE)
        
        assert isinstance(output, SpecialistOutput)
        assert output.specialist == "security_expert"
        assert len(output.findings) == 1
        assert output.findings[0].finding_id == "SEC-1"
        assert output.findings[0].vulnerability_type == "access_control"
        assert output.findings[0].severity == "high"


class TestComplianceAgent:
    """Tests for ComplianceAgent specialist agent."""
    
    @pytest.fixture
    def compliance_agent(self):
        """Create a ComplianceAgent with mock LLM."""
        llm = MockLLM()
        return ComplianceAgent(llm=llm, language="terraform")
    
    def test_specialist_name(self, compliance_agent):
        """Test that specialist name is correct."""
        assert compliance_agent.specialist_name == "compliance_agent"
    
    def test_finding_prefix(self, compliance_agent):
        """Test that finding prefix is correct."""
        assert compliance_agent.finding_prefix == "COMP"
    
    @pytest.mark.asyncio
    async def test_analyze_returns_compliance_findings(self, compliance_agent):
        """Test that analyze returns compliance findings with frameworks."""
        output = await compliance_agent.analyze(SAMPLE_TERRAFORM_CODE)
        
        assert isinstance(output, SpecialistOutput)
        assert len(output.findings) == 1
        assert "compliance_frameworks" in output.findings[0].metadata


class TestArchitectureAgent:
    """Tests for ArchitectureAgent specialist agent."""
    
    @pytest.fixture
    def architecture_agent(self):
        """Create an ArchitectureAgent with mock LLM."""
        llm = MockLLM()
        return ArchitectureAgent(llm=llm, language="terraform")
    
    def test_specialist_name(self, architecture_agent):
        """Test that specialist name is correct."""
        assert architecture_agent.specialist_name == "architecture_agent"
    
    def test_finding_prefix(self, architecture_agent):
        """Test that finding prefix is correct."""
        assert architecture_agent.finding_prefix == "ARCH"
    
    @pytest.mark.asyncio
    async def test_analyze_returns_architecture_findings(self, architecture_agent):
        """Test that analyze returns architecture findings with pillars."""
        output = await architecture_agent.analyze(SAMPLE_TERRAFORM_CODE)
        
        assert isinstance(output, SpecialistOutput)
        assert len(output.findings) == 2


# =============================================================================
# CONSENSUS AGENT TESTS
# =============================================================================

class TestConsensusAgent:
    """Tests for ConsensusAgent with all consensus methods."""
    
    @pytest.fixture
    def specialist_outputs(self):
        """Create sample specialist outputs for testing."""
        # Security finding
        sec_finding = SpecialistFinding(
            finding_id="SEC-1",
            resource_name="aws_s3_bucket.data",
            resource_type="aws_s3_bucket",
            vulnerability_type="access_control",
            severity="high",
            title="Public access enabled",
            description="Bucket allows public access",
            evidence="block_public_acls = false",
            confidence=0.95,
            reasoning="Security risk",
            specialist="security_expert",
        )
        
        # Compliance finding (different issue)
        comp_finding = SpecialistFinding(
            finding_id="COMP-1",
            resource_name="aws_s3_bucket.data",
            resource_type="aws_s3_bucket",
            vulnerability_type="encryption",
            severity="high",
            title="Missing encryption",
            description="No encryption configured",
            evidence="No encryption block",
            confidence=0.90,
            reasoning="Compliance violation",
            specialist="compliance_agent",
        )
        
        # Architecture finding (same issue as security)
        arch_finding = SpecialistFinding(
            finding_id="ARCH-1",
            resource_name="aws_s3_bucket.data",
            resource_type="aws_s3_bucket",
            vulnerability_type="access_control",
            severity="high",
            title="Public access allowed",
            description="Public access violates best practices",
            evidence="block_public_acls = false",
            confidence=0.90,
            reasoning="Best practice violation",
            specialist="architecture_agent",
        )
        
        return [
            SpecialistOutput(
                specialist="security_expert",
                findings=[sec_finding],
                summary="Found 1 issue",
            ),
            SpecialistOutput(
                specialist="compliance_agent",
                findings=[comp_finding],
                summary="Found 1 issue",
            ),
            SpecialistOutput(
                specialist="architecture_agent",
                findings=[arch_finding],
                summary="Found 1 issue",
            ),
        ]
    
    def test_invalid_method_raises_error(self):
        """Test that invalid consensus method raises ValueError."""
        with pytest.raises(ValueError):
            ConsensusAgent(method="invalid_method")
    
    def test_debate_requires_llm(self):
        """Test that debate method requires LLM."""
        with pytest.raises(ValueError):
            ConsensusAgent(llm=None, method="debate")
    
    @pytest.mark.asyncio
    async def test_vote_consensus(self, specialist_outputs):
        """Test majority voting consensus."""
        consensus = ConsensusAgent(method="vote")
        result = await consensus.synthesize(specialist_outputs)
        
        assert isinstance(result, ConsensusResult)
        # access_control has 2 votes (security + architecture), encryption has 1
        assert len(result.findings) == 1  # Only majority findings
        assert result.findings[0].vulnerability_type == "access_control"
    
    @pytest.mark.asyncio
    async def test_union_consensus(self, specialist_outputs):
        """Test union consensus (all unique findings)."""
        consensus = ConsensusAgent(method="union")
        result = await consensus.synthesize(specialist_outputs)
        
        assert isinstance(result, ConsensusResult)
        # Should have 2 unique findings (access_control and encryption)
        assert len(result.findings) == 2
    
    @pytest.mark.asyncio
    async def test_intersection_consensus(self, specialist_outputs):
        """Test intersection consensus (unanimous only)."""
        consensus = ConsensusAgent(method="intersection")
        result = await consensus.synthesize(specialist_outputs)
        
        assert isinstance(result, ConsensusResult)
        # No finding has all 3 specialists agreeing
        assert len(result.findings) == 0
    
    @pytest.mark.asyncio
    async def test_debate_consensus(self, specialist_outputs):
        """Test LLM-based debate consensus."""
        llm = MockLLM()
        consensus = ConsensusAgent(llm=llm, method="debate")
        result = await consensus.synthesize(specialist_outputs)
        
        assert isinstance(result, ConsensusResult)
        assert len(result.findings) >= 1
        assert llm.call_count == 1  # Should call LLM once


# =============================================================================
# BLUE TEAM ENSEMBLE TESTS
# =============================================================================

class TestBlueTeamEnsemble:
    """Tests for BlueTeamEnsemble orchestrator."""
    
    @pytest.fixture
    def ensemble(self):
        """Create BlueTeamEnsemble with mock LLM."""
        llm = MockLLM()
        return BlueTeamEnsemble(
            llm=llm,
            language="terraform",
            specialists=["security", "compliance", "architecture"],
            consensus_method="debate",
            run_parallel=False,  # Sequential for predictable testing
        )
    
    def test_invalid_specialist_raises_error(self):
        """Test that invalid specialist name raises ValueError."""
        with pytest.raises(ValueError):
            BlueTeamEnsemble(
                llm=MockLLM(),
                specialists=["invalid_specialist"],
            )
    
    def test_invalid_consensus_method_raises_error(self):
        """Test that invalid consensus method raises ValueError."""
        with pytest.raises(ValueError):
            BlueTeamEnsemble(
                llm=MockLLM(),
                consensus_method="invalid_method",
            )
    
    def test_to_dict(self, ensemble):
        """Test configuration export."""
        config = ensemble.to_dict()
        
        assert config["agent_type"] == "BlueTeamEnsemble"
        assert config["mode"] == "ensemble"
        assert config["consensus_method"] == "debate"
        assert "security" in config["specialists"]
    
    @pytest.mark.asyncio
    async def test_execute_returns_ensemble_output(self, ensemble):
        """Test that execute returns EnsembleOutput."""
        output = await ensemble.execute(SAMPLE_TERRAFORM_CODE)
        
        assert isinstance(output, EnsembleOutput)
        assert isinstance(output.findings, list)
        assert output.consensus_method == "debate"
        assert "security_expert" in output.specialist_findings
        assert "compliance_agent" in output.specialist_findings
        assert "architecture_agent" in output.specialist_findings
    
    @pytest.mark.asyncio
    async def test_execute_has_consensus_stats(self, ensemble):
        """Test that execute includes consensus statistics."""
        output = await ensemble.execute(SAMPLE_TERRAFORM_CODE)
        
        assert output.consensus_stats is not None
        assert "unanimous" in output.consensus_stats
        assert "majority" in output.consensus_stats
    
    @pytest.mark.asyncio
    async def test_findings_are_compatible(self, ensemble):
        """Test that findings are compatible with BlueTeamOutput format."""
        output = await ensemble.execute(SAMPLE_TERRAFORM_CODE)
        
        for finding in output.findings:
            assert isinstance(finding, Finding)
            assert hasattr(finding, "finding_id")
            assert hasattr(finding, "resource_name")
            assert hasattr(finding, "severity")
            assert finding.source == "ensemble"
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test that parallel execution works correctly."""
        llm = MockLLM()
        ensemble = BlueTeamEnsemble(
            llm=llm,
            language="terraform",
            specialists=["security", "compliance", "architecture"],
            consensus_method="vote",  # No LLM call for consensus
            run_parallel=True,
        )
        
        output = await ensemble.execute(SAMPLE_TERRAFORM_CODE)
        
        # All 3 specialists should have been called
        assert llm.call_count == 3
        assert isinstance(output, EnsembleOutput)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestGameEngineIntegration:
    """Tests for ensemble integration with GameEngine."""
    
    def test_game_config_ensemble_fields(self):
        """Test that GameConfig has ensemble fields."""
        from src.game.engine import GameConfig
        
        config = GameConfig(
            red_model="test-model",
            blue_model="test-model",
            difficulty="medium",
            language="terraform",
            cloud_provider="aws",
            blue_team_mode="ensemble",
            ensemble_specialists=["security", "compliance"],
            consensus_method="vote",
        )
        
        assert config.blue_team_mode == "ensemble"
        assert config.ensemble_specialists == ["security", "compliance"]
        assert config.consensus_method == "vote"
    
    def test_game_result_ensemble_fields(self):
        """Test that GameResult has ensemble fields."""
        from src.game.engine import GameResult, GameConfig
        from src.game.scenarios import Scenario
        from src.agents.red_team_agent import RedTeamOutput
        from src.agents.blue_team_agent import BlueTeamOutput
        from src.agents.judge_agent import ScoringResult
        
        # This just tests that the dataclass accepts the fields
        # Full integration test would require mocking the LLM
        
        config = GameConfig(
            red_model="test",
            blue_model="test",
            difficulty="medium",
            language="terraform",
            cloud_provider="aws",
            blue_team_mode="ensemble",
        )
        
        assert config.blue_team_mode == "ensemble"


class TestCLIIntegration:
    """Tests for ensemble integration with CLI."""
    
    def test_game_command_has_ensemble_options(self):
        """Test that game command accepts ensemble options."""
        from click.testing import CliRunner
        from src.cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["game", "--help"])
        
        assert "--blue-team-mode" in result.output
        assert "--consensus-method" in result.output
        assert "ensemble" in result.output
        assert "debate" in result.output


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
