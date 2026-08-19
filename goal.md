# CyberHardening Goal

## North star

Every code file in this repository has been **traced** for security vulnerabilities — including how it interacts with other files — and every discovery plus a **planned fix** is recorded in the CyberHardening plan under the Planning folder. The scan todo list is **empty**.

This goal is **repository-agnostic**. It applies to whatever tree this file sits in.

---

## The continuation rule (override everything else)

**If the scan todo list has any remaining item, you are not done. Keep working.**

After every batch, reload the todo list from disk and continue. Do not ask whether to continue. Do not substitute a summary, a sample, a risk overview, or a “good enough” plan for a finished inventory.

The only legitimate stops:

1. **Done:** `todo.json` remaining is empty **after** a refresh `init` that discovered no new code files, and every completed file has a ledger entry plus plan updates (findings or clean bill).
2. **Hard block:** the working tree is unreadable or the inventory script cannot run. Write the blocker into the plan’s Scan progress section, persist all state, then stop.
3. **Session cap:** persist plan, ledger, and todo, write a resume pointer (remaining count + next paths) into Scan progress, then stop so a successor can continue from disk.

A long session, a large remaining count, or “enough Critical findings already” is **not** a stop condition.

---

## Definition of done

All of the following must be true at the same time:

1. An inventory script exists at `scripts/cyberhardening_inventory.py` (or `.sh`) and can `init` / `status` / `next` / `done` / `remaining`.
2. That script’s include rules cover **every file with code** in the repo (source, tests, scripts, IaC, CI-as-code, templates that execute, shebang files). Exclusions are only vendor/artifact/binary/non-code, as specified in `prompt.md`.
3. `<Planning>/CyberHardening/todo.json` exists, was produced by the script, and **`remaining` is `[]`** after one final `init`.
4. Every path that appeared in the inventory is in `completed` with a `disposition` of `findings` or `clean`.
5. `<Planning>/CyberHardening/ledger.jsonl` has **one line per completed file**, matching `todo.json`.
6. The CyberHardening plan (`<Planning>/CyberHardening.md` or the existing equivalent under the Planning folder) contains:
   - every finding with ID, severity, confidence, primary file, trace, impact, and **planned fix**
   - clean-bill coverage via the ledger (the plan need not narrate every clean file)
   - an updated Summary table
   - planned fix waves for open items
7. No completed file was popped without a recorded scan. No live secret is written in full into the plan, ledger, or git history by this work.
8. Planned fixes are **plans**, not unrequested repo-wide implementations.

Until 1–8 hold, the goal is **unsatisfied**. Continue per `prompt.md`.

---

## What does not count as done

- Scanning a subdirectory, a “critical path,” or a random sample
- Grep / Semgrep / a tool run **instead of** per-file traces (tools may assist; they do not replace tracing or the todo loop)
- A narrative security review with no todo list
- Findings without planned fixes
- Planned fixes without popping the corresponding files
- Popping files that were not actually traced
- “We will finish the rest later” while remaining > 0
- Implementing fixes while leaving the inventory incomplete

---

## Success test

A successor agent, given only this repo on disk and no chat history, can run the inventory `status` command, see **0 remaining**, open the CyberHardening plan, and execute the first fix wave from written traces and planned fixes alone.

---

## Operating pointer

Follow `prompt.md` in the repository root for paths, script contract, sub-agent rules, finding schema, and the scan loop. This file is the **why and when to stop**. That file is the **how**. If they ever conflict on whether to stop, **this file wins**: remaining items mean continue.
