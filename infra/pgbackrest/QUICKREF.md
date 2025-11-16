# pgBackRest Quick Reference

## Directory Structure

```
ai-governance-control-plane/
├── docs/
│   └── PGBACKREST.md                      # Complete integration guide
├── infra/
│   ├── k8s/
│   │   └── pgbackrest/                    # Kubernetes manifests
│   │       ├── README.md                  # K8s deployment guide
│   │       ├── pgbackrest-config.yaml     # ConfigMap with settings
│   │       ├── pgbackrest-pvc.yaml        # Persistent volume claim
│   │       ├── postgres-config.yaml       # PostgreSQL config with archive mode
│   │       ├── postgres-secret.yaml.example  # Credentials template
│   │       ├── pgbackrest-stanza-create-job.yaml     # One-time stanza init
│   │       ├── pgbackrest-full-backup-cronjob.yaml   # Daily full backups
│   │       ├── pgbackrest-diff-backup-cronjob.yaml   # 6-hourly diff backups
│   │       └── pgbackrest-restore-validation-cronjob.yaml  # Weekly validation
│   └── pgbackrest/                        # VM/Docker Compose config
│       ├── README.md                      # VM deployment guide
│       ├── pgbackrest.conf                # Main pgBackRest config
│       ├── postgresql-archive.conf        # PostgreSQL archive settings
│       ├── cron-pgbackrest                # Cron schedule template
│       ├── pgbackrest-full-backup.service # Systemd service (full)
│       ├── pgbackrest-full-backup.timer   # Systemd timer (full)
│       ├── pgbackrest-diff-backup.service # Systemd service (diff)
│       └── pgbackrest-diff-backup.timer   # Systemd timer (diff)
├── scripts/
│   ├── pgbackrest-init.sh                 # Stanza initialization (bash)
│   ├── pgbackrest-init.ps1                # Stanza initialization (PowerShell)
│   ├── pgbackrest-backup.sh               # Manual backup (bash)
│   ├── pgbackrest-backup.ps1              # Manual backup (PowerShell)
│   ├── pgbackrest-restore-validation.sh   # Restore validation (bash)
│   └── pgbackrest-restore-validation.ps1  # Restore validation (PowerShell)
├── tests/
│   └── test_pgbackrest.py                 # Test suite (10 tests)
└── docker-compose.pgbackrest.yml          # Docker Compose override
```

## Quick Start by Platform

### Kubernetes

```bash
# 1. Create namespace
kubectl create namespace ai-governance

# 2. Create PostgreSQL credentials secret
kubectl create secret generic postgres-credentials \
  --from-literal=username=mcp \
  --from-literal=password=your-secure-password \
  --from-literal=database=mcpgov \
  -n ai-governance

# 3. Deploy all resources
kubectl apply -f infra/k8s/pgbackrest/

# 4. Verify
kubectl get all -n ai-governance -l app=pgbackrest
kubectl logs -n ai-governance job/pgbackrest-stanza-create
```

### Docker Compose

```bash
# 1. Start services with pgBackRest
docker compose -f docker-compose.yml -f docker-compose.pgbackrest.yml up -d

# 2. Initialize stanza
./scripts/pgbackrest-init.sh

# 3. Perform first backup
./scripts/pgbackrest-backup.sh full

# 4. Validate
./scripts/pgbackrest-restore-validation.sh
```

### VM/Bare Metal

```bash
# 1. Install pgBackRest
sudo apt-get install pgbackrest

# 2. Configure
sudo cp infra/pgbackrest/pgbackrest.conf /etc/pgbackrest/
sudo cat infra/pgbackrest/postgresql-archive.conf >> /etc/postgresql/16/main/postgresql.conf

# 3. Initialize stanza
sudo -u postgres pgbackrest --stanza=mcpgov stanza-create

# 4. Setup automation (choose one)
# Option A: Systemd timers
sudo cp infra/pgbackrest/*.service /etc/systemd/system/
sudo cp infra/pgbackrest/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pgbackrest-full-backup.timer
sudo systemctl enable --now pgbackrest-diff-backup.timer

# Option B: Cron
sudo cp infra/pgbackrest/cron-pgbackrest /etc/cron.d/pgbackrest
```

## Backup Schedule

| Type | Frequency | Schedule | Purpose |
|------|-----------|----------|---------|
| Full | Daily | 2:00 AM UTC | Complete database backup |
| Differential | Every 6 hours | 0:00, 6:00, 12:00, 18:00 UTC | Changes since last full |
| Validation | Weekly | Sunday 3:00 AM UTC | Verify restore capability |

## Retention Policy

- **Full backups**: 4 (keeps ~4 days)
- **Differential backups**: 3 (kept between full backups)
- **WAL archives**: 14 days

## Common Commands

### View Backup Info

```bash
# Docker Compose
docker exec mcp-pgbackrest pgbackrest --stanza=mcpgov info

# Kubernetes
kubectl run -n ai-governance pgbackrest-info --rm -it --restart=Never \
  --image=pgbackrest/pgbackrest:latest \
  --overrides='{"spec":{"containers":[{"name":"pgbackrest-info","image":"pgbackrest/pgbackrest:latest","command":["pgbackrest","--stanza=mcpgov","info"],"volumeMounts":[{"name":"config","mountPath":"/etc/pgbackrest"},{"name":"repo","mountPath":"/var/lib/pgbackrest"}]}],"volumes":[{"name":"config","configMap":{"name":"pgbackrest-config"}},{"name":"repo","persistentVolumeClaim":{"claimName":"pgbackrest-repo"}}]}}'

# VM
sudo -u postgres pgbackrest --stanza=mcpgov info
```

### Manual Backup

```bash
# Docker Compose
./scripts/pgbackrest-backup.sh full
./scripts/pgbackrest-backup.sh diff

# Kubernetes
kubectl create job --from=cronjob/pgbackrest-full-backup \
  pgbackrest-manual-$(date +%Y%m%d) -n ai-governance

# VM
sudo -u postgres pgbackrest --stanza=mcpgov --type=full backup
```

### Restore Operations

**Full Restore:**
1. Stop application services
2. Stop PostgreSQL
3. Clear data directory
4. Run restore command
5. Restart PostgreSQL

**Point-in-Time Recovery:**
```bash
pgbackrest --stanza=mcpgov --type=time --target="2024-01-15 14:30:00" restore
```

## Configuration Files

### pgbackrest.conf

Key settings:
- `repo1-retention-full=4` - Keep 4 full backups
- `repo1-retention-diff=3` - Keep 3 differential backups
- `repo1-retention-archive=14` - Keep 14 days of WAL archives
- `process-max=2` - Parallel processes for backup/restore

### postgresql-archive.conf

Required PostgreSQL settings:
- `archive_mode = on` - Enable WAL archiving
- `archive_command = 'pgbackrest --stanza=mcpgov archive-push %p'`
- `wal_level = replica` - Set WAL level for replication/backup
- `restore_command = 'pgbackrest --stanza=mcpgov archive-get %f "%p"'`

## S3 Integration

To use S3 instead of local storage, add to `pgbackrest.conf`:

```ini
[global]
repo1-type=s3
repo1-s3-bucket=your-backup-bucket
repo1-s3-region=us-east-1
repo1-s3-key=YOUR_ACCESS_KEY
repo1-s3-key-secret=YOUR_SECRET_KEY
```

Or use IAM roles (preferred):
```ini
[global]
repo1-type=s3
repo1-s3-bucket=your-backup-bucket
repo1-s3-region=us-east-1
```

## Monitoring

### Check Status

```bash
# Kubernetes
kubectl get cronjobs -n ai-governance -l app=pgbackrest
kubectl logs -n ai-governance -l app=pgbackrest --tail=50

# Docker Compose
docker logs mcp-pgbackrest

# VM (systemd)
sudo systemctl list-timers pgbackrest-*
sudo journalctl -u pgbackrest-full-backup.service -n 50

# VM (cron)
sudo tail -f /var/log/pgbackrest/mcpgov-backup.log
```

### Verify Tests

```bash
# Run test suite
pytest tests/test_pgbackrest.py -v

# Expected: 10 tests passing
```

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Archive command fails | pgBackRest not installed in PostgreSQL pod | Install pgBackRest or use network-based archiving |
| Stanza creation fails | PostgreSQL not accessible | Verify PostgreSQL is running, check credentials |
| Backup fails "no prior backup" | No full backup exists | Run full backup first |
| Permission errors | Wrong user/group | Check security context (K8s) or file permissions (VM) |

## Resources

- **Full Documentation**: `docs/PGBACKREST.md`
- **Kubernetes Guide**: `infra/k8s/pgbackrest/README.md`
- **VM Guide**: `infra/pgbackrest/README.md`
- **Official Docs**: https://pgbackrest.org/
- **Test Suite**: `tests/test_pgbackrest.py`
