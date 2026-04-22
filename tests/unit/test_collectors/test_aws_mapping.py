"""Tests for the NIST mapping helpers in evidentia_collectors.aws.mapping."""

from __future__ import annotations

import pytest
from evidentia_collectors.aws.mapping import (
    map_config_rule_to_controls,
    map_security_hub_control_to_controls,
)


class TestConfigRuleMapping:
    @pytest.mark.parametrize(
        "rule, expected",
        [
            ("s3-bucket-public-read-prohibited", ["AC-3", "AC-6"]),
            ("cloudtrail-enabled", ["AU-2", "AU-3", "AU-12"]),
            ("iam-user-mfa-enabled", ["IA-2"]),
            ("encrypted-volumes", ["SC-28"]),
        ],
    )
    def test_known_rules(self, rule: str, expected: list[str]) -> None:
        assert map_config_rule_to_controls(rule) == expected

    def test_case_insensitive_normalization(self) -> None:
        hyphen = map_config_rule_to_controls("s3-bucket-public-read-prohibited")
        camel = map_config_rule_to_controls("S3BucketPublicReadProhibited")
        assert camel == hyphen

    def test_unknown_rule_returns_empty(self) -> None:
        assert map_config_rule_to_controls("custom-rule-xyz-never-registered") == []

    def test_empty_input_returns_empty(self) -> None:
        assert map_config_rule_to_controls("") == []

    def test_underscores_and_hyphens_normalize_the_same(self) -> None:
        dashed = map_config_rule_to_controls("iam-password-policy")
        underscored = map_config_rule_to_controls("iam_password_policy")
        assert dashed == underscored

    def test_mapping_returns_new_list_each_call(self) -> None:
        """Mutating a returned list must not corrupt the source table."""
        first = map_config_rule_to_controls("iam-user-mfa-enabled")
        first.append("POLLUTION")
        second = map_config_rule_to_controls("iam-user-mfa-enabled")
        assert "POLLUTION" not in second


class TestSecurityHubMapping:
    def test_cis_id_normalizes_with_cis_prefix(self) -> None:
        # Raw ingest: "1.4" -> cis.1.4 -> [AC-6, IA-2]
        controls = map_security_hub_control_to_controls("1.4")
        assert "AC-6" in controls
        assert "IA-2" in controls

    def test_fsbp_id_normalizes_with_fsbp_prefix(self) -> None:
        controls = map_security_hub_control_to_controls("S3.3")
        assert controls == ["AC-3"]

    def test_prefixed_id_passes_through(self) -> None:
        controls = map_security_hub_control_to_controls("fsbp.iam.6")
        assert controls == ["IA-2"]

    def test_unknown_returns_empty(self) -> None:
        assert map_security_hub_control_to_controls("unknown.99.99") == []

    def test_case_insensitive(self) -> None:
        lower = map_security_hub_control_to_controls("s3.3")
        upper = map_security_hub_control_to_controls("S3.3")
        assert lower == upper
