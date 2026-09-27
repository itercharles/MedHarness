"""`verify soup` — the SOUP register against what ships, and against OSV."""

from __future__ import annotations

from pathlib import Path

from medharness.services.envelope import envelope_from


def _parse_accepted_vulns(item: dict, soup_id: str) -> tuple[dict[str, str], list[str]]:
    """Read a SOUP item's ``accepted_vulns`` into {vuln_id: rationale}.

    IEC 62304 §8.1.2 requires SOUP anomalies to be *evaluated*, not necessarily
    fixed. An acceptance is only honoured when it names a specific vulnerability
    ID and records why it is acceptable — a bare ID carries no assessment, and
    blanket acceptance would silently absorb newly published CVEs.

    Returns ({vuln_id: rationale}, malformed_entry_messages).
    """
    accepted: dict[str, str] = {}
    problems: list[str] = []

    for entry in item.get("accepted_vulns") or []:
        if not isinstance(entry, dict):
            problems.append(
                f"{soup_id} — accepted_vulns entry {entry!r} must be a mapping with "
                "'id' and 'rationale'; the vulnerability still blocks."
            )
            continue
        vuln_id = str(entry.get("id") or "").strip()
        rationale = str(entry.get("rationale") or "").strip()
        if not vuln_id:
            problems.append(f"{soup_id} — accepted_vulns entry is missing 'id'.")
            continue
        if not rationale:
            problems.append(
                f"{soup_id} — accepted_vulns entry {vuln_id} is missing 'rationale'; "
                "record why the vulnerability is acceptable or it will keep blocking."
            )
            continue
        accepted[vuln_id] = rationale

    return accepted, problems


_VULN_DETAIL_BUDGET = 25


def _vuln_detail(vuln_id: str, batch_entry: dict, *, fetch: bool) -> dict:
    """Build a reportable vulnerability record for *vuln_id*.

    osv.dev's ``querybatch`` returns only ``id`` and ``modified`` — summary and
    severity live on the per-vulnerability endpoint — so a batch entry alone
    cannot describe what is wrong. Fetch that detail when *fetch* is set, and
    always emit a URL so the finding stays actionable if the lookup fails.
    """
    import json as _json
    import urllib.error
    import urllib.request

    summary = batch_entry.get("summary") or ""
    severity = (
        batch_entry.get("database_specific", {}).get("severity")
        or (batch_entry.get("severity") or [{}])[0].get("score", "")
    )

    if fetch and vuln_id and not summary:
        try:
            with urllib.request.urlopen(
                f"https://api.osv.dev/v1/vulns/{vuln_id}", timeout=10
            ) as resp:
                detail = _json.loads(resp.read())
            summary = detail.get("summary") or (detail.get("details") or "").split("\n")[0]
            severity = severity or detail.get("database_specific", {}).get("severity") or ""
        except (urllib.error.URLError, ValueError, TimeoutError):
            pass  # URL below still identifies the finding

    return {
        "id": vuln_id,
        "summary": summary.strip()[:200],
        "severity": severity,
        "url": f"https://osv.dev/vulnerability/{vuln_id}" if vuln_id else "",
    }


def _drift_messages(drift: dict) -> list[str]:
    """The drift findings that change severity with `--fail-on-drift`."""
    return [
        f"{name} ships but has no SOUP item — it is also never scanned for "
        f"vulnerabilities." for name in drift.get("undocumented", [])
    ] + list(drift.get("misversioned", []))


def soup_gate(
    dhf_path: Path,
    *,
    offline_mode: str = "fail",
    manifest_paths: list[Path] | None = None,
    fail_on_drift: bool = False,
) -> dict:
    """The SOUP register against the manifests, and against known CVEs.

    Both halves of IEC 62304 §8.1.2, because asking them separately gives a
    dangerous answer: a package in a lockfile with no SOUP item is never queried
    for vulnerabilities at all. It does not come back clean — it comes back
    absent.

    Drift warns by default so a project backfilling its register is not blocked;
    `fail_on_drift` makes an undocumented or misversioned component fail.


    For each SOUP item that has both ``name`` and ``ecosystem`` fields, queries
    https://api.osv.dev/v1/querybatch and reports known vulnerabilities.

    Items without an ``ecosystem`` field are skipped with a note so adopters can
    add the field without breaking CI.

    A vulnerability listed in the item's ``accepted_vulns`` (with a rationale) is
    reported as accepted rather than blocking — see :func:`_parse_accepted_vulns`.

    Args:
        offline_mode: ``"fail"`` (default) treats an unreachable osv.dev as a gate
            failure. ``"warn"`` reports the outage but leaves the gate passing, for
            air-gapped or proxy-restricted pipelines where the scan runs elsewhere.

    Returns:
        {
          "passed": bool,
          "soup_count": int,
          "checked_count": int,
          "vulnerable": [{"soup_id", "name", "version", "vulns": [...]}],
          "accepted": [{"soup_id", "name", "version", "vuln_id", "rationale"}],
          "skipped": [{"soup_id", "reason"}],
          "acceptance_problems": [str],
          "error": str | None,
          "summary": str,
        }
    """
    import json as _json
    import urllib.error
    import urllib.request

    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()
    soup_items = [it for it in all_items if it.get("type") == "SOUP"]
    drift = _soup_drift(dhf_path, soup_items, manifest_paths, fail_on_drift)
    drift_blocks = fail_on_drift and bool(
        drift["drift"]["undocumented"] or drift["drift"]["misversioned"]
    )

    checkable: list[dict] = []
    skipped: list[dict] = []
    acceptance_problems: list[str] = []

    for item in soup_items:
        soup_id = item.get("id", "?")
        name = str(item.get("name") or "").strip()
        version = str(item.get("version") or "").strip()
        ecosystem = str(item.get("ecosystem") or "").strip()
        accepted, problems = _parse_accepted_vulns(item, soup_id)
        acceptance_problems.extend(problems)
        if not name or not version:
            skipped.append({"soup_id": soup_id, "reason": "missing name or version"})
            continue
        if not ecosystem:
            skipped.append({"soup_id": soup_id, "reason": "ecosystem not specified — add e.g. ecosystem: PyPI"})
            continue
        checkable.append({
            "soup_id": soup_id, "name": name, "version": version,
            "ecosystem": ecosystem, "accepted": accepted,
        })

    # Assembled once: the gate returns from three places and two of them used
    # to forget, so the JSON said `warnings: []` beside warnings in the log.
    found = drift["drift"]
    base_errors = _drift_messages(found) if drift_blocks else []
    base_warnings = (
        list(acceptance_problems)
        + [f"{item['soup_id']} was not checked: {item['reason']}" for item in skipped]
        + ([] if drift_blocks else _drift_messages(found))
        + [f"{soup_id} has no purpose recorded — §8.1.2 asks why the component "
           f"is used." for soup_id in found.get("undescribed", [])]
        + [f"{soup_id} is in the register but no manifest resolves it."
           for soup_id in found.get("no_longer_shipped", [])]
        + list(found.get("errors", []))
    )

    if not checkable:
        n_soup = len(soup_items)
        return envelope_from("verify soup", {
            "passed": not drift_blocks,
            "errors": base_errors,
            "warnings": base_warnings,
            "soup_count": n_soup,
            "checked_count": 0,
            "vulnerable": [],
            "accepted": [],
            "skipped": skipped,
            "acceptance_problems": acceptance_problems,
            **drift,
            "error": None,
            "summary": (
                f"{n_soup} SOUP item(s) found; none checkable "
                "(add 'ecosystem' field to enable vulnerability scanning)."
            ) if n_soup else "No SOUP items in DHF.",
        })

    queries = [
        {"package": {"name": c["name"], "ecosystem": c["ecosystem"]}, "version": c["version"]}
        for c in checkable
    ]
    body = _json.dumps({"queries": queries}).encode()
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            results = _json.loads(resp.read()).get("results", [])
    except urllib.error.URLError as exc:
        tolerated = offline_mode == "warn"
        outage = f"osv.dev unreachable: {exc}"
        return envelope_from("verify soup", {
            "passed": tolerated and not drift_blocks,
            # The outage belongs in the envelope, not a private key: a caller
            # that handles `errors`/`warnings` for every gate handles this too.
            "errors": base_errors + ([] if tolerated else [outage]),
            "warnings": base_warnings + ([outage] if tolerated else []),
            "soup_count": len(soup_items),
            "checked_count": 0,
            "vulnerable": [],
            "accepted": [],
            "skipped": skipped,
            "acceptance_problems": acceptance_problems,
            **drift,
            "error": f"osv.dev unreachable: {exc}",
            "summary": (
                f"SOUP vulnerability scan skipped — osv.dev unreachable ({exc}). "
                "Gate tolerated the outage (--offline-mode warn); scan SOUP through "
                "your offline process to keep IEC 62304 §8.1.2 evidence complete."
                if tolerated
                else f"SOUP vulnerability check failed: {exc}"
            ),
        })

    vulnerable: list[dict] = []
    accepted_found: list[dict] = []
    detail_budget = _VULN_DETAIL_BUDGET
    for meta, result in zip(checkable, results):
        vulns_raw = result.get("vulns") or []
        if not vulns_raw:
            continue
        blocking = []
        for v in vulns_raw:
            vuln_id = v.get("id", "")
            rationale = meta["accepted"].get(vuln_id)
            if rationale is not None:
                accepted_found.append({
                    "soup_id": meta["soup_id"],
                    "name": meta["name"],
                    "version": meta["version"],
                    "vuln_id": vuln_id,
                    "rationale": rationale,
                })
                continue
            blocking.append(_vuln_detail(vuln_id, v, fetch=detail_budget > 0))
            detail_budget -= 1
        if blocking:
            vulnerable.append({
                "soup_id": meta["soup_id"],
                "name": meta["name"],
                "version": meta["version"],
                "vulns": blocking,
            })

    passed = len(vulnerable) == 0
    n_vuln = sum(len(v["vulns"]) for v in vulnerable)
    summary_parts = [
        f"{len(soup_items)} SOUP item(s), {len(checkable)} checked.",
        f"{n_vuln} unresolved vulnerability(-ies) across {len(vulnerable)} item(s)."
        if not passed
        else "No unresolved vulnerabilities found.",
    ]
    if accepted_found:
        summary_parts.append(f"{len(accepted_found)} documented as accepted.")
    return envelope_from("verify soup", {
        "passed": passed and not drift_blocks,
        # Phrased exactly as a reader needs it — severity and a URL fallback
        # included — so the CLI renders the envelope instead of rebuilding the
        # same line beside it. Two renderers printed every vulnerability twice.
        "errors": [
            f"{item['soup_id']} ({item['name']}@{item['version']}): {v['id']} — "
            + (f"[{v['severity']}] " if v.get("severity") else "")
            + (v.get("summary") or v.get("url") or "see osv.dev")
            for item in vulnerable for v in item["vulns"]
        ] + base_errors,
        "warnings": base_warnings + [
            f"{a['soup_id']}: {a['vuln_id']} accepted — {a['rationale']}"
            for a in accepted_found
        ],
        "soup_count": len(soup_items),
        "checked_count": len(checkable),
        "vulnerable": vulnerable,
        "accepted": accepted_found,
        "skipped": skipped,
        "acceptance_problems": acceptance_problems,
        **drift,
        "error": None,
        "summary": " ".join(summary_parts),
    })


def _soup_drift(
    dhf_path: Path,
    soup_items: list[dict],
    manifest_paths: list[Path] | None,
    fail_on_drift: bool,
) -> dict:
    """The register against the manifests, read-only.

    Writing back is a separate action: a gate that edits the DHF it is judging
    has no business being a gate.
    """
    from medharness.services.soup_sync import (
        collect_manifest_packages,
        diff_against_dhf,
    )

    packages, _parsed, errors = collect_manifest_packages(
        dhf_path, list(manifest_paths or [])
    )
    diff = diff_against_dhf(packages, soup_items)
    return {
        "drift": {
            "manifests_read": len(packages),
            "undocumented": [p["name"] for p in diff["to_create"]],
            "misversioned": [
                f"{e['item']['id']} records {e['old_version']}, manifests resolve "
                f"{e['pkg']['version']}"
                for e in diff["to_update"]
            ],
            "no_longer_shipped": [it["id"] for it in diff["orphans"]],
            # An entry with no purpose satisfies "is it documented" and answers
            # nothing §8.1.2 asks. `build dhf` leaves it empty rather than filling
            # in "Dependency from PyPI", so the gap is visible instead of
            # papered over.
            "undescribed": sorted(
                it["id"] for it in soup_items if not str(it.get("purpose") or "").strip()
            ),
            "blocking": fail_on_drift,
            "errors": errors,
        }
    }
