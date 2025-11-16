## Contributing Guide

Thank you for improving the AI Governance Control Plane. This guide keeps contributions fast, secure, and consistent.

### 1. Prerequisites
| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11 | Match runtime used by services |
| Docker Desktop | Latest | Linux engine enabled |
| PowerShell | 5.1+ | Scripts assume Windows PS; adapt for other shells |
| GitHub CLI (optional) | latest | For auth / workflow inspection |

### 2. Environment Setup
```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pre-commit install
```

### 3. Branching & Commits
- Use short feature branches: `feat/<desc>` / `fix/<desc>` / `chore/<desc>`.
- Keep commits focused; prefer “one logical change per commit”.
- Reference issues with `Closes #ID` when applicable.

### 4. Migrations Workflow
1. Create a new SQL file in `infra/migrations/` named incrementally: `0002_short_description.sql`.
2. Only add forward changes (append-only philosophy). No destructive edits to existing migration files.
3. Run locally:
```powershell
$env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"
python scripts/migrate.py
```
4. Verify schema with a quick dump:
```powershell
docker compose up -d db
pg_dump --schema-only --no-owner --no-privileges $env:DATABASE_URL | Select-String NEW_TABLE_OR_COLUMN
```

### 5. Tests & Coverage
Run fast (unit) tests:
```powershell
pytest -m "not integration" -q
```
Run full suite (requires stack):
```powershell
docker compose up -d
pytest -q
```
Coverage thresholds enforced via `pytest.ini` (fail under 80%). Improve coverage before lowering threshold.

### 6. Linting & Type Checking
Ruff (style + quality) and mypy (types) must pass in CI.
```powershell
ruff check .
mypy services scripts clients
```
Fix import order / formatting:
```powershell
ruff check . --fix
ruff format .
black .
isort .
```

### 7. Pre-commit Hooks
Installed hooks run ruff, ruff-format, black, isort, mypy. Run manually:
```powershell
pre-commit run --all-files
```

### 8. Container & Security Scans
Local multi‑image build (no push):
```powershell
docker build -f services/mcp-gateway/Dockerfile . -t gateway:test
```
CI runs Trivy and generates CycloneDX SBOMs. Address HIGH/CRITICAL vulns unless false positives—document justification in PR.

### 9. Supply Chain Integrity
- Tag releases trigger GHCR publishes with SLSA provenance.
- Do not bypass provenance flags or alter attestation steps.
- Avoid introducing unpinned, unofficial actions. Prefer the `actions/*` or well‑maintained security vendor actions.

### 10. Policy & YAML Changes
Modify `policies/model-policy.yml` or `policies/risk-matrix.yml` thoughtfully:
- Keep keys stable; add new keys for extensions.
- Update/add tests if logic changes.
- Validate YAML with `pytest -k policies_yaml`.

### 11. Logging & Observability
- Preserve structured JSON logging format.
- Continue to propagate and honor `X-Request-ID` headers.
- Add new fields only when they are consistently present or optional.

### 12. Security Checklist
- No raw SQL concatenation (use psycopg parameters).
- No hardcoded secrets—use environment variables.
- Avoid SSRF by never proxying arbitrary external URLs.
- Validate any external input that might form paths or identifiers.
- Use `yaml.safe_load` only for YAML parsing.

### 13. PR Checklist
- [ ] Feature / fix description included.
- [ ] Migration added (if schema changed) and tested.
- [ ] Lint passes (ruff).
- [ ] Type checks pass (mypy).
- [ ] Tests pass locally (unit + integration if applicable).
- [ ] Coverage not reduced significantly.
- [ ] Security scan expected to pass (no new HIGH/CRITICAL without justification).
- [ ] SBOM generation unaffected.
- [ ] Docs / README / API.md updated if endpoints or flows changed.

### 14. Fast Review Tips
- Keep PR size modest (< ~300 lines diff when possible).
- Provide before/after examples for behavioral changes.
- Link related architecture or API doc changes.

### 15. Troubleshooting
| Symptom | Action |
|---------|--------|
| Migration skipped | Check sequential file naming & rerun `scripts/migrate.py` |
| CI ruff failures | Run `ruff check . --fix` then re‑lint |
| mypy new errors | Add/adjust type hints; avoid `# type: ignore` except with justification |
| Trivy false positive | Add comment in PR describing CVE and mitigation/context |
| SBOM missing | Ensure build job ran; confirm `build-images` not skipped by label |

### 16. Accessibility & Inclusivity
Use clear language in docs; avoid jargon when simple terms suffice. Provide descriptive alt text if adding images.

### 17. Contribution Scope
For large or potentially destructive changes (wide deletes, major refactors), open a draft PR first outlining a rollback plan.

---
Built with security, repeatability, and clarity in mind. Please test, lint, type‑check, and document changes.