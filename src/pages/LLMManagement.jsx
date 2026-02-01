import React, { useState, useEffect } from 'react';
// Safe utilities for defensive rendering (Phase 3 refactoring)
import { safeMap, safeFilter } from '../utils/safeArrayUtils';
import { safeToFixed } from '../utils/safeNumberUtils';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
  Grid,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  Snackbar
} from '@mui/material';
import {
  Memory,
  CloudQueue,
  Route,
  Analytics,
  Settings,
  Refresh
} from '@mui/icons-material';
import ModelRegistry from '../components/llm/ModelRegistry';
import ProviderCard from '../components/llm/ProviderCard';
import UsageChart from '../components/llm/UsageChart';
import CostChart from '../components/llm/CostChart';
import CacheStatsCard from '../components/llm/CacheStatsCard';

/**
 * LLMManagement Component
 *
 * Comprehensive LiteLLM management dashboard with:
 * - Tab 1: Models - Model registry with CRUD operations
 * - Tab 2: Providers - Provider configuration and testing
 * - Tab 3: Routing - Routing rules and load balancing
 * - Tab 4: Analytics - Usage and cost analytics
 * - Tab 5: Settings - Rate limits and cache configuration
 */
export default function LLMManagement() {
  const [tabValue, setTabValue] = useState(0);
  const [providers, setProviders] = useState([]);
  const [usage, setUsage] = useState({});
  const [costs, setCosts] = useState({});
  const [cacheStats, setCacheStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  useEffect(() => {
    if (tabValue === 1) fetchProviders();
    if (tabValue === 3) fetchAnalytics();
    if (tabValue === 4) fetchCacheStats();
  }, [tabValue]);

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/llm/providers', {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch providers');
      const data = await response.json();
      // Backend returns array directly, not wrapped in {providers: [...]}
      setProviders(Array.isArray(data) ? data : (data.providers || []));
    } catch (err) {
      showSnackbar(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [usageRes, costsRes] = await Promise.all([
        fetch('/api/v1/llm/usage?period=7d', {
          headers: { 'X-Admin-Token': localStorage.getItem('adminToken') || '' }
        }),
        fetch('/api/v1/llm/costs?period=30d', {
          headers: { 'X-Admin-Token': localStorage.getItem('adminToken') || '' }
        })
      ]);

      if (usageRes.ok) {
        const usageData = await usageRes.json();
        setUsage(usageData.by_model || {});
      }

      if (costsRes.ok) {
        const costsData = await costsRes.json();
        setCosts(costsData.by_model || {});
      }
    } catch (err) {
      showSnackbar(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchCacheStats = async () => {
    try {
      const response = await fetch('/api/v1/llm/cache-stats', {
        headers: { 'X-Admin-Token': localStorage.getItem('adminToken') || '' }
      });
      if (response.ok) {
        const data = await response.json();
        setCacheStats(data);
      }
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleClearCache = async () => {
    try {
      const response = await fetch('/api/v1/llm/cache/clear', {
        method: 'POST',
        headers: { 'X-Admin-Token': localStorage.getItem('adminToken') || '' }
      });
      if (response.ok) {
        showSnackbar('Cache cleared successfully', 'success');
        fetchCacheStats();
      }
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleTestProvider = async (provider) => {
    try {
      showSnackbar('Testing provider connection...', 'info');
      const response = await fetch(`/api/v1/llm/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ provider_id: provider.id })
      });
      
      if (!response.ok) throw new Error('Test request failed');
      
      const result = await response.json();
      
      if (result.status === 'success') {
        showSnackbar(`${result.provider_name} is online (${result.latency_ms}ms)`, 'success');
      } else {
        showSnackbar(`Test failed: ${result.error || result.message}`, 'error');
      }
    } catch (err) {
      showSnackbar(`Test failed: ${err.message}`, 'error');
    }
  };

  const handleEditProvider = (provider) => {
    setSelectedProvider(provider);
    setEditDialogOpen(true);
  };

  const handleDeleteProvider = async (provider) => {
    setSelectedProvider(provider);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteProvider = async () => {
    try {
      const response = await fetch(`/api/v1/llm/providers/${selectedProvider.id}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to delete provider');
      
      showSnackbar('Provider deleted successfully', 'success');
      setDeleteDialogOpen(false);
      setSelectedProvider(null);
      fetchProviders();
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  const handleUpdateProvider = async (updates) => {
    try {
      const response = await fetch(`/api/v1/llm/providers/${selectedProvider.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updates)
      });

      if (!response.ok) throw new Error('Failed to update provider');

      showSnackbar('Provider updated successfully', 'success');
      setEditDialogOpen(false);
      setSelectedProvider(null);
      fetchProviders();
    } catch (err) {
      showSnackbar(err.message, 'error');
    }
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          LiteLLM Management
        </Typography>
        <Typography variant="body1" sx={{ color: 'rgb(243, 232, 255)' }}>
          Manage models, providers, routing, and analytics for your LLM infrastructure
        </Typography>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<Memory />} label="Models" iconPosition="start" />
          <Tab icon={<CloudQueue />} label="Providers" iconPosition="start" />
          <Tab icon={<Route />} label="Routing & Load Balancing" iconPosition="start" />
          <Tab icon={<Analytics />} label="Analytics" iconPosition="start" />
          <Tab icon={<Settings />} label="Settings" iconPosition="start" />
        </Tabs>
      </Paper>

      <Box sx={{ py: 3 }}>
        {/* Tab 1: Models */}
        {tabValue === 0 && (
          <ModelRegistry showSnackbar={showSnackbar} />
        )}

        {/* Tab 2: Providers */}
        {tabValue === 1 && (
          <Box>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h5">Provider Management</Typography>
              <Button startIcon={<Refresh />} onClick={fetchProviders} variant="outlined">
                Refresh
              </Button>
            </Box>

            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : providers.length === 0 ? (
              <Alert severity="info">No providers configured yet.</Alert>
            ) : (
              <Grid container spacing={3}>
                {/* REFACTORED: Using safeMap for provider list */}
                {safeMap(providers, (provider) => (
                  <Grid item xs={12} sm={6} md={4} key={provider.id}>
                    <ProviderCard
                      provider={provider}
                      onEdit={handleEditProvider}
                      onDelete={handleDeleteProvider}
                      onTest={handleTestProvider}
                    />
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        )}

        {/* Tab 3: Routing & Load Balancing */}
        {tabValue === 2 && (
          <Box>
            <Typography variant="h5" gutterBottom>
              Routing Rules & Load Balancing
            </Typography>
            <Alert severity="info" sx={{ mb: 3 }}>
              Routing rules allow you to direct requests to specific providers based on model patterns,
              user tiers, or other conditions.
            </Alert>

            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Load Balancing Strategy
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Current strategy: Round Robin
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  Configure routing rules to optimize cost, latency, or reliability.
                </Typography>
              </CardContent>
            </Card>
          </Box>
        )}

        {/* Tab 4: Analytics */}
        {tabValue === 3 && (
          <Box>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h5">Usage & Cost Analytics</Typography>
              <Button startIcon={<Refresh />} onClick={fetchAnalytics} variant="outlined">
                Refresh
              </Button>
            </Box>

            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <UsageChart data={usage} title="Usage by Model (Last 7 Days)" />
                </Grid>
                <Grid item xs={12} md={6}>
                  <CostChart data={costs} title="Cost Breakdown (Last 30 Days)" />
                </Grid>
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Summary Statistics
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Total Requests
                          </Typography>
                          <Typography variant="h4">
                            {Object.values(usage).reduce(
                              (sum, u) => sum + (u.request_count || 0),
                              0
                            ).toLocaleString()}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Total Tokens
                          </Typography>
                          <Typography variant="h4">
                            {Object.values(usage).reduce(
                              (sum, u) =>
                                sum +
                                (u.total_input_tokens || 0) +
                                (u.total_output_tokens || 0),
                              0
                            ).toLocaleString()}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Total Cost
                          </Typography>
                          <Typography variant="h4" color="primary">
                            ${Object.values(costs).reduce(
                              (sum, c) => sum + (c.total_cost || 0),
                              0
                            ).toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Avg Latency
                          </Typography>
                          <Typography variant="h4">
                            {(
                              Object.values(usage).reduce(
                                (sum, u) => sum + (u.avg_latency_ms || 0),
                                0
                              ) / Object.keys(usage).length || 0
                            ).toFixed(0)}
                            ms
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </Box>
        )}

        {/* Tab 5: Settings */}
        {tabValue === 4 && (
          <Box>
            <Typography variant="h5" gutterBottom>
              Settings
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <CacheStatsCard stats={cacheStats} onClear={handleClearCache} />
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Rate Limiting
                    </Typography>
                    <Alert severity="info">
                      Configure rate limits per model, provider, or user to prevent abuse and
                      manage costs.
                    </Alert>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Fallback Configuration
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Configure automatic fallback to secondary providers when the primary provider
                      fails or is unavailable.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}
      </Box>

      {/* Edit Provider Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Provider: {selectedProvider?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="API Key"
              type="password"
              placeholder="Leave empty to keep current key"
              fullWidth
              onChange={(e) => setSelectedProvider({...selectedProvider, api_key: e.target.value})}
            />
            <TextField
              label="API Base URL"
              defaultValue={selectedProvider?.api_base_url || ''}
              fullWidth
              onChange={(e) => setSelectedProvider({...selectedProvider, api_base_url: e.target.value})}
            />
            <TextField
              label="Priority"
              type="number"
              defaultValue={selectedProvider?.priority || 0}
              fullWidth
              helperText="Higher priority providers are preferred"
              onChange={(e) => setSelectedProvider({...selectedProvider, priority: parseInt(e.target.value)})}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={selectedProvider?.status === 'active'}
                  onChange={(e) => setSelectedProvider({...selectedProvider, enabled: e.target.checked})}
                />
              }
              label="Enabled"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={() => handleUpdateProvider({
              api_key: selectedProvider?.api_key,
              api_base_url: selectedProvider?.api_base_url,
              priority: selectedProvider?.priority,
              enabled: selectedProvider?.enabled ?? selectedProvider?.status === 'active'
            })} 
            variant="contained"
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Provider Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Delete Provider</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone!
          </Alert>
          <Typography>
            Are you sure you want to delete provider <strong>{selectedProvider?.name}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This will also permanently delete all associated models.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmDeleteProvider} variant="contained" color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Container>
  );
}
