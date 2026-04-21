# Pre-Checklist

Read this before starting any code change.

- **Does this change require a DHF update?** — check the table in `AI-harness/context.md`. If yes, create a CR in the DHF repo before writing any code.
- **CR exists and is `planned`** — if a DHF update is needed, verify the CR item exists: `PYTHONPATH=.:DHF python -m utils item list --type CR` in the DHF repo.
- **CR ID is in your branch name** — e.g. `feat/CR-042-add-input-validation`. CI Phase 0 rejects PRs without a CR ID in the title.
- **DHF repo is cloned locally** — if running local compliance checks, the DHF repo must be adjacent: `git clone https://github.com/{{dhf_repo}} ../$(basename {{dhf_repo}})`.
- **Understand the compliance gate** — read what the CI checks in `AI-harness/context.md` so you know what must pass before merge.
