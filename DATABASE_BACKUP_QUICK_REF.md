# Database Backup - Quick Reference

## Quick Start

```bash
# Create a backup
./backup-database.sh create

# List backups
./backup-database.sh list

# Restore backup
./backup-database.sh restore <filename>
```

## Configuration (.env)

```bash
BACKUP_DIR=/app/backups/database
BACKUP_RETENTION_DAYS=7
BACKUP_MAX_COUNT=30
BACKUP_INTERVAL_HOURS=24
```

## API Endpoints

```bash
# Create
POST /api/backups

# List
GET /api/backups

# Restore (⚠️ DESTRUCTIVE)
POST /api/backups/restore

# Delete
DELETE /api/backups/{filename}

# Status
GET /api/backups/status
```

## Docker Commands

```bash
# Backup inside container
docker exec ops-center python3 backend/backup_cli.py create

# Copy to host
docker cp ops-center:/app/backups/database ./backups

# List backups
docker exec ops-center python3 backend/backup_cli.py list
```

## File Locations

- **Service**: `backend/database_backup_service.py`
- **API**: `backend/backup_api.py`
- **CLI**: `backend/backup_cli.py`
- **Script**: `backup-database.sh`
- **Backups**: `/app/backups/database/`

## Backup Filename Format

```
backup_<database>_<YYYYMMDD>_<HHMMSS>.sql.gz
```

Example: `backup_unicorn_db_20260129_143022.sql.gz`

## Features

- ✅ Automated scheduled backups
- ✅ Gzip compression (~85% reduction)
- ✅ Automatic retention/cleanup
- ✅ REST API & CLI interfaces
- ✅ Metadata tracking
- ✅ Point-in-time restore

## Common Tasks

### Before Upgrade
```bash
./backup-database.sh create --description "Before v2.0 upgrade"
```

### Daily Check
```bash
./backup-database.sh list | head -n 10
```

### Emergency Restore
```bash
# Get latest backup
LATEST=$(docker exec ops-center python3 backend/backup_cli.py list | head -n 4 | tail -n 1 | awk '{print $1}')

# Restore
docker exec ops-center python3 backend/backup_cli.py restore $LATEST
```

### Cleanup
```bash
./backup-database.sh cleanup
```

## Monitoring

```bash
# Check status
curl http://localhost:3001/api/backups/status

# Watch logs
docker logs -f ops-center | grep -i backup
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| pg_dump not found | `apt install postgresql-client` |
| Permission denied | Check `BACKUP_DIR` permissions |
| Out of space | Reduce retention or add storage |
| Connection refused | Check `POSTGRES_HOST` settings |

## Production Setup

```yaml
# docker-compose.yml
services:
  ops-center:
    volumes:
      - /mnt/backups:/app/backups
    environment:
      - BACKUP_RETENTION_DAYS=14
      - BACKUP_MAX_COUNT=60
      - BACKUP_INTERVAL_HOURS=12
```

## Documentation

- **Full Guide**: `DATABASE_BACKUP_GUIDE.md`
- **Implementation**: `DATABASE_BACKUP_IMPLEMENTATION.md`
- **Config Example**: `config/backup.env`
- **Docker Example**: `docker-compose.backup.yml`
