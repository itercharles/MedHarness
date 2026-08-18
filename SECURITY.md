# Security Policy

## Supported Versions

The latest minor release always receives security fixes. Older minor versions are not actively patched.

| Version | Supported |
|---------|-----------|
| 0.11.x  | ✓         |
| < 0.11  | ✗         |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Open a [GitHub Security Advisory](https://github.com/itercharles/MedHarness/security/advisories/new)
(confidential — not visible to the public until disclosed).

Include: affected version, description, reproduction steps, potential impact.

Response time: We aim to acknowledge within 48 hours and provide a fix timeline within 7 days.

## Scope

MedHarness is a development tooling library. Security issues include:
- Code execution via malicious DHF YAML/config files
- Path traversal in DHF directory resolution
- Credential exposure via generated workflow templates
