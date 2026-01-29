# Backup Frontend - Quick Reference

## Components

### BackupDashboard.js
Main entry point with tabs for Backups and Settings

### BackupManager.js
Full backup management UI:
- Create backups
- List/view backups
- Restore database
- Upload to cloud
- Delete backups

### BackupSettings.js
Configuration interface:
- Schedule settings
- Retention policy
- Cloud remotes
- Enable/disable automation

## Quick Setup

### 1. Add to Router
```javascript
import BackupDashboard from './components/BackupDashboard';

<Route path="/admin/backups" element={<BackupDashboard />} />
```

### 2. Add to Navigation
```javascript
import { Backup as BackupIcon } from '@mui/icons-material';

<MenuItem onClick={() => navigate('/admin/backups')}>
  <BackupIcon /> Backups
</MenuItem>
```

### 3. Install Dependencies
```bash
npm install @mui/material @mui/icons-material date-fns
# or
./install-backup-frontend.sh
```

## Features at a Glance

### Status Dashboard
- 📊 Total backups count
- ⏱️ Retention period
- 🔄 Backup interval
- ✅ Service status

### Operations
- ➕ Create manual backup
- 📥 Download backup file
- ♻️ Restore from backup
- ☁️ Upload to cloud
- 🗑️ Delete backup
- 🧹 Cleanup old backups

### Cloud Integration
- 🌐 40+ cloud providers via rclone
- ☁️ S3, Google Drive, Dropbox, OneDrive, etc.
- 🔧 Easy remote configuration
- 📤 One-click upload to cloud

### Settings
- ⏰ Configure backup schedule
- 📅 Set retention policies
- 🌍 Manage cloud remotes
- 🔀 Toggle automation

## API Endpoints

```
GET    /api/backups              - List backups
POST   /api/backups              - Create backup
GET    /api/backups/status       - Get status
POST   /api/backups/restore      - Restore backup
DELETE /api/backups/{filename}   - Delete backup
GET    /api/backups/download/{filename} - Download
POST   /api/backups/cleanup      - Cleanup old
```

## Common Tasks

### Create Backup
```
1. Click "Create Backup"
2. Add description (optional)
3. Click "Create Backup"
4. Wait for completion
```

### Restore Database
```
1. Find backup in list
2. Click restore icon
3. Review details
4. Confirm (⚠️ OVERWRITES DATA!)
5. Wait for completion
```

### Upload to Cloud
```
1. Configure remote (Settings tab)
2. Click cloud icon on backup
3. Select remote & path
4. Click "Upload"
```

### Configure Schedule
```
1. Go to Settings tab
2. Set interval (hours)
3. Set retention (days)
4. Set max backups
5. Click "Save Settings"
```

## File Locations

- **Components**: `frontend/src/components/Backup*.js`
- **Guide**: `BACKUP_FRONTEND_GUIDE.md`
- **Quick Ref**: `BACKUP_FRONTEND_QUICK_REF.md`
- **Install Script**: `install-backup-frontend.sh`

## Styling

Material-UI (MUI) with:
- Responsive grid layout
- Mobile-friendly design
- Dark/light mode support
- Icon integration

## Dependencies

```json
{
  "@mui/material": "^5.x",
  "@mui/icons-material": "^5.x",
  "react": "^18.x",
  "date-fns": "^2.x"
}
```

## Security

- 🔒 Requires authentication
- 👤 Admin-only access recommended
- 🛡️ CSRF protection
- ⚠️ Restore requires confirmation

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backups not loading | Check backend API at `/api/backups` |
| Upload fails | Verify rclone remote config |
| Restore fails | Check database accessibility |
| Settings not saving | Implement backend settings endpoint |

## Support

- 📖 Full guide: `BACKUP_FRONTEND_GUIDE.md`
- 🔧 Backend guide: `DATABASE_BACKUP_GUIDE.md`
- 💻 CLI: `./backup-database.sh --help`
- 📝 API docs: Backend `/api/backups` endpoints
