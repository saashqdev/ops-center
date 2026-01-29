#!/usr/bin/env python3
"""
Database Backup CLI Tool

Simple command-line tool for managing database backups.

Usage:
    python backup_cli.py create [--description "text"]
    python backup_cli.py list
    python backup_cli.py restore <backup_filename>
    python backup_cli.py delete <backup_filename>
    python backup_cli.py cleanup
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database_backup_service import DatabaseBackupService
import argparse
from datetime import datetime


def format_size(size_mb):
    """Format size in MB with appropriate unit"""
    if size_mb < 1:
        return f"{size_mb * 1024:.2f} KB"
    elif size_mb > 1024:
        return f"{size_mb / 1024:.2f} GB"
    else:
        return f"{size_mb:.2f} MB"


def create_backup(args):
    """Create a new backup"""
    print("🔄 Creating database backup...")
    
    service = DatabaseBackupService()
    result = service.create_backup(description=args.description or "")
    
    if result['success']:
        print(f"✅ Backup created successfully!")
        print(f"   File: {result['backup_file']}")
        print(f"   Size: {format_size(result['size_mb'])}")
        print(f"   Path: {result['path']}")
    else:
        print(f"❌ Backup failed: {result.get('error')}")
        sys.exit(1)


def list_backups(args):
    """List all backups"""
    service = DatabaseBackupService()
    backups = service.list_backups()
    
    if not backups:
        print("No backups found.")
        return
    
    print(f"\n📦 Available Backups ({len(backups)}):")
    print("-" * 100)
    print(f"{'Filename':<45} {'Size':<12} {'Created':<25} {'Description'}")
    print("-" * 100)
    
    for backup in backups:
        created = backup.get('created_at', '')
        if created:
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        size_str = format_size(backup.get('size_mb', 0))
        desc = backup.get('description', '')[:30]
        
        print(f"{backup['filename']:<45} {size_str:<12} {created:<25} {desc}")
    
    print("-" * 100)
    
    # Calculate total size
    total_mb = sum(b.get('size_mb', 0) for b in backups)
    print(f"\nTotal: {len(backups)} backups, {format_size(total_mb)}")


def restore_backup(args):
    """Restore from a backup"""
    print(f"⚠️  WARNING: This will restore the database from backup!")
    print(f"   Backup file: {args.backup_filename}")
    
    confirm = input("\n   Type 'yes' to continue: ")
    if confirm.lower() != 'yes':
        print("Restore cancelled.")
        return
    
    print("\n🔄 Restoring database...")
    
    service = DatabaseBackupService()
    result = service.restore_backup(args.backup_filename)
    
    if result['success']:
        print(f"✅ Database restored successfully!")
    else:
        print(f"❌ Restore failed: {result.get('error')}")
        sys.exit(1)


def delete_backup(args):
    """Delete a backup"""
    print(f"⚠️  Are you sure you want to delete: {args.backup_filename}?")
    confirm = input("   Type 'yes' to confirm: ")
    
    if confirm.lower() != 'yes':
        print("Delete cancelled.")
        return
    
    service = DatabaseBackupService()
    result = service.delete_backup(args.backup_filename)
    
    if result['success']:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ Delete failed: {result.get('error')}")
        sys.exit(1)


def cleanup_old_backups(args):
    """Cleanup old backups"""
    print("🔄 Cleaning up old backups...")
    
    service = DatabaseBackupService()
    service.cleanup_old_backups()
    
    print("✅ Cleanup completed")


def main():
    parser = argparse.ArgumentParser(
        description='Database Backup Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a backup
  python backup_cli.py create --description "Before major update"
  
  # List all backups
  python backup_cli.py list
  
  # Restore from backup
  python backup_cli.py restore backup_unicorn_db_20260129_120000.sql.gz
  
  # Delete a backup
  python backup_cli.py delete backup_unicorn_db_20260129_120000.sql.gz
  
  # Cleanup old backups
  python backup_cli.py cleanup
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True
    
    # Create backup
    create_parser = subparsers.add_parser('create', help='Create a new backup')
    create_parser.add_argument('--description', '-d', help='Backup description')
    create_parser.set_defaults(func=create_backup)
    
    # List backups
    list_parser = subparsers.add_parser('list', help='List all backups')
    list_parser.set_defaults(func=list_backups)
    
    # Restore backup
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_filename', help='Backup file to restore from')
    restore_parser.set_defaults(func=restore_backup)
    
    # Delete backup
    delete_parser = subparsers.add_parser('delete', help='Delete a backup')
    delete_parser.add_argument('backup_filename', help='Backup file to delete')
    delete_parser.set_defaults(func=delete_backup)
    
    # Cleanup old backups
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old backups')
    cleanup_parser.set_defaults(func=cleanup_old_backups)
    
    # Parse and execute
    args = parser.parse_args()
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
