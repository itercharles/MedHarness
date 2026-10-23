# ADR-004: Signed Approvals of DHF Content

**Status:** Proposed
**Date:** 2026-10-22

## Context

Iteration 3 of the [charter](../charter.md) asks how a person's approval becomes a
compliant review record. Until now MedHarness has said that approval is not a command:
GitHub's branch protection enforces it, and no check reads GitHub
([interface.md](../interface.md), [ai-security.md](../ai-security.md)).

The inventory found that this does not hold up:

- **Approval is outside the DHF.** It lives only in GitHub reviews. The release evidence
  bundle carries no approval record, so retention depends on the hosting vendor.
- **In practice it is mostly absent.** Of the last 100 pull requests merged in the
  reference project, 95 merged with no standing approval (admin bypass). In the CI
  pipeline a design approval is dismissed when the code is pushed, so the code merges
  unapproved. In local mode the maintainer authors the pull request, and GitHub does
  not let an author approve their own.
- **An approval says nothing about its meaning.** It does not say whether a design,
  code or a release was approved, which items were reviewed, or with what result.
- **It is not an electronic signature.** Approving does not re-authenticate the signer,
  states no meaning, and does not live in the record it approves.
- **Its identity is within an agent's reach.** A CI job that checks out with a personal
  access token leaves that token where the agent runs, and the agent can then approve
  as that person.
- **State changes carry no identity.** A CR moved to `completed`, or a REL moved to
  `approved`, records only the new status.

The charter's lesson from iteration 2 applies here: **a field an agent can write is not
an approval.** That is why the `triage_result` gate was removed (#454) and why a CR
marked rejected no longer escapes the impact checks (#455).

Two requirements shape the decision. A controlled document is approved by a designated
function before it is issued (ISO 13485 §4.2.4), so the unit of approval is the item,
not a stage of the work. A change request is approved by a change control board before
it is implemented (IEC 62304 §8.2, ISO 13485 §7.3.9).

## Decision

### What is approved: an item version, by the role that owns its type

The unit of approval is the **current content of one DHF item**. An approval binds to
a hash of the item's content, so when the item changes the approval no longer covers it
and that item alone needs approving again.

Which role approves which item type is set in `global.yaml`, with a default such as:

| Item type | Approving role |
|---|---|
| UC, CRS | Product manager |
| SYS, SYSARCH | System architect |
| SRS, SWDD, MODULE, SOUP | Software lead |
| RISK, RCM | Risk manager |
| CR | Change control board (CCB) |
| REL | Quality lead |

A CR's own content is approved by the CCB. When its status moves to `develop`, the CCB
accepts the change; when it moves to `completed`, the CCB closes it. A status change is
an edit to the CR item, so it needs the CCB's signature like any other edit. Rejection
and cancellation are CCB decisions in the same way.

### Code is not approved here

Code changes are reviewed through the hosting platform's own review (a GitHub approval),
under rules the team sets. MedHarness does not check, export or vouch for code review.
Its concern with code is only that the code follows an approved design: the code's
modules, through MODULE `paths` (#453), reach items in the CR's plan.

### How an approval is recorded: a signed log beside the items

An approval is a **signed record in an append-only log**, `DHF/approvals/`, kept apart
from the items. Records are grouped by the CR they were given in, and each is named by a
ULID:

```yaml
# DHF/approvals/CR-027/01JB3KQ7Z8X4M2N5P6R7S8T9VA.yaml
id: 01JB3KQ7Z8X4M2N5P6R7S8T9VA
cr: CR-027
signer: Charles Chen
roles: [software-lead, ccb]
signed_at: 2026-10-22T09:30:00Z
statement: I have reviewed these items and approve them as written.
items:
  - {id: SRS-012, hash: <content hash>}
  - {id: CR-027, hash: <content hash>, meaning: accept}
key: SHA256:<public key fingerprint>
```

The signature (`<ULID>.yaml.sig`) is made with `ssh-keygen -Y sign` over the record
file's bytes, so the signer, roles, items, hashes and key are all covered. OpenSSH is
the only dependency, and git already uses this signature format.

- **The hash is of the item's content**, not of a commit, so a squash merge leaves it valid.
- **Approvals are not items.** They are records about items. The item store never loads
  them, so every other command costs the same however many approvals accumulate. Only
  `verify approval`, `item approve` and `build release` read the log.
- **Records are named by ULID, not by a sequence.** Many approvals are written in
  parallel branches, and a sequential ID would collide on merge. A ULID sorts by time and
  never collides.
- **Records are grouped by CR.** A CR's approvals read together, and no directory grows
  without bound. An approval not given within a CR (the approvers list, or approving an
  existing DHF on adoption) goes under `DHF/approvals/unscoped/`.
- **Approvals are append-only.** A branch that modifies or deletes an existing record or
  signature fails `verify approval`, which reads the branch's diff (`verify dhf` does not).
  A superseded approval stays as history: the CCB's acceptance, signed before the code
  was written, is still there after the CR is closed.
- **A record holds hashes, not content.** If an item is approved, edited and approved again
  within one pull request that is squash-merged, the first version never reaches the main
  line, and the first record points at content that is no longer kept. The approval that
  counts is the last one; the earlier one is a draft's.

### Who may sign: the approvers list

`DHF/config/approvers` lists each person with their roles and public keys. It guards
every other approval, so it gets its own rules:

- **A change to the list must be approved by someone already on it.** An agent that adds
  its own key cannot produce that approval, and the check fails.
- **The first list is a stated root of trust.** It has no earlier signer, and the
  release evidence says so.
- **Each release pins the list.** The evidence bundle records the list and every key's
  fingerprint, so an auditor sees who could approve at each release.

### Signing keys must need a person present

An agent working locally runs as the user and can reach the user's ssh-agent. A key that
is already unlocked would sign silently. So:

- **The intended default is a hardware key with touch** (`sk-ssh-ed25519`). Its signature
  carries a user-presence flag. OpenSSH's allowed_signers file has no option to require
  that flag (`no-touch-required` belongs to sshd's authorized_keys and is rejected here),
  so proving presence means reading the flag from the signature ourselves. That is not
  done yet; see the open questions.
- **Until then, presence is declared, not proven.** An approver marked
  `no_touch_required` in the approvers list makes approvals that are reported as made
  without proven presence. Other approvers' keys are trusted to require touch, and
  nothing checks it.

### Commands

- **`medharness item approve`** (proposed): lists the items the signer's roles may
  approve that lack a current approval, shows each change, and on confirmation writes
  a record and its signature in the approval log. One statement can cover many items and roles, so
  one touch approves a whole review. `--cr` narrows it to one change request.
- **`medharness verify approval`** (proposed): offline and in the usual envelope. It
  checks every signature, every signer against the approvers list for the role the item
  needs, every hash against the item's current content, and whether each changed item
  has a current approval. It names what is missing and who may approve it.

### Where it blocks, and where it only reports

- **During a CR it never blocks.** CR transitions, `verify impact` and `verify completion`
  do not depend on approvals. Run locally, `verify approval` reports what is pending.
- **Merging blocks.** CI runs `verify approval`: every DHF item the pull request changes
  must carry a current approval from its role.
- **A release blocks.** `build release` re-checks every item in the baseline, refuses
  while any CR with merged changes is not `completed`, and needs a REL approval from the
  quality lead. An approval skipped by an admin bypass at merge is caught here.
- **Off until configured.** Without `DHF/config/approvers`, nothing changes for existing
  projects.

### At scale

A CR can need ten approvals, and a large team may close tens of CRs a day: about fifty
thousand records a year. Two rules keep the cost from following that growth.

- **A check verifies only the candidates** (phase 2). `verify approval` first reads each
  record's item IDs and hashes, without checking signatures, which is cheap. It then
  verifies signatures only for records the branch adds, and for records whose hash
  matches the current content of an item in scope, stopping at the first valid one. A
  record whose hash is stale cannot cover anything and is not verified. A pull request's
  cost then follows the number of items it changes, not the size of the log.
  `--all` and `build release` still verify every record.
- **A release is a checkpoint** (phase 2). `build release` writes an approval manifest,
  signed by the quality lead: for each item in the baseline, the record that covers its
  current version. Records superseded before that release may then leave the working
  tree; they remain in git history and in the release evidence. The next release checks
  the records since the last checkpoint against that manifest. Append-only becomes:
  **never modified, and removed only once a signed checkpoint holds them.**

### One pull request may carry both design and code

DHF and code changes may share a pull request. Each part is approved by its own owner:
items by signature, code by platform review. Pushes that change only code leave the
items' approvals valid. A team that wants the design merged before any code may split
the two into separate pull requests. The rules are the same either way.

"Approved before implemented" is then shown by the record, not enforced by ordering: the
CCB's acceptance and the items' approvals keep their signing time after a squash merge.
Signing times and commit times come from machines a person controls, so MedHarness
reports them and does not gate on them.

## Typical workflow

A three-person team: a developer working with an AI agent, a software lead, and a product
manager who also manages risk. The lead and the product manager form the CCB.

1. **Design (developer and agent, minutes).** The developer opens `feat/CR-027` and creates
   the CR. `build plan --prompt` has the agent write the impact analysis and change SRS-012.
   `verify dhf` and `verify impact` pass.
2. **See what needs signing (one command).** `verify approval --cr CR-027` lists CR-027
   for the CCB, SRS-012 for the software lead, and RCM-004 (reviewed, unchanged) for the
   risk manager. The developer pushes a draft pull request and asks them.
3. **Code (developer and agent, not waiting).** `build code --prompt`, tests, many pushes.
   None of them invalidates an approval.
4. **Sign (each signer, when free).** The lead checks out the branch and runs
   `item approve --role software-lead`, reads the changes, touches the key, and pushes.
   The lead also signs CR-027's acceptance as CCB. The product manager does the same for
   RCM-004.
5. **The design changes mid-way.** The agent amends SRS-012 for a missed case.
   `verify approval` at once shows SRS-012's approval as stale; the lead re-signs that
   one item.
6. **Code review.** A teammate approves on GitHub, under the team's rules.
7. **Close and merge.** The developer moves CR-027 to `completed` and runs
   `verify completion`. The CCB signs the closed CR, CI passes and the pull request merges.
   The acceptance signed in step 4 remains in the DHF.
8. **Release.** `build release` re-checks every approval and open CRs; the quality lead
   signs the release.

Merging is the only point where work waits on people. A small change needs one round of
signatures, and a design change mid-way adds one more, for the changed item alone.

A team of one holds every role. `item approve --cr CR-027` signs everything pending in one
touch. The record states that one person gave every approval, and the release evidence
shows it.

The agent can run `verify approval` and see what is pending or what its own edit made
stale. It cannot sign. Its instructions should say that changing a signed item means
explaining the change in the pull request, so the signer can review it quickly.

## Alternatives considered

- **Keep GitHub reviews as the record, and import them into the release evidence.** This
  keeps the current flow and records the reviews. But it needs GitHub at release time,
  cannot record approvals in local mode where the author cannot approve, and keeps
  identity as safe as the least protected token on the account.
- **Approvals as DHF items, with sequential IDs.** This was the first implementation.
  Every command loads every item, so a growing log slowed everything, and parallel
  branches allocated the same ID.
- **Signed git tags on approved commits.** These are native to git, but squash merging
  means the approved commit is never on the main line.
- **Stage gates within a CR** (approve design before code, then approve code). This
  blocks development on reviewers, and it ties approval to the workflow rather than to
  the content that is controlled.
- **A separate pull request for every DHF change.** This gives the strongest proof that
  design came before code, at the cost of two or three pull requests per CR. It remains
  available to a team that wants it.

## Consequences

- **It reverses "approval is not a command".** CLAUDE.md, interface.md and ai-security.md
  (the human control points and audit trail) are updated when this is implemented. The
  checks still read only the machine.
- **The CLI's four groups stay.** `item approve` writes a record, like `item create`;
  `verify approval` judges, like the other checks.
- **New pieces:**
  - in dhfkit, the approvers list format and its loading; approvals are not an item type;
  - in medharness, the approval log, the two commands, and a `global.yaml` role matrix;
  - in releases, approvals and the approvers list go into the evidence bundle;
  - in `cr.yaml`, transitions need nothing new, because a status edit is approved like
    any other edit.
- **A new external dependency on OpenSSH:** 8.0 for `-Y sign`, 8.2 for hardware keys. It
  falls under iteration 4, tool validation.
- **Approval by people becomes visible work.** The pending list makes the backlog
  explicit, and the release gate stops it piling up silently. Signers need the
  command line, a key and a checkout, which is a burden for roles that rarely use git.
- **Scope stays inside the charter.** It covers approval of DHF content and of CR decisions.
  Training records, role qualification and SOPs are eQMS concerns and stay out.
- **What it does not fix:**
  - **One person holding every role.** It is recorded, not prevented.
  - **Platform hygiene.** Tokens available to agent jobs, and admin bypass of branch
    protection, remain the team's to fix. The release gate limits the damage.

## Open questions

1. **The content hash.** The first implementation uses the SHA-256 of the item file's bytes:
   simple, and needs no git, but any reformatting invalidates approvals. A normalised form
   of the fields is the alternative.
2. **Reviewed items.** A CR's `reviewed_items` are unchanged, so they need no new approval.
   Should their owners confirm the "still holds" judgement? If so, it is a CR-level
   confirmation, not an item approval.
3. **Presence verification.** OpenSSH's allowed_signers cannot require the user-presence
   flag. Proving presence means decoding the SSHSIG signature and reading the flags of an
   `sk-` key's signature, checked with a real hardware key and pinned in a test.
6. **Approvers who leave.** Removing a key from the list makes every approval it signed
   invalid, and approvals are append-only, so `verify approval` would fail for good. The
   list needs revoked keys that still verify past approvals but cannot make new ones.
4. **Markets.** Whether the target markets include the FDA decides whether Part 11 is a
   requirement or a margin. It affects how strictly key presence and signature meaning
   are enforced.
5. **The clause on change approval.** Confirm against the text of IEC 62304 §8.2 and
   ISO 13485 §7.3.9 that a CCB acceptance recorded on the CR before its code, and shown
   rather than enforced, satisfies "approved before implemented".
