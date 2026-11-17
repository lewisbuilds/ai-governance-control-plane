# Interview Guide

## 90-second project overview

> I built a small self-hosted governance control plane with FastAPI, PostgreSQL, and Docker Compose. It separates three things that are often mixed together: model lineage registration, policy evaluation, and audit evidence. A gateway exposes an allowlisted REST API, policy rules are readable YAML, and audit decisions are chained to the previous event hash. I kept the deployment to four application containers and PostgreSQL so the demo is easy to run without Kubernetes. The current version is a REST service set; the `mcp-*` names do not mean it implements the Model Context Protocol. It is a portfolio foundation, not a production security boundary: authentication, tenant isolation, TLS, and reproducible policy digests are still open work.

## Architecture to draw

```text
Client -> Gateway -> {Lineage, Policy, Audit}
                         |        |       |
                         +--------+-------+-> PostgreSQL
                                   |
                          YAML policy + public key
```

Describe a decision as a caller-driven sequence:

1. Register the model/version and artifact references.
2. Submit caller-provided evaluation evidence to the policy service.
3. Record the allow/deny result in the audit service.
4. Export audit events and inspect the hash links.

The three calls are not atomic. A future orchestration endpoint would need an explicit partial-failure and retry contract.

## Design choices and tradeoffs

- **Compose instead of Kubernetes:** fewer moving parts for a single-host demo; no scheduler, multi-node availability, or autoscaling.
- **YAML policy files:** reviewable by operators and easy to diff; the current evaluator needs stronger schema validation and versioned policy evidence before production use.
- **Hash-chained audit rows:** tampering becomes detectable if a row is changed without recomputing later hashes; a privileged database administrator can still rewrite the database and schema.
- **Gateway allowlists:** narrow the reachable API surface and prevent arbitrary target URLs; endpoint changes must update the path allowlist.
- **Optional AIBOM verification:** the service verifies a signature using only a public Ed25519 key; key generation and private-key custody remain external.
- **SLA reporting:** the evaluator reports an over-budget warning but does not interrupt the request or reject the result.

## Live demo sequence

1. Start the stack using the README Quick Start.
2. Call `GET /mcp` and each service's `/healthz` route.
3. Register `examples/register_model.json` and look up its model ID.
4. Validate the passing example from README, then set `flags.contains_forbidden_data` to `true` and show the denial reason.
5. Log the decision and fetch `GET /mcp-audit/export?fmt=csv`.
6. Point out the `prev_hash` to `entry_hash` continuity and name the database-admin limitation.

## Questions worth preparing for

**Why use separate services?** It makes the responsibilities and state boundaries visible and lets the demo show how policy and evidence flows work. The cost is more containers and no transaction across a full decision flow.

**Does the hash chain make the log immutable?** It makes ordinary application updates/deletes fail and makes accidental or unsophisticated edits detectable. It does not stop a database administrator with schema privileges from rewriting history; external anchoring or signed checkpoints would be needed for that threat model.

**Is this an MCP server?** Not yet. The current interfaces are REST/JSON. MCP protocol support would be a separate adapter with defined tools/resources and compatibility tests; the existing service names alone do not provide it.

**What would you do next?** Add authentication and role-based authorization, persist policy/configuration hashes with each decision, validate policy files at startup, add a chain verification command and externally anchored checkpoints, and exercise failure/recovery behavior in CI.

## Claims to keep precise

- Say â€œtamper-evident hash chain,â€ not â€œtamper-proof.â€
- Say â€œpolicy evaluated against submitted metrics,â€ not â€œindependently validated model quality.â€
- Say â€œSLA warning,â€ not â€œhard real-time enforcement.â€
- Say â€œREST services,â€ not â€œMCP protocol server.â€
- A green local Compose run proves that tested image build, migrations, health checks, and exercised endpoints worked in that environment; it does not prove production readiness.
