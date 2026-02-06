/**
 * Edge Device Management Dashboard
 * Epic 7.1: Edge Device Management
 * 
 * Comprehensive dashboard for managing edge devices including:
 * - Device listing with status monitoring
 * - Device detail view with metrics and logs
 * - Configuration management
 * - Registration token generation
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Settings as SettingsIcon,
  Computer as ComputerIcon,
  CloudQueue as CloudIcon,
  CheckCircle as OnlineIcon,
  Cancel as OfflineIcon,
  Error as ErrorIcon,
  Build as MaintenanceIcon,
  ContentCopy as CopyIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';

const EdgeDeviceManagement = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [statistics, setStatistics] = useState({});
  const [filters, setFilters] = useState({
    status: '',
    device_type: '',
    search: '',
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Dialog states
  const [generateTokenDialog, setGenerateTokenDialog] = useState(false);
  const [deviceDetailDialog, setDeviceDetailDialog] = useState(false);
  const [configDialog, setConfigDialog] = useState(false);
  
  // Form states
  const [newDevice, setNewDevice] = useState({
    device_name: '',
    device_type: 'uc1-pro',
    organization_id: '',
  });
  const [generatedToken, setGeneratedToken] = useState(null);
  const [configData, setConfigData] = useState('');
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    fetchDevices();
    fetchStatistics();
    
    // Refresh devices every 30 seconds
    const interval = setInterval(fetchDevices, 30000);
    return () => clearInterval(interval);
  }, [filters, page]);

  const fetchDevices = async () => {
    try {
      const queryParams = new URLSearchParams({
        page,
        page_size: 20,
        ...(filters.status && { status: filters.status }),
        ...(filters.device_type && { device_type: filters.device_type }),
        ...(filters.search && { search: filters.search }),
      });

      const response = await fetch(`/api/v1/admin/edge/devices?${queryParams}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setDevices(data.devices || []);
        setTotalPages(data.pagination?.total_pages || 1);
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await fetch('/api/v1/admin/edge/statistics', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setStatistics(data);
      }
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };

  const handleGenerateToken = async () => {
    try {
      const response = await fetch('/api/v1/admin/edge/devices/generate-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newDevice),
      });

      if (response.ok) {
        const data = await response.json();
        setGeneratedToken(data);
        fetchDevices();
      } else {
        alert('Failed to generate token');
      }
    } catch (error) {
      console.error('Failed to generate token:', error);
      alert('Error generating token');
    }
  };

  const fetchDeviceDetail = async (deviceId) => {
    try {
      const response = await fetch(`/api/v1/admin/edge/devices/${deviceId}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setSelectedDevice(data);
        setDeviceDetailDialog(true);
      }
    } catch (error) {
      console.error('Failed to fetch device detail:', error);
    }
  };

  const handlePushConfig = async () => {
    if (!selectedDevice) return;

    try {
      const response = await fetch(`/api/v1/admin/edge/devices/${selectedDevice.id}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          config_data: JSON.parse(configData),
          apply_immediately: true,
        }),
      });

      if (response.ok) {
        alert('Configuration pushed successfully');
        setConfigDialog(false);
        fetchDeviceDetail(selectedDevice.id);
      } else {
        alert('Failed to push configuration');
      }
    } catch (error) {
      console.error('Failed to push config:', error);
      alert('Error pushing configuration');
    }
  };

  const handleDeleteDevice = async (deviceId) => {
    if (!window.confirm('Are you sure you want to delete this device?')) return;

    try {
      const response = await fetch(`/api/v1/admin/edge/devices/${deviceId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (response.ok) {
        fetchDevices();
        setDeviceDetailDialog(false);
      } else {
        alert('Failed to delete device');
      }
    } catch (error) {
      console.error('Failed to delete device:', error);
      alert('Error deleting device');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
        return <OnlineIcon color="success" />;
      case 'offline':
        return <OfflineIcon color="error" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'maintenance':
        return <MaintenanceIcon color="warning" />;
      default:
        return <ComputerIcon />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
        return 'error';
      case 'error':
        return 'error';
      case 'maintenance':
        return 'warning';
      default:
        return 'default';
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = (now - date) / 1000; // seconds

    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const formatUptime = (seconds) => {
    if (!seconds) return 'Unknown';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            <ComputerIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Edge Device Management
          </Typography>
          <Typography variant="body2" className="text-gray-300">
            Manage and monitor distributed edge computing devices
          </Typography>
        </Box>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchDevices}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setGenerateTokenDialog(true)}
          >
            Add Device
          </Button>
        </Box>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Devices
              </Typography>
              <Typography variant="h4">
                {statistics.total_devices || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Online
              </Typography>
              <Typography variant="h4" color="success.main">
                {statistics.online || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Offline
              </Typography>
              <Typography variant="h4" color="error.main">
                {statistics.offline || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Health Score
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="h4">
                  {Math.round(statistics.health_percentage || 0)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={statistics.health_percentage || 0}
                  sx={{ ml: 2, flex: 1, height: 8, borderRadius: 4 }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Search"
                placeholder="Search devices..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.status}
                  label="Status"
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  sx={{ minWidth: 150 }}
                  MenuProps={{
                    PaperProps: {
                      sx: { minWidth: 150 }
                    }
                  }}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="online">Online</MenuItem>
                  <MenuItem value="offline">Offline</MenuItem>
                  <MenuItem value="error">Error</MenuItem>
                  <MenuItem value="maintenance">Maintenance</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Device Type</InputLabel>
                <Select
                  value={filters.device_type}
                  label="Device Type"
                  onChange={(e) => setFilters({ ...filters, device_type: e.target.value })}
                  sx={{ minWidth: 150 }}
                  MenuProps={{
                    PaperProps: {
                      sx: { minWidth: 150 }
                    }
                  }}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="uc1-pro">UC-1 Pro</MenuItem>
                  <MenuItem value="gateway">Gateway</MenuItem>
                  <MenuItem value="custom">Custom</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Device List */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Device Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Last Seen</TableCell>
                <TableCell>Uptime</TableCell>
                <TableCell>Firmware</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : devices.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    No devices found. Click "Add Device" to get started.
                  </TableCell>
                </TableRow>
              ) : (
                devices.map((device) => (
                  <TableRow key={device.id} hover>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(device.status)}
                        label={device.status}
                        color={getStatusColor(device.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {device.device_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {device.device_id}
                      </Typography>
                    </TableCell>
                    <TableCell>{device.device_type}</TableCell>
                    <TableCell>{device.ip_address || 'N/A'}</TableCell>
                    <TableCell>
                      <Tooltip title={device.last_seen || 'Never'}>
                        <span>{formatTimestamp(device.last_seen)}</span>
                      </Tooltip>
                    </TableCell>
                    <TableCell>{formatUptime(device.uptime)}</TableCell>
                    <TableCell>{device.firmware_version || 'Unknown'}</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => fetchDeviceDetail(device.id)}
                        title="View Details"
                      >
                        <ViewIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedDevice(device);
                          setConfigDialog(true);
                        }}
                        title="Push Config"
                      >
                        <SettingsIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteDevice(device.id)}
                        title="Delete"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Generate Token Dialog */}
      <Dialog
        open={generateTokenDialog}
        onClose={() => {
          setGenerateTokenDialog(false);
          setGeneratedToken(null);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add New Edge Device</DialogTitle>
        <DialogContent>
          {!generatedToken ? (
            <Box sx={{ pt: 2 }}>
              <TextField
                fullWidth
                label="Device Name"
                value={newDevice.device_name}
                onChange={(e) => setNewDevice({ ...newDevice, device_name: e.target.value })}
                sx={{ mb: 2 }}
              />
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Device Type</InputLabel>
                <Select
                  value={newDevice.device_type}
                  label="Device Type"
                  onChange={(e) => setNewDevice({ ...newDevice, device_type: e.target.value })}
                >
                  <MenuItem value="uc1-pro">UC-1 Pro</MenuItem>
                  <MenuItem value="gateway">Gateway</MenuItem>
                  <MenuItem value="custom">Custom</MenuItem>
                </Select>
              </FormControl>
              <Alert severity="info">
                A registration token will be generated that you can use to install the edge agent on your device.
              </Alert>
            </Box>
          ) : (
            <Box sx={{ pt: 2 }}>
              <Alert severity="success" sx={{ mb: 2 }}>
                Registration token generated successfully!
              </Alert>
              
              <Typography variant="subtitle2" gutterBottom>
                Registration Token:
              </Typography>
              <Box sx={{ display: 'flex', mb: 2 }}>
                <TextField
                  fullWidth
                  value={generatedToken.registration_token}
                  InputProps={{ readOnly: true }}
                  size="small"
                />
                <IconButton onClick={() => copyToClipboard(generatedToken.registration_token)}>
                  <CopyIcon />
                </IconButton>
              </Box>

              <Typography variant="subtitle2" gutterBottom>
                Installation Command:
              </Typography>
              <Box sx={{ display: 'flex', mb: 2 }}>
                <TextField
                  fullWidth
                  value={generatedToken.installation_command}
                  InputProps={{ readOnly: true }}
                  size="small"
                  multiline
                  rows={2}
                />
                <IconButton onClick={() => copyToClipboard(generatedToken.installation_command)}>
                  <CopyIcon />
                </IconButton>
              </Box>

              <Typography variant="caption" color="text.secondary">
                Token expires: {new Date(generatedToken.expires_at).toLocaleString()}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setGenerateTokenDialog(false);
            setGeneratedToken(null);
          }}>
            {generatedToken ? 'Close' : 'Cancel'}
          </Button>
          {!generatedToken && (
            <Button variant="contained" onClick={handleGenerateToken}>
              Generate Token
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Device Detail Dialog */}
      <Dialog
        open={deviceDetailDialog}
        onClose={() => setDeviceDetailDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Device Details: {selectedDevice?.device_name}
        </DialogTitle>
        <DialogContent>
          {selectedDevice && (
            <Box>
              <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
                <Tab label="Overview" />
                <Tab label="Metrics" />
                <Tab label="Configuration" />
                <Tab label="Logs" />
              </Tabs>

              {activeTab === 0 && (
                <Box sx={{ pt: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Device ID
                      </Typography>
                      <Typography variant="body2">{selectedDevice.device_id}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Status
                      </Typography>
                      <Typography variant="body2">
                        <Chip
                          label={selectedDevice.status}
                          color={getStatusColor(selectedDevice.status)}
                          size="small"
                        />
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        IP Address
                      </Typography>
                      <Typography variant="body2">{selectedDevice.ip_address || 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Last Seen
                      </Typography>
                      <Typography variant="body2">
                        {formatTimestamp(selectedDevice.last_seen)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Firmware Version
                      </Typography>
                      <Typography variant="body2">
                        {selectedDevice.firmware_version || 'Unknown'}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Uptime
                      </Typography>
                      <Typography variant="body2">
                        {formatUptime(selectedDevice.metadata?.uptime)}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {activeTab === 1 && (
                <Box sx={{ pt: 2 }}>
                  {selectedDevice.recent_metrics?.length > 0 ? (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Type</TableCell>
                            <TableCell>Value</TableCell>
                            <TableCell>Timestamp</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {selectedDevice.recent_metrics.map((metric, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{metric.type}</TableCell>
                              <TableCell>
                                <pre style={{ margin: 0, fontSize: '0.75rem' }}>
                                  {JSON.stringify(metric.value, null, 2)}
                                </pre>
                              </TableCell>
                              <TableCell>{formatTimestamp(metric.timestamp)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  ) : (
                    <Alert severity="info">No metrics available yet</Alert>
                  )}
                </Box>
              )}

              {activeTab === 2 && (
                <Box sx={{ pt: 2 }}>
                  {selectedDevice.current_config ? (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Version: {selectedDevice.current_config.version}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                        Applied: {formatTimestamp(selectedDevice.current_config.applied_at)}
                      </Typography>
                      <TextField
                        fullWidth
                        multiline
                        rows={12}
                        value={JSON.stringify(selectedDevice.current_config.data, null, 2)}
                        InputProps={{ readOnly: true }}
                        sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
                      />
                    </Box>
                  ) : (
                    <Alert severity="info">No configuration set</Alert>
                  )}
                </Box>
              )}

              {activeTab === 3 && (
                <Box sx={{ pt: 2 }}>
                  <Alert severity="info">Log viewer coming soon...</Alert>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeviceDetailDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Push Config Dialog */}
      <Dialog
        open={configDialog}
        onClose={() => setConfigDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Push Configuration</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              Enter configuration as JSON. The device will apply it on next heartbeat.
            </Alert>
            <TextField
              fullWidth
              multiline
              rows={15}
              label="Configuration (JSON)"
              value={configData}
              onChange={(e) => setConfigData(e.target.value)}
              placeholder={`{
  "vllm": {
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "gpu_memory_util": 0.90
  },
  "services": {
    "open-webui": true,
    "center-deep": false
  }
}`}
              sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handlePushConfig}>
            Push Configuration
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default EdgeDeviceManagement;
