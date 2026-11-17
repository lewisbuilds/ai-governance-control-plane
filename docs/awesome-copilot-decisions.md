# Awesome Copilot decision record

## 2026-11-17 - Project interview readiness and runtime verification

- **Need:** Verify the runnable project state, correct concrete API mismatches, and make the design easy to present accurately in an interview.
- **Observed evidence:** FastAPI services, PostgreSQL schema/migrations, Docker Compose stack, GitHub Actions workflows, YAML policy files, and integration tests are present. Compose configuration validates and all four Docker images build. The local Python virtual environments point to a missing interpreter; Docker is the usable runtime in this session.
- **Selected guidance:** Reality Compiler core; QA engineering, security, DevOps, Docker/containerization, and CI/CD resources from the curated pack. The task is a verification and bounded correction of an existing repo.
- **Adaptation:** Validate actual local image and API behavior, add focused regression coverage for the gateway paths and YAML policy rules, and document known scope boundaries. No broader catalog search was needed.
- **Rejected:** Kubernetes guidance because the repository uses Docker Compose and does not deploy Kubernetes. A new specification workflow was not needed for bounded compatibility fixes and documentation.
- **Permissions and limits:** Local repository edits and local Docker build/Compose execution only. No publishing, deployment, merge, or external service change.
- **Revisit when:** Adding MCP protocol support, authentication/authorization, durable policy evidence, a production deployment target, or a material change to audit-chain semantics.
