# Changelog

All notable changes to MedHarness are documented in this file.

MedHarness follows [Semantic Versioning](https://semver.org/):
- **MAJOR** — breaking changes to CLI, templates, scaffold output, or public API
- **MINOR** — backward-compatible new features
- **PATCH** — bug fixes, doc corrections, non-behavioral internal changes

---

## [Unreleased]

---

## [0.16.0] — 2026-09-03

### New Features

- **`required_test_levels` can differ by requirement type.** §5.5 unit
  verification, §5.6 integration testing and §5.7 system testing do not verify
  the same artefact, but the setting was a single list applied to every
  requirement — so a project could demand all three levels of every requirement
  or none of any:

  ```yaml
  required_test_levels:
    SRS: [unit, integration]     # §5.5, §5.6
    SYS: [system]                # §5.7
  ```

  A list still applies to every type, so an existing activity map behaves
  exactly as it did. A type the mapping omits requires no level — silence is
  "not required here", not "inherit the others".

  `safety_activities.yaml` is documented as the project's own interpretation of
  the §5 activity table. Until now it could not hold one: the reference project
  wanted integration evidence for SRS and system evidence for SYS, and the only
  available edit was to drop a level for everything at once.

  The shipped defaults are unchanged. Which clause verifies which artefact
  depends on how a project defines SYS against SRS, and that is not a judgement
  this project should make on anyone's behalf.

  `details.required_levels` is now a `{type: [levels]}` mapping rather than a
  list, and stderr prints one line per type when they differ. `details` is
  documented as gate-specific and unstable; nothing in the envelope changed.

### Bug Fixes

- **A review-file naming mismatch was invisible from both ends.** `approval
  import` globbed `*-Review.md`, so a project whose files are named
  `CR-013-Design.md` saw `0 imported, 0 skipped` with nothing in `errors` — the
  files were never looked at. `verify completion` then failed with "no approval
  record" and nothing connected the two. Every `.md` in the directory is now
  read, and one the importer cannot parse is reported with the pattern it
  expected. `--help` names that pattern too.

- **The verification-level fix hint assumed pytest.** It read
  `Fix: mark a covering test with @pytest.mark.dhf_level("integration")`. The
  gate consumes JUnit XML precisely so it works for any runner; a project whose
  tests are Vitest was sent looking for a decorator that cannot exist in a
  TypeScript file. The hint now leads with the `medharness.level` JUnit property
  and mentions the pytest mark as one way to set it.

## [0.15.0] — 2026-09-02

### Behaviour changes

- **`verify classification` now fails when a declared class has no activity map.**
  It previously warned and exited zero, summarising "all required activities
  present" while checking nothing. Declaring the class is taking the opt-in, so
  a gate that then cannot check anything has to say so in a way CI cannot
  ignore.

  **What breaks:** a project that declared `software_safety_class` but has no
  `DHF/config/safety_activities.yaml` goes from green to red on this gate. That
  is the state `medharness upgrade` used to leave projects in — run
  `medharness upgrade --apply` to obtain the file, then edit it to match what
  your project has agreed. This is why the release is a minor rather than a
  patch.

### Bug Fixes

- **`medharness upgrade` never delivered three scaffold files.** `_UPGRADE_MAP`
  is hand-written, and `config/doc_types/apr.yaml`, `config/safety_activities.yaml`
  and `config/soup-sources.yaml` were absent from it — so a project that adopted
  MedHarness before those files existed never received them, while `upgrade`
  reported everything up to date.

  `apr.yaml` was the hard failure: without the doc type, `dhfkit item create
  --type APR` exits with "Unknown doc type", so the approval records
  `verify completion` requires could not be created at all. Every one of the
  twelve sibling doc types was listed; this one was missed and nothing said so.

  `safety_activities.yaml` failed quietly instead: the gates that depend on it
  ran and passed. See **Behaviour changes** above.

- **`verify dhf`'s verification_criteria warning read as a bug in the gate.** It
  said only "missing verification_criteria" while `dhfkit validate schema`
  passed, so a reader concluded the gate was warning about a field the schema
  never defined. The field *is* defined on CRS/SYS/SRS and is optional; the
  warning now says so and gives the command to fill it.

- **Files the project owns are seeded, not overwritten.** `safety_activities.yaml`
  and `soup-sources.yaml` are created when absent and left alone thereafter —
  managing them like templates would report an edited copy as outdated and
  replace a project's agreed scope on `--apply`.

  `tests/unit/test_upgrade_map_covers_scaffold.py` asserts every file `init`
  writes is claimed by exactly one category, so a template added later cannot
  be forgotten silently. Verified by removing each of the three entries.

### Internal

- **Mocks are now checked against the functions they stand in for.** A mock is a
  claim about what a service returns, and nothing failed when the claim stopped
  being true: the test kept feeding the CLI a shape production no longer
  produced, the line stayed green in coverage, and only the real call path
  broke. That is how `verify branch` shipped a `TypeError` in 0.14.0 — its test
  mocked the service with dicts in `errors` while the service had moved to
  strings.

  `tests/unit/test_mock_contracts.py` compares every literal mock in the suite
  against the shape the real function returns, resolving re-exported patch
  targets and preferring a declared `-> tuple[...]` annotation over inference.
  A service that changes shape now fails there rather than in a pipeline.

  The audit that motivated it found **no stale mock today**: of 173 patch sites,
  most return scalars or empty lists that cannot carry a stale key, and every
  structured one currently matches. The gap was never a backlog of bad mocks —
  it was having nothing that notices when one goes bad.

## [0.14.0] — 2026-09-02

### Breaking Changes

- **Every gate now returns the same envelope.** The only key all gates shared
  was `passed` — five gates meant five shapes, and each new gate added another
  for callers to special-case. Gate-specific payload moves under `details`:

  ```json
  {
    "gate": "verify plans",
    "passed": false,
    "summary": "Class B: 1 plan(s) written, 0 missing, 3 unchanged.",
    "errors": ["development_plan.md is unchanged from the template ..."],
    "warnings": ["integration_plan.md: 6 section(s) still match ..."],
    "details": { "declared": "B", "checked": [...], "unwritten": [...] }
  }
  ```

  A CI script or an agent parses this once and handles any gate, including ones
  that do not exist yet. `errors` are what made the gate fail; `warnings` are
  what it noticed without failing — both plain strings, already phrased for a
  reader, because the machine-readable form is in `details`.

  **What breaks:** anything reading a gate-specific key at the top level of the
  JSON. Exit codes, `passed`, and all stderr output are unchanged, so a pipeline
  that only checks exit status — which is how the reference project consumes
  them — is unaffected.

  `verify soup` no longer carries a private `error` key; an unreachable osv.dev
  appears in `errors`, or in `warnings` under `--offline-mode warn`, like any
  other finding.

### New Features

- **`medharness gates`** — the verification gates, described for whoever calls
  them. `--json` for an agent discovering what it can invoke; plain text for a
  person wiring a pipeline:

  ```
  verify soup  [network]
      SOUP items against the OSV vulnerability database, honouring documented
      per-CVE acceptances.
      clauses:  IEC 62304 §8.1.2
      requires: --dhf
      blocking: always
                An unreachable osv.dev fails by default; --offline-mode warn
                tolerates it for air-gapped runners.
  ```

  CI is deliberately not scaffolded — a pipeline carries a project's runner
  labels, secrets, and branch names, and a generated one would be wrong for most
  teams. That choice only holds up if the interface is described well enough to
  build against, which is what this is. The same manifest serves both readers.

  The registry is hand-written, because the facts that matter most — whether a
  gate blocks, reaches the network, or is inert until a safety class is declared
  — are not expressible as command metadata. A test asserts it against the live
  Click command tree, so it cannot drift.

### Bug Fixes

- **Two gates crashed on their failure path.** Moving gate payloads under
  `details` left several CLI reader sites unconverted: `verify plans` raised
  `KeyError: 'declared'` whenever a required plan was absent, and `verify branch`
  raised `TypeError` on every failure, because the envelope's `errors` are now
  strings while the loop still read `error['field']`.

- **Findings vanished from stderr.** `verify verification` read `missing_method`
  at the top level, so "no verification_method declared" lines were silently
  dropped; `verify branch`'s risk-impact warning became dead code; and
  `verify tests` always printed "seen in this evidence: none".

- **Three gates could fail while saying nothing.** `docs/interface.md` states
  that a failing gate always populates `errors`, and three paths did not: SOUP
  with real vulnerabilities, an explicit `--coverage-pair` failure, and a CR
  missing `proposed_new_items`. A `passed: false` with an empty `errors` is the
  defect the document names.

- **`verify tests` named the wrong cause.** A missing `--junit-dir` failed with
  "Test coverage gaps found." while the envelope correctly said "No JUnit files
  found". Every stderr detail loop in that command iterates `results`, which is
  empty on that path, so nothing but the generic exception text was printed.

- **`verify dhf` never showed its verification_criteria warnings.** They reached
  the envelope and the JSON; the command had no loop that rendered them, so a
  reader of CI logs never saw them.

- **`verify soup` printed every vulnerability twice.** `_render_envelope` and a
  manual loop beside it rendered the same findings. The envelope strings now
  carry severity and the URL fallback, and the manual loop is gone.

- **The branch gate's contract test asserted the superseded shape.** It mocked
  the service with a flat pre-envelope dict and asserted flat top-level keys —
  including `errors` as a list of dicts, which contradicts the documented string
  type. Removing the envelope from `verify branch` entirely left it passing.

  New guards: every envelope message must be findable on stderr, no gate may
  print a finding twice, and SOUP's rendering path is exercised with a stubbed
  osv.dev because the scaffold has nothing checkable to reach it. Each was
  verified by reintroducing the defect it was written for.

- **The interface document's sample manifest drifted from the real one.** The
  exit-code table was corrected while the sample JSON above it kept the
  superseded wording — the same defect class, in the same document, introduced
  by the fix for it. The guard compared only the table's codes; it now parses
  the sample and compares it to `gates_manifest()`.

- **The documented exit codes were wrong.** A usage error raised before a gate
  runs — a missing `--dhf`, for instance — exits **1** with no stdout, not 2. The
  document's own sample consumer would have raised `IndexError` on it. Both the
  document and the manifest now describe the three real cases, and the sample
  checks stdout before parsing.

- **Three gates were not answering with the envelope.** `verify verification`,
  `verify branch`, and `verify code` are implemented outside
  `services/ci.py`, and the discovery test added with the envelope enumerated
  functions named `*_gate` in that one module — so it never saw them. All nine
  now share the shape, and discovery walks the CLI command tree instead, which
  has no such blind spot.

- **`verify branch` put dicts in `errors`.** The envelope's messages are strings
  a caller can print; the structured findings now live in `details.findings`.
  Its `summary` was empty.

- **`verify verification` and `verify completion` failed while saying nothing.**
  Their findings sat in `details` but never reached `errors`, so a caller saw
  `passed: false` with no explanation. `verify completion` has four exit paths;
  an early one that skips later checks still has to say why it failed.

### Documentation

- **[docs/interface.md](docs/interface.md)** — the machine interface as a
  contract: the result envelope, exit-code semantics, what blocks a build, and a
  stability promise saying which fields a caller may rely on and which may
  change.

  Declining to scaffold CI is only defensible if the interface is described well
  enough to build against. This is the other half of that decision, and it
  serves the same two readers as `medharness gates` — a pipeline author and an
  agent.

  It states plainly what is *not* a contract: `details` varies per gate, and
  stderr is written for a person and must never be parsed.

  `tests/unit/test_interface_doc.py` checks the document against the
  implementation — envelope keys, exit codes, the blocking vocabulary, and that
  every opt-in gate is named. A document that drifts is worse than none, because
  it produces confident code resting on a promise nothing keeps.

### Internal

- **The envelope tests ran gates through `CliRunner`, which hid both crashes.**
  It captures an exception raised *after* the JSON line reaches stdout, so a
  command that prints its result and then dies looked identical to one that
  succeeded. They now run real subprocesses and assert no traceback.

- **They also only ever ran against a clean scaffold**, where soup short-circuits,
  plans skips everything, and branch has nothing to compare — so every defect
  above sat on a path the suite never reached. A deliberately broken DHF now
  exercises each gate's failure path.

- `tests/unit/test_gate_envelope.py` pins the contract, including a discovery
  test that enumerates the module rather than naming gates — a gate added
  without the envelope fails there rather than reaching a caller.

## [0.13.0] — 2026-08-23

Completeness gates. Every check before this release answered one shape of
question — *are these items consistent with each other?* None could answer
*is this DHF complete for the kind of software it describes, and did someone
approve it?* Five gates close that gap, keyed to the IEC 62304 safety class a
project declares.

**Adoption is opt-in.** A DHF with no declared `software_safety_class` sees
the new gates stay inactive, so nothing that passes today starts failing —
with one deliberate exception, called out under Behaviour changes.

This release also carries a large batch of correctness fixes found by four
review passes over the verification gates and the document pipeline. Several
of them concern the DHF misreporting itself, which for a tool whose output is
a compliance record is the defect class that matters most.

### New Features

- **Software safety classification (IEC 62304 §4.3).** The class a project
  declares decides which development activities the standard requires, and the
  DHF had no way to express it. `DHF/config/global.yaml` gains
  `software_safety_class` (A/B/C) and `classification_rationale`, and a new gate
  reports what the declared class demands:

  ```
  $ medharness --dhf DHF verify classification
  FAIL [classification] Class C requires SWDD items and the DHF has none (§5.4 detailed design).
  ```

  Until now every gate could prove that existing items were consistent with each
  other; none could ask whether the items a project is *required* to have exist.

  **Adoption is opt-in.** A DHF with no declared class warns and exits zero, so
  nothing that passes today starts failing.

- **The class-to-activity map is project-owned.** `config/safety_activities.yaml`
  ships with a documented default and is meant to be edited: assessors differ on
  how the §5 activity table reads, and a project's interpretation is part of its
  regulatory strategy rather than something the tool should decide. The file
  lives in the DHF, so the choice is recorded beside the evidence it governs.

- **Per-module classification (§4.3(b)).** MODULE items accept `safety_class`
  and `segregation_rationale`, for systems where a lower-class item is separated
  from higher-class ones. An override without a rationale is reported as a
  warning, not an error — the justification may legitimately live in the
  architecture.

- **Approval records are DHF items (IEC 62304 §5.1.1, 21 CFR 820.30(e)).** Who
  accepted a change, and against which state of the design, lived in a GitHub
  label and a `docs/reviews/*.md` file — outside the DHF, so absent from the
  traceability matrix, from evidence bundles, and from every gate. A new `APR`
  doc type makes the decision a first-class item.

  **The approved revision is deliberately not a field.** It is the commit that
  introduced the record. Writing it in would be circular — the SHA of the commit
  containing `APR-014` cannot appear inside `APR-014` — and would create a second
  source of truth a hand edit could make disagree with git:

  ```
  $ dhfkit --dhf DHF approval show APR-001
  APR-001 approved at 66136e7b (2026-08-23) by T
  ```

  `approver` is kept because git records who *wrote* the file, which in CI is a
  bot, and a bot cannot be accountable for a decision.

- **`approval act --cr --approver`** writes the decision into the DHF alongside
  the label and comment it already posts. Rejections are recorded too — a
  rejection is a decision that belongs in the account. A DHF write that fails is
  reported rather than unwinding a decision the PR has already made public.

- **`dhfkit approval import`** backfills records from the legacy review-file
  convention, mapping design reviews to the design stage and code reviews to
  develop. Safe to re-run.

- **`verify completion` checks the record, not a filename.** The file convention
  still works as a fallback so projects mid-flight are not stranded, but a DHF
  that has adopted approval items is judged on them — a stale review file can no
  longer approve a CR whose recorded verdict says otherwise.

- **Plan completeness (IEC 62304 §5.1).** The scaffold ships seven plans as
  templates and nothing verified any of them was ever filled in — a DHF of
  untouched placeholders passed every gate. `verify plans` checks the plans the
  declared safety class requires:

  ```
  PASS [plan] verification_plan.md
  FAIL [plan] development_plan.md: unchanged from the template (29 section(s))
  WARN [plan] integration_plan.md: 6 section(s) still match the shipped template
  SKIP [plan] maintenance_plan.md: not required for Class B
  ```

  **Detection compares against the template, not marker text.** Only
  `development_plan.md` carries a "starter content" banner; the other six read
  like finished plans, so a marker-based check would miss six of seven. Removing
  a banner is also not the same as writing a plan.

  Comparison is per section and starts at level-2 headings — a document's title
  block is its own front matter, so editing it cannot make an unwritten plan
  read as written.

  A plan whose every section still matches the template **fails**: §5.1 asks for
  a plan that is maintained, not one that was scaffolded. Individual unchanged
  sections **warn**, because a project may legitimately accept some shipped
  wording and the tool cannot tell that from neglect. No percentage threshold is
  involved.

  Inactive until a safety class is declared, like the rest of Phase 1's checks.

- **Verification levels (IEC 62304 §5.6, §5.7).** `verify tests` mapped JUnit
  results to requirements without regard for whether they came from unit,
  integration, or system testing — so a project running only unit tests showed
  every requirement `verified`, and the distinct integration and system testing
  records the standard asks for were invisible.

  Tests declare their level with a marker:

  ```python
  @pytest.mark.dhf_links("SRS-012")
  @pytest.mark.dhf_level("integration")
  def test_password_policy_enforced_end_to_end():
      ...
  ```

  It travels as the `medharness.level` JUnit property rather than being inferred
  from a directory, so a results file copied between CI jobs keeps saying what
  it is. A level the marker does not recognise raises rather than recording the
  wrong one silently.

  ```
  FAIL [test-level] SRS-012: verified at unit but missing integration, system
  ```

  **Unlabelled tests count as unit** — which is what they were already being
  counted as. Existing suites keep working, and the requirement only applies
  once a class demanding it is declared.

- **Known anomalies in the release record (IEC 62304 §9.7).** The REL item held
  `title · version · content · included_items · release_notes`, and nothing
  connected an unresolved defect to the release shipping with it. §9.7 does not
  forbid releasing with known anomalies — it requires that they be documented
  and assessed.

  `release-baseline` now collects DEF items still in `draft`, `open`, or
  `in_progress` into the REL item and the baseline artifact, each carrying the
  assessment that made it acceptable:

  ```yaml
  release_rationale: >
    Affects an export path unreachable in the released configuration —
    series over 900 slices are rejected at import. Assessed under RISK-001.
  ```

  The mechanism mirrors SOUP `accepted_vulns`: an assessment recorded against
  the specific finding, never a blanket suppression.

- **`dhfkit doc export --format html`** (now the default) renders a
  specification to a standalone HTML file with inlined CSS. No native libraries,
  so it works everywhere `medharness` installs — and the result can be committed,
  published, or handed to a reviewer without a viewer.

### Behaviour changes

- **An unresolved defect without a `release_rationale` blocks the baseline.**
  This is the one deliberate break in the gap-closure sequence. A release that
  ships with an unassessed anomaly is exactly what §9.7 exists to prevent, and
  the error names the defect and both ways out — assess it, or resolve it.

### Bug Fixes

- **`release-baseline` crashed on any scaffolded DHF.** It read `item["uid"]`
  while items expose `id`, and every scaffold ships a SOUP item — so the §9
  release baseline, a regulatory deliverable, raised `KeyError` on a default
  project.

  Its tests stayed green because their own helpers built `{"uid": …}` dicts,
  a shape neither `LocalDHFAdapter` nor the test stub produces. The fixture and
  the production code shared one wrong assumption and agreed with each other;
  only running against a real DHF disagreed. The `uid` key in the emitted
  artifact is unchanged, so existing consumers are unaffected.

- `GitRepository.get_file_history` truncated commit hashes to eight characters.
  An approval identifies the state it accepted by its commit, and a truncated
  hash is not an identifier an audit can rely on. Full hashes are now returned,
  with `short_sha` alongside for display.

- **Generated documents named the wrong project.** `ProjectConfig` did not
  declare `project_name`, and pydantic drops undeclared fields, so every
  specification rendered `| **Project** | DHF Project |` regardless of what
  `medharness init` had written into `global.yaml`.

- **Document versions still advanced once per day.** The previous fix compared
  renders with the `Version` and `Generated` metadata rows masked, but every
  spec template also prints the date in prose (`**Last Updated**: …`), so a
  regeneration on a later day still read as a content change. Comparison now
  re-renders using the existing document's own date, which is exact and does not
  depend on knowing where a template prints it. The earlier test could not catch
  this because all its generations ran within one second.

- **A running GitLab pipeline shadowed the finished one.** Dropping the
  `status=success` filter made failing runs fetchable, but also let a re-run
  still in flight — or a cancelled one — win the "newest pipeline" query and
  return zero artifacts. GitLab has no `completed` status to ask for, so a page
  is fetched and the newest terminal pipeline (`success` or `failed`) is taken,
  matching what GitHub's `status=completed` already did.

- **JUnit injection kept requirements verified by deleted tests.** The merge
  introduced in the previous release preserved *every* stored result, so
  removing a test left its requirement `verified` by a stale stored PASS. The
  merge now preserves only what a JUnit run cannot carry — manual review records
  — while ordinary automated results are superseded by the batch. This keeps the
  behaviour that merge was chosen for and drops the part that was never intended.

- `evidence bundle` wrote date-stamped HTML into `DHF/documents/exports/` with
  no `.gitignore` entry, so a merge-to-main CI run dirtied the tree and
  accumulated a fresh set daily.

- In the test specification template, `{{ status or 'NOT VERIFIED' | upper }}`
  binds as `status or ('NOT VERIFIED' | upper)`, so a set status rendered
  lowercase beside the badge that was just fixed to uppercase it.

- `gh api --slurp` requires gh 2.44. On an older CLI the paginated call failed
  outright, aborting CR intake where it previously succeeded with truncated
  input; it now falls back to a single page.

- **`medharness init` permanently corrupted the installed package.** The
  documented setup creates `.venv` inside the project, and
  `_replace_placeholders` walked the whole tree — so it rewrote
  `site-packages/dhfkit/templates` in place, substituting the first project's
  name into the shipped templates. Every later `init` from that virtualenv then
  scaffolded with the wrong project name, and `upgrade` compared against
  corrupted templates while reporting everything up to date. The walk now prunes
  environment directories, and an unreadable file is skipped rather than
  aborting the scaffold.

- **The scaffolded `.gitignore` excluded the result store.** The pattern
  `test-results/` matched `DHF/test-results/`, so `results.yaml` — which holds
  verification evidence, including the manual review records the previous
  release taught `evidence bundle` to preserve — was never committed. Now
  anchored as `/test-results/`, which still ignores transient local JUnit output
  at the project root.

- **The prefix fix in 0.12.x reached only half the callers.** `core.py` still
  derived prefixes with `split("-")[0]` in three places, so a doc type
  configuring a multi-segment prefix (code `VER`, prefix `VER-SW-`) never
  resolved and its items never received a `verification_status`. The previous
  changelog's "now consistent" claim was wrong.

- **Unknown coverage types are no longer fatal for the implicit defaults.**
  Making unknown types an error applied it to `DEFAULT_ACCEPTANCE_COVERAGE_PAIRS`
  as well, so a DHF that legitimately omits a V-model layer started failing the
  acceptance gate with no user change. Pairs the user supplies stay strict — a
  typo there is a real error; the implicit defaults now skip layers the project
  does not configure.

- **A rejected coverage pair printed as a coverage shortfall.** The explanatory
  `error` was returned in JSON but never written to stderr, so a typo surfaced
  as `FAIL [gate] NOPE→CRS: 0/0 covered` and sent people looking for missing
  items. Both the error and the new skip reason are now printed.

- **`cr status` and `assert_cr_active` disagreed about the same CR.** The former
  still parsed the raw status string, so a status-less CR was accepted by the
  workflow gate and simultaneously reported `valid: false`. It now delegates to
  `get_cr_phase`.

- The traceability report grouped coverage by a prefix guessed from the item ID.
  It now uses the resolved doc-type code, which is what the matrix columns use.

- **`change plan` reported "CR not found" for the CR the scaffold just wrote.**
  The starter `CR-001.yaml` carries no `status` field, and `get_cr_phase`
  returned `None` for a missing CR, an absent status, and an unrecognised status
  alike — so the documented first command of a new project failed on the item it
  was pointed at. An absent status now reads as `new`, the scaffolded CR states
  it explicitly, and `assert_cr_active` checks existence separately so its
  error names the real problem. `CRPhase` gains `rejected`, which the
  generate-dhf triage step writes and which was previously indistinguishable
  from a missing CR.

- **An item could report `verified` with no evidence at all.**
  `_refresh_verification_status` returned early on an empty result store,
  leaving a stale `verification_status: verified` in the YAML standing. Adding a
  single *unrelated* result then flipped the same item to `not_verified` — the
  status of one requirement depended on whether another had a test. The status
  is derived, so it is now always computed: no linked evidence means
  `not_verified`.

- **`evidence bundle --junit` wiped verification held in the result store.**
  `inject_junit_results` computed status purely from the supplied files, so a
  requirement verified by previously pulled CI results — or by a manual review
  record, which can never appear in a generated JUnit file — was silently
  demoted to `not_verified`. Injection now merges: items named in the JUnit take
  their status from it, items absent from it keep what the store established.

- **A typo in `--coverage-pair` greened the gate.** An unknown document type
  matched no items and reported `passed: True, total: 0`. Unknown codes are now
  reported as a failure naming the configured codes.

- **`_get_prefix` never resolved a prefix from config.** It passed a doc-type
  *code* to `get_item_type`, which matches on *prefix*, so the lookup always
  missed and fell through to `code + "-"`. That is correct only when the prefix
  happens to be the code plus a dash; a project configuring `TC-VER-` for code
  `TCVER` got `TCVER-` and matched nothing.

- **Multi-segment prefixes were dropped from the traceability report.** The
  verification column derived a prefix with `split("-")[0]`, reducing `TC-VER-`
  to `TC-`, while `dhfkit`'s own `Item.prefix` uses `rsplit("-", 1)`. Now
  consistent.

- **Issue comments were truncated at 100.** CR intake called `gh api` with
  `per_page=100` but no `--paginate`, so a long discussion silently built the CR
  from partial input. Now paginated, with the `--slurp` page wrapper flattened.

- **GitLab artifact fetching was broken for every auto-detected project.** The
  project path (`namespace/project`) was interpolated unencoded into
  `/api/v4/projects/{id}/...`, so the unescaped slash made GitLab read it as
  extra path segments and every request 404d. It is now URL-encoded; a numeric
  `GITLAB_PROJECT_ID` is still passed through as-is.

- **Failing GitLab pipelines could not be fetched.** The pipeline lookup
  filtered on `status=success`, so a run whose tests failed raised "no pipeline
  found" — the run whose results a DHF most needs to record. The filter is gone;
  the most recent pipeline for the commit is used regardless of outcome. GitHub
  was already correct here, filtering on `status=completed`.

- **Denied artifact downloads were reported as "no evidence".** A bare
  `except Exception: continue` swallowed 403s and transport errors alongside the
  404s that legitimately mean "this job uploaded nothing", so an auth failure
  silently recorded every requirement as unverified. Only 404 is skipped now;
  anything else propagates.

- **Artifact and job listings were truncated silently.** Neither fetcher set
  `per_page`, so GitHub returned at most 30 artifacts and GitLab 20 jobs. A
  matrix build exceeding those limits lost evidence with no indication. Both now
  request 100.

- **Specifications contained items belonging to other document types.** The item
  filter matched on the bare doc-type code, and `"SYSARCH-001".startswith("SYS")`
  is true — so every architecture item was emitted into the system requirements
  specification. It now matches on the configured prefix (`SYS-`). This affected
  the default scaffold, whose starter DHF has both `SYS-001` and `SYSARCH-001`.

- **Document versions tracked how often the generator ran, not content.** Every
  regeneration bumped the minor version and rewrote the file, so a CI job that
  regenerates docs inflated the version of a controlled document with nothing
  changed (1.0 → 1.3 after three no-op runs). The version now advances only when
  the rendered content actually differs, and an unchanged document is not
  rewritten at all.

- **`evidence bundle` could not run on a base install.** Both the specification
  and plan paths hard-required WeasyPrint, which lives in the optional `docs`
  extra, so `pip install medharness` followed by `evidence bundle` raised an
  unhandled `ModuleNotFoundError`. Bundles now render HTML by default;
  `--doc-format pdf` opts back into the PDF path.

- **PDF exports were written to a hardcoded `/tmp` path**, so concurrent runs on
  one CI runner overwrote each other's evidence, and the path was unusable on
  Windows. Output now defaults to `DHF/documents/exports` and accepts
  `--out-dir`.

- **A missing PDF renderer produced a traceback** rather than a message saying
  what to install. It now reports the extra and the native-library requirement,
  and points at HTML export.

- The SRS specification was titled "Software Requirement Specification
  Specification" — `doc_type_name` already carried the suffix the template
  appends. Items without a `status` rendered as an empty `<span class="status-">`.

### Documentation

- `docs/adopting.md` gains a **Software safety classification** section covering
  the class, the project-owned activity map, §4.3(b) per-module overrides, and
  the opt-in behaviour — Phase 1 shipped the feature without it.

### Internal

- `dhfkit/tests/test_document_generation.py` imported `medharness.workflows.init`,
  breaking the `dhfkit` → `medharness` boundary and the ability to run dhfkit's
  suite standalone. It now builds its fixture from the bundled templates
  directly. A check over the whole package confirms no such import remains.

- Removed `medharness/services/release_baseline.py`, a dead duplicate of
  `dhfkit/release_baseline.py` orphaned by #189 when DHF data operations moved
  to `dhfkit`. Nothing imported it — the two copies differed only in one import
  line — but it shipped in the wheel, showed as 0% coverage (diluting the signal
  used to find genuinely untested code), and was a trap: editing it would have
  had no effect and raised no error.

- `dhfkit/tests/test_artifact_fetcher.py` — the module had no test file at all
  (250 statements, reachable only through `test pull` against a live CI
  provider). A fake `urlopen` records requested URLs, so the tests assert on the
  requests themselves rather than only on parsed output. Coverage 20% → 63%.

- `dhfkit/tests/test_document_generation.py` covers all of the above.

- The `evidence bundle` contract test returned early whenever WeasyPrint was
  absent, so on CI it asserted nothing at all — which is why none of this was
  caught. It now runs the bundle and checks the rendered artifacts.

## [0.12.1] — 2026-08-19

### Bug Fixes

- **`medharness init` no longer claims to create a CI workflow it cannot.** The
  CI workflow is deliberately not part of the release payload — a policy dating
  to May 2026 and enforced by `scripts/audit_oss_delivery.sh`. The rest of the
  project had never been reconciled with it:

  - `_scaffold_dhf` copied `github/workflows` into `.github/workflows`, which
    silently did nothing on an installed package because the source is absent.
  - The README showed `.github/workflows/dhf.yml` as part of `init` output.
  - `medharness upgrade` listed that path in its template map and claimed to
    manage it, while skipping any template missing from the installation without
    comment — then reporting "All 25 scaffold file(s) are up to date".
  - `docs/adopting.md` told adopters to use "the scaffolded workflow from
    `init`", which never existed for anyone installing from PyPI.

  Nothing caught the split: the scaffold CI job installs with `pip install -e .`,
  where the repository tree stands in for the package and every template is
  present.

  `init` now scaffolds only what it can deliver, and the CI recipe has a real
  home in [Setting up CI](docs/adopting.md#setting-up-ci).

- **`medharness upgrade` reports templates it cannot supply.** A template absent
  from the installation is a packaging fault rather than a project state, so it
  now appears under an `unavailable` key and in the summary rather than being
  passed over silently.

### Documentation

- **New "Setting up CI" section** in `docs/adopting.md` with the complete
  `.github/workflows/dhf.yml` and a table of what each job does. This is now the
  delivery path for the pipeline, including the `--fail-on-uncovered` change
  from v0.12.0.
- README no longer shows `.github/workflows/` in the `init` output tree.

### Internal

- `tests/unit/test_packaging_templates.py` inspects the built wheel: workflow
  templates stay out, every template the upgrade map claims survives packaging,
  and `docs/adopting.md` embeds the workflow recipe verbatim so the two cannot
  drift. It builds with `python -m build` from a clean copy of the tree, because
  neither shortcut reproduces what gets published — `uv build` resolves a
  different setuptools and applies `exclude-package-data` globs differently, and
  a stale `*.egg-info/SOURCES.txt` in the working tree masks exclusion changes
  entirely.
- The unit-test CI job installs `.[dev]`, which now carries `build`; without it
  the packaging suite skips and the faults it guards reach PyPI unnoticed.
- The scaffold CI check asserts `.github/workflows` is *not* created.

---

## [0.12.0] — 2026-08-19

Two correctness fixes in the verification gates, and the SOUP gate becomes
usable in regulated pipelines. **Read "Behaviour changes" below before
upgrading** — `verify dhf` can now fail on a DHF that previously passed.

### Bug Fixes

- **Dangling traceability links are now detected.** A link whose target ID does
  not exist was never reported as such. It surfaced only as a downstream
  coverage gap — with remediation advice ("add a link") that did not apply,
  because the link was already there and simply resolved to nothing. Where
  coverage happened to be satisfied elsewhere, the broken reference was
  completely silent. `verify dhf` and `dhfkit validate traceability` now name
  the source item, field, and missing target:

  ```
  FAIL [dangling] RCM-001.mitigates → RISK-404: target does not exist
      Fix: correct the ID in RCM-001.yaml, or create RISK-404.
           The link exists but resolves to nothing.
  ```

- **Advisory coverage gaps no longer print `FAIL` on a passing build.** Coverage
  gaps have always been advisory unless `--fail-on-uncovered` is set, but both
  CLIs labelled them `FAIL` — so a green check sat on a CI log full of failures,
  telling readers the gate had blocked when it had not. They now print `WARN`
  (`⚠` in `dhfkit`) with a note on how to enforce them.

- **Scaffolded CI now enforces the coverage gate it reports.** The `dhf.yml`
  template ran `verify dhf --dhf DHF` without `--fail-on-uncovered`, so every
  project created by `medharness init` had a coverage gate that could not fail.

- `medharness verify dhf --fail-on-uncovered` had no help text at all.

- `medharness init` was documented as "Interactive onboarding" while taking no
  prompts.

### New Features

- **`verify soup --offline-mode warn`** — an unreachable `api.osv.dev` failed the
  gate outright, which is a hard block for the air-gapped and proxy-restricted
  pipelines common in this industry. `warn` tolerates the outage while still
  recording it in the JSON output and printing a `WARN` line, so the gap stays
  visible in evidence rather than becoming invisible. Default remains `fail`.

- **Documented vulnerability acceptance on SOUP items.** IEC 62304 §8.1.2
  requires SOUP anomalies to be *evaluated*, not necessarily fixed. The gate
  previously blocked on every finding with no suppression path, so a project
  carrying an assessed-and-accepted CVE had to either fix it or disable the gate.
  Record the assessment on the item instead:

  ```yaml
  accepted_vulns:
    - id: GHSA-xxxx-yyyy-zzzz
      rationale: "Affected API is not reachable from our code paths."
  ```

  Both keys are required — an entry without a rationale, or a bare ID string,
  is reported as a warning and keeps blocking. Acceptance is per-vulnerability-ID
  by design, so a newly published CVE against the same package still fails.

- **Vulnerability findings now carry a summary and a link.** osv.dev's
  `querybatch` returns only `{id, modified}`, so every finding was reported as a
  bare ID with an empty description. Details are now fetched per finding
  (budgeted), and an `osv.dev` URL is always emitted so the finding stays
  actionable if the lookup fails.

- **[`docs/ai-security.md`](docs/ai-security.md)** — what the AI stages can do,
  where they should run, the audit trail they leave, and how to run MedHarness
  with no AI at all. The AI stages execute an agentic loop with an unrestricted
  shell tool; that boundary was previously undocumented, which is not a
  defensible position for a tool aimed at regulated teams.

### Documentation

- README gains a Mermaid diagram of the CR lifecycle and real `verify dhf`
  output showing what the gates actually catch.
- The `claude` CLI is an external dependency `pip` cannot install; the install
  section now says so and points at `medharness doctor`.
- [ContourLab](https://github.com/itercharles/ContourLab) documented as the
  real-world reference implementation.
- `docs/adopting.md` gains a blocking-vs-advisory table for `verify dhf`.
- `SECURITY.md` supported-versions table was still pinned at `0.1.x`.

### Security

- Upgraded `gitpython` 3.1.50→3.1.59, `cryptography` 48.0.1→50.0.0,
  `pillow` 12.2.0→12.3.0, `pyasn1` 0.6.3→0.6.4, closing 36 Dependabot alerts.

### Behaviour changes

- **Dangling links now block.** A DHF carrying one was already broken — it just
  was not being reported. Run `medharness --dhf DHF verify dhf` before upgrading
  CI to see whether you have any.
- **Newly scaffolded projects enforce coverage.** Existing projects are
  unaffected: their `dhf.yml` lives in their own repository. `medharness upgrade`
  surfaces the new template. If you are backfilling an existing DHF, drop
  `--fail-on-uncovered` until the backlog is clear.
- `verify soup` output gained `accepted`, `acceptance_problems`, and a `url`
  field on each vulnerability. Existing keys are unchanged.

---

## [0.11.0] — 2026-08-18

### New Features

- **Multi-ecosystem SOUP sync** — `dhfkit soup-sync` now supports 9 manifest
  formats: `requirements.txt`, `uv.lock`, `poetry.lock`, `pyproject.toml`,
  `package.json`, `package-lock.json` (v1/v2/v3), `go.mod`, `Cargo.lock`, and
  `pom.xml`. Auto-discovers known manifest files in the project root when no
  `--manifest` flag is given.

- **`soup-sources.yaml` extension config** — persistent per-project source list
  at `DHF/config/soup-sources.yaml` with three entry types:
  - `manifest` — path to any supported lockfile/manifest
  - `command` — arbitrary shell command emitting NDJSON `{name,version,ecosystem}`
    per line; enables integration with tools like `syft`, `trivy`, or custom
    scanners
  - `manual` — static entries for hardware, operating systems, and commercial
    software that have no package manager

  Source priority: explicit `--manifest` flags → `--from-command` → `soup-sources.yaml`
  → auto-discovery. New projects get a commented-out template via `medharness init`.

- **Design review gate in `verify completion`** — closure gate now requires
  `docs/reviews/<CR>-Design-Review.md` to exist and contain
  `**Verdict:** Approved`. Missing or non-approved review files emit
  `FAIL [cr-complete]` and block closure.

- **`verify soup` SOUP vulnerability scanning** — new CI gate queries the
  [OSV vulnerability database](https://osv.dev) for all SOUP items that carry
  an `ecosystem` field. Exits non-zero if any known CVEs are found. Items
  without `ecosystem` are skipped with a note. Add `ecosystem: PyPI` (or `npm`,
  `Go`, `Maven`, `crates.io`, etc.) to a SOUP item to enable scanning.

- **`medharness upgrade` scaffold migration** — new command diffs 24 scaffold
  infrastructure files (CI workflow, AI prompts, spec templates, doc-type
  configs) against the installed version and optionally applies updates.
  Never modifies DHF items, `global.yaml`, `context.md`, or `CLAUDE.md`.

### Bug Fixes

- Fixed `parse_pom_xml` namespace traversal bug where child-element lookups
  used the wrong side of a namespace ternary, causing non-namespaced `pom.xml`
  files to parse as empty.

---

## [0.10.0] — 2026-05-28

### New Features

- **`ci verify completion` CR field checks** — closure gate now requires
  `implementation_notes`, `affected_risk_items`, and
  `triage_result.verdict == "approved"` on the CR item before passing.
  Missing or null values emit `FAIL [cr-complete]` and block the gate.

- **`approval act` command** — executes `/approve` (adds stage label +
  confirmation comment) and `/reject` (posts reason + closes PR) from a PR
  comment body.

- **`dhf context for-stage design`** — now returns the full DHF item list so
  the LLM can decide create-vs-update at the start of generate-dhf. Previously
  returned `affected_items`, which is empty at that point.

- **`dhf context for-stage develop`** — now includes `implementation_notes`,
  `proposed_new_items`, `triage_result`, and richer affected-item fields
  (`description`, `content`, `verification_criteria`).

- **Triage structured record** — generate-dhf writes `triage_result` (verdict,
  complexity, affected_subsystems, notes) onto the CR item on approval.

- **Vague `verification_criteria` detection** — warns when criteria on changed
  CRS/SYS/SRS items contain non-measurable phrases ("works correctly", "behaves
  as expected", etc.). Does not trigger a fix pass; surfaced as a warning only.

- **Release baseline in scaffold workflow** — the sample `dhf.yml` gains a
  `release-baseline` job triggered on `v*` tags. Runs
  `dhfkit release-baseline --write`, commits the REL item back to `main`, and
  uploads `release-baseline.json` + `software-bom.json` as artifacts.

- **`ci test-points` coverage scenarios** — 6 additional test cases covering
  multi-test coverage, per-requirement isolation, and SYS/CRS item types.

### Improvements

- Code review conventions now driven by the project's `CLAUDE.md` instead of
  hardcoded TypeScript/Tailwind defaults.

---

## [0.9.0] — 2026-05-21

### New Features

- **`testing` field on CRS, SYS, SRS items** — requirements now carry numbered
  test points (`T1:`, `T2:`, …) written at design time. Rendered in spec
  documents under a "Testing" section.

- **`@testing:Tn` test annotation** — Python tests declare covered points via
  `@pytest.mark.dhf_testing("T1", "T2")`; JS tests embed `@testing:T1` in the
  test name. Both write `medharness.testing` to JUnit XML output via the
  `dhf_testing` pytest marker.

- **`ci test-points` gate** — checks that every numbered test point declared on
  a requirement has at least one covering passing test. Exits non-zero on gaps.
  Consistent with `ci test-coverage`: reads both JUnit `medharness.links`
  properties and inline `@links:REQ-ID` tags from test names.

- **TDD workflow documented** — README and `docs/adopting.md` updated with
  end-to-end examples of writing test points at design time and gating coverage
  in CI.

---

## [0.8.0] — 2026-05-19

### Breaking Changes

- **`dhfkit` now owns all DHF data-layer CLI commands** — `medharness dhf item`,
  `medharness dhf validate`, `medharness dhf doc`, `medharness dhf test`,
  `medharness dhf config`, and `medharness dhf report` have moved to `dhfkit`.
  Use `dhfkit --dhf DHF <command>` for all data operations. `medharness dhf`
  now exposes only AI-harness context commands (`context implementation`,
  `context for-stage`, `context overview`).

- **`dhfkit soup-sync` and `dhfkit release-baseline`** — these commands moved
  from `medharness ci soup-sync` / `medharness ci release-baseline` to top-level
  `dhfkit` commands. Update workflow files and scripts accordingly.

- **`ci evidence import` and `ci artifacts generate` removed** — these commands
  had no active callers and have been deleted entirely.

- **`--spec` flag removed from `ci validate-branch`** — `proposed_new_items` is
  now written directly to the CR item (via `dhf item update` in `generate-dhf`
  Step 4) rather than to a spec Markdown file. The spec-file path argument is no
  longer accepted.

### New Features

- **Risk context in `generate-dhf` prompt** — `_build_risk_context_block()`
  injects the full RISK/RCM landscape into the design prompt so the LLM can
  correctly assign `implements: [RCM-xxx]` on new SYS requirements and avoid
  creating duplicate risks.

- **Spec-to-artifact reconciliation in `develop-cr`** — `_validate_spec_reconciliation()`
  compares `proposed_new_items` type counts from the approved CR spec against
  what was actually created. Shortfalls surface as structured errors in the
  fix-pass loop.

- **`proposed_new_items` written to CR item** — `generate-dhf` Step 4 now
  writes the bill of materials directly onto the CR item. `ci cr-complete`
  closure gate enforcement is now live (previously always vacuously passed
  because the spec file was never written).

- **CI workflow template in scaffold** — `medharness init` now includes
  `dhf.yml` in `.github/workflows/`, giving new projects a working CI pipeline
  (dhf-validate on PR, evidence bundle on merge) out of the box.

- **`docs/adopting.md`** — new guide covering four adoption paths: starting
  fresh, migrating an existing DHF, using dhfkit standalone, and incremental
  adoption into an existing regulated product.

---

## [0.7.0] — 2026-05-17

### New Features

- **Risk chain in `dhf report`** — `check_traceability()` now includes a
  `risk_chain` key mapping each RISK item to its linked RCMs and the
  requirements those RCMs implement. Rendered as a "Risk Chain" section in the
  human-readable traceability report.

- **Risk impact in `ci validate-branch`** — `validate_atomic_branch()` traverses
  changed DHF item IDs through RCM `implements` → `mitigates` links to surface
  RISK items potentially affected by the branch. Emits a WARN to stderr when
  risks are found; `risk_impact` key added to the JSON payload.

- **pytest plugin (`dhfkit.pytest_plugin`)** — `@pytest.mark.dhf_links(*ids)`
  and `@pytest.mark.dhf_id(id)` markers write `medharness.links` and
  `medharness.id` JUnit XML properties, wiring test results to DHF requirement
  IDs. Auto-registered via `pytest11` entry point. When only `dhf_links` is
  present, a `medharness.id` is auto-derived from the first link so evidence
  ingestion works without requiring an explicit `dhf_id`.

- **`dhfkit init` command** — bootstraps a new DHF directory from the bundled
  starter template. Writes `global.yaml` (with `project_name`, `required_traceability`,
  `document_specifications`), copies core doc-type configs, seeds `documents/specs/`
  with Jinja2 templates, and creates item directories for SYS, SRS, RISK, RCM.
  Outputs a JSON summary line to stdout; exits non-zero if the target directory
  is not empty.

- **`ci soup-sync` command** — parses `requirements.txt` (pinned `==` entries)
  and `package.json` (`dependencies`, `devDependencies`, `peerDependencies`) and
  diffs them against DHF SOUP items. Reports new packages, version-drifted items,
  and orphaned SOUP records. `--write` applies creates/updates via `dhfkit.api`.
  Duplicate package names across manifests are deduplicated (first occurrence wins)
  to prevent multiple SOUP records for the same dependency.

- **`ci release-baseline` command** — IEC 62304 §9 release record automation.
  Verifies all included CRs are in `completed` state (cancelled/rejected fail the
  gate), auto-collects completed unreleased CRs when `--cr` is omitted, builds a
  software BOM from DHF SOUP items and package manifests, and writes
  `release-baseline.json` and `software-bom.json` to `--out-dir`. `--write`
  creates a REL item in the DHF. Manifest parse failures propagate as errors so
  an incomplete BOM never silently looks successful.

---

## [0.6.4] — 2026-05-16

### Bug Fixes

- **`ci advance-stage` exits 1 when `add_label` fails** — previously the
  command printed `WARN` and exited 0 when `gh api` calls failed (invalid
  token, missing label, wrong repo context), silently leaving the PR on the
  wrong stage. Now exits 1 with a `FAIL` message when adding the to-stage
  label fails. `remove_label` remains non-fatal (idempotent).

---

## [0.6.3] — 2026-05-16

### New Features

- **`ci advance-stage` command** — replaces multi-step `gh api` label management
  bash in CR lifecycle workflows. Takes `--pr N --from-stage STAGE --to-stage STAGE`
  (optionally `--issue N` to mirror the advance on a linked issue) and
  `--label-prefix PREFIX` (default `cr:stage/`). Idempotent: a missing from-stage
  label is silently ignored.

- **Auto-post PR comments on warnings and errors** — `generate-dhf` and
  `develop-cr` now automatically post a PR comment when warnings are present or
  when the outcome is `completed_with_errors`, eliminating the "Surface warnings"
  and "Gate on X validation" workflow steps that previously duplicated this logic.
  Auto-posting only occurs when `--pr N` is supplied. The posted comment URLs
  are returned in the `pr_comments` field of the JSON response.

- **`ci generate-dhf` and `ci develop-cr` exit non-zero on `completed_with_errors`**
  — previously these commands exited 0 even when deterministic validation found
  residual errors, requiring the caller to parse JSON and check the `outcome`
  field. They now exit 1 for both `tool_error` and `completed_with_errors`,
  allowing workflows to gate on exit code alone.

- **`medharness/services/github_pr.py`** — new internal service providing
  `post_pr_comment`, `add_label`, and `remove_label` helpers used by the above
  features and available for custom tooling.

---

## [0.6.2] — 2026-05-16

### Bug Fixes

- **`get_session` returning `"null"` on first revision run** — the `jq` query
  used `[] | last` which emits the literal string `null` when no session marker
  comment exists yet. Added `// empty` to the jq pipeline and a defensive
  `!= "null"` filter on the return value so the first `--pr` rerun on a PR
  with no stored marker correctly starts a fresh Claude session instead of
  passing `--resume null`.

- **`_run_claude` discarding empty `result` field** — `data.get("result") or
  result.stdout` fell back to the raw JSON envelope when Claude returned an
  empty-string result. Changed to an explicit `None`-check so an intentional
  empty output is preserved.

### Changes

- **Session ID threading** — `generate_dhf` and `generate_code` now capture
  the `session_id` from Claude's `--output-format json` envelope and thread it
  through the full step chain: initial generation → fix pass → (for
  `generate_code`) review step all share one continuous Claude session.
  On revision runs the prior session stored in the PR comment via
  `github_session.get_session` / `put_session` is automatically resumed.
  Session IDs are recorded in `diagnostics.session_id` and
  `diagnostics.resumed_session_id` for observability.

---

## [0.6.1] — 2026-05-15

### Changes

- Test cleanup: extracted `_init_dhf_repo()` helper to eliminate duplicated
  git setup across E2E test fixtures; added `check=True` to subprocess calls
  inside the fix-pass stub so silent failures raise immediately.

---

## [0.6.0] — 2026-05-15

### Breaking Changes

- **`workflow_intake_github_issue` and `workflow_intake_github_issue_ci` drop the spec compatibility stubs**
  - 0.5.0 removed spec generation but kept `spec_generated`, `spec_status`,
    `spec_validation`, `spec_path`, `spec_json_path`, and `spec_error` in
    both return dicts as `false`/`null` stubs "for API compatibility."
    Those stubs are now removed. Callers that read these keys from the Python
    API or parse them from CLI JSON output must drop those references.

### Changes

- Removed unused `_get_document_with_legacy_fallback` helper from `_helpers.py`
  (legacy `docs/cr-specs/` fallback path, no callers).
- `ci generate-dhf` and `ci develop-cr` now emit per-error `field`/`issue`/`Fix:`
  detail lines to stderr when validation errors remain after generation, matching
  the existing pattern in `ci validate-code` and `ci validate-branch`.
- `cr_review_code.md` prompt updated: references CR item via
  `medharness --dhf DHF dhf item get {{cr_id}}` instead of the removed
  `docs/cr-specs/` file path; review output written to `docs/reviews/`.
- DHF scaffold now creates `docs/reviews/` so the code-review output path
  exists in newly initialised repos.
- Added golden E2E integration tests (`test_generate_dhf_e2e.py`) covering
  `generate_dhf` and `generate_code` orchestration with a stubbed Claude CLI,
  including the full validate→fix→validate cycle.

---

## [0.5.0] — 2026-05-14

### Changes

- **Remove cr-spec phase; collapse design+dev into single generate-dhf → develop-cr flow**
  - `ci analyze-cr` and `ci design-cr` commands removed. The new two-phase flow is
    `generate-dhf` (design + DHF items + implementation plan) followed by `develop-cr` (code).
  - `generate-dhf` now includes triage (duplicate / out-of-scope / too-large /
    architecture-conflict), V-model DHF cascade, and writes a structured
    implementation plan into `implementation_notes` on the CR item.
  - `generate-dhf` reads relevant source modules before writing SWDD items so
    the reviewed design reflects the actual codebase. SWDD is only created when
    a genuine design decision exists (threshold rule baked into prompt).
  - `develop-cr` reads `implementation_notes` as its primary implementation spec;
    runs `medharness ci test-coverage` after tests to verify requirement coverage;
    reconciles `implementation_notes` and SWDD items if implementation deviated.
  - CR lifecycle simplified: `new → design → develop → completed` or `new/design → rejected`.
    State transitions are recorded for traceability but not enforced as CI gates.
  - `validate-spec` and `validate-design` commands removed; `validate-code` and
    `validate-branch` retained.
  - `validate-branch` now enforces DHF item changes unconditionally (previously
    only when a spec file was present).
  - `--generate-spec` flag removed from `cr workflow intake-github-issue` and
    `intake-github-issue-ci`. Intake payloads still include `spec_generated`,
    `spec_status`, `spec_validation`, `spec_path`, `spec_json_path`, `spec_error`
    as `false`/`null` for API compatibility.
  - `implementation_notes` is now LLM-authored; the harness no longer writes a
    "Design Impact Snapshot" block to it.
  - `check_status` gate accepts `new`, `design`, and `develop` as valid states.
  - `ItemType` enum V-model defaults: traceability summary now includes an
    opt-out hint when V-model defaults are applied
    (`required_traceability: []` in `global.yaml` to disable).
  - `_item_type_dict` now returns `dt.name` (human-readable) for the `name`
    field instead of `dt.code`.

## [0.4.0] — 2026-05-13

### Changes

- **Breaking CR generation response contract redesign**
  - `ci analyze-cr`, `ci design-cr`, and `ci develop-cr` no longer emit the
    legacy `status` / `validation` / `corrections` / top-level artifact fields.
    They now return a client-facing contract built around `outcome`,
    `summary`, `timing`, `inputs`, `progress`, `steps`, `artifacts`,
    `diagnostics`, `warnings`, and `errors`.
  - `tool_error` is now a first-class outcome for hard generation failures,
    and the CI CLI exits non-zero for those runs instead of printing a false
    success summary.
  - Workflow intake adapters preserve legacy `spec_status` /
    `spec_validation` semantics so existing intake automation can continue to
    branch on those fields while the generation JSON itself moves to the new
    contract.
  - Migration: any client parsing `ci analyze-cr` / `design-cr` /
    `develop-cr` JSON must switch to the new top-level fields and read
    generated paths, change buckets, and analysis data from `artifacts`.

- **CI contract hardening for CR validation**
  - `validate-branch` now normalizes relative `--spec` paths against the repo
    root instead of assuming an already-absolute path.
  - `validate-code` now enforces `@links:` only for `test_plan.needs_new_tc`
    entries that are actual DHF item IDs, and only when the annotation appears
    on an added comment line. Free-form prose entries remain valid analysis
    output but are no longer forced through brittle exact-text annotation
    matching.
  - `validate-spec` now rejects `doc-only` specs that still list DHF impact and
    rejects `test-only` specs that propose new DHF items.
  - The CR analysis prompt now tells the model to keep `standard` when product
    code changes are needed but no DHF item updates are required, and to prefer
    real item IDs in `needs_new_tc` whenever possible.
  - Contract and unit tests now lock the help-surface for `--dhf`, the
    comment-only annotation rule, and the relative-spec-path behavior.
- **Design-phase CR impact recording**
  - `generate_design` now writes successful DHF impact back onto the CR item
    automatically: `affected_items` is updated from the validated design delta,
    and `implementation_notes` gains a managed "Design Impact Snapshot" section
    that records spec-declared new items plus actual created/updated/deleted
    DHF item IDs.
  - Generated Change Request specification documents now render
    `implementation_notes`, so the recorded design impact is visible in CR
    output without re-parsing CI logs.
- **Combined issue intake + initial spec drafting**
  - `cr workflow intake-github-issue` and `intake-github-issue-ci` now
    generate the initial spec draft by default whenever they create a new CR
    with `--write`.
  - This adds one Claude/spec-generation pass to default intake behavior.
    Use `--no-generate-spec` to opt out when a client repo wants the older,
    cheaper CR-only intake path.
  - Intake JSON now includes `spec_generated`, `spec_status`,
    `spec_validation`, `spec_path`, `spec_json_path`, and `spec_error`, so
    client repos can treat spec review as the first real approval gate without
    re-running `ci analyze-cr`.

## [0.3.7] — 2026-05-12

### Changes

- **CR triage routing** — `ci analyze-cr` now classifies CRs before writing a
  full spec, replacing the blunt `direction_fit` field with three dedicated
  front-matter fields:

  - `disposition` — required on every spec. Values: `approve`,
    `decline:out-of-scope`, `decline:duplicate`, `decline:architecture-conflict`,
    `decline:too-large`, `hold:scope-expansion`.
  - `pipeline_route` — required when `disposition: approve`. Values:
    `standard` (analyze → design → develop), `dhf-only` (no code),
    `doc-only` (no design/develop), `test-only` (no new DHF items).
  - `decline_rationale` — required string when disposition is not `approve`.
    Provides an auditable reason for the decline or hold (IEC 62304 evidence).

  For declined/held CRs only `cr_id`, `disposition`, and `decline_rationale`
  are populated; all other spec fields are skipped and not validated.

  `direction_fit` is removed. Existing specs with `direction_fit` are migrated
  transparently by `validate_spec` (legacy values map to the nearest
  `disposition`), so no manual spec updates are required. Specs that contain
  neither field fail validation and trigger the self-correction loop.

- **Enriched `proposed_new_items`** — each entry in the `proposed_new_items`
  front-matter list now supports optional `parent` and `verification_method`
  fields:

  - `parent` — ID of the existing DHF item this new item traces to (e.g.
    `SYS-012`). Validated by `validate_spec` against live DHF item IDs.
  - `verification_method` — `Inspection` or `Demonstration`; only valid for
    item types that carry a verification method in the dhfkit schema (`SYS`,
    `SOUP`). `validate_spec` rejects the field for other types.

  The `ci design-cr` prompt now receives this richer structured data so Claude
  can wire parent links and verification methods at item-creation time.

- **`validate-branch` code-change check is now opt-in** — `--code-path` must
  be passed explicitly to require that implementation files were modified. When
  omitted, the command checks only that the spec file and DHF item changes are
  present. This removes a WebTPS-specific default (`apps/`, `packages/`) that
  was incorrect for all other project layouts.

  Migration: update CI invocations that relied on the implicit default to pass
  `--code-path <dir>` explicitly, or drop the check for doc/DHF-only CRs.

---

## [0.3.6] — 2026-05-11

### Changes

- `ci analyze-cr` now emits a companion `CR-NNN-Spec.json` alongside the
  Markdown spec. The JSON contains every machine-readable front-matter field
  and is read by downstream validators in preference to re-parsing Markdown.
  The `ci analyze-cr` stdout payload gains `spec_json_path` (absolute path
  to the JSON file, or `null` if Claude wrote no spec file).

- Two new required front-matter fields are added to CR specs:
  - `proposed_new_items` — list of `{type, title}` dicts describing DHF items
    the design stage should create. `[]` is valid when no new items are needed.
  - `design_impact_summary` — a non-empty string (1–2 sentences) summarising
    the overall design impact. Required so the summary is machine-readable
    rather than buried in Markdown prose.

  Existing specs that lack these fields will fail `validate_spec` and trigger
  the self-correction loop, prompting Claude to add them.

- `ci design-cr` injects the full `CR-NNN-Spec.json` content as a structured
  block at the top of the design prompt (non-revision mode only). Claude no
  longer needs to re-parse the Markdown spec to identify affected or proposed
  items — the structured data is explicit in the prompt.

- `validate_spec`, `write_spec_json`, and `read_spec_json` are now public
  symbols in `medharness.services.spec_validation`.
- `ci analyze-cr` now also emits a structured `analysis` object in stdout,
  with `direction_fit`, `affected_items`, `proposed_new_items`,
  `design_impact_summary`, and `test_plan`, so clients do not need to
  re-parse the spec file for the most common CR-analysis fields.

- Bundled GitHub workflow templates were removed from the shipped scaffold.
  MedHarness now treats the CLI and Python services as the stable product
  surface, while repository automation is left to client repos.

- `medharness init` no longer generates `.github/workflows/*`. It still
  scaffolds DHF content and `.github/prompts/` for repo-local automation.

  Migration:
  - existing repos that previously copied bundled workflow templates should
    delete or replace those stale `.github/workflows/*` files explicitly
  - new or existing repos should move automation logic to thin repo-local
    wrappers around the CLI (`ci github-event`, `ci validate-design`,
    `ci validate-code`, `ci validate-branch`, `ci cr-status`)

- `ci github-event` now supports configurable event-to-stage and
  event-to-action mapping via CLI flags so client repos can layer their own
  automation without hardcoded MedHarness workflow assumptions.

- New `ci cr-status` command reports machine-readable CR stage and approval
  status in one JSON payload, so client automation can query whether a PR is
  approved for its current stage without re-implementing MedHarness label and
  branch conventions.

- New `ci validate-design` and `ci validate-code` commands expose the existing
  deterministic design and implementation checks as standalone CLI preflight
  steps, so client automation can catch schema, traceability, affected-item,
  and test-annotation issues before opening a PR.

- New `ci validate-branch` command checks that a single branch carries the
  expected coupled CR change set: the approved spec, product code changes, and
  DHF item YAML changes when the spec says DHF impact is expected.

---

## [0.3.5] — 2026-05-10

### Changes

- `ci design-cr` and `ci develop-cr` now run **deterministic structural
  checks before** the LLM review pass, matching the pattern already used
  by `ci analyze-cr`:
  - **design**: schema validation, required-traceability rules, orphans,
    coverage gaps, and presence of every spec `affected_items` ID — all
    via `dhfkit.api`. On failure, a fix-only LLM prompt with structured
    error lines runs once before the soft review.
  - **develop**: presence of `@links:<ID>` annotations in the diff for
    every item in the spec's `test_plan.needs_new_tc`. On failure, a
    fix-only LLM prompt asks for the missing colocated tests.
- The soft-review prompts (`cr_review_design.md`, `cr_review_code.md`)
  are trimmed to judgment questions only — schema, traceability, and
  test-annotation presence are no longer re-asked of the model. The
  prompts are augmented at runtime with a "Deterministic Checks" section
  that tells the reviewer not to re-derive what the harness already
  proved.
- `generate_design` and `generate_code` now return `corrections` and
  `validation` fields (matching `generate_spec`); `validation` is one of
  `"passed"` or `"residual_errors"` (replacing the prior placeholder
  `"not_checked"` value — consumers that string-matched the old value
  will see the new domain).
- `ci design-cr` and `ci develop-cr` stderr summaries now include the
  correction count and validation outcome, matching `ci analyze-cr`.
- `validate_code` now distinguishes git-environment failures (missing
  binary, unfetched ref, non-zero exit) from a legitimately-empty diff:
  the former emits one `field: "environment"` error so the fix-only LLM
  prompt does not waste a call asking for tests the model cannot add;
  the latter still flags missing `needs_new_tc` annotations.

### Enhanced response payload (`generate_spec` / `generate_design` / `generate_code`)

The dict returned by all three functions (and echoed as JSON by the
matching `ci analyze-cr` / `design-cr` / `develop-cr` commands) now
carries a uniform, richer shape so clients can render outcomes without
re-running validators or shelling out to git. New / changed keys:

- `stage` — one of `"spec"` / `"design"` / `"develop"`.
- `status` — `"ok"` when no residual errors remain, `"completed_with_errors"`
  otherwise (previously hard-coded `"ok"`).
- `errors` — list of structured `{field, issue, fix}` dicts surfacing the
  residual deterministic-check failures. Empty when validation passed.
- `items_changed` (design) / `files_changed` (develop) — `{created, updated,
  deleted}` lists derived from `git diff --name-status origin/main`. Item
  IDs are extracted from the YAML stem (`SYS-001` etc.).
- `started_at` (ISO 8601 UTC) and `elapsed_ms` (wall time).

Removed (placeholder fields that always returned `null` / `[]`):
`items_created`, `items_updated`, `files_written`. Use `items_changed.*`
or `files_changed.*` instead.

The `ci design-cr` / `ci develop-cr` / `ci analyze-cr` stderr summaries
now surface correction count, validation outcome, residual error count,
elapsed time, and changed-DHF / changed-files counts via a single shared
formatter.

### New helpers (`medharness.services.git`)

- `collect_path_changes(repo_root, since_ref, *paths)` —
  `{created, updated, deleted}` of file paths.
- `collect_dhf_item_changes(repo_root, since_ref)` — same shape but with
  DHF item IDs extracted from `DHF/items/.../<ID>.yaml`.

### New modules

- `medharness.services.design_validation` — `validate_design(cr_id,
  dhf_path, spec_path) -> list[dict]`
- `medharness.services.code_validation` — `validate_code(cr_id,
  dhf_path, spec_path, since_ref="origin/main") -> list[dict]`

---

## [0.3.4] — 2026-05-09

### Fixes

- `ci artifacts generate` raised `TypeError: sequence item 0: expected str
  instance, dict found` when the JUnit feed populated requirement coverage
  with test entries — `MedHarnessCore.inject_junit_results` stores each test
  as `{"name", "status"}`, but the 0.3.3 PDF formatter joined them as
  strings. The formatter now renders dicts as `"<name> [<status>]"` and
  still accepts plain strings.

---

## [0.3.3] — 2026-05-09

### Features

- `ci artifacts generate` now emits a PDF traceability matrix
  (`Requirements_Traceability_Report.pdf`) alongside the existing JSON report
  when WeasyPrint is installed (`pip install medharness[docs]`). The PDF
  renders the full UC → CRS → SYS → SRS → SWDD chain with per-level coverage
  statistics, per-item verification status, and a JUnit-derived test result
  summary. JSON output is unchanged so compliance gates continue to work.

### Fixes

- `_write_traceability_report` previously discarded the caller-supplied
  `.pdf` extension and wrote JSON only. The path is now honored: a `.pdf`
  output produces a PDF (with JSON written next to it as `.json`).

---

## [0.3.2] — 2026-05-08

### Features

- `ci design-cr` now runs a second LLM pass after DHF item generation to review the output
  against the approved spec. The review is written to
  `docs/cr-specs/<CR_ID>-Design-Review.md` and committed alongside the design artifacts.
- `ci develop-cr` now runs a second LLM pass after code generation to review the
  implementation against the approved spec. The review is written to
  `docs/cr-specs/<CR_ID>-Code-Review.md` and committed with the implementation.
- Both reviews check completeness, traceability, test annotations, and coding conventions.
  They are non-blocking — the stage advances regardless of the verdict.

---

## [0.3.1] — 2026-05-07

### Changes

- `cr_analyze.md`: removed redundant step; analyze phase now identifies DHF items that will
  need creation but does not create them (creation is design phase only)
- `req_manage.md`: removed "do not edit" restriction (skill is also used in design phase);
  added explicit "no change > update > create" preference
- All impact skills (`product_impact.md`, `architecture_impact.md`, `risk_impact.md`,
  `soup_impact.md`, `test_impact.md`): added "no change > update > create" preference
  to Design Updates sections
- Removed `AI-harness` template directory and `.claude/skills` scaffolding from `medharness init`

---

## [0.3.0] — 2026-05-06

### Features

- CI CR lifecycle commands: `ci analyze-cr`, `ci design-cr`, `ci develop-cr` for LLM-driven
  spec generation, DHF design, and code implementation
- Single-repo CR lifecycle: analyze → design → code phases driven by GitHub Actions
- `ci validate-spec` validates spec YAML front-matter (cr_id, direction_fit, affected_items,
  test_plan) with self-correction loop on failure
- `ci dhf-validate` structural gate: schema + traceability checks for CI pipelines
- `ci test-coverage` requirement-to-test coverage gate using JUnit XML evidence
- `ci evidence bundle` and `ci evidence import` for DHF artifact bundling

---

## [0.2.1] — 2026-05-06

### Fixes

- `medharness cr workflow intake-github-issue-ci --open-pr` now passes `--repo`
  explicitly to `gh` PR commands and fails with the actual CLI error when PR
  lookup or creation fails, instead of silently returning an empty `pr_url`

---

## [0.2.0] — 2026-05-05

### Breaking Changes

- `medharness init` now scaffolds into the **current directory** (single-repo layout); the
  separate DHF repo is gone — DHF lives at `DHF/` alongside product source code
- `medharness init` is now **zero-prompt** — no questions about org, repo name, or project name;
  everything is derived from the current directory name
- `_replace_placeholders` no longer accepts a `product_repo` argument
- Generated `cr-complete.yml` uses `GITHUB_TOKEN` only — `DHF_REPO_TOKEN` is no longer required

### Features

- `engineering-control.yml` now has four explicit CI phases: CR validation, DHF schema +
  traceability validation, test coverage gate, evidence bundle (post-merge)
- Test step is language-agnostic with commented examples for pytest, Jest, Maven, and Go;
  only contract is JUnit XML output to `test-results/`
- `.gitignore` is scaffolded automatically

### Changes

- `cr-analyze.yml` and `cr-develop.yml` updated for single-repo: use `github.repository`
  and `GITHUB_TOKEN` instead of cross-repo `PRODUCT_REPO_TOKEN`
- DHF README placed at `DHF/README.md` instead of the repo root
- `AI-harness/context.md` removed from scaffold — `CLAUDE.md` covers the same purpose

### Fixes

- `engineering-control.yml` install step now uses `pip install medharness` (was broken
  `gh release download` with unfilled `{github_org}/{dhf_repo_name}` placeholders)

---

## [0.1.0] — 2026-05-03

### Breaking Changes

- Merged `MedHarness-DHF` into `MedHarness` — single-repo tooling model
- `medharness init` no longer fetches from a remote repo; scaffolds from bundled templates
- `dhfkit` is no longer a separate `pip install dhfkit` package; included in `medharness`
- `medharness init` no longer accepts `--template-ref` (templates are bundled)
- Removed `pip install -e dhf/` dependency from generated CI workflows
- Generated DHF repos no longer contain `dhfkit/`, `pyproject.toml`, or `.github/prompts/`

### Features

- All DHF operations unified under `medharness dhf` (item, validate, doc, test, config, context)
- `dhfkit/templates/` — starter DHF scaffold with 12 sample items
- `docs/architecture.md` — stable architecture documentation
- `docs/adr/` — architecture decision records for major design choices
- Scaffold generates item subdirectories from doc type configs

### Fixes

- Template docs (j2) updated to reflect single-repo model
- Scaffolded GitHub Actions workflows updated for new install flow
- Example project items reflect current architecture
- Removed stale `MedHarness-DHF` references from code, docs, and fixtures

### Migration Notes

See [docs/adr/ADR-001-single-repo-tooling-model.md](docs/adr/ADR-001-single-repo-tooling-model.md) for the migration rationale.

---

## Version History Legend

- **Breaking Changes** — incompatible changes requiring user action
- **Features** — new backward-compatible capabilities
- **Fixes** — bug fixes and corrections
- **Migration Notes** — steps required to upgrade

---

*Changelog format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).*
