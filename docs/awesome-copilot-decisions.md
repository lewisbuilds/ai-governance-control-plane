# Awesome Copilot decision record

## 2026-11-17: Project interview readiness and runtime check

- **Need:** Check that the project runs, fix concrete API mismatches, and make the design easy to present accurately in an interview.
- **What was found:** The repository has FastAPI services, a PostgreSQL schema with migrations, a Docker Compose stack, GitHub Actions workflows, YAML policy files, and integration tests. The Compose file is valid and all four Docker images build. The local Python virtual environments pointed at a missing interpreter, so Docker was the usable runtime in that session.
- **Guidance used:** The Reality Compiler core, plus the QA, security, DevOps, Docker, and CI/CD resources from the curated pack. The task was a bounded check and correction of an existing repository.
- **How it was adapted:** Test the real local images and API behavior, add focused regression tests for the gateway paths and the YAML policy rules, and document the known limits. A wider catalog search was not needed.
- **Left out:** Kubernetes guidance, because the project uses Docker Compose. A new specification workflow, because the fixes and documentation changes were small.
- **Limits:** Local repository edits and local Docker builds only. No publishing, deployment, merge, or change to an outside service.
- **Revisit when:** MCP protocol support, login and permissions, durable policy evidence, a production deployment target, or a major change to how the audit chain works is added.
