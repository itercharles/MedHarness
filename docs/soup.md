# SOUP, SBOM and vulnerabilities

The register of third-party software, and what is built from it.

## Syncing SOUP items from dependency manifests (`medharness build soup`)

The `build soup` command reads dependency files from your project and creates or updates SOUP items in the DHF. It supports nine lockfile/manifest formats across multiple ecosystems:

| File | Ecosystem |
|------|-----------|
| `requirements.txt` | PyPI (pinned `==` only) |
| `uv.lock` | PyPI |
| `poetry.lock` | PyPI |
| `pyproject.toml` | PyPI (best-effort; prefer lockfile) |
| `package.json` | npm |
| `package-lock.json` | npm (v1/v2/v3) |
| `go.mod` | Go |
| `Cargo.lock` | crates.io |
| `pom.xml` | Maven |

### Auto-discovery

With no flags, `build soup` looks for the supported files in the project root automatically:

```bash
medharness --dhf DHF build soup
```

To target a specific file:

```bash
medharness --dhf DHF build soup --manifest uv.lock
medharness --dhf DHF build soup --manifest go.mod --manifest Cargo.lock
```

### Persistent source configuration (`soup-sources.yaml`)

For projects with non-standard layouts, multiple manifests, hardware SOUP, or third-party scanning tools, create `DHF/config/soup-sources.yaml`. This file is checked by default whenever no `--manifest` flags are given:

```yaml
sources:
  # Manifest files — paths relative to project root
  - type: manifest
    path: backend/requirements.txt

  - type: manifest
    path: frontend/package-lock.json

  # External tool — stdout must be NDJSON: {"name":…,"version":…,"ecosystem":…}
  - type: command
    run: |
      syft . -o syft-json=- | python3 -c "
      import sys, json
      for a in json.load(sys.stdin)['artifacts']:
          print(json.dumps({'name': a['name'], 'version': a['version'], 'ecosystem': a['type']}))
      "

  # Manual entries — hardware, OS, commercial tools (no ecosystem = no CVE scan)
  - type: manual
    items:
      - name: Ubuntu Server
        version: "22.04.3 LTS"
        manufacturer: Canonical Ltd.
        license: GPL-2.0
        ecosystem: null
      - name: PostgreSQL
        version: "14.10"
        manufacturer: PostgreSQL Global Development Group
        ecosystem: null
```

Source priority when multiple are configured: explicit `--manifest` flags → `--from-command` flags → `soup-sources.yaml` → auto-discovery.

### Applying changes

`build soup` creates and updates the SOUP items in the working tree, and commits
nothing; review the change with `git diff DHF/` before you commit it:

```bash
medharness --dhf DHF build soup
medharness --dhf DHF build soup --manifest uv.lock
```

## Exporting an SBOM

The SOUP register already holds what an SBOM needs — name, version, ecosystem,
licence, supplier — recorded there because IEC 62304 §8.1.2 asks for it. FDA's
premarket cybersecurity guidance and the EU Cyber Resilience Act want that in a
standard machine-readable format. `build release` writes it as
`sbom.cdx.json`, beside the specifications. Without `--write` the DHF is not
changed:

```bash
medharness build release --version 1.2.0 --out-dir release
```

The output is CycloneDX 1.6 JSON, checked against the official schema by the
test suite rather than by assertion. Each component carries its SOUP id as
`bom-ref` and as a `dhfkit:soup_id` property, so a finding in the SBOM leads back
to the DHF item holding the justification and any documented vulnerability
acceptance.

**A component gets no `purl` when one cannot be built honestly**, and the release
names the reason per component as a `WARN [release]` line and in its `warnings`. Two causes need different fixes:

- the ecosystem has no package-URL type — the mapping is a fixed table;
- the version is a range (`^34.15.1`) rather than a version. §8.1.2 wants the
  version actually in use, and a purl built from a range resolves against a real
  registry and matches nothing.

The component is still listed either way, and its `version` is reported exactly as
the DHF records it — the SBOM does not clean up the register's data. A wrong purl resolves against a real
registry, so an absent one is safer than a guessed one. The mapped ecosystems are
PyPI, npm, Go, Maven, crates.io, NuGet, RubyGems, Packagist, Hex and Pub.

Regenerating an unchanged SBOM leaves the file alone, timestamp included — the
serial number is derived from the component set rather than randomised, so a
regeneration is not a diff in a repository whose purpose is showing what changed.

Everything `build release` writes:

```
release/release-baseline.json
release/software-bom.json      # dhfkit's own shape, unchanged
release/sbom.cdx.json          # the same release in CycloneDX
release/evidence-manifest.json # every file above and below, hashed
release/specifications/ …      # plus traceability and test evidence
```

`--manifest` accepts every format `build soup` reads — `requirements.txt`, `uv.lock`, `poetry.lock`, `pyproject.toml`, `package.json`, `package-lock.json`, `go.mod`, `Cargo.lock`, `pom.xml`.

The release SBOM merges both registers. A package read from a `--manifest` but
absent from the SOUP register still ships, so it appears — carrying a
`dhfkit:manifest_source` property instead of a `dhfkit:soup_id`. Leaving it out
would understate the release and hide the §8.1.2 gap `build soup` exists to close.
Where a package is in both, the SOUP item wins: it carries the licence, supplier
and any documented vulnerability acceptance that the manifest does not.

## SOUP vulnerability scanning (`verify soup`)

SOUP items that carry an `ecosystem` field (e.g. `PyPI`, `npm`, `Go`) are checked against the [OSV vulnerability database](https://osv.dev) on every run:

```bash
medharness --dhf DHF verify soup
```

Add the `ecosystem` field to each SOUP item to enable scanning:

```yaml
id: SOUP-012
name: requests
version: "2.28.2"
ecosystem: PyPI     # enables CVE scanning via osv.dev
manufacturer: Python Software Foundation
purpose: HTTP client for REST API calls
```

Items without `ecosystem` are skipped with a note. The command exits non-zero if any unresolved vulnerabilities are found and outputs structured JSON to stdout. Wire it into CI after `verify dhf` to catch unresolved CVEs before release.

### Accepting a vulnerability you have assessed

IEC 62304 §8.1.2 requires SOUP anomalies to be *evaluated* — not necessarily fixed. Many CVEs do not affect how your product uses the package, and some have no upstream patch. Record the assessment on the SOUP item and the gate stops blocking on it:

```yaml
id: SOUP-012
name: requests
version: "2.28.2"
ecosystem: PyPI
accepted_vulns:
  - id: GHSA-x84v-xcm2-53pg
    rationale: "Affected redirect handling is not reachable — we never follow cross-host redirects. Assessed in CR-018."
```

Both keys are required. An entry without a `rationale` — or a bare ID string — is reported as a warning and the vulnerability **keeps blocking**, because an acceptance with no recorded reason is not an assessment.

Acceptance is per-vulnerability-ID by design. A newly published CVE against the same package still fails the gate, so blanket suppression cannot silently absorb future findings. `verify soup` prints accepted entries as `ACCEPTED [soup-vuln]` lines and lists them in the `warnings` of its answer, so they stay visible in CI logs and evidence bundles.

### Air-gapped and proxy-restricted pipelines

`verify soup` calls `api.osv.dev`. Where that host is unreachable, the gate fails by default rather than passing silently. If your SOUP scanning happens through a separate offline process, tolerate the outage explicitly:

```bash
medharness --dhf DHF verify soup --offline-mode warn
```

The gate then passes, but still records the outage in the `warnings` of its answer and prints a `WARN [soup-vuln]` line — so the gap is visible in the evidence bundle rather than invisible. Keep the default (`--offline-mode fail`) anywhere the scan is expected to run.
