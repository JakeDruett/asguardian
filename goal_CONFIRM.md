# CyberHardening Confirmation Goal

## North star

This repository already finished a CyberHardening **audit** and an **implementation** pass. Every live finding was marked **Fixed** or **Accepted risk**. This pass **re-traces the tree** and **confirms** those claims.

Every code file is scanned again. Every prior finding is re-traced against the current code. Each one is recorded as **Confirmed**, **Reopened**, **Residual**, **Accepted still**, or **Vacated**. New holes get new IDs. The confirmation todo list is **empty**.

This goal is **repository-agnostic**. It applies to whatever tree this file sits in. The first audit is finished. The fixes are claimed. This pass **verifies**.

---

## Pairing (do not mix missions)

| Files | Mission |
|-------|---------|
| `goal.md` + `prompt.md` | First full-tree audit. Discover + plan. Do not implement. |
| `goal_IMPLEMENTATION.md` + `prompt_IMPLEMENTATION.md` | Apply Open planned fixes. Do not re-audit. |
| `goal_CONFIRM.md` + `prompt_CONFIRM.md` | **This pass.** Rescan a already-fixed tree. Confirm or reopen. Do not implement. |

If this tree has **Open** findings, you are in the wrong mission. Stop and run the implementation pair instead.

---

## The continuation rule (override everything else)

**If the confirmation todo list has any remaining item, you are not done. Keep working.**

After every batch, reload the confirmation todo from disk and continue. Do not ask whether to continue. Do not substitute a sample of High findings, a “spot-check of W1,” or a narrative review for a finished confirmation inventory.

The only legitimate stops:

1. **Done:** confirmation `todo.json` remaining is empty **after** a refresh `init` that discovered no new code files; every completed file has a confirmation-ledger entry; every live original finding has a confirmation verdict; every new issue has a `CHC-XXXX` record.
2. **Hard block:** there is no CyberHardening plan, implementation is not finished (Open > 0), the working tree is unreadable, or the inventory script cannot run. Write the blocker into the confirmation plan’s progress section, persist all state, then stop.
3. **Session cap:** persist confirmation plan, ledger, and todo, write a resume pointer (remaining count + next paths + next unconfirmed original IDs), then stop so a successor can continue from disk.

A long session, a large remaining count, or “the High ones confirmed already” is **not** a stop condition.

---

## Definition of done

All of the following must be true at the same time:

1. An existing CyberHardening plan is present (see `prompt_CONFIRM.md` for path resolution). It is the **same file** the audit and implementation used. This pass did not start a competing first-audit plan and did not wipe findings.
2. That plan shows **0 Open** live findings (withdrawn IDs do not count). Status is `FIXES APPLIED` or `FIXES APPLIED — N ACCEPTED RISKS`, or an equivalent recount of the findings matches 0 Open.
3. The inventory script exists and can `init` / `status` / `next` / `done` / `remaining` against a **confirmation workspace** that is **not** the original `todo.json`.
4. Confirmation include rules still cover **every file with code** (same meaning as `prompt.md`).
5. `<Planning>/CyberHardeningConfirm/todo.json` exists and **`remaining` is `[]`** after one final `init`.
6. Every path in that inventory is in `completed` with a disposition (`confirmed` / `reopened` / `residual` / `new-findings` / `clean`).
7. `<Planning>/CyberHardeningConfirm/ledger.jsonl` has **one line per completed file**.
8. The confirmation plan (`<Planning>/CyberHardeningConfirm.md`) contains:
   - a verdict row or section for **every** live original `CH-XXXX` (and withdrawn IDs listed as skipped)
   - every new finding as `CHC-XXXX` with ID, severity, confidence, primary file, trace, impact, and **planned fix**
   - an updated Summary table
   - a progress section whose remaining count is 0
9. Original audit history is intact: original traces, planned fixes, implementation notes, `todo.json`, scan `ledger.jsonl`, and `fix_ledger.jsonl` were not rewritten or deleted.
10. No live secret is written in full into the confirmation plan, ledger, or git history. This pass did **not** implement product fixes (except the same emergency secret-removal rule as the first audit).

Until 1–10 hold, the goal is **unsatisfied**. Continue per `prompt_CONFIRM.md`.

---

## What a verdict means

| Verdict | Meaning |
|---------|---------|
| **Confirmed** | The stated source → sink is closed in current code. The control is actually on the path, not a comment or unused helper. |
| **Reopened** | The same (or an equivalent) source → sink is still live. The fix is missing, bypassed, reverted, or theater. |
| **Residual** | The stated sink is closed, but a leftover of the same class remains (the implementation note already said so, or this pass found a sibling). Not a full reopen. |
| **Accepted still** | Original status is Accepted risk; the hole is still there; reason still holds. |
| **Vacated** | Primary file or sink is gone and the capability did not move. Say where you looked. |
| **Skipped (withdrawn)** | Audit merged this ID into another. Do not reuse it. |

A finding is **not** Confirmed because:

- the plan says Fixed
- a helper exists but is not called
- a test exists but the production path does not use the control
- you grepped for a function name and stopped

---

## What does not count as done

- Confirming only Critical/High and leaving the rest untraced
- Re-reading implementation notes instead of re-tracing current code
- Grep / Semgrep / a tool run **instead of** per-file traces
- Marking Confirmed because Status is Fixed
- Popping files that were not re-traced
- Rewriting or deleting the original plan / original todo / original ledgers
- Implementing reopenings in this pass (record them; do not “just fix it”)
- Starting a new first-audit plan because “the old one is stale”
- Treating residual notes from implementation as Confirmed without looking

---

## Success test

A successor agent, given only this repo on disk and no chat history, can:

1. Open the original CyberHardening plan and see **0 Open**.
2. Open the confirmation plan and see a verdict on every live `CH-XXXX`.
3. Run confirmation `status` and see **0 remaining**.
4. List every **Reopened** and every **CHC-** finding and know what to implement next.

---

## Operating pointer

Follow `prompt_CONFIRM.md` in the repository root for paths, workspace isolation, sub-agent rules, verdict schema, and the rescan loop. This file is the **why and when to stop**. That file is the **how**. If they ever conflict on whether to stop, **this file wins**: remaining confirmation items mean continue.
