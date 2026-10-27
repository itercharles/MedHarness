# AI Execution Model

> **Stability:** Stable
> **Last reviewed:** 2026-10-23

This document describes what the AI stages of MedHarness are allowed to do, where they run, and what evidence they leave behind. It exists because MedHarness is used in regulated environments where "an AI wrote this code" is not an acceptable answer to an auditor — the boundary has to be stated, not assumed.

If you are evaluating MedHarness for a design-controlled project, read this before enabling `build plan` or `build code`.

---

## Scope: which commands invoke an LLM

Only two commands send anything to a model:

| Command | Stage | What it produces |
|---------|-------|------------------|
| `medharness build plan --cr <ID>` | Design | DHF item updates, impact analysis, design review |
| `medharness build code --cr <ID>` | Develop | Source code and tests for the approved design |

**Every other command is deterministic** and makes no call to any model. The `item` commands, the `verify` gates, `build soup`, `build release`, `build approvals` and `build validation` compute their answers from their inputs; the only network they touch is osv.dev for `verify soup`.

This split is intentional: you can adopt the traceability engine and CI gates with no AI in the pipeline at all. See [adopting.md](adopting.md#what-to-adopt-in-what-order).

---

## The AI runs with full local privileges

Both AI stages execute an **agentic loop with an unrestricted shell tool**. The model can read, write, and delete any file the invoking user can, and can run any command that user can run.

Concretely:

**Anthropic path (default)** — [`llm.py`](../medharness/services/llm.py) shells out to the separately-installed `claude` CLI, passing the prompt on stdin:

```python
cmd = ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "json"]
# plus --model <model> and --resume <session> when set
```

`--dangerously-skip-permissions` disables Claude Code's interactive per-action approval prompts. This is deliberate — the stages are designed to run unattended in CI, where there is no human at a terminal to answer prompts. It also means **there is no per-action gate between the model and your filesystem.**

**OpenAI-compatible path** — when `MEDHARNESS_*_MODEL` names any provider other than `anthropic` (`openai:`, `deepseek:`, or a local endpoint such as `ollama:`), MedHarness runs its own loop exposing a single `bash` function tool:

```python
proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
```

Bounded only by `max_turns=100`, a 120-second per-command timeout, and 20,000 characters of output returned to the model per command.

### What this means

- **Do not run AI stages against a workstation holding credentials you would not give a contractor.** The model can read `~/.aws`, `~/.ssh`, `.env`, and your git credentials, and can exfiltrate them through any command that reaches the network.
- **Do not point AI stages at a production or validated environment.**
- **Treat the CR prompt and DHF content as an injection surface.** The model acts on text from your DHF items and, when `--pr` is used, from PR reviews. A CR description or review comment authored by an untrusted party is untrusted input to a shell-capable agent.

What the harness limits on its own:

- **PR reviews.** With `--pr`, only reviews by an owner, member or collaborator of the repository reach the agent; any other review is left out and the run warns `untrusted_reviews_ignored`.
- **The agent's environment.** `GH_TOKEN`, `GITHUB_TOKEN`, `OPENAI_API_KEY` and `DEEPSEEK_API_KEY` are removed from the environment of the `claude` CLI and of the OpenAI-compatible loop's shell. The harness pushes, comments and calls the endpoint itself; the agent needs none of them. The model's own credentials (for `claude`, `ANTHROPIC_API_KEY` or its OAuth token) stay, since the CLI needs them.
- **Time.** A single model call is stopped after `MEDHARNESS_MODEL_TIMEOUT` seconds (default 7200). If the first, generating call fails, the stage stops there: no fix pass or review runs on nothing, and nothing is pushed.
- **Scope of `build plan`.** A design run that writes anything other than DHF items and its review file fails with a `scope` error naming the files, and nothing is pushed.

---

## Recommended isolation

Run the AI stages in a disposable, credential-minimal environment. A GitHub-hosted Actions runner satisfies this: ephemeral, separate from your internal systems, and scoped to a single repository token. The shipped CI recipe runs neither stage; [the AI workflow page](ai-workflow.md#wiring-it-into-github-actions) sketches a workflow that does.

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
2. **Approval is a person's, twice.** During development it is the review of the pull request: branch protection with required approvals and stale approvals dismissed on push makes GitHub refuse a merge without an approving review of the commit being merged. That is the team's rule, kept by GitHub; MedHarness neither reads nor exports it, and it is not the compliance record. At release each specification is signed by the role that owns it (`item approve --release`), and `verify approval --release` checks the signatures against `DHF/config/approvers.yaml` from the files in the repository. A label or a field is not accepted: anyone with write access, an agent included, can write one, and it says nothing about who reviewed what. A signature needs a key on the approvers list; the intended key is a hardware key that needs a touch, and until a touch is proven from the signature, a key marked `no_touch_required` is reported as made without proven presence.
3. **`build code` produces a code PR.** Start it only once the design PR is approved: your workflow decides when it runs, and `build code` itself needs only a CR that carries `implementation_notes`.
4. **Closure is gated deterministically.** `verify completion` requires the CR's recorded fields, every item in its `affected_items` to exist, and passing JUnit evidence for each of those declaring `Test` — none of which the AI can satisfy by assertion.

The gates in step 4 are ordinary code. They do not ask a model whether the work is done.

---

## Audit trail

| Artifact | Where it lives | Contains |
|----------|----------------|----------|
| Session ID | A marker comment on the PR, captured from the `claude` CLI JSON envelope | Correlates a CR stage to a model session, so `--pr` resumes it |
| DHF item history | Git — the commit on the CR branch that carried the change, authored by whoever made it | Every design input the AI added or modified |
| PR diff | GitHub | Every line of code the AI wrote, under normal review |
| Design review | `docs/reviews/<CR>-Design-Review.md` | The model's own notes on its design — verdict and open issues, written by `build plan`. It is not a review record: the review is the person's, in the pull request |
| Release evidence | `medharness build release` output | Specifications, traceability, test evidence and a hashed manifest, per release |
| Release manifest and change report | `DHF/releases/<version>/manifest.yaml` and `changes.md`, in Git | The item hashes each specification consists of, the approvers list the release pins, and what changed in each document since the previous release — what a signer reviews |
| Approval log | `DHF/approvals/release-<version>/`, in Git | One signed record per signer per release: signer, roles, time, statement, the documents and hashes signed, and the key's fingerprint, with the signature beside it. Append-only; the only evidence of an approval |
| Approval sheet | `medharness build approvals` output | Who approved which document of a release, presented from the log. The records stay the evidence |

The model is never the record. Git is the record, and every AI action lands as a reviewable commit attributed to the CR.

---

## Regulatory positioning

MedHarness treats the AI as a **tool operated under design control**, not as a validated component of your device. The generated output is a design input proposal and a code proposal; the controls that make it acceptable are the review and verification gates around it, which are deterministic and testable.

Under IEC 62304, this places the AI stages in your **software development process** rather than in the device software itself. Your `verify` gates, your pull-request reviews and the signed release approvals are the process evidence. If your quality system requires tool validation for development tools, the deterministic commands (`item`, `verify *`, `build soup`, `build release`, `build approvals`) are the ones with defined inputs and outputs suitable for that exercise — the AI stages are not, and should not be relied on as a validated transformation.

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
