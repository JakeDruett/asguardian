# Wiring consumer repos into asguardian's CI

Status as of 2026-09-03: asguardian's toolchain analysers (Rust, Node, Go --
see `Asgard/Bragi/Quality/languages/{rust,node,go}/`) exist and are exercised
by asguardian's own test suite, but **no other repo in the suite runs
`asgard`/`heimdall` in its own CI**. Grepping every listed repo's
`.github/workflows/*.yml` for `asguardian`/`asgard`/`heimdall` returned no
hits anywhere except this repo. The analysers exist; nothing calls them yet.

This doc exists because asguardian's own scope (per `CLAUDE.md`) is limited to
this repository -- wiring another repo's CI has to happen in that repo, by
whoever is working there. `.github/workflows/reusable-quality-gate.yml` in
this repo (added alongside this doc) is the piece asguardian itself can
provide: a `workflow_call` job that checks out this repo, installs it from
source, and runs the right `heimdall quality <check>` commands for a given
language. Each consumer repo still needs one small block added to call it.

## The reusable workflow

```yaml
jobs:
  quality-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: rust   # or node, or go
      scan-path: .      # path within the caller repo to scan
```

Verified locally in this sandbox (not via a real Actions run -- no CI runner
available here): the underlying command the workflow issues,
`heimdall quality go-vet Asgard_Test/fixtures/go_toolchain_demo`, installed
correctly from `pip install -e .` and produced the expected real finding
against the checked-in fixture, with the expected nonzero exit code; a
clean check (`go-fmt` on the same fixture) exited 0. The YAML was validated
with `yaml.safe_load`. The workflow-level checkout/install/dispatch wiring
itself was not exercised inside a real GitHub Actions runner, since none is
available in this sandbox -- treat that part as reviewed, not proven.

## Ordering constraint: asguardian must merge first

**Do not apply the snippets below yet.** They all reference
`primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main`,
and that workflow does not exist on `main` -- it was added on
`claude/gaia-compatibility-matrix` and is unmerged. Verified 2026-09-03:
`git ls-tree origin/main -- .github/workflows/` has no
`reusable-quality-gate.yml`.

Once it is merged, replace `@main` with a full 40-character commit SHA in every
snippet below, in the same pass that lifts this ordering constraint. `@main` is a
live dependency on whatever that branch contains at run time; `reusable-quality-
gate.yml` SHA-pins every action it uses for exactly that reason, and a consumer
referencing it by branch gives that back. `@main` here is a placeholder for a ref
that does not exist yet, not the intended end state.

A `uses:` pointing at a workflow that is not on the referenced ref fails at
job-startup with a workflow-not-found error, so wiring a consumer repo today
buys that repo an immediately-red CI job that no code change can fix. The
order is: merge this branch to asguardian `main` first, confirm the workflow
resolves there, then apply the per-repo snippets.

Pinning a consumer to `@claude/gaia-compatibility-matrix` to get around this
is not a fix -- it leaves a dangling ref in every consumer the moment the
branch is deleted after merge.

## Per-repo snippets

Verified against each repo's actual source in this sandbox before writing --
noted per entry. Add a new job to the repo's existing CI workflow (or a new
`.github/workflows/asguardian-quality-gate.yml`); do not replace existing
jobs.

### GVR-Database (Rust)

Verified: `Cargo.toml` at repo root and in `Benchmarking/`.
`.github/workflows/` already has `dependency-scan.yml` and
`dependency-gate.yml` -- check those aren't already doing what `rust-audit`
would add before wiring this in; they may overlap.

```yaml
jobs:
  asguardian-quality-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: rust
      scan-path: .
```

### Lexicon (Rust, Go, Node -- three separate jobs, one per language surface)

Verified: `LexiconRust/Cargo.toml`, `LexiconGo/go.mod`,
`LexiconTypescript/package.json` all present.
`.github/workflows/lexicon-polyglot.yml` is the existing multi-language CI
entry point -- add these as new jobs there rather than a new file, so they
run alongside the existing per-language jobs it already has.

```yaml
jobs:
  asguardian-rust-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: rust
      scan-path: LexiconRust

  asguardian-go-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: go
      scan-path: LexiconGo

  asguardian-node-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: node
      scan-path: LexiconTypescript
```

### Kairos (Node)

Verified: `package.json` at repo root. Note Kairos already calls into
asguardian at the *application* layer (`server/.../Asgard/` routes proxy to
`heimdall` as a subprocess per Kairos' own prompt-continue file) -- that is
a different integration from CI gating the Kairos repo's own code quality,
and both are worth having. `.github/workflows/test.yml` is the existing test
entry point.

```yaml
jobs:
  asguardian-quality-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: node
      scan-path: .
```

### Panoptes (Go)

Verified: `go.mod` (module `github.com/primordial-creations/Panoptes`) at
repo root. `.github/workflows/ci.yml` is the existing entry point.

```yaml
jobs:
  asguardian-quality-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: go
      scan-path: .
```

### Minos (Go, streaming edge only -- the control plane is Python/FastAPI)

Verified: `streaming/go.mod` (module
`github.com/primordial-creations/Minos/streaming`). Per Minos' own
`CLAUDE.md`, the streaming edge is a separate Go module built with its own
toolchain, not part of the root `pyproject.toml` -- scope the scan path to
`streaming/` accordingly. `.github/workflows/ci.yml` is the existing entry
point.

```yaml
jobs:
  asguardian-go-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: go
      scan-path: streaming
```

### Hercules (Go tooling)

Verified: `language-packages/go/go.mod` (module
`github.com/hercules-framework/testing-go`). This is the Go language package
under Hercules' multi-language framework support, not the API/scheduler
services (those are Python). No existing Go CI job found for it.

```yaml
jobs:
  asguardian-go-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: go
      scan-path: language-packages/go
```

### GAIA -- Keryx (Go)

Verified: `GAIA/Keryx/go.mod` (module `gaia/keryx`), with an existing
`.github/workflows/Keryx-go-test.yml` for its own test suite. That workflow
already exists and is the natural place to add a quality-gate job alongside
the test job rather than a new file.

```yaml
jobs:
  asguardian-quality-gate:
    uses: primordial-creations/asguardian/.github/workflows/reusable-quality-gate.yml@main
    with:
      language: go
      scan-path: Keryx
```

Note: `Keryx/go.mod` has `replace gaia/lexicon => ../Lexicon/LexiconGo`,
resolved relative to `Keryx/`. In this sandbox that resolves because
`GAIA/Lexicon` exists as a checkout nested under `GAIA/`; a real CI checkout
of only the `GAIA` repo needs that sibling path to exist too (it does, since
`Lexicon` lives inside the `GAIA` monorepo tree here) -- this is a note for
whoever wires it, not something asguardian's workflow can control.

### Talos -- premise not confirmed, flagged rather than wired

The original handover entry ("Rust ... Talos") does not match what is in this
sandbox: `find /home/user/Talos -iname "Cargo.toml" -o -iname "*.rs"`
returns nothing. Talos' repo tree here is `ServiceLayer/`, `Gateways/`,
`TalosServer/`, `RemoteServer/`, `CLI/`, `userInterfaces/`, with a root
`package.json` and no Rust source at all. `.github/workflows/` has
`talos.yaml`, `talos-mobile-ci.yaml`, `promote-to-uat.yaml` (`.yaml`, not
`.yml` -- easy to miss with a `*.yml` glob). Rather than write a Rust snippet
for code that is not there, or an unfounded Node snippet for code I have not
read closely enough to characterise correctly, this is left for whoever
verifies Talos' actual current language mix.

## Not attempted here

Every snippet above is unapplied -- CRITICAL SCOPE LIMIT for this pass was
"only modify files inside asguardian", and several of these repos have other
agents working in them concurrently. Apply the relevant block by hand (or
task an agent already working in that repo to add it), then confirm with a
real run rather than trusting this doc's local-only verification.
