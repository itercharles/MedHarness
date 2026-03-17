# Development Plan

## 1. Introduction
This document outlines the development plan for the CompliantFlow ALM platform.

## 2. Development Phases

### Phase 1: Inception
- **Goal**: Define high-level requirements and scope.
- **Activities**:
  - Identify User Needs (USN).
  - Define primary Risks.

### Phase 2: Elaboration
- **Goal**: Establish architecture and system specifications.
- **Activities**:
  - Define System Requirements (SYS).
  - Draft Architecture Design.
  - Prototype core graph engine.

### Phase 3: Construction
- **Goal**: Implement features and verification.
- **Activities**:
  - Detailed Design (SDS).
  - Implementation of Pydantic models and NetworkX logic.
  - Creation of Verification Tests (TC-VER).
  - Execution of Unit and Integration tests.

### Phase 4: Transition
- **Goal**: Validation and Release.
- **Activities**:
  - Validation Testing (TC-VAL).
  - User Acceptance.
  - Release packaging.

## 3. Development Standards, Methods and Tools

The following standards, methods, and tools are applied throughout development:

- **Standards**: IEC 62304 (medical device software), ISO 14971 (risk management)
- **Methods**: Model-based requirements (YAML), graph-based traceability, GitOps approval workflow
- **Tools**: Python, pytest, Git, GitHub Actions CI/CD, CompliantFlow CLI

## 4. Document Lifecycle

The following documents are produced during the software development lifecycle. Each follows the GitOps document control procedure: draft on a feature branch → peer review via GitHub pull request → approval by merge to `main` by an authorised reviewer → modification via a new pull request referencing the applicable Change Request (CR) item.

| Document | Purpose | Procedure |
|---|---|---|
| Development Plan (this document) | Defines development approach, standards, methods, tools, and document lifecycle | Created and updated via CR-linked PRs; reviewed by project lead |
| Verification Plan | Defines verification tasks, deliverables, milestones, and acceptance criteria | Created before Construction phase; updated when new verification tasks are identified |
| Integration Plan | Describes integration sequence and integration testing strategy | Created during Elaboration; updated when architecture changes |
| Configuration Management Plan | Describes CM scheme, controlled items, and change control procedures | Created during Elaboration; reviewed at each release |
| Maintenance Plan | Describes maintenance procedures, feedback handling, and release process | Created before Transition phase |
| System Architecture Specification | Documents the software architecture and SOFTWARE ITEM decomposition | Created during Elaboration; updated when architecture changes |
| Release Notes | Records released version, build environment, and known anomalies | Created per release |

## 5. Defect Identification and Management

### 5.1 Procedure for Identifying Technology-Specific Defect Categories

Defect categories are identified using the following procedure:

1. **Review programming technology characteristics**: Analyse Python's dynamic typing, Pydantic's validation behaviour, and NetworkX graph semantics for known failure modes.
2. **Map to defect categories**: For each identified failure mode, define a defect category, its potential trigger, and an associated automated or manual control.
3. **Link to risk analysis**: Each defect category is reviewed against the RISK items in the DHF to confirm it does not contribute to an unacceptable risk. Categories that could contribute to risk are mitigated by risk control measures (RCM).
4. **Document and review**: The identified categories and their controls (below) are reviewed at each release.

### 5.2 Defect Categories and Controls

| Category | Introduced by | Control |
|---|---|---|
| Logic defects | Python dynamic typing / algorithmic errors | Automated test suite (pytest) executed on every pull request |
| Data integrity defects | Pydantic model misuse or schema evolution | Schema validation in DHF loader; ValidationError tests |
| Traceability defects | NetworkX edge direction errors | `compliantflow validate traceability` in CI Phase 4 |
| Regression defects | Unintended side-effects of changes | CI pipeline regression tests on every merge to `main` |

Evidence that these defects do not contribute to unacceptable risk:
- CI pipeline test results stored per-run as GitHub Actions artifacts and fetched on demand by the DHF
- Risk analysis items (RISK) linked to risk control measures (RCM) in the DHF

## 6. Build and Release Procedure

### 6.1 Build Environment

| Item | Value |
|---|---|
| Operating System | Ubuntu 24.04 (GitHub Actions `ubuntu-latest`) |
| Python runtime | 3.11 (pinned in CI via `actions/setup-python`) |
| Dependency management | `pip` with `requirements.txt` (pinned versions) |
| Key tools | pytest, pydantic, networkx, gitpython, click, pyyaml, google-genai |
| CI platform | GitHub Actions |

### 6.2 Release Procedure

1. All outstanding Change Requests (CR items) for the release are resolved and merged to `main`.
2. CI pipeline (Phases 1–4) passes on `main`: unit tests, SYS API tests, CRS API tests, DHF validation, and IEC 62304 compliance check.
3. A Release item (REL) is created in the DHF with the target version, linked to all applicable CRs.
4. Release notes (`DHF/documents/release_notes.md`) are updated with the version, build environment, and any known residual anomalies (DEF items).
5. A Git tag (`vX.Y.Z`) is created on the passing `main` commit.
6. The release is published via GitHub Releases, referencing the tag and release notes.
