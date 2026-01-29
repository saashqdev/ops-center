# Backup Management Frontend - User Guide

## Overview

The Backup Management Frontend provides a comprehensive web interface for managing database backups, cloud storage integration, and automated backup scheduling.

## Components

### 1. BackupDashboard.js
Main dashboard component with tabbed interface for backups and settings.

### 2. BackupManager.js
Full-featured backup management interface with:
- **Backup List**: View all database backups with details
- **Create Backup**: Manual backup creation with optional descriptions
- **Restore Database**: Point-in-time database restoration
- **Cloud Upload**: Upload backups to configured cloud storage (rclone)
- **Delete Backup**: Remove individual backup files
- **Cleanup**: Automated cleanup of old backups

### 3. BackupSettings.js
Configuration interface for:
- **Schedule Settings**: Configure automated backup intervals
- **Retention Policy**: Set retention days and maximum backup count
- **Cloud Remotes**: Configure rclone cloud storage providers
- **Enable/Disable**: Toggle automated backups

## Features

### 📊 Status Dashboard

Displays real-time backup statistics:
- Total number of backups
- Retention period (days)
- Backup interval (hours)
- Service status (Active/Disabled)

### 💾 Backup Operations

**Create Backup**
- Click "Create Backup" button
- Add optional description
- Backup is created and compressed automatically
- Progress indicator shows backup status

**View Backups**
- Table view with sortable columns
- Pagination for large backup lists
- File size, creation date, and descriptions
- Search and filter capabilities

**Restore Database**
- Select backup from list
- Review backup details
- Confirm restoration (with warning)
- Database is restored from selected backup
- ⚠️ **WARNING**: This overwrites current data!

**Delete Backup**
- Select backup to delete
- Confirm deletion
- Backup file and metadata removed

### ☁️ Cloud Integration

**Supported Providers** (via rclone):
- Amazon S3
- Google Drive
- Dropbox
- Microsoft OneDrive
- Backblaze B2
- Azure Blob Storage
- Google Cloud Storage
- SFTP
- WebDAV
- And 30+ more providers

**Upload to Cloud**
- Select backup file
- Choose configured cloud remote
- Specify remote path
- Backup is uploaded to cloud storage
- Progress tracking and notifications

**Configure Cloud Remote**
- Add new remote from settings
- Select cloud provider
- Configure credentials
- Test connection
- Save configuration

### ⚙️ Settings

**Backup Schedule**
- Enable/disable automated backups
- Set interval (hours between backups)
- Configure retention period (days)
- Set maximum backup count

**Storage Management**
- View total backups and storage usage
- Configure backup directory
- Set retention policies
- Cleanup old backups automatically

## Usage Examples

### Creating a Manual Backup

```
1. Navigate to Backup Dashboard
2. Click "Create Backup" button
3. Enter description (e.g., "Before v2.0 upgrade")
4. Click "Create Backup"
5. Wait for completion notification
6. Backup appears in list
```

### Restoring from Backup

```
1. Locate backup in list
2. Click restore icon (circular arrow)
3. Review backup details in dialog
4. Read warning carefully
5. Click "Restore Database"
6. Confirm action
7. Wait for restoration to complete
8. Application may restart
```

### Uploading to Cloud Storage

```
1. Ensure cloud remote is configured (Settings tab)
2. Click cloud upload icon on backup row
3. Select cloud remote from dropdown
4. Enter remote path (e.g., "backups/production/")
5. Click "Upload"
6. Monitor progress
7. Receive completion notification
```

### Configuring Automated Backups

```
1. Go to Settings tab
2. Toggle "Enable Automated Backups" ON
3. Set "Backup Interval" (e.g., 12 hours)
4. Set "Retention Period" (e.g., 14 days)
5. Set "Maximum Backups" (e.g., 60)
6. Click "Save Settings"
7. Automated backups will run on schedule
```

### Setting Up Cloud Storage

```
1. Go to Settings tab
2. Scroll to "Cloud Storage Remotes"
3. Click "Add Remote"
4. Enter remote name (e.g., "my-s3-backup")
5. Select provider (e.g., "Amazon S3")
6. Click "Add Remote"
7. Configure credentials via rclone config (see note below)
```

## API Integration

The frontend integrates with the following backend endpoints:

### Backup Endpoints

```javascript
// List all backups
GET /api/backups

// Create backup
POST /api/backups
Body: { description: "string" }

// Get backup status
GET /api/backups/status

// Restore backup
POST /api/backups/restore
Body: { backup_filename: "string" }

// Delete backup
DELETE /api/backups/{filename}

// Download backup
GET /api/backups/download/{filename}

// Cleanup old backups
POST /api/backups/cleanup
```

### Rclone Endpoints

```javascript
// List remotes
GET /api/v1/storage/rclone/remotes

// Configure remote
POST /api/v1/storage/rclone/configure
Body: { remote_name: "string", provider: "string", config: {} }

// Copy to cloud
POST /api/v1/storage/rclone/copy
Body: { source_path: "string", remote_name: "string", remote_path: "string" }

// Delete remote
DELETE /api/v1/storage/rclone/remote/{name}
```

## Component Props

### BackupDashboard
No props required - standalone component

### BackupManager
No props required - handles all state internally

### BackupSettings
```javascript
<BackupSettings 
  onSave={(settings) => console.log(settings)} 
/>
```

**onSave callback receives:**
```javascript
{
  retentionDays: number,
  maxBackups: number,
  intervalHours: number,
  autoBackupEnabled: boolean
}
```

## Styling and Theming

Uses Material-UI (MUI) components with:
- Responsive grid layout
- Mobile-friendly design
- Dark/light mode support (via MUI theme)
- Consistent color scheme
- Icon integration

### Color Coding

- **Primary (Blue)**: Main actions, active states
- **Success (Green)**: Completed operations, active status
- **Warning (Orange)**: Cleanup operations, caution
- **Error (Red)**: Delete operations, errors
- **Info (Light Blue)**: Information, status indicators

## Notifications

The interface uses Snackbar notifications for:
- ✅ Success messages (green)
- ❌ Error messages (red)
- ⚠️ Warning messages (orange)
- ℹ️ Info messages (blue)

Notifications auto-dismiss after 6 seconds and appear in bottom-right corner.

## Responsive Design

The interface adapts to different screen sizes:

**Desktop (>960px)**
- 4-column status cards
- Full table view with all columns
- Side-by-side layouts

**Tablet (600-960px)**
- 2-column status cards
- Scrollable table
- Stacked layouts

**Mobile (<600px)**
- Single column layout
- Card view for backups
- Collapsible sections
- Touch-friendly buttons

## Installation

### Add to Router

```javascript
// In your main App.js or routes file
import BackupDashboard from './components/BackupDashboard';

// Add route
<Route path="/admin/backups" element={<BackupDashboard />} />
```

### Dependencies

Required npm packages (should already be installed):
```json
{
  "@mui/material": "^5.x",
  "@mui/icons-material": "^5.x",
  "react": "^18.x",
  "date-fns": "^2.x"
}
```

If not installed:
```bash
npm install @mui/material @mui/icons-material date-fns
```

### Import in Navigation

```javascript
// In your navigation menu
import { Backup as BackupIcon } from '@mui/icons-material';

// Add menu item
<MenuItem onClick={() => navigate('/admin/backups')}>
  <ListItemIcon>
    <BackupIcon />
  </ListItemIcon>
  <ListItemText primary="Backups" />
</MenuItem>
```

## Security Considerations

### Authentication

The backup endpoints should be protected with authentication. Ensure:
- User is logged in
- User has admin privileges
- API tokens are valid
- CSRF protection is enabled

### Authorization

Backup operations should only be accessible to:
- System administrators
- Users with backup management role
- Super admin accounts

### Rate Limiting

Consider implementing rate limiting for:
- Backup creation (prevent abuse)
- Restoration operations
- Cloud uploads

## Troubleshooting

### Backups Not Loading

**Issue**: Backup list is empty or shows loading spinner

**Solutions**:
1. Check backend is running
2. Verify API endpoint `/api/backups` is accessible
3. Check browser console for errors
4. Ensure backup directory exists
5. Check file permissions

### Upload to Cloud Fails

**Issue**: Cloud upload shows error

**Solutions**:
1. Verify rclone is installed
2. Check remote configuration
3. Test rclone connectivity manually
4. Verify credentials are correct
5. Check remote path exists

### Restore Operation Fails

**Issue**: Database restore shows error

**Solutions**:
1. Ensure database is accessible
2. Check PostgreSQL is running
3. Verify backup file is not corrupted
4. Ensure sufficient disk space
5. Check database user permissions

### Settings Not Saving

**Issue**: Settings changes don't persist

**Solutions**:
1. Implement backend settings endpoint
2. Save to environment variables
3. Update docker-compose.yml
4. Restart services after changes

## Advanced Usage

### Automating Cloud Backups

You can configure automatic cloud uploads by:
1. Setting up rclone remote
2. Creating a scheduled task to upload backups
3. Using the API to trigger uploads after backup creation

### Monitoring Backup Health

Track backup operations by:
1. Checking status dashboard regularly
2. Setting up alerts for failed backups
3. Monitoring storage usage
4. Reviewing backup logs

### Integration with CI/CD

Trigger backups before deployments:
```bash
# In your deployment script
curl -X POST http://ops-center:3001/api/backups \
  -H "Content-Type: application/json" \
  -d '{"description": "Pre-deployment backup"}'
```

## Future Enhancements

Potential features for future versions:

1. **Backup Verification**: Test restore in sandbox
2. **Encryption**: Encrypt backups at rest
3. **Incremental Backups**: WAL-based incremental backups
4. **Email Notifications**: Alert on backup success/failure
5. **Backup Comparison**: Compare backups to find differences
6. **Point-in-Time Recovery**: More granular restore options
7. **Multi-Database**: Support for multiple databases
8. **Backup Metrics**: Grafana/Prometheus integration
9. **Backup Scheduling**: Cron-like scheduling interface
10. **Backup Policies**: Different policies for different databases

## Support

For issues or questions:
- Check backend logs: `docker logs ops-center | grep -i backup`
- Review API documentation: `DATABASE_BACKUP_GUIDE.md`
- Test CLI: `./backup-database.sh list`
- Check rclone config: `rclone config`

## Screenshots

(Add screenshots of your implementation here)

## License

Same as Ops-Center OSS project
