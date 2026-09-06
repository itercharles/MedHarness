"""CycloneDX SBOM built from the DHF's SOUP items.

The SOUP register already holds what an SBOM needs — name, version, ecosystem,
licence, manufacturer — recorded there because IEC 62304 §8.1.2 asks for it. What
was missing was the serialisation: FDA's cybersecurity guidance and the EU Cyber
Resilience Act want a machine-readable file in a standard format, not a project's
own YAML.

No CycloneDX library is used. The subset of the 1.6 schema an SBOM of libraries
needs is small and stable, and a dependency added here would become a SOUP item
in every project that adopts this tool — a cost the tool would then ask its users
to document.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SPEC_VERSION = "1.6"

#: The DHF records the OSV ecosystem, because that is what the vulnerability
#: scan queries. purl uses its own type names, so the two have to be mapped
#: rather than assumed equal — "Go" and "crates.io" are neither purl types.
_PURL_TYPES = {
    "pypi": "pypi",
    "npm": "npm",
    "go": "golang",
    "maven": "maven",
    "crates.io": "cargo",
    "cargo": "cargo",
    "nuget": "nuget",
    "rubygems": "gem",
    "packagist": "composer",
    "hex": "hex",
    "pub": "pub",
}

#: A namespace is separated from the name differently per ecosystem: Maven joins
#: groupId and artifactId with ':', npm scopes with '@scope/'.
_NAMESPACE_SEPARATORS = {"maven": ":", "npm": "/"}


def _quote(text: str) -> str:
    """Percent-encode the characters purl reserves, leaving the rest readable."""
    return "".join(
        c if re.match(r"[A-Za-z0-9._~!$&'()*+,;=:@-]", c) else f"%{ord(c):02X}"
        for c in text
    )


def purl_for(name: str, version: str, ecosystem: str) -> str | None:
    """Package URL for a SOUP item, or None when the ecosystem is unmapped.

    Returning None rather than guessing matters: a wrong purl is worse than an
    absent one, because a consumer resolves it against a real registry.
    """
    purl_type = _PURL_TYPES.get((ecosystem or "").strip().lower())
    if not purl_type or not name:
        return None

    namespace = ""
    bare = name.strip()
    separator = _NAMESPACE_SEPARATORS.get(purl_type)
    if separator and separator in bare:
        if purl_type == "npm" and not bare.startswith("@"):
            pass  # a '/' without a leading '@' is not an npm scope
        else:
            namespace, _, bare = bare.partition(separator)

    path = f"{_quote(namespace)}/{_quote(bare)}" if namespace else _quote(bare)
    return f"pkg:{purl_type}/{path}@{_quote(version)}" if version else f"pkg:{purl_type}/{path}"


def _component(item: dict) -> dict[str, Any]:
    """One SOUP item as a CycloneDX component."""
    name = str(item.get("name") or item.get("title") or "").strip()
    version = str(item.get("version") or "").strip()
    ecosystem = str(item.get("ecosystem") or "").strip()

    component: dict[str, Any] = {
        "type": "library",
        # The SOUP id, so a finding in the SBOM leads back to the DHF item that
        # carries the justification and any documented vulnerability acceptance.
        "bom-ref": str(item.get("id") or name),
        "name": name,
        "version": version,
    }

    purl = purl_for(name, version, ecosystem)
    if purl:
        component["purl"] = purl

    supplier = str(item.get("manufacturer") or "").strip()
    if supplier:
        component["supplier"] = {"name": supplier}

    licence = str(item.get("license") or "").strip()
    if licence:
        # `name` rather than `id`: the field is free text in the DHF and an
        # unvalidated SPDX id would be a false claim about the licence.
        component["licenses"] = [{"license": {"name": licence}}]

    homepage = str(item.get("homepage") or "").strip()
    if homepage:
        component["externalReferences"] = [{"type": "website", "url": homepage}]

    description = str(item.get("purpose") or "").strip()
    if description:
        component["description"] = description

    properties = [{"name": "dhfkit:soup_id", "value": str(item.get("id") or "")}]
    if ecosystem:
        properties.append({"name": "dhfkit:ecosystem", "value": ecosystem})
    accepted = item.get("accepted_vulns") or []
    for entry in accepted:
        vuln_id = entry.get("id") if isinstance(entry, dict) else str(entry)
        if vuln_id:
            properties.append({"name": "dhfkit:accepted_vuln", "value": str(vuln_id)})
    component["properties"] = properties

    return component


def _serial_number(project: str, components: list[dict]) -> str:
    """A serial derived from content, so regeneration does not churn the file.

    A random UUID per run would make every regeneration a diff in a repository
    whose whole purpose is showing what changed.
    """
    seed = project + "\n" + "\n".join(
        f"{c.get('bom-ref')}|{c.get('name')}|{c.get('version')}" for c in components
    )
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, seed)}"


def build_sbom(
    items: list[dict],
    project_name: str,
    tool_version: str,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Assemble the CycloneDX document. Pure — no filesystem, no clock."""
    components = sorted(
        (_component(i) for i in items),
        key=lambda c: (c["name"].lower(), c["version"]),
    )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "serialNumber": _serial_number(project_name, components),
        "version": 1,
        "metadata": {
            "timestamp": timestamp or datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "tools": {
                "components": [
                    {"type": "application", "name": "dhfkit", "version": tool_version}
                ]
            },
            "component": {
                "type": "application",
                "bom-ref": "subject",
                "name": project_name,
            },
        },
        "components": components,
    }


def _without_timestamp(document: dict) -> dict:
    stripped = json.loads(json.dumps(document))
    stripped.get("metadata", {}).pop("timestamp", None)
    return stripped


def write_sbom(document: dict, output_path: Path) -> tuple[Path, bool]:
    """Write the SBOM, preserving an existing file's timestamp when unchanged.

    Returns ``(path, changed)``. Regenerating on a later day must not rewrite a
    file whose contents are identical — the same churn that once made every
    document regeneration look like a content change.
    """
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text())
        except (OSError, json.JSONDecodeError):
            existing = None
        if existing and _without_timestamp(existing) == _without_timestamp(document):
            return output_path, False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n")
    return output_path, True
