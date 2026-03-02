"""Docstring metadata extraction utilities.

Used by tests/conftest.py (autouse fixture) and directly by SRS-010 tests.
"""

import re

_TAG_RE = re.compile(r'@([\w]+):\s*(.+)')
_TC_ID_RE = re.compile(r'(?:^|[^A-Za-z])(TC)[_-]([A-Z]+)[_-](\d+)(?:[_-](\d+))?', re.IGNORECASE)


def parse_docstring(doc: str) -> dict:
    """Extract compliantflow metadata from a test docstring.

    Returns a dict with keys: title, test_id, links, reviewer,
    review_date, review_status (all optional).
    """
    meta = {}
    lines = doc.strip().splitlines()

    # Title: first non-empty line, strip leading TC-ID prefix if present
    for line in lines:
        stripped = line.strip()
        if stripped:
            m = re.match(r'^TC[-_][A-Z][-_\w]+:\s*(.+)', stripped, re.IGNORECASE)
            meta['title'] = m.group(1).strip() if m else stripped
            break

    # @tag: value
    for line in lines:
        m = _TAG_RE.search(line.strip())
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()

    return meta


def extract_tc_id_from_name(name: str) -> str | None:
    """Derive normalised TC-XXX-NNN id from a test function name."""
    m = _TC_ID_RE.search(name)
    if not m:
        return None
    doc_type = m.group(2).upper()
    number = m.group(3).zfill(3)
    sub = m.group(4)
    if sub:
        return f"TC-{doc_type}-{number}-{sub.zfill(3)}"
    return f"TC-{doc_type}-{number}"
