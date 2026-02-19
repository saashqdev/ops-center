import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Alert,
  FormControlLabel,
  Switch
} from '@mui/material';

/**
 * ModelEditModal Component
 *
 * Modal for editing an existing model's configuration
 */
export default function ModelEditModal({ open, onClose, onSave, model }) {
  const [formData, setFormData] = useState({
    display_name: '',
    context_length: 4096,
    cost_per_1m_input_tokens: 0,
    cost_per_1m_output_tokens: 0,
    enabled: true
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Populate form when model changes or dialog opens
  useEffect(() => {
    if (model && open) {
      setFormData({
        display_name: model.display_name || model.name || '',
        context_length: model.context_length || 4096,
        cost_per_1m_input_tokens: model.cost_per_1m_input_tokens ?? (model.cost_per_input_token ? model.cost_per_input_token * 1_000_000 : 0),
        cost_per_1m_output_tokens: model.cost_per_1m_output_tokens ?? (model.cost_per_output_token ? model.cost_per_output_token * 1_000_000 : 0),
        enabled: model.enabled !== false && model.status !== 'inactive'
      });
      setError('');
    }
  }, [model, open]);

  if (!open) return null;

  const handleChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value
    });
  };

  const handleSwitchChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.checked
    });
  };

  const handleSubmit = async () => {
    setError('');
    setLoading(true);

    try {
      if (!formData.display_name) {
        throw new Error('Display name is required');
      }

      await onSave(model, {
        display_name: formData.display_name,
        context_length: parseInt(formData.context_length, 10) || 4096,
        cost_per_1m_input_tokens: parseFloat(formData.cost_per_1m_input_tokens) || 0,
        cost_per_1m_output_tokens: parseFloat(formData.cost_per_1m_output_tokens) || 0,
        enabled: formData.enabled
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to update model');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Model: {model?.name || ''}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            label="Display Name"
            value={formData.display_name}
            onChange={handleChange('display_name')}
            required
            fullWidth
            helperText="The name shown in the UI"
          />

          <TextField
            label="Context Length (tokens)"
            value={formData.context_length}
            onChange={handleChange('context_length')}
            type="number"
            fullWidth
            helperText="Maximum context window in tokens"
          />

          <TextField
            label="Cost per 1M Input Tokens ($)"
            value={formData.cost_per_1m_input_tokens}
            onChange={handleChange('cost_per_1m_input_tokens')}
            type="number"
            inputProps={{ step: '0.01' }}
            fullWidth
            helperText="e.g., 0.15 for $0.15 per 1M input tokens (0 = free)"
          />

          <TextField
            label="Cost per 1M Output Tokens ($)"
            value={formData.cost_per_1m_output_tokens}
            onChange={handleChange('cost_per_1m_output_tokens')}
            type="number"
            inputProps={{ step: '0.01' }}
            fullWidth
            helperText="e.g., 0.60 for $0.60 per 1M output tokens (0 = free)"
          />

          <FormControlLabel
            control={
              <Switch
                checked={formData.enabled}
                onChange={handleSwitchChange('enabled')}
              />
            }
            label="Enabled"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {loading ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
