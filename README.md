# MedHarness

**AI-assisted development with design control: your AI agent writes the code and
the design record, and ordinary code checks that they agree before anything
merges.**

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

```mermaid
flowchart LR
    A["<b>1 · Design</b><br/>AI drafts the design"] -->|"<b>you review</b>"| B["<b>2 · Code</b><br/>AI codes and tests"]
    B -->|"<b>you review</b>"| C(["Merge"])
```

For each change request, the agent **designs** first — it assesses the change's
risk, then writes the requirements, design and test points it needs as items in
your repository's Design History File (DHF), each traced to the next — and
**codes** second, tagging each test with the requirement it verifies. You review
the design, then the code. Between them, ordinary code — never a model — checks
that the design traces, every requirement is verified, and the branch changed
what the request said.

`init` writes an `AGENTS.md` (and a `CLAUDE.md` that imports it) telling your
agent when to open a change request and which commands to run; it reads and
writes the DHF through `medharness item`, which refuses a bad edit, and the
checks name the item and field that are wrong. What to call when is in
[Working with your coding agent](docs/agents.md).

Two ways to run it:

- **At your desk**, with the agent you already use: it works in your tree and you commit.
- **Unattended**, from an issue: CI opens the change request and a pull request with
  the design, revises on review, then does the code the same way
  ([recipe](docs/ai-workflow.md#wiring-it-into-github-actions)). This runs an agent
  with a shell: use an ephemeral runner and read [ai-security.md](docs/ai-security.md) first.

## Quick start

```bash
pip install medharness
mkdir my-device && cd my-device
medharness init            # writes DHF/ with sample items, and AGENTS.md for your agent
```

Then ask your coding agent: *"open a CR for PDF export and implement it"*.
Or use the checks alone, with no AI: `medharness verify dhf` checks that the
design holds together.

## What a project looks like

```
my-device/
├── DHF/
│   ├── config/global.yaml       # the project name — and only what you change
│   └── items/                   # one YAML file per item, one directory per type
│       ├── 01_crs/CRS-001.yaml
│       ├── 03_srs/SRS-001.yaml
│       └── …
├── AGENTS.md                    # product context and DHF steps, for any coding agent
└── CLAUDE.md                    # @AGENTS.md, so Claude Code reads it too
```

The item types, their lifecycles and the specification templates ship in the
package; a project overrides only what it changes
([configuration.md](docs/configuration.md)). An item is a small YAML file, with
links written on the child and pointing up:

```yaml
id: SRS-012
title: Password must be at least 12 characters
derives_from: [SYS-004]
verification_method: [Test]
testing: |
  T1: an 11-character password is rejected
```

One CLI, `medharness`, in four groups: `item` reads and changes items, `verify`
checks and writes nothing, `build` produces items, code and release artifacts,
`init` scaffolds. What each command does, prints and exits with is in
[interface.md](docs/interface.md); `--help` lists its options.

[ContourLab](https://github.com/itercharles/ContourLab) is an example project
used to exercise MedHarness end to end.

## Documentation

| | |
|---|---|
| [adopting.md](docs/adopting.md) | starting fresh or bringing an existing DHF |
| [ci.md](docs/ci.md) | the CI recipe, cutting and signing a release |
| [ai-workflow.md](docs/ai-workflow.md) | a change request from design to code |
| [agents.md](docs/agents.md) | working with your coding agent |
| [soup.md](docs/soup.md) | the SOUP register, SBOM, vulnerability scanning |
| [configuration.md](docs/configuration.md) | changing the defaults |
| [interface.md](docs/interface.md) | what a script or pipeline can rely on |
| [validation.md](docs/validation.md) | the tool's own validation |
| [ai-security.md](docs/ai-security.md) | what the AI stages can do |
| [architecture.md](docs/architecture.md) | how the code is organised |
| [charter.md](docs/charter.md) | what it is for, and what it does not do |
| [CHANGELOG.md](CHANGELOG.md) | version history |

## License

MIT. See [LICENSE](LICENSE).
