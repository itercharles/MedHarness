---
name: CompliantFlow Project Overview
description: Core identity, architecture topology, and technology choices for CompliantFlow
type: project
---

CompliantFlow is a Docs-as-Code ALM platform for medical device Design History File (DHF) management. All DHF items (requirements, risks, change requests, test cases) are YAML files in the repo. The system enforces regulatory standards (IEC 62304, ISO 14971, FDA 21 CFR 820.30) through automated CI compliance checks.

**Why:** Medical device software manufacturers need auditable, version-controlled DHF records that map to regulatory standards. Git is the source of truth; compliance is enforced at CI time.

**How to apply:** All architectural recommendations must account for regulatory auditability requirements. Changes to data structures need to remain git-committable and human-readable.

## Key components

- `compliantflow/core.py` — CompliantFlowCore facade (read-only analysis)
- `compliantflow/policy.py` — PolicyEngine with 9 check types; Gemini LLM for semantic checks
- `compliantflow/adapters/protocol.py` — DHFAdapter Protocol (structural subtyping)
- `compliantflow/domain/compliance.py` — PolicyGroup, ComplianceReport, PolicyResult domain models
- `compliantflow/domain/schema.py` — ProjectSchema, ItemTypeSchema (compliantflow-domain vocabulary)
- `compliantflow/graph.py` — NetworkX DiGraph (edge direction: child→parent)
- `DHF/utils/local_adapter.py` — LocalDHFAdapter implements DHFAdapter for local filesystem
- `DHF/utils/result_store.py` — Test result persistence in DHF/test-results/results.yaml
- `DHF/utils/lifecycle.py` — Pure-function lifecycle engine (CR, REL, DEF types only)
- `compliantflow/cli.py` — Read-only analysis CLI
- `DHF/utils/cli.py` — Mutation CLI (item CRUD, lifecycle, doc generation)

## Technology stack

Python 3.11, Click, Pydantic v2, NetworkX, WeasyPrint (PDF), Gemini 2.5 Flash (LLM semantic checks), PyYAML, GitHub Actions
