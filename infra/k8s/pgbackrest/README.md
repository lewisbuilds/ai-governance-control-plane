# pgBackRest Integration for AI Governance Control Plane

This directory contains Kubernetes manifests for integrating pgBackRest with the PostgreSQL database used by the AI Governance Control Plane.

## Overview

pgBackRest is a reliable backup and restore solution for PostgreSQL that provides:

- **Full, Differential, and Incremental Backups**: Optimized backup strategies to minimize backup time and storage
- **Point-in-Time Recovery (PITR)**: Restore to any point in time within the retention period
- **Parallel Backup and Restore**: Fast operations using multiple processes
- **Compression and Encryption**: Secure and efficient backup storage
- **Archive Management**: Automatic WAL archiving with retention policies

## Architecture

The integration consists of:

1. **ConfigMap** (`pgbackrest-config.yaml`): Contains pgBackRest configuration, PostgreSQL archive settings, and validation scripts
2. **PVC** (`pgbackrest-pvc.yaml`): Persistent storage for backup repository (default: 20Gi)
3. **CronJobs**:
   - Full backup: Daily at 2 AM UTC
   - Differential backup: Every 6 hours
   - Restore validation: Weekly on Sundays at 3 AM UTC
4. **Stanza Creation Job** (`pgbackrest-stanza-create-job.yaml`): One-time initialization of pgBackRest stanza
5. **PostgreSQL Configuration** (`postgres-config.yaml`): PostgreSQL settings with archive mode enabled

## Deployment Steps

### Prerequisites

- Kubernetes cluster with a default StorageClass or specify `storageClassName` in PVC
- PostgreSQL deployment with the label `app: postgres`
- Namespace `ai-governance` created

### 1. Create the Namespace (if not exists)

```bash
kubectl create namespace ai-governance
```

### 2. Create PostgreSQL Credentials Secret

Copy the example secret and modify with your actual credentials:

```bash
cp postgres-secret.yaml.example postgres-secret.yaml
# Edit postgres-secret.yaml and change the password
kubectl apply -f postgres-secret.yaml
```

**Important**: Never commit the actual `postgres-secret.yaml` to version control. The `.example` file is provided as a template.

### 3. Apply PostgreSQL Configuration

This configures PostgreSQL with archive mode and archive_command:

```bash
kubectl apply -f postgres-config.yaml
```

You need to ensure your PostgreSQL StatefulSet/Deployment mounts this ConfigMap and uses it. Update your PostgreSQL deployment to include:

```yaml
volumeMounts:
  - name: postgres-config
    mountPath: /etc/postgresql/postgresql.conf
    subPath: postgresql.conf
  - name: postgres-config
    mountPath: /etc/postgresql/pg_hba.conf
    subPath: pg_hba.conf
volumes:
  - name: postgres-config
    configMap:
      name: postgres-pgbackrest-config
```

And configure PostgreSQL to use the custom config:

```yaml
command:
  - postgres
  - -c
  - config_file=/etc/postgresql/postgresql.conf
  - -c
  - hba_file=/etc/postgresql/pg_hba.conf
```

### 4. Deploy pgBackRest Resources

Apply the pgBackRest manifests in order:

```bash
# Create PVC for backup repository
kubectl apply -f pgbackrest-pvc.yaml

# Create ConfigMap with pgBackRest configuration
kubectl apply -f pgbackrest-config.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n ai-governance --timeout=120s

# Initialize the stanza (one-time operation)
kubectl apply -f pgbackrest-stanza-create-job.yaml

# Wait for stanza creation to complete
kubectl wait --for=condition=complete job/pgbackrest-stanza-create -n ai-governance --timeout=300s

# Check the stanza creation logs
kubectl logs -n ai-governance job/pgbackrest-stanza-create

# Deploy the backup CronJobs
kubectl apply -f pgbackrest-full-backup-cronjob.yaml
kubectl apply -f pgbackrest-diff-backup-cronjob.yaml
kubectl apply -f pgbackrest-restore-validation-cronjob.yaml
```

### 5. Verify Deployment

Check that all resources are created:

```bash
kubectl get all -n ai-governance -l app=pgbackrest
kubectl get pvc -n ai-governance -l app=pgbackrest
kubectl get configmap -n ai-governance -l app=pgbackrest
kubectl get cronjob -n ai-governance -l app=pgbackrest
```

## Manual Backup Operations

### Trigger a Manual Full Backup

```bash
kubectl create job --from=cronjob/pgbackrest-full-backup pgbackrest-manual-full-$(date +%Y%m%d-%H%M%S) -n ai-governance
```

### Trigger a Manual Differential Backup

```bash
kubectl create job --from=cronjob/pgbackrest-diff-backup pgbackrest-manual-diff-$(date +%Y%m%d-%H%M%S) -n ai-governance
```

### Trigger a Manual Restore Validation

```bash
kubectl create job --from=cronjob/pgbackrest-restore-validation pgbackrest-manual-validation-$(date +%Y%m%d-%H%M%S) -n ai-governance
```

### View Backup Information

```bash
# Get a pgBackRest pod (from a CronJob run or create one)
kubectl run -n ai-governance pgbackrest-info --rm -it --restart=Never \
  --image=pgbackrest/pgbackrest:latest \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "pgbackrest-info",
      "image": "pgbackrest/pgbackrest:latest",
      "command": ["pgbackrest", "--stanza=mcpgov", "info"],
      "env": [
        {"name": "PGBACKREST_REPO1_PATH", "value": "/var/lib/pgbackrest"},
        {"name": "PGBACKREST_LOG_PATH", "value": "/var/log/pgbackrest"}
      ],
      "volumeMounts": [
        {"name": "config", "mountPath": "/etc/pgbackrest"},
        {"name": "repo", "mountPath": "/var/lib/pgbackrest"}
      ]
    }],
    "volumes": [
      {"name": "config", "configMap": {"name": "pgbackrest-config"}},
      {"name": "repo", "persistentVolumeClaim": {"claimName": "pgbackrest-repo"}}
    ]
  }
}'
```

## Restore Operations

### Full Database Restore

To restore the entire database to the latest backup:

1. **Stop the application services** to prevent writes during restore
2. **Stop PostgreSQL**
3. **Clear the data directory**
4. **Run the restore**:

```bash
kubectl run -n ai-governance pgbackrest-restore --rm -it --restart=Never \
  --image=pgbackrest/pgbackrest:latest \
  --overrides='
{
  "spec": {
    "securityContext": {"runAsUser": 999, "runAsGroup": 999, "fsGroup": 999},
    "containers": [{
      "name": "pgbackrest-restore",
      "image": "pgbackrest/pgbackrest:latest",
      "command": ["/bin/bash", "-c"],
      "args": ["pgbackrest --stanza=mcpgov --type=default restore"],
      "env": [
        {"name": "PGBACKREST_REPO1_PATH", "value": "/var/lib/pgbackrest"},
        {"name": "PGBACKREST_LOG_PATH", "value": "/var/log/pgbackrest"},
        {"name": "PGBACKREST_PG1_PATH", "value": "/var/lib/postgresql/data"}
      ],
      "volumeMounts": [
        {"name": "config", "mountPath": "/etc/pgbackrest"},
        {"name": "repo", "mountPath": "/var/lib/pgbackrest"},
        {"name": "pgdata", "mountPath": "/var/lib/postgresql/data"}
      ]
    }],
    "volumes": [
      {"name": "config", "configMap": {"name": "pgbackrest-config"}},
      {"name": "repo", "persistentVolumeClaim": {"claimName": "pgbackrest-repo"}},
      {"name": "pgdata", "persistentVolumeClaim": {"claimName": "postgres-data"}}
    ]
  }
}'
```

5. **Restart PostgreSQL**
6. **Restart application services**

### Point-in-Time Recovery (PITR)

To restore to a specific point in time:

```bash
# Replace YYYY-MM-DD HH:MM:SS with your desired timestamp
kubectl run -n ai-governance pgbackrest-restore-pitr --rm -it --restart=Never \
  --image=pgbackrest/pgbackrest:latest \
  --overrides='
{
  "spec": {
    "securityContext": {"runAsUser": 999, "runAsGroup": 999, "fsGroup": 999},
    "containers": [{
      "name": "pgbackrest-restore",
      "image": "pgbackrest/pgbackrest:latest",
      "command": ["/bin/bash", "-c"],
      "args": ["pgbackrest --stanza=mcpgov --type=time --target=\"2024-01-15 14:30:00\" restore"],
      "env": [
        {"name": "PGBACKREST_REPO1_PATH", "value": "/var/lib/pgbackrest"},
        {"name": "PGBACKREST_LOG_PATH", "value": "/var/log/pgbackrest"},
        {"name": "PGBACKREST_PG1_PATH", "value": "/var/lib/postgresql/data"}
      ],
      "volumeMounts": [
        {"name": "config", "mountPath": "/etc/pgbackrest"},
        {"name": "repo", "mountPath": "/var/lib/pgbackrest"},
        {"name": "pgdata", "mountPath": "/var/lib/postgresql/data"}
      ]
    }],
    "volumes": [
      {"name": "config", "configMap": {"name": "pgbackrest-config"}},
      {"name": "repo", "persistentVolumeClaim": {"claimName": "pgbackrest-repo"}},
      {"name": "pgdata", "persistentVolumeClaim": {"claimName": "postgres-data"}}
    ]
  }
}'
```

## S3 Configuration

To use S3 (or S3-compatible storage) instead of PVC:

1. Edit `pgbackrest-config.yaml` and uncomment the S3 configuration section:

```yaml
repo1-type=s3
repo1-s3-bucket=your-backup-bucket
repo1-s3-region=us-east-1
repo1-s3-endpoint=s3.amazonaws.com
```

2. Create a Secret with S3 credentials:

```bash
kubectl create secret generic pgbackrest-s3-credentials \
  --from-literal=s3-key=YOUR_ACCESS_KEY \
  --from-literal=s3-key-secret=YOUR_SECRET_KEY \
  -n ai-governance
```

3. Update the CronJobs and Job manifests to:
   - Remove the `pgbackrest-repo` PVC volume mount
   - Add environment variables for S3 credentials:

```yaml
env:
  - name: PGBACKREST_REPO1_S3_KEY
    valueFrom:
      secretKeyRef:
        name: pgbackrest-s3-credentials
        key: s3-key
  - name: PGBACKREST_REPO1_S3_KEY_SECRET
    valueFrom:
      secretKeyRef:
        name: pgbackrest-s3-credentials
        key: s3-key-secret
```

4. You can skip creating the PVC in this case, or keep it as an optional local cache.

## Retention Policy

The current configuration maintains:

- **Full backups**: 4 (daily for 4 days)
- **Differential backups**: 3 (every 6 hours, kept for ~18 hours after last full)
- **Archive logs**: 14 days

To modify retention, edit the `pgbackrest-config.yaml` ConfigMap:

```yaml
repo1-retention-full=7        # Keep 7 full backups (1 week)
repo1-retention-diff=6        # Keep 6 differential backups
repo1-retention-archive=30    # Keep 30 days of archive logs
```

Then reapply the ConfigMap:

```bash
kubectl apply -f pgbackrest-config.yaml
```

## Monitoring and Troubleshooting

### Check CronJob Status

```bash
kubectl get cronjobs -n ai-governance -l app=pgbackrest
```

### View Backup Job Logs

```bash
# List recent jobs
kubectl get jobs -n ai-governance -l app=pgbackrest --sort-by=.metadata.creationTimestamp

# View logs of a specific job
kubectl logs -n ai-governance job/pgbackrest-full-backup-XXXXXXXX
```

### Check Backup Repository Size

```bash
kubectl exec -n ai-governance -it <postgres-pod> -- du -sh /var/lib/pgbackrest
```

### Verify Stanza Status

```bash
kubectl run -n ai-governance pgbackrest-check --rm -it --restart=Never \
  --image=pgbackrest/pgbackrest:latest \
  --overrides='...' # (See "View Backup Information" above for the full command)
```

### Common Issues

**Issue**: Stanza creation fails with "unable to connect to PostgreSQL"
- **Solution**: Ensure PostgreSQL is running and accessible. Check the service name matches `postgres-service` or update the manifests accordingly.

**Issue**: Archive command fails
- **Solution**: Verify the archive_command in `postgresql.conf` is correct and pgBackRest is installed in the PostgreSQL pod or accessible via network.

**Issue**: Backup jobs fail with permission errors
- **Solution**: Ensure the security context (`runAsUser: 999`) matches the PostgreSQL user ID and that the PVC has the correct permissions.

## VM/Non-Kubernetes Deployment

For VM-based deployments, you can adapt these concepts using:

1. **Cron jobs on the VM** instead of Kubernetes CronJobs
2. **Local directories or network mounts** instead of PVCs
3. **systemd timers** as an alternative to cron for better logging and management

Example cron entries for a VM:

```bash
# Full backup daily at 2 AM
0 2 * * * postgres pgbackrest --stanza=mcpgov --type=full backup

# Differential backup every 6 hours
0 */6 * * * postgres pgbackrest --stanza=mcpgov --type=diff backup

# Restore validation weekly on Sundays at 3 AM
0 3 * * 0 postgres /usr/local/bin/pgbackrest-restore-validation.sh
```

Copy the `restore-validation.sh` script from the ConfigMap to `/usr/local/bin/` on your VM.

## Security Considerations

1. **Credentials**: Store PostgreSQL credentials securely using Kubernetes Secrets or a secret management system (Vault, AWS Secrets Manager, etc.)
2. **Encryption**: Enable encryption for backups stored in S3 or on disk
3. **Access Control**: Use RBAC to restrict who can access backup CronJobs and the backup repository PVC
4. **Network Policies**: Apply NetworkPolicies to restrict access to PostgreSQL and backup services
5. **Audit Logging**: Monitor backup job executions and failures

## References

- [pgBackRest Official Documentation](https://pgbackrest.org/)
- [pgBackRest User Guide](https://pgbackrest.org/user-guide.html)
- [PostgreSQL WAL Archiving](https://www.postgresql.org/docs/current/continuous-archiving.html)
