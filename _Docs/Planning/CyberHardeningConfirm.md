# CyberHardening Confirmation Plan

Status: CONFIRMATION COMPLETE — 13 NEW FINDINGS
Started: 2026-08-17
Repo: Asgard
Original plan: `_Docs/Planning/CyberHardening.md`
Original status: FIXES APPLIED
Original live findings: 114
Original accepted risk: 0
Original withdrawn: 1 (CH-0029)

## Purpose

Re-trace every code file after CyberHardening fixes were applied. Confirm each original finding is still closed. Record reopenings, residuals, and new findings. This is not a second first-audit and not an implementation pass.

## Method

Every inventoried code file is traced again (not merely grepped, not merely compared to the implementation note). Original findings are judged against current code. Files with no remaining issue get a clean-bill entry in the confirmation ledger.

## Inventory

- Script: `scripts/cyberhardening_inventory.py --workspace CyberHardeningConfirm`
- Todo: `_Docs/Planning/CyberHardeningConfirm/todo.json`
- Ledger: `_Docs/Planning/CyberHardeningConfirm/ledger.jsonl`
- Original workspace (read-only): `_Docs/Planning/CyberHardening/`

## Original finding confirmation

| ID | Severity | Wave | Verdict | Residual | Note |
|----|----------|------|---------|----------|------|
| CH-0001 | High | W1 | Residual | generated `@v4` leftovers | live workflows SHA-pinned; scaffold + generated scan-wf still emit `@v4` |
| CH-0002 | High | W1 | Confirmed |  | PR jobs ubuntu-latest; no `-e` on PR; persist-credentials false |
| CH-0003 | High | W1 | Confirmed |  | split build/attest/publish; env pypi; tag v[0-9].* |
| CH-0004 | Medium | W1 | Confirmed |  | ci 30m + concurrency; publish 15m |
| CH-0005 | Medium | W1 | Confirmed |  | contents:read; persist-credentials false; SHA pins; still if:false |
| CH-0006 | Low | W1 | Residual | init template omits detect-secrets | repo config SHA-pinned + detect-secrets; generated Python template is not |
| CH-0007 | Medium | W2 | Confirmed |  | folder_name single segment; is_relative_to(base) |
| CH-0008 | Low | W2 | Residual | parent-dir symlink follow | leaf .gitignore symlink skipped; mkdir follows dir symlink |
| CH-0009 | Info | W5 | Residual | ENV/ still in template | lib/ lib64/ env/ dropped; ENV/ remains |
| CH-0010 | Medium | W2 | Confirmed |  | _confined_baseline_path rejects abs/.. |
| CH-0011 | Medium | W3 | Residual | sibling .key HMAC plant | unsigned JSON fail-closed; env-less sibling key forges |
| CH-0012 | High | W3 | Confirmed |  | empty fuzzy keys refused; persist hashes vid; tests exist |
| CH-0013 | Medium | W3 | Confirmed |  | messages persisted as sha256; CLI/report omit raw |
| CH-0014 | Low | W2 | Confirmed |  | refuse dest symlink; mkstemp+replace |
| CH-0015 | Low | W3 | Confirmed |  | 64-hex SHA-256; remove_entry unique only |
| CH-0016 | Low | W4 | Confirmed |  | CIR size/walk/LCOM4 caps live |
| CH-0017 | Medium | W4 | Residual | sibling .key HMAC plant | schema+HMAC on load; env-less sibling key forges |
| CH-0018 | Low | W4 | Confirmed |  | sanitize_path_patterns caps globs |
| CH-0019 | Low | W5 | Residual | two MD reporters unescaped | md_cell used on listed tables; layer/hexagonal reporters raw |
| CH-0020 | Info | W5 | Residual | level/import lists untyped | file/size/layers checks exist; planned coerce incomplete |
| CH-0021 | Low | W4 | Confirmed |  | bounded regex + skip lines >4096 |
| CH-0022 | Medium | W4 | Confirmed |  | iterative walk + RecursionError contained |
| CH-0023 | Info | W1 | Confirmed |  | CLAUDE.md gitignored with credential comment |
| CH-0024 | High | W1 | Residual | textconv/filter drivers | named git-config vectors isolated; local textconv still runs |
| CH-0025 | Low | W4 | Confirmed |  | hunk/blame caps return INSUFFICIENT_DATA |
| CH-0026 | Medium | W2 | Confirmed |  | LANGUAGE_ID_RE + is_relative_to profiles_dir |
| CH-0027 | Medium | W3 | Confirmed |  | schema+clamp on local YAML; unsigned leftover optional |
| CH-0028 | Low | W2 | Confirmed |  | write_local_profile confined under cwd |
| CH-0029 | — | — | Skipped | | withdrawn |
| CH-0030 | Info | W5 | Confirmed |  | language allowlist; finite thresholds; positive weights |
| CH-0031 | Low | W4 | Confirmed |  | ValidationError logged; ctor returns None |
| CH-0032 | Medium | W3 | Confirmed |  | HMAC+version; miss on unsigned; CI use_cache=False |
| CH-0033 | Medium | W1 | Confirmed |  | enable_network default False; https://pypi.org only; 10s timeout |
| CH-0034 | Low | W2 | Confirmed |  | PEP503 + quote; path-like rejected |
| CH-0035 | High | W2 | Confirmed |  | confine_sync_target jail; abs/.. rejected |
| CH-0036 | Medium | W3 | Confirmed |  | HMAC+schema; planted empty refetches |
| CH-0037 | Low | W2 | Confirmed |  | hashed filename + is_relative_to |
| CH-0038 | Medium | W3 | Confirmed |  | is_allowed default False; unknown deny |
| CH-0039 | Low | W4 | Confirmed |  | HMAC+schema; miss on error |
| CH-0040 | Medium | W2 | Confirmed |  | skip symlinks; inode cycle; jail resolve |
| CH-0041 | Low | W2 | Confirmed |  | os.walk followlinks=False; no rglob |
| CH-0042 | Medium | W2 | Confirmed |  | iter_language_files + size/finding caps |
| CH-0043 | Medium | W3 | Residual | Java/Go/C#/C++/shell still copy raw secret | JS/PHP/Ruby/Rust mask; other langs still code_snippet=line |
| CH-0044 | Info | W5 | Confirmed |  | no-eval remediates to JSON.parse not Function |
| CH-0045 | Low | W4 | Confirmed |  | bounded PHP regex + line cap |
| CH-0046 | Medium | W5 | Residual | file-length/scan HTML path unescaped | smell `_esc` holds; `quality_file_length` / `scan_html` still interpolate `scan_path` raw |
| CH-0047 | Medium | W3 | Residual | sibling .key HMAC plant | unsigned JSON miss; env-less sibling key forges |
| CH-0048 | Medium | W3 | Residual | sibling .key HMAC plant | HMAC+rehash; sibling key leftover; enabled default False |
| CH-0049 | High | W1 | Confirmed |  | mypy/pyright runners isolated; planted plugins not loaded |
| CH-0050 | High | W2 | Confirmed |  | pyrightconfig written only in isolated temp workdir |
| CH-0051 | High | W3 | Residual | sibling .key + HMAC plant | unsigned JSON fail-closed; env-less sibling key still forges |
| CH-0052 | Medium | W3 | Confirmed |  | digest includes line+message; unsigned recomputed |
| CH-0053 | Medium | W4 | Confirmed |  | spawn + named import; timeout kills workers |
| CH-0054 | Medium | W3 | Confirmed |  | unmeasured → N/A; overall N/A if any missing |
| CH-0055 | High | W5 | Confirmed |  | esc() on 404/path/issue fields; badge CSS allowlisted |
| CH-0056 | Medium | W1 | Confirmed |  | default localhost; refuse 0.0.0.0/:: without --expose |
| CH-0057 | Medium | W2 | Confirmed |  | confine_source_path before any read |
| CH-0058 | High | W2 | Confirmed |  | json.dumps paths; sanitize identifiers; confine_output_path |
| CH-0059 | High | W2 | Confirmed |  | $ref jailed to schema dir; remotes/file-abs refused |
| CH-0060 | High | W1 | Confirmed |  | http(s)+IP block+redirect revalidate; no file/ftp handlers |
| CH-0061 | High | W1 | Confirmed |  | default 127.0.0.1; generated Flask debug=False |
| CH-0062 | High | W1 | Confirmed |  | localhost default; http(s) upstream; path jail; same-host redirects |
| CH-0063 | High | W1 | Confirmed |  | urljoin + path jail; encode params; same-host redirects |
| CH-0064 | Medium | W5 | Residual | OpenAPI status_code unescaped in HTML | title/contact escaped; `generate_html_endpoint` interpolates raw `{status_code}` |
| CH-0065 | Medium | W2 | Confirmed |  | sanitize_sql_default literals only |
| CH-0066 | High | W1 | Residual | click/reload + many testers/security fetches ungated | start/login/enqueue/tester goto gated; click+reload and Freya Security/testers still raw goto |
| CH-0067 | High | W5 | Residual | visual-regression HTML unescaped | crawler HTML/JUnit use esc/html_link/safe_src/safe_css; `_visual_regression_report` does not |
| CH-0068 | High | W2 | Confirmed |  | confine_storage_path on load/delete/version; tests for ../ and symlink |
| CH-0069 | High | W3 | Confirmed |  | password/token/cookie redacted to **** on generate+save |
| CH-0070 | Medium | W4 | Confirmed |  | page.evaluate static fn + id arg |
| CH-0071 | Medium | W1 | Residual | seed page.goto ungated | HEAD+redirects allowlisted; seed navigation is not |
| CH-0072 | High | W2 | Confirmed |  | sanitize_output_name + confine_output_path on every write |
| CH-0073 | Medium | W3 | Confirmed |  | empty scores → NA; unknown severity BLOCKER |
| CH-0074 | Medium | W4 | Confirmed |  | hide_selectors via json.dumps arg not JS interpolate |
| CH-0075 | Medium | W2 | Confirmed |  | validate_dns_domain then dig -- domain |
| CH-0076 | High | W3 | Confirmed |  | HMAC baseline; adds set has_changes; fail-closed |
| CH-0077 | High | W3 | Confirmed |  | domain_errors fail is_passing; CLI exit 1 |
| CH-0078 | Medium | W2 | Residual | sibling scanners still rglob | secrets/injection/crypto/config/deps now confined; Quality taint/debt, ReDoS/SSRF/Sensitive/Race, Heimdall taint still walk/rglob |
| CH-0079 | Medium | W3 | Confirmed |  | mask_secret last-2 / length-only; span redact |
| CH-0080 | Medium | W3 | Confirmed |  | * not live-checked; unresolved or local CVE |
| CH-0081 | Medium | W3 | Residual | sibling .key HMAC plant | unsigned miss; env-less sibling key forges |
| CH-0082 | Low | W1 | Confirmed |  | default enable_assist=False; Claude not constructed |
| CH-0083 | Medium | W4 | Confirmed |  | whole-value placeholders; flatten depth/cycle-safe |
| CH-0084 | Medium | W4 | Confirmed |  | bounded regex + 1MiB/4096 caps |
| CH-0085 | Medium | W4 | Confirmed |  | FP whole-value only; testhost/AWS-test report |
| CH-0086 | High | W1 | Confirmed |  | Bearer required; refuse 0.0.0.0 without --expose; path jail; 1MiB body |
| CH-0087 | Low | W4 | Confirmed |  | commented index-url does not suppress |
| CH-0088 | Medium | W3 | Confirmed |  | D/E/NA/NOT_MEASURED/domain_errors exit 1 |
| CH-0089 | Medium | W3 | Confirmed |  | --denied maps to prohibited_licenses |
| CH-0090 | Medium | W3 | Confirmed |  | step ERROR sets overall_exit=1 |
| CH-0091 | Medium | W2 | Confirmed |  | confine_eval_path on manifest joins |
| CH-0092 | Medium | W3 | Residual | HMAC opt-in unsigned trust | jail+HMAC exist; unsigned JSON trusted if env unset |
| CH-0093 | High | W1 | Confirmed |  | https API base; quote owner/repo; same-origin redirects; token not sent off-origin |
| CH-0094 | High | W1 | Residual | common formatter GHA/HTML unsanitized | `Reporting/github_formatter.py` encodes; `common/_format_methods.py` still raw |
| CH-0095 | Low | W4 | Residual | FileParseContext.read_bytes unbounded | caps on parse_file; scan hot path reads whole file first |
| CH-0096 | Medium | W1 | Confirmed |  | project_name allowlist ^[A-Za-z_][A-Za-z0-9_-]*$ |
| CH-0097 | Medium | W1 | Confirmed |  | get/mutate WHERE issue_id AND project_path |
| CH-0098 | Medium | W3 | Residual | SLO empty still 100% | sla_checker empty→0; error_budget/sli still 100 |
| CH-0099 | Medium | W4 | Confirmed |  | centroid/bucket caps + finite checks |
| CH-0100 | Medium | W3 | Confirmed |  | invalid baseline → unknown/significant |
| CH-0101 | Low | W4 | Residual | causal_normalizer cycle walks | service_map visited+cap; causal_normalizer still loops |
| CH-0102 | High | W1 | Residual | SecretMount id/target | newline/# refused on listed fields; SecretMount interpolated unsanitized |
| CH-0103 | High | W1 | Residual | Jenkins env keys | run/env values hardened; env keys still raw in Groovy environment {} |
| CH-0104 | Medium | W1 | Confirmed |  | chart name ^[a-z0-9-]+$ before define/include |
| CH-0105 | Medium | W1 | Confirmed |  | https vault_url; harden_service_map rejects privileged/floating |
| CH-0106 | Medium | W2 | Confirmed |  | safe_pipeline_name + confine_pipeline_output |
| CH-0107 | Medium | W3 | Confirmed |  | CI HMAC + refuse * targets + expiry required |
| CH-0108 | Medium | W1 | Residual | raw HCL type/value | 0.0.0.0/0 gone; hcl_quoted on names; type/value still raw |
| CH-0109 | Medium | W3 | Residual | sibling .key HMAC plant | unsigned miss + rehash; sibling key leftover |
| CH-0110 | Medium | W1 | Residual | empty JSON still green | no cd/continue-on-error; critical gate never fails parse |
| CH-0111 | Low | W3 | Residual | --protocols still CERT_NONE | default check CERT_REQUIRED; protocol probe still CERT_NONE |
| CH-0112 | Medium | W1 | Confirmed |  | validate_target_url + safe opener before urlopen |
| CH-0113 | Medium | W1 | Confirmed |  | validate_dns_name then dig -- domain |
| CH-0114 | Medium | W3 | Confirmed |  | strict class load; crash total_issues=-1 fail-closed |
| CH-0115 | Low | W2 | Confirmed |  | confine_output_path; .json/.sarif; no abs/.. |

## Original finding index (primary / also-on-trace)

| ID | Status | Severity | Wave | Primary file | Also on trace |
|----|--------|----------|------|--------------|---------------|
| CH-0001 | Fixed | High | W1 | `.github/workflows/ci.yml` | `.github/workflows/publish.yml`, `.github/workflows/l8-perf-budgets.yml`, `Asgard/Volundr/CICD/services/action_pins.py`, `Asgard_Test/tests_Volundr/golden/ci.yml`, `_FutureItems-Security/Tools_Security/.github/workflows/security-scan.yml` |
| CH-0002 | Fixed | High | W1 | `.github/workflows/ci.yml` | `pyproject.toml`, `Asgard_Test/conftest.py` |
| CH-0003 | Fixed | High | W1 | `.github/workflows/publish.yml` | `pyproject.toml`, `MANIFEST.in`, `Asgard_Test/tests_Volundr/golden/ci-deploy.yml` |
| CH-0004 | Fixed | Medium | W1 | `.github/workflows/ci.yml` | `.github/workflows/publish.yml` |
| CH-0005 | Fixed | Medium | W1 | `.github/workflows/l8-perf-budgets.yml` | `_Docs/Testing/L8_Perf_Budget_Policy.md` |
| CH-0006 | Fixed | Low | W1 | `.pre-commit-config.yaml` | `Asgard/HooksSetup/service.py`, `Asgard/Shared/Init/_templates_python.py` |
| CH-0007 | Fixed | Medium | W2 | `Asgard/BackendInit/service.py` | `Asgard/_cli_handlers.py`, `handle_init_backend`, `Asgard/cli.py`, `folder_name` |
| CH-0008 | Fixed | Low | W2 | `Asgard/BackendInit/service.py` | `Asgard/BackendInit/templates.py` |
| CH-0009 | Fixed | Info | W5 | `Asgard/BackendInit/templates.py` | `Asgard/BackendInit/service.py` |
| CH-0010 | Fixed | Medium | W2 | `Asgard/Baseline/baseline_manager.py` | `Asgard/Heimdall/cli/handlers/baseline.py`, `Asgard/Heimdall/cli/common/scan_args.py` |
| CH-0011 | Fixed | Medium | W3 | `Asgard/Baseline/models.py` | `Asgard/Baseline/baseline_manager.py`, `json.load`, `BaselineFile(**data)`, `Asgard/Baseline/_baseline_operations.py` |
| CH-0012 | Fixed | High | W3 | `Asgard/Baseline/_baseline_operations.py` | `Asgard/Baseline/_baseline_helpers.py`, `get_violation_message`, `Asgard/Baseline/models.py`, `matches_fuzzy`, `Asgard/Heimdall/Security/models/security_models_base.py`, `SecretFinding` |
| CH-0013 | Fixed | Medium | W3 | `Asgard/Baseline/baseline_manager.py` | `Asgard/Baseline/_baseline_operations.py`, `Asgard/Heimdall/cli/handlers/baseline.py` |
| CH-0014 | Fixed | Low | W2 | `Asgard/Baseline/baseline_manager.py` |  |
| CH-0015 | Fixed | Low | W3 | `Asgard/Baseline/_baseline_helpers.py` | `Asgard/Baseline/models.py`, `remove_entry`, `Asgard/Baseline/baseline_manager.py` |
| CH-0016 | Fixed | Low | W4 | `Asgard/Bragi/Architecture/cir/builder.py` | `Asgard/Bragi/Architecture/evaluators/_lcom4.py`, `Asgard/Bragi/Architecture/evaluators/srp.py` |
| CH-0017 | Fixed | Medium | W4 | `Asgard/Bragi/Architecture/graph/service.py` | `Asgard/Bragi/Architecture/graph/propagation.py`, `Asgard/Bragi/Architecture/services/hexagonal_analyzer.py`, `analyze`, `explain_file`, `heimdall architecture hexagonal`, `layers --explain` |
| CH-0018 | Fixed | Low | W4 | `Asgard/Bragi/Architecture/graph/propagation.py` | `Asgard/Bragi/Architecture/graph/reflexion.py`, `Asgard/Bragi/Architecture/services/_architecture_config.py` |
| CH-0019 | Fixed | Low | W5 | `Asgard/Bragi/Architecture/services/_arch_reporter_markdown.py` | `Asgard/Bragi/Architecture/services/_pattern_reporter.py`, `Asgard/Bragi/Architecture/services/_solid_reporter.py`, `Asgard/Bragi/Architecture/services/_suggester_reporter.py`, `Asgard/Bragi/Architecture/services/_generic_hexagonal_checks.py`, `Asgard/Bragi/Coverage/services/_coverage_reporter.py`, `Asgard/Bragi/Dependencies/services/_license_reporter.py` (+3) |
| CH-0020 | Fixed | Info | W5 | `Asgard/Bragi/Architecture/services/_architecture_config.py` | `Asgard/Bragi/Architecture/graph/service.py`, `from_yaml` |
| CH-0021 | Fixed | Low | W4 | `Asgard/Bragi/Architecture/services/_generic_solid_checks.py` | `Asgard/Bragi/Architecture/services/_treesitter_solid_checks.py` |
| CH-0022 | Fixed | Medium | W4 | `Asgard/Bragi/Architecture/services/_treesitter_solid_checks.py` | `Asgard/Bragi/Architecture/services/solid_validator.py`, `analyze_file_generic`, `analyze_multilang` |
| CH-0023 | Fixed | Info | W1 | `.gitignore` | `CLAUDE.md` |
| CH-0024 | Fixed | High | W1 | `Asgard/Bragi/Calibration/services/szz.py` | `Asgard/Bragi/Calibration/services/rule_validator.py`, `Asgard/Bragi/Quality/services/_git_friction.py`, `Asgard/Bragi/QualityGate/services/_git_diff.py`, `Asgard/Bragi/QualityGate/services/_hotspot_ranker.py`, `Asgard/Heimdall/Security/Git/services/git_scanner.py`, `Asgard/Heimdall/cli/handlers/new_code.py` (+4) |
| CH-0025 | Fixed | Low | W4 | `Asgard/Bragi/Calibration/services/szz.py` | `Asgard/Bragi/Calibration/services/rule_validator.py` |
| CH-0026 | Fixed | Medium | W2 | `Asgard/Bragi/Calibration/services/profile_service.py` | `Asgard/Bragi/Calibration/models/calibration_models.py`, `LanguageProfile.language` |
| CH-0027 | Fixed | Medium | W3 | `Asgard/Bragi/Calibration/services/profile_service.py` | `Asgard/Bragi/Calibration/services/local_calibrator.py`, `_clamp`, `.asgard_cache/bragi_local_profile.yaml` |
| CH-0028 | Fixed | Low | W2 | `Asgard/Bragi/Calibration/services/local_calibrator.py` | `Asgard/Heimdall/cli/handlers/calibration.py`, `--write` |
| CH-0029 | withdrawn | — | — | `` |  |
| CH-0030 | Fixed | Info | W5 | `Asgard/Bragi/Calibration/models/calibration_models.py` | `Asgard/Bragi/Calibration/services/profile_service.py`, `Asgard/Bragi/Ratings/services/composite_score_engine.py` |
| CH-0031 | Fixed | Low | W4 | `Asgard/Bragi/Calibration/services/profile_service.py` | `Asgard/Bragi/Calibration/models/calibration_models.py` |
| CH-0032 | Fixed | Medium | W3 | `Asgard/Bragi/Dependencies/services/_license_cache.py` | `Asgard/Bragi/Dependencies/services/license_checker.py`, `use_cache` |
| CH-0033 | Fixed | Medium | W1 | `Asgard/Bragi/Dependencies/services/license_checker.py` |  |
| CH-0034 | Fixed | Low | W2 | `Asgard/Bragi/Dependencies/services/license_checker.py` | `Asgard/Bragi/Dependencies/services/requirements_checker.py`, `_extract_package_name` |
| CH-0035 | Fixed | High | W2 | `Asgard/Bragi/Dependencies/services/requirements_checker.py` | `Asgard/Heimdall/cli/handlers/syntax.py`, `target_file=getattr(args, 'target_file', ...)` |
| CH-0036 | Fixed | Medium | W3 | `Asgard/Bragi/Dependencies/services/_vuln_cache.py` | `Asgard/Bragi/Dependencies/services/vulnerability_checker.py`, `_post_batch_cached`, `_query_nvd_cached` |
| CH-0037 | Fixed | Low | W2 | `Asgard/Bragi/Dependencies/services/_vuln_cache.py` | `cache_key(namespace, payload)` |
| CH-0038 | Fixed | Medium | W3 | `Asgard/Bragi/Dependencies/models/license_models.py` | `Asgard/Bragi/Dependencies/services/license_checker.py`, `_license_policy.py` |
| CH-0039 | Fixed | Low | W4 | `Asgard/Bragi/Dependencies/services/graph_service.py` | `{scan_path}/.asgard_cache/bragi_dep_graph.json` |
| CH-0040 | Fixed | Medium | W2 | `Asgard/Bragi/Performance/utilities/performance_utils.py` | `Asgard/Bragi/Performance/services/cache_analyzer_service.py`, `cpu_profiler_service.py`, `database_analyzer_service.py`, `memory_profiler_service.py`, `static_performance_service.py` |
| CH-0041 | Fixed | Low | W2 | `Asgard/Bragi/Quality/BugDetection/services/bug_detector.py` |  |
| CH-0042 | Fixed | Medium | W2 | `Asgard/Bragi/Quality/languages/javascript/services/js_analyzer.py` | `Asgard/Bragi/Quality/languages/cpp/services/cpp_analyzer.py`, `csharp/services/csharp_analyzer.py`, `go/services/go_analyzer.py`, `java/services/java_analyzer.py`, `php/services/php_analyzer.py`, `ruby/services/ruby_analyzer.py` (+4) |
| CH-0043 | Fixed | Medium | W3 | `Asgard/Bragi/Quality/languages/javascript/services/_js_security_rules.py` | `Asgard/Bragi/Quality/languages/php/services/_php_rules.py`, `Asgard/Bragi/Quality/languages/ruby/services/_ruby_rules.py`, `Asgard/Bragi/Quality/languages/rust/services/_rust_rules.py`, `Asgard/Bragi/Quality/models/env_fallback_models.py`, `Asgard/Bragi/Quality/services/_env_fallback_reporter.py`, `Asgard/Heimdall/cli/handlers/lang_analyzers.py` |
| CH-0044 | Fixed | Info | W5 | `Asgard/Bragi/Quality/languages/javascript/services/_js_rules.py` |  |
| CH-0045 | Fixed | Low | W4 | `Asgard/Bragi/Quality/languages/php/services/_php_rules.py` | `Asgard/Bragi/Quality/languages/php/services/php_analyzer.py` |
| CH-0046 | Fixed | Medium | W5 | `Asgard/Bragi/Quality/services/_code_smell_report_html.py` | `Asgard/Bragi/Quality/services/code_smell_detector.py`, `Asgard/Bragi/Quality/services/_code_smell_visitor.py`, `Asgard/Heimdall/cli/handlers/_base.py`, `Asgard/Heimdall/cli/handlers/quality_file_length.py`, `Asgard/Heimdall/cli/handlers/scan_html.py`, `Asgard/Reporting/_html_report_builders.py` (+1) |
| CH-0047 | Fixed | Medium | W3 | `Asgard/Bragi/Quality/services/_debt_state_store.py` | `{scan_root}/.asgard_cache/bragi_debt_state.json` |
| CH-0048 | Fixed | Medium | W3 | `Asgard/Bragi/Quality/services/_incremental_cache.py` | `Asgard/Bragi/Quality/services/incremental_scanner.py` |
| CH-0049 | Fixed | High | W1 | `Asgard/Bragi/Quality/services/_syntax_linters.py` | `Asgard/Bragi/Quality/services/_mypy_runner.py`, `Asgard/Bragi/Quality/services/_pyright_runner.py` |
| CH-0050 | Fixed | High | W2 | `Asgard/Bragi/Quality/services/_pyright_runner.py` | `Asgard/Bragi/Quality/services/type_checker.py` |
| CH-0051 | Fixed | High | W3 | `Asgard/Bragi/QualityGate/baseline_store.py` | `Asgard/Bragi/QualityGate/services/quality_gate_evaluator.py`, `{scan}/.asgard_cache/bragi_fingerprint_baseline.json` |
| CH-0052 | Fixed | Medium | W3 | `Asgard/Bragi/QualityGate/fingerprint.py` | `Asgard/Bragi/QualityGate/services/_differential_engine.py`, `ensure_fingerprint` |
| CH-0053 | Fixed | Medium | W4 | `Asgard/Bragi/Quality/services/parallel_scanner.py` |  |
| CH-0054 | Fixed | Medium | W3 | `Asgard/Bragi/Ratings/services/ratings_calculator.py` | `Asgard/Bragi/Ratings/services/_report_extractors.py` |
| CH-0055 | Fixed | High | W5 | `Asgard/Dashboard/services/html_renderer.py` | `Asgard/Dashboard/adapters/web/dashboard_handler.py`, `Asgard/Dashboard/services/_html_renderer_pages.py`, `Asgard/Dashboard/services/_html_helpers.py` |
| CH-0056 | Fixed | Medium | W1 | `Asgard/Dashboard/adapters/web/dashboard_handler.py` | `Asgard/Dashboard/server.py`, `--host`, `localhost`, `Asgard/Heimdall/cli/handlers/mcp.py`, `run_dashboard` |
| CH-0057 | Fixed | Medium | W2 | `Asgard/Forseti/Alignment/services/alignment_loader_service.py` | `forseti align check`, `forseti audit`, `alignment-config.yaml` |
| CH-0058 | Fixed | High | W2 | `Asgard/Forseti/CodeGen/services/_python_generator_helpers.py` | `Asgard/Forseti/CodeGen/services/_typescript_generator_helpers.py`, `Asgard/Forseti/CodeGen/services/_golang_generator_client_helpers.py` |
| CH-0059 | Fixed | High | W2 | `Asgard/Forseti/JSONSchema/services/_ref_resolver_helpers.py` | `Asgard/Forseti/JSONSchema/services/schema_compiler_service.py`, `schema_validator_service.py` |
| CH-0060 | Fixed | High | W1 | `Asgard/Forseti/GraphQL/services/introspection_service.py` |  |
| CH-0061 | Fixed | High | W1 | `Asgard/Forseti/MockServer/services/_mock_server_generator_helpers.py` | `Asgard/Forseti/MockServer/models/mock_models.py`, `host`, `mock_server_generator.py` |
| CH-0062 | Fixed | High | W1 | `Asgard/Forseti/MockServer/services/validation_proxy_service.py` | `_validation_proxy_helpers.py` |
| CH-0063 | Fixed | High | W1 | `Asgard/Forseti/LiveContract/services/live_validator_service.py` | `probe_planner_service.py`, `workflow_runner_service.py` |
| CH-0064 | Fixed | Medium | W5 | `Asgard/Forseti/Documentation/services/docs_generator.py` | `_docs_generator_helpers.py`, `templates/base.html`, `{{ title }}` |
| CH-0065 | Fixed | Medium | W2 | `Asgard/Forseti/Database/services/_schema_analyzer_helpers.py` | `migration_generator_service.py`, `_schema_diff_helpers.py` |
| CH-0066 | Fixed | High | W1 | `Asgard/Freya/Integration/services/_crawler_discovery.py` | `site_crawler.py`, `_crawler_spa.py`, `_crawler_page_tester.py`, `page.goto`, `Asgard/Freya/Performance/services/page_load_analyzer.py`, `resource_timing_analyzer.py` (+3) |
| CH-0067 | Fixed | High | W5 | `Asgard/Freya/Integration/services/html_reporter.py` | `_crawler_report.py`, `Asgard/Freya/cli/_formatters_accessibility.py` |
| CH-0068 | Fixed | High | W2 | `Asgard/Freya/Integration/services/baseline_manager.py` | `_baseline_manager_helpers.py` |
| CH-0069 | Fixed | High | W3 | `Asgard/Freya/Integration/services/_crawler_report.py` | `site_crawler.py` |
| CH-0070 | Fixed | Medium | W4 | `Asgard/Freya/Accessibility/services/_aria_validator_checks_part2.py` |  |
| CH-0071 | Fixed | Medium | W1 | `Asgard/Freya/Links/services/link_validator.py` | `_link_validator_helpers.py` |
| CH-0072 | Fixed | High | W2 | `Asgard/Freya/Visual/services/_screenshot_capture_helpers.py` | `screenshot_capture.py`, `visual_regression.py`, `Asgard/Freya/Responsive/services/breakpoint_tester.py` |
| CH-0073 | Fixed | Medium | W3 | `Asgard/Freya/Scoring/services/grade_calculator.py` | `quality_gate.py`, `severity_mapper.py` |
| CH-0074 | Fixed | Medium | W4 | `Asgard/Freya/Visual/services/_screenshot_capture_helpers.py` |  |
| CH-0075 | Fixed | Medium | W2 | `Asgard/Heimdall/Security/DNS/services/dns_checker.py` |  |
| CH-0076 | Fixed | High | W3 | `Asgard/Heimdall/Security/FileIntegrity/services/file_integrity_checker.py` | `.file_integrity_baseline.json` |
| CH-0077 | Fixed | High | W3 | `Asgard/Heimdall/Security/services/static_security_service.py` | `Asgard/Heimdall/Security/models/security_models_findings.py`, `is_passing` |
| CH-0078 | Fixed | Medium | W2 | `Asgard/Heimdall/Security/utilities/_scan_utils.py` | `Asgard/Heimdall/Security/services/secrets_detection_service.py`, `Asgard/Heimdall/Security/services/injection_detection_service.py`, `Asgard/Heimdall/Security/services/cryptographic_validation_service.py`, `Asgard/Heimdall/Security/services/config_secrets_scanner.py`, `Asgard/Heimdall/Security/services/dependency_vulnerability_service.py`, `Asgard/Heimdall/cli/handlers/_security_dispatch.py` |
| CH-0079 | Fixed | Medium | W3 | `Asgard/Heimdall/Security/utilities/security_utils.py` | `Asgard/Heimdall/Security/services/secrets_detection_service.py`, `Asgard/Heimdall/Security/services/_secrets_detection_helpers.py`, `Asgard/Heimdall/Security/services/_static_security_report_json_md.py`, `Asgard/Heimdall/Security/services/_config_secrets_helpers.py`, `Asgard/Heimdall/Security/services/_config_secrets_report.py`, `_FutureItems-Security/Tools_Security/secrets_scanner.py` |
| CH-0080 | Fixed | Medium | W3 | `Asgard/Heimdall/Security/services/_live_vulnerability_lookup.py` | `Asgard/Heimdall/Security/services/_vulnerability_database.py`, `Asgard/Heimdall/Security/services/dependency_vulnerability_service.py`, `Asgard/Heimdall/Security/services/_requirements_parser.py` |
| CH-0081 | Fixed | Medium | W3 | `Asgard/Heimdall/Security/triage/services/triage_cache.py` | `Asgard/Heimdall/Security/triage/services/triage_service.py` |
| CH-0082 | Fixed | Low | W1 | `Asgard/Heimdall/Security/triage/services/triage_adapter.py` | `Asgard/Heimdall/Security/triage/services/triage_service.py` |
| CH-0083 | Fixed | Medium | W4 | `Asgard/Heimdall/Security/services/_config_secrets_helpers.py` | `Asgard/Heimdall/Security/services/config_secrets_scanner.py` |
| CH-0084 | Fixed | Medium | W4 | `Asgard/Heimdall/Security/services/_injection_patterns.py` | `Asgard/Heimdall/Security/services/injection_detection_service.py` |
| CH-0085 | Fixed | Medium | W4 | `Asgard/Heimdall/Security/services/_secret_patterns.py` | `Asgard/Heimdall/Security/services/_secrets_detection_helpers.py`, `Asgard/Heimdall/Security/services/secrets_detection_service.py` |
| CH-0086 | Fixed | High | W1 | `Asgard/Heimdall/cli/handlers/mcp.py` | `Asgard/MCP/server/asgard_mcp_server.py`, `Asgard/MCP/server/_mcp_tools.py`, `Asgard/MCP/server/__init__.py`, `asguardian-mcp` |
| CH-0087 | Fixed | Low | W4 | `Asgard/Heimdall/Security/services/_supply_chain_analysis.py` | `Asgard/Heimdall/Security/services/dependency_vulnerability_service.py` |
| CH-0088 | Fixed | Medium | W3 | `Asgard/Heimdall/cli/handlers/ratings.py` | `Asgard/Heimdall/cli/handlers/security.py`, `run_compliance_analysis`, `return 0` |
| CH-0089 | Fixed | Medium | W3 | `Asgard/Heimdall/cli/handlers/syntax.py` | `Asgard/Heimdall/cli/common/scan_args.py`, `Asgard/Bragi/Dependencies/models/license_models.py` |
| CH-0090 | Fixed | Medium | W3 | `Asgard/Heimdall/cli/handlers/scan.py` | `Asgard/Heimdall/cli/handlers/scan_steps_1_6.py`, `Asgard/Heimdall/cli/handlers/scan_steps_7_11.py` |
| CH-0091 | Fixed | Medium | W2 | `Asgard/Heimdall/evaluation/vendored_corpus.py` | `Asgard/Heimdall/evaluation/corpus.py` |
| CH-0092 | Fixed | Medium | W3 | `Asgard/Heimdall/evaluation/calibration.py` | `Asgard/Heimdall/cli/handlers/evaluation.py`, `--save-calibration` |
| CH-0093 | Fixed | High | W1 | `Asgard/Reporting/PRDecoration/services/github_decorator.py` | `Asgard/Reporting/PRDecoration/services/gitlab_decorator.py`, `Asgard/Reporting/PRDecoration/models/decoration_models.py` |
| CH-0094 | Fixed | High | W1 | `Asgard/Reporting/github_formatter.py` | `Asgard/Reporting/_github_format_helpers.py` |
| CH-0095 | Fixed | Low | W4 | `Asgard/Heimdall/treesitter/file_context.py` | `Asgard/Heimdall/treesitter/_parser_pool.py`, `Asgard/Heimdall/treesitter/_query_runner.py` |
| CH-0096 | Fixed | Medium | W1 | `Asgard/Shared/Init/linter_initializer.py` | `Asgard/Shared/Init/_templates_python.py`, `Asgard/Heimdall/cli/handlers/init_linter.py` |
| CH-0097 | Fixed | Medium | W1 | `Asgard/Shared/Issues/services/_issue_repository.py` | `Asgard/Shared/Issues/services/issue_tracker.py`, `Asgard/Heimdall/cli/handlers/issues.py`, `Asgard/MCP/server/_mcp_tools.py` |
| CH-0098 | Fixed | Medium | W3 | `Asgard/Verdandi/Analysis/services/sla_checker.py` | `Asgard/Verdandi/Analysis/models/analysis_models.py`, `Asgard/Verdandi/SLO/models/slo_models.py`, `Asgard/Verdandi/SLO/services/error_budget_calculator.py`, `Asgard/Verdandi/SLO/services/sli_tracker.py`, `Asgard/Verdandi/SLO/services/_sli_aggregation.py` |
| CH-0099 | Fixed | Medium | W4 | `Asgard/Verdandi/Analysis/services/quantile_sketch.py` | `Asgard/Verdandi/cli/_parser_flags.py`, `Asgard/Verdandi/cli/__init__.py`, `sketch-merge`, `Asgard/Verdandi/cli/handlers_new_apis.py` |
| CH-0100 | Fixed | Medium | W3 | `Asgard/Verdandi/Anomaly/services/baseline_comparator.py` | `Asgard/Verdandi/Anomaly/models/anomaly_models.py`, `Asgard/Verdandi/Anomaly/services/_comparator_helpers.py` |
| CH-0101 | Fixed | Low | W4 | `Asgard/Verdandi/APM/services/service_map_builder.py` | `Asgard/Verdandi/Tracing/services/_path_helpers.py`, `Asgard/Verdandi/Tracing/services/causal_normalizer.py`, `Asgard/Verdandi/Tracing/services/critical_path_analyzer.py` |
| CH-0102 | Fixed | High | W1 | `Asgard/Volundr/Docker/services/dockerfile_generator.py` | `Asgard/Volundr/Docker/models/docker_models.py` |
| CH-0103 | Fixed | High | W1 | `Asgard/Volundr/CICD/services/pipeline_generator_helpers.py` | `Asgard/Volundr/CICD/services/context_hardening.py` |
| CH-0104 | Fixed | Medium | W1 | `Asgard/Volundr/Helm/services/_chart_generator_templates.py` | `Asgard/Volundr/Helm/services/_chart_generator_extras.py`, `Asgard/Volundr/Helm/services/chart_generator.py` |
| CH-0105 | Fixed | Medium | W1 | `Asgard/Volundr/CICD/models/cicd_models.py` | `Asgard/Volundr/CICD/services/pipeline_generator_helpers.py`, `Asgard/Volundr/CICD/services/action_pins.py`, `Asgard/Volundr/Compose/services/compose_generator_helpers.py`, `Asgard/Volundr/Helm/models/helm_models.py` |
| CH-0106 | Fixed | Medium | W2 | `Asgard/Volundr/CICD/services/pipeline_generator.py` | `Asgard/Volundr/CICD/services/pipeline_generator_helpers.py`, `Asgard/Volundr/Scaffold/services/microservice_scaffold.py`, `Asgard/Volundr/Scaffold/services/monorepo_scaffold.py` |
| CH-0107 | Fixed | Medium | W3 | `Asgard/Volundr/Validation/models/suppression_models.py` | `Asgard/Volundr/Validation/services/suppression_engine.py`, `Asgard/Volundr/Validation/services/validation_engine.py`, `ignore_rules` |
| CH-0108 | Fixed | Medium | W1 | `Asgard/Volundr/Terraform/services/_module_builder_blocks.py` | `Asgard/Volundr/Terraform/services/_module_builder_generators.py` |
| CH-0109 | Fixed | Medium | W3 | `Asgard/common/_hash_cache.py` | `Asgard/common/_incremental_models.py`, `_FutureItems-Security/Tools_Security/file_integrity_checker.py` |
| CH-0110 | Fixed | Medium | W1 | `_FutureItems-Security/Tools_Security/.github/workflows/security-scan.yml` | `_FutureItems-Security/Tools_Security/security_api.py`, `_FutureItems-Security/Tools_Security/secrets_scanner.py` |
| CH-0111 | Fixed | Low | W3 | `_FutureItems-Security/Tools_Security/ssl_checker.py` | `_FutureItems-Security/Tools_Security/security_toolkit.py` |
| CH-0112 | Fixed | Medium | W1 | `_FutureItems-Security/Tools_Security/cors_checker.py` | `_FutureItems-Security/Tools_Security/http_security_headers.py`, `_FutureItems-Security/Tools_Security/port_scanner.py`, `_FutureItems-Security/Tools_Security/security_toolkit.py` |
| CH-0113 | Fixed | Medium | W1 | `_FutureItems-Security/Tools_Security/dns_security_checker.py` | `_FutureItems-Security/Tools_Security/security_toolkit.py` |
| CH-0114 | Fixed | Medium | W3 | `_FutureItems-Security/Tools_Security/security_api.py` | `_FutureItems-Security/Tools_Security/security_toolkit.py`, `_FutureItems-Security/Tools_Security/.github/workflows/security-scan.yml` |
| CH-0115 | Fixed | Low | W2 | `_FutureItems-Security/Tools_Security/security_api.py` | `_FutureItems-Security/Tools_Security/security_toolkit.py` |

## Summary (this pass)

| Severity | Reopened | Residual | New Open (CHC) | Confirmed | Accepted still | Vacated |
|----------|----------|----------|----------------|-----------|----------------|---------|
| Critical | 0 | 0 | 0 | 0 | 0 | 0 |
| High     | 0 | 8 | 4 | 20 | 0 | 0 |
| Medium   | 0 | 15 | 8 | 44 | 0 | 0 |
| Low      | 0 | 6 | 1 | 16 | 0 | 0 |
| Info     | 0 | 2 | 0 | 3 | 0 | 0 |

## Reopened / residual detail

### CH-0001 — Residual (generated action tags)

- **Leftover status:** Fixed
- **Fixed in:** 1a46dac
- **Implementation note:** Scaffold CI/CD and Docker scan-workflow emit pinned("actions/checkout@v4") SHAs; tests refuse @vN tags.
- **Original sink (closed):** live `.github/workflows/*.yml` `uses:` were `@v4`/`@v5` / `pypa@release/v1`. Current `ci.yml` / `publish.yml` / `l8-perf-budgets.yml` use 40-char SHAs matching `KNOWN_ACTION_PINS`. Dependabot + Renovate pin updaters exist.
- **Leftover:** generators still emit mutable tags.
  - `Asgard/Volundr/Scaffold/services/_monorepo_infra_templates.py` ~186/198/212: `uses: actions/checkout@v4`
  - `Asgard/Volundr/Docker/services/dockerfile_generator.py` `_scan_workflow` ~153: `uses: actions/checkout@v4`
- **Evidence:** live workflows have no `@v[0-9]` tags; generated artifacts do.
- **Planned leftover fix:** emit `KNOWN_ACTION_PINS` SHAs (or refuse to emit unpinned `uses:`) in scaffold + scan-workflow templates. Tests that generated YAML has no `@vN` action tags.

### CH-0024 — Residual (textconv / extra GIT_*)

- **Leftover status:** Fixed
- **Fixed in:** 8904394
- **Implementation note:** Isolated git adds --no-textconv and wipes GIT_EXEC_PATH/GIT_WORK_TREE/GIT_CONFIG_*.
- **Original sink (closed):** `szz._run_git` → `run_isolated_git` (`Asgard/Shared/common/_git_isolated.py`). `--no-ext-diff` on diff/log/show/blame; `-c diff.external=` / `core.fsmonitor=` / `core.pager=` / `alias.{cmd}=`; env pops `GIT_EXTERNAL_DIFF`/`GIT_PAGER`/`GIT_DIR`; `GIT_CONFIG_NOSYSTEM=1` + `GIT_CONFIG_GLOBAL=os.devnull`. Tests plant `diff.external` and `GIT_EXTERNAL_DIFF`.
- **Leftover:** local `.git/config` `diff.*.textconv` / filter drivers still execute on `git diff` / `git blame`. `GIT_EXEC_PATH`, `GIT_WORK_TREE`, `GIT_CONFIG_PARAMETERS` / `GIT_CONFIG_COUNT` not wiped.
- **Trace:** `compute_szz` → `_fix_commit_hunks` (`git diff`) / `_blame_inducing_commits` (`git blame`) → isolated helper → still honors repo textconv.
- **Planned leftover fix:** `--no-textconv`; blank `diff.*.textconv` / filter drivers; drop additional `GIT_*` override vars. Test a planted textconv is not executed.

### CH-0102 — Residual (SecretMount)

- **Leftover status:** Fixed
- **Fixed in:** 2af3540
- **Implementation note:** SecretMount id/target pass _require_safe_field; newline in id is refused.
- **Original sink (closed):** `_require_safe_field` rejects CR/LF/`#` on name/syntax/args/labels/stage image/workdir/user/copy/run/env/entrypoint/cmd. HEALTHCHECK uses `json.dumps`. Trivy digest-pinned. `docker.sock` only if `privileged_scan`.
- **Leftover:** `_mount_flags` interpolates `mount.id` / `mount.target` into `RUN --mount=...` without `_require_safe_field`. Newline/`#` becomes another Dockerfile instruction. CLI `--secret-mounts` feeds this.
- **Location:** `dockerfile_generator.py` `_mount_flags` ~238-249; `_assert_safe_config` ~177-217 does not walk `secret_mounts`.
- **Planned leftover fix:** run `_require_safe_field` on `SecretMount.id`/`target`; test newline in mount id.

### CH-0103 — Residual (Jenkins env keys)

- **Leftover status:** Fixed
- **Fixed in:** 0c2402d
- **Implementation note:** Jenkins env keys must match [A-Za-z_][A-Za-z0-9_]*; hostile keys raise.
- **Original sink (closed):** `generate_jenkins` calls `harden_steps`; `_jenkins_safe_script` refuses triple-quote/CR; values go through `_jenkins_groovy_string` (quoted `sh(...)`, not raw triple-quoted). Tests refuse triple-quote breakout in `run`.
- **Leftover:** `config.env` keys interpolated raw into the Groovy `environment` block (~596-597). A key with newline or quote breaks out.
- **Planned leftover fix:** allowlist env keys `[A-Za-z_][A-Za-z0-9_]*` (or refuse quote/newline). Test a hostile key.


### CH-0006 — Residual (generated hook template)

- **Leftover status:** Fixed
- **Fixed in:** 317751e
- **Implementation note:** Python init PRE_COMMIT_CONFIG now includes detect-secrets (same rev as the repo hook).
- **Original sink (closed):** repo `.pre-commit-config.yaml` uses 40-char `rev` SHAs, `additional_dependencies` pinned with `==`, and a `detect-secrets` hook.
- **Leftover:** `Asgard/Shared/Init/_templates_python.py` `PRE_COMMIT_CONFIG` still has SHA revs + `==` extras but **omits detect-secrets**. `asguardian init` projects do not get the secret-scan hook the repo itself now uses.
- **Planned leftover fix:** copy the repo hook list (including detect-secrets) into the Python init template. Test generated config contains `id: detect-secrets`.

### CH-0009 — Residual (ENV/ still in template)

- **Leftover status:** Fixed
- **Fixed in:** 018d0db
- **Implementation note:** Dropped ENV/ from BackendInit GITIGNORE_FULL so a directory named ENV is not ignored.
- **Planned leftover fix:** drop ENV/ from the generated gitignore.

### CH-0066 — Residual (click / reload / testers / security fetches)

- **Original sink (closed):** crawl `start_url` / `login_url` / discovery enqueue / tester `goto` use `validate_navigation_url` + `safe_goto`. SPA enqueue uses `should_crawl`. `file:` and literal RFC1918 are rejected before those `goto`s.
- **Leftover:** Playwright still navigates **before** the allowlist on:
  - `site_crawler.py` login `submit` + `wait_for_url` (~183-196)
  - `_crawler_spa.py` `item.click()` + `expect_navigation` (~151-157)
  - `_crawler_spa.py` `page.reload()` (~98)
  - Freya Responsive/Visual testers: `breakpoint_tester`, `mobile_compatibility`, `touch_target_validator`, `viewport_tester`, `layout_validator`, `style_validator`, screenshot helper `page.goto`
  - Freya Security: `mixed_content_checker` / `sri_checker` `page.goto`; `security_header_scanner` `httpx.AsyncClient(follow_redirects=True).get` with no scheme/host allowlist
  - `PlaywrightUtils.navigate` raw `page.goto`; `unified_tester` / runners never call `safe_goto`
  Post-checks use `resolve_host=False`, so a public name that later resolves internally is not DNS-checked.
- **Impact:** Hostile login/SPA/tester/security URL can already hit `file:` / metadata / RFC1918; the later validate only drops the URL from the crawl set.
- **Planned leftover fix:** do not follow unknown navigations; intercept/route-abort non-allowlisted schemes/hosts; re-validate `page.url` with `resolve_host=True` after click/reload/submit; route testers + header/SRI/mixed through `safe_goto` / `validate_navigation_url`.


### CH-0051 — Residual (sibling HMAC key)

- **Leftover status:** Fixed
- **Implementation note:** HMAC keys are env-only; sibling .key files are never read for verify. Cluster with CH-0011/0017/0047/0048/0081/0109.
- **Original sink (closed):** unsigned/rewritten fingerprint baseline JSON cannot hide PR findings. `FingerprintBaselineStore._read_all` HMAC-SHA256 + `compare_digest`; mismatch → empty → evaluator `NOT_EVALUATED`.
- **Leftover:** without `ASGARD_QG_HMAC_KEY`, the same writer can plant sibling `bragi_fingerprint_baseline.json.key` + matching `hmac` and hide findings. Commit-SHA binding from the planned fix is not implemented.
- **This is the textbook Residual leftover** (same uid plants `.key` + signed baseline).
- **Planned leftover fix:** require env-only key in CI; refuse auto-created sibling keys for verify; bind baseline to commit SHA.

### CH-0071 — Residual (seed `page.goto`)

- **Original sink (closed):** extracted-link HEADs go through `validate_link_url` / `validate_navigation_url` (http(s) only, block RFC1918 unless `allow_internal`); redirects re-validated before follow.
- **Leftover:** `_extract_links` still `page.goto(url)` with no scheme/host policy (`link_validator.py` ~126-134). Seed navigation is ungated; only HEADs are.
- **Planned leftover fix:** `safe_goto` / `validate_navigation_url` on the seed URL before Playwright navigation.

### CH-0108 — Residual (raw HCL type/value)

- **Original sink (closed):** SG egress is self-only (no `0.0.0.0/0`). Names/strings go through `hcl_quoted` / `require_hcl_identifier`.
- **Leftover:** `var.type`, `output.value`, `var.validation` still interpolated raw (`_module_builder_generators.py`). Newlines in `type` can break out of the block.
- **Planned leftover fix:** reject CR/LF in type/value/validation or quote them. Test a newline in `var.type`.

### CH-0110 — Residual (empty JSON still green)

- **Original sink (closed):** workflow no longer `cd security-tools` or `continue-on-error`. SARIF empty-file check is fail-closed. SHA-pinned actions.
- **Leftover:** critical gate treats failure as `total_issues < 0` (never true). Empty/zero-issue JSON stays green. No `test -s security-report.json`.
- **Planned leftover fix:** fail if report missing/unreadable or `total_issues` parse fails; treat scanner crash as failure.


### CH-0008 — Residual (parent-dir symlink)

- **Original sink (closed):** leaf `.gitignore` / `_write_if_absent` skip `path.is_symlink()`.
- **Leftover:** `mkdir` then write under `apis/` etc. follows a directory symlink. Populate-if-exists makes this reachable.
- **Planned leftover fix:** refuse symlink directories; `O_NOFOLLOW` on create.

### CH-0009 — Residual (`ENV/`)

- **Original sink (closed):** `lib/`, `lib64/`, `env/` removed from `GITIGNORE_FULL`.
- **Leftover:** `ENV/` remains. On case-insensitive FS it rematches `env/`.
- **Planned leftover fix:** drop `ENV/` or document it as Windows-only.

### CH-0011 — Residual (sibling HMAC key)

- Same leftover class as CH-0051: unsigned JSON fail-closed; without `ASGARD_BASELINE_HMAC_KEY` a planted `.asgard-baseline.json.key` forges suppressions.

### CH-0078 — Residual (sibling rglob walkers)

- **Original sink (closed):** `iter_confined_files` skips symlinks and jails resolve. Secrets/injection/crypto/config/deps + TLS certificate/cipher/protocol analyzers use it (re-confirmed this pass).
- **Leftover:** still unconfined:
  - `Asgard/Bragi/Quality/services/taint/taint_analyzer.py` `Path.rglob("*")` then `read_text`
  - `technical_debt_analyzer.analyze_delta` `path.rglob("*")`
  - `Asgard/Bragi/Quality/utilities/file_utils.py` `os.walk` keeps file symlinks
  - Heimdall `TaintAnalysis/services/taint_analyzer.py` `rglob("*.py")`
  - ReDoS / SSRF / SensitiveData / RaceCondition scanners `os.walk`
  - `log_analyzer.py`, `scan_steps_7_11.py` (prior leftover)
- **Planned leftover fix:** route remaining walkers through `iter_confined_files` / `iter_confined_regular_files`.

### CH-0111 — Residual (`--protocols` CERT_NONE)

- **Original sink (closed):** default `check_certificate` uses `CERT_REQUIRED`.
- **Leftover:** `check_protocol_support` still `CERT_NONE` and connects to the operator host.
- **Planned leftover fix:** use default context or label the probe unauthenticated.


### CH-0017 / CH-0047 / CH-0048 / CH-0081 / CH-0109 — Residual (sibling HMAC keys)

Same leftover class as CH-0011/CH-0051: unsigned JSON fail-closed; without the env key a planted sibling `.key` + matching HMAC forges the cache (arch bounds, debt state, incremental, triage, common FileHashCache).

### CH-0019 — Residual (unconverted MD reporters)

- **Original sink (closed):** listed architecture/coverage/license/oop tables use `md_cell`.
- **Leftover:** `_layer_reporter.py` and `_hexagonal_reporter.py` still interpolate names/paths/messages raw. `md_cell(max_len=…)` slices after escaping, so a trailing `\|` can become `\` and swallow the next table `|`.

### CH-0020 — Residual (incomplete YAML coerce)

- File/size/`layers` mapping checks exist. `level` / `allowed_imports` / `rules.max_module_fan_out` still untyped.

### CH-0043 — Residual (other-language snippets)

- JS/PHP/Ruby/Rust mask credential snippets. Java/Go/C#/C++/shell still set `code_snippet=line`.

### CH-0092 — Residual (unsigned calibration map)

- Path jail + HMAC exist. HMAC is opt-in (`HEIMDALL_CALIBRATION_HMAC_KEY`); unsigned JSON under CWD still loads if env unset.

### CH-0095 — Residual (unbounded disk read)

- `parse_file` stats first. `FileParseContext.parse` `read_bytes()` then checks size.

### CH-0098 — Residual (SLO empty = healthy)

- `sla_checker` empty → 0 / BREACHED. `error_budget_calculator` / `sli_tracker` still treat zero events as 100% / 1.0.
- Same class: `normalization/scoring.py` `multiplicative_security_score({})` is 100; `SecurityReport` defaults `score_counts or {}`. Incomplete CST (CHC-0009) still looks like a perfect score.
- Same class (this pass): `APMReport.health_score` default 100 + `trace_aggregator.aggregate([])`; `vitals_calculator._calculate_score([])` → 100 / GOOD; empty image/link category scores still 100.

### CH-0101 — Residual (causal cycle walks)

- `service_map_builder` has visited + cap. `causal_normalizer._collect_subtree_ids` / `truncate_async` still walk cyclic parents.

### CH-0067 — Residual (visual-regression HTML)

- **Leftover status:** Fixed
- **Implementation note:** html.escape on suite_name, baseline filename, method, status.

- **Original sink (closed):** Freya crawler HTML/JUnit go through `esc` / `html_link` / `safe_src` / `safe_css` (`html_reporter.py`, `_crawler_report.py`).
- **Leftover:** `Asgard/Freya/Visual/services/_visual_regression_report.py` interpolates `suite_name` and `Path(baseline_path).name` into HTML with no escape, then `write_text`.
- **Planned leftover fix:** reuse `_report_escape.esc` on every interpolated field; scheme-allowlist any future `src`/`href`.

### CH-0094 — Residual (common formatter)

- **Leftover status:** Fixed
- **Implementation note:** GHA encoder escapes % CR/LF , : ; HTML formatters use html.escape.
- **Original sink (closed):** `Reporting/github_formatter.py` percent-encodes `%` CR/LF `:` `/` `::` and strips C0.
- **Leftover:** `Asgard/common/_format_methods.py` `format_result_github` still emits `file={file_path}::{message}` raw; `format_result_html` / `format_results_html` interpolate title/location/message without `html.escape`.
- **Planned leftover fix:** share the GHA encoder; `html.escape(..., quote=True)` on HTML formatters.

### CH-0064 — Residual (OpenAPI status_code HTML)

- **Leftover status:** Fixed
- **Implementation note:** generate_html_endpoint html.escapes status_code.
- **Original sink (closed):** docs title `html.escape`; contact href `_safe_href` http(s)/mailto; `custom_css` not interpolated.
- **Leftover:** `_docs_generator_helpers.generate_html_endpoint` ~189 interpolates `{status_code}` raw. A hostile OpenAPI response key is XSS if the HTML is served.
- **Planned leftover fix:** `html.escape(status_code)` (and class tokens allowlisted).

### CH-0046 — Residual (file-length / scan HTML)

- **Leftover status:** Fixed
- **Implementation note:** scan_html and quality HTML escape scan_path / relative_path.
- **Original sink (closed):** smell HTML uses `_esc` on interpolated fields.
- **Leftover:** `quality_file_length.py` HTML interpolates `scan_path` / `relative_path` raw; `scan_html.py` title/`detail` for ERROR raw.
- **Planned leftover fix:** reuse `_esc` on every interpolated field.


## New findings

### CHC-0001 — Draft L8 still editable-installs the PR tree

- **Status:** Fixed
- **Implementation note:** PR path installs pytest/benchmark/pyyaml without `-e`; PYTHONPATH=workspace. Test asserts `pip install -e` is gated by pull_request.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-829
- **Primary file:** `.github/workflows/l8-perf-budgets.yml`
- **Also on trace:** `.github/workflows/ci.yml`
- **Related original:** CH-0002, CH-0005
- **Location:** job `l8-budgets` install step (~39-41)
- **Trace:** `on.pull_request` → (after removing `if: false`) `pip install -e .` → pytest imports package setup on the runner
- **Impact:** Enabling the draft without the ci.yml PR split reintroduces untrusted setup/package exec on CI (ubuntu-latest, not ARC).
- **Evidence:** `pip install -e .` is unconditional; no `github.event_name != 'pull_request'` gate. Job still `if: false`.
- **Planned fix:** Mirror ci.yml: install deps without `-e` on `pull_request`, or keep the draft disabled until that gate exists. Add a test that the L8 workflow has no unguarded `pip install -e`.
- **Fix wave:** W1

### CHC-0002 — Mock server codegen interpolates untrusted OpenAPI into source

- **Status:** Fixed
- **Fixed in:** a449ad7
- **Fixed at:** 2026-08-17T17:20:00Z
- **Implementation note:** Routes use sanitize_identifier / string_literal / escape_docstring; paths allowlisted. Tests reject quote/newline injection.
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-94
- **Primary file:** `Asgard/Forseti/MockServer/services/_mock_server_generator_helpers.py`
- **Also on trace:** `Asgard/Forseti/MockServer/services/mock_server_generator.py` (FastAPI/Express title/description/version also interpolated)
- **Related original:** CH-0061, CH-0058
- **Location:** `generate_flask_route` ~74-78; `generate_flask_route_stateful`; `generate_express_route`
- **Trace:** OpenAPI `endpoint.path` / `summary` / `operation_id` → f-string into `@app.route("...")` / function name / docstring → generated Flask/Express source
- **Impact:** Hostile spec breaks out of quotes and injects Python/JS into the generated mock.
- **Evidence:** `flask_path` is only `{`/`}` rewritten; no escape of quote, newline, or triple-quote.
- **Planned fix:** Escape/allowlist path and identifiers (same class as CH-0058). Tests with a quote/newline in path and summary.
- **Fix wave:** W2

### CHC-0003 — MCP wildcard-bind deny-list is incomplete

- **Status:** Fixed
- **Implementation note:** `normalize_bind_host` + `is_wildcard_bind_host` treat `0` / `::0` / `*` as wildcard; MCP/Dashboard bind the normalized host. Tests for aliases.
- **Severity:** Medium
- **Confidence:** Medium
- **CWE / class:** CWE-306 / CWE-668
- **Primary file:** `Asgard/MCP/server/asgard_mcp_server.py`
- **Also on trace:** `Asgard/Heimdall/cli/handlers/mcp.py`, `Asgard/Dashboard/adapters/web/dashboard_handler.py` (same deny-list)
- **Related original:** CH-0086
- **Location:** `AsgardMCPServer.run` ~163-165, bind at ~233
- **Trace:** `--host 0` / `::0` / `*` (not in `{0.0.0.0, ::, [::]}`) → bind all interfaces without `--expose`. Empty `host=""` is checked as localhost (`or "localhost"`) but MCP binds raw `self._config.host` (INADDR_ANY). Dashboard binds the stripped host (aliases still apply).
- **Impact:** LAN exposure of a token-gated MCP if an operator uses a non-canonical wildcard. Not an unauth bypass.
- **Evidence:** deny-list is a literal set; bind uses `self._config.host` not the stripped/normalized host.
- **Planned fix:** Normalize host (strip, lowercase, treat `0` / `::0` / `*` as wildcard); refuse unless `--expose`. Bind the normalized host. Tests for `--host 0` and `--host ::0`.
- **Fix wave:** W1

### CHC-0004 — Dockerfile `save_to_file` joins unsanitized `filename`

- **Status:** Fixed
- **Fixed in:** bfa0ced
- **Fixed at:** 2026-08-17T17:30:00Z
- **Implementation note:** `confine_output_file` rejects empty/abs/`..` and requires resolve+is_relative_to; wired into Docker/Compose/GitOps/K8s/Kustomize writers.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Volundr/Docker/services/dockerfile_generator.py`
- **Also on trace:** `Asgard/Volundr/Compose/services/compose_generator.py`, `Asgard/Volundr/Docker/services/compose_generator.py`, `Asgard/Volundr/GitOps/services/argocd_generator.py`, `Asgard/Volundr/GitOps/services/flux_generator.py`, `Asgard/Volundr/Kubernetes/services/manifest_generator.py`, `Asgard/Volundr/Kustomize/services/overlay_generator.py`, `Asgard/Volundr/Kustomize/services/patch_generator.py`, `Asgard/Volundr/Kustomize/services/component_generator.py`
- **Related original:** CH-0106
- **Location:** `save_to_file` ~526-538
- **Trace:** caller `filename` → `os.path.join(target_dir, filename)` → `open` with no `resolve`/`is_relative_to`. Same join on compose/gitops/k8s/kustomize writers (name or `filename` as path key).
- **Impact:** Hostile filename writes the generated Dockerfile outside `output_dir`. CLI default is `Dockerfile`. Sibling writers have the same jail miss.
- **Evidence:** no jail; `.dockerignore` write is a fixed name under the same `target_dir`.
- **Planned fix:** allowlist basename; `Path.resolve()` and require `is_relative_to(target_dir)`. Test `../evil`.
- **Fix wave:** W2


### CHC-0005 — Git scanner unbounded per-file `git show`

- **Status:** Fixed
- **Fixed in:** 5aca9c3
- **Fixed at:** 2026-08-17T18:20:00Z
- **Implementation note:** One `git grep -I -n -E` over HEAD replaces per-file `git show`; hit count capped.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-400
- **Primary file:** `Asgard/Heimdall/Security/Git/services/git_scanner.py`
- **Also on trace:** `Asgard/Shared/common/_git_isolated.py`
- **Related original:** CH-0024, CH-0025
- **Location:** `_check_secrets_in_current_files` ~166-185
- **Trace:** `ls-tree -r HEAD --name-only` → one `git show HEAD:{path}` per tree entry (30s timeout) → regex scan
- **Impact:** A huge tree turns a local git scan into thousands of processes / full-history blob materializations. Isolated git helper does not cap count.
- **Evidence:** skip list is only a few binary extensions; no file-count or size cap.
- **Planned fix:** cap files and blob bytes; skip binaries by content; reuse one `git grep`/`git grep -I` instead of per-file `show`. Tests with a planted large tree.
- **Fix wave:** W4


### CHC-0006 — Common baseline fuzzy empty message still wildcards

- **Status:** Fixed
- **Fixed in:** 94f7745
- **Fixed at:** 2026-08-17T17:50:00Z
- **Implementation note:** Fuzzy match reuses is_usable_fuzzy_message; empty stored or query message is not a file+type wildcard.
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-693
- **Primary file:** `Asgard/common/_baseline_models.py`
- **Also on trace:** `Asgard/common/baseline.py`
- **Related original:** CH-0012
- **Location:** fuzzy match ~67-74; `filter_items` defaults `message=""` when `message_func` is None
- **Trace:** empty/missing message → `return True` (file+type wildcard) — the same class CH-0012 closed on `Asgard.Baseline`
- **Impact:** A blank-message baseline entry on this stack suppresses a whole file+type.
- **Evidence:** CH-0012 guards are not imported here.
- **Planned fix:** reuse `is_usable_fuzzy_message` / refuse empty fuzzy keys (same as CH-0012). Tests with empty message.
- **Fix wave:** W3


### CHC-0007 — Python OOP AST parse/walk/LCOM still unbounded

- **Status:** Fixed
- **Fixed in:** 9c74e5e
- **Fixed at:** 2026-08-17T18:35:00Z
- **Implementation note:** Skip symlink/>1MiB/>50k-line files; node budget on ClassExtractor; skip LCOM above MAX_LCOM4_METHODS (128).
- **Severity:** Low
- **Confidence:** High
- **CWE / class:** CWE-400
- **Primary file:** `Asgard/Bragi/OOP/utilities/_class_functions.py`
- **Also on trace:** `Asgard/Bragi/OOP/utilities/_class_visitors.py`, `Asgard/Bragi/OOP/services/cohesion_analyzer.py`, `coupling_analyzer.py`, `rfc_analyzer.py`, `inheritance_analyzer.py`, `oop_analyzer.py`, `_cohesion_helpers.py`
- **Related original:** CH-0016, CH-0022
- **Location:** `extract_classes_from_file` / `ClassExtractor.visit` / LCOM pairwise
- **Trace:** `heimdall oop` → 4× `scan_directory` → `read_text`+`ast.parse`+recursive visit → uncapped LCOM O(n²)
- **Impact:** Hostile/huge `.py` DoS of the Python OOP analyzers (CPU/RAM/RecursionError). Not RCE. File symlink can pull outside-tree content into metrics.
- **Evidence:** CIR path has byte/line/walk/LCOM caps; Python AST path has none. `OOPConfig` has no max file/nodes.
- **Planned fix:** Cap source bytes/lines before `ast.parse`; skip oversize/symlink files; iterative walk + node budget; apply `MAX_LCOM4_METHODS` in `_cohesion_helpers`; one shared tree per file. Tests: >1 MiB skip; >128 methods skip LCOM.
- **Fix wave:** W4


### CHC-0008 — OpenAPI/compat YAML alias cycles unbounded

- **Status:** Fixed
- **Fixed in:** 3460461
- **Fixed at:** 2026-08-17T18:25:00Z
- **Implementation note:** Spec walkers use id() seen-set + depth 64; converters refuse alias cycles. Tests plant self-aliased mapping.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-674 / CWE-400
- **Primary file:** `Asgard/Forseti/Compatibility/utilities/compat_utils.py`
- **Also on trace:** `Asgard/Forseti/OpenAPI/utilities/_openapi_spec_utils.py`, `Asgard/Forseti/OpenAPI/rules/_rule_helpers.py`, `Asgard/Forseti/OpenAPI/services/_spec_converter_2_to_3_helpers.py`, `Asgard/Forseti/OpenAPI/services/_spec_converter_3_to_2_helpers.py`, `Asgard/Forseti/Compatibility/services/_avro_adapter.py`
- **Related original:** CH-0022, CH-0101
- **Location:** `collect_refs` ~106-117; `get_all_refs` / `iter_refs`; `iter_schemas`; converter recurse; Avro named-type registry
- **Trace:** hostile spec (`forseti openapi validate|convert` / `forseti compat check`) → `yaml.safe_load` (aliases become cyclic dicts) → walker follows `.values()` / `properties` without `id()` set → `RecursionError`
- **Impact:** Process crash / CI hang. No RCE (`safe_load`). No SSRF (external `$ref` skipped).
- **Evidence:** `resolve_references` / `_prepare_schema` already depth-cap; these walkers do not.
- **Planned fix:** Shared walk with `id()` seen-set + depth cap (~64); catch `RecursionError` at service edges. Tests: self-aliased mapping `a: &a {b: *a}`.
- **Fix wave:** W4


### CHC-0009 — CST dispatch fail-open looks complete

- **Status:** Fixed
- **Fixed in:** 8156586
- **Fixed at:** 2026-08-17T17:55:00Z
- **Implementation note:** Missing grammar/parse/visitor failure set truncated or parse_failed; CLI records domain_errors, degrades score off 100, and exits 1.
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-390 / CWE-755
- **Primary file:** `Asgard/Heimdall/Security/engine/dispatch.py`
- **Also on trace:** `Asgard/Heimdall/cli/handlers/_security_dispatch.py`, `Asgard/Heimdall/cli/handlers/taint.py`, `Asgard/Heimdall/cli/handlers/scan_steps_1_6.py`
- **Related original:** CH-0077, CH-0098
- **Location:** `_scan_cst_language` ~347-405
- **Trace:** `heimdall security scan` / taint → `run_dispatch_scan` → `DispatchEngine._scan_cst_language`. Missing grammar / `ctx.root is None` → `return [], False`. `scan_fn` `except Exception: flows = []`. CLI does not treat `analysis_truncated` / parse-failed as incomplete.
- **Impact:** JS/TS/Java/Go/C injection can vanish (score 100, “no findings”) when tree-sitter is absent, parse fails, or the visitor throws. Layer 1 regex still runs; data-flow does not. Python still has L2/L3.
- **Evidence:** docstring says empty list is intentional “optional tree-sitter”; `truncated` stays False on those paths so the scan looks complete.
- **Planned fix:** Set `parse_failed`/`analysis_truncated` on miss/exception; CLI/gate must fail or degrade score when any file is incomplete; do not emit 100 for an empty CST pass.
- **Fix wave:** W3


### CHC-0010 — Taint stub YAML path not jailed

- **Status:** Fixed
- **Fixed in:** 47280b3
- **Fixed at:** 2026-08-17T17:25:00Z
- **Implementation note:** Stub names must match [A-Za-z0-9_-]+; resolved path must stay under the stubs directory.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22 / CWE-693
- **Primary file:** `Asgard/Heimdall/Security/TaintAnalysis/stubs/__init__.py`
- **Also on trace:** `Asgard/Heimdall/Security/TaintAnalysis/services/taint_analyzer.py`, `Asgard/Heimdall/Security/TaintAnalysis/models/taint_models.py`
- **Related original:** none
- **Location:** `load_framework_stubs` ~42-47
- **Trace:** `TaintConfig.framework_stubs` (user/API) → `_STUB_DIR / f"{name}.yml"` → `exists()` + `yaml.safe_load`. No basename allowlist, no `resolve().is_relative_to(_STUB_DIR)`. Loaded `sanitizer_names` become exact taint clears.
- **Impact:** Not RCE (`safe_load`). With config control and a planted `*.yml`: arbitrary YAML read + sanitizer injection (mute taint).
- **Evidence:** no `..` / separator reject; `Path / name` follows `../`.
- **Planned fix:** Allow `[A-Za-z0-9_-]+` only; resolve and require relative to `_STUB_DIR`. Tests: `../evil` and `flask/../evil`.
- **Fix wave:** W2


### CHC-0011 — CST taint walk unbounded recursion

- **Status:** Fixed
- **Fixed in:** 5709590
- **Fixed at:** 2026-08-17T18:30:00Z
- **Implementation note:** Depth/node caps on _walk/_eval/_node_chain/_find_functions/alias walk; RecursionError at scan re-raised so dispatch marks truncated.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-674 / CWE-400
- **Primary file:** `Asgard/Heimdall/Security/TaintAnalysis/engine/cst_taint_visitor.py`
- **Also on trace:** `Asgard/Heimdall/Security/TaintAnalysis/engine/cst_alias.py`, `Asgard/Heimdall/Security/TaintAnalysis/engine/cst_summaries.py`
- **Related original:** CHC-0007, CHC-0009
- **Location:** `_walk` / `_eval` / `_find_functions` / `_collect_identifiers` / `_node_chain`; `cst_alias.walk`; `_js_destructure_names`
- **Trace:** deep/hostile CST → recursive walk → `RecursionError`. Alias map is outside the scan try and can crash `scan_file`; other walks are swallowed into CHC-0009 fail-open.
- **Impact:** Scanner DoS, or silent skip of a file (empty taint looks clean).
- **Evidence:** hop bound exists in `summaries.py` (`max_hops=4`); CST visitor walks have no depth cap.
- **Planned fix:** Iterative walk or hard depth cap; catch `RecursionError` at `scan_file` and mark truncated.
- **Fix wave:** W4


### CHC-0012 — Forseti sourcemap `yaml.compose` uses unsafe Loader

- **Status:** Fixed
- **Implementation note:** `yaml.compose(..., Loader=SafeLoader)` plus refuse `python/*` tags. Test plants `!!python/object/apply`.
- **Severity:** High
- **Confidence:** High
- **CWE / class:** CWE-502
- **Primary file:** `Asgard/Forseti/Reporting/utilities/sourcemap_loader.py`
- **Also on trace:** Forseti reporters that call `load_with_sourcemap` / `build_sourcemap`
- **Related original:** none
- **Location:** `build_sourcemap` ~42-43
- **Trace:** untrusted spec text → `yaml.compose(text)` (default `Loader`, not `SafeLoader`) while `load_with_sourcemap` uses `safe_load` only for the data object
- **Impact:** `!!python/object` (or similar) in a spec can execute during sourcemap build even though the document load is safe.
- **Evidence:** `yaml.compose(text)` has no `Loader=yaml.SafeLoader`.
- **Planned fix:** `yaml.compose(text, Loader=yaml.SafeLoader)` (or `SafeComposer`). Test a `!!python/object/apply:os.system` plant does not run.
- **Fix wave:** W1


### CHC-0013 — Helm values `--environment` path not jailed

- **Status:** Fixed
- **Fixed in:** 4cf7629
- **Fixed at:** 2026-08-17T17:35:00Z
- **Implementation note:** Environment must match [A-Za-z0-9._-]+; dest is confine_output_file(values-{env}.yaml). Hostile paths return 1.
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Volundr/cli/handlers_gitops.py`
- **Also on trace:** `Asgard/Volundr/cli/_parser_commands_2.py`
- **Related original:** CH-0106, CHC-0004
- **Location:** `run_helm_values` ~184-187
- **Trace:** CLI `--environment` → `Path(output_dir) / f"values-{environment}.yaml"` → `mkdir` + `write_text` with no allowlist / `resolve` / `is_relative_to`
- **Impact:** `values-../../tmp/x.yaml` writes outside `output_dir`.
- **Evidence:** pathlib splits `/` in the interpolated name; not the same join as CHC-0004 `filename` arg.
- **Planned fix:** allowlist `^[A-Za-z0-9._-]+$`; resolve dest and require `is_relative_to(output_dir)`. Test `../../tmp/x`.
- **Fix wave:** W2


## Confirmation progress

Updated: 2026-08-17T02:45:00+00:00
- remaining: 0 (refresh `init` discovered 3938, no new files)
- completed: 3938
- last CHC ID: CHC-0013
- All 114 live original CH-XXXX have verdicts (1 Skipped withdrawn). Reopened=0.
- Batch 14: remaining Asgard_Test fixtures/tests + MANIFEST.in/scripts. All corpus/tests clean (no live secrets). Golden ci.yml/ci-deploy.yml SHA-pinned (CH-0001/0002/0003 Confirmed on those files).
- Ledger: 3938 lines / 3938 completed (1:1 after dropping extra `.gitignore`). Every completed path has a ledger line. Asgard_Test bench/Heimdall-tests/package-tests/meta clusters rewritten from traces.
- Phase 4: Status CONFIRMATION COMPLETE — 13 NEW FINDINGS.
- Next mission: implement remaining Open CHC + Residual leftovers. Do not start a second first-audit.

## Implementation summary

| Severity | Open | Fixed | Accepted risk |
|----------|------|-------|---------------|
| Critical | 0    | 0     | 0             |
| High     | 0    | 5     | 0             |
| Medium   | 0    | 8     | 0             |
| Low      | 0    | 1     | 0             |
| Info     | 0    | 0     | 0             |

CHC Open remaining: none. Residual leftovers still Open.

## Implementation progress

- Open CHC: 0
- Fixed CHC: 13
- Residual leftovers: 31 Open
- Current wave: residuals
- Next: residual leftover planned fixes
- Fix ledger: `_Docs/Planning/CyberHardening/fix_ledger.jsonl`
