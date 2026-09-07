# Continue: GAIA suite compatibility matrix -- asguardian

Branch: `claude/gaia-compatibility-matrix`

This file is the handover for the suite-wide compatibility work as it applies to
asguardian. It records what was done in the sandbox, what is deliberately left,
and which remaining actions are destructive and must not be taken without Jake
Druett's explicit approval.

Read `CLAUDE.md` first. The global rules there override anything in this file.

## Context

asguardian is the suite's development-quality-assurance toolkit (`asgard` CLI).
Its suite obligations are narrow: it is a developer tool, not a deployed service,
so the Lexicon-or-bust infrastructure ruling mostly does not bite here -- it has
no database, no broker, and no secrets of its own. Its obligation is instead to
be able to analyse every language the suite actually writes.

## Done and pushed

1. **Rust and Node toolchain analysis added.** asguardian could only analyse
   Python, but the suite writes Rust (GVR-Database, LexiconRust, Talos) and
   Node/TypeScript (Kairos, Zeus, LexiconTypescript, Panoptes SDK). Both
   analysers are now present.

2. **Four defects fixed after adversarial review of those analysers.** The
   review re-ran everything rather than trusting the implementation report, and
   found:
   - **CVSS severity mapping was silently wrong.** The code read
     `advisory.cvss.get("severity")`, but real `cargo-audit` output emits a CVSS
     *vector string*, not an object with a `severity` key. Every advisory was
     therefore downgraded to WARNING -- a security scanner reporting nothing is
     worse than no scanner. Fixed to parse the vector.
   - **`tsc` failure detection was absent.** A TypeScript compile that failed
     outright was not distinguished from one that passed.
   - **Exit code could not distinguish a clean scan from a crashed tool.** Both
     produced the same result.
   - **Undeclared dependencies** on `matplotlib` and `networkx`.

3. **Licensing** brought into line with the suite ruling: proprietary,
   attributed to Jake Druett.

4. **`CLAUDE.md` structural parity** with the other ten repos, including the
   global rules block and the Claude service-credential section.

5. **Hercules adoption plan and `hercules.yaml` manifest normalisation** --
   asguardian is registered as a Hercules product with the agreed L0-L14 level
   taxonomy.

## Left to do

### Not destructive -- safe to pick up directly

- **Go analyser.** Rust and Node closed the two biggest gaps, but the suite also
  writes Go (Keryx, Panoptes ingest, Minos streaming edge, LexiconGo, Hercules
  tooling). asguardian still cannot analyse it. This is the obvious next
  increment and follows the exact shape of the Rust/Node work already merged.
- **Wire asguardian into the other repos' CI.** Kairos was pointed at asguardian
  as a backend per Jake's ruling, but only partially -- see Kairos' own
  prompt-continue file. Nothing else in the suite runs `asgard` in CI yet, so
  the analysers exist but are not actually protecting anything.
- **Verify the CVSS fix against a real advisory corpus.** The fix was verified
  against captured `cargo-audit` output. It has not been run against a broad set
  of real advisories, so the severity mapping is correct-in-principle rather
  than correct-in-evidence.

### Requires Jake's approval before acting

- **Publishing to PyPI.** asguardian is the one repo in the suite that is
  published (`asguardian` on PyPI, CLI `asgard`). Any version bump that would
  trigger a release is an outward-facing, effectively irreversible action.
  Do not publish, tag a release, or bump the published version without Jake
  saying so explicitly. Note the tension with the suite's proprietary-licensing
  ruling -- whether asguardian stays public is Jake's call, not an agent's.

## Warnings

- **Never build or push a container image locally, and never deploy.**
  Everything goes through CI/CD. This is a hard rule across all eleven repos.
- **Do not procedurally generate code with a script.** This rule earned itself
  during this work: a heuristic script used elsewhere in the suite wrongly
  marked two functions `async` because their `await`s were in nested closures.
  It was caught only by `node --check`. Write the code.
- **Sub-agents default to Sonnet or Haiku** unless Jake specifies otherwise.
- A security scanner that reports nothing looks identical to a clean codebase.
  When touching the analysers, always prove the failure path fires -- construct
  an input that *must* produce a finding and assert that it does.
