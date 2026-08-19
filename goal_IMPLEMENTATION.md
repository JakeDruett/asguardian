# CyberHardening Implementation Goal

## North star

Every **Open** finding in the CyberHardening plan has been **implemented**, **tested**, **committed**, and marked **Fixed** (or formally **Accepted risk**). A successor can reconstruct *what changed and why* from git history and the plan alone.

This goal is **repository-agnostic**. It applies to whatever tree this file sits in. The audit is finished. This pass **applies** the planned fixes.

---

## The continuation rule (override everything else)

**If any finding in the CyberHardening plan still has Status `Open`, you are not done. Keep working.**

After every finding (or tightly coupled cluster), reload the plan from disk and continue. Do not ask whether to continue. Do not substitute a sample wave, a design note, or “the high-severity ones are done” for a finished backlog.

The only legitimate stops:

1. **Done:** every finding is `Fixed` or `Accepted risk`, the Summary table matches those statuses, every Fixed finding has a git commit that names its ID, and a refresh of the plan from disk still shows **0 Open**.
2. **Hard block:** the working tree is unreadable, tests cannot run, or the plan file is missing. Write the blocker into the plan’s implementation-progress section, commit whatever is already correct, then stop.
3. **Session cap:** commit all landed fixes, update the plan (statuses + next Open IDs), then stop so a successor can continue from disk and git log.

A long session, a large Open count, or “enough Critical/High fixes already” is **not** a stop condition.

---

## Definition of done

All of the following must be true at the same time:

1. The CyberHardening plan exists (see `prompt_IMPLEMENTATION.md` for path resolution) and is the **same file** the audit used. No second competing plan.
2. Every `### CH-XXXX` finding that is not withdrawn has Status **Fixed** or **Accepted risk**. Withdrawn IDs stay withdrawn.
3. The Summary table counts match the findings (Open = 0; Fixed + Accepted risk = every live finding).
4. Each **Fixed** finding:
   - implements the **Planned fix** (or a stricter equivalent that still closes the stated trace)
   - has tests or another stated verification named in the finding or added beside it
   - is referenced by at least one git commit message containing that `CH-XXXX` ID
5. Each **Accepted risk** has a written reason, owner-role (not a person’s private data), residual impact, and a commit that records the acceptance on the finding.
6. Implementation history is **not squashed**. One finding (or one declared cluster sharing a single sink) is one commit, so `git log` is the timeline.
7. No live secret is written in full into the plan, ledger, commit message, or chat.
8. Product behavior that the finding did not authorize is unchanged. No drive-by refactors.

Until 1–8 hold, the goal is **unsatisfied**. Continue per `prompt_IMPLEMENTATION.md`.

---

## What does not count as done

- Fixing only Critical/High and leaving Medium/Low/Info Open
- Marking Status Fixed without a commit that names the ID
- One giant commit that “does W1”
- Rewriting the planned fix into a weaker control and calling it done
- Deleting the scanner, test, or generator instead of closing the sink
- Accepting risk with no written reason
- Opening a PR / pushing a remote as a substitute for landing the rest
- Starting a new audit instead of implementing

---

## Success test

A successor agent, given only this repo on disk and no chat history, can:

1. Open the CyberHardening plan and see **0 Open**.
2. Run `git log --oneline` and find a commit per Fixed finding (or documented cluster) whose message contains the `CH-XXXX` ID.
3. Re-run the tests named on a sample of Fixed findings and see them pass.

---

## Operating pointer

Follow `prompt_IMPLEMENTATION.md` in the repository root for paths, wave order, commit rules, sub-agent rules, and the implement loop. This file is the **why and when to stop**. That file is the **how**. If they ever conflict on whether to stop, **this file wins**: Open findings mean continue.
