"""
Tests for Red Team Pipeline Multi-Agent Attack Chain

Tests cover:
1. Individual pipeline stages
2. RedTeamPipeline orchestrator
3. Integration with game engine
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import modules under test
from src.agents.red_specialists.base import PipelineStage, PipelineOutput
from src.agents.red_specialists.architect_agent import ArchitectAgent
from src.agents.red_specialists.vulnerability_selector_agent import VulnerabilitySelectorAgent
from src.agents.red_specialists.code_generator_agent import CodeGeneratorAgent
from src.agents.red_specialists.stealth_reviewer_agent import StealthReviewerAgent
from src.agents.red_team_pipeline import RedTeamPipeline, PipelineRedTeamOutput


# Mock LLM responses
MOCK_ARCHITECT_RESPONSE = json.dumps({
    "architecture_name": "Healthcare Data Storage",
    "description": "S3-based storage for PHI data",
    "components": [
        {
            "name": "data_bucket",
            "resource_type": "aws_s3_bucket",
            "purpose": "Store PHI data",
            "dependencies": [],
            "security_surface": ["encryption", "access_control"],
        },
        {
            "name": "logging_bucket",
            "resource_type": "aws_s3_bucket",
            "purpose": "Store access logs",
            "dependencies": ["data_bucket"],
            "security_surface": ["access_control"],
        },
    ],
    "data_flows": [
        {"from": "data_bucket", "to": "logging_bucket", "data_type": "logs", "sensitivity": "medium"}
    ],
    "security_boundaries": ["VPC boundary"],
    "compliance_requirements": ["HIPAA"],
    "recommended_vuln_injection_points": [
        {"component": "data_bucket", "attack_surface": "encryption", "realistic_mistake": "Missing encryption"}
    ],
})


MOCK_SELECTOR_RESPONSE = json.dumps({
    "selected_vulnerabilities": [
        {
            "vuln_id": "V1",
            "target_component": "data_bucket",
            "vulnerability_type": "encryption",
            "severity": "high",
            "title": "Missing server-side encryption",
            "description": "S3 bucket lacks SSE",
            "injection_point": {
                "resource_type": "aws_s3_bucket",
                "attribute": "server_side_encryption_configuration",
                "vulnerable_value": "null",
                "secure_value": "aws:kms",
            },
            "evasion_strategy": {
                "technique": "Add misleading comment",
                "decoy_configs": "Add bucket policy",
                "naming_strategy": "Name bucket 'secure-data'",
            },
            "detection_hints": "Check for encryption configuration",
        }
    ],
    "injection_narrative": "Developer forgot encryption",
    "expected_detection_difficulty": "medium",
})


MOCK_GENERATOR_RESPONSE = """
MAIN_FILE_BEGINS_HERE
resource "aws_s3_bucket" "data_bucket" {
  bucket = "secure-healthcare-data"
  
  tags = {
    Name = "Healthcare Data Storage"
    Environment = "production"
  }
}

resource "aws_s3_bucket_public_access_block" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
MAIN_FILE_ENDS_HERE

VARIABLES_FILE_BEGINS_HERE
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}
VARIABLES_FILE_ENDS_HERE

IMPLEMENTATION_NOTES_BEGINS_HERE
{
    "implementations": [
        {
            "vuln_id": "V1",
            "resource_name": "aws_s3_bucket.data_bucket",
            "line_number_estimate": 1,
            "implementation_notes": "No encryption configured",
            "evasion_techniques_used": ["misleading_name", "decoy_public_access_block"]
        }
    ]
}
IMPLEMENTATION_NOTES_ENDS_HERE
"""


MOCK_REVIEWER_RESPONSE = """
REFINED_MAIN_FILE_BEGINS_HERE
# Healthcare compliant data storage
# Encryption handled by AWS default settings
resource "aws_s3_bucket" "secure_data_bucket" {
  bucket = "hipaa-compliant-healthcare-data"
  
  tags = {
    Name        = "HIPAA Compliant Storage"
    Environment = "production"
    Compliance  = "HIPAA"
  }
}

resource "aws_s3_bucket_public_access_block" "secure_data_bucket" {
  bucket = aws_s3_bucket.secure_data_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
REFINED_MAIN_FILE_ENDS_HERE

REFINED_VARIABLES_FILE_BEGINS_HERE
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}
REFINED_VARIABLES_FILE_ENDS_HERE

STEALTH_REPORT_BEGINS_HERE
{
    "vulnerabilities_reviewed": [
        {
            "vuln_id": "V1",
            "original_detectability": "easy",
            "refined_detectability": "hard",
            "techniques_applied": ["misleading_comment", "compliance_tags", "security_naming"],
            "decoys_added": ["public_access_block"],
            "confidence": 0.85
        }
    ],
    "overall_stealth_score": 0.85,
    "recommendations": "Consider adding KMS key reference as additional decoy"
}
STEALTH_REPORT_ENDS_HERE
"""


class MockLLM:
    """Mock LLM for testing without API calls."""
    
    def __init__(self):
        self.call_count = 0
        self.call_history = []
    
    async def ainvoke(self, messages):
        self.call_count += 1
        prompt = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])
        self.call_history.append(prompt)
        
        # Return appropriate response based on prompt content
        if "CLOUD INFRASTRUCTURE ARCHITECT" in prompt:
            return MagicMock(content=MOCK_ARCHITECT_RESPONSE)
        elif "SECURITY RESEARCHER selecting" in prompt:
            return MagicMock(content=MOCK_SELECTOR_RESPONSE)
        elif "INFRASTRUCTURE DEVELOPER" in prompt:
            return MagicMock(content=MOCK_GENERATOR_RESPONSE)
        elif "SECURITY EVASION SPECIALIST" in prompt:
            return MagicMock(content=MOCK_REVIEWER_RESPONSE)
        else:
            return MagicMock(content="{}")


# =============================================================================
# PIPELINE STAGE TESTS
# =============================================================================

class TestArchitectAgent:
    """Tests for ArchitectAgent pipeline stage."""
    
    @pytest.fixture
    def architect(self):
        """Create an ArchitectAgent with mock LLM."""
        llm = MockLLM()
        return ArchitectAgent(llm=llm, cloud_provider="aws", language="terraform")
    
    def test_stage_name(self, architect):
        """Test that stage name is correct."""
        assert architect.stage_name == "architect"
    
    @pytest.mark.asyncio
    async def test_execute_returns_pipeline_output(self, architect):
        """Test that execute returns PipelineOutput with architecture."""
        scenario = {"description": "Create S3 bucket for healthcare data"}
        output = await architect.execute(scenario)
        
        assert isinstance(output, PipelineOutput)
        assert output.stage_name == "architect"
        assert output.success
        assert "components" in output.data
        assert len(output.data["components"]) == 2


class TestVulnerabilitySelectorAgent:
    """Tests for VulnerabilitySelectorAgent pipeline stage."""
    
    @pytest.fixture
    def selector(self):
        """Create a VulnerabilitySelectorAgent with mock LLM."""
        llm = MockLLM()
        return VulnerabilitySelectorAgent(
            llm=llm,
            cloud_provider="aws",
            language="terraform",
            difficulty="medium",
            vuln_count=3,
        )
    
    def test_stage_name(self, selector):
        """Test that stage name is correct."""
        assert selector.stage_name == "vulnerability_selector"
    
    @pytest.mark.asyncio
    async def test_execute_returns_vulnerabilities(self, selector):
        """Test that execute returns selected vulnerabilities."""
        architecture = {"components": [{"name": "data_bucket"}]}
        output = await selector.execute(architecture)
        
        assert isinstance(output, PipelineOutput)
        assert output.success
        assert "selected_vulnerabilities" in output.data
        assert len(output.data["selected_vulnerabilities"]) == 1


class TestCodeGeneratorAgent:
    """Tests for CodeGeneratorAgent pipeline stage."""
    
    @pytest.fixture
    def generator(self):
        """Create a CodeGeneratorAgent with mock LLM."""
        llm = MockLLM()
        return CodeGeneratorAgent(llm=llm, cloud_provider="aws", language="terraform")
    
    def test_stage_name(self, generator):
        """Test that stage name is correct."""
        assert generator.stage_name == "code_generator"
    
    @pytest.mark.asyncio
    async def test_execute_returns_code(self, generator):
        """Test that execute returns code files."""
        input_data = {
            "architecture": {"components": []},
            "vulnerabilities": {"selected_vulnerabilities": []},
        }
        output = await generator.execute(input_data)
        
        assert isinstance(output, PipelineOutput)
        assert output.success
        assert "code" in output.data
        assert "main.tf" in output.data["code"]


class TestStealthReviewerAgent:
    """Tests for StealthReviewerAgent pipeline stage."""
    
    @pytest.fixture
    def reviewer(self):
        """Create a StealthReviewerAgent with mock LLM."""
        llm = MockLLM()
        return StealthReviewerAgent(
            llm=llm,
            cloud_provider="aws",
            language="terraform",
            difficulty="medium",
        )
    
    def test_stage_name(self, reviewer):
        """Test that stage name is correct."""
        assert reviewer.stage_name == "stealth_reviewer"
    
    @pytest.mark.asyncio
    async def test_execute_returns_refined_code(self, reviewer):
        """Test that execute returns refined code and stealth report."""
        input_data = {
            "code": {"main.tf": "resource aws_s3_bucket test {}"},
            "vulnerabilities": {"selected_vulnerabilities": []},
            "implementation_notes": [],
        }
        output = await reviewer.execute(input_data)
        
        assert isinstance(output, PipelineOutput)
        assert output.success
        assert "code" in output.data
        assert "stealth_report" in output.data


# =============================================================================
# RED TEAM PIPELINE TESTS
# =============================================================================

class TestRedTeamPipeline:
    """Tests for RedTeamPipeline orchestrator."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a RedTeamPipeline with mock LLM."""
        llm = MockLLM()
        return RedTeamPipeline(
            llm=llm,
            cloud_provider="aws",
            language="terraform",
            difficulty="medium",
            vuln_count=3,
        )
    
    def test_pipeline_stages(self, pipeline):
        """Test that pipeline has all stages."""
        assert len(pipeline.PIPELINE_STAGES) == 4
        assert "architect" in pipeline.PIPELINE_STAGES
        assert "vulnerability_selector" in pipeline.PIPELINE_STAGES
        assert "code_generator" in pipeline.PIPELINE_STAGES
        assert "stealth_reviewer" in pipeline.PIPELINE_STAGES
    
    def test_to_dict(self, pipeline):
        """Test configuration export."""
        config = pipeline.to_dict()
        
        assert config["agent_type"] == "RedTeamPipeline"
        assert config["mode"] == "pipeline"
        assert config["difficulty"] == "medium"
        assert "stages" in config
    
    @pytest.mark.asyncio
    async def test_execute_returns_pipeline_output(self, pipeline):
        """Test that execute returns PipelineRedTeamOutput."""
        scenario = {"description": "Create S3 bucket for healthcare data"}
        output = await pipeline.execute(scenario)
        
        assert isinstance(output, PipelineRedTeamOutput)
        assert "code" in dir(output)
        assert "manifest" in dir(output)
        assert output.pipeline_stages is not None
        assert len(output.pipeline_stages) == 4
    
    @pytest.mark.asyncio
    async def test_execute_produces_code(self, pipeline):
        """Test that execute produces IaC code."""
        scenario = {"description": "Create S3 bucket"}
        output = await pipeline.execute(scenario)
        
        assert output.code is not None
        assert len(output.code) > 0
    
    @pytest.mark.asyncio
    async def test_execute_has_architecture_design(self, pipeline):
        """Test that execute includes architecture design."""
        scenario = {"description": "Create storage infrastructure"}
        output = await pipeline.execute(scenario)
        
        assert output.architecture_design is not None
        assert "components" in output.architecture_design


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestGameEngineIntegration:
    """Tests for pipeline integration with GameEngine."""
    
    def test_game_config_has_red_team_mode(self):
        """Test that GameConfig has red_team_mode field."""
        from src.game.engine import GameConfig
        
        config = GameConfig(
            red_model="test-model",
            blue_model="test-model",
            difficulty="medium",
            language="terraform",
            cloud_provider="aws",
            red_team_mode="pipeline",
        )
        
        assert config.red_team_mode == "pipeline"
    
    def test_game_result_has_pipeline_fields(self):
        """Test that GameResult has pipeline fields."""
        from src.game.engine import GameResult, GameConfig
        
        config = GameConfig(
            red_model="test",
            blue_model="test",
            difficulty="medium",
            language="terraform",
            cloud_provider="aws",
            red_team_mode="pipeline",
        )
        
        assert config.red_team_mode == "pipeline"


class TestCLIIntegration:
    """Tests for pipeline integration with CLI."""
    
    def test_game_command_has_red_team_mode_option(self):
        """Test that game command accepts --red-team-mode."""
        from click.testing import CliRunner
        from src.cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ["game", "--help"])
        
        assert "--red-team-mode" in result.output
        assert "pipeline" in result.output


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
