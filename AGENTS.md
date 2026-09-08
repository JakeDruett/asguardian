# Repository Agent Instructions

## Mandatory Git workflow

- Never make a commit directly on `main`.
- Before editing, create or switch to a non-`main` working branch.
- Commit all work on that branch, then integrate it into `main` with a pull-request merge or a local non-fast-forward merge.
- If uncommitted work is found on `main`, create a branch at once and commit it there; do not commit it on `main` first.
- Never push a direct, non-merge commit to `main`. Do not push any branch or tag unless the user explicitly requests it.
