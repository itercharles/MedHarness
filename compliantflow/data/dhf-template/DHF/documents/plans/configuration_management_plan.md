# Software Configuration Management Plan

## Purpose
This document describes the configuration management process in accordance with
IEC 62304 §5.1.9 and §8.

## Configuration Items
The following classes of items are under configuration control:
- DHF items (requirements, risks, architecture, design) — stored as YAML under `DHF/items/`
- Source code — managed in this Git repository
- Development tools — pinned in `requirements.txt` (Python dependencies, pytest, linters)
- CI/CD tools — defined in `.github/workflows/` (GitHub Actions pipeline configuration)
- Test results — stored in `DHF/test-results/results.yaml`
- Document specifications — stored under `DHF/documents/`
- Governance policies — stored under `governance/`

## Version Control
Git is used for all configuration management. Every change is traceable via
commit history. The `main` branch represents the approved baseline.

## Change Control
All changes to configuration items require a Change Request (CR) item in the DHF.
Changes are implemented via pull requests, reviewed, and merged to `main`.

## Configuration Identification
Each item is uniquely identified by its prefixed ID (e.g., SYS-001, SRS-002).
Software versions are identified by Git commit SHA and semantic version tags.

## Configuration Status Accounting
The history of all controlled configuration items is retained via Git commit log.
Each item version is uniquely identified by a Git commit SHA. The full change
history is retrievable via `git log` and `git blame`.

## Change Request Lifecycle
CR items have two states:

- **planned** — the change has been identified and documented; implementation may be in progress
- **completed** — the change has been implemented and merged to `main`

Approval is implicit in the GitOps model: a pull request merge to `main` constitutes
the approval event, recorded by Git commit metadata (author, timestamp, reviewer identity
in the GitHub audit log). No separate approval status field is required.

## Problem Resolution
Anomalies are recorded as CR items and tracked through the lifecycle workflow.

## Timing
Configuration items are placed under version control before verification.
