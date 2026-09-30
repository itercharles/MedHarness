# AI Execution Model

> **Stability:** Stable
> **Last reviewed:** 2026-09-30

This document describes what the AI stages of MedHarness are allowed to do, where they run, and what evidence they leave behind. It exists because MedHarness is used in regulated environments where "an AI wrote this code" is not an acceptable answer to an auditor — the boundary has to be stated, not assumed.

If you are evaluating MedHarness for a design-controlled project, read this before enabling `build plan` or `build code`.

---

## Scope: which commands invoke an LLM

Only two commands send anything to a model:

| Command | Stage | What it produces |
|---------|-------|------------------|
| `medharness build plan --cr <ID>` | Design | DHF item updates, impact analysis, design review |
| `medharness build code --cr <ID>` | Develop | Source code and tests for the approved design |

**Every other command is deterministic** and makes no call to any model. The `item` commands, the `verify` gates, `build soup` and `build release` compute their answers from their inputs; the only network they touch is osv.dev for `verify soup`.

This split is intentional: you can adopt the traceability engine and CI gates with no AI in the pipeline at all. See [adopting.md](adopting.md#what-to-adopt-in-what-order).

---

## The AI runs with full local privileges

Both AI stages execute an **agentic loop with an unrestricted shell tool**. The model can read, write, and delete any file the invoking user can, and can run any command that user can run.

Concretely:

**Anthropic path (default)** — [`cr_generation.py`](../medharness/services/cr_generation.py) shells out to the separately-installed `claude` CLI:

```python
cmd = ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "json"]
```

`--dangerously-skip-permissions` disables Claude Code's interactive per-action approval prompts. This is deliberate — the stages are designed to run unattended in CI, where there is no human at a terminal to answer prompts. It also means **there is no per-action gate between the model and your filesystem.**

**OpenAI-compatible path** — when `MEDHARNESS_*_MODEL` names an `openai:` or `deepseek:` model, MedHarness runs its own loop exposing a single `bash` function tool:

```python
proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
```

Bounded only by `max_turns=100` and a 120-second per-command timeout.

### What this means

- **Do not run AI stages against a workstation holding credentials you would not give a contractor.** The model can read `~/.aws`, `~/.ssh`, `.env`, and your git credentials, and can exfiltrate them through any command that reaches the network.
- **Do not point AI stages at a production or validated environment.**
- **Treat the CR prompt and DHF content as an injection surface.** The model acts on text from your DHF items and, when `--pr` is used, from PR comments. A CR description or review comment authored by an untrusted party is untrusted input to a shell-capable agent.

---

## Recommended isolation

Run the AI stages in a disposable, credential-minimal environment. A GitHub-hosted Actions runner satisfies this: ephemeral, separate from your internal systems, and scoped to a single repository token. The shipped CI recipe runs neither stage; [adopting.md](adopting.md#wiring-it-into-github-actions) sketches a workflow that does.

| Control | Recommendation |
|---------|----------------|
| Execution host | Ephemeral CI runner or container, destroyed after the job |
| Repository token | Least-privilege, single-repo, no org-wide access |
| Model credentials | CI secrets, never committed; rotate independently of developer keys |
| Network egress | Restrict to the model endpoint and your package registry where your runner supports it |
| Source of truth | The AI writes to a branch; `main` stays protected and requires review |

Locally, do not start the stages at all: `build plan --prompt` and `build code --prompt` hand the steps to the agent you are already using, under that agent's own permission prompts. No second agent runs, and nothing skips a confirmation.

---

## Human control points

The AI cannot advance a change on its own. Every stage transition is gated:

1. **`build plan` produces a design PR.** No code is written. A human reviews the DHF diff and the generated design review.
2. **Approval is evidence.** Branch protection with required approvals and stale approvals dismissed on push makes GitHub refuse a merge without an approving review of the commit being merged — author, timestamp and revision, all recorded outside this tool's control. A label is not accepted: anyone with write access can add or remove one, and it says nothing about what was reviewed.
3. **`build code` produces a code PR.** Start it only once the design PR is approved: your workflow decides when it runs, and `build code` itself refuses only a CR that is `completed`, `rejected` or `cancelled`.
4. **Closure is gated deterministically.** `verify completion` requires the CR's recorded fields, every item in its `affected_items` to exist, and passing JUnit evidence for each of those declaring `Test` — none of which the AI can satisfy by assertion.

The gates in step 4 are ordinary code. They do not ask a model whether the work is done.

---

## Audit trail

| Artifact | Where it lives | Contains |
|----------|----------------|----------|
| Session ID | A marker comment on the PR, captured from the `claude` CLI JSON envelope | Correlates a CR stage to a model session, so `--pr` resumes it |
| DHF item history | Git — the commit on the CR branch that carried the change, authored by whoever made it | Every design input the AI added or modified |
| PR diff | GitHub | Every line of code the AI wrote, under normal review |
| Design review | `docs/reviews/<CR>-Design-Review.md` | Verdict and open issues, written by `build plan` |
| Release evidence | `medharness build release` output | Specifications, traceability, test evidence and a hashed manifest, per release |

The model is never the record. Git is the record, and every AI action lands as a reviewable commit attributed to the CR.

---

## Regulatory positioning

MedHarness treats the AI as a **tool operated under design control**, not as a validated component of your device. The generated output is a design input proposal and a code proposal; the controls that make it acceptable are the review and verification gates around it, which are deterministic and testable.

Under IEC 62304, this places the AI stages in your **software development process** rather than in the device software itself. Your `verify` gates and review records are the process evidence. If your quality system requires tool validation for development tools, the deterministic commands (`item`, `verify *`, `build soup`, `build release`) are the ones with defined inputs and outputs suitable for that exercise — the AI stages are not, and should not be relied on as a validated transformation.

Nothing here is regulatory advice. How you classify and justify AI-assisted development in your QMS is your organisation's decision.

---

## Disabling AI entirely

Never invoke `build plan` or `build code` — the shipped CI recipe runs neither. Everything else keeps working:

```bash
medharness --dhf DHF verify dhf
medharness --dhf DHF verify tests --junit test-results
medharness --dhf DHF verify soup
medharness --dhf DHF build release --version 1.0.0 --out-dir release
```

No model credentials, no `claude` CLI, no network calls to any model provider.
