"""Tests for the dual-engine decorator and engine-mode reporting.

All tests pass whether or not the tree-sitter optional dependency is installed.
"""
import importlib
import logging

import pytest

from Asgard.Heimdall.treesitter import ast_engine
from Asgard.Heimdall.treesitter import _language_loader
from Asgard.Heimdall.treesitter.ast_engine import (
    engine_status,
    is_engine_enabled,
    log_engine_mode,
    reset_engine_mode_logged,
    with_ast_fallback,
    REGEX_MODE_MESSAGE,
)
from Asgard.Heimdall.treesitter.file_context import FileParseContext


class _FakeNode:
    pass


def _fake_ctx(root=None):
    ctx = FileParseContext(file_path="x.py", language="python")
    ctx.root = root
    return ctx


def _make_rule(ast_result=None, ast_raises=False):
    calls = {"ast": 0, "regex": 0}

    def ast_impl(file_path, ctx):
        calls["ast"] += 1
        if ast_raises:
            raise RuntimeError("boom")
        return ast_result if ast_result is not None else [{"engine": "ast"}]

    @with_ast_fallback("python", ast_impl)
    def rule(file_path, lines, enabled=True, **kwargs):
        calls["regex"] += 1
        return [{"engine": "regex"}]

    return rule, calls


# ---------------------------------------------------------------------------
# with_ast_fallback
# ---------------------------------------------------------------------------

def test_disabled_rule_returns_empty():
    rule, calls = _make_rule()
    assert rule("x.py", ["a"], False) == []
    assert calls == {"ast": 0, "regex": 0}


def test_regex_path_when_engine_unavailable(monkeypatch):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", False)
    rule, calls = _make_rule()
    result = rule("x.py", ["a"], True)
    assert result == [{"engine": "regex"}]
    assert calls["ast"] == 0


def test_ast_path_with_provided_context(monkeypatch):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", True)
    monkeypatch.setattr(_language_loader, "is_available", lambda lang: True)
    rule, calls = _make_rule()
    result = rule("x.py", ["a"], True, parse_context=_fake_ctx(root=_FakeNode()))
    assert result == [{"engine": "ast"}]
    assert calls["regex"] == 0


def test_ast_failure_falls_back_to_regex(monkeypatch):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", True)
    monkeypatch.setattr(_language_loader, "is_available", lambda lang: True)
    rule, calls = _make_rule(ast_raises=True)
    result = rule("x.py", ["a"], True, parse_context=_fake_ctx(root=_FakeNode()))
    assert result == [{"engine": "regex"}]
    assert calls["ast"] == 1 and calls["regex"] == 1


def test_context_without_tree_uses_regex(monkeypatch):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", True)
    monkeypatch.setattr(_language_loader, "is_available", lambda lang: True)
    rule, calls = _make_rule()
    result = rule("x.py", ["a"], True, parse_context=_fake_ctx(root=None))
    assert result == [{"engine": "regex"}]
    assert calls["ast"] == 0


def test_decorator_exposes_both_impls():
    rule, _ = _make_rule()
    assert callable(rule.__ast_impl__)
    assert callable(rule.__regex_impl__)
    assert rule.__ast_language__ == "python"
    assert rule.__engine__ == "dual"


def test_dual_engine_fixture_runs_both_modes(dual_engine_mode):
    assert dual_engine_mode in ("regex", "ast")
    if dual_engine_mode == "regex":
        assert ast_engine.TS_AVAILABLE is False
    else:
        assert is_engine_enabled("python")


# ---------------------------------------------------------------------------
# is_engine_enabled / engine_status
# ---------------------------------------------------------------------------

def test_is_engine_enabled_false_when_ts_disabled(monkeypatch):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", False)
    assert is_engine_enabled("python") is False


def test_is_engine_enabled_never_raises():
    for lang in ("python", "cobol_9000", "", None):
        try:
            is_engine_enabled(lang)
        except TypeError:
            pass  # None is acceptable to reject loudly only via TypeError


def test_engine_status_shape():
    status = engine_status()
    assert status["engine"] in ("ast", "regex")
    assert isinstance(status["tree_sitter_available"], bool)
    assert isinstance(status["languages"], list)


# ---------------------------------------------------------------------------
# log_engine_mode — single INFO line per process
# ---------------------------------------------------------------------------

def test_log_engine_mode_emits_single_info_when_unavailable(monkeypatch, caplog):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", False)
    reset_engine_mode_logged()
    with caplog.at_level(logging.INFO, logger="Asgard.Heimdall.treesitter"):
        log_engine_mode()
        log_engine_mode()
    messages = [r.message for r in caplog.records if r.message == REGEX_MODE_MESSAGE]
    assert len(messages) == 1
    reset_engine_mode_logged()


def test_log_engine_mode_silent_when_available(monkeypatch, caplog):
    monkeypatch.setattr(ast_engine, "TS_AVAILABLE", True)
    reset_engine_mode_logged()
    with caplog.at_level(logging.INFO, logger="Asgard.Heimdall.treesitter"):
        log_engine_mode()
    assert all(r.message != REGEX_MODE_MESSAGE for r in caplog.records)
    reset_engine_mode_logged()


# ---------------------------------------------------------------------------
# Per-rule engine registry (Plan 01 Phase D)
# ---------------------------------------------------------------------------

def test_register_regex_only_and_rule_engine_status():
    ast_engine.register_regex_only("test.lexical_rule", reason="Regex optimal (lexical)")
    try:
        rules = ast_engine.rule_engine_status()
        info = rules["test.lexical_rule"]
        assert info["engine"] == "regex"
        assert info["active_engine"] == "regex"
        assert info["language"] is None
        assert "lexical" in info["reason"]
    finally:
        ast_engine._RULE_REGISTRY.pop("test.lexical_rule", None)


def test_dual_rule_auto_registers_and_degrades_when_ts_disabled(monkeypatch):
    def _ast_impl(file_path, ctx):
        return []

    @with_ast_fallback("python", _ast_impl)
    def my_dual_rule_for_registry(file_path, lines, enabled=True, **kwargs):
        return []

    try:
        rules = ast_engine.rule_engine_status()
        info = rules["my_dual_rule_for_registry"]
        assert info["engine"] == "dual"
        assert info["language"] == "python"
        assert info["active_engine"] in ("ast", "regex")

        monkeypatch.setattr(ast_engine, "TS_AVAILABLE", False)
        assert ast_engine.rule_engine_status()["my_dual_rule_for_registry"]["active_engine"] == "regex"
    finally:
        ast_engine._RULE_REGISTRY.pop("my_dual_rule_for_registry", None)


def test_rule_engine_status_deterministic_order():
    ast_engine.register_regex_only("zz.rule")
    ast_engine.register_regex_only("aa.rule")
    try:
        keys = list(ast_engine.rule_engine_status().keys())
        assert keys == sorted(keys)
    finally:
        ast_engine._RULE_REGISTRY.pop("zz.rule", None)
        ast_engine._RULE_REGISTRY.pop("aa.rule", None)


def test_engine_status_includes_rules_map():
    status = engine_status()
    assert isinstance(status["rules"], dict)


#: Every intentionally-unmigrated (AST-Migration-Skipped) module and the rule
#: name it registers.  Importing the module must self-register it.
_REGEX_ONLY_MODULES = [
    ("Asgard.Heimdall.Security.services._secret_patterns", "secrets.hardcoded_patterns"),
    ("Asgard.Heimdall.Security.services._requirements_parser", "dependencies.requirements_parser"),
    ("Asgard.Heimdall.Security.services._crypto_patterns", "crypto.crypto_patterns"),
    ("Asgard.Heimdall.Security.services._injection_patterns", "injection.regex_patterns"),
    ("Asgard.Heimdall.Security.services._supply_chain_analysis", "dependencies.supply_chain"),
    ("Asgard.Heimdall.Security.Access.services.control_analyzer", "access.control_analyzer"),
    ("Asgard.Heimdall.Security.Access.services.permission_analyzer", "access.permission_analyzer"),
    ("Asgard.Heimdall.Security.API.services.api_scanner", "api.api_scanner"),
    ("Asgard.Heimdall.Security.Auth.services._jwt_patterns", "auth.jwt_patterns"),
    ("Asgard.Heimdall.Security.Auth.services._password_patterns", "auth.password_patterns"),
    ("Asgard.Heimdall.Security.Auth.services.session_analyzer", "auth.session_analyzer"),
    ("Asgard.Heimdall.Security.Backdoor.services.backdoor_detector", "backdoor.backdoor_detector"),
    ("Asgard.Heimdall.Security.Container.services._dockerfile_patterns", "container.dockerfile_patterns"),
    ("Asgard.Heimdall.Security.DataExfil.services.data_exfil_detector", "dataexfil.data_exfil_detector"),
    ("Asgard.Heimdall.Security.Deserialization.services.deserialization_scanner", "deserialization.deserialization_scanner"),
    ("Asgard.Heimdall.Security.Frontend.services.frontend_scanner", "frontend.frontend_scanner"),
    ("Asgard.Heimdall.Security.Headers.services._cors_patterns", "headers.cors_patterns"),
    ("Asgard.Heimdall.Security.Headers.services._header_patterns", "headers.header_patterns"),
    ("Asgard.Heimdall.Security.Hotspots.services._regex_hotspot_checks", "hotspots.regex_hotspot_checks"),
    ("Asgard.Heimdall.Security.InfoDisclosure.services.info_disclosure_scanner", "infodisclosure.info_disclosure_scanner"),
    ("Asgard.Heimdall.Security.Infrastructure.services._config_patterns", "infrastructure.config_patterns"),
    ("Asgard.Heimdall.Security.Infrastructure.services._credential_patterns", "infrastructure.credential_patterns"),
    ("Asgard.Heimdall.Security.Infrastructure.services._hardening_patterns", "infrastructure.hardening_patterns"),
    ("Asgard.Heimdall.Security.InputValidation.services.input_validation_scanner", "inputvalidation.input_validation_scanner"),
    ("Asgard.Heimdall.Security.LogAnalysis.services.log_analyzer", "loganalysis.log_analyzer"),
    ("Asgard.Heimdall.Security.Malware.services.malware_scanner", "malware.malware_scanner"),
    ("Asgard.Heimdall.Security.Misconfig.services.misconfig_scanner", "misconfig.misconfig_scanner"),
    ("Asgard.Heimdall.Security.PathTraversal.services.path_traversal_scanner", "pathtraversal.path_traversal_scanner"),
    ("Asgard.Heimdall.Security.RaceCondition.services.race_condition_detector", "racecondition.race_condition_detector"),
    ("Asgard.Heimdall.Security.ReDoS.services.redos_scanner", "redos.redos_scanner"),
    ("Asgard.Heimdall.Security.SensitiveData.services.sensitive_data_scanner", "sensitivedata.sensitive_data_scanner"),
    ("Asgard.Heimdall.Security.SSRF.services.ssrf_scanner", "ssrf.ssrf_scanner"),
    ("Asgard.Heimdall.Security.TLS.services._certificate_patterns", "tls.certificate_patterns"),
    ("Asgard.Heimdall.Security.TLS.services._cipher_patterns", "tls.cipher_patterns"),
    ("Asgard.Heimdall.Security.TLS.services._protocol_patterns", "tls.protocol_patterns"),
    ("Asgard.Heimdall.Security.TLS.services.tls_config_analyzer", "tls.config_analyzer"),
]


@pytest.mark.parametrize("module_name,rule_name", _REGEX_ONLY_MODULES)
def test_lexical_modules_register_as_regex_only(module_name, rule_name):
    importlib.import_module(module_name)
    rules = ast_engine.rule_engine_status()
    assert rule_name in rules
    info = rules[rule_name]
    assert info["engine"] == "regex"
    assert info["active_engine"] == "regex"
    assert info["language"] is None
    assert isinstance(info["reason"], str) and info["reason"]


def test_regex_only_registrations_do_not_shadow_dual_rules():
    for module_name, _ in _REGEX_ONLY_MODULES:
        importlib.import_module(module_name)
    import Asgard.Heimdall.Security.services._ast_python_rules  # noqa: F401
    rules = ast_engine.rule_engine_status()
    assert rules["check_eval_exec"]["engine"] == "dual"
    regex_names = {name for m, name in _REGEX_ONLY_MODULES}
    dual_names = {n for n, i in rules.items() if i["engine"] == "dual"}
    assert not (regex_names & dual_names)
