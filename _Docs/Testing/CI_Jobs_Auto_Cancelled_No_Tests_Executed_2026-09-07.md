# CI jobs auto-cancelled: no tests have executed on main

Status: OPEN. Found by the GAIA-workspace CI-compatibility sweep (checking whether CI actually
runs tests, not just what the badge says). No code changed for this finding.

## What was found

`ci.yml`'s five jobs (`Lint`, `Type Check`, `Test (Python 3.11)`, `Test (Python 3.12)`,
`Test (Python 3.13)`) all show conclusion `cancelled` on the last 5 runs against `main` I checked
(run numbers 41, 40, 39, 38, 37; latest checked was run 32203452218). Every one of those jobs
carries **no step data at all** — no "Set up job", no checkout, nothing. `list_workflow_jobs`
returns only the job name, `runs-on: [arc-x86]`, and `created_at`/`completed_at` timestamps.

## What is verified vs. what is inferred

**Verified, directly from the job data:** every job's `completed_at` is exactly 24 hours after its
`created_at` (for example, run 41's jobs: created `2026-08-19T01:01:51/52Z`, completed
`2026-08-20T01:01:52/53Z`, to the second). This pattern repeats identically across all five jobs in
all five runs checked. No log exists for any of these jobs — `get_job_logs` has nothing to return
for a job that never started running.

**Inferred, not verified:** a job whose lifetime is exactly 24 hours with zero recorded steps is
consistent with GitHub Actions' own queue timeout — a job that never gets picked up by a runner is
automatically cancelled 24 hours after being queued. This matches the shape of the evidence, but I
did not independently confirm it against GitHub's own documentation or support channel, and no log
line states "cancelled: queue timeout" or equivalent — there is no log at all to state it.

**Explicitly not verified:** why no runner picks up the job. The repository's own commit history
(`ci: move workflows to self-hosted runners (org policy — cloud runners burn paid minutes and
cannot reach LAN services)`) shows `ci.yml` was deliberately moved onto the self-hosted `arc-x86`
runner label. Whether that pool is offline, unreachable, mislabeled, or simply saturated with other
repositories' jobs on a shared host is not something this sweep determined — there is no log, no
runner-registration data, and no infrastructure access available to this investigation to
distinguish between those causes. Do not read the runner-pool diagnosis in the paragraph above as
verified; it is the most likely explanation given the evidence, not a confirmed root cause.

## Why this is the dangerous case, not the ordinary one

This is not a red build failing on a real assertion, and it is not a green build silently skipping
a step (the two shapes this sweep found elsewhere). It is a third shape: the workflow shows
`cancelled`, not `failure` — a status a human skimming the Actions tab or a PR check list is likely
to read as "did not finish for some external reason," not as "nothing happened here since
2026-08-19." Zero of `Lint`, `Type Check`, or any of the three Python versions' test suites have
run against `main` for at least this last 5-run window (spanning 2026-07-27 through 2026-08-19 by
run timestamps).

## Recommendation

1. Confirm whether the `arc-x86` self-hosted runner pool is online and correctly labeled for this
   repository — this is an infrastructure question outside this repository's own files, and outside
   what this investigation could check.
2. If LAN access genuinely is not required for `Lint`/`Type Check`/`Test (Python 3.1x)` (they appear
   to be pure lint/type-check/pytest jobs with no stated dependency on internal services), consider
   reverting `ci.yml` to `ubuntu-latest` for these jobs specifically, reserving self-hosted runners
   for whichever jobs actually need LAN reachability, so a runner-pool outage does not silently
   zero out this repository's entire test signal for weeks.
3. Whatever the fix, re-run `ci.yml` against `main` once and confirm at least one job reaches a
   real step before treating this as resolved — the absence of `cancelled` is not the same evidence
   as the presence of a passing test.

## Does not license

Treating `cancelled` as equivalent to `success` in any report; assuming the self-hosted pool is
the cause without confirming it; adding `continue-on-error` or similar to make the badge green
without addressing dispatch.
