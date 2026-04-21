# Pre-Checklist

Read this before starting analysis on any task.

- **Understand the scope** — identify which layer owns the change (CLI, compliance engine, DHF utils, CI). Changes should stay in the owning layer.
- **Find affected tests** — locate the test file(s) for the code you'll touch before writing anything. Know what already exists.
- **Check docs that may need updating** — if the task touches user-visible behaviour, note which sections of `GETTING_STARTED.md` are affected.
- **Check for stale references** — if the task involves version numbers, install paths, or command examples, locate every place they appear before editing.
- **Confirm the CR exists and is `planned`** — if this is a tracked change, verify the CR item exists in the DHF before writing code.
