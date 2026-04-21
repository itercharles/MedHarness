# Post-Checklist

Verify each applicable item before declaring a task done.

- [ ] **Tests run locally** — run the relevant test file with `.venv/bin/python -m pytest <file> -q` and confirm all pass
- [ ] **Smoke tested** — for user-facing features (e.g. `init`, CLI commands), run a quick functional check in Python to verify the core path works end-to-end
- [ ] **Docs updated** — if the change affects user-visible behaviour, update `GETTING_STARTED.md`; if it changes CLI output or prompts, update the relevant examples
- [ ] **No stale references** — check for hardcoded version numbers, install paths, or command examples that may be out of date
- [ ] **Release tagged** — after committing and pushing, tag with `git tag vX.Y.Z && git push origin vX.Y.Z` to trigger CI build
