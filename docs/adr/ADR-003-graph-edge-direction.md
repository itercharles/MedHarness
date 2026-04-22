# ADR-003: Graph Edge Direction — Child Points to Parent

**Status:** Accepted
**Date:** 2026-01-01
**Deciders:** Engineering Lead

---

## Context

The DHF traceability model is a directed graph. Items are nodes; traceability links are edges. The question is which direction edges run: does a parent requirement point to its child requirements, or does a child requirement point to its parent?

In IEC 62304, traceability runs upward: a software requirement derives from a system requirement which derives from a customer requirement. The natural English reading is "parent → child" (top-down). Most traceability matrix tools draw it this way.

In the CompliantFlow YAML schema, items declare `derives_from: [SYS-001]` — the child (SRS) declares its parent (SYS), not the other way around. This is the "child → parent" direction.

## Decision

Edges in `compliantflow/graph.py` run **child → parent**. An SRS item has an outbound edge to its parent SYS item.

Consequence for traversal API:
- `descendants(SYS-001)` returns items that SYS-001 derives from (business-upstream: toward UC/CRS)
- `ancestors(SYS-001)` returns items derived from SYS-001 (business-downstream: toward SRS/TC)

This is the **opposite** of natural English. `ancestors` means downstream.

## Rationale

The `derives_from` field is the natural place for a child item to declare its parents — you know the parent when you write the child. Requiring parent items to maintain a `has_children` list would create synchronization risk (two items must be updated for one new link).

NetworkX (the underlying graph library) defines `ancestors`/`descendants` relative to edge direction. Since we store child→parent edges, the method names are inverted from their English meanings. This is a documented quirk, not a design flaw.

## Consequences

**Positive:**
- Items are self-contained — each item declares its own upstream dependencies
- No update needed to parent items when adding a new child
- Schema is append-only from the child's perspective

**Negative:**
- `ancestors()` and `descendants()` mean the opposite of their English meanings — must be documented in every context where this API is used
- New contributors must be warned before touching graph traversal code

**Constraints this imposes:**
- Every function or comment that uses `ancestors`/`descendants` must clarify the business direction in a comment
- Do not "fix" this by reversing edge direction without updating all traversal logic and tests
