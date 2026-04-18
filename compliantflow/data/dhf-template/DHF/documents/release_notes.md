# Release Notes

This document records released versions of the software system in accordance
with IEC 62304 §5.8.4.

## Version History

Each release is identified by a Git tag and corresponds to a merge to `main`
following successful CI validation.

| Version | Date | Commit | Description |
|---------|------|--------|-------------|
| 2.0.0 | 2026-04-18 | d218cbb | Commercial release — compliance CI gate, 510(k) submission package, AI agent harness |
| See Git tags | — | `git tag -l` | Earlier releases tracked via Git |

## v2.0.0 (2026-04-18)

**Build environment:** Ubuntu 24.04 (GitHub Actions), Python 3.11, pip

**Included CRs:** CR-035, CR-036, CR-037, CR-039, CR-040, CR-041, CR-042, CR-043, CR-044, CR-045, CR-046, CR-047, CR-049, CR-050

**Key capabilities delivered:**
- IEC 62304, ISO 14971, IEC 82304-1, ISO 13485 compliance policy engine
- CI merge gate with automated evidence generation
- 510(k) submission evidence package (`compliantflow export submission`)
- AI coding agent harness (AGENTS.md / CLAUDE.md in DHF template)
- Wheel distribution (`compliantflow-2.0.0-py3-none-any.whl`)
- DHF template with governance files, utils, document templates, CI workflows

**Known anomalies:** None (no open DEF items at release)

**Residual risks:** All risks accepted or mitigated via RCM items in DHF.

## Release Identification
Released versions are identified by:
- Semantic version tag in Git (e.g., `v1.0.0`)
- Commit SHA recorded in CI build artifacts
- DHF baseline at time of release (frozen via Git tag)
