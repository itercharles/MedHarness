# AI Harness

Configuration files that help AI coding assistants work correctly in this DHF repository.

## Structure

```
AI-harness/
├── context.md          # Core DHF context — item types, invariants, commands (model-agnostic)
├── CLAUDE.md           # Claude Code config — references context.md + checklist instructions
├── AGENTS.md           # Generic agent config — references context.md
├── pre-checklist.md    # Read before starting any DHF change
├── post-checklist.md   # Verify before opening a PR
└── adapters/           # Model-specific entry points that reference context.md
    ├── .cursorrules            → copy to repo root for Cursor
    └── copilot-instructions.md → copy to .github/ for GitHub Copilot
```

## How it works

`context.md` is the single source of truth. All configuration lives in this folder.

The root `CLAUDE.md` and `AGENTS.md` are minimal entry points required by tooling that looks for these files at the repo root — they simply delegate here.

## Adding a new AI tool

1. Create a new file under `adapters/` following the same pattern as the existing ones
2. Include the key rules and common commands
3. Add a note pointing to `context.md` for the full reference
4. Document the install location in this README

## What needs user configuration

The following items in `context.md` are project-specific and are set by `compliantflow init`:

- **Project name** — substituted into `DHF/config/global.yaml`
- **Selected standards** — only the chosen governance files are included in `governance/`
