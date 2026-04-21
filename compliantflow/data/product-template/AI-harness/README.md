# AI Harness

Configuration files that help AI coding assistants work correctly in this medical device software repository.

## Structure

```
AI-harness/
├── context.md          # Core project context — DHF location, when to update DHF, compliance gate (model-agnostic)
├── CLAUDE.md           # Claude Code config — references context.md + checklist instructions
├── AGENTS.md           # Generic agent config — references context.md
├── GEMINI.md           # Gemini CLI config — references context.md
├── pre-checklist.md    # Read before starting any code change
├── post-checklist.md   # Verify before opening a PR
└── adapters/           # Model-specific entry points
    ├── .cursorrules            → copy to repo root for Cursor
    └── copilot-instructions.md → copy to .github/ for GitHub Copilot
```

## How it works

`context.md` is the single source of truth. All other files reference it.

The root `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` files (if present) are minimal entry points required by tooling that looks for these files at the repo root.

## What needs user configuration

The following placeholders in `context.md`, `pre-checklist.md`, `post-checklist.md`, and adapters are substituted by `compliantflow init`:

| Placeholder | Description |
|-------------|-------------|
| `{{project_name}}` | Name of this medical device project |
| `{{dhf_repo}}` | GitHub path of the DHF repository (e.g. `acme/insulin-pump-dhf`) |
| `{{standards}}` | Compliance standards selected during init |
