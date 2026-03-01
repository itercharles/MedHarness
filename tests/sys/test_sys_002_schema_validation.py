"""
API tests for strict schema validation (SRS-001: Item Persistence and Versioning)

Verifies: The system shall validate item YAML files against the project
config schema and reject invalid items with clear error messages.

@links: SRS-001
"""

import pytest
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.repository.loader import ItemLoader
from traceability.exceptions import ValidationError
from traceability.compliant_flow_core import CompliantFlowCore


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_valid_item_loads_without_error(test_dhf_root):
    """
    TC-SRS-001-VAL-001: Valid items load successfully (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-001

    Confirm that all items in the test DHF pass schema validation.
    """
    core = CompliantFlowCore(test_dhf_root)
    items = core.get_all_items()
    assert len(items) > 0, "Test DHF should contain items"


def test_unknown_field_raises_validation_error(test_dhf_root):
    """
    TC-SRS-001-VAL-002: Unknown field rejected with clear error (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-002

    An item YAML with a field not declared in the doc-type config must raise
    ValidationError naming both the field and the file.
    """
    core = CompliantFlowCore(test_dhf_root)
    tmp = test_dhf_root / "items" / "02_req_sys" / "SYS-INVALID-FIELD.yaml"
    _write_yaml(tmp, {
        "id": "SYS-INVALID-FIELD",
        "title": "Bad item",
        "content": "Valid content",
        "unknown_field_xyz": "should be rejected",
        "status": "draft",
    })

    with pytest.raises(ValidationError) as exc:
        loader = ItemLoader(test_dhf_root / "items", project_config=core.config)
        loader.load_file(tmp)

    assert "unknown_field_xyz" in str(exc.value).lower()
    assert "SYS-INVALID-FIELD.yaml" in str(exc.value)


def test_missing_id_raises_validation_error(test_dhf_root):
    """
    TC-SRS-001-VAL-003: Missing 'id' field rejected (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-003
    """
    core = CompliantFlowCore(test_dhf_root)
    tmp = test_dhf_root / "items" / "02_req_sys" / "SYS-NO-ID.yaml"
    _write_yaml(tmp, {
        "title": "Item without id",
        "content": "Missing id field",
        "status": "draft",
    })

    with pytest.raises(ValidationError) as exc:
        loader = ItemLoader(test_dhf_root / "items", project_config=core.config)
        loader.load_file(tmp)

    assert "id" in str(exc.value).lower()


def test_unknown_doc_type_raises_validation_error(test_dhf_root):
    """
    TC-SRS-001-VAL-004: Unknown doc type rejected (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-004
    """
    core = CompliantFlowCore(test_dhf_root)
    tmp = test_dhf_root / "items" / "02_req_sys" / "BOGUS-001.yaml"
    _write_yaml(tmp, {
        "id": "BOGUS-001",
        "title": "Unknown type",
        "status": "draft",
    })

    with pytest.raises(ValidationError) as exc:
        loader = ItemLoader(test_dhf_root / "items", project_config=core.config)
        loader.load_file(tmp)

    assert "BOGUS" in str(exc.value)


def test_no_validation_without_config(test_dhf_root):
    """
    TC-SRS-001-VAL-005: No validation when config is absent (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-005

    When ItemLoader is created without a project_config, unknown fields must
    NOT raise errors (backward-compatible behaviour).
    """
    tmp = test_dhf_root / "items" / "02_req_sys" / "SYS-NO-CONFIG.yaml"
    _write_yaml(tmp, {
        "id": "SYS-NO-CONFIG",
        "title": "Item with unknown field",
        "unknown_field_xyz": "ignored without config",
        "status": "draft",
    })

    # No project_config → should load without raising
    loader = ItemLoader(test_dhf_root / "items", project_config=None)
    item = loader.load_file(tmp)
    assert item is not None
    assert item.uid == "SYS-NO-CONFIG"


def test_select_field_invalid_value_rejected(test_dhf_root):
    """
    TC-SRS-001-VAL-006: Invalid select value rejected (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-006

    A field with format='select' must reject values not in the options list.
    """
    core = CompliantFlowCore(test_dhf_root)

    # Find a doc type that has a select field
    select_field = None
    target_doc_type = None
    for dt in core.config.doc_types:
        for prop in dt.properties:
            if isinstance(prop, dict) and prop.get("format") == "select" and prop.get("options"):
                select_field = prop
                target_doc_type = dt
                break
        if select_field:
            break

    if not select_field or not target_doc_type:
        pytest.skip("No select field with options found in test config")

    tmp = test_dhf_root / "items" / target_doc_type.directory / "TEST-SELECT-INVALID.yaml"
    _write_yaml(tmp, {
        "id": f"{target_doc_type.code}-SELECT-INVALID",
        "title": "Bad select value",
        select_field["name"]: "DEFINITELY_NOT_A_VALID_OPTION_XYZ",
        "status": "draft",
    })

    with pytest.raises(ValidationError) as exc:
        loader = ItemLoader(test_dhf_root / "items", project_config=core.config)
        loader.load_file(tmp)

    assert "DEFINITELY_NOT_A_VALID_OPTION_XYZ" in str(exc.value)


def test_core_loads_all_items_with_validation_enabled(test_dhf_root):
    """
    TC-SRS-001-VAL-007: CompliantFlowCore enables validation automatically (API)

    @links: SRS-001
    @test_id: TC-SRS-001-VAL-007

    After config is loaded, CompliantFlowCore passes it to the loader so
    schema validation is active without any extra caller setup.
    """
    core = CompliantFlowCore(test_dhf_root)
    # Validation is enabled; existing items must all be valid
    assert core.loader.project_config is not None, "Loader should have project_config set"
    items = core.get_all_items()
    assert len(items) > 0
