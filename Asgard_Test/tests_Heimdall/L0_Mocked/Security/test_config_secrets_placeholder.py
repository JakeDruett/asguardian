"""CH-0083: config-secrets placeholders must not drop real credentials."""

from pathlib import Path

import pytest
import yaml

from Asgard.Heimdall.Security.services._config_secrets_helpers import (
    MAX_FLATTEN_DEPTH,
    PLACEHOLDER_FRAGMENTS,
    flatten_dict,
    is_placeholder,
)
from Asgard.Heimdall.Security.services.config_secrets_scanner import ConfigSecretsScanner

_ANGLE_PASSWORD = "p@ss<word"


def _password_keys(report) -> set[str]:
    return {finding.key_name for finding in report.detected_findings}


class TestPlaceholderFragments:
    def test_bare_angle_bracket_is_not_a_fragment(self):
        assert "<" not in PLACEHOLDER_FRAGMENTS

    @pytest.mark.parametrize(
        "value",
        [
            "${DB_PASSWORD}",
            "{{password}}",
            "<password>",
            "changeme",
            "TODO",
            "replace_me",
            "example",
            "placeholder",
            "insert_here",
            "your-password",
            "your_api_key",
            "xxxxx",
            "00000",
            "",
        ],
    )
    def test_placeholder_shaped_tokens_are_dropped(self, value):
        assert is_placeholder(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            _ANGLE_PASSWORD,
            "mytodo",
            "notanexample",
            "reinserted",
            "ContestWinner1",
            "foo<bar>baz",
        ],
    )
    def test_real_secrets_are_not_placeholders(self, value):
        assert is_placeholder(value) is False


class TestFlattenDictBounds:
    def test_cyclic_mapping_terminates_and_yields_secret(self):
        data = {"password": _ANGLE_PASSWORD}
        data["child"] = data
        leaves = list(flatten_dict(data))
        assert any(key == "password" and value == _ANGLE_PASSWORD for _, key, value in leaves)
        assert len(leaves) == 1

    def test_depth_cap_stops_recursion(self):
        node: dict = {"password": "deep-secret-value-01"}
        for _ in range(MAX_FLATTEN_DEPTH + 8):
            node = {"child": node}
        leaves = list(flatten_dict(node, max_depth=MAX_FLATTEN_DEPTH))
        assert leaves == []
        shallow = list(flatten_dict({"password": _ANGLE_PASSWORD}, max_depth=MAX_FLATTEN_DEPTH))
        assert shallow == [("password", "password", _ANGLE_PASSWORD)]


class TestConfigSecretsScannerPlaceholder:
    def test_angle_bracket_password_is_reported(self, tmp_path: Path):
        (tmp_path / "settings.yaml").write_text(
            f"database:\n  password: {_ANGLE_PASSWORD}\n",
            encoding="utf-8",
        )
        report = ConfigSecretsScanner().analyze(tmp_path)
        assert "password" in _password_keys(report)

    def test_cyclic_yaml_does_not_hang_and_reports_secret(self, tmp_path: Path):
        yaml_text = (
            "root: &cycle\n"
            f"  password: {_ANGLE_PASSWORD}\n"
            "  child: *cycle\n"
        )
        loaded = yaml.safe_load(yaml_text)
        assert loaded["root"]["child"] is loaded["root"]
        target = tmp_path / "loop.yaml"
        target.write_text(yaml_text, encoding="utf-8")
        report = ConfigSecretsScanner().analyze(target)
        assert report.files_scanned == 1
        assert "password" in _password_keys(report)
