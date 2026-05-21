"""Utility for parsing numbered test points from requirement item testing fields.

Test points are written in the ``testing`` field of CRS/SYS/SRS items as:
    T1: Given a CT series is active, when Run is clicked, the button disables.
    T2: Given the job succeeds, the imported structure set is marked dirty.

``parse_testing_points`` extracts the point IDs from that free-form text.
"""

from __future__ import annotations

import re

_POINT_RE = re.compile(r"^\s*(T\d+)\s*:", re.MULTILINE)


def parse_testing_points(testing_text: str | None) -> list[str]:
    """Return the list of test-point IDs defined in *testing_text*.

    Scans each line for the pattern ``T<digits>:`` (leading whitespace is
    ignored) and returns the matched IDs in document order.

    Args:
        testing_text: Raw string value of a requirement's ``testing`` field.
                      ``None`` or empty string returns an empty list.

    Returns:
        Ordered list of point IDs, e.g. ``["T1", "T2", "T3"]``.
    """
    if not testing_text:
        return []
    return _POINT_RE.findall(testing_text)
