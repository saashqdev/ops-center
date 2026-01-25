import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../contexts/ThemeContext';
import { useToast } from '../components/Toast';
import {
  Brain,
  Zap,
  DollarSign,
  Activity,
  Settings,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  TrendingUp,
  TrendingDown,
  PieChart,
  BarChart3,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  Edit,
  Play,
  Key,
  Shield,
  Sparkles,
  Target,
  Clock,
  Gauge,
  Save,
  Download,
  Filter,
  ChevronDown,
  ChevronUp,
  Info
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip as ChartTooltip,
  Legend
} from 'chart.js';
import { Line, Pie, Bar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend
);

// Power Level Configurations
const POWER_LEVELS = {
  ECO: {
    name: 'ECO',
    color: 'emerald',
    icon: Zap,
    description: 'Free & fast models for casual use',
    costRange: '$0.00 - $0.10 per 1M tokens',
    examples: ['Groq Mixtral', 'Local Qwen', 'Llama 405B']
  },
  BALANCED: {
    name: 'BALANCED',
    color: 'blue',
    icon: Target,
    description: 'Best value for most tasks',
    costRange: '$0.10 - $3.00 per 1M tokens',
    examples: ['GPT-4o Mini', 'Claude Haiku', 'Qwen 72B']
  },
  PRECISION: {
    name: 'PRECISION',
    color: 'purple',
    icon: Sparkles,
    description: 'Premium quality for critical work',
    costRange: '$3.00 - $75.00 per 1M tokens',
    examples: ['Claude Sonnet', 'GPT-4o', 'O1 Preview']
  }
};

// Provider status colors
const getProviderStatusColor = (isHealthy) => {
  if (isHealthy) return 'green';
  return 'red';
};

// ============================================================================
// Components
// ============================================================================

// Statistics Card
const StatCard = ({ title, value, subtitle, icon: Icon, color, trend, loading }) => {
  const { theme } = useTheme();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`${theme.card} rounded-xl p-6 border border-${color}-500/20 hover:border-${color}-500/40 transition-all`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon className={`h-5 w-5 text-${color}-400`} />
            <p className={`text-sm ${theme.text.secondary}`}>{title}</p>
          </div>
          
          {loading ? (
            <div className="animate-pulse">
              <div className={`h-8 w-24 ${theme.bg.secondary} rounded`}></div>
            </div>
          ) : (
            <>
              <h3 className={`text-3xl font-bold ${theme.text.primary} mb-1`}>{value}</h3>
              {subtitle && (
                <p className={`text-xs ${theme.text.tertiary}`}>{subtitle}</p>
              )}
              {trend !== undefined && (
                <div className={`flex items-center gap-1 mt-2 text-sm ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {trend >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  <span>{Math.abs(trend)}% vs last month</span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// Provider Card
const ProviderCard = ({ provider, onAddKey, onTest, onToggle, isAdmin }) => {
  const { theme } = useTheme();
  const [isExpanded, setIsExpanded] = useState(false);
  
  const statusColor = provider.is_enabled ? 'green' : 'gray';
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`${theme.card} rounded-xl border border-${statusColor}-500/20 overflow-hidden`}
    >
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br from-${statusColor}-500/20 to-${statusColor}-600/20 flex items-center justify-center`}>
              <Brain className={`h-6 w-6 text-${statusColor}-400`} />
            </div>
            <div>
              <h3 className={`text-lg font-semibold ${theme.text.primary}`}>{provider.name}</h3>
              <p className={`text-sm ${theme.text.tertiary}`}>{provider.provider_type}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className={`px-3 py-1 rounded-full text-xs font-medium ${
              provider.is_enabled 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              {provider.is_enabled ? 'Active' : 'Disabled'}
            </div>
            <div className={`px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400`}>
              Priority: {provider.priority}
            </div>
          </div>
        </div>
        
        {/* API Endpoint */}
        <div className="mb-4">
          <p className={`text-xs ${theme.text.tertiary} mb-1`}>API Endpoint</p>
          <code className={`text-sm ${theme.text.secondary} ${theme.bg.secondary} px-2 py-1 rounded`}>
            {provider.api_endpoint}
          </code>
        </div>
        
        {/* BYOK Status */}
        {provider.requires_byok && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Key className="h-4 w-4 text-yellow-400" />
              <p className={`text-sm ${theme.text.secondary}`}>
                Requires BYOK (Bring Your Own Key)
              </p>
            </div>
            {!provider.user_has_key && (
              <button
                onClick={onAddKey}
                className="w-full py-2 px-4 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Add API Key
              </button>
            )}
            {provider.user_has_key && (
              <div className="flex items-center gap-2 text-sm text-green-400">
                <CheckCircle className="h-4 w-4" />
                <span>API Key Configured</span>
              </div>
            )}
          </div>
        )}
        
        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={onTest}
            disabled={provider.requires_byok && !provider.user_has_key}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
              provider.requires_byok && !provider.user_has_key
                ? 'bg-gray-500/20 text-gray-500 cursor-not-allowed'
                : 'bg-purple-500/20 hover:bg-purple-500/30 text-purple-400'
            }`}
          >
            <Play className="h-4 w-4" />
            Test Provider
          </button>
          
          {isAdmin && (
            <button
              onClick={onToggle}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                provider.is_enabled
                  ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
                  : 'bg-green-500/20 hover:bg-green-500/30 text-green-400'
              }`}
            >
              {provider.is_enabled ? 'Disable' : 'Enable'}
            </button>
          )}
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${theme.bg.secondary} ${theme.text.secondary} hover:${theme.bg.tertiary}`}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>
      
      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className={`border-t ${theme.border} px-6 py-4`}
          >
            <h4 className={`text-sm font-semibold ${theme.text.primary} mb-2`}>Configuration</h4>
            <pre className={`text-xs ${theme.text.tertiary} ${theme.bg.secondary} p-3 rounded overflow-auto`}>
              {JSON.stringify(provider.config, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Model Card
const ModelCard = ({ model }) => {
  const { theme } = useTheme();
  const powerLevel = POWER_LEVELS[model.power_level] || POWER_LEVELS.BALANCED;
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`${theme.card} rounded-lg p-4 border border-${powerLevel.color}-500/20 hover:border-${powerLevel.color}-500/40 transition-all`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h4 className={`font-semibold ${theme.text.primary}`}>{model.model_name}</h4>
            <div className={`px-2 py-0.5 rounded text-xs font-medium bg-${powerLevel.color}-500/20 text-${powerLevel.color}-400`}>
              {model.power_level}
            </div>
          </div>
          <p className={`text-xs ${theme.text.tertiary}`}>{model.provider_name}</p>
        </div>
        
        {model.is_enabled ? (
          <CheckCircle className="h-5 w-5 text-green-400" />
        ) : (
          <XCircle className="h-5 w-5 text-gray-500" />
        )}
      </div>
      
      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div>
          <p className={`text-xs ${theme.text.tertiary} mb-1`}>Cost (1M)</p>
          <p className={`text-sm font-medium ${theme.text.secondary}`}>
            ${parseFloat(model.input_cost_per_1m).toFixed(2)}
          </p>
        </div>
        <div>
          <p className={`text-xs ${theme.text.tertiary} mb-1`}>Latency</p>
          <p className={`text-sm font-medium ${theme.text.secondary}`}>
            {model.avg_latency_ms}ms
          </p>
        </div>
        <div>
          <p className={`text-xs ${theme.text.tertiary} mb-1`}>Quality</p>
          <p className={`text-sm font-medium ${theme.text.secondary}`}>
            {parseFloat(model.quality_score).toFixed(1)}/10
          </p>
        </div>
      </div>
      
      {/* Capabilities */}
      <div className="flex flex-wrap gap-1">
        {model.supports_streaming && (
          <span className={`px-2 py-0.5 rounded text-xs ${theme.bg.secondary} ${theme.text.tertiary}`}>
            Streaming
          </span>
        )}
        <span className={`px-2 py-0.5 rounded text-xs ${theme.bg.secondary} ${theme.text.tertiary}`}>
          {(model.max_context_tokens / 1000).toFixed(0)}K context
        </span>
      </div>
    </motion.div>
  );
};

// Power Level Selector
const PowerLevelSelector = ({ selected, onChange }) => {
  const { theme } = useTheme();
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {Object.values(POWER_LEVELS).map((level) => {
        const Icon = level.icon;
        const isSelected = selected === level.name;
        
        return (
          <motion.button
            key={level.name}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onChange(level.name)}
            className={`${theme.card} rounded-xl p-6 border-2 transition-all text-left ${
              isSelected
                ? `border-${level.color}-500 bg-${level.color}-500/10`
                : `border-${level.color}-500/20 hover:border-${level.color}-500/40`
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-10 h-10 rounded-lg bg-${level.color}-500/20 flex items-center justify-center`}>
                <Icon className={`h-5 w-5 text-${level.color}-400`} />
              </div>
              <div>
                <h3 className={`font-semibold ${theme.text.primary}`}>{level.name}</h3>
                <p className={`text-xs text-${level.color}-400`}>{level.costRange}</p>
              </div>
            </div>
            
            <p className={`text-sm ${theme.text.secondary} mb-2`}>{level.description}</p>
            
            <div className="flex flex-wrap gap-1">
              {level.examples.slice(0, 2).map((example, idx) => (
                <span key={idx} className={`px-2 py-1 rounded text-xs ${theme.bg.secondary} ${theme.text.tertiary}`}>
                  {example}
                </span>
              ))}
            </div>
          </motion.button>
        );
      })}
    </div>
  );
};

// Routing Configuration Panel
const RoutingConfigPanel = ({ config, onChange, onSave }) => {
  const { theme } = useTheme();
  const [localConfig, setLocalConfig] = useState(config);
  
  useEffect(() => {
    setLocalConfig(config);
  }, [config]);
  
  const handleSliderChange = (key, value) => {
    setLocalConfig(prev => ({ ...prev, [key]: value }));
  };
  
  const handleSave = () => {
    onChange(localConfig);
    onSave();
  };
  
  const totalWeight = (localConfig.cost_weight || 0) + (localConfig.latency_weight || 0) + (localConfig.quality_weight || 0);
  const isValidWeight = Math.abs(totalWeight - 1.0) < 0.01;
  
  return (
    <div className={`${theme.card} rounded-xl p-6 border ${theme.border}`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-blue-400" />
          <h3 className={`text-lg font-semibold ${theme.text.primary}`}>Routing Configuration</h3>
        </div>
        
        <button
          onClick={handleSave}
          disabled={!isValidWeight}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            isValidWeight
              ? 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400'
              : 'bg-gray-500/20 text-gray-500 cursor-not-allowed'
          }`}
        >
          <Save className="h-4 w-4" />
          Save Changes
        </button>
      </div>
      
      {/* Weight Sliders */}
      <div className="space-y-6">
        {/* Cost Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className={`text-sm font-medium ${theme.text.secondary}`}>Cost Weight</label>
            <span className="text-sm font-mono text-blue-400">{(localConfig.cost_weight || 0).toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={localConfig.cost_weight || 0.4}
            onChange={(e) => handleSliderChange('cost_weight', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <p className={`text-xs ${theme.text.tertiary} mt-1`}>
            Higher values prioritize cheaper models
          </p>
        </div>
        
        {/* Latency Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className={`text-sm font-medium ${theme.text.secondary}`}>Latency Weight</label>
            <span className="text-sm font-mono text-blue-400">{(localConfig.latency_weight || 0).toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={localConfig.latency_weight || 0.4}
            onChange={(e) => handleSliderChange('latency_weight', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <p className={`text-xs ${theme.text.tertiary} mt-1`}>
            Higher values prioritize faster models
          </p>
        </div>
        
        {/* Quality Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className={`text-sm font-medium ${theme.text.secondary}`}>Quality Weight</label>
            <span className="text-sm font-mono text-blue-400">{(localConfig.quality_weight || 0).toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={localConfig.quality_weight || 0.2}
            onChange={(e) => handleSliderChange('quality_weight', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <p className={`text-xs ${theme.text.tertiary} mt-1`}>
            Higher values prioritize higher quality models
          </p>
        </div>
        
        {/* Total Weight Validation */}
        <div className={`p-4 rounded-lg ${isValidWeight ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
          <div className="flex items-center gap-2">
            {isValidWeight ? (
              <CheckCircle className="h-5 w-5 text-green-400" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-400" />
            )}
            <p className={`text-sm ${isValidWeight ? 'text-green-400' : 'text-red-400'}`}>
              Total Weight: {totalWeight.toFixed(2)} {isValidWeight ? '✓' : '(must equal 1.00)'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// BYOK Modal
const BYOKModal = ({ isOpen, onClose, provider, onSave }) => {
  const { theme } = useTheme();
  const toast = useToast();
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  
  if (!isOpen) return null;
  
  const handleSave = async () => {
    if (!apiKey.trim()) {
      toast.error('Please enter an API key');
      return;
    }
    
    setSaving(true);
    try {
      const response = await fetch('/api/v2/llm/byok', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          provider_id: provider.id,
          api_key: apiKey
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save API key');
      }
      
      toast.success('API key saved successfully');
      onSave();
      setApiKey('');
      onClose();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSaving(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`${theme.card} rounded-xl p-6 max-w-md w-full border ${theme.border}`}
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-blue-400" />
            <h3 className={`text-lg font-semibold ${theme.text.primary}`}>
              Add API Key for {provider?.name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className={`p-2 rounded-lg ${theme.bg.secondary} ${theme.text.secondary} hover:${theme.bg.tertiary}`}
          >
            <XCircle className="h-5 w-5" />
          </button>
        </div>
        
        <div className="mb-6">
          <div className={`p-4 rounded-lg bg-blue-500/10 border border-blue-500/20 mb-4`}>
            <div className="flex items-start gap-2">
              <Shield className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className={`text-sm text-blue-400 font-medium mb-1`}>Secure Encryption</p>
                <p className={`text-xs ${theme.text.tertiary}`}>
                  Your API key will be encrypted using Fernet symmetric encryption before storage. We never store keys in plain text.
                </p>
              </div>
            </div>
          </div>
          
          <label className={`text-sm font-medium ${theme.text.secondary} mb-2 block`}>
            API Key
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className={`w-full px-4 py-3 pr-12 rounded-lg ${theme.bg.secondary} ${theme.text.primary} border ${theme.border} focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
            />
            <button
              onClick={() => setShowKey(!showKey)}
              className={`absolute right-3 top-1/2 -translate-y-1/2 p-1 ${theme.text.tertiary} hover:${theme.text.secondary}`}
            >
              {showKey ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className={`flex-1 py-2 px-4 rounded-lg ${theme.bg.secondary} ${theme.text.secondary} hover:${theme.bg.tertiary} font-medium`}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !apiKey.trim()}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
              saving || !apiKey.trim()
                ? 'bg-gray-500/20 text-gray-500 cursor-not-allowed'
                : 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400'
            }`}
          >
            {saving ? 'Saving...' : 'Save Key'}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// Routing Test Tool
const RoutingTestTool = ({ powerLevel }) => {
  const { theme } = useTheme();
  const toast = useToast();
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);
  
  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    
    try {
      const response = await fetch('/api/v2/llm/route', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          power_level: powerLevel,
          fallback_count: 3
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get routing recommendation');
      }
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setTesting(false);
    }
  };
  
  return (
    <div className={`${theme.card} rounded-xl p-6 border ${theme.border}`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Play className="h-5 w-5 text-purple-400" />
          <h3 className={`text-lg font-semibold ${theme.text.primary}`}>Routing Test</h3>
        </div>
        
        <button
          onClick={handleTest}
          disabled={testing}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            testing
              ? 'bg-gray-500/20 text-gray-500 cursor-not-allowed'
              : 'bg-purple-500/20 hover:bg-purple-500/30 text-purple-400'
          }`}
        >
          <RefreshCw className={`h-4 w-4 ${testing ? 'animate-spin' : ''}`} />
          {testing ? 'Testing...' : 'Test Routing'}
        </button>
      </div>
      
      {result && (
        <div className="space-y-4">
          {/* Primary Recommendation */}
          <div className={`p-4 rounded-lg bg-purple-500/10 border border-purple-500/20`}>
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-5 w-5 text-purple-400" />
              <h4 className={`font-semibold ${theme.text.primary}`}>Primary Recommendation</h4>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-3">
              <div>
                <p className={`text-xs ${theme.text.tertiary} mb-1`}>Model</p>
                <p className={`text-sm font-medium ${theme.text.primary}`}>{result.primary.model_name}</p>
                <p className={`text-xs ${theme.text.tertiary}`}>{result.primary.provider_name}</p>
              </div>
              <div>
                <p className={`text-xs ${theme.text.tertiary} mb-1`}>Composite Score</p>
                <p className={`text-2xl font-bold text-purple-400`}>
                  {(result.primary.composite_score * 100).toFixed(0)}%
                </p>
              </div>
            </div>
            
            {/* Score Breakdown */}
            <div className="grid grid-cols-3 gap-2">
              <div className={`p-2 rounded ${theme.bg.secondary}`}>
                <p className={`text-xs ${theme.text.tertiary} mb-1`}>Cost</p>
                <p className={`text-sm font-medium text-green-400`}>
                  {(result.primary.cost_score * 100).toFixed(0)}%
                </p>
              </div>
              <div className={`p-2 rounded ${theme.bg.secondary}`}>
                <p className={`text-xs ${theme.text.tertiary} mb-1`}>Latency</p>
                <p className={`text-sm font-medium text-blue-400`}>
                  {(result.primary.latency_score * 100).toFixed(0)}%
                </p>
              </div>
              <div className={`p-2 rounded ${theme.bg.secondary}`}>
                <p className={`text-xs ${theme.text.tertiary} mb-1`}>Quality</p>
                <p className={`text-sm font-medium text-purple-400`}>
                  {(result.primary.quality_score * 100).toFixed(0)}%
                </p>
              </div>
            </div>
          </div>
          
          {/* Fallback Options */}
          {result.fallbacks.length > 0 && (
            <div>
              <h4 className={`text-sm font-semibold ${theme.text.primary} mb-2`}>
                Fallback Options ({result.fallbacks.length})
              </h4>
              <div className="space-y-2">
                {result.fallbacks.map((fallback, idx) => (
                  <div key={idx} className={`p-3 rounded-lg ${theme.bg.secondary}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className={`text-sm font-medium ${theme.text.primary}`}>
                          {fallback.model_name}
                        </p>
                        <p className={`text-xs ${theme.text.tertiary}`}>{fallback.provider_name}</p>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-medium text-blue-400`}>
                          {(fallback.composite_score * 100).toFixed(0)}%
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      {!result && !testing && (
        <div className={`text-center py-8 ${theme.text.tertiary}`}>
          <Info className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>Click "Test Routing" to see which model would be selected</p>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export default function LiteLLMManagementV2() {
  const { theme } = useTheme();
  const toast = useToast();
  
  // State
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [providers, setProviders] = useState([]);
  const [models, setModels] = useState([]);
  const [userSettings, setUserSettings] = useState(null);
  const [usageStats, setUsageStats] = useState(null);
  const [byokKeys, setByokKeys] = useState([]);
  
  // Modal state
  const [showBYOKModal, setShowBYOKModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  
  // Filters
  const [powerLevelFilter, setPowerLevelFilter] = useState(null);
  const [providerFilter, setProviderFilter] = useState(null);
  
  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchProviders(),
        fetchModels(),
        fetchUserSettings(),
        fetchUsageStats(),
        fetchBYOKKeys()
      ]);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchProviders = async () => {
    try {
      const response = await fetch('/api/v2/llm/providers', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setProviders(data);
      }
    } catch (error) {
      console.error('Failed to fetch providers:', error);
    }
  };
  
  const fetchModels = async () => {
    try {
      const url = new URL('/api/v2/llm/models', window.location.origin);
      if (powerLevelFilter) url.searchParams.set('power_level', powerLevelFilter);
      if (providerFilter) url.searchParams.set('provider_id', providerFilter);
      
      const response = await fetch(url, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setModels(data);
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };
  
  const fetchUserSettings = async () => {
    try {
      const response = await fetch('/api/v2/llm/settings', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setUserSettings(data);
      }
    } catch (error) {
      console.error('Failed to fetch user settings:', error);
    }
  };
  
  const fetchUsageStats = async () => {
    try {
      const response = await fetch('/api/v2/llm/usage?days=30', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setUsageStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch usage stats:', error);
    }
  };
  
  const fetchBYOKKeys = async () => {
    try {
      const response = await fetch('/api/v2/llm/byok', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setByokKeys(data);
      }
    } catch (error) {
      console.error('Failed to fetch BYOK keys:', error);
    }
  };
  
  const handleUpdateSettings = async (updates) => {
    try {
      const response = await fetch('/api/v2/llm/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(updates)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update settings');
      }
      
      const data = await response.json();
      setUserSettings(data);
      toast.success('Settings updated successfully');
    } catch (error) {
      toast.error(error.message);
    }
  };
  
  const handleTestProvider = async (provider) => {
    toast.info(`Testing ${provider.name}...`);
    // TODO: Implement actual provider test
  };
  
  const handleToggleProvider = async (provider) => {
    // Admin only - toggle provider enabled state
    toast.info(`Toggle ${provider.name} (admin feature)`);
  };
  
  // Refresh models when filter changes
  useEffect(() => {
    fetchModels();
  }, [powerLevelFilter, providerFilter]);
  
  // Calculate statistics
  const stats = {
    totalProviders: providers.length,
    activeProviders: providers.filter(p => p.is_enabled).length,
    totalModels: models.length,
    totalSpend: usageStats?.total_cost_usd || 0,
    totalRequests: usageStats?.total_requests || 0,
    avgCostPerRequest: usageStats?.total_requests > 0 
      ? (usageStats.total_cost_usd / usageStats.total_requests) 
      : 0
  };
  
  // Chart data for usage by provider
  const usageByProviderChart = usageStats?.by_provider ? {
    labels: Object.keys(usageStats.by_provider),
    datasets: [{
      data: Object.values(usageStats.by_provider).map(p => p.requests),
      backgroundColor: [
        'rgba(124, 58, 237, 0.8)',
        'rgba(16, 163, 127, 0.8)',
        'rgba(217, 119, 6, 0.8)',
        'rgba(59, 130, 246, 0.8)',
        'rgba(245, 158, 11, 0.8)',
      ]
    }]
  } : null;
  
  const usageByPowerLevelChart = usageStats?.by_power_level ? {
    labels: Object.keys(usageStats.by_power_level),
    datasets: [{
      label: 'Requests',
      data: Object.values(usageStats.by_power_level).map(p => p.requests),
      backgroundColor: [
        'rgba(16, 185, 129, 0.8)',
        'rgba(59, 130, 246, 0.8)',
        'rgba(168, 85, 247, 0.8)',
      ]
    }]
  } : null;
  
  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Brain className="h-8 w-8 text-blue-400" />
          <h1 className={`text-3xl font-bold ${theme.text.primary}`}>
            LLM Multi-Provider Routing
          </h1>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400">
            Epic 3.1
          </span>
        </div>
        <p className={`${theme.text.secondary}`}>
          Intelligent routing across multiple LLM providers with cost optimization
        </p>
      </div>
      
      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview', icon: Activity },
          { id: 'providers', label: 'Providers', icon: Brain },
          { id: 'models', label: 'Model Catalog', icon: Sparkles },
          { id: 'settings', label: 'Settings', icon: Settings },
          { id: 'analytics', label: 'Analytics', icon: BarChart3 }
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-blue-500/20 text-blue-400'
                  : `${theme.bg.secondary} ${theme.text.secondary} hover:${theme.bg.tertiary}`
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>
      
      {/* Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                title="Total Providers"
                value={stats.totalProviders}
                subtitle={`${stats.activeProviders} active`}
                icon={Brain}
                color="blue"
                loading={loading}
              />
              <StatCard
                title="Available Models"
                value={stats.totalModels}
                subtitle="Across all tiers"
                icon={Sparkles}
                color="purple"
                loading={loading}
              />
              <StatCard
                title="Total Spend (30d)"
                value={`$${stats.totalSpend.toFixed(2)}`}
                subtitle={`${stats.totalRequests.toLocaleString()} requests`}
                icon={DollarSign}
                color="green"
                loading={loading}
              />
              <StatCard
                title="Avg Cost/Request"
                value={`$${stats.avgCostPerRequest.toFixed(4)}`}
                subtitle="Last 30 days"
                icon={TrendingUp}
                color="emerald"
                loading={loading}
              />
            </div>
            
            {/* Power Level Selector */}
            <div>
              <h2 className={`text-xl font-semibold ${theme.text.primary} mb-4`}>
                Select Your Power Level
              </h2>
              <PowerLevelSelector
                selected={userSettings?.preferred_power_level || 'BALANCED'}
                onChange={(level) => handleUpdateSettings({ preferred_power_level: level })}
              />
            </div>
            
            {/* Routing Test */}
            <RoutingTestTool powerLevel={userSettings?.preferred_power_level || 'BALANCED'} />
            
            {/* Charts */}
            {usageStats && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {usageByProviderChart && (
                  <div className={`${theme.card} rounded-xl p-6 border ${theme.border}`}>
                    <h3 className={`text-lg font-semibold ${theme.text.primary} mb-4`}>
                      Usage by Provider
                    </h3>
                    <Pie data={usageByProviderChart} />
                  </div>
                )}
                
                {usageByPowerLevelChart && (
                  <div className={`${theme.card} rounded-xl p-6 border ${theme.border}`}>
                    <h3 className={`text-lg font-semibold ${theme.text.primary} mb-4`}>
                      Usage by Power Level
                    </h3>
                    <Bar data={usageByPowerLevelChart} />
                  </div>
                )}
              </div>
            )}
          </motion.div>
        )}
        
        {activeTab === 'providers' && (
          <motion.div
            key="providers"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className={`text-xl font-semibold ${theme.text.primary}`}>
                LLM Providers ({providers.length})
              </h2>
              <button
                onClick={() => toast.info('Add provider (admin feature)')}
                className="px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 font-medium flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Add Provider
              </button>
            </div>
            
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className={`${theme.card} rounded-xl p-6 border ${theme.border} animate-pulse`}>
                    <div className={`h-12 w-12 ${theme.bg.secondary} rounded-xl mb-4`}></div>
                    <div className={`h-6 w-32 ${theme.bg.secondary} rounded mb-2`}></div>
                    <div className={`h-4 w-48 ${theme.bg.secondary} rounded`}></div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {providers.map(provider => {
                  const hasKey = byokKeys.some(k => k.provider_id === provider.id);
                  return (
                    <ProviderCard
                      key={provider.id}
                      provider={{ ...provider, user_has_key: hasKey }}
                      onAddKey={() => {
                        setSelectedProvider(provider);
                        setShowBYOKModal(true);
                      }}
                      onTest={() => handleTestProvider(provider)}
                      onToggle={() => handleToggleProvider(provider)}
                      isAdmin={false} // TODO: Get from auth context
                    />
                  );
                })}
              </div>
            )}
          </motion.div>
        )}
        
        {activeTab === 'models' && (
          <motion.div
            key="models"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Filters */}
            <div className="flex gap-4 flex-wrap">
              <div className="flex gap-2">
                <button
                  onClick={() => setPowerLevelFilter(null)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    !powerLevelFilter
                      ? 'bg-blue-500/20 text-blue-400'
                      : `${theme.bg.secondary} ${theme.text.secondary}`
                  }`}
                >
                  All Tiers
                </button>
                {Object.keys(POWER_LEVELS).map(level => (
                  <button
                    key={level}
                    onClick={() => setPowerLevelFilter(level)}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      powerLevelFilter === level
                        ? `bg-${POWER_LEVELS[level].color}-500/20 text-${POWER_LEVELS[level].color}-400`
                        : `${theme.bg.secondary} ${theme.text.secondary}`
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Model Grid */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map(i => (
                  <div key={i} className={`${theme.card} rounded-lg p-4 border ${theme.border} animate-pulse`}>
                    <div className={`h-6 w-32 ${theme.bg.secondary} rounded mb-2`}></div>
                    <div className={`h-4 w-24 ${theme.bg.secondary} rounded mb-4`}></div>
                    <div className={`h-16 ${theme.bg.secondary} rounded`}></div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {models.map(model => (
                  <ModelCard key={model.id} model={model} />
                ))}
              </div>
            )}
            
            {!loading && models.length === 0 && (
              <div className={`text-center py-12 ${theme.text.tertiary}`}>
                <Sparkles className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No models found matching your filters</p>
              </div>
            )}
          </motion.div>
        )}
        
        {activeTab === 'settings' && (
          <motion.div
            key="settings"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6 max-w-4xl"
          >
            {/* Power Level */}
            <div>
              <h2 className={`text-xl font-semibold ${theme.text.primary} mb-4`}>
                Preferred Power Level
              </h2>
              <PowerLevelSelector
                selected={userSettings?.preferred_power_level || 'BALANCED'}
                onChange={(level) => handleUpdateSettings({ preferred_power_level: level })}
              />
            </div>
            
            {/* Routing Configuration */}
            {userSettings && (
              <RoutingConfigPanel
                config={userSettings.routing_config}
                onChange={(config) => setUserSettings(prev => ({ ...prev, routing_config: config }))}
                onSave={() => handleUpdateSettings({ routing_config: userSettings.routing_config })}
              />
            )}
            
            {/* Monthly Budget */}
            <div className={`${theme.card} rounded-xl p-6 border ${theme.border}`}>
              <div className="flex items-center gap-2 mb-4">
                <DollarSign className="h-5 w-5 text-green-400" />
                <h3 className={`text-lg font-semibold ${theme.text.primary}`}>Monthly Budget</h3>
              </div>
              
              <div className="mb-4">
                <label className={`text-sm font-medium ${theme.text.secondary} mb-2 block`}>
                  Budget Limit (USD)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={userSettings?.monthly_budget_usd || ''}
                  onChange={(e) => setUserSettings(prev => ({ 
                    ...prev, 
                    monthly_budget_usd: parseFloat(e.target.value) || null 
                  }))}
                  placeholder="No limit"
                  className={`w-full px-4 py-3 rounded-lg ${theme.bg.secondary} ${theme.text.primary} border ${theme.border} focus:ring-2 focus:ring-blue-500`}
                />
              </div>
              
              {userSettings?.monthly_budget_usd && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-sm ${theme.text.secondary}`}>Current Month Spend</span>
                    <span className={`text-sm font-medium ${theme.text.primary}`}>
                      ${userSettings.current_month_spend?.toFixed(2) || '0.00'} / ${userSettings.monthly_budget_usd.toFixed(2)}
                    </span>
                  </div>
                  <div className={`w-full h-2 ${theme.bg.secondary} rounded-full overflow-hidden`}>
                    <div
                      className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all"
                      style={{
                        width: `${Math.min(100, (userSettings.current_month_spend / userSettings.monthly_budget_usd) * 100)}%`
                      }}
                    />
                  </div>
                </div>
              )}
              
              <button
                onClick={() => handleUpdateSettings({ monthly_budget_usd: userSettings?.monthly_budget_usd })}
                className="w-full py-2 px-4 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                <Save className="h-4 w-4" />
                Save Budget
              </button>
            </div>
          </motion.div>
        )}
        
        {activeTab === 'analytics' && (
          <motion.div
            key="analytics"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className={`text-xl font-semibold ${theme.text.primary}`}>
                Usage Analytics (Last 30 Days)
              </h2>
              <button
                onClick={() => toast.info('Export data feature coming soon')}
                className="px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 font-medium flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>
            </div>
            
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatCard
                title="Total Requests"
                value={(usageStats?.total_requests || 0).toLocaleString()}
                icon={Activity}
                color="blue"
              />
              <StatCard
                title="Total Tokens"
                value={((usageStats?.total_input_tokens || 0) + (usageStats?.total_output_tokens || 0)).toLocaleString()}
                subtitle={`${(usageStats?.total_input_tokens || 0).toLocaleString()} in / ${(usageStats?.total_output_tokens || 0).toLocaleString()} out`}
                icon={Zap}
                color="purple"
              />
              <StatCard
                title="Total Cost"
                value={`$${(usageStats?.total_cost_usd || 0).toFixed(2)}`}
                icon={DollarSign}
                color="green"
              />
            </div>
            
            {/* Provider Breakdown */}
            {usageStats?.by_provider && Object.keys(usageStats.by_provider).length > 0 && (
              <div className={`${theme.card} rounded-xl p-6 border ${theme.border}`}>
                <h3 className={`text-lg font-semibold ${theme.text.primary} mb-4`}>
                  Usage by Provider
                </h3>
                <div className="space-y-3">
                  {Object.entries(usageStats.by_provider).map(([provider, data]) => (
                    <div key={provider} className={`p-4 rounded-lg ${theme.bg.secondary}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-medium ${theme.text.primary}`}>{provider}</span>
                        <span className={`text-sm ${theme.text.secondary}`}>
                          {data.requests.toLocaleString()} requests
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className={`${theme.text.tertiary} mb-1`}>Tokens</p>
                          <p className={`font-medium ${theme.text.secondary}`}>
                            {(data.input_tokens + data.output_tokens).toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <p className={`${theme.text.tertiary} mb-1`}>Cost</p>
                          <p className={`font-medium text-green-400`}>
                            ${parseFloat(data.cost_usd).toFixed(2)}
                          </p>
                        </div>
                        <div>
                          <p className={`${theme.text.tertiary} mb-1`}>Avg Latency</p>
                          <p className={`font-medium text-blue-400`}>
                            {data.avg_latency_ms}ms
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {!usageStats && !loading && (
              <div className={`text-center py-12 ${theme.text.tertiary}`}>
                <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No usage data available yet</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* BYOK Modal */}
      <BYOKModal
        isOpen={showBYOKModal}
        onClose={() => {
          setShowBYOKModal(false);
          setSelectedProvider(null);
        }}
        provider={selectedProvider}
        onSave={() => {
          fetchBYOKKeys();
          fetchProviders();
        }}
      />
    </div>
  );
}
