# Security Policy

## Report a vulnerability

We take security reports seriously and will respond quickly. Please report problems privately.

**Do not open a public GitHub issue for a security problem.** Use GitHub Security Advisories instead:

1. Go to https://github.com/lewisbuilds/ai-governance-control-plane/security/advisories
2. Select **Report a vulnerability**.
3. Fill in the details described below.

If you prefer email, write to security@lewisbuilds.com and start the subject with [SECURITY].

### What to include

- **Title:** a short, clear summary.
- **Description:** what the problem is and why it matters.
- **Affected versions:** which versions have the problem.
- **Attack vector:** how someone could exploit it, such as over the network or locally, and whether they need to log in.
- **Proof of concept:** steps, code, or an exploit. This is optional but helpful.
- **Impact:** how severe it is (Critical, High, Medium, or Low) and what could happen.
- **Suggested fix:** your idea for a fix. This is optional.

Example:

```text
Title: Path traversal in file upload handler

Description: The upload endpoint does not clean user supplied file names. An attacker can write files outside the upload folder by using "../" in the name.

Affected versions: v0.2.0, v0.2.1

Attack vector: Network. No login is needed.

Proof of concept: [steps to reproduce]

Impact: High. An attacker can overwrite important files or place malicious files on the server.

Suggested fix: Clean the file name and keep uploads inside a safe folder.
```

### What is in scope

- Bypassing login or permission checks
- Injection attacks (SQL, command, YAML, and similar)
- Weak or broken cryptography
- Exposure of sensitive data such as credentials, personal data, or audit logs
- Server side request forgery (SSRF)
- Unsafe deserialization
- Dependency problems with a demonstrated impact on this project
- Broken access control or privilege escalation
- Weak settings in the default deployment

### What is out of scope

- Social engineering or phishing
- Physical security
- Dependency problems with no demonstrated impact on this project
- Problems that need major misuse or misconfiguration
- Missing security headers, unless they are critical
- Theoretical issues with no evidence

## What happens after you report

1. **Within 24 hours:** we confirm we received your report and give you a reference number.
2. **3 to 7 days:** we reproduce and investigate the problem.
3. **Ongoing:** we decide how severe it is and work on a fix.
4. **1 to 4 weeks:** we build the fix.
5. **Release:** we ship a patched version.
6. **Disclosure:** we publish an advisory and credit you, unless you prefer to stay anonymous.

### Disclosure timeline

- **Day 0:** you report the problem.
- **Day 1:** we acknowledge it.
- **Day 7:** we send a first status update.
- **Day 30:** target date for the patch, or an update on what is blocking it.
- **Day 90:** public disclosure, even if the patch is not ready.

Please:

- Do not share the problem publicly before we release a patch.
- Do not test on systems you do not own or have permission to test.
- Do not read, change, or copy data beyond what you need to show the problem.
- Give us a reasonable amount of time to fix it.

## Stay up to date

- Watch this repository to hear about security patches.
- Check the [Releases](https://github.com/lewisbuilds/ai-governance-control-plane/releases) page for advisories.
- Apply security updates as soon as you can.

## Before you deploy

This project is a demo. If you adapt it for real use, do these things first:

1. **Update dependencies.** Run `pip-audit` regularly to find known vulnerabilities.
2. **Use strong passwords** for the database and any service accounts.
3. **Turn on AIBOM verification** with an Ed25519 key to check model signatures. See [docs/SECURITY-AIBOM.md](docs/SECURITY-AIBOM.md).
4. **Add network policies** to limit which services can talk to each other. See `infra/k8s/network-policies/`.
5. **Run containers as a normal user** with the fewest privileges possible.
6. **Keep audit logs** and monitor them.
7. **Use HTTPS.** Terminate TLS at the gateway.
8. **Limit access** to trusted networks.
9. **Collect logs centrally** and set up alerts for security events.
10. **Back up the database** and test restores regularly.

## Known limits

- **Append only data:** audit and lineage records are not meant to change. Deleting one needs direct database access.
- **Policy files:** policies are loaded with `yaml.safe_load`. Review any policy file from an untrusted source before you use it.
- **One customer only:** this version does not separate multiple customers. Use network isolation if you need that.
- **No rate limiting:** put the gateway behind a reverse proxy such as nginx or HAProxy that limits request rates.

## Contact

Report vulnerabilities or ask security questions through [GitHub Security Advisories](https://github.com/lewisbuilds/ai-governance-control-plane/security/advisories).

## Thanks

We are grateful to the researchers who help keep this project safe. With your permission, we will credit you in the release notes and the advisory.

**Last updated:** November 2026
