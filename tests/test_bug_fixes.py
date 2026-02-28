"""
Tests for critical bug fixes:
1. Manifest validation: dataclass-to-dict conversion (engine.py)
2. Checkov runner: None severity handling (checkov_runner.py)
3. Red Team: unique vuln_id generation (red_team_agent.py)

These tests verify regressions found during E3 experiment execution.
"""

import json
import pytest
from dataclasses import dataclass, asdict
from unittest.mock import MagicMock, patch, AsyncMock


# ============================================================================
# Test 1: Manifest validation dataclass-to-dict conversion
# ============================================================================

class TestManifestValidationConversion:
    """
    Bug: engine.py passed VulnerabilityManifest dataclass objects to
    ManifestValidator.validate(), which expected List[Dict]. The validator
    called .get() on dataclass objects, causing:
      'VulnerabilityManifest' object has no attribute 'get'
    
    Fix: Convert dataclass objects to dicts before passing to validator.
    """

    def test_dataclass_to_dict_conversion(self):
        """VulnerabilityManifest objects should be converted to dicts."""
        from src.agents.red_team_agent import VulnerabilityManifest

        vuln = VulnerabilityManifest(
            vuln_id="V1",
            rule_id="AVD-AWS-001",
            title="Missing encryption",
            type="encryption",
            severity="high",
            resource_name="aws_s3_bucket.data",
            resource_type="aws_s3_bucket",
            line_number_estimate=10,
            vulnerable_attribute="server_side_encryption_configuration",
            vulnerable_value="",
            stealth_technique="omission",
            detection_hint="Look for missing encryption",
        )

        # Simulate what engine.py now does
        manifest_dicts = []
        for v in [vuln]:
            if hasattr(v, '__dataclass_fields__'):
                manifest_dicts.append(asdict(v))
            elif isinstance(v, dict):
                manifest_dicts.append(v)
            else:
                manifest_dicts.append({"vuln_id": str(v)})

        assert len(manifest_dicts) == 1
        assert isinstance(manifest_dicts[0], dict)
        assert manifest_dicts[0]["vuln_id"] == "V1"
        assert manifest_dicts[0]["resource_name"] == "aws_s3_bucket.data"
        assert manifest_dicts[0]["type"] == "encryption"

    def test_dict_input_passthrough(self):
        """If manifest is already a list of dicts, pass through unchanged."""
        vuln_dict = {
            "vuln_id": "V1",
            "resource_name": "aws_s3_bucket.data",
            "type": "encryption",
        }

        manifest_dicts = []
        for v in [vuln_dict]:
            if hasattr(v, '__dataclass_fields__'):
                manifest_dicts.append(asdict(v))
            elif isinstance(v, dict):
                manifest_dicts.append(v)
            else:
                manifest_dicts.append({"vuln_id": str(v)})

        assert len(manifest_dicts) == 1
        assert manifest_dicts[0] is vuln_dict  # Same object, not copied

    def test_converted_dict_has_get_method(self):
        """Converted dicts must support .get() (what the validator uses)."""
        from src.agents.red_team_agent import VulnerabilityManifest

        vuln = VulnerabilityManifest(
            vuln_id="V1",
            rule_id="",
            title="Test",
            type="encryption",
            severity="high",
            resource_name="bucket",
            resource_type="aws_s3_bucket",
            line_number_estimate=0,
            vulnerable_attribute="sse",
            vulnerable_value="",
            stealth_technique="",
            detection_hint="",
        )

        d = asdict(vuln)

        # These are the exact .get() calls the ManifestValidator makes
        assert d.get("vuln_id", "unknown") == "V1"
        assert d.get("resource_name", "").lower() == "bucket"
        assert d.get("type", "unknown").lower() == "encryption"
        assert d.get("vulnerable_attribute", "").lower() == "sse"
        assert d.get("title", "").lower() == "test"

    def test_novel_vuln_fields_preserved(self):
        """Novel vulnerability fields (is_novel, rule_source) survive conversion."""
        from src.agents.red_team_agent import VulnerabilityManifest

        vuln = VulnerabilityManifest(
            vuln_id="V1",
            rule_id="NOVEL-V1",
            title="Custom vuln",
            type="access_control",
            severity="medium",
            resource_name="aws_iam_role.admin",
            resource_type="aws_iam_role",
            line_number_estimate=5,
            vulnerable_attribute="assume_role_policy",
            vulnerable_value="*",
            stealth_technique="naming",
            detection_hint="Check wildcard",
            is_novel=True,
            rule_source="novel",
        )

        d = asdict(vuln)
        assert d["is_novel"] is True
        assert d["rule_source"] == "novel"


# ============================================================================
# Test 2: Checkov None severity handling
# ============================================================================

class TestCheckovNoneSeverity:
    """
    Bug: checkov_runner.py called .lower() on check["severity"] which could
    be None, causing:
      'NoneType' object has no attribute 'lower'
    
    Fix: Use check.get("severity") which returns None for missing keys,
    and the truthiness check skips None values.
    """

    def test_none_severity_returns_default(self):
        """Checkov check with severity=None should return inferred severity."""
        from src.tools.checkov_runner import CheckovRunner

        runner = CheckovRunner.__new__(CheckovRunner)
        runner.config = MagicMock()
        runner.config.severity_filter = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        runner.logger = MagicMock()

        # Check with severity explicitly set to None
        check = {
            "check_id": "CKV_AWS_18",
            "check_name": "Ensure the S3 bucket has access logging enabled",
            "severity": None,
        }

        severity = runner._determine_severity(check)
        assert severity is not None
        assert isinstance(severity, str)
        assert severity in ["critical", "high", "medium", "low"]

    def test_missing_severity_returns_default(self):
        """Checkov check with no severity key should return inferred severity."""
        from src.tools.checkov_runner import CheckovRunner

        runner = CheckovRunner.__new__(CheckovRunner)
        runner.config = MagicMock()
        runner.logger = MagicMock()

        check = {
            "check_id": "CKV_AWS_999",
            "check_name": "Some unknown check",
        }

        severity = runner._determine_severity(check)
        assert severity == "medium"  # Default

    def test_valid_severity_passes_through(self):
        """Checkov check with valid severity should pass through."""
        from src.tools.checkov_runner import CheckovRunner

        runner = CheckovRunner.__new__(CheckovRunner)
        runner.config = MagicMock()
        runner.logger = MagicMock()

        check = {
            "check_id": "CKV_AWS_18",
            "check_name": "test",
            "severity": "HIGH",
        }

        severity = runner._determine_severity(check)
        assert severity == "high"

    def test_public_check_name_returns_high(self):
        """Checkov checks with 'public' in name should be high severity."""
        from src.tools.checkov_runner import CheckovRunner

        runner = CheckovRunner.__new__(CheckovRunner)
        runner.config = MagicMock()
        runner.logger = MagicMock()

        check = {
            "check_id": "CKV_AWS_20",
            "check_name": "Ensure S3 bucket is not public",
            "severity": None,  # None severity shouldn't crash
        }

        severity = runner._determine_severity(check)
        assert severity == "high"

    def test_convert_check_with_none_severity(self):
        """Full _convert_check_to_finding should not crash with None severity."""
        from src.tools.checkov_runner import CheckovRunner

        runner = CheckovRunner.__new__(CheckovRunner)
        runner.config = MagicMock()
        runner.config.severity_filter = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        runner.logger = MagicMock()

        check = {
            "check_id": "CKV_AWS_18",
            "check_name": "Ensure S3 access logging",
            "check_result": {"result": "FAILED"},
            "resource": "aws_s3_bucket.data",
            "resource_type": "aws_s3_bucket",
            "severity": None,
            "guideline": "https://docs.example.com",
            "file_path": "/main.tf",
            "file_line_range": [10, 15],
        }

        finding = runner._convert_check_to_finding(check, 1)

        # Should NOT return None (which would mean it crashed)
        assert finding is not None
        assert finding.finding_id == "CKV-1"
        assert finding.resource_name == "aws_s3_bucket.data"


# ============================================================================
# Test 3: Unique vuln_id generation in manifest parsing
# ============================================================================

class TestUniqueVulnIds:
    """
    Bug: red_team_agent._parse_manifest_json() didn't enforce unique vuln_ids.
    If the LLM generated duplicate IDs (e.g., two "V1" entries), the display
    showed V1/V2/V3 (from enumeration) but match results showed V1/V1/V2.
    
    Fix: Track seen vuln_ids and auto-assign unique IDs for duplicates.
    """

    def test_duplicate_vuln_ids_get_unique_ids(self):
        """Duplicate vuln_ids from LLM should be made unique."""
        from src.agents.red_team_agent import RedTeamAgent

        agent = RedTeamAgent.__new__(RedTeamAgent)
        agent.logger = MagicMock()

        json_str = json.dumps({
            "injected_vulnerabilities": [
                {"vuln_id": "V1", "title": "First vuln", "resource_name": "bucket1"},
                {"vuln_id": "V1", "title": "Second vuln", "resource_name": "bucket2"},
                {"vuln_id": "V2", "title": "Third vuln", "resource_name": "bucket3"},
            ]
        })

        manifest = agent._parse_manifest_json(json_str)

        assert len(manifest) == 3
        vuln_ids = [v.vuln_id for v in manifest]
        # All IDs must be unique
        assert len(set(vuln_ids)) == 3
        # First V1 keeps its ID
        assert vuln_ids[0] == "V1"
        # Second V1 gets reassigned (becomes V2)
        assert vuln_ids[1] != "V1"
        assert vuln_ids[1] == "V2"
        # Original V2 gets bumped (V2 is taken, so becomes V3)
        assert vuln_ids[2] == "V3"

    def test_empty_vuln_ids_get_assigned(self):
        """Empty vuln_ids should get auto-assigned."""
        from src.agents.red_team_agent import RedTeamAgent

        agent = RedTeamAgent.__new__(RedTeamAgent)
        agent.logger = MagicMock()

        json_str = json.dumps({
            "injected_vulnerabilities": [
                {"vuln_id": "", "title": "First vuln"},
                {"vuln_id": "", "title": "Second vuln"},
            ]
        })

        manifest = agent._parse_manifest_json(json_str)

        assert len(manifest) == 2
        vuln_ids = [v.vuln_id for v in manifest]
        assert len(set(vuln_ids)) == 2  # All unique
        assert all(v.startswith("V") for v in vuln_ids)

    def test_unique_vuln_ids_unchanged(self):
        """Already-unique vuln_ids should pass through unchanged."""
        from src.agents.red_team_agent import RedTeamAgent

        agent = RedTeamAgent.__new__(RedTeamAgent)
        agent.logger = MagicMock()

        json_str = json.dumps({
            "injected_vulnerabilities": [
                {"vuln_id": "V1", "title": "First"},
                {"vuln_id": "V2", "title": "Second"},
                {"vuln_id": "V3", "title": "Third"},
            ]
        })

        manifest = agent._parse_manifest_json(json_str)

        assert len(manifest) == 3
        assert [v.vuln_id for v in manifest] == ["V1", "V2", "V3"]

    def test_missing_vuln_id_key_gets_assigned(self):
        """Vulnerabilities without vuln_id key should get auto-assigned."""
        from src.agents.red_team_agent import RedTeamAgent

        agent = RedTeamAgent.__new__(RedTeamAgent)
        agent.logger = MagicMock()

        json_str = json.dumps({
            "injected_vulnerabilities": [
                {"title": "No ID vuln", "resource_name": "bucket"},
            ]
        })

        manifest = agent._parse_manifest_json(json_str)

        assert len(manifest) == 1
        assert manifest[0].vuln_id.startswith("V")
        assert manifest[0].vuln_id != ""
