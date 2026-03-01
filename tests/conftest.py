"""Root conftest: auto-inject compliantflow metadata into JUnit XML.

For every test that has a recognisable docstring, the following
<property> elements are written into the JUnit XML <testcase> node:

  compliantflow.id           – from @test_id tag, or extracted from function name
  compliantflow.title        – from first docstring line (after "TC-XXX: ")
  compliantflow.links        – from @links tag (comma-separated)
  compliantflow.reviewer     – from @reviewer tag (optional)
  compliantflow.review_date  – from @review_date tag (optional)
  compliantflow.review_status – from @review_status tag (optional)
"""

import re
import pytest

_TAG_RE = re.compile(r'@([\w]+):\s*(.+)')
_TC_ID_RE = re.compile(r'(?:^|[^A-Za-z])(TC)[_-]([A-Z]+)[_-](\d+)(?:[_-](\d+))?', re.IGNORECASE)


def _parse_docstring(doc: str) -> dict:
    """Extract compliantflow metadata from a test docstring."""
    meta = {}
    lines = doc.strip().splitlines()

    # Title: first non-empty line, strip leading TC-ID prefix if present
    for line in lines:
        stripped = line.strip()
        if stripped:
            # "TC-SYS-001-001: My title" → "My title"
            m = re.match(r'^TC[-_][A-Z][-_\w]+:\s*(.+)', stripped, re.IGNORECASE)
            meta['title'] = m.group(1).strip() if m else stripped
            break

    # @tag: value
    for line in lines:
        m = _TAG_RE.search(line.strip())
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()

    return meta


def _extract_tc_id_from_name(name: str) -> str | None:
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


@pytest.fixture(autouse=True)
def _inject_compliantflow_metadata(request, record_property):
    """Auto-inject compliantflow.* properties from docstring into JUnit XML."""
    doc = request.function.__doc__ or ""
    if not doc.strip():
        return

    meta = _parse_docstring(doc)

    # TC ID: prefer explicit @test_id, fall back to function name
    tc_id = meta.get('test_id') or _extract_tc_id_from_name(request.node.name)
    if tc_id:
        record_property("compliantflow.id", tc_id)

    if meta.get('title'):
        record_property("compliantflow.title", meta['title'])

    if meta.get('links'):
        record_property("compliantflow.links", meta['links'])

    if meta.get('reviewer'):
        record_property("compliantflow.reviewer", meta['reviewer'])

    if meta.get('review_date'):
        record_property("compliantflow.review_date", meta['review_date'])

    if meta.get('review_status'):
        record_property("compliantflow.review_status", meta['review_status'])
