# Database Backup System

## Overview

The Ops-Center includes an integrated PostgreSQL database backup system with automated scheduling, retention policies, and restore capabilities.

## Features

- **Automated Backups**: Scheduled backups run automatically at configurable intervals
- **Compression**: Backups are gzip-compressed to save storage space
- **Retention Policy**: Automatic cleanup based on age and count limits
- **REST API**: Full API for backup management
- **CLI Tool**: Command-line interface for manual operations
- **Metadata Tracking**: JSON metadata for each backup with size, timestamp, and description

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Backup directory
BACKUP_DIR=/app/backups/database

# Retention settings
BACKUP_RETENTION_DAYS=7      # Keep backups for 7 days
BACKUP_MAX_COUNT=30          # Keep maximum 30 backups

# Automation
BACKUP_INTERVAL_HOURS=24     # Run backup every 24 hours
BACKUP_ENABLED=true          # Enable scheduled backups
```

### Docker Volume Configuration

Add a volume mount to your `docker-compose.yml` to persist backups:

```yaml
services:
  ops-center:
    volumes:
      # ... existing volumes ...
      - backup-data:/app/backups

volumes:
  backup-data:
    driver: local
```

For external/persistent storage:

```yaml
volumes:
  backup-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/backup/storage
```

## Usage

### REST API

The backup API is available at `/api/backups`:

#### Create Backup

```bash
curl -X POST http://localhost:3001/api/backups \
  -H "Content-Type: application/json" \
  -d '{"description": "Manual backup before upgrade"}'
```

#### List Backups

```bash
curl http://localhost:3001/api/backups
```

#### Restore Backup

⚠️ **WARNING**: This will overwrite the current database!

```bash
curl -X POST http://localhost:3001/api/backups/restore \
  -H "Content-Type: application/json" \
  -d '{"backup_filename": "backup_unicorn_db_20260129_120000.sql.gz"}'
```

#### Delete Backup

```bash
curl -X DELETE http://localhost:3001/api/backups/backup_unicorn_db_20260129_120000.sql.gz
```

#### Get Status

```bash
curl http://localhost:3001/api/backups/status
```

#### Cleanup Old Backups

```bash
curl -X POST http://localhost:3001/api/backups/cleanup
```

### CLI Tool

The CLI tool provides a simple command-line interface:

#### Create a Backup

```bash
# Simple backup
./backup-database.sh create

# With description
./backup-database.sh create --description "Before major update"

# Or use Python directly
python3 backend/backup_cli.py create -d "My backup"
```

#### List All Backups

```bash
./backup-database.sh list
```

Output:
```
📦 Available Backups (5):
────────────────────────────────────────────────────────────────────────────────
Filename                                      Size         Created                   Description
────────────────────────────────────────────────────────────────────────────────
backup_unicorn_db_20260129_143022.sql.gz      15.32 MB     2026-01-29 14:30:22      Before upgrade
backup_unicorn_db_20260129_120000.sql.gz      14.87 MB     2026-01-29 12:00:00      Automated scheduled backup
...
────────────────────────────────────────────────────────────────────────────────
Total: 5 backups, 72.45 MB
```

#### Restore from Backup

```bash
./backup-database.sh restore backup_unicorn_db_20260129_120000.sql.gz
```

You'll be prompted to confirm:
```
⚠️  WARNING: This will restore the database from backup!
   Backup file: backup_unicorn_db_20260129_120000.sql.gz

   Type 'yes' to continue:
```

#### Delete a Backup

```bash
./backup-database.sh delete backup_unicorn_db_20260129_120000.sql.gz
```

#### Cleanup Old Backups

Manually trigger cleanup based on retention policy:

```bash
./backup-database.sh cleanup
```

### Docker Exec

If running in Docker, you can execute commands inside the container:

```bash
# Create backup
docker exec ops-center python3 backend/backup_cli.py create

# List backups
docker exec ops-center python3 backend/backup_cli.py list

# Restore backup
docker exec ops-center python3 backend/backup_cli.py restore <filename>
```

## Scheduled Backups

The backup service automatically starts when the application launches and runs backups according to `BACKUP_INTERVAL_HOURS`.

### Default Schedule

- **Interval**: Every 24 hours (configurable)
- **First Run**: 24 hours after startup
- **Description**: "Automated scheduled backup"

### Monitoring

Check application logs for backup activity:

```bash
# View logs
docker logs -f ops-center | grep -i backup

# Expected output
[INFO] Database Backup Service initialized (interval: 24h)
[INFO] Running scheduled backup...
[INFO] ✅ Backup created successfully: backup_unicorn_db_20260129_120000.sql.gz (14.87 MB)
[INFO] ✅ Scheduled backup completed: backup_unicorn_db_20260129_120000.sql.gz
```

## Backup File Format

Backups are stored with the following structure:

```
/app/backups/database/
├── backup_unicorn_db_20260129_143022.sql.gz       # Compressed SQL dump
├── backup_unicorn_db_20260129_143022.sql.gz.json  # Metadata
├── backup_unicorn_db_20260129_120000.sql.gz
└── backup_unicorn_db_20260129_120000.sql.gz.json
```

### Metadata Format

```json
{
  "filename": "backup_unicorn_db_20260129_143022.sql.gz",
  "timestamp": "20260129_143022",
  "created_at": "2026-01-29T14:30:22.123456",
  "database": "unicorn_db",
  "size_bytes": 16070144,
  "size_mb": 15.32,
  "description": "Before major update",
  "compressed": true
}
```

## Retention Policy

Backups are automatically cleaned up based on:

1. **Age**: Older than `BACKUP_RETENTION_DAYS` (default: 7 days)
2. **Count**: Exceeds `BACKUP_MAX_COUNT` (default: 30 backups)

Cleanup runs:
- After each backup creation
- When manually triggered via API or CLI

**Note**: The system keeps backups that meet either criteria, so you'll always have the most recent `BACKUP_MAX_COUNT` backups, even if they're older than the retention period.

## Best Practices

### Before Major Updates

```bash
./backup-database.sh create --description "Before v2.0 upgrade"
```

### Regular Monitoring

```bash
# Check backup status
curl http://localhost:3001/api/backups/status

# List recent backups
./backup-database.sh list | head -n 15
```

### Disaster Recovery

1. **Keep External Copies**: Copy critical backups to external storage
   ```bash
   docker cp ops-center:/app/backups/database/backup_*.sql.gz ./external-backup/
   ```

2. **Test Restores**: Periodically test restore procedures in staging
   ```bash
   # Staging environment
   ./backup-database.sh restore backup_unicorn_db_YYYYMMDD_HHMMSS.sql.gz
   ```

3. **Monitor Disk Space**: Ensure adequate storage for backups
   ```bash
   df -h /app/backups
   ```

### Backup Before Critical Operations

- Database migrations
- Major version upgrades
- Data cleanup operations
- Configuration changes

## Troubleshooting

### Backup Fails

**Error**: `pg_dump: error: connection to server failed`

**Solution**: Check database connection settings:
```bash
echo $POSTGRES_HOST
echo $POSTGRES_PORT
```

### Out of Disk Space

**Error**: `OSError: [Errno 28] No space left on device`

**Solution**: 
1. Reduce `BACKUP_RETENTION_DAYS` or `BACKUP_MAX_COUNT`
2. Run cleanup manually: `./backup-database.sh cleanup`
3. Add more storage to backup volume

### Restore Fails

**Error**: `psql: error: connection refused`

**Solution**: Ensure database is running and accessible

### Permission Denied

**Error**: `Permission denied: '/app/backups/database'`

**Solution**: Check volume permissions or run with appropriate user

## Security Considerations

1. **Backup Encryption**: Consider encrypting backups for sensitive data
2. **Access Control**: Restrict API access to authorized users
3. **Storage Security**: Ensure backup directory has appropriate permissions
4. **Off-site Backups**: Maintain copies outside the primary server

## API Response Examples

### Successful Backup

```json
{
  "success": true,
  "message": "Backup created successfully",
  "backup": {
    "filename": "backup_unicorn_db_20260129_143022.sql.gz",
    "timestamp": "20260129_143022",
    "created_at": "2026-01-29T14:30:22.123456",
    "size_mb": 15.32,
    "description": "Manual backup"
  }
}
```

### Backup List

```json
[
  {
    "filename": "backup_unicorn_db_20260129_143022.sql.gz",
    "size_mb": 15.32,
    "created_at": "2026-01-29T14:30:22.123456",
    "description": "Before upgrade",
    "compressed": true
  }
]
```

### Status Response

```json
{
  "enabled": true,
  "backup_directory": "/app/backups/database",
  "retention_days": 7,
  "max_backups": 30,
  "interval_hours": 24,
  "total_backups": 5
}
```

## Integration with CI/CD

### Pre-Deployment Backup

Add to your deployment pipeline:

```yaml
- name: Create Pre-Deployment Backup
  run: |
    curl -X POST http://ops-center:3001/api/backups \
      -H "Content-Type: application/json" \
      -d '{"description": "Pre-deployment backup - Build ${{ github.run_number }}"}'
```

### Health Checks

```yaml
- name: Verify Backup System
  run: |
    status=$(curl -s http://ops-center:3001/api/backups/status)
    echo $status | jq '.enabled' | grep -q true
```
