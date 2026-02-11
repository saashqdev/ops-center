import React, { useState, useEffect } from 'react';
import { useToast } from '../components/Toast';
import FlowBuilder from '../components/agents/FlowBuilder';
import { flowTemplates, getAllCategories } from '../data/flowTemplates';
import {
  Box,
  Card,
  CardContent,
  Button,
  Grid,
  Typography,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Code as CodeIcon,
  Key as KeyIcon,
  Category as CategoryIcon,
  Star as StarIcon
} from '@mui/icons-material';

export default function ClaudeAgents() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState(0);
  const [flows, setFlows] = useState([]);
  const [selectedFlow, setSelectedFlow] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showExecuteDialog, setShowExecuteDialog] = useState(false);
  const [showAPIKeyDialog, setShowAPIKeyDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [executions, setExecutions] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Creation flow states
  const [createStep, setCreateStep] = useState(0); // 0: choose template, 1: configure
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateCategory, setTemplateCategory] = useState('');
  const [editFlowData, setEditFlowData] = useState(null);
  
  // Execution states
  const [executePrompt, setExecutePrompt] = useState('');
  const [executionResult, setExecutionResult] = useState(null);

  // API Key form
  const [apiKeyName, setApiKeyName] = useState('');
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [apiKeyProvider, setApiKeyProvider] = useState('anthropic');

  useEffect(() => {
    fetchFlows();
    fetchAPIKeys();
  }, []);

  // Fetch user's agent flows
  const fetchFlows = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/claude-agents/flows', {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch flows');
      const data = await response.json();
      setFlows(data.flows || []);
    } catch (err) {
      setError(err.message);
      toast.error('Failed to load flows');
    } finally {
      setLoading(false);
    }
  };

  // Fetch API keys
  const fetchAPIKeys = async () => {
    try {
      const response = await fetch('/api/v1/claude-agents/api-keys', {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch API keys');
      const data = await response.json();
      setApiKeys(data.api_keys || []);
    } catch (err) {
      console.error('Failed to load API keys:', err);
    }
  };

  // Create new flow
  const createFlow = async (flowData) => {
    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();

      const response = await fetch('/api/v1/claude-agents/flows', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token
        },
        credentials: 'include',
        body: JSON.stringify(flowData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create flow');
      }

      toast.success('Agent flow created successfully!');
      setShowCreateDialog(false);
      setCreateStep(0);
      setSelectedTemplate(null);
      fetchFlows();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const startCreateFlow = () => {
    setCreateStep(0);
    setSelectedTemplate(null);
    setShowCreateDialog(true);
  };

  const selectTemplate = (template) => {
    setSelectedTemplate(template);
    setCreateStep(1);
  };

  // Execute flow
  const executeFlow = async (flow) => {
    if (!executePrompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    setLoading(true);
    setExecutionResult(null);

    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();

      const response = await fetch(`/api/v1/claude-agents/flows/${flow.id}/execute`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token
        },
        credentials: 'include',
        body: JSON.stringify({
          input_data: { prompt: executePrompt }
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Execution failed');
      }

      const result = await response.json();
      setExecutionResult(result);
      toast.success('Flow executed successfully!');
    } catch (err) {
      toast.error(err.message);
      setExecutionResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  // Delete flow
  const deleteFlow = async (flowId) => {
    if (!confirm('Are you sure you want to delete this flow?')) return;

    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();

      const response = await fetch(`/api/v1/claude-agents/flows/${flowId}`, {
        method: 'DELETE',
        headers: {
          'X-CSRF-Token': csrfData.csrf_token
        },
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete flow');

      toast.success('Flow deleted successfully');
      fetchFlows();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Edit flow
  const openEditDialog = (flow) => {
    setSelectedFlow(flow);
    setEditFlowData({
      name: flow.name,
      description: flow.description,
      ...flow.flow_config
    });
    setShowEditDialog(true);
  };

  const updateFlow = async (flowData) => {
    try {
      const { name, description, systemPrompt, modelParams, tools, agents } = flowData;
      
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();

      const response = await fetch(`/api/v1/claude-agents/flows/${selectedFlow.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token
        },
        credentials: 'include',
        body: JSON.stringify({
          name,
          description,
          flow_config: { systemPrompt, modelParams, tools, agents }
        })
      });
      
      if (!response.ok) throw new Error('Failed to update flow');
      
      setShowEditDialog(false);
      toast.success('Flow updated successfully');
      fetchFlows();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const duplicateFlow = async (flow) => {
    const newFlowData = {
      name: `${flow.name} (Copy)`,
      description: flow.description,
      ...flow.flow_config
    };
    await createFlow(newFlowData);
  };

  // Add API key
  const addAPIKey = async () => {
    try {
      // Get CSRF token
      const csrfResponse = await fetch('/api/v1/auth/csrf-token', {
        credentials: 'include'
      });
      const csrfData = await csrfResponse.json();

      const response = await fetch('/api/v1/claude-agents/api-keys', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token
        },
        credentials: 'include',
        body: JSON.stringify({
          key_name: apiKeyName,
          provider: apiKeyProvider,
          api_key: apiKeyValue,
          is_default: apiKeys.length === 0
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add API key');
      }

      toast.success('API key added successfully!');
      setShowAPIKeyDialog(false);
      setApiKeyName('');
      setApiKeyValue('');
      fetchAPIKeys();
    } catch (err) {
      toast.error(err.message);
    }
  };



  const openExecuteDialog = (flow) => {
    setSelectedFlow(flow);
    setExecutePrompt('');
    setExecutionResult(null);
    setShowExecuteDialog(true);
    // Load execution history for this flow
    fetchFlowExecutions(flow.id);
  };

  const fetchFlowExecutions = async (flowId) => {
    try {
      const response = await fetch(`/api/v1/claude-agents/flows/${flowId}/executions`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch executions');
      const data = await response.json();
      setExecutions(data.executions || []);
    } catch (err) {
      console.error('Failed to load execution history:', err);
    }
  };

  return (
    <Box p={3}>
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="center">
        <div>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
            🤖 Claude Agent Workflows
          </Typography>
          <Typography variant="body1" sx={{ color: '#c084fc' }}>
            Create and manage custom AI agent workflows powered by Claude
          </Typography>
        </div>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<KeyIcon />}
            onClick={() => setShowAPIKeyDialog(true)}
          >
            API Keys
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={startCreateFlow}
          >
            Create Flow
          </Button>
        </Box>
      </Box>

      {apiKeys.length === 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No API keys configured. Please add an Anthropic API key to execute flows.
        </Alert>
      )}

      <Card>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="My Flows" />
          <Tab label="Execution History" />
        </Tabs>

        <CardContent>
          {activeTab === 0 && (
            <Box>
              {loading && <CircularProgress />}
              
              {!loading && flows.length === 0 && (
                <Box textAlign="center" py={8}>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    No flows created yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Create your first agent workflow to get started
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={startCreateFlow}
                  >
                    Create Your First Flow
                  </Button>
                </Box>
              )}

              {!loading && flows.length > 0 && (
                <Grid container spacing={3}>
                  {flows.map((flow) => (
                    <Grid item xs={12} sm={6} md={4} key={flow.id}>
                      <Card variant="outlined">
                        <CardContent>
                          <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              {flow.name}
                            </Typography>
                            <Chip
                              label={flow.status}
                              color={flow.status === 'active' ? 'success' : 'default'}
                              size="small"
                            />
                          </Box>
                          
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {flow.description || 'No description'}
                          </Typography>

                          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                            Last executed: {flow.last_executed_at || 'Never'}
                          </Typography>

                          <Box display="flex" gap={1}>
                            <Button
                              size="small"
                              variant="contained"
                              startIcon={<PlayIcon />}
                              onClick={() => openExecuteDialog(flow)}
                              disabled={apiKeys.length === 0}
                            >
                              Execute
                            </Button>
                            <IconButton size="small" onClick={() => openEditDialog(flow)}>
                              <EditIcon />
                            </IconButton>
                            <Button
                              size="small"
                              onClick={() => duplicateFlow(flow)}
                            >
                              Duplicate
                            </Button>
                            <IconButton size="small" color="error" onClick={() => deleteFlow(flow.id)}>
                              <DeleteIcon />
                            </IconButton>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}
            </Box>
          )}

          {activeTab === 1 && (
            <Box>
              <Typography variant="h6" gutterBottom>Recent Executions</Typography>
              {loading && <CircularProgress />}
              
              {!loading && executions.length === 0 && (
                <Alert severity="info">No executions yet. Run a flow to see history here.</Alert>
              )}

              {!loading && executions.length > 0 && (
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Flow</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Tokens</TableCell>
                        <TableCell>Duration</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell>Output Preview</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {executions.slice(0, 20).map((exec) => (
                        <TableRow key={exec.id}>
                          <TableCell>
                            {flows.find(f => f.id === exec.flow_id)?.name || 'Unknown'}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={exec.status}
                              size="small"
                              color={
                                exec.status === 'completed' ? 'success' :
                                exec.status === 'failed' ? 'error' : 'default'
                              }
                            />
                          </TableCell>
                          <TableCell>
                            {exec.tokens_used ? 
                              `${exec.tokens_used.input + exec.tokens_used.output}` : 
                              '-'
                            }
                          </TableCell>
                          <TableCell>
                            {exec.execution_time_ms ? `${exec.execution_time_ms}ms` : '-'}
                          </TableCell>
                          <TableCell>
                            {new Date(exec.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                              {exec.output_data?.output?.substring(0, 50)}...
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Edit Flow Dialog */}
      <Dialog open={showEditDialog} onClose={() => setShowEditDialog(false)} maxWidth="lg" fullWidth>
        <DialogTitle>Edit Flow: {selectedFlow?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            {editFlowData && (
              <FlowBuilder
                initialFlow={editFlowData}
                onSave={updateFlow}
                onCancel={() => setShowEditDialog(false)}
              />
            )}
          </Box>
        </DialogContent>
      </Dialog>

      {/* Create Flow Dialog */}
      <Dialog
        open={showCreateDialog}
        onClose={() => {
          setShowCreateDialog(false);
          setCreateStep(0);
          setSelectedTemplate(null);
        }}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {createStep === 0 ? 'Choose a Template' : `Create: ${selectedTemplate?.name}`}
        </DialogTitle>
        <DialogContent>
          {createStep === 0 && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Start with a pre-built template or create from scratch
              </Typography>

              <Box sx={{ mb: 3, mt: 2 }}>
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={templateCategory}
                    onChange={(e) => setTemplateCategory(e.target.value)}
                  >
                    <MenuItem value="">All Categories</MenuItem>
                    {getAllCategories().map(cat => (
                      <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>

              <Grid container spacing={2}>
                {flowTemplates
                  .filter(t => !templateCategory || t.category === templateCategory)
                  .map((template) => (
                    <Grid item xs={12} sm={6} md={4} key={template.id}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          '&:hover': { boxShadow: 4, transform: 'translateY(-2px)' },
                          transition: 'all 0.2s',
                          height: '100%'
                        }}
                        onClick={() => selectTemplate(template)}
                      >
                        <CardContent>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <Typography variant="h4">{template.icon}</Typography>
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              {template.name}
                            </Typography>
                          </Box>
                          <Chip label={template.category} size="small" sx={{ mb: 1 }} />
                          <Typography variant="body2" color="text.secondary">
                            {template.description}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
              </Grid>
            </Box>
          )}

          {createStep === 1 && selectedTemplate && (
            <Box sx={{ pt: 2 }}>
              <FlowBuilder
                onSave={createFlow}
                initialFlow={{
                  name: selectedTemplate.name,
                  description: selectedTemplate.description,
                  flow_config: selectedTemplate.flow_config
                }}
              />
            </Box>
          )}
        </DialogContent>
        {createStep === 0 && (
          <DialogActions>
            <Button onClick={() => setShowCreateDialog(false)}>Cancel</Button>
          </DialogActions>
        )}
      </Dialog>

      {/* Execute Flow Dialog */}
      <Dialog open={showExecuteDialog} onClose={() => setShowExecuteDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Execute: {selectedFlow?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Prompt"
              fullWidth
              multiline
              rows={4}
              value={executePrompt}
              onChange={(e) => setExecutePrompt(e.target.value)}
              placeholder="Enter your prompt here..."
            />
            
            {loading && <CircularProgress />}
            
            {executionResult && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Result:</Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                  {executionResult.error ? (
                    <Typography color="error">{executionResult.error}</Typography>
                  ) : (
                    <>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
                        {executionResult.output}
                      </Typography>
                      {executionResult.tokens_used && (
                        <Typography variant="caption" color="text.secondary">
                          Tokens: {executionResult.tokens_used.input} in / {executionResult.tokens_used.output} out
                          ({executionResult.execution_time_ms}ms)
                        </Typography>
                      )}
                    </>
                  )}
                </Paper>
              </Box>
            )}

            {/* Recent executions for this flow */}
            {executions.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Recent Executions ({executions.length})
                </Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {executions.slice(0, 5).map((exec, idx) => (
                    <Paper
                      key={exec.id}
                      variant="outlined"
                      sx={{ p: 1.5, mb: 1, bgcolor: exec.status === 'completed' ? '#f0fdf4' : '#fef2f2' }}
                    >
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Chip label={exec.status} size="small" color={exec.status === 'completed' ? 'success' : 'error'} />
                        <Typography variant="caption">
                          {new Date(exec.created_at).toLocaleString()}
                        </Typography>
                      </Box>
                      <Typography variant="caption" noWrap>
                        {exec.output_data?.output?.substring(0, 80)}...
                      </Typography>
                    </Paper>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowExecuteDialog(false)}>Close</Button>
          <Button
            onClick={() => executeFlow(selectedFlow)}
            variant="contained"
            disabled={loading || !executePrompt.trim()}
            startIcon={<PlayIcon />}
          >
            Execute
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add API Key Dialog */}
      <Dialog open={showAPIKeyDialog} onClose={() => setShowAPIKeyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add API Key</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Key Name"
              fullWidth
              value={apiKeyName}
              onChange={(e) => setApiKeyName(e.target.value)}
              placeholder="e.g., My Anthropic Key"
            />
            
            <TextField
              label="API Key"
              fullWidth
              type="password"
              value={apiKeyValue}
              onChange={(e) => setApiKeyValue(e.target.value)}
              placeholder="sk-ant-..."
            />

            <Typography variant="caption" color="text.secondary">
              Your API key will be encrypted and stored securely. Current keys: {apiKeys.length}
            </Typography>

            {apiKeys.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Existing Keys:</Typography>
                {apiKeys.map((key) => (
                  <Chip
                    key={key.id}
                    label={`${key.key_name} ${key.is_default ? '(default)' : ''}`}
                    size="small"
                    sx={{ mr: 1, mb: 1 }}
                  />
                ))}
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAPIKeyDialog(false)}>Cancel</Button>
          <Button
            onClick={addAPIKey}
            variant="contained"
            disabled={!apiKeyName.trim() || !apiKeyValue.trim()}
          >
            Add Key
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
