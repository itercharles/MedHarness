# Working with your coding agent

MedHarness does not replace the agent that writes your code. The agent explores, designs and implements;
MedHarness keeps the record and judges it, with ordinary code and not a model. This page is about the
seam between them, and is written for [Claude Code](https://code.claude.com/docs); another agent that
reads `AGENTS.md` and runs shell commands gets the first two sections as they stand.

## Three layers

| Layer | What it is | Holds the agent to it? |
|-------|-----------|------------------------|
| Advice | `AGENTS.md`, `CLAUDE.md`, a skill: what to do and in what order | No. The agent can forget or skip it |
| Local feedback | A hook in the agent that runs a MedHarness check and sends the result back | Only while the hook is installed. Whoever owns the machine can remove it |
| Enforcement | `verify` in CI, and branch protection that needs a person's review | Yes. A pull request cannot edit the check away |

Only the last layer is a control. The first two make the agent right earlier and cheaper, so CI rarely has to
say no.

## Local by default

Every command changes local files and commits nothing; `build plan|code --pr N` is what reaches a pull request.
An agent follows the same line: it designs and builds in the working tree, and starts a CI pipeline (an issue, a
milestone, a workflow run, a push) only when the person asks for it. Say so in the project's `CLAUDE.md` when a
pipeline exists, since "follow the project's process" can mean either.

## What to call, and when

Every command writes JSON to stdout, a human summary to stderr, and exits non-zero when it found something
wrong, so an agent, a script and a hook all use them the same way. `--dhf PATH` goes before the command.

| When | Command | A non-zero exit means |
|------|---------|-----------------------|
| A change begins | `medharness item create --type CR --data '{"title": "…", "description": "…"}'` | The CR was refused; the message names the field |
| Designing it | `medharness build plan --cr CR-NNN --prompt` | The CR is not in the DHF, or its type lacks a field the stage records |
| After any DHF edit | `medharness verify dhf` | A broken record: schema, links, cycles; under `--strict` also uncovered items |
| After designing it | `medharness verify impact --cr CR-NNN` | The CR's record of its impact is incomplete or unevidenced, or leaves an item the change reaches unsettled |
| Building it | `medharness build code --cr CR-NNN --prompt` | The CR has no `implementation_notes` to implement |
| After the code | `medharness verify changes --cr CR-NNN --code-path src/` | The branch did not change what the CR promised, or changed more than it lists |
| Before closing | `medharness verify completion --cr CR-NNN --junit test-results` | The CR's record is incomplete, or an item it affects has no passing test |

`item create|update --data` takes the JSON inline, from a file (`--data @fields.json`) or from standard input
(`--data -`); use a file for anything long, such as a CR's `impact_analysis`.

Signing a release is a person's. `item approve --release` shows the signer the changes and asks them to confirm, so an agent prepares the release (`build release --write`) and stops there; see [Signing a release](ci.md#signing-a-release).

`--prompt` prints the stage's steps and this CR's DHF context as Markdown, and starts no model: the agent that
is already running does the work.

## In Claude Code

### Advice: `CLAUDE.md` and a skill

`medharness init` writes `AGENTS.md` and a `CLAUDE.md` that imports it, so Claude Code already knows the
steps. For the same steps as a skill that loads when a request matches it, and that you can run as
`/medharness`, put [the skill](skills/medharness/SKILL.md) in your repository and commit it:

```bash
mkdir -p .claude/skills/medharness
curl -fsSL https://raw.githubusercontent.com/itercharles/MedHarness/main/docs/skills/medharness/SKILL.md \
  -o .claude/skills/medharness/SKILL.md
```

Anyone who clones the project gets it. Read it first, and edit it to your process.

### Local feedback: two hooks

Claude Code runs a command at fixed points and lets it stop the agent
([hooks reference](https://code.claude.com/docs/en/hooks)). Two are worth having. Put them in the project's
`.claude/settings.json` so the team shares them; they need `jq`.

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/medharness-stop.sh" }] }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/medharness-no-hand-edits.sh" }]
      }
    ]
  }
}
```

**Do not end a turn on a broken DHF.** When the agent is about to stop and the DHF has uncommitted changes,
run `verify dhf`; if it fails, stop the agent from finishing and hand it the findings. `stop_hook_active` is
true when the agent is already continuing because of this hook, which is what keeps it from looping on a
failure it cannot fix:

```bash
#!/usr/bin/env bash
# .claude/hooks/medharness-stop.sh
[ "$(jq -r '.stop_hook_active' )" = "true" ] && exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
[ -x .venv/bin/medharness ] && PATH="$PWD/.venv/bin:$PATH"
[ -z "$(git status --porcelain -- DHF/items)" ] && exit 0
findings=$(medharness --dhf DHF verify dhf 2>&1 >/dev/null) && exit 0
echo "$findings" | grep -A1 '^FAIL' >&2 || echo "$findings" >&2
exit 2
```

**Keep the agent to `medharness item`.** `item` checks the schema before it writes; a hand edit does not. Refuse an
edit to a file under `DHF/items/` and say what to do instead:

```bash
#!/usr/bin/env bash
# .claude/hooks/medharness-no-hand-edits.sh
case "$(jq -r '.tool_input.file_path // empty')" in
  */DHF/items/*) echo "Change DHF items with medharness item create|update, not by editing the file." >&2; exit 2 ;;
esac
```

The script runs the project's own `medharness` (`.venv/bin/medharness`) when there is one, and otherwise the first on
`PATH`: an older `medharness` on `PATH` cannot read a current DHF, and blaming a good DHF is worse than no hook. It
looks only at `DHF/items`, so a generated file elsewhere under `DHF/` (an SBOM) does not wake it.

Exit code 2 is the one that blocks; any other non-zero code only shows a notice and lets the action through.
Make both scripts executable (`chmod +x .claude/hooks/*.sh`).

Hooks are not a control: the agent works in your checkout, and anyone can edit `.claude/settings.json`. What the
hooks save is a round trip to CI.

## Other agents

Hooks and skills are written differently by every agent, and MedHarness does not generate them. What carries
over is the table above: any hook, script or plugin that runs those commands and acts on the exit code gets the
same behaviour.
