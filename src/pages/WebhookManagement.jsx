import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Tooltip,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Send as SendIcon,
  History as HistoryIcon,
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

const EVENT_CATEGORIES = {
  'User Events': [
    'user.created',
    'user.updated',
    'user.deleted',
    'user.login',
    'user.logout',
    'user.password_changed',
    'user.email_verified',
    'user.profile_updated',
  ],
  'Subscription Events': [
    'subscription.created',
    'subscription.updated',
    'subscription.cancelled',
    'subscription.renewed',
    'subscription.payment_failed',
  ],
  'Billing Events': [
    'payment.succeeded',
    'payment.failed',
    'payment.refunded',
    'invoice.created',
    'invoice.paid',
    'invoice.overdue',
  ],
  'Organization Events': [
    'organization.created',
    'organization.updated',
    'organization.deleted',
  ],
  'Edge Device Events': [
    'device.registered',
    'device.updated',
    'device.deleted',
    'device.online',
    'device.offline',
    'device.alert',
  ],
  'Monitoring Events': [
    'alert.triggered',
    'alert.resolved',
  ],
};

const WebhookManagement = () => {
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deliveryDialogOpen, setDeliveryDialogOpen] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  
  // Form state
  const [formData, setFormData] = useState({
    url: '',
    events: [],
    description: '',
    active: true,
  });

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/v1/webhooks', {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to load webhooks');
      }
      
      const data = await response.json();
      setWebhooks(data.webhooks || []);
    } catch (err) {
      setError(err.message);
      showSnackbar('Failed to load webhooks', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadDeliveries = async (webhookId) => {
    try {
      setDeliveriesLoading(true);
      const response = await fetch(`/api/v1/webhooks/${webhookId}/deliveries`, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to load deliveries');
      }
      
      const data = await response.json();
      setDeliveries(data.deliveries || []);
    } catch (err) {
      showSnackbar('Failed to load delivery history', 'error');
    } finally {
      setDeliveriesLoading(false);
    }
  };

  const handleCreateWebhook = async () => {
    try {
      const response = await fetch('/api/v1/webhooks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create webhook');
      }

      const data = await response.json();
      showSnackbar('Webhook created successfully', 'success');
      setCreateDialogOpen(false);
      resetForm();
      loadWebhooks();
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleUpdateWebhook = async () => {
    try {
      const response = await fetch(`/api/v1/webhooks/${selectedWebhook.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update webhook');
      }

      showSnackbar('Webhook updated successfully', 'success');
      setEditDialogOpen(false);
      resetForm();
      loadWebhooks();
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleDeleteWebhook = async (webhookId) => {
    if (!confirm('Are you sure you want to delete this webhook?')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/webhooks/${webhookId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to delete webhook');
      }

      showSnackbar('Webhook deleted successfully', 'success');
      loadWebhooks();
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleTestWebhook = async (webhookId) => {
    try {
      const response = await fetch(`/api/v1/webhooks/${webhookId}/test`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Test failed');
      }

      const data = await response.json();
      showSnackbar(`Test sent! Status: ${data.status_code}`, 'success');
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleEventToggle = (event) => {
    setFormData((prev) => {
      const events = prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event];
      return { ...prev, events };
    });
  };

  const handleSelectAllEvents = (category) => {
    const categoryEvents = EVENT_CATEGORIES[category];
    const allSelected = categoryEvents.every((event) => formData.events.includes(event));
    
    setFormData((prev) => {
      let newEvents;
      if (allSelected) {
        newEvents = prev.events.filter((e) => !categoryEvents.includes(e));
      } else {
        newEvents = [...new Set([...prev.events, ...categoryEvents])];
      }
      return { ...prev, events: newEvents };
    });
  };

  const openCreateDialog = () => {
    resetForm();
    setCreateDialogOpen(true);
  };

  const openEditDialog = (webhook) => {
    setSelectedWebhook(webhook);
    setFormData({
      url: webhook.url,
      events: webhook.events || [],
      description: webhook.description || '',
      active: webhook.active,
    });
    setEditDialogOpen(true);
  };

  const openDeliveryDialog = (webhook) => {
    setSelectedWebhook(webhook);
    setDeliveryDialogOpen(true);
    loadDeliveries(webhook.id);
  };

  const resetForm = () => {
    setFormData({
      url: '',
      events: [],
      description: '',
      active: true,
    });
    setSelectedWebhook(null);
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const closeSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const getStatusIcon = (webhook) => {
    if (!webhook.active) {
      return <WarningIcon color="warning" />;
    }
    return <CheckCircleIcon color="success" />;
  };

  const getDeliveryStatusColor = (statusCode) => {
    if (!statusCode) return 'default';
    if (statusCode >= 200 && statusCode < 300) return 'success';
    if (statusCode >= 400 && statusCode < 500) return 'warning';
    return 'error';
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Webhook Management</Typography>
        <Box>
          <Button
            startIcon={<RefreshIcon />}
            onClick={loadWebhooks}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openCreateDialog}
          >
            Create Webhook
          </Button>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Info Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            About Webhooks
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Webhooks allow you to receive real-time notifications when events occur in your organization.
            Configure endpoints to receive HTTP POST requests with event data, secured with HMAC signatures.
          </Typography>
        </CardContent>
      </Card>

      {/* Webhooks Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Status</TableCell>
              <TableCell>URL</TableCell>
              <TableCell>Events</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {webhooks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    No webhooks configured. Create your first webhook to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              webhooks.map((webhook) => (
                <TableRow key={webhook.id}>
                  <TableCell>
                    <Tooltip title={webhook.active ? 'Active' : 'Inactive'}>
                      {getStatusIcon(webhook)}
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {webhook.url}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={`${webhook.events?.length || 0} events`} 
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {webhook.description || 'No description'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatTimestamp(webhook.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="View Deliveries">
                      <IconButton
                        size="small"
                        onClick={() => openDeliveryDialog(webhook)}
                        color="info"
                      >
                        <HistoryIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Test Webhook">
                      <IconButton
                        size="small"
                        onClick={() => handleTestWebhook(webhook.id)}
                        color="primary"
                      >
                        <SendIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton
                        size="small"
                        onClick={() => openEditDialog(webhook)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteWebhook(webhook.id)}
                        color="error"
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

      {/* Create Webhook Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Create Webhook
          <IconButton
            onClick={() => setCreateDialogOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Webhook URL"
                placeholder="https://example.com/webhook"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                required
                helperText="The endpoint URL that will receive webhook events"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                placeholder="Optional description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.active}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                  />
                }
                label="Active"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Select Events ({formData.events.length} selected)
              </Typography>
              {Object.entries(EVENT_CATEGORIES).map(([category, events]) => (
                <Accordion key={category}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" justifyContent="space-between" width="100%">
                      <Typography>{category}</Typography>
                      <Chip
                        label={`${events.filter((e) => formData.events.includes(e)).length}/${events.length}`}
                        size="small"
                        color={events.every((e) => formData.events.includes(e)) ? 'primary' : 'default'}
                        sx={{ mr: 2 }}
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box>
                      <Button
                        size="small"
                        onClick={() => handleSelectAllEvents(category)}
                        sx={{ mb: 1 }}
                      >
                        {events.every((e) => formData.events.includes(e)) ? 'Deselect All' : 'Select All'}
                      </Button>
                      <Grid container spacing={1}>
                        {events.map((event) => (
                          <Grid item xs={12} sm={6} key={event}>
                            <FormControlLabel
                              control={
                                <Switch
                                  checked={formData.events.includes(event)}
                                  onChange={() => handleEventToggle(event)}
                                  size="small"
                                />
                              }
                              label={event}
                            />
                          </Grid>
                        ))}
                      </Grid>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateWebhook}
            disabled={!formData.url || formData.events.length === 0}
          >
            Create Webhook
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Webhook Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Edit Webhook
          <IconButton
            onClick={() => setEditDialogOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Webhook URL"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.active}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                  />
                }
                label="Active"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Select Events ({formData.events.length} selected)
              </Typography>
              {Object.entries(EVENT_CATEGORIES).map(([category, events]) => (
                <Accordion key={category}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" justifyContent="space-between" width="100%">
                      <Typography>{category}</Typography>
                      <Chip
                        label={`${events.filter((e) => formData.events.includes(e)).length}/${events.length}`}
                        size="small"
                        color={events.every((e) => formData.events.includes(e)) ? 'primary' : 'default'}
                        sx={{ mr: 2 }}
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box>
                      <Button
                        size="small"
                        onClick={() => handleSelectAllEvents(category)}
                        sx={{ mb: 1 }}
                      >
                        {events.every((e) => formData.events.includes(e)) ? 'Deselect All' : 'Select All'}
                      </Button>
                      <Grid container spacing={1}>
                        {events.map((event) => (
                          <Grid item xs={12} sm={6} key={event}>
                            <FormControlLabel
                              control={
                                <Switch
                                  checked={formData.events.includes(event)}
                                  onChange={() => handleEventToggle(event)}
                                  size="small"
                                />
                              }
                              label={event}
                            />
                          </Grid>
                        ))}
                      </Grid>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleUpdateWebhook}
            disabled={!formData.url || formData.events.length === 0}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delivery History Dialog */}
      <Dialog
        open={deliveryDialogOpen}
        onClose={() => setDeliveryDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Delivery History
          {selectedWebhook && (
            <Typography variant="body2" color="text.secondary">
              {selectedWebhook.url}
            </Typography>
          )}
          <IconButton
            onClick={() => setDeliveryDialogOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {deliveriesLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : deliveries.length === 0 ? (
            <Box py={4} textAlign="center">
              <Typography variant="body2" color="text.secondary">
                No delivery history yet
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Event</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Attempts</TableCell>
                    <TableCell>Delivered At</TableCell>
                    <TableCell>Response</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {deliveries.map((delivery) => (
                    <TableRow key={delivery.id}>
                      <TableCell>
                        <Chip label={delivery.event} size="small" />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={delivery.response_status || 'Pending'}
                          size="small"
                          color={getDeliveryStatusColor(delivery.response_status)}
                        />
                      </TableCell>
                      <TableCell>{delivery.attempt_number || 1}</TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatTimestamp(delivery.delivered_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            maxWidth: 200,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {delivery.response_body || 'N/A'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => loadDeliveries(selectedWebhook.id)} startIcon={<RefreshIcon />}>
            Refresh
          </Button>
          <Button onClick={() => setDeliveryDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={closeSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default WebhookManagement;
