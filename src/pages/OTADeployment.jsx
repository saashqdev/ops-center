import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Alert,
  Tabs,
  Tab,
  Stepper,
  Step,
  StepLabel,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormLabel,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as StartIcon,
  Pause as PauseIcon,
  Stop as CancelIcon,
  Refresh as RefreshIcon,
  GetApp as DownloadIcon,
  CloudUpload as UploadIcon,
  Visibility as ViewIcon,
  Undo as RollbackIcon,
} from '@mui/icons-material';
import axios from 'axios';

const OTADeployment = () => {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Create deployment wizard state
  const [activeStep, setActiveStep] = useState(0);
  const [deploymentForm, setDeploymentForm] = useState({
    deployment_name: '',
    target_version: '',
    rollout_strategy: 'manual',
    rollout_percentage: 100,
    device_filters: {
      device_type: '',
      current_version: '',
      version_operator: '!=',
      status: 'online',
    },
    update_package_url: '',
    checksum: '',
    release_notes: '',
  });

  const steps = ['Basic Info', 'Target Devices', 'Update Package', 'Review'];

  useEffect(() => {
    fetchDeployments();
  }, [page, statusFilter]);

  const fetchDeployments = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: 20,
      };
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      const response = await axios.get('/api/v1/admin/ota/deployments', { params });
      setDeployments(response.data.deployments);
      setTotalPages(response.data.pagination.total_pages);
    } catch (error) {
      console.error('Failed to fetch deployments:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDeploymentDetails = async (deploymentId) => {
    try {
      const response = await axios.get(`/api/v1/admin/ota/deployments/${deploymentId}`);
      setSelectedDeployment(response.data);
      setDetailsDialogOpen(true);
    } catch (error) {
      console.error('Failed to fetch deployment details:', error);
    }
  };

  const handleCreateDeployment = async () => {
    try {
      const response = await axios.post('/api/v1/admin/ota/deployments', deploymentForm);
      
      setCreateDialogOpen(false);
      resetForm();
      fetchDeployments();
      
      // Show success message
      alert(`Deployment created successfully: ${response.data.deployment_name}`);
    } catch (error) {
      console.error('Failed to create deployment:', error);
      alert('Failed to create deployment: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeploymentAction = async (deploymentId, action) => {
    try {
      await axios.post(`/api/v1/admin/ota/deployments/${deploymentId}/${action}`);
      fetchDeployments();
      
      if (selectedDeployment && selectedDeployment.deployment_id === deploymentId) {
        fetchDeploymentDetails(deploymentId);
      }
    } catch (error) {
      console.error(`Failed to ${action} deployment:`, error);
      alert(`Failed to ${action} deployment: ` + (error.response?.data?.detail || error.message));
    }
  };

  const handleRollbackDevice = async (deploymentId, deviceId, previousVersion) => {
    if (!window.confirm(`Are you sure you want to rollback this device to ${previousVersion}?`)) {
      return;
    }

    try {
      await axios.post(
        `/api/v1/admin/ota/deployments/${deploymentId}/devices/${deviceId}/rollback`,
        { previous_version: previousVersion }
      );
      
      fetchDeploymentDetails(deploymentId);
      alert('Device rollback initiated');
    } catch (error) {
      console.error('Failed to rollback device:', error);
      alert('Failed to rollback device: ' + (error.response?.data?.detail || error.message));
    }
  };

  const resetForm = () => {
    setDeploymentForm({
      deployment_name: '',
      target_version: '',
      rollout_strategy: 'manual',
      rollout_percentage: 100,
      device_filters: {
        device_type: '',
        current_version: '',
        version_operator: '!=',
        status: 'online',
      },
      update_package_url: '',
      checksum: '',
      release_notes: '',
    });
    setActiveStep(0);
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'default',
      in_progress: 'info',
      completed: 'success',
      failed: 'error',
      paused: 'warning',
      cancelled: 'default',
    };
    return colors[status] || 'default';
  };

  const getDeviceStatusColor = (status) => {
    const colors = {
      pending: 'default',
      downloading: 'info',
      installing: 'info',
      verifying: 'info',
      completed: 'success',
      failed: 'error',
      skipped: 'default',
      rolled_back: 'warning',
    };
    return colors[status] || 'default';
  };

  const renderBasicInfoStep = () => (
    <Box>
      <TextField
        fullWidth
        label="Deployment Name"
        value={deploymentForm.deployment_name}
        onChange={(e) => setDeploymentForm({ ...deploymentForm, deployment_name: e.target.value })}
        margin="normal"
        required
      />
      
      <TextField
        fullWidth
        label="Target Version"
        value={deploymentForm.target_version}
        onChange={(e) => setDeploymentForm({ ...deploymentForm, target_version: e.target.value })}
        margin="normal"
        required
        helperText="Version to deploy (e.g., v2.1.0)"
      />
      
      <FormControl fullWidth margin="normal">
        <InputLabel>Rollout Strategy</InputLabel>
        <Select
          value={deploymentForm.rollout_strategy}
          onChange={(e) => setDeploymentForm({ ...deploymentForm, rollout_strategy: e.target.value })}
          label="Rollout Strategy"
        >
          <MenuItem value="manual">Manual - Admin selects devices</MenuItem>
          <MenuItem value="immediate">Immediate - All devices at once</MenuItem>
          <MenuItem value="canary">Canary - Gradual rollout by percentage</MenuItem>
          <MenuItem value="rolling">Rolling - Batch deployment</MenuItem>
        </Select>
      </FormControl>
      
      {deploymentForm.rollout_strategy === 'canary' && (
        <TextField
          fullWidth
          type="number"
          label="Canary Percentage"
          value={deploymentForm.rollout_percentage}
          onChange={(e) => setDeploymentForm({ ...deploymentForm, rollout_percentage: parseInt(e.target.value) })}
          margin="normal"
          inputProps={{ min: 1, max: 100 }}
          helperText="Percentage of devices for initial canary deployment"
        />
      )}
    </Box>
  );

  const renderTargetDevicesStep = () => (
    <Box>
      <Typography variant="h6" gutterBottom>Device Selection Filters</Typography>
      
      <TextField
        fullWidth
        label="Device Type (optional)"
        value={deploymentForm.device_filters.device_type}
        onChange={(e) => setDeploymentForm({
          ...deploymentForm,
          device_filters: { ...deploymentForm.device_filters, device_type: e.target.value }
        })}
        margin="normal"
        helperText="Filter by device type (e.g., raspberry_pi, nvidia_jetson)"
      />
      
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <FormControl fullWidth margin="normal">
            <InputLabel>Version Operator</InputLabel>
            <Select
              value={deploymentForm.device_filters.version_operator}
              onChange={(e) => setDeploymentForm({
                ...deploymentForm,
                device_filters: { ...deploymentForm.device_filters, version_operator: e.target.value }
              })}
              label="Version Operator"
            >
              <MenuItem value="<">Less than</MenuItem>
              <MenuItem value="<=">Less than or equal</MenuItem>
              <MenuItem value="!=">Not equal</MenuItem>
              <MenuItem value="=">Equal</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={8}>
          <TextField
            fullWidth
            label="Current Version (optional)"
            value={deploymentForm.device_filters.current_version}
            onChange={(e) => setDeploymentForm({
              ...deploymentForm,
              device_filters: { ...deploymentForm.device_filters, current_version: e.target.value }
            })}
            margin="normal"
            helperText="Filter by current version"
          />
        </Grid>
      </Grid>
      
      <FormControl fullWidth margin="normal">
        <InputLabel>Device Status</InputLabel>
        <Select
          value={deploymentForm.device_filters.status}
          onChange={(e) => setDeploymentForm({
            ...deploymentForm,
            device_filters: { ...deploymentForm.device_filters, status: e.target.value }
          })}
          label="Device Status"
        >
          <MenuItem value="">All devices</MenuItem>
          <MenuItem value="online">Online only</MenuItem>
          <MenuItem value="offline">Offline only</MenuItem>
        </Select>
      </FormControl>
    </Box>
  );

  const renderUpdatePackageStep = () => (
    <Box>
      <TextField
        fullWidth
        label="Update Package URL"
        value={deploymentForm.update_package_url}
        onChange={(e) => setDeploymentForm({ ...deploymentForm, update_package_url: e.target.value })}
        margin="normal"
        required
        helperText="HTTP(S) URL to download the update package (.tar.gz)"
      />
      
      <TextField
        fullWidth
        label="SHA256 Checksum"
        value={deploymentForm.checksum}
        onChange={(e) => setDeploymentForm({ ...deploymentForm, checksum: e.target.value })}
        margin="normal"
        helperText="SHA256 hash for package verification (optional but recommended)"
      />
      
      <TextField
        fullWidth
        label="Release Notes"
        value={deploymentForm.release_notes}
        onChange={(e) => setDeploymentForm({ ...deploymentForm, release_notes: e.target.value })}
        margin="normal"
        multiline
        rows={4}
        helperText="Release notes for this update"
      />
    </Box>
  );

  const renderReviewStep = () => (
    <Box>
      <Typography variant="h6" gutterBottom>Review Deployment</Typography>
      
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary">Deployment Name</Typography>
          <Typography variant="body1" gutterBottom>{deploymentForm.deployment_name}</Typography>
          
          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Target Version</Typography>
          <Typography variant="body1" gutterBottom>{deploymentForm.target_version}</Typography>
          
          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Rollout Strategy</Typography>
          <Typography variant="body1" gutterBottom>
            {deploymentForm.rollout_strategy}
            {deploymentForm.rollout_strategy === 'canary' && ` (${deploymentForm.rollout_percentage}%)`}
          </Typography>
          
          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Device Filters</Typography>
          <Box>
            {deploymentForm.device_filters.device_type && (
              <Chip label={`Type: ${deploymentForm.device_filters.device_type}`} size="small" sx={{ mr: 1 }} />
            )}
            {deploymentForm.device_filters.current_version && (
              <Chip 
                label={`Version ${deploymentForm.device_filters.version_operator} ${deploymentForm.device_filters.current_version}`} 
                size="small" 
                sx={{ mr: 1 }} 
              />
            )}
            {deploymentForm.device_filters.status && (
              <Chip label={`Status: ${deploymentForm.device_filters.status}`} size="small" />
            )}
          </Box>
          
          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Update Package</Typography>
          <Typography variant="body2">{deploymentForm.update_package_url}</Typography>
        </CardContent>
      </Card>
      
      <Alert severity="info">
        After creation, the deployment will be in PENDING status. 
        You'll need to manually start it to begin the rollout.
      </Alert>
    </Box>
  );

  const renderCreateDialog = () => (
    <Dialog 
      open={createDialogOpen} 
      onClose={() => setCreateDialogOpen(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>Create OTA Deployment</DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mt: 2, mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        
        {activeStep === 0 && renderBasicInfoStep()}
        {activeStep === 1 && renderTargetDevicesStep()}
        {activeStep === 2 && renderUpdatePackageStep()}
        {activeStep === 3 && renderReviewStep()}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
        <Button 
          onClick={() => setActiveStep(activeStep - 1)}
          disabled={activeStep === 0}
        >
          Back
        </Button>
        {activeStep < steps.length - 1 ? (
          <Button 
            onClick={() => setActiveStep(activeStep + 1)}
            variant="contained"
          >
            Next
          </Button>
        ) : (
          <Button 
            onClick={handleCreateDeployment}
            variant="contained"
            color="primary"
          >
            Create Deployment
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );

  const renderDetailsDialog = () => {
    if (!selectedDeployment) return null;

    const progress = selectedDeployment.progress || {};
    
    return (
      <Dialog 
        open={detailsDialogOpen} 
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{selectedDeployment.deployment_name}</Typography>
            <Chip 
              label={selectedDeployment.status} 
              color={getStatusColor(selectedDeployment.status)}
              size="small"
            />
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={3}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary" variant="subtitle2">Total Devices</Typography>
                  <Typography variant="h4">{progress.total_devices || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={3}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary" variant="subtitle2">Completed</Typography>
                  <Typography variant="h4" color="success.main">{progress.completed || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={3}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary" variant="subtitle2">In Progress</Typography>
                  <Typography variant="h4" color="info.main">{progress.in_progress || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={3}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary" variant="subtitle2">Failed</Typography>
                  <Typography variant="h4" color="error.main">{progress.failed || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Progress: {progress.percentage || 0}%
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={progress.percentage || 0} 
              sx={{ height: 10, borderRadius: 5 }}
            />
          </Box>
          
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>Deployment Info</Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">Target Version</Typography>
                <Typography variant="body1">{selectedDeployment.target_version}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">Rollout Strategy</Typography>
                <Typography variant="body1">{selectedDeployment.rollout_strategy}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">Created</Typography>
                <Typography variant="body1">
                  {new Date(selectedDeployment.created_at).toLocaleString()}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">Started</Typography>
                <Typography variant="body1">
                  {selectedDeployment.started_at 
                    ? new Date(selectedDeployment.started_at).toLocaleString()
                    : 'Not started'}
                </Typography>
              </Grid>
            </Grid>
          </Box>
          
          <Typography variant="subtitle1" gutterBottom>Device Status</Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Device Name</TableCell>
                  <TableCell>Current Version</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Completed</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(selectedDeployment.devices || []).map((device) => (
                  <TableRow key={device.device_id}>
                    <TableCell>{device.device_name}</TableCell>
                    <TableCell>{device.current_version}</TableCell>
                    <TableCell>
                      <Chip 
                        label={device.status} 
                        color={getDeviceStatusColor(device.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {device.started_at 
                        ? new Date(device.started_at).toLocaleString()
                        : '-'}
                    </TableCell>
                    <TableCell>
                      {device.completed_at 
                        ? new Date(device.completed_at).toLocaleString()
                        : '-'}
                    </TableCell>
                    <TableCell>
                      {device.status === 'failed' && (
                        <Tooltip title="Rollback">
                          <IconButton
                            size="small"
                            onClick={() => handleRollbackDevice(
                              selectedDeployment.deployment_id,
                              device.device_id,
                              device.current_version
                            )}
                          >
                            <RollbackIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
        <DialogActions>
          {selectedDeployment.status === 'pending' && (
            <Button
              startIcon={<StartIcon />}
              onClick={() => handleDeploymentAction(selectedDeployment.deployment_id, 'start')}
              color="success"
            >
              Start
            </Button>
          )}
          {selectedDeployment.status === 'in_progress' && (
            <Button
              startIcon={<PauseIcon />}
              onClick={() => handleDeploymentAction(selectedDeployment.deployment_id, 'pause')}
              color="warning"
            >
              Pause
            </Button>
          )}
          {selectedDeployment.status === 'paused' && (
            <Button
              startIcon={<StartIcon />}
              onClick={() => handleDeploymentAction(selectedDeployment.deployment_id, 'resume')}
              color="success"
            >
              Resume
            </Button>
          )}
          {['pending', 'in_progress', 'paused'].includes(selectedDeployment.status) && (
            <Button
              startIcon={<CancelIcon />}
              onClick={() => handleDeploymentAction(selectedDeployment.deployment_id, 'cancel')}
              color="error"
            >
              Cancel
            </Button>
          )}
          <Button onClick={() => {
            setDetailsDialogOpen(false);
            setSelectedDeployment(null);
          }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    );
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4">OTA Deployments</Typography>
          <Box>
            <Button
              startIcon={<RefreshIcon />}
              onClick={fetchDeployments}
              sx={{ mr: 1 }}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              New Deployment
            </Button>
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Status</InputLabel>
            <Select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              label="Filter by Status"
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="in_progress">In Progress</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
              <MenuItem value="paused">Paused</MenuItem>
              <MenuItem value="cancelled">Cancelled</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {loading ? (
          <LinearProgress />
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Deployment Name</TableCell>
                  <TableCell>Target Version</TableCell>
                  <TableCell>Strategy</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Progress</TableCell>
                  <TableCell>Devices</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {deployments.map((deployment) => (
                  <TableRow key={deployment.deployment_id} hover>
                    <TableCell>{deployment.deployment_name}</TableCell>
                    <TableCell>{deployment.target_version}</TableCell>
                    <TableCell>{deployment.rollout_strategy}</TableCell>
                    <TableCell>
                      <Chip 
                        label={deployment.status} 
                        color={getStatusColor(deployment.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ minWidth: 100 }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={deployment.progress_percentage} 
                        />
                        <Typography variant="caption" color="text.secondary">
                          {deployment.completed_devices}/{deployment.total_devices} ({deployment.progress_percentage}%)
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{deployment.total_devices}</TableCell>
                    <TableCell>{new Date(deployment.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton 
                          size="small"
                          onClick={() => fetchDeploymentDetails(deployment.deployment_id)}
                        >
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {deployment.status === 'pending' && (
                        <Tooltip title="Start">
                          <IconButton
                            size="small"
                            onClick={() => handleDeploymentAction(deployment.deployment_id, 'start')}
                            color="success"
                          >
                            <StartIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {deployment.status === 'in_progress' && (
                        <Tooltip title="Pause">
                          <IconButton
                            size="small"
                            onClick={() => handleDeploymentAction(deployment.deployment_id, 'pause')}
                            color="warning"
                          >
                            <PauseIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Pagination */}
        <Box display="flex" justifyContent="center" mt={3}>
          <Button
            onClick={() => setPage(page - 1)}
            disabled={page === 1}
          >
            Previous
          </Button>
          <Typography sx={{ mx: 2, alignSelf: 'center' }}>
            Page {page} of {totalPages}
          </Typography>
          <Button
            onClick={() => setPage(page + 1)}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </Box>
      </Box>

      {renderCreateDialog()}
      {renderDetailsDialog()}
    </Container>
  );
};

export default OTADeployment;
