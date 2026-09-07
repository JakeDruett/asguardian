# Asgard — Handover

**As of:** 2026-08-14 | **Branch:** `main` | **Full suite:** 10,621 passed / 0 failed / 11 skipped

This is the single entry point for picking this project back up — what Asgard is, what's
done, what's left, and exactly where to look for more detail.

---

## What Asgard is

A deterministic static-analysis suite (Python package `asguardian`) with six modules under
`Asgard/`:

| Module | Domain |
|---|---|
| **Heimdall** | Code quality, security/taint analysis, SOLID/architecture enforcement |
| **Forseti** | API contract testing (OpenAPI/JSON-Schema/GraphQL/gRPC), compatibility, mocking |
| **Freya** | Frontend: accessibility (WCAG), visual regression, performance, security framing |
| **Verdandi** | Observability: SLOs, error budgets, cache/network/system/database analysis |
| **Volundr** | Infra: Terraform/Docker/Kubernetes/CICD/GitOps validation and scoring |
| **Bragi** | Cross-cutting: composite scoring, technical debt, git-history calibration |

Tests live in `Asgard_Test/` at levels L0 (mocked unit) → L8 (perf budgets); see
`_Docs/Testing/Testing_Standards.md`. Core invariants (apply everywhere, always): never
mute a real finding; unresolved/ambiguous over-approximates, never confidently clean;
severity is independent of confidence; **zero network calls in the default path**
(network features are strictly opt-in); honest labeling; deterministic output.

---

## Status: uplift complete

The original uplift effort (`_Docs/Planning/` plans, tracked in `UPLIFT_STATUS.md`) is
**fully delivered** across 5 waves, most recently:
- **Wave 4** (2026-08-13): audited every remaining plan file against the code, closed the
  genuine gaps (Heimdall reflexion-model summary, calibration-map loading, Verdandi SLA
  CLI, Volundr score/CICD extensions, 3 real Freya product bugs found + fixed).
- **Wave 5** (2026-08-13/14): executed everything unblocked in the resulting MasterPlan —
  test-infra hardening, L2/L3/L5 coverage burn-down, L8 perf-budget gating (which exposed
  and fixed a real bottleneck: tree-sitter query compilation, 124s → 0.8s), CLI parity,
  and the AST-engine registry rollout.

All plan files are archived at `_Docs/Delivered/Planning/` (historical record — do not
re-implement from these). **The one live planning document going forward is
`_Docs/Planning/MasterPlan/00_MasterPlan.md`** — phased, dependency-ordered, with a
completion ledger at the bottom of what Wave 5 closed and what's still open.

**CyberHardening is applied.** Audit + fixes + confirmation + leftovers
are closed. Durable controls: `_Docs/Architecture/Security_Hardening.md`.
Per-finding commits: `git log --grep=CH-`.

---

## What's left — and who owns it

### You (Phase 0 — nothing else is blocked on this, but it's the most important)
Full detail in `_Docs/Planning/Jake-todo.md`. Short version:
1. **Rotate the Vault token** that was hardcoded in `CLAUDE.md` (never reached GitHub —
   push-protection caught it — but treat it as burned). Also rotate the MariaDB/Gitea/
   AppRole credentials that shared the same exposure surface.
2. Enable GitHub secret scanning on `primordial-creations/asguardian`.
3. CI: install the `asguardian[ast]` extra so tree-sitter paths run in CI; decide whether
   to enable the **drafted-but-disabled** L8 perf-budget CI workflow (ships with `if: false`
   pending your decision); add the nightly `heimdall-eval` job.
4. Verify upstream SHAs for the curated GitHub Action pin-map and zizmor/actionlint pins
   (network-bound — cannot be done by the tooling offline).
5. Curate the real-world CVE holdout corpus for Heimdall's evaluation harness (50 CVE
   repos / 50 clean repos — data collection, not code).

*(We're already working through this list together — pick up at whichever step you were on.)*

### Tooling / next session (Phases 1-5 in the MasterPlan)
- **Phase 2 ratchet**: 224 pydantic models still lack L3 contract tests (tracked in
  `Asgard_Test/L3_Meta/l3_uncovered_allowlist.txt` — shrink-only, the meta-test enforces
  it never grows).
- **Coverage**: Heimdall re-measure (timed out >25min with `--cov` last attempt — needs a
  bounded strategy), Bragi uplift (currently 66.5%), a pre-existing Forseti
  benchmark-plugin collection-error set (28, undiagnosed).
- **Phase 5** (research-gated): Freya visual-recalibration items waiting on
  `_Docs/Research/RESEARCH_03/04/09`; a couple of manual-verification/optional items.
- Small noted exposures: Bragi `_debt_workers` substring test-path heuristic; a dead
  `is_in_test_context` stub in `_crypto_validation_helpers.py`; Freya's
  `WCAGValidator.validate()` hard-instantiates Playwright (no seam for a deterministic
  end-to-end test — the harness at `Asgard_Test/_fixtures/freya_harness.py` drives the
  underlying check functions directly instead).

---

## Where to look for more

| Need | File |
|---|---|
| Live, sequenced plan | `_Docs/Planning/MasterPlan/00_MasterPlan.md` |
| Your manual to-do list | `_Docs/Planning/Jake-todo.md` |
| Full wave-by-wave delivery history/evidence | `UPLIFT_STATUS.md` (repo root) |
| Archived (delivered) original plans | `_Docs/Delivered/Planning/` |
| Per-module architecture docs | `_Docs/Asgard/<Module>/` |
| Test conventions, level definitions (L0-L8) | `_Docs/Testing/Testing_Standards.md` |
| Coverage baseline (2026-08-13) | `_Docs/Planning/MasterPlan/coverage_baseline_2026-08-13.md` |
| L3 model-coverage ratchet | `Asgard_Test/L3_Meta/` |
| L5 known-bad fixture library | `Asgard_Test/L5_known_bad/` |
| L8 perf budgets | `Asgard_Test/L8_budgets.yaml`, `Asgard_Test/L8_PerfBudgets/` |

## Running the suite
```bash
python3 -m pytest Asgard_Test -q                 # full suite (~15 min)
python3 -m pytest Asgard_Test/tests_<Module> -q  # one module
```
No network access is required or attempted by default.
