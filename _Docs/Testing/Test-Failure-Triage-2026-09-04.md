# Test Failure Triage — 2026-09-04

Session scope: `tests_Bragi` + `tests_Heimdall` (excluding the network-dependent
`tests_Heimdall/L14_Industry`). Baseline measured at session start: ~23 failed /
~4515 passed / ~247 skipped.

## Summary

| Cluster | Root cause | Classification | Disposition |
|---|---|---|---|
| C pointer taint analysis (SA3) | `tree-sitter` / `tree-sitter-c` not installed | Environment artefact | Installed the `treesitter` extra. All 10 tests now pass — **no detection bug**. |
| Multilang CLI wiring (JS/TS/Java) | Same — `tree-sitter` not installed | Environment artefact | Fixed by the same install. |
| Legacy scanner compliance (L5) | Same — `tree-sitter` not installed | Environment artefact | Fixed by the same install. |
| SBOM generator (3 tests) | Tests pre-date the real transitive-closure feature (Plan 03 Phase C) and assumed zero closure | Test-side defect | Updated 3 tests to pass `SBOMConfig(include_transitive=False)`, matching what they actually exercise (dedup / purl / editable-install skip), independent of what the sandbox happens to have installed. |
| Debt-state-store, incremental-cache, differential-gate, `_hash_cache` incremental mixin | **Real product bug**: HMAC signing key for the on-disk cache was regenerated with `os.urandom(32)` on every call/instance and never persisted, so a signature written by one `save()` could never be verified by a later, separate `load()`. Every affected cache silently treated *every* run as a cold cache (or refused to load) unless a caller manually set an env-var key. `_key_path()` methods existed in 3 of the 4 files but were dead code — never called. | Real bug (cache never round-trips) | Implemented the sibling `.key` file persistence the docstrings already promised (`0o600`, symlink-guarded, `O_NOFOLLOW`) in all 4 affected modules. Verified via the existing `TestHmacPersistence` / round-trip tests, which now pass. |
| L14 NodeGoat JS `test_xss_detected` | **Real, documented detection-scope gap** (see below) — not fixed | Real bug / known scanner limitation | Left failing; documented, not weakened. |

## C pointer taint analysis — priority item, verified NOT a detection bug

`is_engine_enabled("c")` was `False` because `tree-sitter` and `tree-sitter-c`
were not installed in this sandbox (`pip show tree-sitter` -> not found). With
the engine disabled, `DispatchEngine._scan_cst_language` correctly took its
documented degrade path — return no flows and set `analysis_truncated=True` —
which is the *safe* behaviour the sound-over-approximation invariant demands
(never silently claim "clean"; the caller must not read an empty result as
"no vulnerabilities"). This is exactly working as designed for the
missing-grammar case; it is an environment artefact, not a false negative in
the points-to engine itself.

Fix: `pip install -e ".[treesitter]"` (already declared in `pyproject.toml`;
PyPI was reachable in this sandbox). After install, all 10
`test_taint_sa3_c_points_to.py` tests pass, including the double/triple
pointer dereference, struct-pointer alias-group canonical-root migration,
array-decay aliasing, and the "unresolved pointer never mutes" adversarial
regressions. **No change was made to the taint engine itself** — the SA3
points-to logic was correct; only the environment was missing the optional
`[ast]`/`[treesitter]` extra.

Same root cause fixed, in the same commit, the `test_cli_multilang_wiring.py`
(JS/TS/Java dispatch) and `test_legacy_scanner_compliance.py` failures.

## SBOM generator — test-side defect, not a product bug

`SBOMGenerator.generate()` legitimately resolves the full **installed**
transitive closure by default (`SBOMConfig.include_transitive=True`,
"Plan 03 Phase C") — this is intentional, accurate-SBOM behaviour, and is
exercised correctly by `test_generate_with_requirements_txt` in the same
file. Three older tests (`test_generate_deduplicates_components`,
`test_generate_component_has_purl`, `test_generate_skips_editable_installs`)
were written before the closure feature landed and asserted
`total_components == 1` for a single declared root. Because `requests`
happens to be pip-installed in this sandbox (with `certifi`/`idna`/
`urllib3`/`charset_normalizer` as real transitive deps), the closure walk
correctly added 4 more components and the stale assertion broke. These three
tests were not actually testing closure behaviour — they test dedup-on-
declared-roots, purl formatting, and `-e` editable-line skipping — so they
were updated to pass `SBOMConfig(include_transitive=False)`, isolating them
from both the closure feature and from what happens to be installed in any
given environment.

## The persisted-HMAC-key bug (debt-state-store / incremental-cache / differential-gate)

Four files shared the identical anti-pattern:

```python
def _hmac_key(self) -> bytes:
    ...
    if getattr(self, "_ephemeral_hmac", None) is None:
        self._ephemeral_hmac = os.urandom(32)
    return self._ephemeral_hmac
```

`self._ephemeral_hmac` lives only on the Python object. A `save()` call
signs the cache file with one random key; a `load()` call from a *different*
instance (a different process, or even a fresh object in the same test) asks
for a fresh `_hmac_key()`, gets a *different* random key, and the HMAC
comparison in `load()`/`load_state()`/`_read_all()` always fails — so the
cache is always treated as absent/corrupt and the caller always does a full,
uncached rescan. Three of the four files even had a `_key_path()` method
already defined for exactly the sibling-`.key`-file persistence their own
docstrings describe, but it was dead code, never called from `_hmac_key`.

Affected, fixed in this session (all four now read-then-write a sibling
`<cache-file>.key` at `0o600`, `O_NOFOLLOW`-guarded, matching the pattern the
docstrings already promised):

- `Asgard/Bragi/Quality/services/_debt_state_store.py`
- `Asgard/Bragi/Quality/services/_incremental_cache.py`
- `Asgard/Bragi/QualityGate/baseline_store.py`
- `Asgard/common/_hash_cache.py`

This is **not** a security-detection false negative (nothing about scan
findings was affected) — it silently defeated the *performance/incrementality*
promise of four separate caching layers, always forcing a full rescan. Still
a real, user-visible correctness bug: "incremental" scanning was not
incremental across process boundaries without manually exporting an env-var
HMAC key.

### Related, NOT fixed this session — same anti-pattern found elsewhere

The same `_ephemeral_hmac = os.urandom(32)` pattern (with `_key_path()` dead
or absent) also exists in, but none of these currently have failing test
coverage to verify a fix against, so they were left untouched to avoid a
blind change:

- `Asgard/Heimdall/Security/FileIntegrity/services/file_integrity_checker.py`
- `Asgard/Heimdall/Security/triage/services/triage_cache.py`
- `Asgard/Bragi/Architecture/graph/service.py`
- `Asgard/Bragi/Dependencies/services/_license_cache.py`
- `Asgard/Bragi/Dependencies/services/_vuln_cache.py`
- `Asgard/Bragi/Dependencies/services/graph_service.py`
- `Asgard/Baseline/baseline_manager.py`

**Follow-up recommended**: apply the same sibling-`.key`-file fix to these
seven files (ideally by extracting one shared helper instead of a fifth
copy-paste) — flagged here so it isn't lost.

## L14 NodeGoat JS `test_xss_detected` — real detection-scope gap, left failing

`TestNodeGoatJS::test_xss_detected` asserts the `JSAnalyzer` finds an
`js.xss`-rule finding somewhere in the real OWASP NodeGoat corpus
(`Asgard_Test/fixtures/nodegoat`, 25 real `.js` files, present locally — not
network-blocked).

Investigation: `js.xss` (`Asgard/Bragi/Quality/languages/javascript/services/
_js_security_rules.py::check_xss`) is a narrow, correctly-scoped regex rule
for **client-side DOM XSS**: `.innerHTML = <expr>` or `document.write(<expr>)`.
Neither pattern appears anywhere in NodeGoat's real (non-vendor) application
code — confirmed by direct grep. NodeGoat's actual, well-known XSS
vulnerability (`app/routes/profile.js`) is a **server-side, cross-context
output-encoding bug**: user-controlled `doc.website` is HTML-encoded with
`ESAPI.encoder().encodeForHTML(...)` but then rendered into a URL attribute
context inside a separate Pug template (`views/profile.pug`), i.e. the wrong
encoding function for the sink context. Detecting this requires:

1. cross-file taint from an Express route handler into a Pug/Jade template
   (the analyzer only scans `.js`, not `.pug`), and
2. context-sensitive encoding-function analysis (recognising that
   "HTML-encoded" data can still be XSS when the sink context is a URL
   attribute, not HTML body text) — well beyond what a lexical
   innerHTML/document.write regex rule was ever built to catch.

This is a genuine, real gap in JS security detection coverage (the analyzer
has no rule for server-side template-render XSS or encoding-context
confusion at all), but closing it is a real feature addition — a
template-aware taint source/sink and an encoding-context model — not a bug
fix inside a triage pass. Per the "never fake a detection test green" rule,
the test was **left failing** rather than weakened to match the tool's
current (narrower) capability, and is recorded here as a tracked, known
limitation rather than silently accepted.

## Final numbers (this session's scope)

Before: ~23 failed / ~4515 passed / ~247 skipped (network-dependent
`Heimdall/L14_Industry` excluded; ~247 skipped was itself largely an
artefact of the missing tree-sitter extra suppressing collection of
AST-dependent tests).

After: 1 known, documented failure (`TestNodeGoatJS::test_xss_detected`,
real coverage gap, tracked above) + `TestNodeGoatJS::test_open_redirect_or_
ssrf_detectable`/`test_tpr_exceeds_30pct` and `test_throughput` unaffected
(verify independently — TPR/throughput checks pass; only the specific
XSS-rule assertion fails). All other targeted clusters pass.
