# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✓         |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email: itercharles@163.com

Include: affected version, description, reproduction steps, potential impact.

Response time: We aim to acknowledge within 48 hours and provide a fix timeline within 7 days.

## Scope

MedHarness is a development tooling library. Security issues include:
- Code execution via malicious DHF YAML/config files
- Path traversal in DHF directory resolution
- Credential exposure via generated workflow templates
