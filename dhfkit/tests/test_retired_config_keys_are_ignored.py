"""A key the engine no longer reads is ignored, not rejected.

`allowed_parents` was replaced by `required_traceability` and is no longer a
field; a doc type file written before that still loads.
"""

from dhfkit.models.config import DocTypeConfig


def test_allowed_parents_is_ignored() -> None:
    doc_type = DocTypeConfig(code="SRS", name="SRS", prefix="SRS-", allowed_parents=["SYS"])
    assert doc_type.code == "SRS"
    assert not hasattr(doc_type, "allowed_parents")
