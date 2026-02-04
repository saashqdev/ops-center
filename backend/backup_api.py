"""
Database Backup API

REST API endpoints for managing database backups:
- POST /api/backups - Create a new backup
- GET /api/backups - List all backups
- POST /api/backups/restore - Restore from backup
- DELETE /api/backups/{filename} - Delete a backup
- GET /api/backups/status - Get backup service status
- GET /api/backups/download/{filename} - Download a backup file
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime
from pathlib import Path

from database_backup_service import get_backup_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backups", tags=["backups"])


class CreateBackupRequest(BaseModel):
    """Request model for creating a backup"""
    description: Optional[str] = ""


class RestoreBackupRequest(BaseModel):
    """Request model for restoring a backup"""
    backup_filename: str


class BackupInfo(BaseModel):
    """Backup information response"""
    filename: str
    size_mb: float
    created_at: str
    description: Optional[str] = ""
    compressed: bool


class BackupStatusResponse(BaseModel):
    """Backup service status"""
    enabled: bool
    backup_directory: str
    retention_days: int
    max_backups: int
    interval_hours: int
    auto_backup_enabled: bool
    total_backups: int
    total_size_mb: float


class UpdateBackupSettingsRequest(BaseModel):
    """Request to update backup settings"""
    retention_days: Optional[int] = None
    max_backups: Optional[int] = None
    interval_hours: Optional[int] = None
    auto_backup_enabled: Optional[bool] = None


@router.post("/")
async def create_backup(request: CreateBackupRequest, background_tasks: BackgroundTasks):
    """
    Create a new database backup.
    
    This endpoint triggers a backup of the PostgreSQL database.
    The backup is compressed and stored in the configured backup directory.
    """
    try:
        service = get_backup_service()
        
        # Run backup synchronously (could take some time)
        result = service.create_backup(description=request.description)
        
        if result['success']:
            return {
                'success': True,
                'message': 'Backup created successfully',
                'backup': result['metadata']
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Backup failed'))
            
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[BackupInfo])
async def list_backups():
    """
    List all available database backups.
    
    Returns a list of all backup files with metadata including
    filename, size, creation date, and description.
    """
    try:
        service = get_backup_service()
        backups = service.list_backups()
        return backups
        
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore")
async def restore_backup(request: RestoreBackupRequest):
    """
    Restore database from a backup file.
    
    ⚠️ WARNING: This will overwrite the current database!
    Make sure to create a backup before restoring.
    """
    try:
        service = get_backup_service()
        
        # Run restore (this is a critical operation)
        result = service.restore_backup(request.backup_filename)
        
        if result['success']:
            return {
                'success': True,
                'message': 'Database restored successfully',
                'backup_file': request.backup_filename
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Restore failed'))
            
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{backup_filename}")
async def delete_backup(backup_filename: str):
    """
    Delete a specific backup file.
    
    Args:
        backup_filename: Name of the backup file to delete
    """
    try:
        service = get_backup_service()
        result = service.delete_backup(backup_filename)
        
        if result['success']:
            return {
                'success': True,
                'message': result['message']
            }
        else:
            raise HTTPException(status_code=404, detail=result.get('error', 'Backup not found'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status():
    """
    Get the current status of the backup service.
    
    Returns configuration and statistics about the backup system.
    """
    try:
        service = get_backup_service()
        backups = service.list_backups()
        
        # Calculate total size of all backups
        total_size_bytes = sum(backup.get('size_bytes', 0) for backup in backups)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
        
        return {
            'enabled': True,
            'backup_directory': str(service.backup_dir),
            'retention_days': service.retention_days,
            'max_backups': service.max_backups,
            'interval_hours': service.auto_backup_interval_hours,
            'auto_backup_enabled': service.auto_backup_enabled,
            'total_backups': len(backups),
            'total_size_mb': total_size_mb
        }
        
    except Exception as e:
        logger.error(f"Failed to get backup status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_backups():
    """
    Manually trigger cleanup of old backups.
    
    This removes backups older than the retention period
    and backups exceeding the maximum count.
    """
    try:
        service = get_backup_service()
        service.cleanup_old_backups()
        
        return {
            'success': True,
            'message': 'Cleanup completed'
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_backup_settings(request: UpdateBackupSettingsRequest):
    """
    Update backup configuration settings.
    
    Args:
        request: Settings to update (only provided fields will be updated)
    """
    try:
        service = get_backup_service()
        
        # Update settings if provided
        if request.retention_days is not None:
            service.retention_days = request.retention_days
        if request.max_backups is not None:
            service.max_backups = request.max_backups
        if request.interval_hours is not None:
            service.auto_backup_interval_hours = request.interval_hours
        if request.auto_backup_enabled is not None:
            service.auto_backup_enabled = request.auto_backup_enabled
        
        logger.info(f"Backup settings updated: retention={service.retention_days}d, max={service.max_backups}, interval={service.auto_backup_interval_hours}h, auto_enabled={service.auto_backup_enabled}")
        
        return {
            'success': True,
            'retention_days': service.retention_days,
            'max_backups': service.max_backups,
            'interval_hours': service.auto_backup_interval_hours,
            'auto_backup_enabled': service.auto_backup_enabled
        }
        
    except Exception as e:
        logger.error(f"Failed to update settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{backup_filename}")
async def download_backup(backup_filename: str):
    """
    Download a backup file.
    
    Args:
        backup_filename: Name of the backup file to download
    """
    try:
        service = get_backup_service()
        backup_path = service.backup_dir / backup_filename
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail=f"Backup file not found: {backup_filename}")
        
        return FileResponse(
            path=str(backup_path),
            filename=backup_filename,
            media_type='application/gzip'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

