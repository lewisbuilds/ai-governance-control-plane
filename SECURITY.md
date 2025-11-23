# Security Policy

## Reporting a Vulnerability

The AI Governance Control Plane team takes security vulnerabilities seriously. We appreciate your responsible disclosure and will work quickly to address any legitimate security concerns.

### How to Report

**Please DO NOT open a public GitHub issue for security vulnerabilities.** Instead, report privately via GitHub's Security Advisory feature:

1. Visit: https://github.com/lewisbuilds/ai-governance-control-plane/security/advisories
2. Click **"Report a vulnerability"**
3. Fill in the vulnerability details (see guidance below)

**Alternative:** If you prefer email, contact security@lewisbuilds.com with subject line starting with [SECURITY].

### What to Include in Your Report

To help us understand and address the issue quickly, please provide:

- **Title**: Clear, descriptive summary of the vulnerability
- **Description**: Detailed explanation of the vulnerability and its impact
- **Affected Version(s)**: Which version(s) of the project are vulnerable
- **Attack Vector**: How an attacker could exploit this (e.g., network, local, requires authentication)
- **Proof of Concept**: Steps to reproduce, code snippet, or working exploit (optional but helpful)
- **Impact**: Severity assessment (Critical, High, Medium, Low) and potential consequences
- **Suggested Fix**: Any proposed remediation (optional)

**Example:**
```
Title: CVE-2025-XXXXX - Path Traversal in File Upload Handler

Description: The file upload endpoint does not properly sanitize user-supplied filenames, allowing attackers to upload files outside the intended directory via path traversal sequences (e.g., "../").

Affected Versions: v0.2.0, v0.2.1

Attack Vector: Network - unauthenticated attacker can upload files with crafted filenames

Proof of Concept: [steps to trigger the vulnerability]

Impact: HIGH - An attacker can overwrite critical files or place malicious files on the server.

Suggested Fix: Validate and sanitize filenames to prevent path traversal; restrict uploads to a safe directory.
```

### Scope of Vulnerabilities

We're interested in reports that demonstrate:

✅ **In scope:**
- Authentication/authorization bypasses
- Injection attacks (SQL, command, YAML, etc.)
- Cryptographic failures or weak algorithms
- Sensitive data exposure (credentials, PII, audit logs)
- Server-side request forgery (SSRF)
- Insecure deserialization
- Dependency vulnerabilities with demonstrable impact
- Improper access control or privilege escalation
- Configuration weaknesses in default deployments

❌ **Out of scope:**
- Social engineering or phishing attacks
- Physical security issues
- Vulnerabilities in dependencies without demonstrated project impact
- Issues requiring extensive user misuse or misconfiguration
- Missing security headers (unless critical to core functionality)
- Unsubstantiated "could lead to" theoretical vulnerabilities

### Response Process

1. **Acknowledgment (within 24 hours)**: We'll confirm receipt and provide a reference number
2. **Investigation (3-7 days)**: We'll analyze the vulnerability and reproduce it
3. **Assessment (ongoing)**: We'll determine severity and develop a fix
4. **Patch Development (1-4 weeks)**: We'll create a security fix
5. **Release (coordinated)**: We'll release a patched version
6. **Public Disclosure**: We'll publish a security advisory and credit you (unless you prefer anonymity)

### Responsible Disclosure Timeline

- **Day 0**: Vulnerability reported to us
- **Day 1**: Initial acknowledgment
- **Day 7**: First status update
- **Day 30**: Target patch release date (or update on blockers)
- **Day 90**: Public disclosure (if patch not released by then)

We ask that you:
- Do **not** disclose the vulnerability publicly before we've released a patch
- Do **not** test the vulnerability on systems you don't own or have permission to test
- Do **not** access, modify, or exfiltrate data beyond what's needed to demonstrate the vulnerability
- **Allow us reasonable time** to develop and release a fix

### Security Updates

- **Subscribe to releases**: Watch this repository to be notified of security patches
- **Check regularly**: Review the [Releases](https://github.com/lewisbuilds/ai-governance-control-plane/releases) page for security advisories
- **Patch promptly**: Apply security updates as soon as possible after release

### Security Best Practices for Deployment

When deploying this project in production:

1. **Keep dependencies updated**: Regularly run pip-audit or safety check to scan for known vulnerabilities
2. **Use strong credentials**: Set complex passwords for database and service accounts
3. **Enable AIBOM verification**: Use Ed25519 key verification for model artifact signing (see docs/SECURITY-AIBOM.md)
4. **Implement network policies**: Restrict service-to-service communication (see infra/k8s/network-policies/)
5. **Run as non-root**: Ensure containers run with minimal privileges
6. **Enable audit logging**: Ensure audit events are persisted and monitored
7. **Use HTTPS**: Terminate TLS at the gateway in production
8. **Limit exposure**: Restrict API access to trusted networks
9. **Monitor logs**: Set up centralized logging and alerting for security events
10. **Regular backups**: Test backup and restore procedures regularly

### Known Security Considerations

- **Append-only design**: Audit logs and lineage are immutable by design; deletion requires database-level access
- **Policy YAML evaluation**: Policies are evaluated using yaml.safe_load; untrusted policy files should be validated before deployment
- **Multi-tenant**: This version is not designed for multi-tenant deployments; use network isolation if required
- **Rate limiting**: No built-in rate limiting; deploy behind a reverse proxy (nginx, HAProxy) with rate limiting

### Contact

To report a vulnerability or ask security questions:
- **GitHub Security Advisory**: https://github.com/lewisbuilds/ai-governance-control-plane/security/advisories

### Acknowledgments

We deeply appreciate the security researchers who help us keep this project safe. With your permission, we'll acknowledge your contribution in release notes and our security advisory.

---

**Last Updated**: November 2025
