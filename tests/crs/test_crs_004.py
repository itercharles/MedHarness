"""
API tests for CRS-004: Automated Documentation

Verifies that documentation-related data can be retrieved via the
CompliantFlowCore API (document generation relies on item data).

@links: CRS-004
"""


def test_TC_CRS_004_001_list_srs_items_for_document(core):
    """
    TC-CRS-004-001: List SRS Items for Document Generation via API

    @test_id: TC-CRS-004-001
    @links: CRS-004

    get_items_filtered('SRS') returns multiple SRS items, confirming
    that sufficient data exists for specification document generation.
    """
    srs_items = core.get_items_filtered("SRS", None, "")

    assert len(srs_items) >= 2, \
        f"Document generation requires multiple SRS items; found {len(srs_items)}"
    for item in srs_items:
        assert item["id"].startswith("SRS-")
        assert "title" in item


def test_TC_CRS_004_002_get_doc_type_metrics(core):
    """
    TC-CRS-004-002: Get Document Type Metrics via API

    @test_id: TC-CRS-004-002
    @links: CRS-004

    get_doc_type_metrics('SRS') returns count and status breakdown,
    representing the data that backs document preview.
    """
    metrics = core.get_doc_type_metrics("SRS")

    assert isinstance(metrics, dict), "Expected a dict of metrics"
    assert "total" in metrics or "count" in metrics or len(metrics) > 0, \
        f"Expected non-empty metrics for SRS, got: {metrics}"
