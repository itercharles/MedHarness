# System Configuration Documentation

## Purpose
This document identifies the set of configuration items and their versions that
comprise the software system configuration, in accordance with IEC 62304 §8.1.3.

## Software Configuration Items

| Item | Location | Version Scheme |
|------|----------|---------------|
| DHF requirements | `DHF/items/` | Git commit SHA |
| Application source | `compliantflow/` | Git commit SHA |
| DHF utilities | `DHF/utils/` | Git commit SHA |
| Test suite | `tests/` | Git commit SHA |
| Governance policies | `governance/` | Git commit SHA |
| CI pipeline | `.github/workflows/` | Git commit SHA |

## SOUP Items
Third-party software dependencies are listed in `DHF/items/04_soup/` as SOUP items,
each identifying the title, manufacturer, and version designator.

## System Configuration Baseline
The current system configuration is identified by the Git commit SHA of `main`.
Full configuration history is retrievable via `git log`.
