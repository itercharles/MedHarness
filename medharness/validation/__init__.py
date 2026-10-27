"""The validation set `build validation` runs where MedHarness is installed (ADR-005).

Each case runs the real CLI against a scratch project in a temporary directory and checks
test points of a high-risk requirement in MedHarness's own DHF. The cases ship in the
wheel, so they need nothing a plain install lacks: no pytest, no checkout.
"""

from medharness.validation import changes, completion, release, seeded, structure, verification

CASES = [*seeded.CASES, *completion.CASES, *verification.CASES, *changes.CASES, *structure.CASES, *release.CASES]
