# DHF Requirements Hierarchy Guide

This document provides guidance on establishing a standards-compliant requirements hierarchy for CompliantFlow's Design History File (DHF).

---

## Requirements and Architecture Model

### Dual-Track Model

CompliantFlow uses a **dual-track model** that separates requirements flow from architecture views:

```
                        UC (Use Cases)
                             ↓
                    CRS (Stakeholder Requirements)
                             ↓
┌────────────────────────────────────────────────────────┐
│                 SYS (System Requirements)              │
│                 "What system must do"                  │
└─────────────┬──────────────────────────┬───────────────┘
              ↓                          ↓
       SRS (Software Req)         SYS_ARCH (System Arch)
       "What software does"       "How system structured"
              ↓                          
       SWDD (Detailed Design)     SWAD (Software Arch)
       "How units work"           "How software structured"
              ↓
         TC-* (Tests)
```

### Two Parallel Tracks

**Track 1: Requirements Flow (Vertical)**
```
SYS → SRS → SWDD → Code
```
- **SYS:** System requirements (what system must do)
- **SRS:** Software requirements (what software must do)
- **SWDD:** Detailed design (how each unit implements it)

**Track 2: Architecture Views (Horizontal)**
```
SYS → SYS_ARCH (system structure)
SRS → SWAD (software structure)
```
- **SYS_ARCH:** System architecture decisions
- **SWAD:** Software architecture decisions

### Key Principle

**Architecture is a VIEW, not a step in requirements flow**

- Requirements define **what to build** (SYS → SRS → SWDD)
- Architecture defines **how to structure it** (SYS_ARCH, SWAD)
- SWAD informs SWDD but doesn't sit between SRS and SWDD

---

## Level Definitions

| Level | Type | Purpose | Example |
|-------|------|---------|---------|
| **UC** | Use Case | User goals | "User manages traceability" |
| **CRS** | Stakeholder Req | Stakeholder needs | "System shall support regulatory compliance" |
| **SYS** | System Req | External behavior | "System shall visualize traceability" |
| **SYS_ARCH** | Architecture | System structure | "Web-based Python application" |
| **SRS** | Software Req | Software behavior | "Software shall use NetworkX graph" |
| **SWAD** | Architecture | Software structure | "GraphEngine, ItemLoader components" |
| **SWDD** | Design | Unit implementation | "find_orphans: filter nodes with no incoming edges" |
| **TC-*** | Test | Verification | "Verify orphan detection returns correct items" |

---

## Relationships

```yaml
# Requirements flow
SYS-001 
  ↓ derives
SRS-001
  ↓ implements
SWDD-001

# Architecture views
SYS-001
  ↓ informs
SYS_ARCH-001 (describes system structure)

SRS-001
  ↓ informs
SWAD-001 (describes software structure)

# Cross-references
SWAD-001
  ↓ guides
SWDD-001 (implementation follows architecture)
```

---

## Complete Example: Traceability Feature

### SYS-001: System Requirement
```yaml
id: SYS-001
title: "Traceability Visualization"
content: "System shall provide interactive visualization of traceability relationships"
```

### SYS_ARCH-001: System Architecture
```yaml
id: SYS_ARCH-001
title: "Web Application Architecture"
content: |
  System architecture:
  - Python/Streamlit web application
  - YAML file storage
  - Git version control
  - Browser-based UI
informs: [SYS-001, SYS-002, SYS-003]
```

### SRS-001: Software Requirement
```yaml
id: SRS-001
title: "Graph Data Structure"
content: "Software shall use NetworkX directed graph with nodes and edges"
derives_from: [SYS-001]
```

### SWAD-001: Software Architecture
```yaml
id: SWAD-001
title: "Traceability Architecture"
content: |
  Components:
  - GraphEngine: Builds and analyzes graph
  - ItemLoader: Loads items from YAML
  - TraceabilityUI: Streamlit visualization
  
  Interfaces:
  - GraphEngine.build_graph() -> nx.DiGraph
  - GraphEngine.find_orphans(doc_type) -> List[str]
implements: [SRS-001]
```

### SWDD-001: Detailed Design
```yaml
id: SWDD-001
title: "Orphan Detection Algorithm"
content: "Find items without parent links"
unit_name: "GraphEngine.find_orphans"
algorithm: "Filter nodes of specified type with no incoming edges, excluding root types"
implements: [SRS-001]
guided_by: [SWAD-001]
```

---

## SYS vs SRS Distinction

### SYS (System Requirements)
- **Perspective:** External, user-facing
- **Language:** What system must do
- **Audience:** Stakeholders, users, managers
- **Technology:** Agnostic
- **Example:** "System shall visualize traceability"

### SRS (Software Requirements)
- **Perspective:** Internal, implementation
- **Language:** How software will do it
- **Audience:** Developers, architects
- **Technology:** Specific
- **Example:** "Software shall use NetworkX directed graph"

**Key:** SYS is technology-agnostic, SRS is technology-specific

---

## Derivation Examples

### Example 1: Traceability

**SYS-001:**
```yaml
title: "Traceability Visualization"
content: "System shall provide interactive graph visualization"
```

**SRS-001:**
```yaml
title: "Graph Data Structure"
content: "Software shall use NetworkX directed graph with nodes and edges"
derives_from: [SYS-001]
```

**What changed:** Added technology (NetworkX), data structure details

### Example 2: Document Generation

**SYS-003:**
```yaml
title: "Automated Document Generation"
content: "System shall generate specification documents in PDF format"
```

**SRS-003:**
```yaml
title: "Template-Based PDF Generation"
content: |
  Software shall:
  - Render Jinja2 templates
  - Convert markdown to HTML using Python-Markdown
  - Generate PDF using WeasyPrint
derives_from: [SYS-003]
```

**What changed:** Added specific libraries, workflow steps

---

## IEC 62304 Compliance

### Requirements Track (§5.2)
```
SYS → SRS → SWDD
```
- ✅ §5.2.1: SRS defines software requirements
- ✅ §5.4.2: SWDD provides detailed design

### Architecture Track (§5.3)
```
SRS → SWAD
```
- ✅ §5.3.1: SWAD transforms SRS into architecture
- ✅ §5.3.2: SWAD documents software architecture

**Key Point:** IEC 62304 doesn't mandate linear flow, just that these artifacts exist and are traceable.

### Traceability Requirements

**IEC 62304 §5.2.6 requires:**
- Software requirements trace to system requirements ✅ SRS → SYS
- Software requirements trace to risk controls ✅ SRS → RISK
- Architecture implements requirements ✅ SWAD → SRS
- Detailed design implements requirements ✅ SWDD → SRS

**Our model provides:**
```yaml
SYS-001
  ↓ derives
SRS-001
  ↓ implements (parallel)
  ├─→ SWAD-001 (architecture view)
  └─→ SWDD-001 (detailed design)
```

All required traceability is maintained ✅

---

## ISO/IEC/IEEE 15288 Compliance

| Section | Requirement | CompliantFlow Artifact |
|---------|-------------|------------------------|
| §6.4.2 | Stakeholder needs | UC, CRS |
| §6.4.3 | System requirements | SYS |
| §6.4.4 | Architecture definition | SYS_ARCH |
| §6.4.5 | Design definition | SRS, SWAD, SWDD |

---

## Benefits of Dual-Track Model

✅ **Clearer separation:** Requirements vs. architecture  
✅ **Standards compliant:** Satisfies IEC 62304 §5.2-5.4  
✅ **Flexible:** Architecture can evolve without changing requirements  
✅ **Traceable:** Clear links between all artifacts

---

## Design Rationale

### Why Dual-Track Model?

**Traditional Linear Model:**
```
SYS → SRS → SWAD → SWDD ❌
```
**Problem:** Implies architecture comes "between" requirements and design

**Our Dual-Track Model:**
```
SYS → SRS → SWDD (requirements flow)
SYS → SYS_ARCH (architecture view)
SRS → SWAD (architecture view)
```
**Benefit:** Separates "what to build" from "how to structure it"

### SYS_ARCH vs SWAD

**SYS_ARCH (System Architecture):**
- **Scope:** Entire system
- **Purpose:** High-level technology decisions
- **Example:** "Web-based Python application with YAML storage"
- **Audience:** System architects, project managers

**SWAD (Software Architecture):**
- **Scope:** Software only
- **Purpose:** Software component structure
- **Example:** "GraphEngine, ItemLoader, TraceabilityUI components"
- **Audience:** Software architects, developers

**Relationship:**
```
SYS_ARCH: "Use Python/Streamlit web application"
  ↓ refines to
SWAD: "GraphEngine, DocumentGenerator, WorkflowEngine components"
```

---

## When to Use This Model

**Use dual-track model when:**
- ✅ Want clear separation of concerns
- ✅ Architecture may evolve independently
- ✅ Need to satisfy IEC 62304 explicitly
- ✅ Team understands architecture as a view

**Use linear model when:**
- ❌ Very simple system (few components)
- ❌ Architecture is trivial
- ❌ Team prefers traditional waterfall

**CompliantFlow uses dual-track** because:
- Clear separation of requirements and architecture
- Easier to maintain and evolve
- Better alignment with standards

---

## Testing and Verification Strategy

### What Gets Tested

**IEC 62304 §5.5 requires testing at the SOFTWARE UNIT and INTEGRATION levels, not at the DESIGN level.**

```
SRS (Software Requirements) → MUST be tested ✅
  ↓
SWDD (Detailed Design) → Verified via review, NOT separate tests ❌
  ↓
Code Implementation → MUST be tested ✅
```

### Testing Hierarchy

| Artifact | Verification Method | Test Files |
|----------|-------------------|------------|
| **SRS** | Automated tests | `tests/test_srs_*.py` ✅ |
| **SWAD** | Design review | No test files ❌ |
| **SWDD** | Design review + Code review | No test files ❌ |
| **Code** | Unit/Integration tests | `tests/test_*.py` ✅ |

### Why SWDD Doesn't Need Separate Tests

**SWDD is design documentation, not executable code:**

1. **SWDD describes HOW** the software is designed
2. **Code implements** the SWDD design
3. **Tests verify** the code works correctly

**Verification of SWDD:**
- ✅ Peer review of design documents
- ✅ Traceability check (SWDD → SRS)
- ✅ Code review (code matches SWDD)
- ✅ Tests verify code behavior (which implements SWDD)
- ❌ NOT separate automated tests for SWDD

### Example: Orphan Detection

**SWDD-001: Orphan Detection Algorithm**
```yaml
title: "Orphan Detection Algorithm"
algorithm: "Filter nodes with no incoming edges, excluding root types"
complexity: "O(N) where N = number of nodes"
```

**Verification:**
- ✅ Design review: Algorithm is sound
- ✅ Code review: `GraphEngine.find_orphans()` implements the algorithm
- ✅ SRS test: `test_srs_007_orphans.py` verifies orphan detection works
- ❌ No `test_swdd_001.py` needed

### Compliance Summary

**IEC 62304 Requirements:**
- §5.5.1: Software unit testing → ✅ Unit tests for code
- §5.5.2: Integration testing → ✅ Integration tests
- §5.5.3: Test procedures → ✅ Automated test files
- §5.5.4: Test results → ✅ Test execution logs

**What CompliantFlow Has:**
- ✅ SRS tests (17 test files): Verify requirements
- ✅ SWDD documents (17 items): Design specifications
- ✅ Traceability: SRS → SWDD → Code
- ✅ Code tests: Verify implementation

**This satisfies all regulatory requirements** ✅

---

## References

- IEC 62304:2006+AMD1:2015 - Medical device software lifecycle processes
- ISO/IEC/IEEE 15288:2015 - Systems and software engineering
- ISO 13485:2016 - Medical devices quality management systems
- INCOSE Systems Engineering Handbook v4

---

**Last Updated:** 2025-12-22
