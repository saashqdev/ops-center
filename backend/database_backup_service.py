"""
Database Backup Service for Ops-Center

Provides automated PostgreSQL database backups with:
- Scheduled backups (configurable interval)
- Manual backup triggers via API
- Backup rotation and retention policies
- Compressed backup files
- Backup restoration capabilities
"""

import os
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import logging
import asyncio
import json

logger = logging.getLogger(__name__)


class DatabaseBackupService:
    """Service for managing PostgreSQL database backups"""
    
    def __init__(
        self,
        backup_dir: str = "/app/backups/database",
        retention_days: int = 7,
        max_backups: int = 30,
        auto_backup_interval_hours: int = 24
    ):
        """
        Initialize the database backup service.
        
        Args:
            backup_dir: Directory to store backup files
            retention_days: Number of days to keep backups
            max_backups: Maximum number of backups to keep
            auto_backup_interval_hours: Hours between automatic backups
        """
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.max_backups = max_backups
        self.auto_backup_interval_hours = auto_backup_interval_hours
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Database connection parameters from environment
        self.db_host = os.getenv('POSTGRES_HOST', 'postgresql')
        self.db_port = os.getenv('POSTGRES_PORT', '5432')
        self.db_name = os.getenv('POSTGRES_DB', 'unicorn_db')
        self.db_user = os.getenv('POSTGRES_USER', 'unicorn')
        self.db_password = os.getenv('POSTGRES_PASSWORD', 'change-me')
        
        logger.info(f"Database Backup Service initialized")
        logger.info(f"Backup directory: {self.backup_dir}")
        logger.info(f"Retention: {self.retention_days} days, Max backups: {self.max_backups}")
    
    def create_backup(self, description: str = "") -> Dict[str, any]:
        """
        Create a new database backup.
        
        Args:
            description: Optional description for the backup
            
        Returns:
            Dict with backup information
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{self.db_name}_{timestamp}.sql.gz"
        backup_path = self.backup_dir / backup_filename
        temp_sql_path = self.backup_dir / f"temp_{timestamp}.sql"
        
        try:
            logger.info(f"Creating database backup: {backup_filename}")
            
            # Use pg_dump to create SQL backup
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            cmd = [
                'pg_dump',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-F', 'p',  # Plain SQL format
                '-f', str(temp_sql_path),
                '--no-owner',  # Don't include ownership commands
                '--no-acl',    # Don't include ACL commands
            ]
            
            # Execute pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Compress the SQL file
            logger.info(f"Compressing backup file...")
            with open(temp_sql_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove temporary uncompressed file
            temp_sql_path.unlink()
            
            # Get backup file size
            backup_size = backup_path.stat().st_size
            backup_size_mb = backup_size / (1024 * 1024)
            
            # Create metadata file
            metadata = {
                'filename': backup_filename,
                'timestamp': timestamp,
                'created_at': datetime.now().isoformat(),
                'database': self.db_name,
                'size_bytes': backup_size,
                'size_mb': round(backup_size_mb, 2),
                'description': description,
                'compressed': True
            }
            
            metadata_path = self.backup_dir / f"{backup_filename}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Backup created successfully: {backup_filename} ({backup_size_mb:.2f} MB)")
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            return {
                'success': True,
                'backup_file': backup_filename,
                'size_mb': backup_size_mb,
                'path': str(backup_path),
                'metadata': metadata
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Backup timeout - database dump took too long")
            if temp_sql_path.exists():
                temp_sql_path.unlink()
            return {
                'success': False,
                'error': 'Backup timeout - operation took too long'
            }
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            if temp_sql_path.exists():
                temp_sql_path.unlink()
            if backup_path.exists():
                backup_path.unlink()
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_backup(self, backup_filename: str) -> Dict[str, any]:
        """
        Restore database from a backup file.
        
        Args:
            backup_filename: Name of the backup file to restore
            
        Returns:
            Dict with restoration status
        """
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            return {
                'success': False,
                'error': f'Backup file not found: {backup_filename}'
            }
        
        try:
            logger.warning(f"⚠️  Starting database restore from: {backup_filename}")
            
            # Decompress backup file
            temp_sql_path = self.backup_dir / f"restore_temp.sql"
            
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_sql_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Restore using psql
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            cmd = [
                'psql',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-f', str(temp_sql_path)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # Remove temporary file
            temp_sql_path.unlink()
            
            if result.returncode != 0:
                raise Exception(f"Database restore failed: {result.stderr}")
            
            logger.info(f"✅ Database restored successfully from: {backup_filename}")
            
            return {
                'success': True,
                'backup_file': backup_filename,
                'message': 'Database restored successfully'
            }
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            if temp_sql_path.exists():
                temp_sql_path.unlink()
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_backups(self) -> List[Dict[str, any]]:
        """
        List all available backups with metadata.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("backup_*.sql.gz"), reverse=True):
            metadata_file = self.backup_dir / f"{backup_file.name}.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                backups.append(metadata)
            else:
                # Create basic metadata if file doesn't exist
                stat = backup_file.stat()
                backups.append({
                    'filename': backup_file.name,
                    'size_bytes': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'compressed': True
                })
        
        return backups
    
    def delete_backup(self, backup_filename: str) -> Dict[str, any]:
        """
        Delete a specific backup file.
        
        Args:
            backup_filename: Name of the backup file to delete
            
        Returns:
            Dict with deletion status
        """
        backup_path = self.backup_dir / backup_filename
        metadata_path = self.backup_dir / f"{backup_filename}.json"
        
        if not backup_path.exists():
            return {
                'success': False,
                'error': f'Backup file not found: {backup_filename}'
            }
        
        try:
            backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"Deleted backup: {backup_filename}")
            return {
                'success': True,
                'message': f'Backup deleted: {backup_filename}'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy."""
        try:
            backups = list(self.backup_dir.glob("backup_*.sql.gz"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for i, backup_path in enumerate(backups):
                backup_date = datetime.fromtimestamp(backup_path.stat().st_mtime)
                metadata_path = self.backup_dir / f"{backup_path.name}.json"
                
                # Delete if older than retention period OR exceeds max count
                if backup_date < cutoff_date or i >= self.max_backups:
                    backup_path.unlink()
                    if metadata_path.exists():
                        metadata_path.unlink()
                    deleted_count += 1
                    logger.info(f"Cleaned up old backup: {backup_path.name}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backups")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
    
    async def run_scheduled_backups(self):
        """Run automatic backups on schedule."""
        logger.info(f"Starting scheduled backup service (every {self.auto_backup_interval_hours} hours)")
        
        while True:
            try:
                # Wait for the interval
                await asyncio.sleep(self.auto_backup_interval_hours * 3600)
                
                logger.info("Running scheduled backup...")
                result = self.create_backup(description="Automated scheduled backup")
                
                if result['success']:
                    logger.info(f"✅ Scheduled backup completed: {result['backup_file']}")
                else:
                    logger.error(f"❌ Scheduled backup failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error in scheduled backup: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


# Global service instance
backup_service: Optional[DatabaseBackupService] = None


def get_backup_service() -> DatabaseBackupService:
    """Get or create the backup service instance."""
    global backup_service
    
    if backup_service is None:
        # Read configuration from environment
        backup_dir = os.getenv('BACKUP_DIR', '/app/backups/database')
        retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
        max_backups = int(os.getenv('BACKUP_MAX_COUNT', '30'))
        interval_hours = int(os.getenv('BACKUP_INTERVAL_HOURS', '24'))
        
        backup_service = DatabaseBackupService(
            backup_dir=backup_dir,
            retention_days=retention_days,
            max_backups=max_backups,
            auto_backup_interval_hours=interval_hours
        )
    
    return backup_service
