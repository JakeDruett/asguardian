# To-Do: Publish Asgard to PyPI

## Goal
Automate PyPI publishing via GitHub Actions on the standalone `github.com/JakeDruett/asgard` repo using self-hosted runners.

## Decisions Needed
- [x] Package name: `asguardian` (both `asgardian` and `asguardian` were available; `asgard` is taken)
- [ ] Confirm self-hosted runners are org-level (so the standalone repo can use them), or re-register them if repo-level

## Steps
1. Update `pyproject.toml` — change `name` to the chosen package name
2. Create `.github/workflows/publish.yml` in this folder (it will be pushed to the standalone repo via `publish-asgard.sh`)
   - Trigger: push of a `v*` tag on the standalone repo
   - Runner: `[self-hosted, UAT, arm64]`
   - Steps: checkout, setup-python, build, twine upload
3. Create a PyPI API token at pypi.org and add it as secret `PYPI_API_TOKEN` on the standalone GitHub repo
4. Push subtree: `./Asgard/publish-asgard.sh` from GAIA monorepo root
5. Tag a release on the standalone repo to trigger the first publish

## Notes
- The publish script is at `Asgard/publish-asgard.sh` (run from GAIA monorepo root)
- Runner label from existing workflows: `[self-hosted, UAT, arm64]`
- PyPI publishing uses Twine with `__token__` as the username and the API token as the password
