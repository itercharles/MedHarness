# Adopting MedHarness

How to take MedHarness into a project, and where each part is documented.

| You want to | Read |
|---|---|
| Add the CI gates, or cut a release | [CI and releases](ci.md) |
| Let an agent plan and write a change, with your own agent or unattended in CI | [The AI-assisted CR workflow](ai-workflow.md) |
| Keep the SOUP register, an SBOM and vulnerability checks | [SOUP, SBOM and vulnerabilities](soup.md) |
| Change a default, or add a type or a relationship | [Configuration](configuration.md) |
| Know how far to trust the checks, and what a reviewer still reads | [How far to trust the checks](trust.md) |
| Look up a command, its options or its answer | [interface.md](interface.md) |

## Starting fresh

Run `medharness init` as in the [README](../README.md#quick-start), then replace:

| Replace | Why |
|---------|-----|
| `DHF/items/` | The sample items. Delete them and add your own, or keep them while you learn the schema |
| `DHF/config/global.yaml` | Check the project name. Anything else you set here overrides a default ([Configuration](configuration.md#changing-the-defaults)) |
| `AGENTS.md` | Describe the product, so every coding agent, and the AI stages, reason about your domain |

CI is the one piece you add yourself ([CI and releases](ci.md#setting-up-ci)).

## Bringing an existing DHF

One YAML file per item; the types and links are listed in the `DHF/README.md` that `init` writes. A requirements spreadsheet becomes SYS and SRS items, one row per item. A risk register becomes RISK items with RCM items that `mitigates` them. A SOUP list becomes SOUP items. Test code stays in pytest, and generated documents come from `build release`.

Run `medharness --dhf DHF verify dhf` as you go: it names the item, field and target of every broken link. While backfilling, leave `--strict` off, so coverage gaps warn and only schema, required links and dangling links fail ([what blocks a build](interface.md#what-blocks-a-build)).

### Change requests you already have

Settle two things once, before the first release.

**A status that is no state of the type.** A CR written as `implementing` fails `verify dhf`. Set each to what it is: `develop` for work in flight, `completed` or `cancelled` for work that finished or stopped.

```bash
medharness --dhf DHF item update CR-004 --data '{"status": "develop"}'
```

**Completed CRs that never recorded their closure.** `build release` asks every completed CR it includes for what closing one asks. Do not backfill those fields: a triage approval written years later records nothing. Baseline the history instead. A REL item listing those CRs in `included_items` takes them out of the default, as a reviewable change:

```bash
medharness --dhf DHF item create --type REL --data '{"title": "Baseline of change requests completed before closure records", "version": "baseline", "included_items": ["CR-003", "CR-005"], "release_notes": "Completed before the closure criteria existed; accepted as they are."}'
```

## Test points

A requirement's `testing` field holds numbered test points, written at design time:

```yaml
id: SRS-012
title: "Password must be at least 12 characters"
content: "The system shall reject passwords shorter than 12 characters."
testing: |
  T1: Given a password of 11 characters, registration returns a validation error.
  T2: Given a password of exactly 12 characters, registration succeeds.
```

Tests declare what they cover:

```python
@pytest.mark.dhf_links("SRS-012")
@pytest.mark.dhf_testing("T1", "T2")
def test_password_length_validation(): ...
```

```javascript
test("rejects short password @links:SRS-012 @testing:T1", () => { ... });
```

Under pytest with `--junit-xml` the markers become JUnit properties; other runners carry the tags in the test name. `medharness --dhf DHF verify tests --junit test-results` fails when a requirement, or a declared test point, has no covering test.

## What to adopt, in what order

Start with the AI development, and add the checks that make it trustworthy. Each step is useful on its own.

| Step | Add | Needs |
|------|-----|-------|
| 1 | Your coding agent follows the process: `init` writes `AGENTS.md`, and the agent runs `build plan --prompt` and `build code --prompt` | A coding agent you already use. No key, nothing in CI |
| 2 | `verify dhf` as a PR gate | Nothing. It checks the design the agent wrote |
| 3 | `verify impact` and `verify tests --cr` on change-request branches (the recipe's `change-check` job) | Test annotations in JUnit output |
| 4 | Unattended AI in CI: `build plan` and `build code` from an issue | An AI key, an ephemeral runner, and branch protection that requires an approving review. Put it behind step 2 |
| 5 | `build soup`, `verify soup` | A dependency manifest |
| 6 | `build release` on version tags | Steps 2, 3 and 5 passing |

A team that writes its DHF by hand starts at step 2 and loses nothing the standard asks for.

## Validating your installation

Every release runs its full test suite against the dependency versions in its lockfile, and attaches the evidence to the GitHub Release: `medharness-<version>-tested-with.txt` (a pip constraints file), `-junit.xml` and `-test-summary.txt`. To install that configuration:

```bash
pip install "medharness[docs]==<version>" -c medharness-<version>-tested-with.txt
```

That shows the suite passed where MedHarness was built. To show your copy behaves the same in your environment:

```bash
medharness build validation --out-dir validation
```

It runs the validation set that ships in the package against a scratch project, never your DHF, and writes `validation/validation-report.html` (`--doc-format pdf` with the `docs` extra). The report gives `passed`, `failed` or `incomplete`; the installed files checked against the release; each dependency beside its tested version; your platform; and, for each high-risk requirement of MedHarness's own DHF, every test point and its result. It ends with blank fields for who performed and reviewed it. The command exits 0 only on `passed`, and takes about half a minute on four cores (`--jobs N`).

- **A dependency at another version** is a deviation, not a failure. Whether it matters is your assessment.
- **A missing `ssh-keygen`** leaves the signing points not run, so the result is `incomplete`.
- **An install from a source checkout or in editable mode** cannot be checked file by file, so it is `incomplete`. Validate the wheel you install from PyPI.

Run it on the CI runner that runs your gates and `build release`, and where people sign releases. Run it when you adopt a version, after every upgrade, and when the environment changes (operating system, Python). File the report with the release's JUnit and test summary. Deciding that MedHarness is fit for your intended use, and signing, are yours ([ADR-005](adr/ADR-005-installation-validation.md)).
