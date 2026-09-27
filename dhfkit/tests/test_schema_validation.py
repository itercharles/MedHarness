"""The schema check: a clean DHF passes, an undeclared field fails."""

from dhfkit.local_adapter import LocalDHFAdapter


def test_a_clean_dhf_passes(populated_dhf):
    assert LocalDHFAdapter(populated_dhf).validate_schema()["valid"]


def test_an_unknown_field_fails(populated_dhf):
    bad_file = populated_dhf / "items" / "02_sys" / "SYS-001.yaml"
    bad_file.write_text(bad_file.read_text(encoding="utf-8")
                        + "\nunknown_field_xyz: should_not_be_here\n", encoding="utf-8")
    result = LocalDHFAdapter(populated_dhf).validate_schema()
    assert not result["valid"]
    assert "unknown_field_xyz" in " ".join(result["errors"])
