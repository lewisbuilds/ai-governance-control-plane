# pgBackRest Integration Guide

This guide covers the integration of pgBackRest for PostgreSQL backup and recovery in the AI Governance Control Plane project.

## Overview

pgBackRest provides enterprise-grade backup and restore capabilities for PostgreSQL databases, including:

- **Full, Differential, and Incremental Backups**: Optimized backup strategies
- **Point-in-Time Recovery (PITR)**: Restore to any point in time
- **Parallel Operations**: Fast backup and restore using multiple processes
- **Compression**: Efficient storage usage
- **Retention Policies**: Automatic cleanup of old backups
- **WAL Archiving**: Continuous archiving of transaction logs

## Deployment Options

### Option 1: Kubernetes (Recommended for Production)

Kubernetes manifests are located in `infra/k8s/pgbackrest/`.

**Features:**
- Automated scheduled backups using CronJobs
- Persistent storage with PVCs
- Optional S3 integration for cloud storage
- Automated restore validation
- NetworkPolicies for security

See [infra/k8s/pgbackrest/README.md](../infra/k8s/pgbackrest/README.md) for detailed Kubernetes deployment instructions.

### Option 2: Docker Compose (Development/Testing)

Docker Compose configuration is provided in `docker-compose.pgbackrest.yml`.

**Features:**
- Easy local setup for development
- Shared volumes with PostgreSQL
- Manual backup operations via scripts

**Quick Start:**

```bash
# Start services with pgBackRest
docker compose -f docker-compose.yml -f docker-compose.pgbackrest.yml up -d

# Initialize the stanza (one-time)
./scripts/pgbackrest-init.sh
# Or on Windows:
./scripts/pgbackrest-init.ps1

# Perform a full backup
./scripts/pgbackrest-backup.sh full
# Or on Windows:
./scripts/pgbackrest-backup.ps1 -BackupType full

# Validate restore capability
./scripts/pgbackrest-restore-validation.sh
# Or on Windows:
./scripts/pgbackrest-restore-validation.ps1
```

### Option 3: VM Deployment with Cron/Systemd

For VM-based deployments, install pgBackRest directly on the PostgreSQL server or a dedicated backup server.

**Setup Steps:**

1. Install pgBackRest:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install pgbackrest
   
   # RHEL/CentOS
   sudo yum install pgbackrest
   ```

2. Configure pgBackRest:
   - Copy `infra/pgbackrest/pgbackrest.conf` to `/etc/pgbackrest/pgbackrest.conf`
   - Update paths and settings for your environment

3. Configure PostgreSQL:
   - Add archive settings from `infra/pgbackrest/postgresql-archive.conf` to `postgresql.conf`
   - Restart PostgreSQL

4. Initialize stanza:
   ```bash
   sudo -u postgres pgbackrest --stanza=mcpgov stanza-create
   sudo -u postgres pgbackrest --stanza=mcpgov check
   ```

5. Set up automated backups with cron:
   ```bash
   # Edit crontab for postgres user
   sudo crontab -u postgres -e
   
   # Add these entries:
   # Full backup daily at 2 AM
   0 2 * * * /usr/bin/pgbackrest --stanza=mcpgov --type=full backup
   
   # Differential backup every 6 hours
   0 */6 * * * /usr/bin/pgbackrest --stanza=mcpgov --type=diff backup
   
   # Restore validation weekly on Sundays at 3 AM
   0 3 * * 0 /usr/local/bin/pgbackrest-restore-validation.sh
   ```

## Configuration

### PostgreSQL Archive Settings

The following settings must be configured in PostgreSQL to enable WAL archiving:

```ini
# Enable WAL archiving
archive_mode = on
archive_command = 'pgbackrest --stanza=mcpgov archive-push %p'
archive_timeout = 60

# WAL settings
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1024

# Restore command (for recovery)
restore_command = 'pgbackrest --stanza=mcpgov archive-get %f "%p"'
```

These settings are included in:
- `infra/pgbackrest/postgresql-archive.conf` (for Docker Compose)
- `infra/k8s/pgbackrest/postgres-config.yaml` (for Kubernetes)

### pgBackRest Configuration

Key configuration parameters in `pgbackrest.conf`:

```ini
[global]
repo1-path=/var/lib/pgbackrest          # Repository location
repo1-retention-full=4                   # Keep 4 full backups
repo1-retention-diff=3                   # Keep 3 differential backups
repo1-retention-archive=14               # Keep 14 days of WAL archives
log-level-console=info                   # Console log level
log-level-file=debug                     # File log level
process-max=2                            # Parallel processes

[mcpgov]
pg1-path=/var/lib/postgresql/data        # PostgreSQL data directory
pg1-host=db                              # PostgreSQL host (or IP)
pg1-port=5432                            # PostgreSQL port
pg1-user=mcp                             # PostgreSQL user
```

### Retention Policies

Default retention policy:
- **Full backups**: 4 (daily for ~4 days)
- **Differential backups**: 3 (kept between full backups)
- **Archive logs**: 14 days

To adjust retention, modify the `repo1-retention-*` settings in `pgbackrest.conf`.

## Backup Operations

### Backup Types

1. **Full Backup**: Complete copy of the database
   - Schedule: Daily at 2 AM UTC
   - Frequency: Use for baseline backups

2. **Differential Backup**: Changes since last full backup
   - Schedule: Every 6 hours
   - Frequency: Use for regular incremental coverage

3. **Incremental Backup**: Changes since last backup (any type)
   - Not scheduled by default, but can be used for high-frequency backups

### Manual Backup Commands

**Docker Compose:**
```bash
# Full backup
./scripts/pgbackrest-backup.sh full

# Differential backup
./scripts/pgbackrest-backup.sh diff

# Incremental backup
./scripts/pgbackrest-backup.sh incr
```

**Kubernetes:**
```bash
# Trigger a manual full backup
kubectl create job --from=cronjob/pgbackrest-full-backup \
  pgbackrest-manual-full-$(date +%Y%m%d-%H%M%S) -n ai-governance

# Trigger a manual differential backup
kubectl create job --from=cronjob/pgbackrest-diff-backup \
  pgbackrest-manual-diff-$(date +%Y%m%d-%H%M%S) -n ai-governance
```

**VM/Direct:**
```bash
# Full backup
sudo -u postgres pgbackrest --stanza=mcpgov --type=full backup

# Differential backup
sudo -u postgres pgbackrest --stanza=mcpgov --type=diff backup
```

### View Backup Information

**Docker Compose:**
```bash
docker exec mcp-pgbackrest pgbackrest --stanza=mcpgov info
```

**Kubernetes:**
```bash
# See the full command in infra/k8s/pgbackrest/README.md
```

**VM/Direct:**
```bash
sudo -u postgres pgbackrest --stanza=mcpgov info
```

## Restore Operations

### Full Database Restore

**Prerequisites:**
1. Stop application services to prevent database writes
2. Back up current database state (if possible)

**Docker Compose:**
```bash
# Stop services
docker compose stop mcp-lineage mcp-audit mcp-policy mcp-gateway

# Stop PostgreSQL
docker compose stop db

# Clear data directory (DESTRUCTIVE - ensure you have backups!)
docker volume rm ai-governance-control-plane_pg

# Recreate volume
docker volume create ai-governance-control-plane_pg

# Perform restore
docker run --rm \
  --volumes-from mcp-db \
  -v $(pwd)/infra/pgbackrest/pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro \
  -v pgbackrest-repo:/var/lib/pgbackrest \
  --network container:mcp-pgbackrest \
  pgbackrest/pgbackrest:latest \
  pgbackrest --stanza=mcpgov --pg1-path=/var/lib/postgresql/data restore

# Start PostgreSQL
docker compose up -d db

# Verify database
docker exec mcp-db psql -U mcp -d mcpgov -c "SELECT version();"

# Start application services
docker compose up -d
```

**Kubernetes:**
See detailed instructions in `infra/k8s/pgbackrest/README.md`.

**VM/Direct:**
```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Clear data directory (DESTRUCTIVE - ensure you have backups!)
sudo rm -rf /var/lib/postgresql/data/*

# Perform restore
sudo -u postgres pgbackrest --stanza=mcpgov --pg1-path=/var/lib/postgresql/data restore

# Start PostgreSQL
sudo systemctl start postgresql
```

### Point-in-Time Recovery (PITR)

To restore to a specific timestamp:

**Docker Compose:**
```bash
# Same as full restore, but specify target time
docker run --rm \
  --volumes-from mcp-db \
  -v $(pwd)/infra/pgbackrest/pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro \
  -v pgbackrest-repo:/var/lib/pgbackrest \
  --network container:mcp-pgbackrest \
  pgbackrest/pgbackrest:latest \
  pgbackrest --stanza=mcpgov --pg1-path=/var/lib/postgresql/data \
    --type=time --target="2024-01-15 14:30:00" restore
```

**Kubernetes/VM:**
Use the same `--type=time --target="YYYY-MM-DD HH:MM:SS"` options in the restore command.

## Restore Validation

Automated restore validation runs weekly to ensure backups are restorable.

**Docker Compose:**
```bash
./scripts/pgbackrest-restore-validation.sh
```

**Kubernetes:**
Scheduled via CronJob `pgbackrest-restore-validation` (Sundays at 3 AM UTC).

Manual trigger:
```bash
kubectl create job --from=cronjob/pgbackrest-restore-validation \
  pgbackrest-manual-validation-$(date +%Y%m%d-%H%M%S) -n ai-governance
```

**VM:**
```bash
# Copy the validation script
sudo cp scripts/pgbackrest-restore-validation.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/pgbackrest-restore-validation.sh

# Run manually
sudo -u postgres /usr/local/bin/pgbackrest-restore-validation.sh

# Or add to crontab for automation
```

## S3 Integration (Optional)

To use S3 for backup storage:

1. **Configure pgBackRest for S3:**

   Edit `pgbackrest.conf`:
   ```ini
   [global]
   repo1-type=s3
   repo1-s3-bucket=your-backup-bucket
   repo1-s3-region=us-east-1
   repo1-s3-endpoint=s3.amazonaws.com
   repo1-s3-key=<access-key>
   repo1-s3-key-secret=<secret-key>
   ```

2. **For Kubernetes:**
   
   Store S3 credentials in a Secret:
   ```bash
   kubectl create secret generic pgbackrest-s3-credentials \
     --from-literal=s3-key=YOUR_ACCESS_KEY \
     --from-literal=s3-key-secret=YOUR_SECRET_KEY \
     -n ai-governance
   ```
   
   Update CronJobs to use the secret (see `infra/k8s/pgbackrest/README.md`).

3. **For Docker Compose:**
   
   Add environment variables:
   ```yaml
   environment:
     PGBACKREST_REPO1_S3_KEY: ${AWS_ACCESS_KEY_ID}
     PGBACKREST_REPO1_S3_KEY_SECRET: ${AWS_SECRET_ACCESS_KEY}
   ```

4. **For VM:**
   
   Update `pgbackrest.conf` with S3 credentials or use IAM roles if running on AWS EC2.

## Monitoring and Troubleshooting

### Check Backup Status

**Docker Compose:**
```bash
docker exec mcp-pgbackrest pgbackrest --stanza=mcpgov info
docker logs mcp-pgbackrest
```

**Kubernetes:**
```bash
# Check CronJob status
kubectl get cronjobs -n ai-governance -l app=pgbackrest

# View recent job logs
kubectl logs -n ai-governance -l app=pgbackrest --tail=100

# Check backup repository size
kubectl exec -n ai-governance -it <postgres-pod> -- du -sh /var/lib/pgbackrest
```

**VM:**
```bash
sudo -u postgres pgbackrest --stanza=mcpgov info
sudo tail -f /var/log/pgbackrest/mcpgov-backup.log
```

### Common Issues

**Issue**: Archive command fails with "could not open file"
- **Cause**: pgBackRest not installed in PostgreSQL pod/container
- **Solution**: Ensure pgBackRest is available in the PostgreSQL environment or use network-based archiving

**Issue**: Stanza creation fails with connection error
- **Cause**: PostgreSQL not accessible or wrong credentials
- **Solution**: Verify PostgreSQL is running, check host/port/credentials in `pgbackrest.conf`

**Issue**: Backup fails with "no prior backup exists"
- **Cause**: Attempting differential/incremental backup without a full backup
- **Solution**: Run a full backup first: `pgbackrest --stanza=mcpgov --type=full backup`

**Issue**: Insufficient space in backup repository
- **Cause**: Retention policy keeps too many backups or PVC too small
- **Solution**: Adjust retention settings or increase PVC size

## Security Considerations

1. **Credentials**: Store PostgreSQL passwords securely using Secrets (Kubernetes) or environment variables (Docker Compose)
2. **Encryption**: Enable encryption for backups, especially when using S3
3. **Access Control**: Restrict access to backup repository using RBAC (Kubernetes) or file permissions (VM)
4. **Network Policies**: Use NetworkPolicies to limit access to PostgreSQL and backup services
5. **Audit Logging**: Monitor backup job executions and failures

## Performance Tuning

- **process-max**: Increase for parallel operations (default: 2, recommended: 4-8 for production)
- **Compression**: Enable compression to reduce storage usage (add `compress-type=lz4` to `pgbackrest.conf`)
- **Buffer sizes**: Adjust `buffer-size` for network throughput optimization
- **Schedule optimization**: Spread backups to avoid peak usage hours

## References

- [pgBackRest Official Documentation](https://pgbackrest.org/)
- [pgBackRest User Guide](https://pgbackrest.org/user-guide.html)
- [PostgreSQL WAL Archiving](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [pgBackRest Best Practices](https://pgbackrest.org/user-guide.html#quickstart/perform-backup)
