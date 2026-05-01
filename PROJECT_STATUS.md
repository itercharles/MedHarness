# Project Status

> **Last updated:** 2026-04-30
>
> This note supplements the formal product documents in CompliantFlow-DHF.
> CR-level feature planning; this file gives an at-a-glance status for external adopters.

---

## What Is Stable Now

The following is ready for external use and will maintain backward compatibility
across minor versions:

- **`compliantflow init`** — interactive project scaffolding (DHF template,
  product CI workflows)
- **`ci test-coverage`** — requirement → test coverage gate (JUnit XML contract)
- **`ci evidence bundle`** — CI evidence bundle production
- **`ci release consume-artifact`** / **`ci release assemble`** — release
  assembly pipeline
- **`cr workflow`** — CR intake (GitHub Issues) and completion
- DHF item types: UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM, SOUP, TC, CR,
  REL, DEF

---

## What Is Evolving

These areas are under active development and may see interface changes:

- **AI agent context package** — machine-readable context for AI coding
  tools (CR-040)
- **RDM migration** — Innolitics RDM → CompliantFlow DHF migration (CR-046)
- **Command output formats** — `status` output format evolving

---

## What Is Not in Scope Yet (OSS)

These are acknowledged gaps — planned for future milestones, not accidentally
missing:

- **Standards compliance checking** — IEC 62304, ISO 14971 policy enforcement
  is planned as a commercial capability
- **Web UI** — CLI only for now. Web dashboard planned for commercial release.
- **PyPI distribution** — GitHub Releases is the current distribution channel.
- **GitLab CI / Bitbucket Pipelines** — GitHub Actions only. Community
  contributions welcome.

---

## Commercial vs Open Source

The open-source core covers the full design-controlled engineering workflow:
scaffolding, design traceability, requirement → test coverage, evidence
bundles, and AI context. It is and will remain MIT-licensed.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed boundary between OSS
infrastructure and commercial intelligence.
