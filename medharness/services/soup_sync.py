"""Re-export dhfkit.soup_sync for medharness internal consumers."""
from dhfkit.soup_sync import (  # noqa: F401
    diff_against_dhf,
    discover_manifests,
    load_soup_sources,
    parse_cargo_lock,
    parse_go_mod,
    parse_package_json,
    parse_package_lock_json,
    parse_poetry_lock,
    parse_pom_xml,
    parse_pyproject_toml,
    parse_requirements_txt,
    parse_uv_lock,
    sync_soup_items,
)
