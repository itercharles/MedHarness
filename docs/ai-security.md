# AI Execution Model

> **Stability:** Stable
> **Last reviewed:** 2026-08-18

This document describes what the AI stages of MedHarness are allowed to do, where they run, and what evidence they leave behind. It exists because MedHarness is used in regulated environments where "an AI wrote this code" is not an acceptable answer to an auditor — the boundary has to be stated, not assumed.

If you are evaluating MedHarness for a design-controlled project, read this before enabling `change plan` or `change implement`.

---

## Scope: which commands invoke an LLM

Only two commands send anything to a model:

| Command | Stage | What it produces |
|---------|-------|------------------|
| `medharness change plan --cr <ID>` | Design | DHF item updates, impact analysis, design review |
| `medharness change implement --cr <ID>` | Develop | Source code and tests for the approved design |

**Every other command is deterministic.** `dhfkit` (item CRUD, validation, traceability, document generation, SOUP sync, release baseline) makes no network calls to any model and has no dependency on `medharness`. All `verify` gates, `evidence bundle`, and `approval` commands are pure local computation.

This split is intentional: you can adopt the traceability engine and CI gates with no AI in the pipeline at all. See [adopting.md](adopting.md#incremental-adoption).

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

Run the AI stages in a disposable, credential-minimal environment. The scaffolded workflow (`.github/workflows/dhf.yml`) already targets a GitHub Actions runner, which satisfies this: ephemeral, network-isolated from your internal systems, and scoped to a single repository token.

| Control | Recommendation |
|---------|----------------|
| Execution host | Ephemeral CI runner or container, destroyed after the job |
| Repository token | Least-privilege, single-repo, no org-wide access |
| Model credentials | CI secrets, never committed; rotate independently of developer keys |
| Network egress | Restrict to the model endpoint and your package registry where your runner supports it |
| Source of truth | The AI writes to a branch; `main` stays protected and requires review |

If you must run locally, use a dedicated checkout and a shell without your primary credentials in scope.

---

## Human control points

The AI cannot advance a change on its own. Every stage transition is gated:

1. **`change plan` produces a design PR.** No code is written. A human reviews the DHF diff and the generated design review.
2. **Approval is explicit.** `medharness approval check` requires a stage label plus a maintainer `/approve` comment before `change advance` will move the CR to `develop`.
3. **`change implement` produces a code PR.** It cannot run until the design stage is approved.
4. **Closure is gated deterministically.** `verify completion` requires an approved design review file, populated CR fields, and passing JUnit evidence for every requirement — none of which the AI can satisfy by assertion.

The gates in step 4 are ordinary code. They do not ask a model whether the work is done.

---

## Audit trail

| Artifact | Where it lives | Contains |
|----------|----------------|----------|
| Session ID | CR item, captured from the `claude` CLI JSON envelope | Correlates a CR stage to a model session |
| DHF item history | Git, one commit per change with author and CR ID | Every design input the AI added or modified |
| PR diff | GitHub | Every line of code the AI wrote, under normal review |
| Design review | `docs/reviews/<CR>-Design-Review.md` | Verdict and open issues, required by `verify completion` |
| Evidence bundle | `medharness evidence bundle` output | Test results and traceability state at merge |

The model is never the record. Git is the record, and every AI action lands as a reviewable commit attributed to the CR.

---

## Regulatory positioning

MedHarness treats the AI as a **tool operated under design control**, not as a validated component of your device. The generated output is a design input proposal and a code proposal; the controls that make it acceptable are the review and verification gates around it, which are deterministic and testable.

Under IEC 62304, this places the AI stages in your **software development process** rather than in the device software itself. Your `verify` gates and review records are the process evidence. If your quality system requires tool validation for development tools, the deterministic commands (`dhfkit`, `verify *`, `evidence bundle`) are the ones with defined inputs and outputs suitable for that exercise — the AI stages are not, and should not be relied on as a validated transformation.

Nothing here is regulatory advice. How you classify and justify AI-assisted development in your QMS is your organisation's decision.

---

## Disabling AI entirely

Remove the AI stage jobs from `.github/workflows/dhf.yml` and never invoke `change plan` / `change implement`. Everything else keeps working:

```bash
dhfkit --dhf DHF validate traceability
medharness --dhf DHF verify dhf
medharness --dhf DHF verify tests --junit-dir test-results
medharness --dhf DHF verify soup
medharness --dhf DHF evidence bundle --out-dir artifacts
```

No model credentials, no `claude` CLI, no network calls to any model provider.
