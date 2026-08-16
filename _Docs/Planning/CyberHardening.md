# CyberHardening Plan

Status: IN PROGRESS
Started: 2026-08-16
Repo: Asgard

## Purpose

Track every security finding discovered by the full-tree traced audit, and the planned fix for each. This document is the hardening backlog, not a marketing summary.

## Method

Every inventoried code file is traced (not merely grepped). Findings include cross-file data flow, trust boundaries, and a planned fix. Files with no issue get a clean-bill entry in the ledger.

## Inventory

- Script: `scripts/cyberhardening_inventory.py`
- Todo: `_Docs/Planning/CyberHardening/todo.json`
- Ledger: `_Docs/Planning/CyberHardening/ledger.jsonl`
- Planning folder: `_Docs/Planning/` (first existing match)

## Summary

| Severity | Open | Planned | Accepted risk |
|----------|------|---------|---------------|
| Critical | 0    | 0       | 0             |
| High     | 0    | 0       | 0             |
| Medium   | 0    | 0       | 0             |
| Low      | 0    | 0       | 0             |
| Info     | 0    | 0       | 0             |

## Findings

<!-- Newest findings appended below. Never delete a finding; mark status changes in place. -->

## Planned fix waves

Group planned fixes into dependency-ordered waves once enough findings exist to see clusters. Update after each batch, not only at the end.

## Accepted risks

Only with a written reason, owner-role (not a person’s private data), and residual impact.

## Scan progress

- Inventory init (2026-08-16): discovered=3875 remaining=3875 completed=0
- Last paths completed: (none)
- Next batch: first remaining paths starting at `.github/workflows/ci.yml`
- Resume pointer: remaining=3875; process lexicographic remaining from `todo.json`
