# Hercules Adoption Plan

Fills in `Hercules/_Docs/Onboarding/13-Repo-Adoption-Plan-Template.md` for asguardian, to the
standard set by `14-Minos-Adoption-Plan-Worked-Example.md`. Placed alongside the existing
`_Docs/Testing/Testing_Standards.md` and `L8_Perf_Budget_Policy.md`.

Grounded in files actually read: `asguardian/README.md` (implied from CLAUDE.md's description),
`asguardian/CLAUDE.md`, `asguardian/pyproject.toml`, `asguardian/.github/workflows/{ci.yml,
l8-perf-budgets.yml}`, and the full `asguardian/Asgard_Test/` directory tree, including opening
`L2_CrossPackage/README.md`/`QUICK_START.md`/`TEST_SUMMARY.md`, `L3_Meta/`,
`L5_Meta/`, and `L8_PerfBudgets/` directly, plus one representative per-package tree
(`tests_Heimdall/`).

---

## 1. Repo identity and scope

- **Repo:** asguardian — a suite of Python development-QA tools (Heimdall: static analysis;
  Forseti: SAST/DAST/dependency/taint security scanning; Freya: web/UI testing; Verdandi:
  performance metrics; Volundr: infrastructure generation), published as the `asguardian` package
  (`asgard` CLI), plus a web dashboard and an MCP server. Single git working tree, single `origin`
  (`primordial-creations/asguardian`). Python 3.11+ required.
- **Canonical `source.repo` (template §0.1): `gitea.internal/asguardian/asguardian`.** No existing Branch 1 of §0.1's decision tree applies: this repo is one working tree with one `origin` and splitting supplies no independent benefit for its toolchain, so the single-repo shape is used, not because a per-product rule mandates it.
  `hercules.yaml` found anywhere in the repo — fresh adoption, no drift to fix.
- **System vs module structure.** One Python package (`Asgard/`) with several named sub-tools
  (Heimdall, Forseti, Freya, Verdandi, Volundr, Bragi, Dashboard, MCP, Reporting, Shared) — each
  already has its own `Asgard_Test/tests_<Tool>/` tree. Module identities per sub-tool:
  `{module: heimdall}`, `{module: forseti}`, `{module: freya}`, `{module: verdandi}`,
  `{module: volundr}`, `{module: bragi}`, `{module: dashboard}`, `{module: mcp}`,
  `{module: reporting}`, `{module: shared}` — plus a system-scoped concern for whatever
  `L2_CrossPackage/` actually is (see §5).

## 2. The fake-taxonomy folders — what they actually are

The task brief names `L2_CrossPackage`, `L3_Meta`, `L5_Meta`, `L8_PerfBudgets` as folder names
that imitate the Hercules taxonomy while using no Hercules machinery. Verified directly by
opening each:

| Folder | What it actually contains | Real pytest? | Hercules machinery used? | Honest classification |
|---|---|---|---|---|
| `L2_CrossPackage/` | Real, substantial pytest suite (`test_asguardian_passthrough.py`, `test_baseline_drift_scenario.py`, `test_deployment_gate_scenario.py`, `test_forseti_freya_integration.py`, its own `README.md`/`QUICK_START.md`/`TEST_SUMMARY.md`, `conftest.py`) exercising real cross-package integration — Forseti findings feeding Freya, baseline drift detection, deployment-gate logic across tools. | Yes | No — no `hercules.yaml`, no `L2TestCase` base class, no Hercules runner invocation anywhere; it runs via plain `pytest`. | **Real content, correctly-numbered by coincidence, wrong home.** This genuinely is L2-shaped (real internal collaborators — two asguardian sub-tools calling each other — no external network). It is not "fake" in the sense of being empty or misleading about what it tests; it is fake only in the specific sense the task means: it borrows Hercules' `L2` name and directory-naming convention without being a registered Hercules suite. |
| `L3_Meta/` | `test_model_coverage_meta.py` plus `l3_uncovered_allowlist.txt` — a coverage-introspection tool that checks which Pydantic/dataclass models across the whole codebase have no test touching them, against a maintained allowlist of accepted gaps. | Yes | No | **Real content, wrongly numbered — not actually L3 (Contract) at all.** This is a meta-test-about-tests (coverage auditing), which has no canonical Hercules level; it is closer in spirit to `analyze-test-coverage`-shaped tooling than to L3's "OpenAPI schema validation, Pact contracts" (`02-Level-Taxonomy.md`). The `L3` in its name is actively misleading, not just unregistered. |
| `L5_Meta/` | `test_regulatory_mapping.py` plus `l5_fixtures.py`/`l5_reference_manifest.yaml` — maps asguardian's own findings taxonomy against named regulatory frameworks (a reference manifest of standards), i.e. this is compliance-shaped self-verification, not cross-service testing. | Yes | No | **Real content, wrongly numbered — the content is Compliance-shaped (canonical L6), not Cross-Service (canonical L5).** This is the same specific error pattern as Kairos' manifest (L5 used to mean compliance) but manifesting as a folder name with no manifest to correct — there is nothing to relabel because there is no manifest, only a directory name to eventually rename if this suite is ever registered. |
| `L8_PerfBudgets/` | `enforcement.py`, `test_budget_smoke.py`, `test_cir_50kloc.py`, `test_corpus_and_self_scan.py`, `test_enforcement_unit.py` — a real, CI-wired (`.github/workflows/l8-perf-budgets.yml`) performance-budget enforcement system, backed by `_Docs/Testing/L8_Perf_Budget_Policy.md`. | Yes | No — runs via the dedicated GitHub Actions workflow and plain pytest, not Hercules. | **Real content, correctly-numbered by coincidence, wrong home.** This is genuinely L8-shaped (module performance thresholds) and already has more supporting policy documentation (`L8_Perf_Budget_Policy.md`) than most repos in this workspace have for any level. Like `L2_CrossPackage`, its problem is exclusively "not a registered Hercules suite," not "misleading content." |

**Summary of the honest distinction the task asks for:** `L2_CrossPackage` and `L8_PerfBudgets`
are real content that happens to already carry the *correct* canonical level number — they are
folders imitating registration, not imitating meaning. `L3_Meta` and `L5_Meta` are real content
carrying the *wrong* canonical level number for what they actually test (coverage-audit tooling
has no real L3 fit at all; regulatory-mapping content is L6-shaped, not L5-shaped) — closer in
kind to Kairos' manifest-level drift, except asguardian has no manifest for these two to correct,
only a folder name.

## 3. The per-package trees also drift, beyond what the task named — reported, not silently found and ignored

Opening one representative per-package tree, `tests_Heimdall/`, in full (all six other
`tests_<Tool>/` directories share the same subfolder set per the earlier directory listing:
`tests_Forseti`, `tests_Bragi`, `tests_Reporting`, `tests_Verdandi`, `tests_Volundr` all repeat
`L0_Mocked`, `L1_Integration`, `L3_Contract`, `L5_Compliance`, `L8_Performance`, `L14_Industry`)
surfaces a second, previously-unflagged drift:

| Folder suffix used | Canonical Hercules meaning at that number | Match? |
|---|---|---|
| `L0_Mocked` | L0 = Unit | Close enough — "mocked" is a reasonable gloss on isolated/no-I/O, not a contradiction. |
| `L1_Integration` | L1 = Functional (route-handler level); L2 = Integration | **Drifts** — asguardian's own `L1_Integration` folder name uses "Integration," which is canonically L2's word, not L1's. |
| `L3_Contract` | L3 = Contract | Matches exactly. |
| `L5_Compliance` | L5 = Cross-Service; L6 = Compliance | **Drifts, the same specific swap as Kairos and `L5_Meta` above** — "Compliance" content sitting at the `L5` name instead of `L6`. |
| `L8_Performance` | L8 = Module Perf | Matches exactly. |
| `L14_Industry` | L14 = Industry Benchmarks | Matches exactly. |

This means asguardian's L5-means-Compliance drift is not confined to the one top-level `L5_Meta/`
folder the task named — it is the **standing convention across every one of the seven
`tests_<Tool>/` trees** (`Heimdall`, `Forseti`, `Bragi`, `Reporting`, `Verdandi`, `Volundr`, and by
the same pattern almost certainly `Freya`, `Dashboard`, `MCP`, `Shared` too, though those were not
individually opened in this pass). Reporting this rather than silently treating it as covered by
the task's four named folders, per the task's own instruction to read code rather than infer from
names alone.

## 4. Level-by-level table

| Level | Applicable? | What it would test here | Notes |
|---|---|---|---|
| L0 Unit | Yes | Every `tests_<Tool>/L0_Mocked/` tree is already this shape. | No correction needed. |
| L1 Functional | Yes, content needs re-homing | `tests_<Tool>/L1_Integration/` is currently Integration-shaped (per §3) — genuine L1 (route/CLI-handler level, DI-mocked) would be new content, and the existing folder's content is a migration candidate for L2, not L1, per §5. | |
| L2 Integration | Yes | `L2_CrossPackage/` (§2) already fits, once registered; each tool's own `L1_Integration/` content (§3) is also an L2 migration candidate. | |
| L3 Contract | Yes | `tests_<Tool>/L3_Contract/` already correctly named and (presumably) correctly shaped — not individually verified content-wise in this pass beyond the directory name matching canonically. | |
| L4 UI/E2E | Yes, for Freya specifically | Freya is asguardian's own web/UI testing tool — a natural L4 candidate for testing Freya's own dashboard/reporting UI (`tests_Dashboard/`), distinct from Freya's role as a scanning tool used *by* L4 elsewhere. | Not yet manifested. |
| L5 Cross-Service | Uncertain | Genuine cross-service testing (asguardian's MCP server talking to an external Claude Code session, say) is plausible given the MCP server exists, but not established in this pass — and crucially, **not** what any existing `L5_Compliance`/`L5_Meta` folder actually contains (§3). | Do not conflate with the mislabelled compliance content. |
| L6 Compliance | Yes, and this is where the mislabelled content belongs | `L5_Meta/` and every `tests_<Tool>/L5_Compliance/` folder's actual content maps here once renamed (§5). | |
| L7 Module Smoke | Yes, not yet manifested | Live-environment health check per sub-tool once a live asguardian deployment (the dashboard/MCP server) exists. | |
| L8 Module Perf | Yes, and this already has the most mature story of any level in this repo | `L8_PerfBudgets/` (§2) plus every `tests_<Tool>/L8_Performance/`, backed by `_Docs/Testing/L8_Perf_Budget_Policy.md` and its own CI workflow. | Registering this under Hercules would be additive, not a rescue — it already works. |
| L9 System E2E | Uncertain | Depends on whether the dashboard + MCP server + CLI constitute "a system" with journeys worth testing end-to-end, or remain closer to a CLI tool suite; not resolved here. | |
| L10 Load/Stress | Uncertain | Same open question as L9 — depends on whether asguardian's dashboard/MCP server is meant to serve concurrent load at any meaningful scale. | |
| L11 Chaos | Uncertain, likely low priority | Same reasoning as L9/L10; asguardian is a developer tool, not a production service other systems depend on staying up — chaos-testing it is plausible but not obviously valuable without a live multi-user deployment. | |
| L12 Security | Yes | asguardian's own Forseti tool is literally a SAST/DAST scanner — using it to scan its *own* codebase (`test_corpus_and_self_scan.py` in `L8_PerfBudgets/` already does something adjacent to this for perf) is a natural, low-effort L12 target ("does asguardian pass its own security bar"). | |
| L13 Asguardian | **N/A to itself, structurally** | L13 exists specifically to run the Asguardian binary *against another system*. Running asguardian's own L13-shaped assessment against asguardian itself is not meaningless, but it is a different relationship than every other repo's L13 row (self-scan vs. external-target scan) and should be modelled as an L12-adjacent self-scan (already covered above), not force-fit into L13's "external target" framing. | Worth a decision from whoever owns this repo's Hercules manifests, not asserted definitively either way here. |
| L14 Benchmarks | Uncertain | `L14_Industry` folders already exist per-tool (`tests_Heimdall/L14_Industry`, etc.) — worth checking whether these are genuine external-benchmark-shaped (MMLU/HumanEval/RAGAS-equivalent for a static-analysis tool would be something like "detection rate against a labelled vulnerability corpus") or another Meta-shaped folder; not opened in this pass. | |

## 5. Migration path for existing tests

| Existing suite | Maps to | What changes |
|---|---|---|
| `L2_CrossPackage/` | L2 (already correct) | Author `hercules.yaml`, no content change — register as-is. |
| `L8_PerfBudgets/` | L8 (already correct) | Author `hercules.yaml` alongside the existing `l8-perf-budgets.yml` CI workflow, no content change. |
| `L3_Meta/` | No canonical level | Rename away from the `L3` prefix (it is not contract testing) — a coverage-audit tool, better named `coverage-meta/` or similar and left outside the L0-L14 tree entirely, the same way Kairos' `kairos-wide/` is deliberately outside the taxonomy rather than mis-numbered. |
| `L5_Meta/` | L6 (Compliance) | Rename `L5_Meta/` → `L6_Compliance/` (or fold into wherever `tests_<Tool>/L5_Compliance/`'s renamed content ends up, per the next row) — content-wise this already is what canonical L6 wants. |
| Every `tests_<Tool>/L1_Integration/` | L2 (Integration) | Rename `L1_Integration/` → `L2_integration/` per tool; genuine L1 (route/CLI-handler, DI-mocked) becomes new content to author, not a rename. |
| Every `tests_<Tool>/L5_Compliance/` | L6 (Compliance) | Rename `L5_Compliance/` → `L6_compliance/` per tool — same swap as `L5_Meta/`, repeated seven times. |

**None of these renames are applied in this pass** — per the template's explicit instruction not
to silently move files, and because a rename across seven `tests_<Tool>/` trees plus two top-level
folders is a coordinated change that should happen alongside authoring the corresponding
`hercules.yaml` files, not as a bare `git mv` with no manifest to register the result.

## 6. Runner and language-package requirements

`runner.language: python` throughout — asguardian is a single Python package (3.11+). All levels
identified as applicable run via pytest already; `runner.command` per module/level was not
finalised in this pass.

## 7. Environment requirements

- **Ephemeral (L4-L6):** needed only once L4 (Freya's own dashboard UI) is manifested; not
  resolved what infrastructure that would require.
- **Live environments (L7+):** none registered; whether asguardian's dashboard/MCP server has an
  existing deployment target is unassessed.

## 8. Phased adoption order

1. **Phase 0 — Manifests for the already-correct content.** `L2_CrossPackage/` and
   `L8_PerfBudgets/` need only a `hercules.yaml` each — zero content risk, immediate value,
   the lowest-effort win in this entire plan.
2. **Phase 0.5 — The rename/reorganisation from §5.** Coordinated across nine locations
   (`L3_Meta`, `L5_Meta`, seven `tests_<Tool>/L1_Integration` and `L5_Compliance` pairs);
   unstarted, needs sign-off from whoever owns `Asgard_Test/` given its scope.
3. **Phase 1 — Band 1 (L0-L3), per tool.** Mostly already-correct content per tool
   (`L0_Mocked`, `L3_Contract`); L1's genuine content still needs authoring after §5's rename
   frees up the `L1_Integration` name.
4. **Phase 2+ — Bands 2-4.** Blocked on the open L5/L9/L10/L11 applicability questions in §4.
5. **Phase 5 — L12/L13.** L12 (self-scan via Forseti) has no prerequisites and could start in
   Phase 0.

## 9. Blockers and open questions

- **Gitea mTLS migration (template §0.2).** Applies identically to every repo in this workspace.
- **The §5 rename is the largest concrete open item** — a coordinated, multi-location directory
  rename that needs an owner's sign-off, not something to script blind.
- **L5 (Cross-Service), L9, L10, L11, L13's self-scan framing, and L14's actual content (§4)** are
  all genuinely unresolved, each needing a decision or a closer read this pass did not have budget
  for.
- **Whether the drift found in §3 (`L1_Integration`, `L5_Compliance` repeated across seven tool
  trees) extends to the four tool trees not individually opened in this pass (`Freya`, `Dashboard`,
  `MCP`, `Shared`)** is assumed-likely by pattern but not directly confirmed for those four.
