"""Dual-engine (Strangler-Fig) infrastructure: AST rule with regex fallback.

The ``@with_ast_fallback`` decorator lets a rule ship an AST implementation
*additively* on top of its existing regex implementation:

- tree-sitter installed and parse succeeded  → AST implementation runs;
- tree-sitter missing / grammar missing / parse or rule failure → the
  original regex implementation runs, byte-for-byte unchanged.

Tree-sitter is an optional extra (``pip install asguardian[ast]``).  When it
is unavailable, scanning continues in regex mode and a single INFO line is
emitted per process.
"""
import functools
import logging

from Asgard.Heimdall.treesitter import _language_loader
from Asgard.Heimdall.treesitter.file_context import FileParseContext

logger = logging.getLogger("Asgard.Heimdall.treesitter")

#: True when at least one tree-sitter grammar loaded.  Tests may monkeypatch
#: this to False to force the regex engine (dual-engine parametrized fixture).
TS_AVAILABLE: bool = bool(_language_loader.get_supported_languages())

REGEX_MODE_MESSAGE = "Regex mode. Install 'asguardian[ast]' for AST-precision scanning."

_engine_mode_logged = False

#: Per-rule engine registry (Plan 01 Phase D).  Dual-engine rules register
#: automatically via :func:`with_ast_fallback`; intentionally-unmigrated
#: lexical rules register via :func:`register_regex_only` so users can see
#: which rules are AST-backed and which stay regex by design.
_RULE_REGISTRY: dict = {}


def register_regex_only(rule_name: str, reason: str = "Regex optimal (lexical)") -> None:
    """Record a rule that intentionally stays regex (AST-Migration-Skipped)."""
    _RULE_REGISTRY[rule_name] = {
        "engine": "regex",
        "language": None,
        "reason": reason,
    }


def _register_dual(rule_name: str, language: str) -> None:
    _RULE_REGISTRY[rule_name] = {
        "engine": "dual",
        "language": language,
        "reason": None,
    }


def rule_engine_status() -> dict:
    """Per-rule engine map: rule name -> engine info (deterministic order).

    ``active_engine`` reports what actually runs for that rule right now:
    a dual rule degrades to regex when its language's grammar is missing.
    """
    out = {}
    for name in sorted(_RULE_REGISTRY):
        info = dict(_RULE_REGISTRY[name])
        if info["engine"] == "dual":
            info["active_engine"] = (
                "ast" if is_engine_enabled(info["language"]) else "regex"
            )
        else:
            info["active_engine"] = "regex"
        out[name] = info
    return out


def is_engine_enabled(language: str) -> bool:
    """True when the AST engine can be used for *language*."""
    return bool(TS_AVAILABLE) and _language_loader.is_available(language)


def log_engine_mode() -> None:
    """Emit the one-per-process INFO line when running without tree-sitter."""
    global _engine_mode_logged
    if _engine_mode_logged:
        return
    _engine_mode_logged = True
    if not TS_AVAILABLE:
        logger.info(REGEX_MODE_MESSAGE)


def reset_engine_mode_logged() -> None:
    """Test helper: allow :func:`log_engine_mode` to fire again."""
    global _engine_mode_logged
    _engine_mode_logged = False


def engine_status() -> dict:
    """Machine-readable engine status (for reports/profiles metadata)."""
    languages = sorted(_language_loader.get_supported_languages())
    return {
        "engine": "ast" if TS_AVAILABLE else "regex",
        "tree_sitter_available": bool(TS_AVAILABLE),
        "languages": languages if TS_AVAILABLE else [],
        "rules": rule_engine_status(),
    }


def with_ast_fallback(language: str, ast_impl):
    """Wrap a regex rule with an AST implementation and graceful fallback.

    The decorated (regex) rule keeps its signature
    ``(file_path, lines, enabled=True, **kwargs)`` and behaviour.  The AST
    implementation has signature ``(file_path, ctx: FileParseContext)``.

    Orchestrators that already parsed the file pass the context via
    ``kwargs["parse_context"]`` (single parse per file per scan); otherwise
    the wrapper parses on demand when the engine is available.
    """

    def decorator(regex_impl):
        @functools.wraps(regex_impl)
        def wrapper(file_path, lines, enabled=True, **kwargs):
            if not enabled:
                return []
            ctx = kwargs.pop("parse_context", None)
            if ctx is None and is_engine_enabled(language):
                ctx = FileParseContext.parse(file_path, lines, language)
            if ctx is not None and getattr(ctx, "root", None) is not None and is_engine_enabled(language):
                try:
                    return ast_impl(file_path, ctx)
                except Exception:
                    logger.debug(
                        "AST rule %s failed on %s; regex fallback",
                        regex_impl.__name__, file_path,
                    )
            return regex_impl(file_path, lines, enabled, **kwargs)

        wrapper.__ast_impl__ = ast_impl
        wrapper.__regex_impl__ = regex_impl
        wrapper.__ast_language__ = language
        wrapper.__engine__ = "dual"
        _register_dual(regex_impl.__name__, language)
        return wrapper

    return decorator
