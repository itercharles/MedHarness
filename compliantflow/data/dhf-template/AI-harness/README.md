# AI Harness

Configuration files that help AI coding assistants work correctly in this DHF repository.

## Structure

```
AI-harness/
├── context.md          # Core DHF context — item types, invariants, commands (model-agnostic)
├── pre-checklist.md    # Read before starting any DHF change
├── post-checklist.md   # Verify before opening a PR
└── adapters/           # Model-specific entry points that reference context.md
    ├── .cursorrules            → copy to repo root for Cursor
    └── copilot-instructions.md → copy to .github/ for GitHub Copilot
```

## How it works

`context.md` is the single source of truth. The root `CLAUDE.md` and `AGENTS.md` files reference it directly. Adapter files for other tools contain a condensed version with a pointer back to `context.md`.

## Adding a new AI tool

1. Create a new file under `adapters/` following the same pattern as the existing ones
2. Include the key rules and common commands
3. Add a note pointing to `context.md` for the full reference
4. Document the install location in this README

## What needs user configuration

The following items in `context.md` are project-specific and are set by `compliantflow init`:

- **Project name** — substituted into `DHF/config/global.yaml`
- **Selected standards** — only the chosen governance files are included in `governance/`
