"""Test pgBackRest configuration files and manifests."""
import yaml
from pathlib import Path


def test_pgbackrest_config_files_exist():
    """Verify pgBackRest configuration files exist."""
    required_files = [
        "infra/pgbackrest/pgbackrest.conf",
        "infra/pgbackrest/postgresql-archive.conf",
    ]
    for file_path in required_files:
        p = Path(file_path)
        assert p.exists(), f"Required file {file_path} is missing"


def test_pgbackrest_k8s_manifests_exist():
    """Verify pgBackRest Kubernetes manifests exist."""
    required_manifests = [
        "infra/k8s/pgbackrest/pgbackrest-config.yaml",
        "infra/k8s/pgbackrest/pgbackrest-pvc.yaml",
        "infra/k8s/pgbackrest/pgbackrest-full-backup-cronjob.yaml",
        "infra/k8s/pgbackrest/pgbackrest-diff-backup-cronjob.yaml",
        "infra/k8s/pgbackrest/pgbackrest-restore-validation-cronjob.yaml",
        "infra/k8s/pgbackrest/pgbackrest-stanza-create-job.yaml",
        "infra/k8s/pgbackrest/postgres-config.yaml",
        "infra/k8s/pgbackrest/postgres-secret.yaml.example",
    ]
    for file_path in required_manifests:
        p = Path(file_path)
        assert p.exists(), f"Required manifest {file_path} is missing"


def test_pgbackrest_k8s_manifests_parse():
    """Verify pgBackRest Kubernetes manifests are valid YAML."""
    manifest_files = [
        "infra/k8s/pgbackrest/pgbackrest-config.yaml",
        "infra/k8s/pgbackrest/pgbackrest-pvc.yaml",
        "infra/k8s/pgbackrest/pgbackrest-full-backup-cronjob.yaml",
        "infra/k8s/pgbackrest/pgbackrest-diff-backup-cronjob.yaml",
        "infra/k8s/pgbackrest/pgbackrest-restore-validation-cronjob.yaml",
        "infra/k8s/pgbackrest/pgbackrest-stanza-create-job.yaml",
        "infra/k8s/pgbackrest/postgres-config.yaml",
        "infra/k8s/pgbackrest/postgres-secret.yaml.example",
    ]
    
    for file_path in manifest_files:
        with open(file_path, "r") as f:
            try:
                yaml.safe_load(f)
            except yaml.YAMLError as e:
                assert False, f"Failed to parse {file_path}: {e}"


def test_pgbackrest_docker_compose_override_parses():
    """Verify Docker Compose override file is valid YAML."""
    p = Path("docker-compose.pgbackrest.yml")
    assert p.exists(), "docker-compose.pgbackrest.yml is missing"
    
    with open(p, "r") as f:
        try:
            config = yaml.safe_load(f)
            assert "services" in config, "docker-compose.pgbackrest.yml must have 'services' key"
            assert "pgbackrest" in config["services"], "pgbackrest service not defined"
            assert "volumes" in config, "docker-compose.pgbackrest.yml must have 'volumes' key"
        except yaml.YAMLError as e:
            assert False, f"Failed to parse docker-compose.pgbackrest.yml: {e}"


def test_pgbackrest_scripts_exist():
    """Verify pgBackRest scripts exist."""
    required_scripts = [
        "scripts/pgbackrest-init.sh",
        "scripts/pgbackrest-init.ps1",
        "scripts/pgbackrest-backup.sh",
        "scripts/pgbackrest-backup.ps1",
        "scripts/pgbackrest-restore-validation.sh",
        "scripts/pgbackrest-restore-validation.ps1",
    ]
    for script_path in required_scripts:
        p = Path(script_path)
        assert p.exists(), f"Required script {script_path} is missing"


def test_pgbackrest_documentation_exists():
    """Verify pgBackRest documentation exists."""
    docs = [
        "docs/PGBACKREST.md",
        "infra/k8s/pgbackrest/README.md",
    ]
    for doc_path in docs:
        p = Path(doc_path)
        assert p.exists(), f"Required documentation {doc_path} is missing"


def test_pgbackrest_k8s_configmap_structure():
    """Verify pgBackRest ConfigMap has expected structure."""
    p = Path("infra/k8s/pgbackrest/pgbackrest-config.yaml")
    with open(p, "r") as f:
        config = yaml.safe_load(f)
    
    assert config["kind"] == "ConfigMap", "Expected ConfigMap kind"
    assert "data" in config, "ConfigMap must have data section"
    
    # Check for required configuration keys
    data = config["data"]
    assert "pgbackrest.conf" in data, "ConfigMap must have pgbackrest.conf"
    assert "postgresql-archive.conf" in data, "ConfigMap must have postgresql-archive.conf"
    assert "restore-validation.sh" in data, "ConfigMap must have restore-validation.sh"


def test_pgbackrest_k8s_cronjobs_have_schedules():
    """Verify pgBackRest CronJobs have valid schedules."""
    cronjobs = [
        ("infra/k8s/pgbackrest/pgbackrest-full-backup-cronjob.yaml", "0 2 * * *"),
        ("infra/k8s/pgbackrest/pgbackrest-diff-backup-cronjob.yaml", "0 */6 * * *"),
        ("infra/k8s/pgbackrest/pgbackrest-restore-validation-cronjob.yaml", "0 3 * * 0"),
    ]
    
    for file_path, expected_schedule in cronjobs:
        with open(file_path, "r") as f:
            config = yaml.safe_load(f)
        
        assert config["kind"] == "CronJob", f"{file_path} must be a CronJob"
        assert "spec" in config, f"{file_path} must have spec"
        assert "schedule" in config["spec"], f"{file_path} must have schedule"
        assert config["spec"]["schedule"] == expected_schedule, \
            f"{file_path} schedule mismatch: expected {expected_schedule}, got {config['spec']['schedule']}"


def test_pgbackrest_retention_settings():
    """Verify retention settings are configured in pgBackRest config."""
    p = Path("infra/pgbackrest/pgbackrest.conf")
    content = p.read_text()
    
    # Check for retention settings
    assert "repo1-retention-full" in content, "pgbackrest.conf must define repo1-retention-full"
    assert "repo1-retention-diff" in content, "pgbackrest.conf must define repo1-retention-diff"
    assert "repo1-retention-archive" in content, "pgbackrest.conf must define repo1-retention-archive"


def test_postgresql_archive_mode_configured():
    """Verify PostgreSQL is configured for archive mode."""
    p = Path("infra/pgbackrest/postgresql-archive.conf")
    content = p.read_text()
    
    # Check for critical archive settings
    assert "archive_mode = on" in content, "Archive mode must be enabled"
    assert "archive_command" in content, "Archive command must be configured"
    assert "pgbackrest" in content, "Archive command must use pgbackrest"
    assert "wal_level = replica" in content, "WAL level must be set to replica"
