# Interview Guide

## The 90 second overview

> I built a small governance control plane that runs on one machine. It uses FastAPI, PostgreSQL, and Docker Compose. It keeps three things apart that are often mixed together: model lineage, policy checks, and audit evidence. A gateway exposes a limited REST API. Policy rules are readable YAML. Each audit decision is linked to the hash of the event before it. I kept it to four application containers and PostgreSQL so anyone can run it without Kubernetes. The `mcp` in the service names does not mean it implements the Model Context Protocol. It is a portfolio project, not a production security boundary. Login, customer separation, TLS, and reproducible policy digests are still open work.

## What to draw

```text
Client -> Gateway -> {Lineage, Policy, Audit}
                         |        |       |
                         +--------+-------+-> PostgreSQL
                                   |
                          YAML policy + public key
```

Describe a decision as a sequence the caller drives:

1. Register the model, version, and artifact references.
2. Send the evaluation evidence to the policy service.
3. Record the allow or deny result in the audit service.
4. Export the audit events and inspect the hash links.

The three calls are not one all or nothing step. A future endpoint that combines them would need a clear plan for partial failures and retries.

## Design choices and tradeoffs

- **Compose instead of Kubernetes:** fewer moving parts for a demo on one machine. The cost is no scheduler, no multi node availability, and no autoscaling.
- **YAML policy files:** operators can read and compare them easily. Before production they need stronger validation and versioned evidence.
- **Hash chained audit rows:** if a row changes without recomputing the later hashes, you can see it. A database administrator can still rewrite the data and the schema.
- **Gateway allowlists:** they limit what can be reached and block arbitrary target URLs. Every new endpoint must be added to the allowlist.
- **Optional AIBOM checks:** the service verifies signatures with a public Ed25519 key only. Creating keys and guarding the private key happen elsewhere.
- **SLA reporting:** a slow check adds a warning. It does not stop the request or reject the result.

## Live demo steps

1. Start the stack with the README quick start.
2. Call `GET /mcp` and each service's `/healthz` route.
3. Register `examples/register_model.json` and look up the model ID.
4. Send the passing example from the README. Then set `flags.contains_forbidden_data` to `true` and show the denial reason.
5. Log the decision and fetch `GET /mcp-audit/export?fmt=csv`.
6. Point out that each `prev_hash` matches the previous `entry_hash`. Mention the database administrator limit.

## Questions to prepare for

**Why separate services?** It makes each job and its data easy to see. It also shows how evidence and rules flow. The cost is more containers and no single transaction across the whole decision.

**Does the hash chain make the log unchangeable?** No. Normal application updates and deletes fail, and careless edits are easy to spot. A database administrator with schema access can still rewrite history. You would need outside anchoring or signed checkpoints to cover that threat.

**Is this an MCP server?** Not yet. The interfaces are REST and JSON. MCP support would be a separate adapter with defined tools, resources, and compatibility tests. The service names alone do not provide it.

**What would you do next?** Add login and role based permissions. Store a hash of the policy files with each decision. Validate policy files at startup. Add a command that verifies the chain, and add signed checkpoints stored elsewhere. Test failure and recovery in CI.

## Keep your claims precise

- Say "tamper evident hash chain", not "tamper proof".
- Say "policy checked against submitted metrics", not "independently verified model quality".
- Say "SLA warning", not "hard real time enforcement".
- Say "REST services", not "MCP protocol server".
- A passing local Compose run shows that the image build, migrations, health checks, and tested endpoints worked in that environment. It does not prove the system is ready for production.
