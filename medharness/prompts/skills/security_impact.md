# Security Impact

Use this guidance during CR analysis and CR design when a change may affect
cybersecurity posture, data protection, or threat surface of the medical device
software (FDA 2023 Cybersecurity Guidance, IEC 81001-5-1, AAMI TIR57).

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- `DHF/documents/plans/risk_management_plan.md`
- Risk items and SOUP items (see Type Registry — `risk` and `soup` roles)
- Relevant system and software requirement items when applicable

## Analysis

Check whether the CR:
- Changes network communication, API endpoints, authentication, or
  authorization flows.
- Introduces or modifies handling of PHI, PII, or other protected data.
- Adds, removes, or upgrades an external dependency with security implications
  (SOUP item).
- Introduces new user-input, file-import, or data-ingestion paths that could
  be exploited.
- Changes encryption, key management, or secrets handling.
- Introduces client-side storage of sensitive data or changes session
  management.
- Requires SBOM (Software Bill of Materials) updates.
- Triggers threat modeling review for a new or changed data flow.

## Output

Return a concise security impact entry:

```markdown
Security: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <risk / SOUP / system requirement item IDs or "None">
Recommended action: <none, update threat model, update SBOM, create risk item,
  or consult security during design>
```

For purely visual, localization, or documentation changes that do not alter
data flows, authentication, or dependency security posture, use `Not required`.

## Design Updates

When the approved spec requires security changes. Prefer no change > update > create.
- Update or create **risk items** for security-related hazards (see Type Registry
  — `risk` role).
- Update **SOUP items** when third-party dependencies change with security
  implications (see Type Registry — `soup` role).
- Do not create standalone security DHF items unless the project config
  defines a security document type.
- Flag items that require security review before approval so the reviewer
  gate can surface them.
