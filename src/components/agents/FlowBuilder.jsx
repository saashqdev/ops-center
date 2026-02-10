import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Chip,
  Divider,
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  DragIndicator as DragIcon,
  Settings as SettingsIcon,
  Code as CodeIcon
} from '@mui/icons-material';

/**
 * Visual Flow Builder Component
 * Allows users to create agent workflows by configuring:
 * - System prompts
 * - Model parameters
 * - Tools and capabilities
 * - Multi-step agent chains
 */
export default function FlowBuilder({ onSave, initialFlow = null }) {
  const [flowName, setFlowName] = useState(initialFlow?.name || '');
  const [flowDescription, setFlowDescription] = useState(initialFlow?.description || '');
  const [systemPrompt, setSystemPrompt] = useState(
    initialFlow?.flow_config?.system_prompt || 'You are a helpful AI assistant.'
  );
  const [model, setModel] = useState(
    initialFlow?.flow_config?.model || 'claude-3-5-sonnet-20241022'
  );
  const [maxTokens, setMaxTokens] = useState(
    initialFlow?.flow_config?.max_tokens || 4096
  );
  const [temperature, setTemperature] = useState(
    initialFlow?.flow_config?.temperature || 1.0
  );
  const [tools, setTools] = useState(initialFlow?.flow_config?.tools || []);
  const [agents, setAgents] = useState(initialFlow?.flow_config?.agents || []);
  const [showJSON, setShowJSON] = useState(false);

  const addTool = () => {
    setTools([...tools, {
      name: '',
      description: '',
      input_schema: {
        type: 'object',
        properties: {},
        required: []
      }
    }]);
  };

  const removeTool = (index) => {
    setTools(tools.filter((_, i) => i !== index));
  };

  const updateTool = (index, field, value) => {
    const newTools = [...tools];
    newTools[index] = { ...newTools[index], [field]: value };
    setTools(newTools);
  };

  const addAgent = () => {
    setAgents([...agents, {
      name: '',
      role: 'assistant',
      capabilities: []
    }]);
  };

  const removeAgent = (index) => {
    setAgents(agents.filter((_, i) => i !== index));
  };

  const updateAgent = (index, field, value) => {
    const newAgents = [...agents];
    newAgents[index] = { ...newAgents[index], [field]: value };
    setAgents(newAgents);
  };

  const getFlowConfig = () => ({
    system_prompt: systemPrompt,
    model: model,
    max_tokens: maxTokens,
    temperature: temperature,
    tools: tools.filter(t => t.name), // Only include tools with names
    agents: agents.filter(a => a.name) // Only include agents with names
  });

  const handleSave = () => {
    const flowData = {
      name: flowName,
      description: flowDescription,
      flow_config: getFlowConfig()
    };
    onSave(flowData);
  };

  const getJSONPreview = () => {
    return JSON.stringify(getFlowConfig(), null, 2);
  };

  return (
    <Box>
      {/* Basic Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Flow Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Flow Name"
                fullWidth
                value={flowName}
                onChange={(e) => setFlowName(e.target.value)}
                placeholder="e.g., Research Assistant"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Model</InputLabel>
                <Select value={model} onChange={(e) => setModel(e.target.value)}>
                  <MenuItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</MenuItem>
                  <MenuItem value="claude-3-opus-20240229">Claude 3 Opus</MenuItem>
                  <MenuItem value="claude-3-sonnet-20240229">Claude 3 Sonnet</MenuItem>
                  <MenuItem value="claude-3-haiku-20240307">Claude 3 Haiku</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description"
                fullWidth
                multiline
                rows={2}
                value={flowDescription}
                onChange={(e) => setFlowDescription(e.target.value)}
                placeholder="Brief description of what this flow does"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* System Prompt */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            System Prompt
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={6}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Define the agent's role, personality, and behavior..."
            helperText="This sets the context for how the agent should behave"
          />
        </CardContent>
      </Card>

      {/* Model Parameters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Model Parameters
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Max Tokens"
                type="number"
                fullWidth
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                helperText="Maximum tokens in response (1-8192)"
                inputProps={{ min: 1, max: 8192 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Temperature"
                type="number"
                fullWidth
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                helperText="Randomness in responses (0.0-2.0)"
                inputProps={{ min: 0, max: 2, step: 0.1 }}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Tools Configuration */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Tools & Capabilities
            </Typography>
            <Button startIcon={<AddIcon />} onClick={addTool} size="small">
              Add Tool
            </Button>
          </Box>

          {tools.length === 0 && (
            <Alert severity="info">
              No tools configured. Add tools to give your agent special capabilities like web search, calculations, or API access.
            </Alert>
          )}

          {tools.map((tool, index) => (
            <Card key={index} variant="outlined" sx={{ mb: 2, bgcolor: '#f9fafb' }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Grid container spacing={2} sx={{ flexGrow: 1 }}>
                    <Grid item xs={12} md={4}>
                      <TextField
                        label="Tool Name"
                        fullWidth
                        size="small"
                        value={tool.name}
                        onChange={(e) => updateTool(index, 'name', e.target.value)}
                        placeholder="e.g., web_search"
                      />
                    </Grid>
                    <Grid item xs={12} md={8}>
                      <TextField
                        label="Description"
                        fullWidth
                        size="small"
                        value={tool.description}
                        onChange={(e) => updateTool(index, 'description', e.target.value)}
                        placeholder="What this tool does"
                      />
                    </Grid>
                  </Grid>
                  <IconButton onClick={() => removeTool(index)} size="small" sx={{ ml: 1 }}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>

      {/* Agent Chain (for multi-agent flows) */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Agent Chain (Advanced)
            </Typography>
            <Button startIcon={<AddIcon />} onClick={addAgent} size="small">
              Add Agent
            </Button>
          </Box>

          <Alert severity="info" sx={{ mb: 2 }}>
            Create a multi-agent workflow where multiple specialized agents work together sequentially.
          </Alert>

          {agents.map((agent, index) => (
            <Card key={index} variant="outlined" sx={{ mb: 2, bgcolor: '#f0f9ff' }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Grid container spacing={2} sx={{ flexGrow: 1 }}>
                    <Grid item xs={12} md={4}>
                      <TextField
                        label="Agent Name"
                        fullWidth
                        size="small"
                        value={agent.name}
                        onChange={(e) => updateAgent(index, 'name', e.target.value)}
                        placeholder="e.g., Researcher"
                      />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Role</InputLabel>
                        <Select
                          value={agent.role}
                          onChange={(e) => updateAgent(index, 'role', e.target.value)}
                        >
                          <MenuItem value="researcher">Researcher</MenuItem>
                          <MenuItem value="analyst">Analyst</MenuItem>
                          <MenuItem value="coder">Coder</MenuItem>
                          <MenuItem value="writer">Writer</MenuItem>
                          <MenuItem value="assistant">Assistant</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Chip label={`Step ${index + 1}`} color="primary" size="small" />
                    </Grid>
                  </Grid>
                  <IconButton onClick={() => removeAgent(index)} size="small" sx={{ ml: 1 }}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>

      {/* JSON Preview */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Configuration Preview
            </Typography>
            <Button
              startIcon={<CodeIcon />}
              onClick={() => setShowJSON(!showJSON)}
              size="small"
            >
              {showJSON ? 'Hide JSON' : 'Show JSON'}
            </Button>
          </Box>

          {showJSON && (
            <TextField
              fullWidth
              multiline
              rows={12}
              value={getJSONPreview()}
              InputProps={{
                readOnly: true,
                sx: { fontFamily: 'monospace', fontSize: '0.875rem' }
              }}
            />
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <Box display="flex" justifyContent="flex-end" gap={2}>
        <Button variant="outlined" onClick={() => window.history.back()}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={!flowName.trim()}
        >
          Save Flow
        </Button>
      </Box>
    </Box>
  );
}
