import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Tab,
  Tabs,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  Alert,
  Tooltip,
  Divider
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Business as BusinessIcon,
  People as PeopleIcon,
  Devices as DevicesIcon,
  Assessment as AssessmentIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

/**
 * Tenant Management Dashboard
 * 
 * Comprehensive multi-tenant management interface for platform administrators.
 * Allows creating, managing, and monitoring all tenant organizations.
 */
export default function TenantManagement() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [platformStats, setPlatformStats] = useState(null);
  const [error, setError] = useState(null);
  
  // Form state for creating/editing tenants
  const [formData, setFormData] = useState({
    name: '',
    plan_tier: 'trial',
    owner_email: '',
    owner_name: '',
    subdomain: '',
    custom_domain: ''
  });

  // Load tenants on mount
  useEffect(() => {
    loadTenants();
    loadPlatformStats();
  }, []);

  const loadTenants = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/admin/tenants/', {
        credentials: 'include',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      });
      
      if (!response.ok) throw new Error('Failed to load tenants');
      
      const data = await response.json();
      setTenants(data.tenants || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPlatformStats = async () => {
    try {
      const response = await fetch('/api/v1/admin/analytics/platform-stats', {
        credentials: 'include',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      });
      
      if (!response.ok) throw new Error('Failed to load platform stats');
      
      const data = await response.json();
      setPlatformStats(data);
    } catch (err) {
      console.error('Failed to load platform stats:', err);
    }
  };

  const handleCreateTenant = async () => {
    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();
      
      const response = await fetch('/api/v1/admin/tenants/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create tenant');
      }
      
      setCreateDialogOpen(false);
      setFormData({
        name: '',
        plan_tier: 'trial',
        owner_email: '',
        owner_name: '',
        subdomain: '',
        custom_domain: ''
      });
      loadTenants();
      loadPlatformStats();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateTenant = async () => {
    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();
      
      const response = await fetch(`/api/v1/admin/tenants/${selectedTenant.organization_id}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token
        },
        body: JSON.stringify({
          name: formData.name,
          plan_tier: formData.plan_tier,
          subdomain: formData.subdomain || null,
          custom_domain: formData.custom_domain || null
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update tenant');
      }
      
      setEditDialogOpen(false);
      setSelectedTenant(null);
      loadTenants();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTenant = async (tenantId, hardDelete = false) => {
    if (!window.confirm(`Are you sure you want to ${hardDelete ? 'permanently delete' : 'deactivate'} this tenant?`)) {
      return;
    }

    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();
      
      const response = await fetch(`/api/v1/admin/tenants/${tenantId}?hard_delete=${hardDelete}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'X-CSRF-Token': csrfData.csrf_token
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete tenant');
      }
      
      loadTenants();
      loadPlatformStats();
    } catch (err) {
      setError(err.message);
    }
  };

  const openEditDialog = (tenant) => {
    setSelectedTenant(tenant);
    setFormData({
      name: tenant.name,
      plan_tier: tenant.plan_tier,
      owner_email: tenant.owner_email,
      owner_name: '',
      subdomain: tenant.subdomain || '',
      custom_domain: tenant.custom_domain || ''
    });
    setEditDialogOpen(true);
  };

  const getTierLabel = (tier) => {
    const labels = {
      trial: 'Trial',
      starter: 'Starter',
      professional: 'Professional',
      enterprise: 'Enterprise',
      founders_friend: 'Founder Friend'
    };
    return labels[tier] || tier;
  };

  const getTierColor = (tier) => {
    const colors = {
      trial: 'default',
      starter: 'primary',
      professional: 'secondary',
      enterprise: 'success',
      founders_friend: 'primary'
    };
    return colors[tier] || 'default';
  };

  const renderPlatformStats = () => {
    if (!platformStats) return null;

    return (
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <BusinessIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Tenants</Typography>
              </Box>
              <Typography variant="h3">{platformStats.total_tenants}</Typography>
              <Typography variant="body2" color="text.secondary">
                {platformStats.active_tenants} active
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <PeopleIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Users</Typography>
              </Box>
              <Typography variant="h3">{platformStats.total_users}</Typography>
              <Typography variant="body2" color="text.secondary">
                {platformStats.growth_stats?.new_users_30d || 0} new (30d)
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <DevicesIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Devices</Typography>
              </Box>
              <Typography variant="h3">{platformStats.total_devices}</Typography>
              <Typography variant="body2" color="text.secondary">
                Avg: {platformStats.growth_stats?.avg_devices_per_tenant?.toFixed(1) || 0} / tenant
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <AssessmentIcon color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">Webhooks</Typography>
              </Box>
              <Typography variant="h3">{platformStats.total_webhooks}</Typography>
              <Typography variant="body2" color="text.secondary">
                {platformStats.total_api_keys} API keys
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderTenantList = () => (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Organization</TableCell>
            <TableCell>Tier</TableCell>
            <TableCell>Owner</TableCell>
            <TableCell>Members</TableCell>
            <TableCell>Resources</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Created</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {tenants.map((tenant) => (
            <TableRow key={tenant.organization_id}>
              <TableCell>
                <Box>
                  <Typography variant="body1">{tenant.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {tenant.organization_id}
                  </Typography>
                  {tenant.subdomain && (
                    <Typography variant="caption" display="block" color="primary">
                      {tenant.subdomain}.ops-center.com
                    </Typography>
                  )}
                </Box>
              </TableCell>
              <TableCell>
                <Chip label={getTierLabel(tenant.plan_tier)} color={getTierColor(tenant.plan_tier)} size="small" />
              </TableCell>
              <TableCell>{tenant.owner_email}</TableCell>
              <TableCell>{tenant.member_count}</TableCell>
              <TableCell>
                <Typography variant="caption" display="block">
                  {tenant.resource_counts?.users || 0} users
                </Typography>
                <Typography variant="caption" display="block">
                  {tenant.resource_counts?.devices || 0} devices
                </Typography>
                <Typography variant="caption" display="block">
                  {tenant.resource_counts?.webhooks || 0} webhooks
                </Typography>
              </TableCell>
              <TableCell>
                {tenant.is_active ? (
                  <Chip icon={<CheckIcon />} label="Active" color="success" size="small" />
                ) : (
                  <Chip icon={<CloseIcon />} label="Inactive" color="error" size="small" />
                )}
              </TableCell>
              <TableCell>
                {new Date(tenant.created_at).toLocaleDateString()}
              </TableCell>
              <TableCell align="right">
                <Tooltip title="Edit">
                  <IconButton size="small" onClick={() => openEditDialog(tenant)}>
                    <EditIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Deactivate">
                  <IconButton size="small" onClick={() => handleDeleteTenant(tenant.organization_id, false)}>
                    <CloseIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete Permanently">
                  <IconButton size="small" color="error" onClick={() => handleDeleteTenant(tenant.organization_id, true)}>
                    <DeleteIcon />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderTierDistribution = () => {
    if (!platformStats?.tier_distribution) return null;

    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Tier Distribution</Typography>
          <Divider sx={{ mb: 2 }} />
          {Object.entries(platformStats.tier_distribution).map(([tier, count]) => (
            <Box key={tier} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2">{tier}</Typography>
                <Typography variant="body2" fontWeight="bold">{count}</Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={(count / platformStats.total_tenants) * 100}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          ))}
        </CardContent>
      </Card>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          <BusinessIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Tenant Management
        </Typography>
        <Box>
          <Button
            startIcon={<RefreshIcon />}
            onClick={() => { loadTenants(); loadPlatformStats(); }}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Tenant
          </Button>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Platform Statistics */}
      {renderPlatformStats()}

      {/* Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={selectedTab} onChange={(e, v) => setSelectedTab(v)}>
          <Tab label="All Tenants" />
          <Tab label="Tier Distribution" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {loading ? (
        <LinearProgress />
      ) : selectedTab === 0 ? (
        renderTenantList()
      ) : (
        renderTierDistribution()
      )}

      {/* Create Tenant Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Tenant</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Organization Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Owner Email"
            type="email"
            value={formData.owner_email}
            onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Owner Name"
            value={formData.owner_name}
            onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
            margin="normal"
            required
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Plan Tier</InputLabel>
            <Select
              value={formData.plan_tier}
              onChange={(e) => setFormData({ ...formData, plan_tier: e.target.value })}
              label="Plan Tier"
            >
              <MenuItem value="trial">Trial</MenuItem>
              <MenuItem value="starter">Starter</MenuItem>
              <MenuItem value="professional">Professional</MenuItem>
              <MenuItem value="enterprise">Enterprise</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Subdomain (optional)"
            value={formData.subdomain}
            onChange={(e) => setFormData({ ...formData, subdomain: e.target.value })}
            margin="normal"
            helperText="e.g., 'acme' for acme.ops-center.com"
          />
          <TextField
            fullWidth
            label="Custom Domain (optional)"
            value={formData.custom_domain}
            onChange={(e) => setFormData({ ...formData, custom_domain: e.target.value })}
            margin="normal"
            helperText="e.g., ops.company.com"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateTenant} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Tenant Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Tenant</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Organization Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Plan Tier</InputLabel>
            <Select
              value={formData.plan_tier}
              onChange={(e) => setFormData({ ...formData, plan_tier: e.target.value })}
              label="Plan Tier"
            >
              <MenuItem value="trial">Trial</MenuItem>
              <MenuItem value="starter">Starter</MenuItem>
              <MenuItem value="professional">Professional</MenuItem>
              <MenuItem value="enterprise">Enterprise</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Subdomain"
            value={formData.subdomain}
            onChange={(e) => setFormData({ ...formData, subdomain: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Custom Domain"
            value={formData.custom_domain}
            onChange={(e) => setFormData({ ...formData, custom_domain: e.target.value })}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateTenant} variant="contained">Update</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
