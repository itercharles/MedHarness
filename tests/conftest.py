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

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent / "utils"))
from docstring_parser import parse_docstring, extract_tc_id_from_name


@pytest.fixture(autouse=True)
def _inject_compliantflow_metadata(request, record_property):
    """Auto-inject compliantflow.* properties from docstring into JUnit XML."""
    doc = request.function.__doc__ or ""
    if not doc.strip():
        return

    meta = parse_docstring(doc)

    # TC ID: prefer explicit @test_id, fall back to function name
    tc_id = meta.get('test_id') or extract_tc_id_from_name(request.node.name)
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
