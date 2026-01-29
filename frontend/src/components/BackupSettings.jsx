import React, { useState, useEffect } from 'react';
import {
  Paper, Typography, Grid, TextField, Button, Box, Alert, CircularProgress,
  FormControl, InputLabel, Select, MenuItem, Divider, Switch, FormControlLabel,
  Card, CardContent, List, ListItem, ListItemText, ListItemIcon, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions, Chip
} from '@mui/material';
import {
  Save as SaveIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  CloudQueue as CloudIcon,
  Check as CheckIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';

export default function BackupSettings({ onSave }) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [rcloneRemotes, setRcloneRemotes] = useState([]);
  const [addRemoteDialog, setAddRemoteDialog] = useState(false);
  
  // Backup settings
  const [retentionDays, setRetentionDays] = useState(7);
  const [maxBackups, setMaxBackups] = useState(30);
  const [intervalHours, setIntervalHours] = useState(24);
  const [autoBackupEnabled, setAutoBackupEnabled] = useState(true);
  
  // Rclone settings
  const [remoteName, setRemoteName] = useState('');
  const [remoteType, setRemoteType] = useState('s3');
  const [remoteConfig, setRemoteConfig] = useState({});

  useEffect(() => {
    fetchBackupStatus();
    fetchRcloneRemotes();
  }, []);

  const fetchBackupStatus = async () => {
    try {
      const response = await fetch('/api/backups/status');
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      setStatus(data);
      setRetentionDays(data.retention_days || 7);
      setMaxBackups(data.max_backups || 30);
      setIntervalHours(data.interval_hours || 24);
      setAutoBackupEnabled(data.enabled || true);
    } catch (error) {
      console.error('Status fetch error:', error);
    }
  };

  const fetchRcloneRemotes = async () => {
    try {
      const response = await fetch('/api/v1/storage/rclone/remotes');
      if (response.ok) {
        const data = await response.json();
        setRcloneRemotes(data.remotes || []);
      }
    } catch (error) {
      console.error('Rclone remotes fetch error:', error);
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      // Here you would save the settings to your backend
      // For now, just notify parent component
      if (onSave) {
        onSave({
          retentionDays,
          maxBackups,
          intervalHours,
          autoBackupEnabled
        });
      }
      alert('Settings saved successfully!');
    } catch (error) {
      alert('Failed to save settings: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const configureRcloneRemote = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/storage/rclone/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          remote_name: remoteName,
          provider: remoteType,
          config: remoteConfig
        })
      });
      
      if (!response.ok) throw new Error('Failed to configure remote');
      
      alert('Remote configured successfully!');
      setAddRemoteDialog(false);
      setRemoteName('');
      setRemoteConfig({});
      fetchRcloneRemotes();
    } catch (error) {
      alert('Configuration failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteRemote = async (remoteName) => {
    if (!window.confirm(`Delete remote ${remoteName}?`)) return;
    
    try {
      const response = await fetch(`/api/v1/storage/rclone/remote/${remoteName}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) throw new Error('Failed to delete remote');
      
      alert('Remote deleted successfully!');
      fetchRcloneRemotes();
    } catch (error) {
      alert('Deletion failed: ' + error.message);
    }
  };

  const cloudProviders = [
    { value: 's3', label: 'Amazon S3' },
    { value: 'drive', label: 'Google Drive' },
    { value: 'dropbox', label: 'Dropbox' },
    { value: 'onedrive', label: 'OneDrive' },
    { value: 'b2', label: 'Backblaze B2' },
    { value: 'azureblob', label: 'Azure Blob Storage' },
    { value: 'gcs', label: 'Google Cloud Storage' },
    { value: 'sftp', label: 'SFTP' },
    { value: 'webdav', label: 'WebDAV' }
  ];

  return (
    <Box>
      {/* Backup Schedule Settings */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Backup Schedule Settings
        </Typography>
        <Divider sx={{ mb: 3 }} />
        
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={autoBackupEnabled}
                  onChange={(e) => setAutoBackupEnabled(e.target.checked)}
                />
              }
              label="Enable Automated Backups"
            />
          </Grid>
          
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Backup Interval (hours)"
              value={intervalHours}
              onChange={(e) => setIntervalHours(parseInt(e.target.value))}
              helperText="Hours between automatic backups"
              disabled={!autoBackupEnabled}
            />
          </Grid>
          
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Retention Period (days)"
              value={retentionDays}
              onChange={(e) => setRetentionDays(parseInt(e.target.value))}
              helperText="Days to keep backups"
            />
          </Grid>
          
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Maximum Backups"
              value={maxBackups}
              onChange={(e) => setMaxBackups(parseInt(e.target.value))}
              helperText="Maximum number of backups to keep"
            />
          </Grid>

          <Grid item xs={12}>
            <Alert severity="info">
              Current Status: <strong>{status?.total_backups || 0}</strong> backups using approximately{' '}
              <strong>{status?.backup_directory || '/app/backups/database'}</strong>
            </Alert>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={saveSettings}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Save Settings'}
          </Button>
        </Box>
      </Paper>

      {/* Cloud Storage Configuration */}
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Cloud Storage Remotes
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => setAddRemoteDialog(true)}
          >
            Add Remote
          </Button>
        </Box>
        <Divider sx={{ mb: 2 }} />

        {rcloneRemotes.length === 0 ? (
          <Alert severity="info">
            No cloud remotes configured. Add a remote to enable automatic cloud backups.
          </Alert>
        ) : (
          <Grid container spacing={2}>
            {rcloneRemotes.map((remote) => (
              <Grid item xs={12} md={6} key={remote.name}>
                <Card variant="outlined">
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="subtitle1" gutterBottom>
                          {remote.name}
                        </Typography>
                        <Chip
                          label={remote.type}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                        {remote.configured && (
                          <Chip
                            label="Configured"
                            size="small"
                            color="success"
                            variant="outlined"
                            sx={{ ml: 1 }}
                            icon={<CheckIcon />}
                          />
                        )}
                      </Box>
                      <IconButton
                        color="error"
                        onClick={() => deleteRemote(remote.name)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Paper>

      {/* Add Remote Dialog */}
      <Dialog
        open={addRemoteDialog}
        onClose={() => setAddRemoteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Cloud Storage Remote</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Remote Name"
            fullWidth
            value={remoteName}
            onChange={(e) => setRemoteName(e.target.value)}
            placeholder="my-s3-backup"
            sx={{ mb: 2, mt: 1 }}
          />
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Provider</InputLabel>
            <Select
              value={remoteType}
              label="Provider"
              onChange={(e) => setRemoteType(e.target.value)}
            >
              {cloudProviders.map((provider) => (
                <MenuItem key={provider.value} value={provider.value}>
                  {provider.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Alert severity="info">
            <Typography variant="body2">
              After creating the remote, you'll need to configure credentials via the rclone config.
              Use: <code>rclone config</code> in the terminal.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddRemoteDialog(false)}>Cancel</Button>
          <Button
            onClick={configureRcloneRemote}
            variant="contained"
            disabled={!remoteName || loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Add Remote'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
