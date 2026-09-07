# Asgard Security Hardening

Status: APPLIED (audit + confirmation + leftover fixes, 2026-08)
Scope: every code file in this tree was traced. 114 live findings (`CH-0001`–`CH-0115`, `CH-0029` withdrawn) and 13 confirmation findings (`CHC-0001`–`CHC-0013`) are closed. Per-finding traces live in `git log` (`Fix CH-XXXX` / `Fix CHC-XXXX`). This document is the durable product of that work.

## Invariants

These apply everywhere. New code must keep them.

1. **Fail closed.** Missing, unsigned, truncated, or empty analysis is not a green score. Empty SLI/SLO/vitals/APM windows are 0 / unknown / `INSUFFICIENT_DATA`, not 100. Unmeasured ratings are `N/A`. Incomplete CST/taint is truncated and fails the CLI/gate.
2. **No default network.** License, vuln, and similar lookups stay off unless explicitly enabled. Allowed remotes are https + allowlisted hosts with timeouts and redirect revalidation.
3. **Bind localhost.** Dashboard, MCP, mock servers, and generated Flask default to `127.0.0.1`. Wildcards (`0.0.0.0`, `::`, `0`, `::0`, `*`) require `--expose`.
4. **Jail writes and reads.** Caller paths must `resolve()` and stay `is_relative_to` the intended root. Refuse absolute / `..` / separators where a basename is expected.
5. **Do not follow scan-tree symlinks.** Walkers use confined iterators. Creates use `O_NOFOLLOW` / refuse symlink dirs and dest files.
6. **HMAC is env-only.** Caches and baselines sign with `hmac_key_from_env`. Sibling `.key` files are never used to verify. Unsigned JSON is a miss (empty / refetch), not trust.
7. **Secrets never leave the file whole.** Reports, baselines, and CLI output mask quoted literals (last-2 / length-only). Fuzzy baseline empty messages are not file+type wildcards.
8. **Escape interpolated output.** HTML, markdown tables, GitHub Actions commands, generated source, Docker/HCL/Groovy, and Helm names go through an allowlist or escape helper.
9. **Cap hostile input.** File bytes/lines, regex line length, walk depth, LCOM method count, YAML alias cycles, and `git` blob materialization have budgets.
10. **Isolate untrusted execution.** Git runs with wiped `GIT_*` and `--no-textconv`. Type checkers / linters run in an isolated workdir so planted project config is not loaded.

## Operator environment

Set these in CI if you persist signed state:

| Variable | Used by |
|----------|---------|
| `ASGARD_BASELINE_HMAC_KEY` | `.asgard-baseline.json` |
| `ASGARD_QG_HMAC_KEY` | Quality-gate fingerprint baseline |
| `ASGARD_INTEGRITY_HMAC_KEY` | File-integrity baseline |
| `HEIMDALL_CALIBRATION_HMAC_KEY` | Calibration map |
| `HEIMDALL_CALIBRATION_DIR` | Calibration write root (else CWD) |
| `ASGARD_NO_CACHE` | Force cache miss (license / vuln) |

`--expose` is required to bind a non-loopback host. `--insecure` / `verify=False` is an unauthenticated TLS peek and is labeled as such.

`CLAUDE.md` is tracked following workspace standardization (`ec7652a`). CH-0023's original ignore requirement is superseded: the file documents credential locations and retrieval commands, not literal credentials. `Asgard_Test/tests_Volundr/test_claude_md_ignored.py` enforces that no literal credentials are committed. Internal topology disclosure remains a workspace policy decision. Rotate any historical exposed credentials — see `_Docs/Planning/Jake-todo.md`.

## CI and supply chain

Live workflows (`.github/workflows/ci.yml`, `publish.yml`, `l8-perf-budgets.yml`) SHA-pin every `uses:`, set `permissions`, `timeout-minutes`, and `persist-credentials: false`.

- **PR jobs** run on `ubuntu-latest` and do **not** `pip install -e`. Push-to-main may editable-install.
- **Publish** is split: build (no OIDC) / attest / publish. Environment `pypi`. Tags `v[0-9].*`.
- **L8** workflow stays `if: false` until Jake enables it. It already has `contents: read` and the PR install split.
- **Pre-commit** hook `rev`s are SHAs; extras use `==`; `detect-secrets` is installed. `asguardian init` Python templates include the same hook.
- **Generated** CI (Volundr scaffold / Docker scan-workflow) emit pinned SHAs, not `@vN`.
- Dependabot and Renovate update action pins.

Repo-side secret scanning on GitHub is still a Jake item (`Jake-todo.md`).

## Package controls

### Shared / CLI / Dashboard / MCP / Reporting

- `init-backend`: single-segment `folder_name`; refuse symlink project/subdirs; writes `O_NOFOLLOW`.
- Generated `.gitignore` does not ignore `lib/`, `lib64/`, `env/`, or `ENV/`.
- Dashboard HTML escapes 404/path/issue fields. Default bind localhost.
- MCP requires Bearer, 1 MiB body, path jail, same wildcard-bind rule as Dashboard.
- Common GHA formatter percent-encodes `%` CR/LF `:` `;`. HTML formatters use `html.escape`.
- `init-linter` `project_name` allowlist `^[A-Za-z_][A-Za-z0-9_-]*$`.
- Issue get/mutate is scoped by `issue_id` **and** `project_path`.
- PR decorator: https API base, quote owner/repo, same-origin redirects, token not sent off-origin.

### Heimdall / Bragi (scan, quality, security, ratings, gate)

- Baseline path confined; dest symlink refused; messages stored as SHA-256; IDs 64-hex; empty fuzzy keys refused (`is_usable_fuzzy_message` on both Baseline and `Asgard.common`).
- Architecture YAML: file + 256 KiB cap; layers are mappings; `level` / `max_module_fan_out` ints or None; import lists strings only; `fnmatch` patterns capped.
- Markdown reporters use `md_cell`.
- CIR / OOP / LCOM / tree-sitter / PHP regex / SZZ blame: size, walk, node, and hunk caps. RecursionError is contained or marked truncated.
- Isolated git: `--no-ext-diff`, `--no-textconv`, blank `diff.external` / pager / alias, wipe `GIT_EXTERNAL_DIFF` / `GIT_EXEC_PATH` / `GIT_WORK_TREE` / `GIT_CONFIG_*`.
- Language profile path: `LANGUAGE_ID_RE` + `is_relative_to(profiles_dir)`. Local YAML clamped; write confined under CWD.
- License / vuln / dep-graph / debt / incremental / triage / FileHashCache: HMAC + schema; unsigned is a miss. License network default off (`https://pypi.org` only, 10s). `is_allowed` defaults False.
- Walkers: `iter_confined_files` — no `rglob` out of the scan root, skip file/dir symlinks, inode cycle break.
- Credential snippets masked in JS/PHP/Ruby/Rust/Java/Go/C#/C++/shell.
- `js.no-eval` remediates to `JSON.parse`, never `Function`.
- Smell / file-length / scan HTML escape paths and messages.
- Mypy/pyright run in an isolated temp workdir; planted project plugins are not loaded.
- Parallel scanner: spawn + named import; timeout kills workers.
- Unmeasured ratings → `N/A`; overall `N/A` if any required dimension is missing. D/E/`NOT_MEASURED`/domain errors exit 1.
- Quality-gate unsigned fingerprint baseline → empty → `NOT_EVALUATED`.
- Secrets: last-2 / length-only mask; `*` versions are not treated as live-checked clean.
- `--denied` maps to `prohibited_licenses`. Scan step `ERROR` sets `overall_exit=1`.
- Evaluation corpus paths jailed. Calibration map: jail + refuse unsigned.
- CST dispatch: missing grammar / parse / visitor failure sets truncated; CLI degrades score off 100 and exits 1.
- Taint stubs: name `^[A-Za-z0-9_-]+$`, resolve under stub dir. CST taint walks depth/node capped.
- `parse_file` / `FileParseContext`: stat size before read.
- Git secret scan: one `git grep -I`, not per-file `git show`.
- DNS: validate name, then `dig -- domain`.

### Forseti

- Codegen / mock routes: `sanitize_identifier` / string literals / path allowlist. Hostile quote/newline in OpenAPI is refused.
- `$ref` jailed to the schema directory; remotes and file-absolute refs refused.
- GraphQL introspection: http(s) only, IP block, redirect revalidate; no `file:`/`ftp`.
- Mock server: bind `127.0.0.1`; generated Flask `debug=False`.
- LiveContract / validation proxy: localhost default, http(s) upstream, path jail, same-host redirects.
- Docs HTML: escape title/contact/`status_code`.
- SQL defaults: literals only (`sanitize_sql_default`).
- YAML: `SafeLoader` / refuse `python/*` tags; walkers use `id()` seen-set + depth 64.

### Freya

- Navigation: `validate_navigation_url` + `safe_goto`. Login/SPA click/reload re-check `page.url` with `resolve_host=True`. Testers, SRI/mixed, header scanner, and `PlaywrightUtils.navigate` use the same path. `file:` / ftp / javascript / data aborted.
- Link-validator seed URL is validated before Playwright launch.
- HTML/JUnit/visual-regression reports: `esc` / `html_link` / `safe_src` / `safe_css`.
- Baseline storage: `confine_storage_path` on load/delete/version.
- Crawl `password`/`token`/`cookie` redacted on generate+save.
- `page.evaluate` takes a static function + id arg. `hide_selectors` via `json.dumps`.
- Screenshot / visual output names jailed.
- Empty scores → `NA`; unknown severity → `BLOCKER`.

### Verdandi

- SLA empty window: 0 / BREACHED, not 100.
- Error budget / SLI: zero events → 0 / `UNKNOWN`, not 1.0.
- Invalid anomaly baseline → `unknown` / significant, not in-bounds.
- Causal walks: visited set + cap (no cyclic parent loops).
- Empty vitals: `INSUFFICIENT_DATA` and score 0.
- Empty APM traces: `health_score` 0.
- Sketch `from_dict`: centroid/bucket caps + finite checks.

### Volundr

- Generated Actions: SHA pins from `KNOWN_ACTION_PINS`.
- Dockerfile: `_require_safe_field` on names, run/env, **and** `SecretMount` id/target. `save_to_file` jailed.
- Jenkins: `run`/env values quoted; env **keys** `[A-Za-z_][A-Za-z0-9_]*`.
- Helm chart name `^[a-z0-9-]+$`. `--environment` allowlisted; `values-{env}.yaml` jailed.
- Vault URL https. Service map rejects privileged / floating tags.
- Pipeline name + output jail. Suppressions: CI HMAC, refuse `*` targets, expiry required.
- Terraform: no `0.0.0.0/0` egress; `hcl_quoted` / `require_hcl_identifier`; type/value/validation refuse CR/LF/`#`.

### FutureItems security toolkit

- Workflow: no `cd security-tools`, no `continue-on-error`. Require non-empty SARIF **and** JSON. Missing/`total_issues` parse failure / crash sentinel fails the job.
- SSL: default `CERT_REQUIRED`. `--protocols` verifies unless `--insecure`.
- CORS / headers / port scan: URL/host allowlist; no private/metadata unless `--allow-internal`.
- DNS: `validate_dns_name` then `dig --`.
- API loader: strict class load; crash `total_issues=-1` fail-closed. `-o` jailed (`.json`/`.sarif`).

## Finding index (closed)

Original live IDs `CH-0001`–`CH-0115` except withdrawn `CH-0029`. Confirmation IDs `CHC-0001`–`CHC-0013`. Confirmation re-traced the tree (3938 files); leftovers of Residual verdicts were implemented after. Reconstruct a single change with `git log --grep=CH-00XX`.

## Related

- `_Docs/Planning/Jake-todo.md` — Vault rotation, GitHub secret scanning, enable L8 CI
- `_Docs/Planning/MasterPlan/00_MasterPlan.md` — remaining product work
- `_Docs/Testing/Testing_Standards.md` — how to test these controls
- `_Docs/Testing/L8_Perf_Budget_Policy.md` — L8 workflow still draft
