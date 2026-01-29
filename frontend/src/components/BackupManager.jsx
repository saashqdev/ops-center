import React, { useState, useEffect } from 'react';
import {
  Container, Paper, Tabs, Tab, Box, Typography, Grid, Card, CardContent,
  CardActions, Button, IconButton, Chip, LinearProgress, Alert, Snackbar,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, Select,
  MenuItem, FormControl, InputLabel, List, ListItem, ListItemText,
  ListItemSecondaryAction, Tooltip, Divider, CircularProgress, Switch,
  FormControlLabel, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, TablePagination
} from '@mui/material';
import {
  Backup as BackupIcon,
  CloudUpload as CloudUploadIcon,
  Restore as RestoreIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Schedule as ScheduleIcon,
  Storage as StorageIcon,
  CloudQueue as CloudQueueIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { format } from 'date-fns';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function BackupManager() {
  const [tabValue, setTabValue] = useState(0);
  const [backups, setBackups] = useState([]);
  const [backupStatus, setBackupStatus] = useState(null);
  const [rcloneRemotes, setRcloneRemotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  
  // Dialog states
  const [createBackupDialog, setCreateBackupDialog] = useState(false);
  const [restoreDialog, setRestoreDialog] = useState(false);
  const [rcloneDialog, setRcloneDialog] = useState(false);
  const [scheduleDialog, setScheduleDialog] = useState(false);
  
  // Form states
  const [backupDescription, setBackupDescription] = useState('');
  const [selectedBackup, setSelectedBackup] = useState(null);
  const [rcloneRemote, setRcloneRemote] = useState('');
  const [rclonePath, setRclonePath] = useState('');
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    fetchBackups();
    fetchBackupStatus();
    fetchRcloneRemotes();
  }, []);

  const fetchBackups = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/backups/');
      if (!response.ok) throw new Error('Failed to fetch backups');
      const data = await response.json();
      setBackups(data);
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchBackupStatus = async () => {
    try {
      const response = await fetch('/api/backups/status/');
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      setBackupStatus(data);
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

  const createBackup = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/backups/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: backupDescription })
      });
      
      if (!response.ok) throw new Error('Backup creation failed');
      
      const data = await response.json();
      showSnackbar('Backup created successfully!', 'success');
      setCreateBackupDialog(false);
      setBackupDescription('');
      fetchBackups();
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const deleteBackup = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete ${filename}?`)) return;
    
    try {
      setLoading(true);
      const response = await fetch(`/api/backups/${filename}/`, {
        method: 'DELETE'
      });
      
      if (!response.ok) throw new Error('Backup deletion failed');
      
      showSnackbar('Backup deleted successfully!', 'success');
      fetchBackups();
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const restoreBackup = async () => {
    if (!selectedBackup) return;
    
    try {
      setLoading(true);
      const response = await fetch('/api/backups/restore/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backup_filename: selectedBackup.filename })
      });
      
      if (!response.ok) throw new Error('Backup restoration failed');
      
      showSnackbar('Database restored successfully!', 'success');
      setRestoreDialog(false);
      setSelectedBackup(null);
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const uploadToCloud = async (backup) => {
    if (!rcloneRemote) {
      showSnackbar('Please select a cloud remote', 'warning');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/storage/rclone/copy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: `/app/backups/database/${backup.filename}`,
          remote_name: rcloneRemote,
          remote_path: rclonePath || 'backups/'
        })
      });
      
      if (!response.ok) throw new Error('Cloud upload failed');
      
      showSnackbar('Backup uploaded to cloud successfully!', 'success');
      setRcloneDialog(false);
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const cleanupOldBackups = async () => {
    if (!window.confirm('This will remove backups older than the retention period. Continue?')) return;
    
    try {
      setLoading(true);
      const response = await fetch('/api/backups/cleanup/', {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Cleanup failed');
      
      showSnackbar('Old backups cleaned up successfully!', 'success');
      fetchBackups();
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateString;
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Database Backup Management
      </Typography>

      {/* Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Backups
                  </Typography>
                  <Typography variant="h4">
                    {backupStatus?.total_backups || 0}
                  </Typography>
                </Box>
                <BackupIcon sx={{ fontSize: 40, color: 'primary.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Retention Period
                  </Typography>
                  <Typography variant="h5">
                    {backupStatus?.retention_days || 0} days
                  </Typography>
                </Box>
                <ScheduleIcon sx={{ fontSize: 40, color: 'warning.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Backup Interval
                  </Typography>
                  <Typography variant="h5">
                    {backupStatus?.interval_hours || 0}h
                  </Typography>
                </Box>
                <RefreshIcon sx={{ fontSize: 40, color: 'info.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Status
                  </Typography>
                  <Chip
                    label={backupStatus?.enabled ? 'Active' : 'Disabled'}
                    color={backupStatus?.enabled ? 'success' : 'default'}
                    size="small"
                  />
                </Box>
                {backupStatus?.enabled ? (
                  <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main', opacity: 0.3 }} />
                ) : (
                  <ErrorIcon sx={{ fontSize: 40, color: 'error.main', opacity: 0.3 }} />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Actions */}
      <Paper sx={{ mb: 3, p: 2 }}>
        <Grid container spacing={2}>
          <Grid item>
            <Button
              variant="contained"
              startIcon={<BackupIcon />}
              onClick={() => setCreateBackupDialog(true)}
              disabled={loading}
            >
              Create Backup
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchBackups}
              disabled={loading}
            >
              Refresh
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="outlined"
              startIcon={<DeleteIcon />}
              onClick={cleanupOldBackups}
              disabled={loading}
              color="warning"
            >
              Cleanup Old Backups
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Backups Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Filename</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Description</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && backups.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : backups.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <Typography color="textSecondary">No backups found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                backups
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((backup) => (
                    <TableRow key={backup.filename} hover>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {backup.filename}
                        </Typography>
                      </TableCell>
                      <TableCell>{formatBytes(backup.size_bytes || backup.size_mb * 1024 * 1024)}</TableCell>
                      <TableCell>{formatDate(backup.created_at)}</TableCell>
                      <TableCell>
                        <Typography variant="body2" color="textSecondary">
                          {backup.description || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Restore">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => {
                              setSelectedBackup(backup);
                              setRestoreDialog(true);
                            }}
                          >
                            <RestoreIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Upload to Cloud">
                          <IconButton
                            size="small"
                            color="info"
                            onClick={() => {
                              setSelectedBackup(backup);
                              setRcloneDialog(true);
                            }}
                          >
                            <CloudUploadIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => deleteBackup(backup.filename)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={backups.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      {/* Create Backup Dialog */}
      <Dialog open={createBackupDialog} onClose={() => setCreateBackupDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Backup</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Description (optional)"
            type="text"
            fullWidth
            variant="outlined"
            value={backupDescription}
            onChange={(e) => setBackupDescription(e.target.value)}
            placeholder="e.g., Before major update"
            sx={{ mt: 2 }}
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            This will create a compressed PostgreSQL dump of your database.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateBackupDialog(false)}>Cancel</Button>
          <Button onClick={createBackup} variant="contained" disabled={loading}>
            {loading ? <CircularProgress size={24} /> : 'Create Backup'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Restore Dialog */}
      <Dialog open={restoreDialog} onClose={() => setRestoreDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Restore Database</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mt: 2, mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              <strong>WARNING:</strong> This will restore your database from the selected backup.
            </Typography>
            <Typography variant="body2">
              All current data will be replaced with the backup data.
            </Typography>
          </Alert>
          {selectedBackup && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>Backup Details:</Typography>
              <Typography variant="body2" color="textSecondary">
                Filename: {selectedBackup.filename}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Created: {formatDate(selectedBackup.created_at)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Size: {formatBytes(selectedBackup.size_bytes || selectedBackup.size_mb * 1024 * 1024)}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestoreDialog(false)}>Cancel</Button>
          <Button onClick={restoreBackup} variant="contained" color="error" disabled={loading}>
            {loading ? <CircularProgress size={24} /> : 'Restore Database'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rclone Upload Dialog */}
      <Dialog open={rcloneDialog} onClose={() => setRcloneDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload to Cloud Storage</DialogTitle>
        <DialogContent>
          {selectedBackup && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Uploading: {selectedBackup.filename}
              </Typography>
            </Box>
          )}
          <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
            <InputLabel>Cloud Remote</InputLabel>
            <Select
              value={rcloneRemote}
              label="Cloud Remote"
              onChange={(e) => setRcloneRemote(e.target.value)}
            >
              {rcloneRemotes.map((remote) => (
                <MenuItem key={remote.name} value={remote.name}>
                  {remote.name} ({remote.type})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Remote Path"
            value={rclonePath}
            onChange={(e) => setRclonePath(e.target.value)}
            placeholder="backups/"
            helperText="Path on remote storage (e.g., backups/)"
          />
          {rcloneRemotes.length === 0 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              No cloud remotes configured. Configure rclone remotes first.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRcloneDialog(false)}>Cancel</Button>
          <Button
            onClick={() => uploadToCloud(selectedBackup)}
            variant="contained"
            disabled={loading || !rcloneRemote}
          >
            {loading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}
