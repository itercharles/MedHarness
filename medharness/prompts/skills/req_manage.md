# Requirements Management

Use this guidance during CR analysis and CR design to evaluate requirement
coverage and traceability. During analysis, identify which CRS, SYS, SRS, and
SWDD items need to be created or updated, and document them in the spec.
During design, create or update those items with correct traceability.

## Change Preference

**For every item type, always prefer: no change > update > create.**

Before touching any item, ask:
1. Does an existing item already cover this need? → make no change, just reference it.
2. Can an existing item be extended or clarified to cover this need? → update it.
3. Only if neither applies → create a new item.

This minimises DHF churn and keeps the item count stable.

## Requirement Hierarchy

```
UC (Use Case)
  └─ CRS (Customer Requirement)     derives_from: [UC-xxx]
       └─ SYS (System Requirement)  satisfies: [CRS-xxx]
            └─ SRS (Software Req.)  derives_from: [SYS-xxx]
                 └─ SWDD (Design)   implements: [SRS-xxx]

RISK                                related_requirements: [SYS-xxx]
  └─ RCM (Risk Control Measure)     mitigates: [RISK-xxx]
       └─ implements: [SYS-xxx]     (risk control implemented through SYS)

SOUP                                used by SRS items via uses_soup: [SOUP-xxx]
```

Rules:
- Every CRS must derive from at least one UC
- Every SYS must satisfy at least one CRS
- Every SRS must derive from at least one SYS
- Every SWDD must implement at least one SRS
- RISK.related_requirements must reference SYS items (not SRS)
- RCM.mitigates must reference RISK items
- Every SYS must satisfy at least one CRS — including infrastructure SYS items;
  if no existing CRS fits, create a new CRS (e.g. CRS-010 for system reachability)

## Item ID Naming

| Type   | Prefix | Directory             |
|--------|--------|-----------------------|
| UC     | UC-    | DHF/items/00_uc/      |
| CRS    | CRS-   | DHF/items/01_req_crs/ |
| SYS    | SYS-   | DHF/items/02_req_sys/ |
| SRS    | SRS-   | DHF/items/03_req_srs/ |
| SWDD   | SWDD-  | DHF/items/05_swdd/    |
| RISK   | RISK-  | DHF/items/12_risks/   |
| RCM    | RCM-   | DHF/items/13_rcm/     |
| SOUP   | SOUP-  | DHF/items/11_soup/    |

Assign the next sequential number within each type.

## When to Create Items

| Trigger                          | Minimum items to create or update          |
|----------------------------------|--------------------------------------------|
| New user-facing feature          | UC → CRS → SYS → SRS (in order)           |
| New SOUP dependency              | SOUP item + uses_soup on affected SRS      |
| New identified hazard            | RISK → RCM → link RCM to SYS              |
| Architecture decision            | SYSARCH + update affected SRS derives_from |
| CR implemented                   | Transition CR status to completed          |

## Requirements Quality Rules

Apply these rules to every item you create or modify:

| Rule | What it means |
|---|---|
| **No conflict** | Must not contradict any existing item at the same or adjacent level. If a conflict exists, resolve it by updating the conflicting item. |
| **Clear hierarchy** | Each item must be a proper specialisation of its parent — more specific, never a generalisation. Do not skip levels (e.g. SRS cannot link directly to UC). |
| **Atomicity** | One requirement per item. Do not combine multiple requirements with "and" or list multiple acceptance criteria under a single ID. |
| **Verifiability** | Every requirement must be testable. Avoid vague terms: "fast", "easy", "appropriate", "sufficient". State a concrete, measurable criterion. |
| **No duplication** | Before creating a new item, check whether an existing item already covers the same need. If so, update it rather than adding a new one. |
| **Downward completeness** | The set of child items should together fully address the parent intent — not just partially. |

## Creating Items via CLI

**Always use the CLI — do not write YAML files directly.**

```bash
# Create a new item
python -m medharness --dhf DHF dhf item create \
  --type <TYPE> \
  --data '<JSON>' \
  --author "github-actions[bot]" \
  --cr "<CR_ID>"

# Update an existing item
python -m medharness --dhf DHF dhf item update <ITEM_ID> \
  --data '<JSON>' \
  --author "github-actions[bot]" \
  --cr "<CR_ID>"
```

IDs are assigned by medharness on creation.

## Item Field Reference

### UC
```json
{ "title": "<verb phrase describing the user goal>",
  "content": "<narrative: actor, preconditions, numbered primary flow, postconditions>" }
```

### CRS
```json
{ "title": "<user group> shall <observable behavior>",
  "content": "As a <role>, I need to <capability> so that <outcome>.",
  "user_group": "<role>",
  "derives_from": ["UC-NNN"],
  "priority": "Critical | High | Medium | Low" }
```

### SYS
```json
{ "title": "System shall <system-boundary behavior>",
  "content": "<precise system-level behavioral description — independent of implementation>",
  "category": "Functional | Performance | Security | Usability | Reliability | Maintainability",
  "verification_method": ["Test"],
  "critical_safety": false,
  "satisfies": ["CRS-NNN"] }
```

### SRS
```json
{ "title": "Software shall <software-level behavior>",
  "content": "<precise software implementation requirement>",
  "derives_from": ["SYS-NNN"],
  "verification_method": ["Test"],
  "critical_safety": false }
```

## Design Workflow

1. **Check existing coverage** — run `python -m medharness --dhf DHF dhf item list --type <TYPE>` for each relevant type
2. **Check for conflicts and duplicates** — read existing items before writing anything
3. **List gaps** — identify missing UC, CRS, SYS, or SRS items
4. **Apply change preference top-down** — UC first, then CRS, then SYS, then SRS; for each: no change > update > create; apply quality rules
5. **Validate schema** — run `python -m medharness --dhf DHF dhf validate schema`
6. **Validate traceability** — run `python -m medharness --dhf DHF dhf validate traceability`; fix orphans or uncovered pairs, repeat until clean
