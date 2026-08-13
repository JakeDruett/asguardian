# Asgard Master Plan — remaining work, sequenced

**Last updated:** 2026-08-13 (post Wave 4).
All original uplift plans are DELIVERED and archived under `_Docs/Delivered/Planning/`
(see its `README.md` for the ledger; per-wave evidence in `UPLIFT_STATUS.md` at repo root).
Full suite is green: **9,758 passed / 0 failed / 11 skipped**.

This document is now the single live plan. Phases are ordered by dependency; within a
phase, items are independent and parallelizable. Invariants apply throughout: never mute
a real flow; unresolved over-approximates; severity ⊥ confidence; zero network calls in
the default path; honest labeling; deterministic output.

---

## Phase 0 — Manual / credentials / external (Jake only — see `../Jake-todo.md`)
Blockers for nothing else, but highest urgency:
- **Rotate the Vault token** that sat in `CLAUDE.md` (plus MariaDB/Gitea/AppRole creds — same exposure surface).
- Enable GitHub secret scanning on `primordial-creations/asguardian`.
- CI: install `asguardian[ast]` extra so tree-sitter paths run in CI; optionally wire `--online` OSV/NVD into a scheduled scan (needs egress to api.osv.dev / services.nvd.nist.gov).
- Add the nightly `heimdall-eval` CI job (gate + CLI exit codes already exist).
- Verify upstream SHAs for the curated GitHub-Action pin-map and zizmor/actionlint version pins (network-bound; cannot be done offline by tooling).
- Curate the plan-10 real-world holdout corpus (50 CVE repos / 50 clean repos — data collection; manifest machinery exists).

## Phase 1 — Test-infrastructure hardening (unblocks Phases 2–3)
1. **Neutral-tempdir fixture convention.** pytest `tmp_path` embeds the test name, which trips scanner test-context suppression and silently mutes known-bad fixtures. Provide a shared `neutral_tmp` fixture, migrate security-fixture tests onto it, and add a meta-test that a known-bad fixture under `tmp_path` vs `neutral_tmp` demonstrates the trap.
2. **Freya browser/page fixture harness** (deterministic, no live browser in default path) so Freya-side integration pairs become writable.
3. **Fix**: Volundr `PipelineGenerator` silently drops a stage literally named `"deploy"` (discovered in Wave 4; surfaced, not yet fixed).

## Phase 2 — Coverage burn-down (depends on Phase 1)
1. **L2**: remaining pairs `heimdall_freya`, `forseti_freya`, `freya_verdandi` (need Phase 1.2) + the 4 Phase-3 scenario files.
2. **L3**: burn down the 781-model inventory (`_Docs/Delivered/Planning/TestCoverage/_artifacts/model_inventory.txt`, regenerate via `_scripts/list_pydantic_models.py`) to full L3 contract coverage, then land the Phase-4 meta-test (start with an allowlist, shrink it to zero).
3. **L5**: per-CWE fixture directory library (`L5_known_bad/` tree), non-Heimdall L5 suites (Forseti/Freya/Verdandi/Volundr), regulatory-mapping meta-test.
4. **L0/L1 line-coverage expansion** toward module targets (old 52.72% baseline is stale — re-measure first; suite is now ~9.8k tests).

## Phase 3 — Performance & CI gating (depends on Phase 1; CI parts on Phase 0)
1. Migrate the 24 existing pytest-benchmark suites onto the `l8_budget` fixture / `Asgard_Test/L8_budgets.yaml`.
2. Benchmark corpus + self-scan bench (Asgard scanning itself with time budget).
3. CI baseline/regression enforcement workflow for L8 (needs Phase 0 CI access).
4. Heimdall Plan-02 perf test: synthetic 50k LOC CIR build < 5s on 4 cores.

## Phase 4 — Small code residuals (independent, any time)
- `volundr posture` CLI wiring for the delivered GWPI posture-index library (plan 07 "optional, later phase").
- `verdandi analysis` CLI: `sketch merge`, `co-check` subcommands; `anomaly regression --profile` flag (library APIs exist and are tested).
- Incremental `AST-Migration-Skipped` registry tagging of remaining lexical scanners (convention + registry landed in Wave 4; secrets and requirements/.env done).
- Optional: source Ca/Ce from the plan-03 module graph instead of recomputing imports (pure wiring optimization; current computation is correct — only do with regression tests).

## Phase 5 — Research-gated / conditional (do not start until trigger fires)
- Freya visual-comparison recalibration items — gated on RESEARCH_03/04/09 (`_Docs/Research/`).
- Freya bytearray Image refactor — only if profiling shows > ~2s compare times.
- Heimdall coupling accuracy sample vs LSP ground truth on a real OSS repo (manual verification exercise).
- Optional LLM post-filter track (plan 10) — informational/document-only by design.

---

## Known accepted ceilings (not work items)
Documented limitations, deliberate and honestly labeled in code/manifests: taint engines
intra-procedural for JS/Java cross-file summaries; no import/binding resolution for
library-sanitizer shadowing (downgraded, not cleared); Spring `@RequestParam` seeding
unwired; SZZ cannot filter commits post-dating a bug report (no tracker integration);
SA4 guard-narrowing is Python/JS-only (Java/Go/C get sound branch-join); C pointer flow
intra-procedural only.
