import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  MenuItem,
  Typography,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import { Add, Refresh } from '@mui/icons-material';
import ModelCard from './ModelCard';
import ModelAddModal from './ModelAddModal';
import ModelEditModal from './ModelEditModal';
import ModelTestModal from './ModelTestModal';

/**
 * ModelRegistry Component
 *
 * Main component for managing LLM models
 */
export default function ModelRegistry({ showSnackbar }) {
  const [models, setModels] = useState([]);
  const [filteredModels, setFilteredModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [filterProvider, setFilterProvider] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [models, filterProvider, filterStatus, searchQuery]);

  const fetchModels = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/v1/llm/models', {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }

      const data = await response.json();
      // API returns { object: 'list', data: [...] } or { models: [...] }
      const rawModels = data.data || data.models || [];
      // Normalize fields for ModelCard compatibility
      const normalized = rawModels.map(m => ({
        ...m,
        model_id: m.model_id || m.id || '',
        name: m.display_name || m.name || m.id || '',
        status: m.status || (m.enabled !== false ? 'active' : 'inactive'),
        cost_per_input_token: m.cost_per_input_token ?? (m.pricing?.input ?? 0),
        cost_per_output_token: m.cost_per_output_token ?? (m.pricing?.output ?? 0),
        latency_avg_ms: m.latency_avg_ms ?? m.avg_latency_ms ?? null,
        usage_count: m.usage_count ?? 0,
      }));
      setModels(normalized);
    } catch (err) {
      setError(err.message);
      showSnackbar(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...models];

    if (filterProvider !== 'all') {
      filtered = filtered.filter((m) => m.provider === filterProvider);
    }

    if (filterStatus !== 'all') {
      filtered = filtered.filter((m) => m.status === filterStatus);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          m.name.toLowerCase().includes(query) ||
          m.model_id.toLowerCase().includes(query)
      );
    }

    setFilteredModels(filtered);
  };

  const handleAddModel = async (modelData) => {
    try {
      const response = await fetch('/api/v1/llm/models', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(modelData)
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to add model');
      }

      showSnackbar('Model added successfully', 'success');
      fetchModels();
    } catch (err) {
      showSnackbar(err.message, 'error');
      throw err;
    }
  };

  const handleDeleteModel = (model) => {
    setSelectedModel(model);
    setDeleteModalOpen(true);
  };

  const confirmDeleteModel = async () => {
    if (!selectedModel) return;
    setDeleteLoading(true);
    try {
      const response = await fetch(`/api/v1/llm/models/${selectedModel.model_id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to delete model');
      }

      showSnackbar('Model deleted successfully', 'success');
      setDeleteModalOpen(false);
      setSelectedModel(null);
      fetchModels();
    } catch (err) {
      showSnackbar(err.message, 'error');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleTestModel = async (modelId, prompt) => {
    const response = await fetch(`/api/v1/llm/models/${modelId}/test`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ test_prompt: prompt })
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Test failed');
    }

    return await response.json();
  };

  const handleEditModel = (model) => {
    setSelectedModel(model);
    setEditModalOpen(true);
  };

  const handleSaveModel = async (model, updates) => {
    const modelId = model.model_id || model.id;
    const response = await fetch(`/api/v1/llm/models/${modelId}`, {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to update model');
    }

    showSnackbar('Model updated successfully', 'success');
    fetchModels();
  };

  const handleOpenTest = (model) => {
    setSelectedModel(model);
    setTestModalOpen(true);
  };

  const providers = ['all', ...new Set(models.map(m => m.provider).filter(Boolean))];
  const statuses = ['all', 'active', 'inactive', 'error', 'testing'];

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <TextField
          label="Search Models"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          variant="outlined"
          sx={{ 
            minWidth: 250,
            '& .MuiOutlinedInput-root': {
              '& fieldset': { borderColor: 'rgba(139, 92, 246, 0.5)' },
              '&:hover fieldset': { borderColor: 'rgb(139, 92, 246)' },
              '&.Mui-focused fieldset': { borderColor: 'rgb(139, 92, 246)' }
            },
            '& .MuiOutlinedInput-input': { color: 'rgb(243, 244, 246)' },
            '& .MuiInputLabel-root': { color: 'rgb(243, 232, 255)' },
            '& .MuiInputLabel-root.Mui-focused': { color: 'rgb(139, 92, 246)' }
          }}
        />

        <TextField
          select
          label="Provider"
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
          size="small"
          variant="outlined"
          sx={{ 
            minWidth: 150,
            '& .MuiOutlinedInput-root': {
              '& fieldset': { borderColor: 'rgba(139, 92, 246, 0.5)' },
              '&:hover fieldset': { borderColor: 'rgb(139, 92, 246)' },
              '&.Mui-focused fieldset': { borderColor: 'rgb(139, 92, 246)' }
            },
            '& .MuiOutlinedInput-input': { color: 'rgb(243, 244, 246)' },
            '& .MuiSvgIcon-root': { color: 'rgba(139, 92, 246, 0.5)' },
            '& .MuiInputLabel-root': { color: 'rgb(243, 232, 255)' },
            '& .MuiInputLabel-root.Mui-focused': { color: 'rgb(139, 92, 246)' }
          }}
        >
          {providers.map((p) => (
            <MenuItem key={p} value={p}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </MenuItem>
          ))}
        </TextField>

        <TextField
          select
          label="Status"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          size="small"
          variant="outlined"
          sx={{ 
            minWidth: 150,
            '& .MuiOutlinedInput-root': {
              '& fieldset': { borderColor: 'rgba(139, 92, 246, 0.5)' },
              '&:hover fieldset': { borderColor: 'rgb(139, 92, 246)' },
              '&.Mui-focused fieldset': { borderColor: 'rgb(139, 92, 246)' }
            },
            '& .MuiOutlinedInput-input': { color: 'rgb(243, 244, 246)' },
            '& .MuiSvgIcon-root': { color: 'rgba(139, 92, 246, 0.5)' },
            '& .MuiInputLabel-root': { color: 'rgb(243, 232, 255)' },
            '& .MuiInputLabel-root.Mui-focused': { color: 'rgb(139, 92, 246)' }
          }}
        >
          {statuses.map((s) => (
            <MenuItem key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </MenuItem>
          ))}
        </TextField>

        <Box sx={{ flexGrow: 1 }} />

        <Button
          startIcon={<Refresh />}
          onClick={fetchModels}
          variant="outlined"
          size="small"
        >
          Refresh
        </Button>

        <Button
          startIcon={<Add />}
          onClick={() => setAddModalOpen(true)}
          variant="contained"
          size="small"
        >
          Add Model
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {filteredModels.length === 0 ? (
        <Alert severity="info">
          No models found. Click "Add Model" to get started.
        </Alert>
      ) : (
        <>
          <p className="text-gray-300 text-sm mb-3">
            Showing {filteredModels.length} of {models.length} models
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredModels.map((model) => (
              <div key={model.model_id || model.id}>
                <ModelCard
                  model={model}
                  onEdit={handleEditModel}
                  onDelete={handleDeleteModel}
                  onTest={handleOpenTest}
                />
              </div>
            ))}
          </div>
        </>
      )}

      <ModelAddModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onAdd={handleAddModel}
      />

      <ModelEditModal
        open={editModalOpen}
        model={selectedModel}
        onClose={() => {
          setEditModalOpen(false);
          setSelectedModel(null);
        }}
        onSave={handleSaveModel}
      />

      <ModelTestModal
        open={testModalOpen}
        model={selectedModel}
        onClose={() => {
          setTestModalOpen(false);
          setSelectedModel(null);
        }}
        onTest={handleTestModel}
      />

      <Dialog
        open={deleteModalOpen}
        onClose={() => { setDeleteModalOpen(false); setSelectedModel(null); }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Delete Model</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete <strong>{selectedModel?.name}</strong>? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDeleteModalOpen(false); setSelectedModel(null); }}>
            Cancel
          </Button>
          <Button onClick={confirmDeleteModel} color="error" variant="contained" disabled={deleteLoading}>
            {deleteLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
