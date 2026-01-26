"""
Automated Backup Plugin

Automatically backs up device configurations and Ops-Center data.
Demonstrates: Scheduled tasks, file operations, compression, external storage
"""

from ops_center_sdk import Plugin
from typing import Dict, Any, List
from datetime import datetime, timedelta
import tarfile
import gzip
import shutil
import os
from pathlib import Path


# Create plugin instance
plugin = Plugin(
    id="automated-backup",
    name="Automated Backup",
    version="1.0.0",
    description="Automated backups of device configs and system data",
    author="Ops-Center Team",
    category="security"
)


# ==================== Configuration ====================

plugin.config.set("backup_schedule", "0 2 * * *")  # Daily at 2 AM
plugin.config.set("backup_path", "/var/backups/ops-center")
plugin.config.set("retention_days", 30)
plugin.config.set("compress_backups", True)
plugin.config.set("backup_device_configs", True)
plugin.config.set("backup_alerts", True)
plugin.config.set("backup_users", False)  # Privacy consideration
plugin.config.set("max_backup_size_mb", 1024)  # 1GB limit


# ==================== Lifecycle Hooks ====================

@plugin.on_install
async def on_install():
    """Initialize backup system"""
    plugin.logger.info("Installing Automated Backup plugin...")
    
    # Create backup directory
    backup_path = plugin.config.get("backup_path")
    Path(backup_path).mkdir(parents=True, exist_ok=True)
    
    # Initialize stats
    await plugin.storage.set("backups_created", 0)
    await plugin.storage.set("total_backup_size", 0)
    await plugin.storage.set("last_backup_time", None)
    
    plugin.logger.info(f"Backup directory created: {backup_path}")


@plugin.on_enable
async def on_enable():
    """Start backup scheduler"""
    plugin.logger.info("Enabling automated backups...")
    
    # Schedule daily backup
    schedule = plugin.config.get("backup_schedule", "0 2 * * *")
    
    await plugin.scheduler.schedule(
        cron=schedule,
        task_name="daily_backup",
        handler=perform_backup
    )
    
    # Schedule cleanup
    await plugin.scheduler.schedule(
        cron="0 3 * * *",  # Daily at 3 AM
        task_name="cleanup_old_backups",
        handler=cleanup_old_backups
    )
    
    plugin.logger.info(f"Backup scheduled: {schedule}")


@plugin.on_disable
async def on_disable():
    """Stop backup scheduler"""
    plugin.logger.info("Disabling automated backups...")
    
    await plugin.scheduler.cancel_all()
    
    plugin.logger.info("Backup scheduler stopped")


# ==================== Backup Functions ====================

async def perform_backup() -> Dict[str, Any]:
    """
    Perform full backup
    
    Returns backup metadata
    """
    plugin.logger.info("Starting backup process...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = plugin.config.get("backup_path")
    backup_name = f"backup_{timestamp}"
    backup_dir = Path(backup_path) / backup_name
    
    # Create backup directory
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_metadata = {
        "timestamp": timestamp,
        "started_at": datetime.now().isoformat(),
        "components": [],
        "total_items": 0,
        "total_size": 0,
        "status": "in_progress"
    }
    
    try:
        # Backup device configurations
        if plugin.config.get("backup_device_configs", True):
            plugin.logger.info("Backing up device configurations...")
            
            devices = await plugin.api.devices.list(page_size=1000)
            device_count = await backup_devices(backup_dir, devices)
            
            backup_metadata["components"].append({
                "name": "devices",
                "count": device_count
            })
            backup_metadata["total_items"] += device_count
        
        # Backup alerts
        if plugin.config.get("backup_alerts", True):
            plugin.logger.info("Backing up alerts...")
            
            alerts = await plugin.api.alerts.list()
            alert_count = await backup_alerts(backup_dir, alerts)
            
            backup_metadata["components"].append({
                "name": "alerts",
                "count": alert_count
            })
            backup_metadata["total_items"] += alert_count
        
        # Backup users (if enabled)
        if plugin.config.get("backup_users", False):
            plugin.logger.info("Backing up users...")
            
            users = await plugin.api.users.list()
            user_count = await backup_users(backup_dir, users)
            
            backup_metadata["components"].append({
                "name": "users",
                "count": user_count
            })
            backup_metadata["total_items"] += user_count
        
        # Compress backup
        if plugin.config.get("compress_backups", True):
            plugin.logger.info("Compressing backup...")
            
            archive_path = await compress_backup(backup_dir, backup_path, backup_name)
            
            # Get archive size
            backup_metadata["total_size"] = os.path.getsize(archive_path)
            backup_metadata["archive_path"] = str(archive_path)
            
            # Remove uncompressed directory
            shutil.rmtree(backup_dir)
        else:
            # Calculate directory size
            backup_metadata["total_size"] = sum(
                f.stat().st_size for f in backup_dir.rglob('*') if f.is_file()
            )
            backup_metadata["backup_path"] = str(backup_dir)
        
        backup_metadata["status"] = "completed"
        backup_metadata["completed_at"] = datetime.now().isoformat()
        
        # Update statistics
        backups_created = await plugin.storage.get("backups_created", 0)
        total_size = await plugin.storage.get("total_backup_size", 0)
        
        await plugin.storage.set("backups_created", backups_created + 1)
        await plugin.storage.set("total_backup_size", total_size + backup_metadata["total_size"])
        await plugin.storage.set("last_backup_time", datetime.now().isoformat())
        await plugin.storage.set(f"backup:{timestamp}", backup_metadata)
        
        plugin.logger.info(
            f"Backup completed: {backup_metadata['total_items']} items, "
            f"{backup_metadata['total_size'] / (1024*1024):.2f} MB"
        )
        
        # Create alert for successful backup
        await plugin.api.alerts.create({
            "severity": "info",
            "title": "Backup Completed",
            "message": f"Backup {backup_name} completed successfully. "
                      f"{backup_metadata['total_items']} items backed up."
        })
        
        return backup_metadata
        
    except Exception as e:
        plugin.logger.error(f"Backup failed: {e}")
        
        backup_metadata["status"] = "failed"
        backup_metadata["error"] = str(e)
        backup_metadata["completed_at"] = datetime.now().isoformat()
        
        # Create alert for failed backup
        await plugin.api.alerts.create({
            "severity": "error",
            "title": "Backup Failed",
            "message": f"Backup {backup_name} failed: {str(e)}"
        })
        
        return backup_metadata


async def backup_devices(backup_dir: Path, devices: List[Dict]) -> int:
    """Backup device configurations"""
    devices_dir = backup_dir / "devices"
    devices_dir.mkdir(exist_ok=True)
    
    for device in devices:
        device_file = devices_dir / f"{device['id']}.json"
        
        import json
        with open(device_file, 'w') as f:
            json.dump(device, f, indent=2)
    
    return len(devices)


async def backup_alerts(backup_dir: Path, alerts: List[Dict]) -> int:
    """Backup alerts"""
    alerts_file = backup_dir / "alerts.json"
    
    import json
    with open(alerts_file, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return len(alerts)


async def backup_users(backup_dir: Path, users: List[Dict]) -> int:
    """Backup user data (without passwords)"""
    users_dir = backup_dir / "users"
    users_dir.mkdir(exist_ok=True)
    
    import json
    for user in users:
        # Remove sensitive data
        safe_user = {k: v for k, v in user.items() if k not in ['password', 'password_hash']}
        
        user_file = users_dir / f"{user['id']}.json"
        with open(user_file, 'w') as f:
            json.dump(safe_user, f, indent=2)
    
    return len(users)


async def compress_backup(backup_dir: Path, backup_path: str, backup_name: str) -> Path:
    """Compress backup directory to tar.gz"""
    archive_path = Path(backup_path) / f"{backup_name}.tar.gz"
    
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(backup_dir, arcname=backup_name)
    
    return archive_path


async def cleanup_old_backups():
    """Remove backups older than retention period"""
    plugin.logger.info("Cleaning up old backups...")
    
    retention_days = plugin.config.get("retention_days", 30)
    backup_path = Path(plugin.config.get("backup_path"))
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    removed_count = 0
    
    # Check compressed backups
    for backup_file in backup_path.glob("backup_*.tar.gz"):
        # Extract timestamp from filename
        timestamp_str = backup_file.stem.replace("backup_", "")
        
        try:
            backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if backup_date < cutoff_date:
                backup_file.unlink()
                removed_count += 1
                plugin.logger.info(f"Removed old backup: {backup_file.name}")
        except ValueError:
            pass
    
    # Check uncompressed backups
    for backup_dir in backup_path.glob("backup_*"):
        if backup_dir.is_dir():
            timestamp_str = backup_dir.name.replace("backup_", "")
            
            try:
                backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if backup_date < cutoff_date:
                    shutil.rmtree(backup_dir)
                    removed_count += 1
                    plugin.logger.info(f"Removed old backup: {backup_dir.name}")
            except ValueError:
                pass
    
    plugin.logger.info(f"Cleanup completed: {removed_count} old backups removed")


# ==================== Custom API Routes ====================

@plugin.route("/backup/now", methods=["POST"])
async def trigger_backup_now(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger immediate backup
    
    POST /plugins/automated-backup/backup/now
    """
    plugin.logger.info("Manual backup triggered")
    
    backup_metadata = await perform_backup()
    
    return {
        "success": backup_metadata["status"] == "completed",
        "backup": backup_metadata
    }


@plugin.route("/backups", methods=["GET"])
async def list_backups() -> Dict[str, Any]:
    """
    List all backups
    
    GET /plugins/automated-backup/backups
    """
    backup_path = Path(plugin.config.get("backup_path"))
    
    backups = []
    
    # List compressed backups
    for backup_file in sorted(backup_path.glob("backup_*.tar.gz"), reverse=True):
        timestamp_str = backup_file.stem.replace("backup_", "")
        
        backups.append({
            "name": backup_file.name,
            "timestamp": timestamp_str,
            "size": backup_file.stat().st_size,
            "path": str(backup_file),
            "compressed": True
        })
    
    # List uncompressed backups
    for backup_dir in sorted(backup_path.glob("backup_*"), reverse=True):
        if backup_dir.is_dir():
            timestamp_str = backup_dir.name.replace("backup_", "")
            
            size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
            
            backups.append({
                "name": backup_dir.name,
                "timestamp": timestamp_str,
                "size": size,
                "path": str(backup_dir),
                "compressed": False
            })
    
    return {
        "backups": backups,
        "total_count": len(backups)
    }


@plugin.route("/stats", methods=["GET"])
async def get_stats() -> Dict[str, Any]:
    """
    Get backup statistics
    
    GET /plugins/automated-backup/stats
    """
    return {
        "backups_created": await plugin.storage.get("backups_created", 0),
        "total_backup_size": await plugin.storage.get("total_backup_size", 0),
        "last_backup_time": await plugin.storage.get("last_backup_time"),
        "backup_path": plugin.config.get("backup_path"),
        "retention_days": plugin.config.get("retention_days"),
        "schedule": plugin.config.get("backup_schedule")
    }


# ==================== Export FastAPI App ====================

app = plugin.create_app()


@app.on_event("startup")
async def startup():
    plugin.logger.info(f"Starting {plugin.metadata.name} v{plugin.metadata.version}")


@app.on_event("shutdown")
async def shutdown():
    plugin.logger.info("Shutting down Automated Backup")
    await plugin.api.close()
