/**
 * Programmatic API Keys Component - Epic 7.0
 * 
 * Manage API keys for programmatic access to the platform
 * - Create API keys with custom names and expiration
 * - View rate limits and quotas
 * - Revoke/delete keys
 * - View usage statistics
 * 
 * Backend: /api/v1/keys (Epic 7.0)
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  KeyIcon,
  PlusIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  ClipboardDocumentIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  CodeBracketIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../components/Toast';

export default function ProgrammaticAPIKeys() {
  const { currentTheme } = useTheme();
  const toast = useToast();
  
  const [loading, setLoading] = useState(true);
  const [apiKeys, setApiKeys] = useState([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyData, setNewKeyData] = useState(null);
  const [creating, setCreating] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    expires_days: '90'
  });

  // Theme classes
  const isDark = currentTheme === 'dark' || currentTheme === 'unicorn';
  const themeClasses = {
    card: currentTheme === 'unicorn'
      ? 'bg-purple-900/50 backdrop-blur-xl border-white/20'
      : currentTheme === 'light'
      ? 'bg-white border-gray-200'
      : 'bg-slate-800 border-slate-700',
    text: isDark ? 'text-slate-100' : 'text-gray-900',
    subtext: isDark ? 'text-slate-400' : 'text-gray-600',
    input: isDark 
      ? 'bg-slate-900 border-slate-600 text-slate-100 placeholder-slate-500'
      : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400',
    button: currentTheme === 'unicorn'
      ? 'bg-purple-600 hover:bg-purple-700'
      : 'bg-blue-600 hover:bg-blue-700',
    modal: isDark
      ? 'bg-slate-800 border-slate-700'
      : 'bg-white border-gray-200'
  };

  useEffect(() => {
    loadAPIKeys();
  }, []);

  const loadAPIKeys = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/keys/');
      if (!response.ok) throw new Error('Failed to load API keys');
      
      const data = await response.json();
      setApiKeys(data.keys || []);
    } catch (error) {
      console.error('Error loading API keys:', error);
      toast?.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const createAPIKey = async () => {
    if (!formData.name.trim()) {
      toast?.error('Please provide a name for the API key');
      return;
    }

    try {
      setCreating(true);
      const response = await fetch('/api/v1/keys/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || null,
          expires_days: formData.expires_days ? parseInt(formData.expires_days) : null
        })
      });

      if (!response.ok) throw new Error('Failed to create API key');
      
      const data = await response.json();
      setNewKeyData(data);
      setFormData({ name: '', description: '', expires_days: '90' });
      toast?.success('API key created successfully');
      loadAPIKeys();
    } catch (error) {
      console.error('Error creating API key:', error);
      toast?.error('Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const revokeAPIKey = async (keyId, name) => {
    if (!confirm(`Revoke API key "${name}"? This action cannot be undone.`)) return;

    try {
      const response = await fetch(`/api/v1/keys/${keyId}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'User revoked via UI' })
      });

      if (!response.ok) throw new Error('Failed to revoke API key');
      
      toast?.success('API key revoked');
      loadAPIKeys();
    } catch (error) {
      console.error('Error revoking API key:', error);
      toast?.error('Failed to revoke API key');
    }
  };

  const deleteAPIKey = async (keyId, name) => {
    if (!confirm(`Permanently delete API key "${name}"? This action cannot be undone.`)) return;

    try {
      const response = await fetch(`/api/v1/keys/${keyId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete API key');
      
      toast?.success('API key deleted');
      loadAPIKeys();
    } catch (error) {
      console.error('Error deleting API key:', error);
      toast?.error('Failed to delete API key');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast?.success('Copied to clipboard');
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const isExpired = (expiresAt) => {
    return expiresAt && new Date(expiresAt) < new Date();
  };

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-3xl font-bold ${themeClasses.text} flex items-center gap-3`}>
              <KeyIcon className="h-8 w-8" />
              Programmatic API Keys
            </h1>
            <p className={`mt-2 ${themeClasses.subtext}`}>
              Create API keys for programmatic access to your account
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className={`${themeClasses.button} text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all`}
          >
            <PlusIcon className="h-5 w-5" />
            Create API Key
          </button>
        </div>
      </div>

      {/* API Keys List */}
      <div className="max-w-6xl mx-auto">
        <div className={`border rounded-xl overflow-hidden ${themeClasses.card}`}>
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className={`mt-4 ${themeClasses.subtext}`}>Loading API keys...</p>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="p-12 text-center">
              <KeyIcon className={`h-16 w-16 mx-auto ${themeClasses.subtext} opacity-50`} />
              <p className={`mt-4 text-lg font-semibold ${themeClasses.text}`}>No API keys yet</p>
              <p className={`mt-2 ${themeClasses.subtext}`}>
                Create your first API key to start making programmatic requests
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                className={`mt-6 ${themeClasses.button} text-white px-6 py-2 rounded-lg`}
              >
                Create Your First Key
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-700">
              {apiKeys.map((key) => (
                <div key={key.id} className="p-6 hover:bg-slate-700/30 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className={`text-lg font-semibold ${themeClasses.text}`}>
                          {key.name}
                        </h3>
                        {key.is_revoked && (
                          <span className="px-2 py-1 bg-red-900/50 text-red-300 text-xs rounded">
                            Revoked
                          </span>
                        )}
                        {!key.is_revoked && isExpired(key.expires_at) && (
                          <span className="px-2 py-1 bg-yellow-900/50 text-yellow-300 text-xs rounded">
                            Expired
                          </span>
                        )}
                        {!key.is_revoked && !isExpired(key.expires_at) && (
                          <span className="px-2 py-1 bg-green-900/50 text-green-300 text-xs rounded">
                            Active
                          </span>
                        )}
                      </div>
                      
                      {key.description && (
                        <p className={`mt-1 ${themeClasses.subtext} text-sm`}>
                          {key.description}
                        </p>
                      )}

                      <div className={`mt-3 flex items-center gap-4 text-sm ${themeClasses.subtext}`}>
                        <div className="flex items-center gap-1">
                          <span className="font-mono">{key.key_prefix}...</span>
                          <button
                            onClick={() => copyToClipboard(key.key_prefix)}
                            className="p-1 hover:text-blue-400"
                          >
                            <ClipboardDocumentIcon className="h-4 w-4" />
                          </button>
                        </div>
                        <div>Created: {formatDate(key.created_at)}</div>
                        {key.expires_at && (
                          <div>Expires: {formatDate(key.expires_at)}</div>
                        )}
                      </div>

                      {/* Rate Limits */}
                      <div className={`mt-3 flex gap-4 text-xs ${themeClasses.subtext}`}>
                        {key.per_minute && <div>⚡ {key.per_minute}/min</div>}
                        {key.per_hour && <div>🕐 {key.per_hour}/hour</div>}
                        {key.per_day && <div>📅 {key.per_day}/day</div>}
                        {key.monthly_quota && <div>📊 {key.monthly_quota.toLocaleString()}/month</div>}
                      </div>
                    </div>

                    <div className="flex gap-2">
                      {!key.is_revoked && (
                        <button
                          onClick={() => revokeAPIKey(key.id, key.name)}
                          className="p-2 text-yellow-400 hover:bg-yellow-900/20 rounded-lg transition-colors"
                          title="Revoke"
                        >
                          <ExclamationCircleIcon className="h-5 w-5" />
                        </button>
                      )}
                      <button
                        onClick={() => deleteAPIKey(key.id, key.name)}
                        className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
            onClick={() => !newKeyData && setShowCreateModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className={`${themeClasses.modal} border rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto`}
            >
              {newKeyData ? (
                // Success - Show the key
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className={`text-2xl font-bold ${themeClasses.text} flex items-center gap-2`}>
                      <CheckCircleIcon className="h-7 w-7 text-green-500" />
                      API Key Created
                    </h2>
                    <button
                      onClick={() => {
                        setNewKeyData(null);
                        setShowCreateModal(false);
                      }}
                      className={`p-1 ${themeClasses.subtext} hover:text-red-400`}
                    >
                      <XMarkIcon className="h-6 w-6" />
                    </button>
                  </div>

                  <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4 mb-6">
                    <p className="text-yellow-300 text-sm font-semibold flex items-center gap-2">
                      <ExclamationCircleIcon className="h-5 w-5" />
                      Save this key now - you won't be able to see it again!
                    </p>
                  </div>

                  <div className={`${themeClasses.input} p-4 rounded-lg mb-4`}>
                    <p className={`text-xs ${themeClasses.subtext} mb-2`}>API Key</p>
                    <div className="flex items-center gap-2">
                      <code className={`flex-1 text-sm ${themeClasses.text} font-mono break-all`}>
                        {newKeyData.api_key}
                      </code>
                      <button
                        onClick={() => copyToClipboard(newKeyData.api_key)}
                        className={`${themeClasses.button} text-white p-2 rounded-lg`}
                      >
                        <ClipboardDocumentIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>

                  <div className={`${themeClasses.card} border rounded-lg p-4 space-y-2 text-sm`}>
                    <div className="flex justify-between">
                      <span className={themeClasses.subtext}>Name:</span>
                      <span className={themeClasses.text}>{newKeyData.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className={themeClasses.subtext}>Key ID:</span>
                      <span className={`${themeClasses.text} font-mono`}>{newKeyData.key_prefix}...</span>
                    </div>
                    {newKeyData.expires_at && (
                      <div className="flex justify-between">
                        <span className={themeClasses.subtext}>Expires:</span>
                        <span className={themeClasses.text}>{formatDate(newKeyData.expires_at)}</span>
                      </div>
                    )}
                  </div>

                  <div className="mt-6 bg-blue-900/20 border border-blue-600/30 rounded-lg p-4">
                    <p className={`text-sm ${themeClasses.text} mb-2 font-semibold`}>Usage Example (cURL):</p>
                    <pre className={`${themeClasses.input} p-3 rounded text-xs overflow-x-auto`}>
{`curl -H "Authorization: Bearer ${newKeyData.api_key}" \\
     https://kubeworkz.io/api/v1/your-endpoint`}
                    </pre>
                  </div>

                  <button
                    onClick={() => {
                      setNewKeyData(null);
                      setShowCreateModal(false);
                    }}
                    className={`mt-6 w-full ${themeClasses.button} text-white py-2 rounded-lg`}
                  >
                    Done
                  </button>
                </div>
              ) : (
                // Create Form
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <h2 className={`text-2xl font-bold ${themeClasses.text}`}>
                      Create API Key
                    </h2>
                    <button
                      onClick={() => setShowCreateModal(false)}
                      className={`p-1 ${themeClasses.subtext} hover:text-red-400`}
                    >
                      <XMarkIcon className="h-6 w-6" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className={`block text-sm font-medium ${themeClasses.text} mb-2`}>
                        Name *
                      </label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder="Production API Key"
                        className={`w-full ${themeClasses.input} border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none`}
                      />
                    </div>

                    <div>
                      <label className={`block text-sm font-medium ${themeClasses.text} mb-2`}>
                        Description (optional)
                      </label>
                      <textarea
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        placeholder="Used for CI/CD pipeline"
                        rows={3}
                        className={`w-full ${themeClasses.input} border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none`}
                      />
                    </div>

                    <div>
                      <label className={`block text-sm font-medium ${themeClasses.text} mb-2`}>
                        Expiration
                      </label>
                      <select
                        value={formData.expires_days}
                        onChange={(e) => setFormData({ ...formData, expires_days: e.target.value })}
                        className={`w-full ${themeClasses.input} border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none`}
                      >
                        <option value="30">30 days</option>
                        <option value="90">90 days</option>
                        <option value="180">180 days</option>
                        <option value="365">1 year</option>
                        <option value="">Never</option>
                      </select>
                    </div>
                  </div>

                  <div className={`mt-6 ${themeClasses.card} border rounded-lg p-4`}>
                    <p className={`text-sm ${themeClasses.subtext}`}>
                      <ShieldCheckIcon className="h-5 w-5 inline mr-2" />
                      Your API key will be shown only once. Make sure to copy and store it securely.
                    </p>
                  </div>

                  <div className="mt-6 flex gap-3">
                    <button
                      onClick={() => setShowCreateModal(false)}
                      className={`flex-1 ${themeClasses.input} border py-2 rounded-lg hover:bg-slate-700/50 transition-colors`}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={createAPIKey}
                      disabled={creating || !formData.name.trim()}
                      className={`flex-1 ${themeClasses.button} text-white py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {creating ? 'Creating...' : 'Create Key'}
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
