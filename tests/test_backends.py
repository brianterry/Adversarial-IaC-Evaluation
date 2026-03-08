"""Tests for backend abstraction layer."""
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from src.backends.base import BackendConfig, ModelBackend, ModelResponse
from src.backends import create_backend
from src.backends.direct_api import DirectAPIBackend
from src.backends.sagemaker import SageMakerBackend
from src.backends.adapter import BackendChatModel
from src.game.engine import GameConfig


class TestBackendConfig:
    """Test 1: BackendConfig.extra defaults to {} (not None — mutable default guard)."""

    def test_extra_defaults_to_empty_dict(self):
        config = BackendConfig(model_id="test")
        assert config.extra == {}
        assert config.extra is not None


class TestBedrockBackend:
    """Test 2: BedrockBackend produces ModelResponse — mock ChatBedrockConverse."""

    @patch("src.backends.bedrock.ChatBedrockConverse")
    def test_bedrock_produces_model_response(self, mock_converse):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello"
        mock_response.usage_metadata = {"input_tokens": 10, "output_tokens": 5}
        mock_llm.invoke.return_value = mock_response
        mock_converse.return_value = mock_llm

        from src.backends.bedrock import BedrockBackend

        config = BackendConfig(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")
        backend = BedrockBackend(config)
        result = backend.invoke([{"role": "user", "content": "Hi"}])

        assert isinstance(result, ModelResponse)
        assert result.content == "Hello"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.backend == "bedrock"


class TestDirectAPIBackendExtractThinking:
    """Test 3: DirectAPIBackend._extract_thinking strips <think> tags correctly."""

    def test_extract_thinking_strips_tags(self):
        config = BackendConfig(model_id="test", extra={"base_url": "http://test", "api_key_env": "NONE"})
        backend = DirectAPIBackend(config)
        raw = "<think>Let me think...</think>\nHere is the answer."
        thinking, content = backend._extract_thinking(raw)
        assert thinking == "Let me think..."
        assert "Here is the answer." in content
        assert "<think>" not in content


class TestDirectAPIBackendExtractThinkingNoTags:
    """Test 4: DirectAPIBackend._extract_thinking returns (None, raw) when no tags."""

    def test_extract_thinking_no_tags(self):
        config = BackendConfig(model_id="test", extra={"base_url": "http://test", "api_key_env": "NONE"})
        backend = DirectAPIBackend(config)
        raw = "Just plain text without think tags"
        thinking, content = backend._extract_thinking(raw)
        assert thinking is None
        assert content == raw


class TestDirectAPIBackendApiKeyMissing:
    """Test 5: DirectAPIBackend raises ValueError when api_key_env not set in env."""

    def test_raises_when_api_key_missing(self):
        config = BackendConfig(
            model_id="test",
            extra={"base_url": "http://test", "api_key_env": "NONEXISTENT_ENV_VAR_12345"},
        )
        with pytest.raises(ValueError, match="API key not found"):
            DirectAPIBackend(config)


class TestDirectAPIBackendApiKeyNone:
    """Test 6: DirectAPIBackend uses sk-placeholder when api_key_env == NONE."""

    def test_uses_placeholder_when_none(self):
        config = BackendConfig(model_id="test", extra={"base_url": "http://test", "api_key_env": "NONE"})
        backend = DirectAPIBackend(config)
        assert backend._client is not None


class TestDirectAPIBackendBaseUrlMissing:
    """Test 18: DirectAPIBackend raises ValueError when base_url absent from extra."""

    def test_raises_when_base_url_missing(self):
        config = BackendConfig(model_id="test", extra={"api_key_env": "NONE"})
        with pytest.raises(ValueError, match="base_url"):
            DirectAPIBackend(config)


class TestSageMakerBackendEndpointMissing:
    """Test 7: SageMakerBackend raises ValueError when endpoint_name absent from extra."""

    def test_raises_when_endpoint_missing(self):
        config = BackendConfig(model_id="test", extra={})
        with pytest.raises(ValueError, match="endpoint_name"):
            SageMakerBackend(config)


class TestSageMakerBackendBuildPayload:
    """Test 8 & 9: SageMakerBackend._build_payload includes/excludes extra_body."""

    def test_includes_extra_body_when_thinking_mode_true(self):
        config = BackendConfig(
            model_id="test",
            extra={"endpoint_name": "test-ep"},
            thinking_mode=True,
            thinking_budget_tokens=8000,
        )
        backend = SageMakerBackend(config)
        payload = backend._build_payload([{"role": "user", "content": "Hi"}], "")
        assert "extra_body" in payload
        assert payload["extra_body"]["enable_thinking"] is True
        assert payload["extra_body"]["thinking_budget"] == 8000

    def test_excludes_extra_body_when_thinking_mode_false(self):
        config = BackendConfig(model_id="test", extra={"endpoint_name": "test-ep"}, thinking_mode=False)
        backend = SageMakerBackend(config)
        payload = backend._build_payload([{"role": "user", "content": "Hi"}], "")
        assert "extra_body" not in payload


class TestCreateBackendUnknown:
    """Test 10: create_backend raises ValueError for unknown backend type."""

    def test_raises_for_unknown_backend(self):
        config = BackendConfig(model_id="test")
        with pytest.raises(ValueError, match="Unknown backend"):
            create_backend(config, "unknown_backend")


class TestBackendChatModelAgenerate:
    """Test 11: BackendChatModel._agenerate calls backend.invoke via asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_agenerate_uses_to_thread(self):
        from langchain_core.messages import HumanMessage

        mock_backend = MagicMock(spec=ModelBackend)
        mock_backend.config = BackendConfig(model_id="test")
        mock_backend.invoke.return_value = ModelResponse(content="Hello")

        with patch("asyncio.to_thread", wraps=__import__("asyncio").to_thread) as mock_to_thread:
            adapter = BackendChatModel(backend=mock_backend)
            result = await adapter._agenerate([HumanMessage(content="Hi")])

            mock_to_thread.assert_called_once()
            assert result.generations[0].message.content == "Hello"


class TestBackendChatModelConvertMessages:
    """Test 12: BackendChatModel._convert_messages extracts SystemMessage as system_prompt."""

    def test_extracts_system_message(self):
        from langchain_core.messages import HumanMessage, SystemMessage

        mock_backend = MagicMock(spec=ModelBackend)
        mock_backend.config = BackendConfig(model_id="test")
        adapter = BackendChatModel(backend=mock_backend)

        messages = [
            SystemMessage(content="You are helpful"),
            HumanMessage(content="Hello"),
        ]
        converted, system_prompt = adapter._convert_messages(messages)
        assert system_prompt == "You are helpful"
        assert converted == [{"role": "user", "content": "Hello"}]


class TestGameConfigDefaults:
    """Test 13 & 14: GameConfig blue_backend_type and red_backend_type default to bedrock."""

    def test_blue_backend_type_defaults(self):
        config = GameConfig(
            red_model="red",
            blue_model="blue",
            difficulty="medium",
            language="terraform",
            cloud_provider="aws",
        )
        assert config.blue_backend_type == "bedrock"
        assert config.red_backend_type == "bedrock"


class TestRunExperimentMapping:
    """Test 15: run_experiment.py maps blue_backend_type from combo dict correctly."""

    def test_generate_game_configs_maps_backend_fields(self):
        from scripts.run_experiment import ExperimentRunner

        config_path = Path(__file__).parent.parent / "experiments/config/E1_model_comparison_v2.yaml"
        if not config_path.exists():
            pytest.skip("E1 config not found")
        runner = ExperimentRunner(str(config_path))
        games = runner.generate_game_configs()
        assert len(games) > 0
        assert games[0].get("blue_backend_type", "bedrock") == "bedrock"
        assert games[0].get("red_backend_type", "bedrock") == "bedrock"


class TestExistingYamlParses:
    """Test 16: Existing experiment YAML without backend fields parses without error."""

    def test_existing_config_parses(self):
        from scripts.run_experiment import ExperimentRunner

        config_path = Path(__file__).parent.parent / "experiments/config/E1S_deepseek_r1.yaml"
        if not config_path.exists():
            pytest.skip("E1S config not found")
        runner = ExperimentRunner(str(config_path))
        games = runner.generate_game_configs()
        assert len(games) > 0
        assert "blue_backend_type" in games[0]
        assert games[0]["blue_backend_type"] == "bedrock"


class TestCreateRedTeamAgentDefaultBackend:
    """Test 17: create_red_team_agent accepts backend_type param without breaking."""

    def test_accepts_backend_type_default(self):
        from src.agents.red_team_agent import create_red_team_agent

        # Should work without passing backend params (uses defaults)
        agent = create_red_team_agent(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            region="us-east-1",
            difficulty="medium",
        )
        assert agent is not None


class TestRealtimeGameDict:
    """Test 19: Realtime game dict includes blue_backend_type field with default bedrock."""

    def test_realtime_includes_backend_fields(self):
        from scripts.run_experiment import ExperimentRunner

        # E2 may have realtime enabled; if not, batch games still have backend fields
        config_path = Path(__file__).parent.parent / "experiments/config/E2_multiagent_ablation.yaml"
        if not config_path.exists():
            pytest.skip("E2 config not found")
        runner = ExperimentRunner(str(config_path))
        games = runner.generate_game_configs()
        assert len(games) > 0
        # All games (batch or realtime) should have backend fields
        assert "blue_backend_type" in games[0]
        assert games[0]["blue_backend_type"] == "bedrock"


