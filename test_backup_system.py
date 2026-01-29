#!/usr/bin/env python3
"""
Simple test to verify backup system components load correctly
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Test that all modules import correctly"""
    print("Testing backup system imports...")
    
    try:
        from database_backup_service import DatabaseBackupService, get_backup_service
        print("✅ database_backup_service imports OK")
    except Exception as e:
        print(f"❌ database_backup_service import failed: {e}")
        return False
    
    try:
        from backup_api import router
        print("✅ backup_api imports OK")
    except Exception as e:
        print(f"❌ backup_api import failed: {e}")
        return False
    
    print("\n✅ All backup system components load successfully!")
    return True

def test_service_init():
    """Test basic service initialization"""
    print("\nTesting service initialization...")
    
    try:
        from database_backup_service import DatabaseBackupService
        
        service = DatabaseBackupService(
            backup_dir="/tmp/test_backups",
            retention_days=7,
            max_backups=30,
            auto_backup_interval_hours=24
        )
        
        print(f"✅ Service initialized")
        print(f"   Backup dir: {service.backup_dir}")
        print(f"   Retention: {service.retention_days} days")
        print(f"   Max backups: {service.max_backups}")
        print(f"   Interval: {service.auto_backup_interval_hours} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False

if __name__ == '__main__':
    success = True
    
    if not test_imports():
        success = False
    
    if not test_service_init():
        success = False
    
    if success:
        print("\n" + "="*60)
        print("✅ All tests passed! Backup system is ready to use.")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ Some tests failed. Check errors above.")
        print("="*60)
        sys.exit(1)
