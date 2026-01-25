import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  CheckIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
  EyeIcon,
  EyeSlashIcon,
  CodeBracketIcon,
  BoltIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';

export default function TierFeatureManagement() {
  const { theme, currentTheme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [tiers, setTiers] = useState([]);
  const [selectedTier, setSelectedTier] = useState(null);
  const [features, setFeatures] = useState([]);
  const [showFeatureModal, setShowFeatureModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Feature definitions (predefined feature flags)
  const featureDefinitions = [
    // Services
    { key: 'chat_access', name: 'Open-WebUI Chat', category: 'services', type: 'boolean', description: 'Access to chat interface' },
    { key: 'search_enabled', name: 'Center-Deep Search', category: 'services', type: 'boolean', description: 'Search functionality' },
    { key: 'tts_enabled', name: 'Text-to-Speech (Orator)', category: 'services', type: 'boolean', description: 'TTS service access' },
    { key: 'stt_enabled', name: 'Speech-to-Text (Amanuensis)', category: 'services', type: 'boolean', description: 'STT service access' },
    { key: 'brigade_access', name: 'Brigade AI Orchestration', category: 'services', type: 'boolean', description: 'Brigade service' },
    { key: 'litellm_access', name: 'LiteLLM Proxy', category: 'services', type: 'boolean', description: 'LiteLLM proxy access' },
    { key: 'vllm_access', name: 'vLLM Engine', category: 'services', type: 'boolean', description: 'vLLM model serving' },
    { key: 'embeddings_access', name: 'Embeddings Service', category: 'services', type: 'boolean', description: 'Vector embeddings' },
    { key: 'forgejo_access', name: 'Forgejo Git', category: 'services', type: 'boolean', description: 'Git repository access' },
    { key: 'magicdeck_access', name: 'MagicDeck Presentations', category: 'services', type: 'boolean', description: 'Presentation builder' },
    
    // Models
    { key: 'gpt4_enabled', name: 'GPT-4 Models', category: 'models', type: 'boolean', description: 'OpenAI GPT-4 access' },
    { key: 'claude_enabled', name: 'Claude Models', category: 'models', type: 'boolean', description: 'Anthropic Claude access' },
    { key: 'gemini_enabled', name: 'Gemini Models', category: 'models', type: 'boolean', description: 'Google Gemini access' },
    { key: 'llama_enabled', name: 'Llama Models', category: 'models', type: 'boolean', description: 'Meta Llama access' },
    { key: 'mistral_enabled', name: 'Mistral Models', category: 'models', type: 'boolean', description: 'Mistral AI access' },
    
    // Features
    { key: 'api_access', name: 'API Access', category: 'features', type: 'boolean', description: 'REST API access' },
    { key: 'webhooks_enabled', name: 'Webhooks', category: 'features', type: 'boolean', description: 'Webhook notifications' },
    { key: 'custom_branding', name: 'Custom Branding', category: 'features', type: 'boolean', description: 'White-label branding' },
    { key: 'sso_enabled', name: 'SSO Integration', category: 'features', type: 'boolean', description: 'Single sign-on' },
    { key: 'audit_logs', name: 'Audit Logs', category: 'features', type: 'boolean', description: 'Detailed audit logging' },
    { key: 'advanced_analytics', name: 'Advanced Analytics', category: 'features', type: 'boolean', description: 'In-depth analytics' },
    { key: 'team_management', name: 'Team Management', category: 'features', type: 'boolean', description: 'Multi-user teams' },
    
    // Limits
    { key: 'max_file_upload_mb', name: 'Max File Upload (MB)', category: 'limits', type: 'integer', description: 'Maximum file size' },
    { key: 'max_concurrent_requests', name: 'Max Concurrent Requests', category: 'limits', type: 'integer', description: 'Request concurrency limit' },
    { key: 'rate_limit_per_minute', name: 'Rate Limit (per minute)', category: 'limits', type: 'integer', description: 'API rate limiting' },
    
    // Support
    { key: 'support_level', name: 'Support Level', category: 'support', type: 'string', description: 'Support tier (community/standard/priority/dedicated)' },
    { key: 'sla_guarantee', name: 'SLA Guarantee', category: 'support', type: 'boolean', description: 'Uptime SLA' },
    { key: 'dedicated_support', name: 'Dedicated Support', category: 'support', type: 'boolean', description: 'Dedicated support rep' }
  ];

  const [featureForm, setFeatureForm] = useState({
    feature_key: '',
    feature_value: '',
    enabled: true
  });

  useEffect(() => {
    loadTiers();
  }, []);

  useEffect(() => {
    if (selectedTier) {
      loadTierFeatures(selectedTier.id);
    }
  }, [selectedTier]);

  const loadTiers = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/admin/tiers?active_only=true', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setTiers(data);
        if (data.length > 0 && !selectedTier) {
          setSelectedTier(data[0]);
        }
      }
    } catch (error) {
      console.error('Error loading tiers:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTierFeatures = async (tierId) => {
    try {
      const response = await fetch(`/api/v1/admin/tiers/${tierId}/features`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setFeatures(data);
      }
    } catch (error) {
      console.error('Error loading features:', error);
    }
  };

  const handleSaveFeatures = async () => {
    if (!selectedTier) return;

    setSaving(true);
    try {
      const response = await fetch(`/api/v1/admin/tiers/${selectedTier.id}/features`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ features })
      });

      if (response.ok) {
        alert('Features saved successfully!');
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to save features'}`);
      }
    } catch (error) {
      console.error('Error saving features:', error);
      alert('Failed to save features');
    } finally {
      setSaving(false);
    }
  };

  const addFeature = (featureDef) => {
    const exists = features.find(f => f.feature_key === featureDef.key);
    if (exists) {
      alert('Feature already added to this tier');
      return;
    }

    const defaultValue = featureDef.type === 'boolean' ? 'true' : 
                         featureDef.type === 'integer' ? '0' : '';

    setFeatures([
      ...features,
      {
        feature_key: featureDef.key,
        feature_value: defaultValue,
        enabled: true
      }
    ]);
  };

  const removeFeature = (featureKey) => {
    setFeatures(features.filter(f => f.feature_key !== featureKey));
  };

  const updateFeature = (featureKey, updates) => {
    setFeatures(features.map(f => 
      f.feature_key === featureKey ? { ...f, ...updates } : f
    ));
  };

  const toggleFeature = (featureKey) => {
    setFeatures(features.map(f => 
      f.feature_key === featureKey ? { ...f, enabled: !f.enabled } : f
    ));
  };

  const getFeatureDefinition = (key) => {
    return featureDefinitions.find(f => f.key === key);
  };

  const groupedDefinitions = featureDefinitions.reduce((acc, feature) => {
    if (!acc[feature.category]) {
      acc[feature.category] = [];
    }
    acc[feature.category].push(feature);
    return acc;
  }, {});

  const filteredFeatures = features.filter(f => {
    if (!searchQuery) return true;
    const def = getFeatureDefinition(f.feature_key);
    const query = searchQuery.toLowerCase();
    return f.feature_key.toLowerCase().includes(query) ||
           def?.name.toLowerCase().includes(query);
  });

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'services': return SparklesIcon;
      case 'models': return CodeBracketIcon;
      case 'features': return BoltIcon;
      case 'limits': return AdjustmentsHorizontalIcon;
      case 'support': return CheckIcon;
      default: return AdjustmentsHorizontalIcon;
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case 'services': return 'text-blue-500';
      case 'models': return 'text-purple-500';
      case 'features': return 'text-green-500';
      case 'limits': return 'text-orange-500';
      case 'support': return 'text-pink-500';
      default: return 'text-gray-500';
    }
  };

  // Add Feature Modal
  const AddFeatureModal = () => (
    <AnimatePresence>
      {showFeatureModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
          onClick={() => setShowFeatureModal(false)}
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-y-auto"
            style={{ backgroundColor: currentTheme.cardBackground }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold" style={{ color: currentTheme.text }}>
                  ➕ Add Feature Flag
                </h2>
                <button
                  onClick={() => setShowFeatureModal(false)}
                  className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                >
                  <XMarkIcon className="w-6 h-6" style={{ color: currentTheme.textSecondary }} />
                </button>
              </div>

              {Object.entries(groupedDefinitions).map(([category, defs]) => {
                const Icon = getCategoryIcon(category);
                const colorClass = getCategoryColor(category);

                return (
                  <div key={category} className="mb-6">
                    <h3 className={`text-lg font-semibold mb-3 flex items-center space-x-2 ${colorClass}`}>
                      <Icon className="w-6 h-6" />
                      <span className="capitalize">{category}</span>
                    </h3>
                    <div className="grid grid-cols-2 gap-3">
                      {defs.map(def => {
                        const exists = features.find(f => f.feature_key === def.key);
                        return (
                          <button
                            key={def.key}
                            onClick={() => !exists && addFeature(def)}
                            disabled={exists}
                            className={`p-3 rounded-lg border text-left transition-all ${
                              exists 
                                ? 'opacity-50 cursor-not-allowed'
                                : 'hover:shadow-md hover:border-blue-500'
                            }`}
                            style={{
                              backgroundColor: currentTheme.inputBackground,
                              borderColor: exists ? currentTheme.border : currentTheme.border
                            }}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="font-semibold text-sm mb-1" style={{ color: currentTheme.text }}>
                                  {def.name}
                                </p>
                                <p className="text-xs mb-2" style={{ color: currentTheme.textSecondary }}>
                                  {def.description}
                                </p>
                                <code className="text-xs px-2 py-1 rounded bg-gray-200 dark:bg-gray-700">
                                  {def.key}
                                </code>
                              </div>
                              {exists && (
                                <CheckIcon className="w-5 h-5 text-green-500 ml-2 flex-shrink-0" />
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: currentTheme.background }}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2" style={{ color: currentTheme.text }}>
            🎛️ Feature Flag Management
          </h1>
          <p style={{ color: currentTheme.textSecondary }}>
            Configure feature flags for each subscription tier
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-12 gap-6">
            {/* Tier Selector Sidebar */}
            <div className="col-span-3">
              <div className="rounded-lg shadow-lg p-4" style={{ backgroundColor: currentTheme.cardBackground }}>
                <h3 className="text-lg font-bold mb-4" style={{ color: currentTheme.text }}>
                  Select Tier
                </h3>
                <div className="space-y-2">
                  {tiers.map(tier => (
                    <button
                      key={tier.id}
                      onClick={() => setSelectedTier(tier)}
                      className={`w-full p-3 rounded-lg text-left transition-all ${
                        selectedTier?.id === tier.id
                          ? 'bg-blue-500 text-white shadow-md'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                      style={selectedTier?.id !== tier.id ? { color: currentTheme.text } : {}}
                    >
                      <p className="font-semibold">{tier.tier_name}</p>
                      <p className={`text-xs ${selectedTier?.id === tier.id ? 'text-white' : ''}`}
                         style={selectedTier?.id !== tier.id ? { color: currentTheme.textSecondary } : {}}>
                        {tier.tier_code}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Features Panel */}
            <div className="col-span-9">
              {selectedTier && (
                <>
                  {/* Toolbar */}
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex-1 relative mr-4">
                      <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2" style={{ color: currentTheme.textSecondary }} />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search features..."
                        className="w-full pl-10 pr-4 py-2 rounded-lg border"
                        style={{
                          backgroundColor: currentTheme.inputBackground,
                          borderColor: currentTheme.border,
                          color: currentTheme.text
                        }}
                      />
                    </div>
                    <button
                      onClick={() => setShowFeatureModal(true)}
                      className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 flex items-center space-x-2"
                    >
                      <PlusIcon className="w-5 h-5" />
                      <span>Add Feature</span>
                    </button>
                    <button
                      onClick={handleSaveFeatures}
                      disabled={saving}
                      className="ml-3 px-6 py-2 rounded-lg bg-green-500 text-white hover:bg-green-600 disabled:opacity-50 flex items-center space-x-2"
                    >
                      {saving ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          <span>Saving...</span>
                        </>
                      ) : (
                        <>
                          <CheckIcon className="w-5 h-5" />
                          <span>Save Changes</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Features List */}
                  <div className="rounded-lg shadow-lg overflow-hidden" style={{ backgroundColor: currentTheme.cardBackground }}>
                    {filteredFeatures.length === 0 ? (
                      <div className="text-center py-20">
                        <AdjustmentsHorizontalIcon className="w-16 h-16 mx-auto mb-4 opacity-30" style={{ color: currentTheme.textSecondary }} />
                        <p className="text-xl mb-2" style={{ color: currentTheme.textSecondary }}>
                          No features configured
                        </p>
                        <button
                          onClick={() => setShowFeatureModal(true)}
                          className="text-blue-500 hover:underline"
                        >
                          Add your first feature →
                        </button>
                      </div>
                    ) : (
                      <table className="w-full">
                        <thead className="bg-gray-100 dark:bg-gray-800">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Feature</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Category</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Value</th>
                            <th className="px-4 py-3 text-center text-sm font-semibold" style={{ color: currentTheme.text }}>Enabled</th>
                            <th className="px-4 py-3 text-center text-sm font-semibold" style={{ color: currentTheme.text }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredFeatures.map((feature, idx) => {
                            const def = getFeatureDefinition(feature.feature_key);
                            const Icon = def ? getCategoryIcon(def.category) : AdjustmentsHorizontalIcon;
                            const colorClass = def ? getCategoryColor(def.category) : 'text-gray-500';

                            return (
                              <tr key={feature.feature_key} className="border-t" style={{ borderColor: currentTheme.border }}>
                                <td className="px-4 py-3">
                                  <div className="flex items-center space-x-2">
                                    <Icon className={`w-5 h-5 ${colorClass}`} />
                                    <div>
                                      <p className="font-semibold text-sm" style={{ color: currentTheme.text }}>
                                        {def?.name || feature.feature_key}
                                      </p>
                                      <code className="text-xs" style={{ color: currentTheme.textSecondary }}>
                                        {feature.feature_key}
                                      </code>
                                    </div>
                                  </div>
                                </td>
                                <td className="px-4 py-3">
                                  {def && (
                                    <span className={`px-2 py-1 rounded text-xs ${colorClass} bg-opacity-10`}>
                                      {def.category}
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-3">
                                  {def?.type === 'boolean' ? (
                                    <select
                                      value={feature.feature_value}
                                      onChange={(e) => updateFeature(feature.feature_key, { feature_value: e.target.value })}
                                      className="px-2 py-1 rounded border text-sm"
                                      style={{
                                        backgroundColor: currentTheme.inputBackground,
                                        borderColor: currentTheme.border,
                                        color: currentTheme.text
                                      }}
                                    >
                                      <option value="true">True</option>
                                      <option value="false">False</option>
                                    </select>
                                  ) : (
                                    <input
                                      type="text"
                                      value={feature.feature_value || ''}
                                      onChange={(e) => updateFeature(feature.feature_key, { feature_value: e.target.value })}
                                      className="px-2 py-1 rounded border text-sm w-full"
                                      style={{
                                        backgroundColor: currentTheme.inputBackground,
                                        borderColor: currentTheme.border,
                                        color: currentTheme.text
                                      }}
                                    />
                                  )}
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <button
                                    onClick={() => toggleFeature(feature.feature_key)}
                                    className={`p-2 rounded-full transition-colors ${
                                      feature.enabled
                                        ? 'bg-green-500 text-white'
                                        : 'bg-gray-300 dark:bg-gray-600'
                                    }`}
                                  >
                                    {feature.enabled ? (
                                      <EyeIcon className="w-5 h-5" />
                                    ) : (
                                      <EyeSlashIcon className="w-5 h-5" />
                                    )}
                                  </button>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <button
                                    onClick={() => removeFeature(feature.feature_key)}
                                    className="p-2 rounded hover:bg-red-100 dark:hover:bg-red-900 transition-colors"
                                  >
                                    <TrashIcon className="w-5 h-5 text-red-500" />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Summary */}
                  <div className="mt-6 grid grid-cols-3 gap-4">
                    <div className="rounded-lg shadow p-4" style={{ backgroundColor: currentTheme.cardBackground }}>
                      <p className="text-sm mb-1" style={{ color: currentTheme.textSecondary }}>Total Features</p>
                      <p className="text-2xl font-bold" style={{ color: currentTheme.text }}>{features.length}</p>
                    </div>
                    <div className="rounded-lg shadow p-4" style={{ backgroundColor: currentTheme.cardBackground }}>
                      <p className="text-sm mb-1" style={{ color: currentTheme.textSecondary }}>Enabled</p>
                      <p className="text-2xl font-bold text-green-500">
                        {features.filter(f => f.enabled).length}
                      </p>
                    </div>
                    <div className="rounded-lg shadow p-4" style={{ backgroundColor: currentTheme.cardBackground }}>
                      <p className="text-sm mb-1" style={{ color: currentTheme.textSecondary }}>Disabled</p>
                      <p className="text-2xl font-bold text-red-500">
                        {features.filter(f => !f.enabled).length}
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        <AddFeatureModal />
      </div>
    </div>
  );
}
