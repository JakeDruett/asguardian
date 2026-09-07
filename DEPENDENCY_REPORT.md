# Asguardian Dependency Analysis Report

Generated: 2026-03-19

---

## Declared Dependencies (`pyproject.toml`)

### Core

| Package | Version | Files | Lines | Purpose |
|---|---|---|---|---|
| pydantic | >=2.0.0 | 108 | ~6,738 | Data validation, schema definition, configuration models |
| pyyaml | >=6.0 | 44 | ~136 | YAML parsing/generation for config, K8s, Docker, Helm, CI/CD |
| playwright | >=1.40.0 | 22-23 | ~623 | Browser automation for Freya web testing module |

### Test (optional extras)

| Package | Version | Purpose |
|---|---|---|
| pytest | >=7.0.0 | Test framework — 200+ files, 17,652 lines of tests |
| pytest-asyncio | >=0.21.0 | async/await support in tests |
| pytest-mock | >=3.10.0 | Fixture-based mocking |
| pytest-cov | >=4.0.0 | Coverage reporting |

---

## Undeclared Dependencies (used in code, missing from `pyproject.toml`)

> These are a packaging bug — the project will fail to install cleanly without them.

### Production Code

| Package | Files | Purpose | Key Files |
|---|---|---|---|
| **httpx** | 4 | Async HTTP client for link validation, header scanning, robots.txt, image optimization | `Freya/Security/services/security_header_scanner.py`, `Freya/Links/services/link_validator.py`, `Freya/SEO/services/robots_analyzer.py`, `Freya/Images/services/image_optimization_scanner.py` |
| **networkx** | 4 | Dependency graph algorithms (cycle detection, modularity, centrality) | `Heimdall/Dependencies/services/cycle_detector.py`, `Heimdall/Dependencies/services/graph_builder.py`, `Heimdall/Dependencies/utilities/graph_utils.py`, `Heimdall/Dependencies/services/modularity_analyzer.py` |
| **matplotlib** | 1 | Dependency graph visualization | `Heimdall/Dependencies/services/graph_builder.py` |

### Generators / Scaffold (not runtime)

| Package | Files | Purpose |
|---|---|---|
| fastapi | 2 | Template generation for FastAPI microservice scaffolds and mock servers |
| flask | 1 | Template generation for Flask mock servers |

### Test-Only

| Package | Files | Purpose |
|---|---|---|
| sqlalchemy | 3 | Mocking database analyzers and Forseti DB integration tests |
| django | 2 | Mocking Django ORM in tests |
| redis | 1 | Mocking Redis cache analyzer in tests |
| requests | 3 | HTTP testing utilities in tests |
| numpy | 3 | Statistical calculations in tests |

---

## Full Dependency Summary

| Package | Declared | Type | Files | Lines | Replaceability |
|---|---|---|---|---|---|
| pydantic | Yes | Core | 108 | 6,738 | Not realistic |
| pyyaml | Yes | Core | 44 | ~136 | Not practical (ecosystem lock-in) |
| playwright | Yes | Core | 22-23 | ~623 | Not realistic |
| pytest | Yes | Test | 200+ | 17,652 | Replaceable, impractical |
| pytest-asyncio | Yes | Test | many | — | Replaceable |
| pytest-mock | Yes | Test | many | — | Replaceable |
| pytest-cov | Yes | Test | many | — | Replaceable |
| **httpx** | **No** | Production | 4 | ~68 | Yes — custom or stdlib |
| **networkx** | **No** | Production | 4 | — | Partially — custom graph for ~80% |
| **matplotlib** | **No** | Production | 1 | ~10 | Easily — drop or use graphviz |
| fastapi | No | Generator | 2 | — | Easily — string templates |
| flask | No | Generator | 1 | — | Easily — string templates |
| django | No | Test | 2 | — | Yes — mock differently |
| sqlalchemy | No | Test/Gen | 3 | — | Yes |
| redis | No | Test | 1 | — | Easily |
| requests | No | Test | 3 | — | Yes — use httpx or urllib |
| numpy | No | Test | 3 | — | Easily — use `statistics` stdlib |

---

## Replaceability Assessment

### Not Worth Replacing

**pydantic** — The entire data model layer of the application is built on Pydantic `BaseModel`. It's present in every module (Heimdall, Freya, Forseti, Verdandi, Volundr, Asgard config). Replacing it would mean rewriting the application.

**playwright** — Browser automation at this level requires the Chrome DevTools Protocol. There is no stdlib equivalent. Selenium is the only alternative, but that's still a third-party browser library — a trade, not a removal.

**pyyaml** — The YAML format is mandated by the K8s, Docker Compose, Helm, and CI/CD ecosystems that Asguardian generates files for. Even if parsing were replaced, output must remain YAML.

---

### Good Candidates for Custom Replacement

#### `httpx` → custom async HTTP client
- **Scope:** 4 files, ~68 lines
- **Approach:** `asyncio` + `urllib.request` with an async wrapper
- **Effort:** Low (~50-100 lines of custom code)
- **Covers:** GET requests, response headers, status codes, redirect following
- **Benefit:** Removes an undeclared production dependency

#### `networkx` → custom graph module
- **Scope:** 4 files in `Heimdall/Dependencies/`
- **Approach:** Custom `Graph` class with adjacency list; implement DFS-based cycle detection, topological sort, and basic modularity scoring
- **Effort:** Medium (~200-300 lines)
- **Covers:** ~80% of current usage
- **Gap:** Advanced modularity/community detection algorithms are harder; may keep networkx optional for those features
- **Benefit:** Removes an undeclared production dependency; improves portability

#### `matplotlib` → drop or replace
- **Scope:** 1 file, ~10 lines
- **Approach:** Output Graphviz `.dot` format (stdlib-friendly) or plain ASCII adjacency list; alternatively remove visualization entirely
- **Effort:** Minimal
- **Benefit:** Removes a heavyweight undeclared production dependency

#### Test deps (`numpy`, `redis`, `requests`, `django`)
- All test-only. Replace `numpy` with `statistics` stdlib, `requests` with `urllib`, and mock `redis`/`django` without importing the real packages.
- **Effort:** Low per dep

---

## Key Files Reference

| File | Relevance |
|---|---|
| `pyproject.toml` | All declared dependencies |
| `Asgard/config/models.py` | Main Pydantic config model (854 lines) |
| `Asgard/config/loader.py` | PyYAML config loading |
| `Asgard/Freya/Integration/services/playwright_utils.py` | Playwright core utilities (409 lines) |
| `Asgard/Heimdall/Dependencies/services/graph_builder.py` | NetworkX + matplotlib usage |
| `Asgard/Heimdall/Dependencies/services/cycle_detector.py` | NetworkX cycle detection |
| `Asgard/Heimdall/Dependencies/utilities/graph_utils.py` | NetworkX graph utilities |
| `Asgard/Freya/Links/services/link_validator.py` | httpx usage |
| `Asgard/Freya/Security/services/security_header_scanner.py` | httpx usage |
| `Asgard/Freya/SEO/services/robots_analyzer.py` | httpx usage |
| `Asgard/Freya/Images/services/image_optimization_scanner.py` | httpx usage |

---

## Recommended Actions

1. **Fix packaging bug** — Add `httpx`, `networkx`, and `matplotlib` to `pyproject.toml` immediately so the package installs correctly.
2. **Replace `httpx`** — Small scope, high value. Custom async HTTP covers all use cases.
3. **Replace `matplotlib`** — Trivial effort, removes a heavy dependency.
4. **Partially replace `networkx`** — Custom graph module for core algorithms; keep networkx optional for advanced modularity analysis.
5. **Clean up test deps** — Replace `numpy`, `requests`, `redis`, `django` test imports with stdlib equivalents.
6. **Leave alone** — `pydantic`, `playwright`, `pyyaml`.
