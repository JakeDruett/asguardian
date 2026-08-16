# CyberHardening Plan

Status: IN PROGRESS
Started: 2026-08-16
Repo: Asgard

## Purpose

Track every security finding discovered by the full-tree traced audit, and the planned fix for each. This document is the hardening backlog, not a marketing summary.

## Method

Every inventoried code file is traced (not merely grepped). Findings include cross-file data flow, trust boundaries, and a planned fix. Files with no issue get a clean-bill entry in the ledger.

## Inventory

- Script: `scripts/cyberhardening_inventory.py`
- Todo: `_Docs/Planning/CyberHardening/todo.json`
- Ledger: `_Docs/Planning/CyberHardening/ledger.jsonl`
- Planning folder: `_Docs/Planning/` (first existing match)

## Summary

| Severity | Open | Planned | Accepted risk |
|----------|------|---------|---------------|
| Critical | 0    | 0       | 0             |
| High     | 16   | 0       | 0             |
| Medium   | 27   | 0       | 0             |
| Low      | 15   | 0       | 0             |
| Info     | 5    | 0       | 0             |

## Findings

<!-- Newest findings appended below. Never delete a finding; mark status changes in place. -->

### CH-0001 — GitHub Actions pinned to mutable tags

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-829 / supply chain
- **Primary file:** `.github/workflows/ci.yml`
- **Also on trace:** `.github/workflows/publish.yml`, `.github/workflows/l8-perf-budgets.yml`, `Asgard/Volundr/CICD/services/action_pins.py`, `Asgard_Test/tests_Volundr/golden/ci.yml`
- **Location:** every `uses:` step
- **Trace:** workflow `uses: actions/*@v4|v5` / `pypa/gh-action-pypi-publish@release/v1` → GitHub resolves a moving tag → action code runs with job token / OIDC
- **Impact:** A rewritten action tag executes in lint/test/publish. Publish path has `id-token: write`.
- **Evidence:** `ci.yml` checkout/setup-python/upload-artifact at `@v4`/`@v5`; `publish.yml` publisher at `@release/v1`. In-repo `KNOWN_ACTION_PINS` already maps the first-party actions to 40-char SHAs but workflows do not use them.
- **Planned fix:** Rewrite every `uses:` to the SHAs in `KNOWN_ACTION_PINS` with `# vX.Y.Z` comments (match `golden/ci.yml`). Add and pin `pypa/gh-action-pypi-publish`. Add Dependabot/Renovate for action pins.
- **Fix wave:** W1

### CH-0002 — Public `pull_request` jobs execute untrusted code on self-hosted `arc-x86`

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-250
- **Primary file:** `.github/workflows/ci.yml`
- **Also on trace:** `pyproject.toml`, `Asgard_Test/conftest.py`
- **Location:** jobs `lint` / `type-check` / `test` (`runs-on: arc-x86`); `pip install -e ".[test]"`; `pytest Asgard_Test/`
- **Trace:** public `pull_request` → checkout PR SHA → setuptools from the PR runs → pytest executes PR tests on the ARC node
- **Impact:** Fork/PR code gets RCE on the self-hosted fleet (persistence depends on whether ARC pods are ephemeral). `contents: read` limits the GitHub token, not the runner.
- **Evidence:** `ci.yml` `pull_request: branches: [main]`; all live jobs `runs-on: arc-x86`; `pip install -e ".[test]"`. Repo is public (`primordial-creations/asguardian`).
- **Planned fix:** Run `pull_request` on `ubuntu-latest`. Keep `arc-x86` only for `push` to `main` if needed. Require approval for outside collaborators. `persist-credentials: false`, `timeout-minutes`, and `concurrency` with cancel-in-progress. Do not install the PR package on a shared runner.
- **Fix wave:** W1

### CH-0003 — PyPI OIDC publish: floating publisher, no environment, no split-trust

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-345 / CWE-269
- **Primary file:** `.github/workflows/publish.yml`
- **Also on trace:** `pyproject.toml`, `MANIFEST.in`, `Asgard_Test/tests_Volundr/golden/ci-deploy.yml`
- **Location:** job `publish` (lines 8–29)
- **Trace:** `git push` tag `v*` → same job builds (`python -m build`) → `id-token: write` → `pypa/gh-action-pypi-publish@release/v1` uploads
- **Impact:** Compromised publisher tag, compromised build backend, or an unprotected `v*` tag publishes `asguardian` as this repo’s trusted publisher. No environment reviewers, no artifact seal, no provenance attestation.
- **Evidence:** `on.push.tags: "v*"`; `permissions: id-token: write`; no `environment:`; publisher on a movable tag. Golden deploy uses `environment: production`, SHA pins, and split trust.
- **Planned fix:** Workflow-level `permissions: {}`; job `contents: read` + `id-token: write`. `environment: pypi` with required reviewers, bound to the PyPI trusted publisher. Pin the publisher action. Split build (no OIDC) and publish (download + checksum). Add `actions/attest-build-provenance`. Restrict tags (`v[0-9].*` + ruleset). Prefer GitHub-hosted for the OIDC job.
- **Fix wave:** W1

### CH-0004 — No `timeout-minutes` on live ARC workflows

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-400
- **Primary file:** `.github/workflows/ci.yml`
- **Also on trace:** `.github/workflows/publish.yml`
- **Location:** jobs `lint`, `type-check`, `test`, `publish`
- **Trace:** PR or tag → job on `arc-x86` → no cap → pytest / `python -m build` can run until org/runner limit
- **Impact:** Runner exhaustion / lock of the labeled ARC pool. Worse with CH-0002.
- **Evidence:** Live jobs have no `timeout-minutes`. Draft L8 already sets `timeout-minutes: 20`.
- **Planned fix:** `timeout-minutes: 30` (test/lint) and `15` (publish). Add workflow `concurrency` with `cancel-in-progress: true`.
- **Fix wave:** W1

### CH-0005 — Draft L8 workflow would inherit default token and unpinned actions

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-250 / CWE-829 (latent)
- **Primary file:** `.github/workflows/l8-perf-budgets.yml`
- **Also on trace:** `_Docs/Testing/L8_Perf_Budget_Policy.md`
- **Location:** job `l8-budgets` (`if: false`)
- **Trace:** Removal of `if: false` → `pull_request` / `workflow_dispatch` → default GITHUB_TOKEN + unpinned actions + `pip install -e .`
- **Impact:** Enabling the draft (documented as a pending switch) ships a PR-triggered workflow that fails the repo’s own VOL-CICD-0001/0002 checks. No current runtime impact.
- **Evidence:** Header “DRAFT — NOT YET ENABLED”; `if: false`; unpinned `checkout@v4` / `setup-python@v5`; no `permissions:`.
- **Planned fix:** Before flipping `if: false`: `permissions: contents: read`, SHA-pin actions, `persist-credentials: false`, keep `ubuntu-latest` and `timeout-minutes`.
- **Fix wave:** W1

### CH-0006 — Pre-commit pins are movable tags; no secret-scan hook

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-829
- **Primary file:** `.pre-commit-config.yaml`
- **Also on trace:** `Asgard/HooksSetup/service.py`, `Asgard/Shared/Init/_templates_python.py`
- **Location:** `repos[].rev`; hook list
- **Trace:** `asguardian setup-hooks` → `pre-commit install` → clone tag revs → run locally only. CI does not execute this file.
- **Impact:** A moved hook tag or floating `pydantic>=2` / `pyyaml>=6` extra can execute on developer machines. Secrets are not scanned at commit time.
- **Evidence:** `rev: v5.0.0` / `v0.8.6` / `v1.14.1`; no detect-secrets/gitleaks; `_Docs/Planning/Jake-todo.md` notes GitHub secret scanning still off.
- **Planned fix:** Pin each `rev` to a full commit SHA. Pin `additional_dependencies` with `==`. Add detect-secrets or gitleaks. Optionally `pre-commit run --all-files` in CI.
- **Fix wave:** W1

### CH-0007 — `init-backend` writes outside the intended base directory

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/BackendInit/service.py`
- **Also on trace:** `Asgard/_cli_handlers.py` (`handle_init_backend`), `Asgard/cli.py` (`folder_name`)
- **Location:** `init_backend` — `root = (base_dir or Path.cwd()) / folder_name`
- **Trace:** argv `folder_name` → `handle_init_backend` → `init_backend` → `Path.__truediv__` → `mkdir` / `_write_if_absent` / `_ensure_gitignore`
- **Impact:** Absolute `folder_name` or `..` segments create the scaffold tree anywhere the process can write. Existing files are not overwritten, but new files are added and `.gitignore` may be merged.
- **Evidence:** No `is_absolute` / `..` / `is_relative_to` check. Tests only use names like `"proj"`.
- **Planned fix:** Reject empty/`.`/`..`, separators, and absolute names; `resolve()` `root` and require `root.is_relative_to((base_dir or Path.cwd()).resolve())`; return 1 on error. Tests for absolute, `..`, nested `a/../../b`, empty string.
- **Fix wave:** W2

### CH-0008 — BackendInit `.gitignore` merge follows symlinks

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-59
- **Primary file:** `Asgard/BackendInit/service.py`
- **Also on trace:** `Asgard/BackendInit/templates.py`
- **Location:** `_ensure_gitignore` / `_write_if_absent`
- **Trace:** `init_backend` → `_ensure_gitignore(root / ".gitignore")`. If the path is a symlink, pathlib writes the target. Combined with CH-0007 this can append to an arbitrary writable file.
- **Impact:** Integrity of a non-gitignore target. Not remote RCE.
- **Evidence:** No `is_symlink` / `O_NOFOLLOW`. Tests never plant a symlink.
- **Planned fix:** Skip or error if `path.is_symlink()`. Test that a symlink `.gitignore` does not change the link target.
- **Fix wave:** W2

### CH-0009 — Generated `GITIGNORE_FULL` ignores real source trees

- **Status:** Open
- **Severity:** Info
- **Confidence:** High
- **CWE / class:** CWE-693 adjacent
- **Primary file:** `Asgard/BackendInit/templates.py`
- **Also on trace:** `Asgard/BackendInit/service.py`
- **Location:** `GITIGNORE_FULL` entries `lib/`, `lib64/`, `env/`
- **Trace:** New projects get the full template via `_ensure_gitignore` when `.gitignore` is absent.
- **Impact:** Legitimate `lib/` or `env/` packages can be silently untracked.
- **Evidence:** Those names are not in `GITIGNORE_ENTRIES` (only `.claude`, `Claude Team`, `.env`).
- **Planned fix:** Drop or comment `lib/`, `lib64/`, `env/` in `GITIGNORE_FULL`. Update the template-equality test.
- **Fix wave:** W5

### CH-0010 — Unconfined `baseline_path` join

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Baseline/baseline_manager.py`
- **Also on trace:** `Asgard/Heimdall/cli/handlers/baseline.py`, `Asgard/Heimdall/cli/common/scan_args.py`
- **Location:** `BaselineManager.__init__` (`project_path / baseline_file`); `load` / `save`
- **Trace:** CLI `--baseline-file` → `BaselineManager` → absolute RHS replaces base, `..` walks out → `open` read/write
- **Impact:** Read/parse any readable file; write if `save()` runs (`create_from_violations` always saves; CLI `clean`/`remove` save on mutate).
- **Evidence:** `self.baseline_path = self.project_path / self.baseline_file` with no confinement.
- **Planned fix:** After join, `resolved = baseline_path.resolve()`; require `resolved.is_relative_to(project_path.resolve())`; reject absolute `baseline_file` before `open`.
- **Fix wave:** W2

### CH-0011 — Unsigned baseline is a suppression oracle

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Baseline/models.py`
- **Also on trace:** `Asgard/Baseline/baseline_manager.py` (`json.load` + `BaselineFile(**data)`), `Asgard/Baseline/_baseline_operations.py`
- **Location:** `BaselineEntry.matches` (path + line + type only)
- **Trace:** attacker/PR writes `.asgard-baseline.json` → `load` trusts it → `filter_violations` → `find_match` drops the finding even if message/code changed
- **Impact:** A CI/gate that calls `filter_violations` can be gamed: one entry per `file:line:type` hides any new issue at that locus.
- **Evidence:** `matches` ignores `message` and `violation_id`. No HMAC/signature field.
- **Planned fix:** Include `message` or `violation_id` in `matches`. Optional sidecar HMAC of canonical JSON. Treat load-hash mismatch as fail-closed for gates.
- **Fix wave:** W3

### CH-0012 — Fuzzy match with empty message suppresses a whole file+type

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-184
- **Primary file:** `Asgard/Baseline/_baseline_operations.py`
- **Also on trace:** `Asgard/Baseline/_baseline_helpers.py` (`get_violation_message`), `Asgard/Baseline/models.py` (`matches_fuzzy`), `Asgard/Heimdall/Security/models/security_models_base.py` (`SecretFinding`)
- **Location:** `filter_violations` fuzzy path; `get_violation_message`
- **Trace:** `create_from_violations(secret_findings, "heimdall_secret")` stores `message=""` → later `filter_violations(..., use_fuzzy_matching=True)` → `find_fuzzy_match(path, type, "")` matches every same-file/type finding
- **Impact:** One baselined secret (or any object without `message`/`description`/`import_statement`/`code_snippet`) hides all later findings of that type in that file when fuzzy is on. Default is off; the flag is public.
- **Evidence:** `get_violation_message` returns `""` when none of those attrs exist. `SecretFinding` has none of them.
- **Planned fix:** If fuzzy and `not message.strip()`, treat as unmatched. Prefer a stable non-empty key (`pattern_name` + masked value / `violation_id`). Refuse to persist empty messages that fuzzy could use.
- **Fix wave:** W3

### CH-0013 — Raw violation text persisted and dumped

- **Status:** Open
- **Severity:** Medium
- **Confidence:** Medium
- **CWE / class:** CWE-532
- **Primary file:** `Asgard/Baseline/baseline_manager.py`
- **Also on trace:** `Asgard/Baseline/_baseline_operations.py`, `Asgard/Heimdall/cli/handlers/baseline.py`
- **Location:** `save`; `generate_report("json")`
- **Trace:** `get_violation_message` may copy `description` / `import_statement` / `code_snippet` → JSON on disk → `model_dump` / CLI list
- **Impact:** `.asgard-baseline.json` and JSON reports can hold snippets/secrets when those attrs are present. Text/markdown reports omit `message`.
- **Evidence:** JSON report is `json.dumps(baseline.model_dump(...))` with no redaction.
- **Planned fix:** Persist a hash of the message, not raw text. Strip `description`/`code_snippet` unless a redaction hook. Omit `message` from default JSON report/list.
- **Fix wave:** W3

### CH-0014 — Baseline save is non-atomic and follows symlinks

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-59
- **Primary file:** `Asgard/Baseline/baseline_manager.py`
- **Also on trace:** CH-0010 path
- **Location:** `load` exists-then-open; `save` `open(..., 'w')`
- **Trace:** `exists()` then `open`; `open(..., 'w')` on a symlink clobbers the target
- **Impact:** Replace/symlink of the baseline path redirects read or overwrite. Concurrent writers can corrupt JSON.
- **Evidence:** In-place write; no `O_NOFOLLOW`; no temp + `os.replace`.
- **Planned fix:** Refuse `is_symlink()`. Write temp in the same dir + `os.replace`. Drop `exists()`; handle `FileNotFoundError`.
- **Fix wave:** W2

### CH-0015 — 12-hex violation IDs collide; `remove_entry` deletes every match

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-328
- **Primary file:** `Asgard/Baseline/_baseline_helpers.py`
- **Also on trace:** `Asgard/Baseline/models.py` (`remove_entry`), `Asgard/Baseline/baseline_manager.py`
- **Location:** `generate_violation_id`
- **Trace:** ID = SHA-256[:12] of `path:line:type:message` → `remove_entry` drops all rows with that id
- **Impact:** 48-bit id; a collision removes extra suppressions. Not a MAC of the file.
- **Evidence:** `hexdigest()[:12]`; remove-by-id is not unique-constrained.
- **Planned fix:** Store the full digest (or UUID). `remove_entry` should require a unique match or also match file/line.
- **Fix wave:** W3

### CH-0016 — Unbounded CIR parse / walk / LCOM4 (local DoS)

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-400
- **Primary file:** `Asgard/Bragi/Architecture/cir/builder.py`
- **Also on trace:** `Asgard/Bragi/Architecture/evaluators/_lcom4.py`, `Asgard/Bragi/Architecture/evaluators/srp.py`
- **Location:** `build_file_cir` → `parse_source`; recursive `_walk`; `lcom4_components` pairwise
- **Trace:** Untrusted scanned `source` → encode → tree-sitter parse → language handler → `evaluate_file` → LCOM4 O(n²)
- **Impact:** Hostile or huge files can spike CPU/RAM during a scan. Process does not execute the file. No query injection (queries are static).
- **Evidence:** No source-size cap; LCOM4 is pairwise on methods; SRP evidence concatenates component names.
- **Planned fix:** Cap source bytes/lines before parse; iterative walk with a node budget; cap LCOM4 method count and skip/flag oversized classes.
- **Fix wave:** W4

### CH-0017 — Architecture bounds cache is unsigned and unvalidated

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345 / CWE-20
- **Primary file:** `Asgard/Bragi/Architecture/graph/service.py`
- **Also on trace:** `Asgard/Bragi/Architecture/graph/propagation.py`, `Asgard/Bragi/Architecture/services/hexagonal_analyzer.py` (`analyze` / `explain_file`; live on `heimdall architecture hexagonal` and `layers --explain`)
- **Location:** `_load_bounds_cache` / `infer` hydrate / `_save_bounds_cache`
- **Trace:** Scan root → `.asgard_cache/bragi_arch_bounds.json` → `json.load` → if `version` + `config_hash` match, cached bounds skip `infer_levels`. Malformed bounds raise outside the load `try`.
- **Impact:** A hostile tree or poisoned CI cache can suppress drift/layer findings (matching file hashes + fake bounds) or crash the analyzer. Default cache is on (`ASGARD_NO_CACHE` disables).
- **Evidence:** Load checks version + `config_hash` only; hydrate reads `min_level` unguarded.
- **Planned fix:** Validate cache with a strict schema; wrap hydrate in `except (TypeError, KeyError, AttributeError)` and treat as miss; optionally HMAC or refuse cache unless produced this run.
- **Fix wave:** W4

### CH-0018 — `fnmatch` on attacker-controlled architecture.yml patterns

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-1333
- **Primary file:** `Asgard/Bragi/Architecture/graph/propagation.py`
- **Also on trace:** `Asgard/Bragi/Architecture/graph/reflexion.py`, `Asgard/Bragi/Architecture/services/_architecture_config.py`
- **Location:** `_match_layer`; `layer_name_for_module`
- **Trace:** `architecture.yml` `heuristics.paths` / `path_patterns` → `LayerConfig.path_patterns` → `fnmatch.fnmatch` per module. Nested `*` globs vs long names can hang CPython `fnmatch`.
- **Impact:** CPU hang on infer/reflexion. CLI today uses `default_architecture_config()`; `from_yaml` is unused by Heimdall handlers but reachable via API/tests.
- **Evidence:** No pattern length / `*` count cap in `_parse_layer`.
- **Planned fix:** Cap pattern length and `*` count; reject non-str patterns; coerce YAML lists to bounded `list[str]`.
- **Fix wave:** W4

### CH-0019 — Markdown reporters interpolate scan-controlled strings unescaped

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-116
- **Primary file:** `Asgard/Bragi/Architecture/services/_arch_reporter_markdown.py`
- **Also on trace:** `Asgard/Bragi/Architecture/services/_pattern_reporter.py`, `Asgard/Bragi/Architecture/services/_solid_reporter.py`, `Asgard/Bragi/Architecture/services/_suggester_reporter.py`, `Asgard/Bragi/Architecture/services/_generic_hexagonal_checks.py`, `Asgard/Bragi/Coverage/services/_coverage_reporter.py`, `Asgard/Bragi/Dependencies/services/_license_reporter.py`, `Asgard/Bragi/Dependencies/services/_dependency_reporter.py`, `Asgard/Bragi/OOP/services/_oop_reporter.py`, `Asgard/Bragi/Performance/services/_static_performance_reporter.py`
- **Location:** markdown table cells (`class_name`, `message`, `source_module`, `signals`)
- **Trace:** Scanned source tokens → violation/suggestion fields → f-string MD tables → CLI `print(report)`. JSON path uses `json.dumps` (safe). Full-scan HTML escapes the text reporter.
- **Impact:** Broken tables; if a downstream Markdown→HTML renderer does not sanitize, `|` / HTML in identifiers can inject markup. No in-repo HTML consumer of these MD reports.
- **Evidence:** No escaping of `|`, newlines, or HTML in table cells.
- **Planned fix:** Shared `_md_cell()` that escapes `|`, backticks, and control chars; HTML-escape if MD is ever rendered as HTML.
- **Fix wave:** W5

### CH-0020 — Architecture YAML loader: caller path + no schema

- **Status:** Open
- **Severity:** Info
- **Confidence:** High
- **CWE / class:** CWE-20
- **Primary file:** `Asgard/Bragi/Architecture/services/_architecture_config.py`
- **Also on trace:** `Asgard/Bragi/Architecture/graph/service.py` (`from_yaml`)
- **Location:** `load_architecture_config` — `open` + `yaml.safe_load`
- **Trace:** Caller-supplied filesystem path → `yaml.safe_load` (not `yaml.load`) → layer names/patterns into CSP / messages. No production CLI caller today.
- **Impact:** No RCE (`safe_load`). If wired later: any readable path as YAML; malformed types crash or weaken `fnmatch`.
- **Evidence:** No `Path.is_file()`, size cap, or type coercion of `path_patterns`.
- **Planned fix:** Require a file; size cap; validate `layers` is a list of mappings; coerce list/int fields. Keep `safe_load`.
- **Fix wave:** W5

### CH-0021 — Regex SOLID fallback ReDoS on large source lines

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-1333
- **Primary file:** `Asgard/Bragi/Architecture/services/_generic_solid_checks.py`
- **Also on trace:** `Asgard/Bragi/Architecture/services/_treesitter_solid_checks.py` (fallback)
- **Location:** `_METHOD_PATTERNS` JS/TS `\(.*\)`
- **Trace:** CIR/tree-sitter miss → regex fallback on scanned lines → greedy groups on huge/minified lines
- **Impact:** Availability only; triggered only on the fallback path.
- **Evidence:** JS/TS method patterns use `\(.*\)`.
- **Planned fix:** Bound match (`.{0,200}`), skip lines over a max length, or drop regex when CIR exists.
- **Fix wave:** W4

### CH-0022 — Unbounded tree-sitter recursion can abort a multi-language SOLID run

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-674 / CWE-400
- **Primary file:** `Asgard/Bragi/Architecture/services/_treesitter_solid_checks.py`
- **Also on trace:** `Asgard/Bragi/Architecture/services/solid_validator.py` (`analyze_file_generic` / `analyze_multilang`)
- **Location:** `_walk_classes`; `_check_isp_*._walk`
- **Trace:** Untrusted file → `read_text` → `parse_source` → Python recursion over every child → `RecursionError`. `analyze_multilang` has no per-file `try/except` (unlike `validate()`).
- **Impact:** One deeply nested source file can crash a multi-language SOLID run. Default Heimdall architecture CLI uses `validate()` (iterative `ast.walk`), so this is the generic/TS API path.
- **Evidence:** Walks are unbounded; `analyze_file_generic` only catches `OSError` on read.
- **Planned fix:** Iterative stack walk with a max depth/node budget; wrap each file’s TS checks in `except (RecursionError, MemoryError)`; skip sources over a byte/line cap.
- **Fix wave:** W4

### CH-0023 — Local `CLAUDE.md` is documented as credential-bearing and is gitignored

- **Status:** Open
- **Severity:** Info
- **Confidence:** High
- **CWE / class:** CWE-540
- **Primary file:** `.gitignore` (policy; file itself is not inventory code)
- **Also on trace:** `CLAUDE.md` (present on disk, not committed)
- **Location:** `.gitignore` “Local project instructions — contains live credentials, never commit”
- **Trace:** Local instruction file exists; ignore rule prevents add. Not scanned for contents.
- **Impact:** If the ignore rule is ever removed or the file is force-added, live credentials would enter history. Contents were not read or copied.
- **Evidence:** File exists at repo root; ignore comment states credentials. No tracked `.env` files found.
- **Planned fix:** Keep the ignore. Confirm GitHub secret scanning / push protection (Jake-todo). Rotate anything that was ever pasted into local instruction files. Do not commit `CLAUDE.md`.
- **Fix wave:** W1

### CH-0024 — SZZ runs `git diff` against an untrusted repo without isolating git config

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-78 / CWE-829 (untrusted git repo)
- **Primary file:** `Asgard/Bragi/Calibration/services/szz.py`
- **Also on trace:** `Asgard/Bragi/Calibration/services/rule_validator.py`, `Asgard/Bragi/Quality/services/_git_friction.py`, `Asgard/Bragi/QualityGate/services/_git_diff.py` (live `git diff` on `heimdall --diff`), `Asgard/Bragi/QualityGate/services/_hotspot_ranker.py`
- **Location:** `_run_git` → `_fix_commit_hunks` (`git diff`)
- **Trace:** `compute_szz(repo_root)` / Stage 2 validity → `subprocess.run(["git", "-C", repo_root] + args)` with inherited env → `git diff` honors that repo’s `diff.external` / `GIT_EXTERNAL_DIFF` / pager/fsmonitor
- **Impact:** Pointing Stage 2 at a hostile clone can execute a command from repo config or env. Not `shell=True` injection. **Not on Heimdall CLI today** (Stage 1 only); public API is live.
- **Evidence:** argv-list git, no `--no-ext-diff`, no `-c diff.external=`, no env wipe. Timeouts set.
- **Planned fix:** Always pass `--no-ext-diff`; prefix `-c` overrides to disable `diff.external`, `core.fsmonitor`, `core.pager`, `alias.*`. Clear `GIT_EXTERNAL_DIFF` / `GIT_PAGER` / `GIT_DIR`. Prefer `GIT_CONFIG_NOSYSTEM=1` and a blank global. Add a test that a repo with `diff.external` does not execute it. Do not hook Stage 2 to CLI until this lands.
- **Fix wave:** W1

### CH-0025 — SZZ unbounded per-hunk `git blame`

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-400
- **Primary file:** `Asgard/Bragi/Calibration/services/szz.py`
- **Also on trace:** `Asgard/Bragi/Calibration/services/rule_validator.py`
- **Location:** `compute_szz` hunk loop + `_blame_inducing_commits`
- **Trace:** `MAX_FIX_COMMITS_SCANNED=500` only; each hunk is a separate `git blame -w -C` (30s timeout)
- **Impact:** A fix commit with thousands of hunks can spawn thousands of blame processes.
- **Evidence:** Commit cap exists; no hunk/blame cap.
- **Planned fix:** Cap hunks per commit and total blame calls; skip copy-detection on huge diffs; fail with `INSUFFICIENT_DATA` when over budget.
- **Fix wave:** W4

### CH-0026 — `LanguageProfileService` joins unsanitized `language` into a file path

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Bragi/Calibration/services/profile_service.py`
- **Also on trace:** `Asgard/Bragi/Calibration/models/calibration_models.py` (`LanguageProfile.language` unconstrained)
- **Location:** `_load_language` — `self.profiles_dir / f"{language}.yaml"`
- **Trace:** CLI JSON / YAML / `resolve(language)` → path join. Absolute `language` replaces the base; `../` escapes `profiles/`. Then `yaml.safe_load` (no RCE from tags).
- **Impact:** Arbitrary `.yaml` read into thresholds/weights, or crash on bad schema. **Latent:** no production `LanguageProfileService()` caller under `Asgard/` yet (tests + this module only).
- **Evidence:** No allowlist / `is_relative_to`. `Path / abs` replaces the profiles dir.
- **Planned fix:** Allowlist `language` as `^[a-z][a-z0-9_]*$` matching shipped profile stems. `resolve()` the path and require `is_relative_to(profiles_dir)`. Unknown language → generic profile.
- **Fix wave:** W2

### CH-0027 — Local calibration profile YAML is trusted without clamp or authenticity check

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Bragi/Calibration/services/profile_service.py`
- **Also on trace:** `Asgard/Bragi/Calibration/services/local_calibrator.py` (`_clamp` only on generate), `.asgard_cache/bragi_local_profile.yaml`
- **Location:** `_load_local_override`
- **Trace:** `{project_path}/.asgard_cache/bragi_local_profile.yaml` → `safe_load` → `LanguageProfile(**data)` merged over language/generic with no re-clamp and no signature
- **Impact:** Hand-edited or committed YAML can set extreme `fail` / weights and bypass the “cannot normalize its own rot” guard. Same class as CH-0017 (unsigned project cache).
- **Evidence:** `_clamp` is not applied on load. Extra keys dropped; no HMAC.
- **Planned fix:** Re-apply `_clamp` against the language/generic anchor on load. Optionally refuse cache unless produced this run. Schema-validate numerics (finite, `warn <= fail`, weight bounds).
- **Fix wave:** W3

### CH-0028 — `write_local_profile` write root is caller-controlled

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Bragi/Calibration/services/local_calibrator.py`
- **Also on trace:** `Asgard/Heimdall/cli/handlers/calibration.py` (`--write` uses cwd only today)
- **Location:** `write_local_profile(profile, project_path)`
- **Trace:** Any `project_path` → `{path}/.asgard_cache/bragi_local_profile.yaml` (`mkdir` + truncate write)
- **Impact:** Confined relative filename; still writes under an unsanitized root if a future caller passes a path.
- **Evidence:** No `is_relative_to` / existence policy on `project_path`. CLI currently passes cwd.
- **Planned fix:** Resolve and confine `project_path` to cwd or an explicit project root; refuse `..` / absolute escapes. Test a `project_path` outside the intended root.
- **Fix wave:** W2

### CH-0029 — (withdrawn — merged into CH-0019)

Coverage markdown interpolation is recorded on CH-0019 (`_coverage_reporter.py` added to Also on trace). This ID is reserved so numbering stays monotonic; do not reuse.

### CH-0030 — `LanguageProfile` accepts unconstrained language and numeric fields

- **Status:** Open
- **Severity:** Info
- **Confidence:** High
- **CWE / class:** CWE-20
- **Primary file:** `Asgard/Bragi/Calibration/models/calibration_models.py`
- **Also on trace:** `Asgard/Bragi/Calibration/services/profile_service.py`, `Asgard/Bragi/Ratings/services/composite_score_engine.py`
- **Location:** `LanguageProfile.language`; `ThresholdSpec.warn`/`fail`; `category_weights`
- **Trace:** YAML/JSON → Pydantic v2 (extra ignored) → weights copied into `CompositeScoreEngine` with no clamp
- **Impact:** Inf/NaN/negative thresholds or zero/negative weights warp scoring. Enables CH-0026 if `language` is used as a path.
- **Evidence:** No charset/path check on `language`; no `warn <= fail`; no finite-range validators.
- **Planned fix:** Constrain `language` to the shipped-profile pattern; `FiniteFloat` + `warn <= fail`; clamp or reject non-positive weights.
- **Fix wave:** W5

### CH-0031 — Profile YAML `ValidationError` aborts `LanguageProfileService` construction

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-248 / availability
- **Primary file:** `Asgard/Bragi/Calibration/services/profile_service.py`
- **Also on trace:** `Asgard/Bragi/Calibration/models/calibration_models.py`
- **Location:** `_load_yaml_profile` — catches `YAMLError`/`OSError` only
- **Trace:** Poisoned `.asgard_cache/bragi_local_profile.yaml` or a bad bundled profile → `LanguageProfile(**data)` raises Pydantic `ValidationError` out of `__init__`
- **Impact:** Availability crash of any future caller of the service. Not RCE (`safe_load`).
- **Evidence:** Handler does not catch `ValidationError` / `TypeError`.
- **Planned fix:** Catch validation errors, log, fall back to generic/in-code defaults. Tests for `thresholds: []` and bad enums.
- **Fix wave:** W4

### CH-0032 — Unsigned license disk cache can bypass license policy

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Bragi/Dependencies/services/_license_cache.py`
- **Also on trace:** `Asgard/Bragi/Dependencies/services/license_checker.py` (`use_cache` default True)
- **Location:** `LicenseDiskCache` load/save `{scan_path}/.asgard_cache/bragi_license_cache.json`
- **Trace:** `analyze()` → cache get by package name (not version) → `license_name` / `license_classifier` treated as truth → policy engine
- **Impact:** A planted or committed cache entry can make a prohibited license look ALLOWED. Same class as CH-0017/CH-0027.
- **Evidence:** Version string check only; no HMAC; keyed by name not version. `ASGARD_NO_CACHE` is the only integrity control.
- **Planned fix:** Sign or refuse cache unless produced this run; include version in the key; validate record schema; default `use_cache=False` in CI.
- **Fix wave:** W3

### CH-0033 — License checker performs default-on HTTP to PyPI

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-668 / unexpected network
- **Primary file:** `Asgard/Bragi/Dependencies/services/license_checker.py`
- **Also on trace:** none
- **Location:** `_get_license_from_pypi` via `_resolve_packages` thread pool
- **Trace:** Uninstalled package name → `urlopen(https://pypi.org/pypi/{name}/json)` during `analyze()`. Unlike the vuln checker, there is no `enable_network` gate.
- **Impact:** Unexpected egress; package names leak to PyPI; scan hangs/fails on restricted networks. Default TLS verify is on (good).
- **Evidence:** Hardcoded pypi.org URL; called from the default analyze path.
- **Planned fix:** Gate PyPI behind `enable_network` (same as `VulnerabilityChecker`). Prefer installed metadata only unless opted in.
- **Fix wave:** W1

### CH-0034 — Unquoted package name interpolated into the PyPI URL

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-20 / CWE-918 adjacent
- **Primary file:** `Asgard/Bragi/Dependencies/services/license_checker.py`
- **Also on trace:** `Asgard/Bragi/Dependencies/services/requirements_checker.py` (`_extract_package_name`)
- **Location:** `f"https://pypi.org/pypi/{package_name}/json"`
- **Trace:** Requirements line → package name → URL path. Host is fixed; `urlopen` follows redirects. Name is not PEP 503 normalized or `quote()`’d.
- **Impact:** Path injection on pypi.org; possible redirect off-host if PyPI ever 3xx’s a crafted path. Not classic SSRF to an attacker origin from this string alone.
- **Evidence:** No `urllib.parse.quote`; no `[A-Za-z0-9._-]` allowlist on this path (SBOM parsers do restrict names).
- **Planned fix:** PEP 503 normalize + `quote(name, safe="")`; reject names outside `[A-Za-z0-9._-]`. Do not follow off-host redirects.
- **Fix wave:** W2

### CH-0035 — `RequirementsChecker.sync` writes an unconfined `target_file`

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Bragi/Dependencies/services/requirements_checker.py`
- **Also on trace:** `Asgard/Heimdall/cli/handlers/syntax.py` (`target_file=getattr(args, 'target_file', ...)`)
- **Location:** `sync` — `req_file = scan_path / target_file` then `write_text`
- **Trace:** CLI `--target-file` → `sync` → POSIX `Path / abs` replaces the scan root → overwrite/create that path if the process can write
- **Impact:** Arbitrary file write of a requirements-like text file. Also reads that path first if it exists.
- **Evidence:** No `is_relative_to` after join. CLI passes `args.target_file` through.
- **Planned fix:** Reject absolute `target_file` and `..`; `resolve()` and require `is_relative_to(scan_path)`. Tests for `/tmp/x` and `../x`.
- **Fix wave:** W2

### CH-0036 — Unsigned vulnerability lookup cache can hide or inject CVEs

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Bragi/Dependencies/services/_vuln_cache.py`
- **Also on trace:** `Asgard/Bragi/Dependencies/services/vulnerability_checker.py` (`_post_batch_cached` / `_query_nvd_cached`)
- **Location:** `{cwd}/.asgard_cache/vulnerability/{key}.json`
- **Trace:** `enable_network=True` → cache get → treat `envelope["value"]` as OSV/NVD body → findings
- **Impact:** A planted cache can hide CVEs (`checked=True`, empty vulns) or inject findings. Only on the opt-in network path. `ASGARD_NO_CACHE=1` bypasses.
- **Evidence:** No HMAC; `mkdir` not `0o700`; TTL only.
- **Planned fix:** Schema-validate cached bodies; optional HMAC; `0o700` cache dir; document `ASGARD_NO_CACHE` for CI gates.
- **Fix wave:** W3

### CH-0037 — Vuln cache key is used as a path fragment

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Bragi/Dependencies/services/_vuln_cache.py`
- **Also on trace:** `cache_key(namespace, payload)`
- **Location:** `self.cache_dir / f"{key}.json"`
- **Trace:** If a caller passes a raw `key` with `/` or an absolute path, POSIX join escapes `cache_dir`. In-repo callers only use `cache_key("osv"|"nvd", ...)`.
- **Impact:** Latent arbitrary cache read/write if a future caller skips `cache_key()`.
- **Evidence:** Comment claims keys cannot traverse; true only for `cache_key()` outputs. `namespace` is interpolated unsanitized.
- **Planned fix:** Allowlist keys as `^[a-z0-9_]+$`; always hash the full key; `resolve()` + `is_relative_to(cache_dir)`.
- **Fix wave:** W2

### CH-0038 — `PackageLicense.is_allowed` defaults True (fail-open)

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-696 / fail-open
- **Primary file:** `Asgard/Bragi/Dependencies/models/license_models.py`
- **Also on trace:** `Asgard/Bragi/Dependencies/services/license_checker.py`, `_license_policy.py`
- **Location:** `PackageLicense.is_allowed: bool = True` while `verdict` defaults `"unknown"`
- **Trace:** Any consumer that only checks the booleans treats an un-evaluated package as allowed
- **Impact:** Policy bypass if a caller skips `verdict` / `_classify_license`. WARN packages also keep `is_allowed=True` by documented design.
- **Evidence:** Comment at models L121–124. Defaults are fail-open.
- **Planned fix:** Default `is_allowed=False` until classified; gates must use `verdict == "allowed"`. Tests for unclassified packages.
- **Fix wave:** W3

### CH-0039 — Unsigned dep-graph JSON cache can crash the scan

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-20 / CWE-345
- **Primary file:** `Asgard/Bragi/Dependencies/services/graph_service.py`
- **Also on trace:** `{scan_path}/.asgard_cache/bragi_dep_graph.json`
- **Location:** `_load_cache` / `build`
- **Trace:** `json.load` → `version == "1.0.0"` only → `files`/`derived` accessed outside the load `try`. Graph edges are always rebuilt live (not a finding-suppression clone of CH-0017).
- **Impact:** Hostile cache → `AttributeError` / large-JSON DoS. Cycle results not currently poisoned.
- **Evidence:** Non-dict `files` crashes; write is non-atomic.
- **Planned fix:** Schema-validate; wrap hydrate in try/except and treat as miss; atomic replace. Do not consume `_derived` without recompute unless signed.
- **Fix wave:** W4

### CH-0040 — Performance directory walker follows symlinks and can recurse forever

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-59 / CWE-674
- **Primary file:** `Asgard/Bragi/Performance/utilities/performance_utils.py`
- **Also on trace:** `Asgard/Bragi/Performance/services/cache_analyzer_service.py`, `cpu_profiler_service.py`, `database_analyzer_service.py`, `memory_profiler_service.py`, `static_performance_service.py`
- **Location:** `scan_directory_for_performance` → `_scan_recursive`
- **Trace:** `entry.is_dir()` / `is_file()` follow symlinks; no visited-inode set; no `is_relative_to(root)`. Cycle `link → .` recurses until stack overflow. File symlink targets are `open().read()`’d into findings.
- **Impact:** Escape the scan root via a directory symlink; CPU DoS via a cycle; host-file contents can appear in reports. Other Bragi walkers (`os.walk(followlinks=False)`) do not follow dir links.
- **Evidence:** Only `PermissionError` is caught. No `is_symlink()` skip.
- **Planned fix:** Skip symlinks (or `follow_symlinks=False`); track resolved inodes; require yielded paths `is_relative_to(root.resolve())`. Tests for dir-link escape and `link → .`.
- **Fix wave:** W2

### CH-0041 — `BugDetector` `rglob("*.py")` follows directory symlinks

- **Status:** Open
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-59
- **Primary file:** `Asgard/Bragi/Quality/BugDetection/services/bug_detector.py`
- **Also on trace:** none
- **Location:** `_collect_python_files` / `scan`
- **Trace:** `Path.rglob("*.py")` follows dir symlinks; `read_text` follows file symlinks; no `is_relative_to`
- **Impact:** A planted dir link under the scan root pulls outside-tree `.py` into findings/`code_snippet`.
- **Evidence:** No symlink skip; exclude is name/fnmatch only.
- **Planned fix:** Same walker policy as CH-0040; prefer `os.walk(followlinks=False)` + skip file symlinks (or resolve+jail).
- **Fix wave:** W2

### CH-0042 — Language analyzers `rglob` and ignore advertised exclude/size limits

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-59 / CWE-400
- **Primary file:** `Asgard/Bragi/Quality/languages/javascript/services/js_analyzer.py`
- **Also on trace:** `Asgard/Bragi/Quality/languages/cpp/services/cpp_analyzer.py`, `csharp/services/csharp_analyzer.py`, `go/services/go_analyzer.py`, `java/services/java_analyzer.py`, `php/services/php_analyzer.py`, `ruby/services/ruby_analyzer.py`, `rust/services/rust_analyzer.py`, `shell/services/shell_analyzer.py` (`rglob("*")` when shebang scan is on), `typescript/services/ts_analyzer.py` (delegates to JS walker)
- **Location:** `analyze` / `_discover_files` / `analyze_directory`
- **Trace:** `Path(scan_path).rglob(f"*{ext}")` → `read_text` of entire files. `rglob` follows directory symlinks. `exclude_patterns`, `max_file_lines`, `max_findings` exist on scan configs and are never applied.
- **Impact:** Escape via dir symlink; unbounded memory/CPU on huge trees/`bundle.js`; `include_extensions` glob interpolation can widen the walk.
- **Evidence:** Same unused-limit pattern in C++/C#/Go/Java/JS/PHP analyzers. JS is wired through `Heimdall/cli/handlers/lang_analyzers.py`.
- **Planned fix:** Shared walker: `os.walk(followlinks=False)`, skip file symlinks, apply exclude/max_file_lines/max_findings, cap line length before regex. Validate extensions against an allowlist.
- **Fix wave:** W2

### CH-0043 — Hardcoded-credential rules copy the secret into `code_snippet`

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-532
- **Primary file:** `Asgard/Bragi/Quality/languages/javascript/services/_js_security_rules.py`
- **Also on trace:** `Asgard/Bragi/Quality/languages/php/services/_php_rules.py`, `Asgard/Bragi/Quality/languages/ruby/services/_ruby_rules.py`, `Asgard/Bragi/Quality/languages/rust/services/_rust_rules.py`, `Asgard/Bragi/Quality/models/env_fallback_models.py`, `Asgard/Bragi/Quality/services/_env_fallback_reporter.py`, `Asgard/Heimdall/cli/handlers/lang_analyzers.py`
- **Location:** `check_hardcoded_credentials`
- **Trace:** Matching source line (including the literal) → `code_snippet` → CLI print / `report.dict()`
- **Impact:** Detected secrets leave the file into reports, logs, and CI artifacts.
- **Evidence:** No redaction/masking of the matched credential.
- **Planned fix:** Store a masked snippet (keep last 4 chars or variable name only). Same policy as CH-0013. Tests that a fake key is not present in full in the report.
- **Fix wave:** W3

### CH-0044 — `js.no-eval` remediates to `Function`

- **Status:** Open
- **Severity:** Info
- **Confidence:** High
- **CWE / class:** CWE-94 adjacent (unsafe guidance)
- **Primary file:** `Asgard/Bragi/Quality/languages/javascript/services/_js_rules.py`
- **Also on trace:** none
- **Location:** `check_no_eval` `fix_suggestion`
- **Trace:** Finding recommends “JSON.parse() or Function.” `Function` is implied eval. The checker does not execute it.
- **Impact:** Operators following the suggestion reintroduce code execution.
- **Evidence:** `fix_suggestion` text names `Function`.
- **Planned fix:** Recommend `JSON.parse` / structured parsers only; never `Function`/`eval`.
- **Fix wave:** W5

### CH-0045 — PHP rule regexes are quadratic on long lines

- **Status:** Open
- **Severity:** Low
- **Confidence:** Medium
- **CWE / class:** CWE-1333
- **Primary file:** `Asgard/Bragi/Quality/languages/php/services/_php_rules.py`
- **Also on trace:** `Asgard/Bragi/Quality/languages/php/services/php_analyzer.py`
- **Location:** SQL-build and XSS-concat patterns using `.*` + `$_GET|POST|...`
- **Trace:** Unbounded source line → `re.search` with `.*` → polynomial backtracking
- **Impact:** Availability on huge/minified PHP lines. Combined with CH-0042 unused `max_file_lines`.
- **Evidence:** Two patterns use `.*` before `$_(?:GET|POST|REQUEST|COOKIE)`.
- **Planned fix:** Bound `.{0,200}`; skip lines over a max length; apply `max_file_lines`.
- **Fix wave:** W4

### CH-0046 — Code-smell HTML report interpolates scan strings unescaped

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-79
- **Primary file:** `Asgard/Bragi/Quality/services/_code_smell_report_html.py`
- **Also on trace:** `Asgard/Bragi/Quality/services/code_smell_detector.py`, `Asgard/Bragi/Quality/services/_code_smell_visitor.py`
- **Location:** `generate_html_report` (`scan_path`, `filename`, `description`, `evidence`, `sev` class attribute)
- **Trace:** AST names / file basenames / scan_path → f-string HTML with no `html.escape` → CLI report string (if saved/opened in a browser)
- **Impact:** Stored XSS when the HTML report is opened. Attribute breakout if `severity` is a raw string.
- **Evidence:** No `html.escape`. `{sev}` used in `class="smell-{sev}"`.
- **Planned fix:** `html.escape` every interpolated field; never put untrusted values in attributes without quoting+escape. Tests with `<img` in a filename and scan_path.
- **Fix wave:** W5

### CH-0047 — Unsigned debt-state JSON cache can skip re-analysis

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Bragi/Quality/services/_debt_state_store.py`
- **Also on trace:** `{scan_root}/.asgard_cache/bragi_debt_state.json`
- **Location:** `load_state` / `changed_files` / `apply_delta`
- **Trace:** Planted cache with matching SHA-256 hashes + `total_debt_minutes: 0` → delta is a no-op → gate sees planted total. Pydantic validates schema (better than CH-0017) but there is no MAC.
- **Impact:** Integrity of Plan 06 PR-differential debt gating. Not RCE. `rel` join can also read outside `scan_root`.
- **Evidence:** Cache lives in the scanned tree. Skip is hash-only.
- **Planned fix:** Refuse cache unless produced this run or HMAC’d; confine `rel` with `is_relative_to`; treat missing/forged state as full rescan.
- **Fix wave:** W3

### CH-0048 — Incremental file-hash cache is unsigned and mtime-skips

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345 / CWE-22
- **Primary file:** `Asgard/Bragi/Quality/services/_incremental_cache.py`
- **Also on trace:** `Asgard/Bragi/Quality/services/incremental_scanner.py` (not yet popped if later)
- **Location:** `FileHashCache.load` / `is_changed` / `save`
- **Trace:** `json.load` → trust `hash`/`result`; `is_changed` returns unchanged on mtime+size match without hashing; `cache_path` may be absolute
- **Impact:** Planted `.asgard-cache.json` can skip re-scan and inject stored results. Latent: `enabled` defaults False; no in-repo scanner subclass found.
- **Evidence:** `max_cache_age_days` is never read.
- **Planned fix:** Always re-hash; schema+HMAC; confine `cache_path`; honor TTL. Do not enable until fixed.
- **Fix wave:** W3

### CH-0049 — Type checkers / linters execute untrusted project config

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-94 / CWE-829
- **Primary file:** `Asgard/Bragi/Quality/services/_syntax_linters.py`
- **Also on trace:** `Asgard/Bragi/Quality/services/_mypy_runner.py`, `Asgard/Bragi/Quality/services/_pyright_runner.py`
- **Location:** `run_pylint` / `run_flake8` / `run_mypy`; `run_mypy` cwd=scan path; `invoke_pyright` `npx` with cwd=scan path
- **Trace:** CLI `heimdall` syntax/type-check → subprocess argv-list (no `shell=True`) but no isolation flags → pylint `init-hook` / flake8 local-plugins / mypy `plugins=` / `npx` local `node_modules/.bin/pyright` from the scanned tree
- **Impact:** Scanning a hostile repo executes attacker code as the analyst. Same class as CH-0024.
- **Evidence:** No `--rcfile` override / isolated config; mypy cwd is the scan path; npx uses scan cwd.
- **Planned fix:** Pass isolated config files from Asgard; `cwd` a empty/safe dir; `npx --no-install` or invoke a pinned absolute binary; disable plugins. Add `--` before path operands. Tests that a planted `mypy.ini` plugin is not loaded.
- **Fix wave:** W1

### CH-0050 — Pyright runner writes/unlinks config in the scan tree (symlink clobber)

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-59
- **Primary file:** `Asgard/Bragi/Quality/services/_pyright_runner.py`
- **Also on trace:** `Asgard/Bragi/Quality/services/type_checker.py`
- **Location:** `invoke_pyright` write of `pyrightconfig.json` / `.pyrightconfig.heimdall.json` then `unlink`
- **Trace:** `open(..., "w")` follows a planted symlink → overwrite an arbitrary file; dangling symlink: write creates the target, unlink removes only the link
- **Impact:** Arbitrary file overwrite as the scanner user. Race if two scans share a dir.
- **Evidence:** Writes inside the untrusted scan tree; no `O_NOFOLLOW`.
- **Planned fix:** Write config to a `tempfile.mkdtemp` outside the tree; pass `--project` that path; never write into the scan root. Refuse if the dest is a symlink.
- **Fix wave:** W2

### CH-0051 — Unsigned QualityGate fingerprint baseline can hide all PR findings

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Bragi/QualityGate/baseline_store.py`
- **Also on trace:** `Asgard/Bragi/QualityGate/services/quality_gate_evaluator.py`, `{scan}/.asgard_cache/bragi_fingerprint_baseline.json`
- **Location:** `_read_all` / `load` → `BranchBaseline(**raw)`
- **Trace:** `heimdall --diff` → `evaluate_differential` → load unsigned JSON from the scan tree → classify matching fingerprints PRE-EXISTING
- **Impact:** Plant the current finding fingerprints → no blockers. Combined with CH-0052 (weak identity) one planted file+rule hash hides a whole file.
- **Evidence:** Schema-only Pydantic; no HMAC/commit binding. Missing JSON fail-closes to `NOT_EVALUATED`.
- **Planned fix:** HMAC or refuse cache unless produced this run; bind to commit SHA; treat load-hash mismatch as empty baseline for gates. Tests with a planted baseline of current fingerprints.
- **Fix wave:** W3

### CH-0052 — Gate fingerprints collapse to rule+path when snippet is empty

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-345
- **Primary file:** `Asgard/Bragi/QualityGate/fingerprint.py`
- **Also on trace:** `Asgard/Bragi/QualityGate/services/_differential_engine.py` (`ensure_fingerprint` keeps a caller-supplied fingerprint)
- **Location:** `fingerprint_with_anchor`; `ensure_fingerprint`
- **Trace:** CLI `GateFinding` with empty fp → hash(rule + path + "") if no snippet → one baseline entry matches every finding of that rule in that file. Non-empty `finding.fingerprint` is never recomputed (SARIF/dict can match a planted baseline).
- **Impact:** Over-suppression of NEW findings; assists CH-0051.
- **Evidence:** Anchor is snippet else file; `ensure_fingerprint` trusts pre-set fp.
- **Planned fix:** Always include line + message (or source hash); recompute unless a signed fp is present. Tests that two findings in one file get distinct fps.
- **Fix wave:** W3

### CH-0053 — `ParallelScanner` pickles analyzer callables over fork IPC

- **Status:** Open
- **Severity:** Medium
- **Confidence:** Medium
- **CWE / class:** CWE-502 / CWE-400
- **Primary file:** `Asgard/Bragi/Quality/services/parallel_scanner.py`
- **Also on trace:** none
- **Location:** `_scan_parallel` / `_process_file_wrapper`
- **Trace:** `ProcessPoolExecutor` pickles `(file_path, analyze_func, config)` to workers (Linux fork copies parent FDs/secrets). Per-file timeout does not kill hung workers.
- **Impact:** Not standalone RCE today. Compromised worker + pickle-decode in parent is RCE. Hung worker hangs the scan.
- **Evidence:** No spawn context; no result-type allowlist; `timeout_per_file` on `future.result` only.
- **Planned fix:** `multiprocessing.get_context("spawn")`; do not pickle callables (import a named worker); kill workers on timeout; cap `workers`.
- **Fix wave:** W4

### CH-0054 — Unmeasured Ratings dimensions default to letter A

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-693 / fail-open scoring
- **Primary file:** `Asgard/Bragi/Ratings/services/ratings_calculator.py`
- **Also on trace:** `Asgard/Bragi/Ratings/services/_report_extractors.py`, QualityGate metric extract
- **Location:** `_calculate_maintainability` / `_calculate_reliability` / `_calculate_security` when report missing
- **Trace:** Missing/disabled dimension → `LetterRating.A` + `NOT_MEASURED` → `_derive_overall_rating` worst-of letters ignores confidence → CLI prints A
- **Impact:** A scan that skipped security still looks like A. `"blocker"` severity maps to A. GENERATED path regex can drop file-level security tallies.
- **Evidence:** Confidence not used in overall letter. Extractors treat `blocker` as cap but calculator does not.
- **Planned fix:** Unmeasured dimensions must be `N/A` and excluded from overall, or fail-closed. Map `blocker` to E. Tests for missing security report.
- **Fix wave:** W3

### CH-0055 — Dashboard HTML interpolates request path and issue fields unescaped

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-79
- **Primary file:** `Asgard/Dashboard/services/html_renderer.py`
- **Also on trace:** `Asgard/Dashboard/adapters/web/dashboard_handler.py`, `Asgard/Dashboard/services/_html_renderer_pages.py`, `Asgard/Dashboard/services/_html_helpers.py`
- **Location:** `render_error({message})`; issue `file_path` / `rule_id` / `assigned_to` in tables; `title="{project_path}"`
- **Trace:** GET path → 404 `Page not found: {path}` → raw HTML. Stored: scan-derived `file_path`/`rule_id`/`assigned_to` → table cells/attributes. `html.escape` is unused.
- **Impact:** Reflected XSS on any reachable dashboard. Stored XSS from a hostile scan tree or writable `~/.asgard/issues.db`.
- **Evidence:** No escape helper. Badge helpers interpolate raw class and text.
- **Planned fix:** `html.escape` every interpolated field; never put untrusted values in attributes without quoting. Tests for `<img` in 404 path and `file_path`.
- **Fix wave:** W5

### CH-0056 — Dashboard has no authentication; `--host` can bind all interfaces

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-306
- **Primary file:** `Asgard/Dashboard/adapters/web/dashboard_handler.py`
- **Also on trace:** `Asgard/Dashboard/server.py` (`--host`, default `localhost`)
- **Location:** `do_GET`; `HTTPServer((host, port), …)`
- **Trace:** Any client that can reach the port reads issues/history. `--host 0.0.0.0` binds all interfaces with no warning/TLS/auth.
- **Impact:** LAN/WAN exposure of analysis data + CH-0055 XSS if bound broadly. Default localhost limits blast radius.
- **Evidence:** No cookie/token/Basic auth. Host unrestricted.
- **Planned fix:** Keep default localhost; warn/refuse `0.0.0.0` unless `--expose`. Optional token query or loopback-only check. Document that the dashboard is not a multi-user UI.
- **Fix wave:** W1

### CH-0057 — Alignment config `file:` paths are not confined to `base_dir`

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Forseti/Alignment/services/alignment_loader_service.py`
- **Also on trace:** `forseti align check` / `forseti audit` (`alignment-config.yaml`)
- **Location:** `build_ir_record` — `Path(base_dir) / source.file`
- **Trace:** YAML `EntitySource.file` absolute or `../` → `read_text` / validator on files outside the project. `forseti audit` auto-loads `alignment-config.yaml`.
- **Impact:** A committed malicious config reads arbitrary files the process can open (then may emit snippets in reports).
- **Evidence:** No `is_relative_to(base_dir.resolve())`. `yaml.safe_load` (no RCE from tags).
- **Planned fix:** Resolve and require paths under `base_dir`. Reject absolute/`..`. Tests for `/etc/passwd` and `../`.
- **Fix wave:** W2

### CH-0058 — CodeGen interpolates untrusted OpenAPI strings into generated source

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-94
- **Primary file:** `Asgard/Forseti/CodeGen/services/_python_generator_helpers.py`
- **Also on trace:** `Asgard/Forseti/CodeGen/services/_typescript_generator_helpers.py`, `Asgard/Forseti/CodeGen/services/_golang_generator_client_helpers.py`
- **Location:** Python `path = f"{path}"` from OpenAPI path; TS template literals; Go quoted `fmt.Sprintf`
- **Trace:** Hostile OpenAPI path/operationId/schema name → generated client source → RCE when that client is imported/run
- **Impact:** A malicious spec poisons generated Python/TS/Go. Write paths are currently hardcoded (no zip-slip today) but `_write_files` does not jail `file.path`.
- **Evidence:** No escaping of `path`/`operationId`/descriptions. Python emits a live f-string of the spec path.
- **Planned fix:** Treat spec strings as data: JSON-encode paths; allowlist identifiers `[A-Za-z_][A-Za-z0-9_]*`; escape comments. Jail writes with `is_relative_to(output_dir)`. Tests with `{__import__('os')}` in a path.
- **Fix wave:** W2

### CH-0059 — JSON Schema `$ref` reads arbitrary local files

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-22 / CWE-73
- **Primary file:** `Asgard/Forseti/JSONSchema/services/_ref_resolver_helpers.py`
- **Also on trace:** `Asgard/Forseti/JSONSchema/services/schema_compiler_service.py`, `schema_validator_service.py`
- **Location:** `SchemaRegistry._load_external`
- **Trace:** File-backed validate → compile with `schema_path` → `$ref` `file:///…` or `/…` or `../` → `load_schema_file` with no jail. HTTP `$ref` is rejected.
- **Impact:** Untrusted schema exfiltrates local files into the compilation/validation process.
- **Evidence:** Absolute and `file:` refs used as-is; no `is_relative_to(root_path)`.
- **Planned fix:** Allow only relative refs under `root_path.resolve()`. Reject `file:` absolute and `http(s)`. Tests for `/etc/passwd` and `../`.
- **Fix wave:** W2

### CH-0060 — GraphQL introspection `urlopen` is unauthenticated SSRF

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-918
- **Primary file:** `Asgard/Forseti/GraphQL/services/introspection_service.py`
- **Also on trace:** none
- **Location:** `_execute_query` → `urllib.request.urlopen(Request(endpoint))`
- **Trace:** Caller `endpoint` (CLI) → POST; follows redirects; no scheme/host allowlist (`file:` possible)
- **Impact:** Operator-controlled today; library API can be pointed at internal hosts or `file:`.
- **Evidence:** No allowlist. `allow_introspection` gates the feature, not the URL.
- **Planned fix:** Require `http`/`https`; block link-local/RFC1918 unless `--allow-internal`; disable redirects or re-validate Location.
- **Fix wave:** W1

### CH-0061 — Generated mock servers bind `0.0.0.0` with no auth and Flask `debug=True`

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-306 / CWE-489
- **Primary file:** `Asgard/Forseti/MockServer/services/_mock_server_generator_helpers.py`
- **Also on trace:** `Asgard/Forseti/MockServer/models/mock_models.py` (`host` default), `mock_server_generator.py`
- **Location:** generated Flask `app.run(host="0.0.0.0", debug=True)`
- **Trace:** `forseti mock generate` → artifact listens on all interfaces, no security, Werkzeug debugger on
- **Impact:** Network-exposed debugger and unauthenticated mock API.
- **Evidence:** CLI never overrides host. `MockEndpoint.security` unused.
- **Planned fix:** Default `127.0.0.1`; `debug=False`; honor security schemes or document local-only. Tests assert generated host/debug.
- **Fix wave:** W1

### CH-0062 — Validation proxy is an open SSRF forwarder

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-918
- **Primary file:** `Asgard/Forseti/MockServer/services/validation_proxy_service.py`
- **Also on trace:** `_validation_proxy_helpers.py`
- **Location:** `handle_request` — `urlopen(upstream + path)`
- **Trace:** Client method/path/headers/body → `urlopen`; follows redirects; no path `..` check; no scheme allowlist
- **Impact:** Anyone who can hit the proxy (default bind `0.0.0.0`) can pivot to `--upstream` or follow a 3xx to metadata IPs.
- **Evidence:** Headers forwarded except Content-Length. `file:` accepted by urllib.
- **Planned fix:** Bind localhost; require `http(s)` upstream; strip hop-by-hop headers; refuse `..` and scheme-relative paths; do not follow off-host redirects.
- **Fix wave:** W1

### CH-0063 — LiveContract probe URL join can rewrite authority; `urlopen` follows redirects

- **Status:** Open
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-918
- **Primary file:** `Asgard/Forseti/LiveContract/services/live_validator_service.py`
- **Also on trace:** `probe_planner_service.py`, `workflow_runner_service.py`
- **Location:** `base_url.rstrip("/") + path` without requiring `path` starts with `/`
- **Trace:** Spec path `@host/...` or missing `/` → `http://intended@attacker/` ; `urlopen` follows 3xx; `verify_tls=False` is opt-in
- **Impact:** Hostile spec or workflow params redirect probes to attacker/internal hosts.
- **Evidence:** `extract_operations` does not enforce OpenAPI “paths start with `/`”.
- **Planned fix:** `urllib.parse.urljoin` + require path `/`; allowlist scheme/host; no off-host redirects; URL-encode workflow params.
- **Fix wave:** W1

### CH-0064 — Documentation HTML interpolates title/contact/custom_css unescaped

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-79
- **Primary file:** `Asgard/Forseti/Documentation/services/docs_generator.py`
- **Also on trace:** `_docs_generator_helpers.py`, `templates/base.html` (unused `{{ title }}`)
- **Location:** `<title>{doc_structure.title}</title>`; contact `href`; `custom_css` in `<style>`
- **Trace:** OpenAPI title/contact/css → HTML file. Most other fields use `html.escape`.
- **Impact:** XSS if generated docs are served as HTML.
- **Evidence:** `javascript:` possible in contact.url; `</style><script>` in custom_css.
- **Planned fix:** Escape title/contact; allowlist CSS or drop `custom_css`. Tests for `javascript:` URL.
- **Fix wave:** W5

### CH-0065 — SQL `DEFAULT` interpolated unsanitized into migrations/Alembic

- **Status:** Open
- **Severity:** Medium
- **Confidence:** Medium
- **CWE / class:** CWE-89 / CWE-94
- **Primary file:** `Asgard/Forseti/Database/services/_schema_analyzer_helpers.py`
- **Also on trace:** `migration_generator_service.py`, `_schema_diff_helpers.py`
- **Location:** `parse_column` `DEFAULT\s+([^\s,]+)`; `to_sql` `DEFAULT {self.default_value}`
- **Trace:** Hostile SQL dump → default value → generated `.sql` / Alembic `op.execute('...')` string
- **Impact:** Stacked SQL or Python breakout if generated migrations are executed. Names are `\w+`; `quote_identifier` exists but unused.
- **Evidence:** Alembic escape is only `'` → `\'`.
- **Planned fix:** Restrict defaults to literals; use `quote_identifier`; emit parameterized Alembic. Tests with `1;DROP`.
- **Fix wave:** W2

## Planned fix waves

- **W1 — CI / supply chain / secrets policy (do first):** CH-0001–CH-0006, CH-0023, CH-0024, CH-0033, CH-0049, CH-0056, CH-0060, CH-0061, CH-0062, CH-0063. Isolate git/linters; lock mock/proxy/probe/introspection network.
- **W2 — Path confinement:** … CH-0050, CH-0057, CH-0058, CH-0059, CH-0065. Jail `$ref` and generated SQL/Alembic.
- **W3 — Baseline / cache / policy integrity:** CH-0011, CH-0012, CH-0013, CH-0015, CH-0027, CH-0032, CH-0036, CH-0038, CH-0043, CH-0047, CH-0048, CH-0051, CH-0052, CH-0054. Sign QualityGate baselines; fix fingerprint identity; do not grade unmeasured dimensions as A.
- **W4 — Analyzer robustness:** CH-0016, CH-0017, CH-0018, CH-0021, CH-0022, CH-0025, CH-0031, CH-0039, CH-0045, CH-0053. Size/recursion/hunk/regex caps; spawn-safe parallel workers.
- **W5 — Output / template hygiene:** CH-0009, CH-0019, CH-0020, CH-0030, CH-0044, CH-0046, CH-0055, CH-0064. Escape Dashboard and Forseti docs HTML.

## Accepted risks

None yet.

## Scan progress

- Inventory init (2026-08-16): discovered=3875 remaining=3875 completed=0
- Batch 1 merged: 64 files (CI + BackendInit + Baseline + Architecture CIR/graph/services helpers)
- Batch 2 merged: Architecture analyzers + Calibration + CodeFix + Coverage core (50 files)
- Batch 3 merged: Coverage extractors + Dependencies + OOP models (40 files)
- Batch 4 merged: OOP + Performance + BugDetection (48 files)
- Batch 5 merged: Quality language analyzers C++ through PHP
- Batch 6 merged (2026-08-16): Quality ruby/rust/shell/typescript + Quality models A
- Last paths completed: through Quality services `error_handling_scanner.py` (batch 7, ~80 files)
- Next batch: remaining Quality scanners (file_length, taint, type_checker, parallel_scanner) + QualityGate + Ratings
- Resume pointer: `python3 scripts/cyberhardening_inventory.py status` then `next 8`
- Spot-check batch 7: `_git_friction` git -C (CH-0024); HTML smell report unescaped; mypy/pyright/pylint untrusted config; pyright writes into scan tree.
- Batch 8 merged: remaining Quality scanners + taint + QualityGate + Ratings
- Batch 9: Dashboard + Forseti Alignment/AsyncAPI/Avro/CodeGen
- Batch 10: Forseti Compatibility through MockServer/LiveContract
- Highest ID: CH-0065
- **Successor:** do not rebuild inventory unless `todo.json` is missing. Continue `next N`. Do not implement fixes.
