# pgBackRest Configuration for VM Deployment

This directory contains configuration files and systemd units for deploying pgBackRest on a VM or bare-metal server.

## Files

- `pgbackrest.conf` - Main pgBackRest configuration
- `postgresql-archive.conf` - PostgreSQL archive mode settings
- `cron-pgbackrest` - Cron schedule for automated backups
- `pgbackrest-full-backup.service` - Systemd service for full backups
- `pgbackrest-full-backup.timer` - Systemd timer for scheduling full backups
- `pgbackrest-diff-backup.service` - Systemd service for differential backups
- `pgbackrest-diff-backup.timer` - Systemd timer for scheduling differential backups

## Installation (Ubuntu/Debian)

### 1. Install pgBackRest

```bash
# Add PostgreSQL apt repository if not already added
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update and install
sudo apt-get update
sudo apt-get install pgbackrest
```

### 2. Configure pgBackRest

```bash
# Copy configuration to system location
sudo cp pgbackrest.conf /etc/pgbackrest/pgbackrest.conf
sudo chown postgres:postgres /etc/pgbackrest/pgbackrest.conf
sudo chmod 640 /etc/pgbackrest/pgbackrest.conf

# Create log directory
sudo mkdir -p /var/log/pgbackrest
sudo chown postgres:postgres /var/log/pgbackrest

# Create repository directory (local)
sudo mkdir -p /var/lib/pgbackrest
sudo chown postgres:postgres /var/lib/pgbackrest
```

### 3. Configure PostgreSQL

Add the archive settings to PostgreSQL configuration:

```bash
# Append to postgresql.conf (or include as a separate file)
sudo cat postgresql-archive.conf | sudo tee -a /etc/postgresql/16/main/postgresql.conf

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 4. Initialize pgBackRest Stanza

```bash
# Create the stanza
sudo -u postgres pgbackrest --stanza=mcpgov stanza-create

# Verify the stanza
sudo -u postgres pgbackrest --stanza=mcpgov check

# View stanza information
sudo -u postgres pgbackrest --stanza=mcpgov info
```

### 5. Perform Initial Full Backup

```bash
sudo -u postgres pgbackrest --stanza=mcpgov --type=full backup
```

## Scheduling Backups

You have two options for scheduling backups:

### Option A: Using Cron (Traditional)

```bash
# Copy cron file to system location
sudo cp cron-pgbackrest /etc/cron.d/pgbackrest
sudo chmod 644 /etc/cron.d/pgbackrest

# Edit to set your email for notifications
sudo nano /etc/cron.d/pgbackrest
```

### Option B: Using Systemd Timers (Recommended)

```bash
# Install systemd units
sudo cp pgbackrest-full-backup.service /etc/systemd/system/
sudo cp pgbackrest-full-backup.timer /etc/systemd/system/
sudo cp pgbackrest-diff-backup.service /etc/systemd/system/
sudo cp pgbackrest-diff-backup.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timers
sudo systemctl enable pgbackrest-full-backup.timer
sudo systemctl start pgbackrest-full-backup.timer

sudo systemctl enable pgbackrest-diff-backup.timer
sudo systemctl start pgbackrest-diff-backup.timer

# Check timer status
sudo systemctl list-timers pgbackrest-*
```

## Manual Operations

### View Backup Information

```bash
sudo -u postgres pgbackrest --stanza=mcpgov info
```

### Manual Backup

```bash
# Full backup
sudo -u postgres pgbackrest --stanza=mcpgov --type=full backup

# Differential backup
sudo -u postgres pgbackrest --stanza=mcpgov --type=diff backup

# Incremental backup
sudo -u postgres pgbackrest --stanza=mcpgov --type=incr backup
```

### Restore Operations

**Full restore:**

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Clear data directory (CAUTION: ensure you have backups!)
sudo rm -rf /var/lib/postgresql/16/main/*

# Restore
sudo -u postgres pgbackrest --stanza=mcpgov --pg1-path=/var/lib/postgresql/16/main restore

# Start PostgreSQL
sudo systemctl start postgresql
```

**Point-in-Time Recovery:**

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Clear data directory
sudo rm -rf /var/lib/postgresql/16/main/*

# Restore to specific time
sudo -u postgres pgbackrest --stanza=mcpgov \
  --pg1-path=/var/lib/postgresql/16/main \
  --type=time \
  --target="2024-01-15 14:30:00" \
  restore

# Start PostgreSQL
sudo systemctl start postgresql
```

## Monitoring

### Check Systemd Timer Status

```bash
# List all pgBackRest timers
sudo systemctl list-timers pgbackrest-*

# View logs
sudo journalctl -u pgbackrest-full-backup.service -n 50
sudo journalctl -u pgbackrest-diff-backup.service -n 50
```

### Check Backup Logs

```bash
# View recent log
sudo tail -f /var/log/pgbackrest/mcpgov-backup.log

# List all logs
sudo ls -lh /var/log/pgbackrest/
```

### Check Repository Size

```bash
sudo du -sh /var/lib/pgbackrest
```

## S3 Configuration

To use S3 for backup storage:

1. Edit `/etc/pgbackrest/pgbackrest.conf` and add:

```ini
[global]
repo1-type=s3
repo1-s3-bucket=your-backup-bucket
repo1-s3-region=us-east-1
repo1-s3-endpoint=s3.amazonaws.com
repo1-s3-key=YOUR_ACCESS_KEY
repo1-s3-key-secret=YOUR_SECRET_KEY
```

2. Or use IAM roles if running on AWS EC2 (preferred):

```ini
[global]
repo1-type=s3
repo1-s3-bucket=your-backup-bucket
repo1-s3-region=us-east-1
```

3. Restart the stanza:

```bash
sudo -u postgres pgbackrest --stanza=mcpgov stanza-upgrade
sudo -u postgres pgbackrest --stanza=mcpgov check
```

## Troubleshooting

**Issue: Archive command fails**
- Check PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql-16-main.log`
- Verify pgBackRest is accessible: `sudo -u postgres which pgbackrest`
- Check permissions on `/var/lib/pgbackrest`

**Issue: Stanza creation fails**
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check connection settings in `/etc/pgbackrest/pgbackrest.conf`
- Ensure `pg1-path` points to correct data directory

**Issue: Backup fails with "no prior backup exists"**
- Run a full backup first: `sudo -u postgres pgbackrest --stanza=mcpgov --type=full backup`

## Security Notes

1. Protect configuration files:
   ```bash
   sudo chmod 640 /etc/pgbackrest/pgbackrest.conf
   sudo chown postgres:postgres /etc/pgbackrest/pgbackrest.conf
   ```

2. For S3 credentials, consider using AWS IAM roles instead of access keys
3. Enable encryption: Add `repo1-cipher-type=aes-256-cbc` to config
4. Regularly test restores to ensure backup integrity

## References

- [pgBackRest Official Documentation](https://pgbackrest.org/)
- [pgBackRest User Guide](https://pgbackrest.org/user-guide.html)
