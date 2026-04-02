---
name: CompliantFlow Product Overview
description: Core product identity, architecture, users, and compliance targets
type: project
---

CompliantFlow is a **Docs-as-Code ALM (Application Lifecycle Management) platform for medical devices**. It manages the Design History File (DHF) — requirements, risks, tests, and change requests — stored as YAML files tracked in Git.

**Why:** Medical device manufacturers (under IEC 62304 and ISO 14971) must maintain a complete, traceable, auditable DHF. Traditional tools are expensive, opaque, and lock data in proprietary formats. CompliantFlow treats the DHF as code: plain YAML in Git, CLI-driven, CI/CD-native.

**Architecture (two-layer):**
- `DHF/utils/` — Data layer: YAML CRUD, lifecycle state machine, schema validation, document generation, test result storage. CLI: `python -m utils`
- `compliantflow/` — Read-only analysis engine: traceability graph (NetworkX DiGraph), compliance policy engine, PDF report generation. CLI: `python -m compliantflow`
- `DHFAdapter` protocol decouples the two layers; alternative backends (cloud, DB) can plug in without changing the engine.

**GitOps approval model:** Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, RCM) have no explicit `status` field. `main` branch = approved; feature branch = draft.

**Explicit lifecycle items:** CR, REL, DEF have full state machines (draft → in_review → approved → implementing → completed / cancelled).

**Compliance standards implemented:** IEC 62304 (106 policies, 75 automated), IEC 82304-1 (partial).

**Primary personas:**
- Quality/Regulatory Engineer — manages DHF, runs compliance checks, generates audit evidence
- Software Engineer — creates/links requirements, runs tests, imports results via CI
- DevOps/CI Engineer — integrates CLI into GitHub Actions pipelines

**Current released version:** 1.0.0 (initial release) and 1.2.0 (feature release). Version 1.1.0 is a draft with no included items.

**Tech stack:** Python, Pydantic v2, NetworkX, GitPython, Click, Jinja2, WeasyPrint, google-genai (Gemini for semantic compliance checks).
