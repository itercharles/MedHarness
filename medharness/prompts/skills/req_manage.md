# Requirements Management

Use this guidance during CR analysis and CR design to evaluate requirement
coverage and traceability. During analysis, identify which DHF items need to
be created or updated and document them in the spec. During design, create or
update those items with correct traceability.

**Resolve all type codes from the Type Registry in the pre-computed DHF context.**
Do not assume a specific code (SRS, SYS, etc.) — every project may differ.

## Change Preference

**For every item type, always prefer: no change > update > create.**

Before touching any item, ask:
1. Does an existing item already cover this need? → make no change, just reference it.
2. Can an existing item be extended or clarified to cover this need? → update it.
3. Only if neither applies → create a new item.

This minimises DHF churn and keeps the item count stable.

## Traceability Hierarchy

DHF requirements form a chain from user needs down to implementation. The exact
type codes depend on the project — resolve them from the **Type Registry**:

```
Use cases / user scenarios  (tier 0 — "use_case" role)
    ↓ derives_from
Customer / user needs        (tier 1 — "customer_requirement" role)
    ↓ derives_from / satisfies
System requirements          (tier 2 — "system_requirement" role)
    ↓ derives_from
Software / subsystem req.    (tier 3 — "software_requirement" role, if present)
    ↓ implements
Design detail                (tier 4 — "design_detail" role, if present)

Cross-cutting:
  Architecture items ("architecture" role) — link to tier-2 system requirements
  Risk items ("risk" role) — link to tier-2 or tier-3 requirements
  Risk controls ("risk_control" role) — mitigate risk items
  SOUP items ("soup" role) — referenced by software requirements that use them
```

Projects that omit a tier (e.g., no tier-3 software requirements) link directly
from tier 2 to design or to tests. Never skip levels by creating items that link
across non-adjacent tiers unless the project's traceability rules explicitly allow it.

## Traceability Rules

- Every tier-1 item must derive from at least one tier-0 item
- Every tier-2 item must satisfy at least one tier-1 item
- Every tier-3 item (if present) must derive from at least one tier-2 item
- Every tier-4 item (if present) must implement at least one tier-3 item
- Risk items must link to tier-2 items (system-level), not lower tiers
- Risk controls must link to risk items
- If no existing tier-1 item covers a new infrastructure need, create one

## When to Create Items

| Trigger | Minimum items to create or update |
|---------|----------------------------------|
| New user-facing feature | tier-0 → tier-1 → tier-2 → tier-3 (in order) |
| New SOUP dependency | SOUP item + reference on affected tier-3 item |
| New identified hazard | risk item → risk control → link control to tier-2 |
| Architecture decision | architecture item + update affected tier-3 derivation |
| CR completed | Transition CR status to completed |

## Requirements Quality Rules

| Rule | What it means |
|------|--------------|
| **No conflict** | Must not contradict any existing item at the same or adjacent level. Resolve conflicts by updating the conflicting item. |
| **Clear hierarchy** | Each item must be a proper specialisation of its parent — more specific, never a generalisation. Do not skip levels. |
| **Atomicity** | One requirement per item. Do not combine multiple requirements with "and". |
| **Verifiability** | Every requirement must be testable. Avoid vague terms: "fast", "easy", "appropriate". State a concrete, measurable criterion. |
| **No duplication** | Check existing items before creating. Update rather than duplicate. |
| **Downward completeness** | Child items should together fully address the parent intent. |

## Creating Items via CLI

**Always use the CLI — do not write YAML files directly.**

```bash
# Create a new item (use the type code from the Type Registry)
python -m dhfkit --dhf DHF item create \
  --type <TYPE> \
  --data '<JSON>' \
  --author "github-actions[bot]" \
  --cr "<CR_ID>"

# Update an existing item
python -m dhfkit --dhf DHF item update <ITEM_ID> \
  --data '<JSON>' \
  --author "github-actions[bot]" \
  --cr "<CR_ID>"
```

IDs are assigned automatically on creation.

## Design Workflow

1. **Check existing coverage** — run `python -m dhfkit --dhf DHF item list --type <TYPE>` for each relevant type
2. **Check for conflicts and duplicates** — read existing items before writing anything
3. **List gaps** — identify missing items at each tier
4. **Apply change preference top-down** — tier 0 first, then tier 1, tier 2, tier 3; for each: no change > update > create; apply quality rules
5. **Validate schema** — run `python -m dhfkit --dhf DHF validate schema`
6. **Validate traceability** — run `python -m dhfkit --dhf DHF validate traceability`; fix orphans or uncovered pairs, repeat until clean
