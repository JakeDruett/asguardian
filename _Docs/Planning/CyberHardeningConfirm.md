# CyberHardening Confirmation Plan

Status: IN PROGRESS
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
| CH-0016 | Low | W4 | (pending) | | `Asgard/Bragi/Architecture/cir/builder.py` |
| CH-0017 | Medium | W4 | (pending) | | `Asgard/Bragi/Architecture/graph/service.py` |
| CH-0018 | Low | W4 | (pending) | | `Asgard/Bragi/Architecture/graph/propagation.py` |
| CH-0019 | Low | W5 | (pending) | | `Asgard/Bragi/Architecture/services/_arch_reporter_markdown.py` |
| CH-0020 | Info | W5 | (pending) | | `Asgard/Bragi/Architecture/services/_architecture_config.py` |
| CH-0021 | Low | W4 | (pending) | | `Asgard/Bragi/Architecture/services/_generic_solid_checks.py` |
| CH-0022 | Medium | W4 | (pending) | | `Asgard/Bragi/Architecture/services/_treesitter_solid_checks.py` |
| CH-0023 | Info | W1 | Confirmed |  | CLAUDE.md gitignored with credential comment |
| CH-0024 | High | W1 | Residual | textconv/filter drivers | named git-config vectors isolated; local textconv still runs |
| CH-0025 | Low | W4 | Confirmed |  | hunk/blame caps return INSUFFICIENT_DATA |
| CH-0026 | Medium | W2 | Confirmed |  | LANGUAGE_ID_RE + is_relative_to profiles_dir |
| CH-0027 | Medium | W3 | Confirmed |  | schema+clamp on local YAML; unsigned leftover optional |
| CH-0028 | Low | W2 | Confirmed |  | write_local_profile confined under cwd |
| CH-0029 | — | — | Skipped | | withdrawn |
| CH-0030 | Info | W5 | Confirmed |  | language allowlist; finite thresholds; positive weights |
| CH-0031 | Low | W4 | Confirmed |  | ValidationError logged; ctor returns None |
| CH-0032 | Medium | W3 | (pending) | | `Asgard/Bragi/Dependencies/services/_license_cache.py` |
| CH-0033 | Medium | W1 | Confirmed |  | enable_network default False; https://pypi.org only; 10s timeout |
| CH-0034 | Low | W2 | (pending) | | `Asgard/Bragi/Dependencies/services/license_checker.py` |
| CH-0035 | High | W2 | Confirmed |  | confine_sync_target jail; abs/.. rejected |
| CH-0036 | Medium | W3 | (pending) | | `Asgard/Bragi/Dependencies/services/_vuln_cache.py` |
| CH-0037 | Low | W2 | (pending) | | `Asgard/Bragi/Dependencies/services/_vuln_cache.py` |
| CH-0038 | Medium | W3 | (pending) | | `Asgard/Bragi/Dependencies/models/license_models.py` |
| CH-0039 | Low | W4 | (pending) | | `Asgard/Bragi/Dependencies/services/graph_service.py` |
| CH-0040 | Medium | W2 | Confirmed |  | skip symlinks; inode cycle; jail resolve |
| CH-0041 | Low | W2 | Confirmed |  | os.walk followlinks=False; no rglob |
| CH-0042 | Medium | W2 | Confirmed |  | iter_language_files + size/finding caps |
| CH-0043 | Medium | W3 | (pending) | | `Asgard/Bragi/Quality/languages/javascript/services/_js_security_rules.py` |
| CH-0044 | Info | W5 | (pending) | | `Asgard/Bragi/Quality/languages/javascript/services/_js_rules.py` |
| CH-0045 | Low | W4 | (pending) | | `Asgard/Bragi/Quality/languages/php/services/_php_rules.py` |
| CH-0046 | Medium | W5 | (pending) | | `Asgard/Bragi/Quality/services/_code_smell_report_html.py` |
| CH-0047 | Medium | W3 | (pending) | | `Asgard/Bragi/Quality/services/_debt_state_store.py` |
| CH-0048 | Medium | W3 | (pending) | | `Asgard/Bragi/Quality/services/_incremental_cache.py` |
| CH-0049 | High | W1 | Confirmed |  | mypy/pyright runners isolated; planted plugins not loaded |
| CH-0050 | High | W2 | Confirmed |  | pyrightconfig written only in isolated temp workdir |
| CH-0051 | High | W3 | Residual | sibling .key + HMAC plant | unsigned JSON fail-closed; env-less sibling key still forges |
| CH-0052 | Medium | W3 | (pending) | | `Asgard/Bragi/QualityGate/fingerprint.py` |
| CH-0053 | Medium | W4 | (pending) | | `Asgard/Bragi/Quality/services/parallel_scanner.py` |
| CH-0054 | Medium | W3 | (pending) | | `Asgard/Bragi/Ratings/services/ratings_calculator.py` |
| CH-0055 | High | W5 | Confirmed |  | esc() on 404/path/issue fields; badge CSS allowlisted |
| CH-0056 | Medium | W1 | Confirmed |  | default localhost; refuse 0.0.0.0/:: without --expose |
| CH-0057 | Medium | W2 | Confirmed |  | confine_source_path before any read |
| CH-0058 | High | W2 | Confirmed |  | json.dumps paths; sanitize identifiers; confine_output_path |
| CH-0059 | High | W2 | Confirmed |  | $ref jailed to schema dir; remotes/file-abs refused |
| CH-0060 | High | W1 | Confirmed |  | http(s)+IP block+redirect revalidate; no file/ftp handlers |
| CH-0061 | High | W1 | Confirmed |  | default 127.0.0.1; generated Flask debug=False |
| CH-0062 | High | W1 | Confirmed |  | localhost default; http(s) upstream; path jail; same-host redirects |
| CH-0063 | High | W1 | Confirmed |  | urljoin + path jail; encode params; same-host redirects |
| CH-0064 | Medium | W5 | (pending) | | `Asgard/Forseti/Documentation/services/docs_generator.py` |
| CH-0065 | Medium | W2 | Confirmed |  | sanitize_sql_default literals only |
| CH-0066 | High | W1 | Residual | click/reload/login-submit follow first | start/login/enqueue/tester goto gated; click+reload navigate before allowlist |
| CH-0067 | High | W5 | Confirmed |  | esc/html_link/safe_src/safe_css on HTML and JUnit |
| CH-0068 | High | W2 | Confirmed |  | confine_storage_path on load/delete/version; tests for ../ and symlink |
| CH-0069 | High | W3 | Confirmed |  | password/token/cookie redacted to **** on generate+save |
| CH-0070 | Medium | W4 | (pending) | | `Asgard/Freya/Accessibility/services/_aria_validator_checks_part2.py` |
| CH-0071 | Medium | W1 | Residual | seed page.goto ungated | HEAD+redirects allowlisted; seed navigation is not |
| CH-0072 | High | W2 | Confirmed |  | sanitize_output_name + confine_output_path on every write |
| CH-0073 | Medium | W3 | (pending) | | `Asgard/Freya/Scoring/services/grade_calculator.py` |
| CH-0074 | Medium | W4 | (pending) | | `Asgard/Freya/Visual/services/_screenshot_capture_helpers.py` |
| CH-0075 | Medium | W2 | Confirmed |  | validate_dns_domain then dig -- domain |
| CH-0076 | High | W3 | Confirmed |  | HMAC baseline; adds set has_changes; fail-closed |
| CH-0077 | High | W3 | Confirmed |  | domain_errors fail is_passing; CLI exit 1 |
| CH-0078 | Medium | W2 | Residual | sibling scanners still rglob | owned walker confined; taint/log/scan_steps still rglob |
| CH-0079 | Medium | W3 | (pending) | | `Asgard/Heimdall/Security/utilities/security_utils.py` |
| CH-0080 | Medium | W3 | (pending) | | `Asgard/Heimdall/Security/services/_live_vulnerability_lookup.py` |
| CH-0081 | Medium | W3 | (pending) | | `Asgard/Heimdall/Security/triage/services/triage_cache.py` |
| CH-0082 | Low | W1 | Confirmed |  | default enable_assist=False; Claude not constructed |
| CH-0083 | Medium | W4 | (pending) | | `Asgard/Heimdall/Security/services/_config_secrets_helpers.py` |
| CH-0084 | Medium | W4 | (pending) | | `Asgard/Heimdall/Security/services/_injection_patterns.py` |
| CH-0085 | Medium | W4 | (pending) | | `Asgard/Heimdall/Security/services/_secret_patterns.py` |
| CH-0086 | High | W1 | Confirmed |  | Bearer required; refuse 0.0.0.0 without --expose; path jail; 1MiB body |
| CH-0087 | Low | W4 | (pending) | | `Asgard/Heimdall/Security/services/_supply_chain_analysis.py` |
| CH-0088 | Medium | W3 | (pending) | | `Asgard/Heimdall/cli/handlers/ratings.py` |
| CH-0089 | Medium | W3 | (pending) | | `Asgard/Heimdall/cli/handlers/syntax.py` |
| CH-0090 | Medium | W3 | (pending) | | `Asgard/Heimdall/cli/handlers/scan.py` |
| CH-0091 | Medium | W2 | Confirmed |  | confine_eval_path on manifest joins |
| CH-0092 | Medium | W3 | (pending) | | `Asgard/Heimdall/evaluation/calibration.py` |
| CH-0093 | High | W1 | Confirmed |  | https API base; quote owner/repo; same-origin redirects; token not sent off-origin |
| CH-0094 | High | W1 | Confirmed |  | percent-encode % CR/LF :/ :: ; strip C0 |
| CH-0095 | Low | W4 | (pending) | | `Asgard/Heimdall/treesitter/file_context.py` |
| CH-0096 | Medium | W1 | Confirmed |  | project_name allowlist ^[A-Za-z_][A-Za-z0-9_-]*$ |
| CH-0097 | Medium | W1 | Confirmed |  | get/mutate WHERE issue_id AND project_path |
| CH-0098 | Medium | W3 | (pending) | | `Asgard/Verdandi/Analysis/services/sla_checker.py` |
| CH-0099 | Medium | W4 | (pending) | | `Asgard/Verdandi/Analysis/services/quantile_sketch.py` |
| CH-0100 | Medium | W3 | (pending) | | `Asgard/Verdandi/Anomaly/services/baseline_comparator.py` |
| CH-0101 | Low | W4 | (pending) | | `Asgard/Verdandi/APM/services/service_map_builder.py` |
| CH-0102 | High | W1 | Residual | SecretMount id/target | newline/# refused on listed fields; SecretMount interpolated unsanitized |
| CH-0103 | High | W1 | Residual | Jenkins env keys | run/env values hardened; env keys still raw in Groovy environment {} |
| CH-0104 | Medium | W1 | Confirmed |  | chart name ^[a-z0-9-]+$ before define/include |
| CH-0105 | Medium | W1 | Confirmed |  | https vault_url; harden_service_map rejects privileged/floating |
| CH-0106 | Medium | W2 | Confirmed |  | safe_pipeline_name + confine_pipeline_output |
| CH-0107 | Medium | W3 | (pending) | | `Asgard/Volundr/Validation/models/suppression_models.py` |
| CH-0108 | Medium | W1 | Residual | raw HCL type/value | 0.0.0.0/0 gone; hcl_quoted on names; type/value still raw |
| CH-0109 | Medium | W3 | (pending) | | `Asgard/common/_hash_cache.py` |
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
| High     | 0 | 6 | 2 | 22 | 0 | 0 |
| Medium   | 0 | 5 | 4 | 23 | 0 | 0 |
| Low      | 0 | 3 | 0 | 8 | 0 | 0 |
| Info     | 0 | 1 | 0 | 2 | 0 | 0 |

## Reopened / residual detail

### CH-0001 — Residual (generated action tags)

- **Original sink (closed):** live `.github/workflows/*.yml` `uses:` were `@v4`/`@v5` / `pypa@release/v1`. Current `ci.yml` / `publish.yml` / `l8-perf-budgets.yml` use 40-char SHAs matching `KNOWN_ACTION_PINS`. Dependabot + Renovate pin updaters exist.
- **Leftover:** generators still emit mutable tags.
  - `Asgard/Volundr/Scaffold/services/_monorepo_infra_templates.py` ~186/198/212: `uses: actions/checkout@v4`
  - `Asgard/Volundr/Docker/services/dockerfile_generator.py` `_scan_workflow` ~153: `uses: actions/checkout@v4`
- **Evidence:** live workflows have no `@v[0-9]` tags; generated artifacts do.
- **Planned leftover fix:** emit `KNOWN_ACTION_PINS` SHAs (or refuse to emit unpinned `uses:`) in scaffold + scan-workflow templates. Tests that generated YAML has no `@vN` action tags.

### CH-0024 — Residual (textconv / extra GIT_*)

- **Original sink (closed):** `szz._run_git` → `run_isolated_git` (`Asgard/Shared/common/_git_isolated.py`). `--no-ext-diff` on diff/log/show/blame; `-c diff.external=` / `core.fsmonitor=` / `core.pager=` / `alias.{cmd}=`; env pops `GIT_EXTERNAL_DIFF`/`GIT_PAGER`/`GIT_DIR`; `GIT_CONFIG_NOSYSTEM=1` + `GIT_CONFIG_GLOBAL=os.devnull`. Tests plant `diff.external` and `GIT_EXTERNAL_DIFF`.
- **Leftover:** local `.git/config` `diff.*.textconv` / filter drivers still execute on `git diff` / `git blame`. `GIT_EXEC_PATH`, `GIT_WORK_TREE`, `GIT_CONFIG_PARAMETERS` / `GIT_CONFIG_COUNT` not wiped.
- **Trace:** `compute_szz` → `_fix_commit_hunks` (`git diff`) / `_blame_inducing_commits` (`git blame`) → isolated helper → still honors repo textconv.
- **Planned leftover fix:** `--no-textconv`; blank `diff.*.textconv` / filter drivers; drop additional `GIT_*` override vars. Test a planted textconv is not executed.

### CH-0102 — Residual (SecretMount)

- **Original sink (closed):** `_require_safe_field` rejects CR/LF/`#` on name/syntax/args/labels/stage image/workdir/user/copy/run/env/entrypoint/cmd. HEALTHCHECK uses `json.dumps`. Trivy digest-pinned. `docker.sock` only if `privileged_scan`.
- **Leftover:** `_mount_flags` interpolates `mount.id` / `mount.target` into `RUN --mount=...` without `_require_safe_field`. Newline/`#` becomes another Dockerfile instruction. CLI `--secret-mounts` feeds this.
- **Location:** `dockerfile_generator.py` `_mount_flags` ~238-249; `_assert_safe_config` ~177-217 does not walk `secret_mounts`.
- **Planned leftover fix:** run `_require_safe_field` on `SecretMount.id`/`target`; test newline in mount id.

### CH-0103 — Residual (Jenkins env keys)

- **Original sink (closed):** `generate_jenkins` calls `harden_steps`; `_jenkins_safe_script` refuses triple-quote/CR; values go through `_jenkins_groovy_string` (quoted `sh(...)`, not raw triple-quoted). Tests refuse triple-quote breakout in `run`.
- **Leftover:** `config.env` keys interpolated raw into the Groovy `environment` block (~596-597). A key with newline or quote breaks out.
- **Planned leftover fix:** allowlist env keys `[A-Za-z_][A-Za-z0-9_]*` (or refuse quote/newline). Test a hostile key.


### CH-0006 — Residual (generated hook template)

- **Original sink (closed):** repo `.pre-commit-config.yaml` uses 40-char `rev` SHAs, `additional_dependencies` pinned with `==`, and a `detect-secrets` hook.
- **Leftover:** `Asgard/Shared/Init/_templates_python.py` `PRE_COMMIT_CONFIG` still has SHA revs + `==` extras but **omits detect-secrets**. `asguardian init` projects do not get the secret-scan hook the repo itself now uses.
- **Planned leftover fix:** copy the repo hook list (including detect-secrets) into the Python init template. Test generated config contains `id: detect-secrets`.

### CH-0066 — Residual (click / reload / login-submit follow first)

- **Original sink (closed):** crawl `start_url` / `login_url` / discovery enqueue / tester `goto` use `validate_navigation_url` + `safe_goto`. SPA enqueue uses `should_crawl`. `file:` and literal RFC1918 are rejected before those `goto`s.
- **Leftover:** Playwright still navigates **before** the allowlist on:
  - `site_crawler.py` login `submit` + `wait_for_url` (~183-196)
  - `_crawler_spa.py` `item.click()` + `expect_navigation` (~151-157)
  - `_crawler_spa.py` `page.reload()` (~98)
  Post-checks use `resolve_host=False`, so a public name that later resolves internally is not DNS-checked.
- **Impact:** Hostile login/SPA can already hit `file:` / metadata / RFC1918; the later validate only drops the URL from the crawl set.
- **Planned leftover fix:** do not follow unknown navigations; intercept/route-abort non-allowlisted schemes/hosts; re-validate `page.url` with `resolve_host=True` after click/reload/submit.


### CH-0051 — Residual (sibling HMAC key)

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

- **Original sink (closed):** `iter_confined_files` skips symlinks and jails resolve. Secrets/injection/crypto/config/deps/dispatch use it.
- **Leftover:** `taint_analyzer.py`, `log_analyzer.py`, `scan_steps_7_11.py` still `rglob`; several domain scanners `os.walk` then open file symlinks.
- **Planned leftover fix:** route remaining Heimdall walkers through `iter_confined_files`.

### CH-0111 — Residual (`--protocols` CERT_NONE)

- **Original sink (closed):** default `check_certificate` uses `CERT_REQUIRED`.
- **Leftover:** `check_protocol_support` still `CERT_NONE` and connects to the operator host.
- **Planned leftover fix:** use default context or label the probe unauthenticated.


## New findings

### CHC-0001 — Draft L8 still editable-installs the PR tree

- **Status:** Open
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

- **Status:** Open
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

- **Status:** Open
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

- **Status:** Open
- **Severity:** Medium
- **Confidence:** High
- **CWE / class:** CWE-22
- **Primary file:** `Asgard/Volundr/Docker/services/dockerfile_generator.py`
- **Also on trace:** none
- **Related original:** CH-0106
- **Location:** `save_to_file` ~526-538
- **Trace:** caller `filename` → `os.path.join(target_dir, filename)` → `open` with no `resolve`/`is_relative_to`
- **Impact:** Hostile filename writes the generated Dockerfile outside `output_dir`. CLI default is `Dockerfile`.
- **Evidence:** no jail; `.dockerignore` write is a fixed name under the same `target_dir`.
- **Planned fix:** allowlist basename; `Path.resolve()` and require `is_relative_to(target_dir)`. Test `../evil`.
- **Fix wave:** W2


### CHC-0005 — Git scanner unbounded per-file `git show`

- **Status:** Open
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

- **Status:** Open
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


## Confirmation progress

Updated: 2026-08-17T01:05:55+00:00
- remaining: 3852
- completed: 86
- last CHC ID: CHC-0006
- this batch: W2 Medium primaries + FutureItems SSL/API
- next: remaining W3 Medium caches/fail-open + leftover Low/Info primaries, then rest of inventory
- Commands: `python3 scripts/cyberhardening_inventory.py --workspace CyberHardeningConfirm status`
