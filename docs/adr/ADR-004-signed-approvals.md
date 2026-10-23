# ADR-004: Signed Approval of Released Documents

**Status:** Proposed
**Date:** 2026-10-23

## Context

Iteration 3 of the [charter](../charter.md) asks how a person's approval becomes a
compliant review record. Until now MedHarness has said that approval is not a command:
GitHub's branch protection enforces it, and no check reads GitHub
([interface.md](../interface.md), [ai-security.md](../ai-security.md)).

The inventory found that this does not hold up as release evidence:

- **Approval is outside the DHF.** It lives only in GitHub reviews. The release evidence
  bundle carries no approval record, so retention depends on the hosting vendor.
- **In practice it is mostly absent.** Of the last 100 pull requests merged in the
  reference project, 95 merged with no standing approval (admin bypass). In local mode the
  maintainer authors the pull request, and GitHub does not let an author approve their own.
- **An approval says nothing about its meaning,** and it is not an electronic signature:
  it does not re-authenticate the signer and does not live in the record it approves.
- **Its identity is within an agent's reach.** A CI job that checks out with a personal
  access token leaves that token where the agent runs.

The charter's lesson from iteration 2 applies: **a field an agent can write is not an
approval** (#454, #455).

The design went through two earlier drafts, both signing each DHF item as it changed,
with the approval checked at merge. Working through a team's day showed the cost. A CR
can need ten signatures. A shared item is re-signed after every merge that touches it.
A large team writes tens of thousands of records a year. Development waits on signers
at every merge.

What the requirements actually ask is narrower. A controlled document is reviewed and
approved by a designated function **before it is issued** (ISO 13485 §4.2.4). For
software, a document is issued when it is released. A change is reviewed and approved
before it is implemented (IEC 62304 §8.2, ISO 13485 §7.3.9). That is a review of the
change, which a pull-request review records.

## Decision

### During development: pull-request review only

Every change, to the DHF or to code, is reviewed in its pull request under rules the team
sets. That includes accepting and closing CRs, which the change control board (CCB) does
by reviewing the pull request. MedHarness neither checks nor exports these reviews, and
nothing a developer does between releases waits on a signature.

The gates that exist today, `verify dhf`, `impact`, `changes`, `tests` and `completion`,
are unchanged.

### At release: each document is signed by the role that owns it

A release is made by a pipeline started on purpose, never by a merge. In the reference
project that is `release-baseline.yml`, run by hand. A merge to main only builds a
preview bundle and deploys to a test environment. The release produces one specification
per item type, and each is signed by the role that owns that type, set in `global.yaml`:

| Specification (item type) | Signing role |
|---|---|
| UC, CRS | Product manager |
| SYS, SYSARCH | System architect |
| SRS, SWDD, MODULE, SOUP | Software lead |
| RISK, RCM | Risk manager |
| The release as a whole | Quality lead |

A type with no role needs no signature, for example CR, DEF or REL.

### What is signed: a release manifest, not the rendered file

`build release` writes `DHF/releases/<version>/manifest.yaml`:

```yaml
version: 1.4.0
dhf_hash: sha256:<over every item's content hash, sorted by id>
documents:
  SRS:
    file: specifications/SRS.html
    file_hash: sha256:<bytes of the rendered file>
    items:
      - {id: SRS-001, hash: sha256:<item file bytes>}
      - {id: SRS-012, hash: sha256:<item file bytes>}
    hash: sha256:<over this entry's item hashes>
```

A document's `hash` is computed over the items it contains, not over the rendered file,
because rendering is not byte-stable (fonts, timestamps). Signing a document therefore
means "this specification consists of these versions of these items". The rendered
file's hash is recorded alongside, so the PDF or HTML an auditor reads traces to the
signed entry.

`build release` also writes `DHF/releases/<version>/changes.md`, which lists for each
document what changed since the previous release's manifest: items added, modified and
removed, with the CRs that changed them. **The signer reviews the changes and signs the
whole document.** Nobody rereads a full specification at each release.

### How a signature is recorded: a signed log

A signature is a record in an append-only log, `DHF/approvals/release-<version>/<ULID>.yaml`,
with `<ULID>.yaml.sig` beside it, made by `ssh-keygen -Y sign` over the record's bytes:

```yaml
id: 01JB3KQ7Z8X4M2N5P6R7S8T9VA
release: 1.4.0
signer: Charles Chen
roles: [software-lead]
signed_at: 2026-10-23T09:30:00Z
statement: I have reviewed the changes to these documents and approve them for release.
documents:
  - {id: SRS, hash: sha256:<the manifest entry's hash>}
  - {id: SWDD, hash: sha256:<...>}
key: SHA256:<public key fingerprint>
```

The quality lead's record names `{id: release, hash: <sha256 of manifest.yaml>}`.

- **Records are not items.** The item store never loads them.
- **Records are named by ULID,** so records made in parallel never collide.
- **Records are append-only.** A branch that modifies or deletes an existing record or
  signature fails `verify approval`.
- **One signer, one touch.** A record covers every document the signer's roles sign for
  that release.

### Who may sign: the approvers list

`DHF/config/approvers.yaml` lists each person with their roles and public keys.

- **A change to the list must be approved by someone already on it,** in a record that
  names `{id: approvers, hash: <the new file's hash>}`, signed by a key on the list as it
  was at the ref. An agent that adds its own key cannot produce that record.
- **The first list is a stated root of trust.** The release evidence says so.
- **Each release pins the list.** The manifest records the list's hash, and the evidence
  bundle carries every key's fingerprint.

### Signing keys must need a person present

An agent working locally runs as the user and can reach the user's ssh-agent.

- **The intended default is a hardware key with touch** (`sk-ssh-ed25519`). Its signature
  carries a user-presence flag. OpenSSH's allowed_signers file has no option to require
  that flag, so proving presence means reading it from the signature ourselves. That is
  not done yet.
- **Until then, presence is declared, not proven.** A signature from an approver marked
  `no_touch_required` is reported as made without proven presence.

### Commands and the release flow

1. **The release pipeline runs `build release --version V ... --write`.** It runs today's
   checks, writes the manifest and the change report, and records the REL item as `draft`.
   The pipeline opens a release pull request with them.
2. **Each signer runs `medharness item approve --release V --key <KEY>`.** It shows the
   change report for the documents the signer's roles cover, asks for confirmation, and
   writes and signs one record. The signer, or anyone else, commits it to the release
   branch. The record proves itself, so who commits it does not matter.
3. **The release pull request's CI runs `medharness verify approval --release V`.** Every
   document in the manifest must carry a valid signature from its role over its current
   hash, and the release must carry the quality lead's. The manifest must also still
   match the DHF: an item edited after the manifest was written fails here. REL items
   are left out of the manifest, because a REL is the record of the release and moves
   through its states after the signatures. The check judges the tree it runs on, so it
   belongs on the release pull request. Re-verifying a past release means checking out
   that release's commit.
4. **The release pull request merges,** and the REL item moves on, as today.

Without `--release`, `verify approval` checks only that the log is sound: every
signature, the append-only rule, and the approvers list's guard. It runs on any pull
request and never asks for a signature. Without `DHF/config/approvers.yaml`, approvals
are off and nothing changes for existing projects.

### Evidence is kept for the life of the device

The manifest, the change report and the signature records are committed to the DHF, so
they live as long as the repository. The rendered documents are attached to the release.
The reference project uploads them as a workflow artifact kept for 90 days, which is not
enough. The project's pipeline must keep them durably, for example as release assets or
in the repository, and `file_hash` in the manifest lets anyone check the copy they hold.

## Typical workflow

A small team: developers working with AI agents, a software lead, a product manager who
also manages risk, and a quality lead.

- **Every day.** Developers open CRs, design, code and merge through pull requests. They
  review each other, and the CCB reviews the CR's acceptance and closure. Nothing waits
  on a signature.
- **At release.**
  1. The quality lead runs the release pipeline for 1.4.0, which opens the release pull
     request with the manifest and `changes.md`.
  2. The software lead runs `item approve --release 1.4.0`, reads the changes to SRS, SWDD
     and MODULE, touches the key, and pushes.
  3. The product manager does the same for CRS and the risk documents.
  4. The quality lead signs the release.
  5. CI passes and the release pull request merges.
- **A late fix.** A defect found while signing is fixed in an ordinary pull request. The
  release pipeline then runs again, the manifest changes, and the affected documents are
  signed again.

A team of one holds every role, and `item approve --release V` signs everything in one
touch. The release evidence shows that one person gave every signature.

## Alternatives considered

- **Sign each DHF item as it changes, checked at merge.** These were the first two drafts
  of this ADR, and a first implementation. They were dropped for the cost described in
  the context, and because the requirement is approval before issue, not at every change.
- **GitHub reviews as the record, imported into the release evidence.** It needs GitHub
  at release time, cannot record approvals in local mode, and its identity is only as safe
  as the least protected token on the account.
- **Sign the rendered PDF.** Rendering is not byte-stable, so the same content would not
  reproduce the signed bytes.
- **A CCB signature on each CR's acceptance.** This was dropped as well: the team records
  the change review in the pull request.

## Consequences

- **"Approval is not a command" is narrowed, not reversed.** It still holds during
  development. Release approval becomes a command and a check. CLAUDE.md, interface.md
  and ai-security.md are updated when this is implemented, and the checks still read
  only the machine.
- **The CLI's four groups stay.** `item approve` writes a record and `verify approval`
  judges.
- **Few records.** About one per signer per release, so no indexing or checkpointing is
  needed.
- **Change approval rests on pull-request review.** Whether that review happened is the
  team's to show. It carries the weaknesses found in the inventory (admin bypass, tokens
  within an agent's reach). The release signatures limit the damage: every change reaches
  a signer through `changes.md` before it is issued.
- **A new external dependency on OpenSSH:** 8.0 for `-Y sign`, 8.2 for hardware keys. It
  falls under iteration 4, tool validation.
- **Scope stays inside the charter.** Training records, role qualification and SOPs are
  eQMS concerns and stay out.

## Open questions

1. **Presence verification.** Decode the SSHSIG signature and read the flags of an `sk-`
   key's signature, checked with a real hardware key and pinned in a test.
2. **Approvers who leave.** Removing a key from the list would invalidate the signatures
   it made in past releases. The list needs revoked keys that still verify the past but
   cannot sign anew.
3. **The first release.** There is no previous manifest, so `changes.md` lists every item
   as added, and the first signature covers each document in full.
4. **Markets.** Whether the target markets include the FDA decides whether Part 11 is a
   requirement or a margin.
5. **Change approval.** Confirm against IEC 62304 §8.2 and ISO 13485 §7.3.9 that a
   pull-request review, kept by the team, satisfies "approved before implemented" for an
   auditor.
