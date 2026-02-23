"""
Tests for Adversarial Debate Verification System

Tests cover:
1. Prosecutor agent arguments
2. Defender agent arguments
3. Judge verdicts
4. Full debate flow
5. Integration with game engine
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.blue_team_agent import Finding
from src.agents.debate_verification import (
    DebateVerificationAgent,
    DebateResult,
    DebateVerificationOutput,
)


# Mock LLM responses
MOCK_PROSECUTION_RESPONSE = json.dumps({
    "position": "VALID_FINDING",
    "finding_id": "F1",
    "arguments": [
        {
            "point": "S3 bucket lacks server-side encryption",
            "evidence": "No aws_s3_bucket_server_side_encryption_configuration resource",
            "impact": "PHI data could be exposed at rest",
            "reference": "AWS CIS Benchmark 2.1.1",
        }
    ],
    "counter_to_defense": [
        "Default encryption does not apply to existing objects",
        "Compliance requires explicit SSE-KMS",
    ],
    "severity_justification": "HIGH because PHI data requires encryption",
    "confidence": 0.95,
    "verdict_recommendation": "TRUE_POSITIVE",
})


MOCK_DEFENSE_RESPONSE = json.dumps({
    "position": "INVALID_FINDING",
    "finding_id": "F1",
    "arguments": [
        {
            "point": "AWS enables default encryption",
            "evidence": "Since 2023, S3 applies SSE-S3 by default",
            "mitigating_factor": "Data is encrypted at rest",
            "context": "Bucket is in us-east-1 with default encryption",
        }
    ],
    "counter_to_prosecution": [
        "Default SSE-S3 is sufficient for many use cases",
        "HIPAA does not mandate KMS specifically",
    ],
    "alternative_interpretation": "Missing explicit config != no encryption",
    "confidence": 0.60,
    "verdict_recommendation": "FALSE_POSITIVE",
})


MOCK_JUDGE_TRUE_POSITIVE = json.dumps({
    "finding_id": "F1",
    "verdict": "TRUE_POSITIVE",
    "reasoning": {
        "prosecution_strengths": ["Clear evidence of missing config", "Valid compliance reference"],
        "prosecution_weaknesses": [],
        "defense_strengths": ["Correct about default encryption"],
        "defense_weaknesses": ["Default encryption not sufficient for HIPAA PHI"],
    },
    "decisive_factors": ["HIPAA requires explicit encryption controls", "Best practice violation"],
    "ground_truth_alignment": "Matches V1 in manifest",
    "final_severity": "high",
    "confidence": 0.90,
    "notes": "Prosecution argument more compelling for compliance context",
})


MOCK_JUDGE_FALSE_POSITIVE = json.dumps({
    "finding_id": "F2",
    "verdict": "FALSE_POSITIVE",
    "reasoning": {
        "prosecution_strengths": [],
        "prosecution_weaknesses": ["Misidentified resource type"],
        "defense_strengths": ["Resource has compensating control"],
        "defense_weaknesses": [],
    },
    "decisive_factors": ["Finding based on incorrect analysis"],
    "ground_truth_alignment": "No matching vulnerability in manifest",
    "final_severity": "none",
    "confidence": 0.85,
    "notes": "Defense successfully demonstrated false positive",
})


class MockLLM:
    """Mock LLM for testing debate without API calls."""
    
    def __init__(self, responses=None):
        self.call_count = 0
        self.responses = responses or []
        self.call_history = []
    
    async def ainvoke(self, messages):
        self.call_count += 1
        prompt = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])
        self.call_history.append(prompt)
        
        # Return appropriate response based on prompt content
        if "SECURITY PROSECUTOR" in prompt:
            return MagicMock(content=MOCK_PROSECUTION_RESPONSE)
        elif "SECURITY DEFENDER" in prompt:
            return MagicMock(content=MOCK_DEFENSE_RESPONSE)
        elif "IMPARTIAL JUDGE" in prompt:
            # Alternate verdicts for variety
            if self.call_count % 2 == 1:
                return MagicMock(content=MOCK_JUDGE_TRUE_POSITIVE)
            else:
                return MagicMock(content=MOCK_JUDGE_FALSE_POSITIVE)
        else:
            return MagicMock(content="{}")


# =============================================================================
# DEBATE RESULT TESTS
# =============================================================================

class TestDebateResult:
    """Tests for DebateResult dataclass."""
    
    def test_create_debate_result(self):
        """Test creating a DebateResult."""
        result = DebateResult(
            finding_id="F1",
            prosecution_argument={"position": "VALID_FINDING"},
            defense_argument={"position": "INVALID_FINDING"},
            verdict="TRUE_POSITIVE",
            verdict_confidence=0.90,
            verdict_reasoning={"decisive_factors": ["test"]},
            final_severity="high",
        )
        
        assert result.finding_id == "F1"
        assert result.verdict == "TRUE_POSITIVE"
        assert result.verdict_confidence == 0.90


# =============================================================================
# DEBATE VERIFICATION AGENT TESTS
# =============================================================================

class TestDebateVerificationAgent:
    """Tests for DebateVerificationAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a DebateVerificationAgent with mock LLM."""
        llm = MockLLM()
        return DebateVerificationAgent(llm=llm, language="terraform", run_parallel=False)
    
    @pytest.fixture
    def sample_findings(self):
        """Create sample findings for testing."""
        return [
            Finding(
                finding_id="F1",
                resource_name="aws_s3_bucket.data",
                resource_type="aws_s3_bucket",
                vulnerability_type="encryption",
                severity="high",
                title="Missing S3 encryption",
                description="S3 bucket lacks server-side encryption",
                evidence="No encryption configuration found",
                line_number_estimate=10,
                confidence=0.8,
                reasoning="S3 bucket should have encryption enabled",
                remediation="Add server_side_encryption_configuration block",
                source="llm",
            ),
            Finding(
                finding_id="F2",
                resource_name="aws_s3_bucket.logs",
                resource_type="aws_s3_bucket",
                vulnerability_type="logging",
                severity="medium",
                title="Missing access logging",
                description="S3 bucket lacks access logging",
                evidence="No logging configuration",
                line_number_estimate=20,
                confidence=0.7,
                reasoning="S3 bucket should have access logging",
                remediation="Add logging configuration block",
                source="llm",
            ),
        ]
    
    @pytest.fixture
    def sample_code(self):
        """Create sample code for testing."""
        return {
            "main.tf": """
resource "aws_s3_bucket" "data" {
  bucket = "test-data-bucket"
}

resource "aws_s3_bucket" "logs" {
  bucket = "test-logs-bucket"
}
""",
        }
    
    @pytest.fixture
    def sample_manifest(self):
        """Create sample manifest for testing."""
        return [
            {
                "vuln_id": "V1",
                "title": "Missing encryption",
                "resource_name": "aws_s3_bucket.data",
                "vulnerability_type": "encryption",
            }
        ]
    
    def test_verdicts_constant(self, agent):
        """Test that agent has all verdict types."""
        assert "TRUE_POSITIVE" in agent.VERDICTS
        assert "FALSE_POSITIVE" in agent.VERDICTS
        assert "PARTIAL_MATCH" in agent.VERDICTS
        assert "DUPLICATE" in agent.VERDICTS
        assert "INCONCLUSIVE" in agent.VERDICTS
    
    def test_to_dict(self, agent):
        """Test configuration export."""
        config = agent.to_dict()
        
        assert config["agent_type"] == "DebateVerificationAgent"
        assert config["mode"] == "debate"
        assert config["language"] == "terraform"
    
    @pytest.mark.asyncio
    async def test_verify_returns_output(self, agent, sample_findings, sample_code, sample_manifest):
        """Test that verify returns DebateVerificationOutput."""
        output = await agent.verify(
            findings=sample_findings,
            code=sample_code,
            manifest=sample_manifest,
        )
        
        assert isinstance(output, DebateVerificationOutput)
        assert output.debate_results is not None
        assert len(output.debate_results) == 2
    
    @pytest.mark.asyncio
    async def test_verify_separates_findings(self, agent, sample_findings, sample_code, sample_manifest):
        """Test that verify separates verified and rejected findings."""
        output = await agent.verify(
            findings=sample_findings,
            code=sample_code,
            manifest=sample_manifest,
        )
        
        # Should have some in each category (based on mock responses)
        assert output.verified_findings is not None
        assert output.rejected_findings is not None
        total = len(output.verified_findings) + len(output.rejected_findings)
        assert total == len(sample_findings)
    
    @pytest.mark.asyncio
    async def test_verify_produces_scoring(self, agent, sample_findings, sample_code, sample_manifest):
        """Test that verify produces scoring results."""
        output = await agent.verify(
            findings=sample_findings,
            code=sample_code,
            manifest=sample_manifest,
        )
        
        assert output.scoring is not None
        assert hasattr(output.scoring, "precision")
        assert hasattr(output.scoring, "recall")
    
    @pytest.mark.asyncio
    async def test_verify_includes_stats(self, agent, sample_findings, sample_code, sample_manifest):
        """Test that verify includes debate statistics."""
        output = await agent.verify(
            findings=sample_findings,
            code=sample_code,
            manifest=sample_manifest,
        )
        
        assert output.debate_stats is not None
        assert "total_findings_debated" in output.debate_stats
        assert output.debate_stats["total_findings_debated"] == 2


class TestDebateVerificationParallel:
    """Tests for parallel debate execution."""
    
    @pytest.fixture
    def parallel_agent(self):
        """Create a parallel DebateVerificationAgent."""
        llm = MockLLM()
        return DebateVerificationAgent(llm=llm, language="terraform", run_parallel=True)
    
    @pytest.fixture
    def many_findings(self):
        """Create many findings for parallel testing."""
        return [
            Finding(
                finding_id=f"F{i}",
                resource_name=f"resource_{i}",
                resource_type="aws_s3_bucket",
                vulnerability_type="encryption",
                severity="high",
                title=f"Finding {i}",
                description="Test finding",
                evidence="Evidence",
                line_number_estimate=i * 10,
                confidence=0.8,
                reasoning=f"Test reasoning {i}",
                remediation=f"Test remediation {i}",
                source="llm",
            )
            for i in range(5)
        ]
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, parallel_agent, many_findings):
        """Test that parallel execution handles multiple findings."""
        output = await parallel_agent.verify(
            findings=many_findings,
            code={"main.tf": "resource test {}"},
            manifest=[],
        )
        
        assert len(output.debate_results) == 5


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestGameEngineIntegration:
    """Tests for debate integration with GameEngine."""
    
    def test_game_config_has_verification_mode(self):
        """Test that GameConfig has verification_mode field."""
        from src.game.engine import GameConfig
        
        config = GameConfig(
            red_model="test-model",
            blue_model="test-model",
            difficulty="medium",
            language="terraform",
            cloud_provider="aws",
            verification_mode="debate",
        )
        
        assert config.verification_mode == "debate"
    
    def test_game_result_has_debate_fields(self):
        """Test that GameResult has debate fields."""
        from src.game.engine import GameResult, GameConfig
        
        # Just test that the fields exist in the dataclass definition
        from dataclasses import fields
        
        field_names = [f.name for f in fields(GameResult)]
        
        assert "debate_results" in field_names
        assert "verified_findings" in field_names
        assert "rejected_findings" in field_names


class TestCLIIntegration:
    """Tests for debate integration with CLI."""
    
    def test_game_command_has_verification_mode_option(self):
        """Test that game command accepts --verification-mode."""
        from click.testing import CliRunner
        from src.cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["game", "--help"])
        
        assert "--verification-mode" in result.output
        assert "debate" in result.output


# =============================================================================
# PROMPT TESTS
# =============================================================================

class TestAdversarialDebatePrompts:
    """Tests for adversarial debate prompts."""
    
    def test_prompts_exist(self):
        """Test that all debate prompts are defined."""
        from src.prompts import AdversarialDebatePrompts
        
        assert hasattr(AdversarialDebatePrompts, "PROSECUTOR_AGENT")
        assert hasattr(AdversarialDebatePrompts, "DEFENDER_AGENT")
        assert hasattr(AdversarialDebatePrompts, "JUDGE_VERDICT_AGENT")
    
    def test_prosecutor_prompt_has_placeholders(self):
        """Test that prosecutor prompt has required placeholders."""
        from src.prompts import AdversarialDebatePrompts
        
        prompt = AdversarialDebatePrompts.PROSECUTOR_AGENT
        
        assert "{finding_json}" in prompt
        assert "{language}" in prompt
        assert "{code}" in prompt
        assert "{manifest_json}" in prompt
    
    def test_defender_prompt_has_placeholders(self):
        """Test that defender prompt has required placeholders."""
        from src.prompts import AdversarialDebatePrompts
        
        prompt = AdversarialDebatePrompts.DEFENDER_AGENT
        
        assert "{finding_json}" in prompt
        assert "{language}" in prompt
        assert "{code}" in prompt
    
    def test_judge_prompt_has_placeholders(self):
        """Test that judge verdict prompt has required placeholders."""
        from src.prompts import AdversarialDebatePrompts
        
        prompt = AdversarialDebatePrompts.JUDGE_VERDICT_AGENT
        
        assert "{finding_json}" in prompt
        assert "{prosecution_json}" in prompt
        assert "{defense_json}" in prompt


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
