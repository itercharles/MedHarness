# SOUP, SBOM and vulnerabilities

The register of third-party software (SOUP, IEC 62304 §8.1.2), and what is built from it. Three commands, run in this order.

## 1. Fill the register: `build soup`

```bash
medharness --dhf DHF build soup
```

Reads your dependency files and creates or updates one SOUP item per package. It writes to the working tree and commits nothing: review with `git diff DHF/`, then commit.

It finds `requirements.txt`, `uv.lock`, `poetry.lock`, `pyproject.toml`, `package.json`, `package-lock.json` and `pnpm-lock.yaml` in the project root. Name a file with `--dependency-file PATH` (repeatable). Prefer a lockfile: a manifest with only version ranges (`^2.1.0`) gives no exact version to scan or list in the SBOM, and the command says so.

### Persistent source configuration

Hardware, an OS, a language with no parser (Go, Cargo, Maven…), or several manifests: list them in `DHF/config/soup-sources.yaml`. It is used whenever no `--dependency-file` is given.

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

A `command` source prints one JSON object per line. Any ecosystem can be fed this way.

## 2. Check it: `verify soup`

```bash
medharness --dhf DHF verify soup
```

Compares the register with your dependency files, then looks each SOUP item that has an `ecosystem` up in [OSV](https://osv.dev). It fails on a known vulnerability. A package missing from the register, or at another version, only warns; `--strict` makes it fail.

**Accept a vulnerability you have assessed.** Many do not affect your product. Record the reason on the SOUP item and the gate stops blocking on that one:

```yaml
accepted_vulns:
  - id: GHSA-x84v-xcm2-53pg
    rationale: "Redirect handling is not reachable: we never follow cross-host redirects. Assessed in CR-018."
```

Both keys are required; without a `rationale` the vulnerability keeps blocking. A new vulnerability in the same package still fails, because acceptance is per ID. Accepted ones stay visible in the output.

**No network.** `verify soup` calls `api.osv.dev` and fails if it cannot. If scanning happens elsewhere, `--on-unreachable warn` lets it pass and records the outage in the answer.

## 3. Release it: the SBOM

`build release` writes `sbom.cdx.json` (CycloneDX 1.6) with the specifications and evidence, from the same register. Each component's `bom-ref` is its SOUP id, so a finding leads back to the item that justifies it. A package in your dependency files but not in the register is still listed, so the release does not understate what ships.

A component with a version range, or an ecosystem with no package-URL type, is listed without a `purl`, and the release names the reason on a `WARN [release]` line. Fix it by pinning the version in the register.
