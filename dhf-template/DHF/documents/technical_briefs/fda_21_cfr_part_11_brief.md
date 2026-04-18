# Technical Brief: FDA 21 CFR Part 11 Compliance in CompliantFlow

| Field | Value |
|---|---|
| **Document ID** | TB-001 |
| **Title** | FDA 21 CFR Part 11 Electronic Records and Electronic Signatures — GitOps Compliance Analysis |
| **Version** | 1.0 |
| **Date** | 2026-04-06 |
| **Status** | Approved |
| **Prepared by** | CompliantFlow Engineering |
| **Reviewed by** | Quality Assurance |
| **Related CR** | CR-027 |
| **Linked CRS** | CRS-011 |

---

## 1. Purpose and Scope

This brief explains how CompliantFlow satisfies FDA 21 CFR Part 11 requirements for electronic
records and electronic signatures through its GitOps-native architecture. It is intended for
regulatory reviewers, auditors, and customers conducting pre-market submission reviews or supplier
qualifications.

**In scope:** Part 11 Subpart B (Electronic Records §11.10) and Subpart C (Electronic Signatures
§11.50, §11.70, §11.100, §11.200) as they apply to the Design History File (DHF) maintained by
CompliantFlow.

**Out of scope:** Computer system validation (CSV) of the hosting environment, 21 CFR Part 820
quality system requirements (addressed separately), and FDA guidance on Part 11 scope narrowing
(August 2003 guidance).

---

## 2. Background: GitOps as an Electronic Records System

CompliantFlow stores the DHF as YAML files in a Git repository. Every change to any DHF item is a
Git commit. This architecture provides a native audit trail that predates most purpose-built
electronic records systems. The key properties are:

- **Immutability**: A Git commit hash (SHA-256) is a cryptographic content address. Any
  modification to a committed record changes the hash, breaking the chain of custody visibly and
  irrefutably.
- **Attribution**: Every commit carries author name, email, and timestamp recorded at commit time.
- **Completeness**: The full history of every file — including deletions and renames — is preserved
  in perpetuity. There is no "overwrite" operation; prior states are always recoverable.
- **Verifiability**: Any third party with a copy of the repository can independently verify the
  integrity of any record by recomputing the Merkle hash tree.

---

## 3. Part 11 Subpart B — Electronic Records (§11.10)

### 3.1 §11.10(a) — Validation

> *Systems shall be validated to ensure accuracy, reliability, consistent intended performance, and
> the ability to discern invalid or altered records.*

**How CompliantFlow addresses this:**

CompliantFlow ships with a CI/CD pipeline (`.github/workflows/ci-pipeline.yml`) that executes
automated validation on every pull request and merge:

- **Phase 1**: DHF schema validation — every YAML item is validated against its doc-type schema,
  rejecting unknown fields, missing required attributes, and invalid values.
- **Phase 2 & 3**: System and customer-requirements API test suites verify that the software
  correctly reads, writes, and reports DHF records.
- **Phase 4+**: Compliance evidence generation and traceability checks confirm that no orphaned
  records exist and all required policy checks pass.

Validation results are persisted as JUnit XML artifacts and imported back into the DHF
(`DHF/test-results/results.yaml`), creating an auditable record of each validation run linked to
the commit SHA under test.

A Computer System Validation (CSV) package based on GAMP 5 Category 4 (configurable software) is
available on request. The CI test suite constitutes the IQ/OQ evidence base.

### 3.2 §11.10(b) — Audit Trails

> *The ability to generate accurate and complete copies of records in both human readable and
> electronic form.*
>
> *Computer-generated, time-stamped audit trails that independently record the date and time of
> operator entries and actions that create, modify, or delete electronic records.*

**How CompliantFlow addresses this:**

Git's reflog and commit history constitute a continuous, tamper-evident audit trail:

| Audit trail element | Git mechanism |
|---|---|
| Who created/modified the record | `git log --format="%an <%ae>"` (author name and email) |
| When the action occurred | `git log --format="%ai"` (author timestamp, ISO 8601) |
| What changed | `git diff <commit>^..<commit> -- <file>` (exact byte-level diff) |
| Why it changed | Commit message (includes CR ID by policy) |
| Prior value of the record | `git show <commit>^:<file>` (parent commit content) |

The CompliantFlow `cr generate-report` command produces a structured JSON report linking every
commit to its originating Change Request, satisfying the requirement for records of modification
with reason.

**Limitation**: Git author timestamps are set by the client clock and can be manipulated by a
local administrator before pushing. See Section 5.1 for mitigation.

### 3.3 §11.10(c) — Limited System Access

> *Protection of records to enable their accurate and ready retrieval throughout the records
> retention period.*

**How CompliantFlow addresses this:**

Access control is enforced at two layers:

1. **Repository access**: GitHub repository permissions (or equivalent) restrict who can push
   commits. Branch protection rules require pull request review before any change reaches the
   `main` branch (the authoritative DHF state).
2. **Branch protection as approval gate**: The CI Phase 0 gate (`cr check-status`) rejects any
   pull request whose title does not reference an approved Change Request. This ensures every
   modification to the DHF is preceded by a documented, reviewed change request — equivalent to
   the access authorization hierarchy required by §11.10(c).

Role-based access should be configured in the hosting GitHub organization to restrict direct
pushes to `main` to release managers only.

### 3.4 §11.10(d) — Authority Checks

> *Use of authority checks to ensure that only authorized individuals can use the system, change a
> record, or perform the operation at issue.*

**How CompliantFlow addresses this:**

- CR lifecycle transitions enforce field-level authority checks (e.g., the `approved_by` field
  must be populated by a named reviewer before a CR can advance to `approved`).
- The CR YAML captures `approved_by` and `approved_date`, creating a record of the approving
  authority.
- The `implementing` state requires `assigned_to` to be set, tying each implementation to a
  named responsible party.

For strict Part 11 environments, GitHub's required reviewer feature (branch protection → required
reviews) provides an additional automated enforcement layer that records the reviewer's identity
in the pull request audit log.

### 3.5 §11.10(e) — Device Checks

> *Use of device (e.g., terminal) checks to determine, as appropriate, the validity and
> authenticity of the source of data input or operational instruction.*

**How CompliantFlow addresses this:**

Each Git commit is attributed to a specific SSH key or HTTPS credential bound to a GitHub user
account. GitHub enforces that credentials are unique per user and may not be shared. Organizations
using SSO (SAML) or hardware security keys (FIDO2/WebAuthn) bind the credential to a physical
identity provider, satisfying device-check requirements.

GPG-signed commits (see §3.7) provide an additional cryptographic binding between the commit and
the signing key device.

### 3.6 §11.10(f) — Operational Checks

> *Use of operational system checks to enforce permitted sequencing of steps and events.*

**How CompliantFlow addresses this:**

The CR lifecycle state machine enforces sequencing:

```
draft → in_review → approved → implementing → completed
```

The CI pipeline enforces that no merge to `main` can occur without an approved CR (Phase 0) and
passing test suites (Phases 1–4). This mechanically prevents out-of-order execution: code cannot
be merged before a CR is approved, and a CR cannot be marked completed before the implementation
is validated.

### 3.7 §11.10(i) — Determination of Validity

> *Use of appropriate controls over systems documentation.*

**How CompliantFlow addresses this:**

Documentation (plans, specifications, technical briefs) is stored in `DHF/documents/` and is
subject to the same Git history and Change Request workflow as item YAML files. Every document
change requires a CR reference in the commit message, creating a traceability link between
document revisions and the authorizing change request.

---

## 4. Part 11 Subpart C — Electronic Signatures

### 4.1 §11.50 — Signature Manifestations

> *Signed electronic records shall contain information associated with the signing that clearly
> indicates: (1) The printed name of the signer; (2) The date and time when the signature was
> executed; (3) The meaning (such as review, approval, responsibility, or authorship) associated
> with the signature.*

**How CompliantFlow addresses this with GPG-signed commits:**

When committers sign commits with GPG (`git commit -S`):

| §11.50 requirement | Git/GPG mechanism |
|---|---|
| Printed name of signer | GPG User ID (name) embedded in signature; also `git log --format="%GN"` |
| Date and time | Commit timestamp (`git log --format="%ai"`) |
| Meaning / purpose | CR ID in commit message + CR lifecycle state at time of commit |

The `approved_by` and `approved_date` fields in the CR YAML, when committed to `main`,
constitute the approval signature record. The combination of field value + commit signature
satisfies the manifestation requirement.

**For strict environments:** Configure commit message templates that require a `Signed-off-by:
<name> <email> [role: approval|review|authorship]` trailer. This provides a machine-readable
signature purpose record alongside the GPG cryptographic signature.

### 4.2 §11.70 — Electronic Signatures and Electronic Records Linkage

> *Electronic signatures and handwritten signatures executed to electronic records shall be linked
> to their respective electronic records to ensure that the signatures cannot be excised, copied,
> or otherwise transferred to falsify an electronic record by ordinary means.*

**How CompliantFlow addresses this:**

A GPG signature on a Git commit is cryptographically bound to the exact byte content of that
commit object (tree hash, parent hash, message, timestamp, author). It is computationally
infeasible to transfer the signature to a different commit without invalidating it. This provides
a stronger linkage than most purpose-built signature systems, which store signatures in a separate
database field.

The `git verify-commit <hash>` command can be used by any auditor to independently verify the
signature without requiring access to CompliantFlow software.

### 4.3 §11.100 — General Signature Requirements

> *Each electronic signature shall be unique to one individual and shall not be reused by, or
> reassigned to, anyone else.*

**How CompliantFlow addresses this:**

GitHub enforces that each user account has a unique identity. GPG key pairs are unique by
construction (RSA/ECC key generation). Revocation of a key does not transfer its past signatures
to a new key.

### 4.4 §11.200 — Electronic Signature Components and Controls

> *Electronic signatures that are not based upon biometrics shall: (1) Employ at least two
> distinct identification components such as an identification code and password.*

**How CompliantFlow addresses this:**

GitHub's authentication supports two-factor authentication (2FA) via TOTP, SMS, or hardware
security keys (FIDO2). When 2FA is enforced at the organization level, every push requires both a
primary credential (SSH key or password) and a second factor, satisfying the two-component
requirement.

For maximum compliance, organizations should enforce SSH key authentication (something you have)
combined with 2FA (something you know/are) at the GitHub organization level.

---

## 5. Known Gaps and Recommended Mitigations

The following gaps exist between CompliantFlow's GitOps architecture and strict FDA 21 CFR Part 11
requirements. Each gap is accompanied by a recommended mitigation.

### 5.1 Client-Side Timestamp Manipulation

**Gap**: Git author timestamps are set by the committing client. A user with local administrator
access could set their system clock back and create commits with falsified timestamps before
pushing.

**Mitigation**:
- Enable GitHub's server-side timestamp (`committer` timestamp differs from `author` timestamp
  when the server processes the push — the `committer` date is set by the server).
- Use GitHub's commit timestamp API (`/repos/{owner}/{repo}/commits/{sha}`) as the authoritative
  timestamp source in audit reports rather than the author date.
- For critical approval events, record the `approved_date` field in the CR YAML via the
  `utils item update` command executed in CI (not locally), ensuring a server-enforced timestamp.

### 5.2 GPG Key Management Infrastructure

**Gap**: GPG-signed commits require each user to maintain a GPG key pair, register the public key
with GitHub, and protect the private key. Without a key management policy, keys may be lost,
stolen, or shared, undermining the signature non-repudiation property.

**Mitigation**:
- Publish a GPG Key Management Procedure in the QMS requiring unique keys per individual, hardware
  security key storage (e.g., YubiKey), annual key rotation, and immediate revocation upon
  personnel change.
- Enforce GPG signing via the repository `commit.gpgsign = true` setting in the organization-level
  Git configuration.
- Log key fingerprints and their associated personnel in a key registry maintained by IT/Security.

### 5.3 Signature Purpose Record

**Gap**: Part 11 §11.50(a)(3) requires the signature to convey its meaning (review, approval,
authorship). A plain GPG-signed commit does not structurally encode this information.

**Mitigation**:
- Adopt a commit message convention that includes a `Signed-off-by:` trailer with a role
  qualifier (e.g., `Signed-off-by: Alice <alice@org.com> [role: approval]`).
- Alternatively, the CR YAML `approved_by` field committed to `main` by the approver's credentials
  constitutes an approval signature with named author and timestamp. Document this interpretation
  in the SOP and QMS.

### 5.4 Closed vs. Open System Classification

**Gap**: Part 11 §11.10 applies to closed systems; §11.30 applies to open systems. A
cloud-hosted Git repository (e.g., GitHub.com) may be classified as an open system by an auditor
because the operator does not control the physical infrastructure.

**Mitigation**:
- For strict Part 11 environments, deploy CompliantFlow with a self-hosted Git server
  (Gitea, GitLab CE) on infrastructure the organization controls.
- For GitHub.com deployments, document the open-system risk acceptance and the additional controls
  applied (encryption in transit, encrypted at rest, SOC 2 Type II audit reports available from
  GitHub, data processing agreements).
- Reference FDA's August 2003 Part 11 scope guidance, which narrows enforcement to records
  required by predicate rules where the agency intended an electronic format requirement — not
  all electronic records.

### 5.5 Biometric Signatures (§11.300)

**Gap**: Part 11 §11.300 requires that biometric electronic signatures ensure uniqueness and
prevent their use by anyone other than the genuine owner. CompliantFlow does not implement
biometric authentication.

**Mitigation**: Biometric signatures are not required; they are one option among non-biometric
(credential-based) alternatives under §11.200. Compliant credential-based signatures (SSH key +
2FA) are the recommended path for CompliantFlow deployments.

---

## 6. Summary Compliance Matrix

| Part 11 Requirement | CompliantFlow Mechanism | Gap | Mitigation Required |
|---|---|---|---|
| §11.10(a) Validation | CI pipeline + test suites | None | No |
| §11.10(b) Audit trail | Git commit history + CR report | Timestamp manipulation | Yes (§5.1) |
| §11.10(c) Access control | Branch protection + CR gate | Requires org configuration | Yes (setup) |
| §11.10(d) Authority checks | CR approved_by field + lifecycle | None | No |
| §11.10(e) Device checks | SSH key / GPG key binding | GPG key management | Yes (§5.2) |
| §11.10(f) Operational checks | CR lifecycle state machine | None | No |
| §11.10(i) Documentation | Git history for docs/ | None | No |
| §11.50 Signature manifestation | GPG commit + approved_by | Signature purpose | Yes (§5.3) |
| §11.70 Signature linkage | GPG cryptographic binding | None | No |
| §11.100 Signature uniqueness | GitHub unique identity | None | No |
| §11.200 Two-factor auth | GitHub 2FA enforcement | Requires org configuration | Yes (setup) |
| §11.300 Biometric | Not applicable (credential path) | None | No |

---

## 7. Conclusion

CompliantFlow's GitOps architecture satisfies the substantive requirements of FDA 21 CFR Part 11
for electronic records and electronic signatures when deployed with the recommended organizational
controls (branch protection, GPG signing, 2FA enforcement, and a GPG key management procedure).
The audit trail provided by Git's cryptographic commit chain is technically superior to most
purpose-built electronic records systems in terms of tamper-evidence and verifiability.

The gaps identified in Section 5 are addressable through organizational policy and deployment
configuration rather than product changes. A regulatory consultant engagement to review the
deployment-specific controls against a customer's Part 11 SOP is recommended prior to any
FDA submission that cites CompliantFlow as a predicate-rule electronic records system.

---

*This document is part of the CompliantFlow Design History File and is subject to change control
under CR-027.*
