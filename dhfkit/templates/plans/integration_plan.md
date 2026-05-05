# Software Integration Plan

## Purpose
This document describes the plan for integrating software items and performing
integration testing in accordance with IEC 62304 §5.1.5 and §5.6.

## Integration Strategy
Software units are integrated incrementally. Each integration step is tested
before proceeding to the next.

## Integration Sequence
1. Unit-level implementation and verification (SWDD items)
2. Integration of software units into software items (SRS level)
3. Integration of software items into the software system (SYS level)
4. Software system testing against system requirements

## Integration Testing
Integration tests are defined as TC-SYS items and executed via the CI pipeline.
Test results are recorded in `DHF/test-results/results.yaml`.

## Tools
- CI pipeline: `.github/workflows/ci-pipeline.yml`
- Test framework: pytest
- Test result storage: DHF ResultStore

## Test Procedure Evaluation
Test procedures are evaluated for adequacy before execution. Evaluation criteria include:
- Coverage of all SYS requirements
- Test case independence and repeatability
- Pass/fail criteria are unambiguous

## Regression Testing
All tests are re-run on every pull request. CI enforces a green build before merge.
Regression test results are stored in `DHF/test-results/results.yaml` and provide
evidence that previously passing tests have not been broken by changes.
