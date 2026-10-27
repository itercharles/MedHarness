"""`verify dhf`: the DHF holds together — schema, links, required links, cycles, states (SRS-035 to SRS-042)."""

from __future__ import annotations

from pathlib import Path

import yaml

from dhfkit.paths import DEFAULTS_DIR
from dhfkit.store import open_store
from medharness.validation.case import Case, check, invoke
from medharness.validation.project import edit, item_path, keep_the_starter_text, scaffolded


def starter_text_kept(root: Path) -> None:
    scaffolded(root, "Structure")
    keep_the_starter_text(root / "DHF")


def as_init_writes_it(root: Path) -> None:
    scaffolded(root, "Structure")


def _verify(root: Path, *flags: str) -> tuple[int, dict, str]:
    return invoke(root, "verify", "dhf", *flags)


def _fails(root: Path, *needles: str, flags: tuple[str, ...] = ()) -> tuple[dict, str]:
    code, answer, stderr = _verify(root, *flags)
    check(code == 1 and answer["passed"] is False, f"exited {code} with passed={answer['passed']}: {answer['errors']}")
    for needle in needles:
        check(any(needle in e for e in answer["errors"]), f"no error says {needle!r}: {answer['errors']}")
    return answer, stderr


def _passes(root: Path, *flags: str) -> tuple[dict, str]:
    code, answer, stderr = _verify(root, *flags)
    check(code == 0 and answer["passed"] is True and answer["errors"] == [], f"exited {code}; errors: {answer['errors']}")
    return answer, stderr


def _new(root: Path, template: str, uid: str, **fields) -> None:
    source = item_path(root, template)
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data.update({"id": uid, "title": uid, "content": "c", **fields})
    (source.parent / f"{uid}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def _append(root: Path, uid: str, text: str) -> None:
    path = item_path(root, uid)
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def _global(root: Path, text: str) -> None:
    path = root / "DHF" / "config" / "global.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\n" + text, encoding="utf-8")


# --- SRS-035: the schema -------------------------------------------------------------------------

def undeclared_field(root: Path) -> None:
    _append(root, "RISK-001", "typo_field: oops\n")
    answer, _ = _fails(root)
    check(any("RISK-001" in e and "typo_field" in e for e in answer["errors"]),
          f"no error names RISK-001 and typo_field: {answer['errors']}")


def item_with_no_id(root: Path) -> None:
    path = item_path(root, "SRS-001")
    path.write_text("".join(line for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
                            if not line.startswith("id:")), encoding="utf-8")
    answer, _ = _fails(root)
    check(any("SRS-001.yaml" in e and "'id'" in e for e in answer["errors"]), f"the file is not named: {answer['errors']}")


def empty_item_file(root: Path) -> None:
    item_path(root, "CRS-001").write_text("# nothing here any more\n", encoding="utf-8")
    _fails(root, "CRS-001.yaml is empty")


def mistyped_field_is_a_message(root: Path) -> None:
    _append(root, "RISK-001", "typo_field: oops\n")
    _, stderr = _fails(root)
    check("Traceback" not in stderr and "RISK-001" in stderr and "typo_field" in stderr, f"stderr: {stderr[-400:]!r}")


# --- SRS-036: links ------------------------------------------------------------------------------

def dangling_link(root: Path) -> None:
    path = item_path(root, "RCM-001")
    path.write_text(path.read_text(encoding="utf-8").replace("RISK-001", "RISK-404"), encoding="utf-8")
    answer, stderr = _fails(root, "RISK-404: target does not exist")
    check("FAIL [dangling]" in stderr, f"stderr: {stderr[-400:]!r}")


def dangling_link_in_a_multiselect(root: Path) -> None:
    edit(root, "DEF-001", violated_requirements=["SRS-999"])
    _fails(root, "DEF-001.violated_requirements → SRS-999: target does not exist")


def link_to_the_wrong_type(root: Path) -> None:
    edit(root, "SYS-001", satisfies=["CRS-001", "RISK-001"])
    _fails(root, "SYS-001.satisfies → RISK-001: RISK is not one of CRS")


def link_in_the_wrong_field_is_no_coverage(root: Path) -> None:
    _new(root, "SRS-001", "SRS-002", title="Second", content="Second requirement.")
    edit(root, "SWDD-001", module=["MODULE-001", "SRS-002"])
    _fails(root, "SWDD-001.module → SRS-002", "SRS->SWDD: 1 uncovered", flags=("--strict",))


def link_in_a_field_of_any_type(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-001", "RISK-001", "SOUP-001"])
    _passes(root, "--strict")


# --- SRS-037: required links ---------------------------------------------------------------------

def _sys_errors(root: Path) -> tuple[int, list[str]]:
    code, answer, _ = _verify(root)
    return code, [e for e in answer["errors"] if e.startswith("SYS-002")]


def sys_with_no_origin(root: Path) -> None:
    _new(root, "SYS-001", "SYS-002", satisfies=[])
    code, errors = _sys_errors(root)
    check(code == 1 and errors == ["SYS-002: SYS satisfies → CRS (count=0, need ≥1), or covered by RCM"],
          f"exited {code}: {errors}")


def sys_with_an_origin(root: Path) -> None:
    _new(root, "SYS-001", "SYS-002", satisfies=["CRS-001"])
    _passes(root)
    _new(root, "SYS-001", "SYS-002", satisfies=[])
    _new(root, "RCM-001", "RCM-002", mitigates=["RISK-001"], implements=["SYS-002"])
    _passes(root)


def changed_rule_is_applied(root: Path) -> None:
    _global(root, "required_traceability:\n- source_type: SYS\n  direction: upstream\n  field: satisfies\n"
                  "  target_type: CRS\n  min_count: 1\n")
    _new(root, "SYS-001", "SYS-002", satisfies=[])
    _new(root, "RCM-001", "RCM-002", mitigates=["RISK-001"], implements=["SYS-002"])
    errors = _sys_errors(root)[1]
    check(errors == ["SYS-002: SYS satisfies → CRS (count=0, need ≥1)"], f"the project's rule is not applied: {errors}")


def dropped_rules_ask_nothing(root: Path) -> None:
    _global(root, "required_traceability: []\n")
    _new(root, "SYS-001", "SYS-002", satisfies=[])
    code, errors = _sys_errors(root)
    check(code == 0 and errors == [], f"exited {code}: {errors}")


# --- SRS-038: cycles -----------------------------------------------------------------------------

def reversed_chain(root: Path) -> None:
    edit(root, "SYS-001", satisfies=["SRS-001"])
    answer, _ = _fails(root, "Traceability cycle")
    cycle = next(e for e in answer["errors"] if "Traceability cycle" in e)
    check("SRS-001" in cycle and "SYS-001" in cycle, f"the cycle does not name its items: {cycle!r}")


def no_cycle_reported(root: Path) -> None:
    code, answer, _ = _verify(root)
    check(code == 0 and not any("cycle" in e.lower() for e in answer["errors"]), f"exited {code}: {answer['errors']}")


# --- SRS-039: states -----------------------------------------------------------------------------

def status_that_is_no_state(root: Path) -> None:
    edit(root, "DEF-001", status="banana")
    _, stderr = _fails(root, "DEF-001: status 'banana' is not a state of DEF (one of ")
    check("FAIL [status] DEF-001" in stderr, f"stderr: {stderr[-400:]!r}")


def lifecycle_takes_only_its_own_states(root: Path) -> None:
    edit(root, "CR-001", status="draft")
    _fails(root, "CR-001: status 'draft' is not a state of CR")


def no_lifecycle_takes_the_global_states(root: Path) -> None:
    edit(root, "SRS-001", status="approved")
    _passes(root)
    edit(root, "SRS-001", status="banana")
    _fails(root, "SRS-001: status 'banana'")


# --- SRS-040: --strict ---------------------------------------------------------------------------

def _without_design(root: Path) -> None:
    item_path(root, "SWDD-001").unlink()


def gap_warns(root: Path) -> None:
    _without_design(root)
    answer, stderr = _passes(root)
    check(answer["warnings"] and "WARN [coverage]" in stderr and "FAIL [coverage]" not in stderr, f"stderr: {stderr[-400:]!r}")


def gap_fails_under_strict(root: Path) -> None:
    _without_design(root)
    _, stderr = _fails(root, flags=("--strict",))
    check("FAIL [coverage]" in stderr, f"stderr: {stderr[-400:]!r}")


def placeholder_text(root: Path) -> None:
    answer, _ = _passes(root)
    mentions = [w for w in answer["warnings"] if w.startswith("SRS-001: placeholder")]
    check(len(mentions) == 1 and "title, content" in mentions[0], f"warnings: {answer['warnings']}")
    _, stderr = _fails(root, "SRS-001: placeholder text in title, content", flags=("--strict",))
    check("[placeholder] SRS-001" in stderr, f"stderr: {stderr[-400:]!r}")


def passed_agrees_with_the_exit_code(root: Path) -> None:
    _without_design(root)
    for flags, expected in (((), True), (("--strict",), False)):
        code, answer, _ = _verify(root, *flags)
        check(answer["passed"] is expected and (code == 0) is expected, f"{flags}: exited {code}, passed={answer['passed']}")


# --- SRS-041: a check that could not run ---------------------------------------------------------

def scan_that_raises(root: Path) -> None:
    """Fault injection: every load after the first raises, as an unreadable store would."""
    store = type(open_store(root / "DHF"))
    real = store.list_items
    calls = []

    def flaky(self, *args, **kwargs):
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("the store went away")
        return real(self, *args, **kwargs)

    store.list_items = flaky
    try:
        _fails(root, "could not be checked")
    finally:
        store.list_items = real


def cr_type_without_the_plan_fields(root: Path) -> None:
    data = yaml.safe_load((DEFAULTS_DIR / "config" / "doc_types" / "cr.yaml").read_text(encoding="utf-8"))
    data["properties"] = [p for p in data["properties"]
                          if not (isinstance(p, dict) and p["name"] in ("impact_analysis", "triage_result"))]
    (root / "DHF" / "config" / "doc_types").mkdir(exist_ok=True)
    (root / "DHF" / "config" / "doc_types" / "cr.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    _fails(root, "CR does not declare triage_result, impact_analysis")


def healthy_dhf_reports_none(root: Path) -> None:
    code, answer, _ = _verify(root)
    check(code == 0 and not any("could not be checked" in e for e in answer["errors"]), f"exited {code}: {answer['errors']}")


# --- SRS-042: a consistent DHF passes ------------------------------------------------------------

def starter_chain_passes_strict(root: Path) -> None:
    _passes(root, "--strict")


def clean_scaffold_passes(root: Path) -> None:
    _, stderr = _passes(root)
    check("FAIL" not in stderr, f"stderr: {stderr[-400:]!r}")


CASES = [
    Case("undeclared_field", "SRS-035", ("T1",), starter_text_kept, undeclared_field, tools=()),
    Case("item_with_no_id", "SRS-035", ("T2",), starter_text_kept, item_with_no_id, tools=()),
    Case("empty_item_file", "SRS-035", ("T3",), starter_text_kept, empty_item_file, tools=()),
    Case("mistyped_field_is_a_message", "SRS-035", ("T4",), starter_text_kept, mistyped_field_is_a_message, tools=()),
    Case("dangling_link", "SRS-036", ("T1",), as_init_writes_it, dangling_link, tools=()),
    Case("dangling_link_in_a_multiselect", "SRS-036", ("T2",), starter_text_kept, dangling_link_in_a_multiselect, tools=()),
    Case("link_to_the_wrong_type", "SRS-036", ("T3",), starter_text_kept, link_to_the_wrong_type, tools=()),
    Case("link_in_the_wrong_field_is_no_coverage", "SRS-036", ("T4",), starter_text_kept,
         link_in_the_wrong_field_is_no_coverage, tools=()),
    Case("link_in_a_field_of_any_type", "SRS-036", ("T5",), starter_text_kept, link_in_a_field_of_any_type, tools=()),
    Case("sys_with_no_origin", "SRS-037", ("T1",), starter_text_kept, sys_with_no_origin, tools=()),
    Case("sys_with_an_origin", "SRS-037", ("T2",), starter_text_kept, sys_with_an_origin, tools=()),
    Case("changed_rule_is_applied", "SRS-037", ("T3",), starter_text_kept, changed_rule_is_applied, tools=()),
    Case("dropped_rules_ask_nothing", "SRS-037", ("T4",), starter_text_kept, dropped_rules_ask_nothing, tools=()),
    Case("reversed_chain", "SRS-038", ("T1",), as_init_writes_it, reversed_chain, tools=()),
    Case("no_cycle_reported", "SRS-038", ("T2",), as_init_writes_it, no_cycle_reported, tools=()),
    Case("status_that_is_no_state", "SRS-039", ("T1",), starter_text_kept, status_that_is_no_state, tools=()),
    Case("lifecycle_takes_only_its_own_states", "SRS-039", ("T2",), starter_text_kept,
         lifecycle_takes_only_its_own_states, tools=()),
    Case("no_lifecycle_takes_the_global_states", "SRS-039", ("T3",), starter_text_kept,
         no_lifecycle_takes_the_global_states, tools=()),
    Case("gap_warns", "SRS-040", ("T1",), as_init_writes_it, gap_warns, tools=()),
    Case("gap_fails_under_strict", "SRS-040", ("T2",), as_init_writes_it, gap_fails_under_strict, tools=()),
    Case("placeholder_text", "SRS-040", ("T3",), as_init_writes_it, placeholder_text, tools=()),
    Case("passed_agrees_with_the_exit_code", "SRS-040", ("T4",), as_init_writes_it, passed_agrees_with_the_exit_code, tools=()),
    Case("scan_that_raises", "SRS-041", ("T1",), as_init_writes_it, scan_that_raises, tools=()),
    Case("cr_type_without_the_plan_fields", "SRS-041", ("T2",), starter_text_kept, cr_type_without_the_plan_fields, tools=()),
    Case("healthy_dhf_reports_none", "SRS-041", ("T3",), as_init_writes_it, healthy_dhf_reports_none, tools=()),
    Case("starter_chain_passes_strict", "SRS-042", ("T1",), starter_text_kept, starter_chain_passes_strict, tools=()),
    Case("clean_scaffold_passes", "SRS-042", ("T2",), as_init_writes_it, clean_scaffold_passes, tools=()),
]
