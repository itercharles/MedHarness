# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest | Yes |
| < latest | No |

Only the latest release receives security updates.

## Reporting a Vulnerability

Do **not** open a public issue for security vulnerabilities.

Email security concerns to the maintainers. Include:

- Description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Any suggested remediation

You will receive a response within 5 business days. If the vulnerability is
confirmed, a fix will be released through the normal release process.

## Security Considerations for CompliantFlow

CompliantFlow runs locally and does not transmit DHF data to external services
unless explicitly configured (e.g. Gemini API for semantic compliance checks).

- DHF repositories contain regulated design history data. Treat them as
  confidential.
- CI secrets (GEMINI_API_KEY, DHF_REPO_TOKEN, etc.) must never be stored in
  DHF YAML files or committed to repositories.
- The `compliantflow init` scaffolding generates CI workflows with placeholder
  secrets — replace them with actual values before pushing.
