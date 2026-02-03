import React, { useState, useEffect } from 'react';
import {
  BanknotesIcon,
  BuildingOfficeIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  UserGroupIcon,
  CpuChipIcon,
  LightBulbIcon,
  PlusIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../../contexts/ThemeContext';
import MetricCard from '../../components/analytics/MetricCard';

/**
 * Cost Optimization Admin - Platform-Wide Cost Management
 * 
 * Admin interface for managing organization costs, budgets, and pricing.
 * Provides comprehensive cost analytics and optimization tools.
 * 
 * Epic: 14 - Cost Optimization Dashboard (Admin View)
 * Features:
 * - Platform-wide cost analytics
 * - Multi-organization budget management
 * - Model pricing configuration
 * - Advanced forecasting
 * - Recommendation management
 */
export default function CostOptimizationAdmin() {
  const { currentTheme } = useTheme();
  const [costAnalysis, setCostAnalysis] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [modelPricing, setModelPricing] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [timeRange, setTimeRange] = useState('30d');
  const [loading, setLoading] = useState(true);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [showRecommendationsModal, setShowRecommendationsModal] = useState(false);
  const [generatedRecommendations, setGeneratedRecommendations] = useState([]);
  const [pricingForm, setPricingForm] = useState({
    provider: '',
    model_name: '',
    input_price_per_million: '',
    output_price_per_million: '',
    model_tier: 'basic',
    quality_score: '',
    is_active: true
  });
  const [savingPricing, setSavingPricing] = useState(false);

  const API_BASE = '/api/v1/costs';

  const bgClass = currentTheme === 'unicorn'
    ? 'bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900'
    : currentTheme === 'light'
    ? 'bg-gradient-to-br from-gray-50 to-gray-100'
    : 'bg-gray-900';

  const cardBg = currentTheme === 'unicorn'
    ? 'bg-purple-900/20 border-purple-500/20'
    : currentTheme === 'light'
    ? 'bg-white border-gray-200'
    : 'bg-gray-800 border-gray-700';

  const textClass = currentTheme === 'light' ? 'text-gray-900' : 'text-white';
  const subtextClass = currentTheme === 'light' ? 'text-gray-600' : 'text-gray-400';

  useEffect(() => {
    loadPlatformCosts();
    loadOrganizations();
    loadModelPricing();
    loadRecommendations();
  }, [timeRange]);

  const loadPlatformCosts = async () => {
    try {
      const response = await fetch(`${API_BASE}/analysis?time_range=${timeRange}&scope=platform`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setCostAnalysis(data.analysis);
      }
    } catch (error) {
      console.error('Failed to load platform costs:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadOrganizations = async () => {
    try {
      const response = await fetch(`${API_BASE}/breakdown/organizations?time_range=${timeRange}`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setOrganizations(data.organizations || []);
      }
    } catch (error) {
      console.error('Failed to load organizations:', error);
    }
  };

  const loadModelPricing = async () => {
    try {
      const response = await fetch(`${API_BASE}/pricing/models`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setModelPricing(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Failed to load model pricing:', error);
    }
  };

  const loadRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE}/recommendations`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setRecommendations(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    }
  };

  const generateRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE}/recommendations/generate`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setGeneratedRecommendations(Array.isArray(data) ? data : []);
        setShowRecommendationsModal(true);
        // Also update the main recommendations list
        loadRecommendations();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to generate recommendations');
      }
    } catch (error) {
      console.error('Failed to generate recommendations:', error);
      alert('Failed to generate recommendations');
    }
  };

  const handleAddModelPricing = async (e) => {
    e.preventDefault();
    setSavingPricing(true);
    
    try {
      const response = await fetch(`${API_BASE}/pricing/models`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          provider: pricingForm.provider,
          model_name: pricingForm.model_name,
          input_price_per_million: parseFloat(pricingForm.input_price_per_million),
          output_price_per_million: parseFloat(pricingForm.output_price_per_million),
          model_tier: pricingForm.model_tier,
          quality_score: pricingForm.quality_score ? parseFloat(pricingForm.quality_score) : null,
          is_active: pricingForm.is_active
        })
      });
      
      if (response.ok) {
        setShowPricingModal(false);
        setPricingForm({
          provider: '',
          model_name: '',
          input_price_per_million: '',
          output_price_per_million: '',
          model_tier: 'basic',
          quality_score: '',
          is_active: true
        });
        loadModelPricing();
        alert('Model pricing added successfully');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to add model pricing');
      }
    } catch (error) {
      console.error('Failed to add model pricing:', error);
      alert('Failed to add model pricing');
    } finally {
      setSavingPricing(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  return (
    <div className={`min-h-screen ${bgClass} p-6`}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-lg">
                <BanknotesIcon className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className={`text-3xl font-bold ${textClass}`}>Cost Optimization</h1>
                <p className={`${subtextClass}`}>Platform-wide cost analytics and management</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={generateRecommendations}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <LightBulbIcon className="w-5 h-5" />
                Generate Recommendations
              </button>
              <div className="flex gap-2">
                {['7d', '30d', '90d'].map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      timeRange === range
                        ? 'bg-purple-600 text-white'
                        : currentTheme === 'light'
                        ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Platform Summary Cards */}
        {costAnalysis && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              icon={BanknotesIcon}
              label="Total Platform Cost"
              value={formatCurrency(costAnalysis.total_cost || 0)}
              trend={costAnalysis.trend > 0 ? 'up' : 'down'}
              trendValue={`${Math.abs(costAnalysis.trend || 0)}%`}
              color="purple"
            />
            <MetricCard
              icon={BuildingOfficeIcon}
              label="Organizations"
              value={(costAnalysis.organization_count || 0).toLocaleString()}
              color="blue"
            />
            <MetricCard
              icon={CpuChipIcon}
              label="Total Requests"
              value={(costAnalysis.total_requests || 0).toLocaleString()}
              color="green"
            />
            <MetricCard
              icon={LightBulbIcon}
              label="Potential Savings"
              value={formatCurrency(costAnalysis.potential_savings || 0)}
              color="yellow"
            />
          </div>
        )}

        {/* Top Organizations by Cost */}
        <div className={`${cardBg} border rounded-lg p-6 mb-6`}>
          <h2 className={`text-xl font-bold ${textClass} mb-4 flex items-center gap-2`}>
            <ChartBarIcon className="w-6 h-6" />
            Top Organizations by Cost
          </h2>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto"></div>
            </div>
          ) : organizations.length > 0 ? (
            <div className="space-y-3">
              {organizations.slice(0, 10).map((org, idx) => (
                <motion.div
                  key={org.organization_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={`p-4 rounded-lg ${
                    currentTheme === 'light' ? 'bg-gray-50' : 'bg-gray-700/50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className={`text-2xl font-bold ${subtextClass}`}>#{idx + 1}</span>
                      <div>
                        <div className={`font-medium ${textClass}`}>{org.organization_name}</div>
                        <div className={`text-sm ${subtextClass}`}>
                          {org.user_count} users • {org.total_requests.toLocaleString()} requests
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-xl font-bold ${textClass}`}>{formatCurrency(org.total_cost)}</div>
                      <div className={`text-sm ${subtextClass}`}>
                        {formatCurrency(org.avg_cost_per_request)}/req
                      </div>
                    </div>
                  </div>
                  {/* Progress bar showing relative cost */}
                  <div className="mt-2 bg-gray-600 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full"
                      style={{ width: `${(org.total_cost / organizations[0].total_cost) * 100}%` }}
                    ></div>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className={`text-center py-8 ${subtextClass}`}>No organization data available</p>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Model Pricing Configuration */}
          <div className={`${cardBg} border rounded-lg p-6`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className={`text-xl font-bold ${textClass} flex items-center gap-2`}>
                <CpuChipIcon className="w-6 h-6" />
                Model Pricing
              </h2>
              <button
                onClick={() => setShowPricingModal(true)}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm flex items-center gap-1"
              >
                <PlusIcon className="w-4 h-4" />
                Add Model
              </button>
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {modelPricing.map((model) => (
                <div
                  key={model.id}
                  className={`p-3 rounded-lg ${
                    currentTheme === 'light' ? 'bg-gray-50' : 'bg-gray-700/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className={`font-medium ${textClass}`}>{model.model_name}</div>
                      <div className={`text-xs ${subtextClass}`}>{model.provider}</div>
                    </div>
                    <div className="text-right text-sm">
                      <div className={textClass}>In: {formatCurrency(model.input_price_per_million)}/M</div>
                      <div className={subtextClass}>Out: {formatCurrency(model.output_price_per_million)}/M</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cost Trends & Forecasting */}
          <div className={`${cardBg} border rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${textClass} mb-4 flex items-center gap-2`}>
              <ArrowTrendingUpIcon className="w-6 h-6" />
              Cost Trends & Forecast
            </h2>
            {costAnalysis?.forecast && (
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${
                  currentTheme === 'light' ? 'bg-blue-50 border border-blue-200' : 'bg-blue-900/20 border border-blue-500/30'
                }`}>
                  <div className={`text-sm font-medium ${textClass} mb-2`}>30-Day Forecast</div>
                  <div className={`text-2xl font-bold ${textClass}`}>
                    {formatCurrency(costAnalysis.forecast.predicted_cost)}
                  </div>
                  <div className={`text-sm ${subtextClass} mt-1`}>
                    Range: {formatCurrency(costAnalysis.forecast.lower_bound)} - {formatCurrency(costAnalysis.forecast.upper_bound)}
                  </div>
                </div>

                <div className={`p-4 rounded-lg ${
                  currentTheme === 'light' ? 'bg-purple-50 border border-purple-200' : 'bg-purple-900/20 border border-purple-500/30'
                }`}>
                  <div className={`text-sm font-medium ${textClass} mb-2`}>Trend Analysis</div>
                  <div className="flex items-center gap-2">
                    {costAnalysis.trend > 0 ? (
                      <ArrowTrendingUpIcon className="w-5 h-5 text-red-400" />
                    ) : (
                      <ArrowTrendingDownIcon className="w-5 h-5 text-green-400" />
                    )}
                    <span className={textClass}>
                      {costAnalysis.trend > 0 ? 'Increasing' : 'Decreasing'} by {Math.abs(costAnalysis.trend)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Platform Recommendations */}
        {recommendations.length > 0 && (
          <div className={`${cardBg} border rounded-lg p-6`}>
            <div className="flex items-center gap-2 mb-4">
              <LightBulbIcon className="w-6 h-6 text-yellow-400" />
              <h2 className={`text-xl font-bold ${textClass}`}>
                Platform Savings Recommendations ({recommendations.length})
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recommendations.map((rec) => (
                <motion.div
                  key={rec.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-4 rounded-lg border ${
                    currentTheme === 'light' ? 'bg-green-50 border-green-200' : 'bg-green-900/20 border-green-500/30'
                  }`}
                >
                  <div className="mb-2">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className={`font-semibold ${textClass}`}>{rec.title}</h3>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        rec.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                        rec.status === 'accepted' ? 'bg-green-500/20 text-green-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {rec.status}
                      </span>
                    </div>
                    <p className={`text-sm ${subtextClass}`}>{rec.description}</p>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-green-500/30">
                    <div>
                      <div className="text-sm font-medium text-green-400">
                        {formatCurrency(rec.potential_savings)}/month
                      </div>
                      <div className={`text-xs ${subtextClass}`}>Priority: {rec.priority_score}/100</div>
                    </div>
                    {rec.affected_organizations && (
                      <div className={`text-xs ${subtextClass}`}>
                        Affects {rec.affected_organizations} orgs
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Generated Recommendations Modal */}
      <AnimatePresence>
        {showRecommendationsModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowRecommendationsModal(false)}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
            >
              <div className={`${cardBg} border rounded-lg p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <LightBulbIcon className="w-6 h-6 text-yellow-400" />
                    <h3 className={`text-xl font-bold ${textClass}`}>
                      Generated Recommendations ({generatedRecommendations.length})
                    </h3>
                  </div>
                  <button
                    onClick={() => setShowRecommendationsModal(false)}
                    className={`p-1 rounded-lg ${
                      currentTheme === 'light' ? 'hover:bg-gray-200' : 'hover:bg-gray-700'
                    }`}
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                {generatedRecommendations.length === 0 ? (
                  <div className="text-center py-12">
                    <LightBulbIcon className={`w-16 h-16 mx-auto mb-4 ${subtextClass}`} />
                    <p className={`text-lg ${textClass} mb-2`}>No Recommendations Generated</p>
                    <p className={subtextClass}>
                      Recommendations require cost analysis data. Start using LLM models to generate insights.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {generatedRecommendations.map((rec, idx) => (
                      <motion.div
                        key={rec.id || idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        className={`p-4 rounded-lg border ${
                          currentTheme === 'light' 
                            ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200' 
                            : 'bg-gradient-to-r from-green-900/20 to-emerald-900/20 border-green-500/30'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className={`font-semibold text-lg ${textClass}`}>{rec.title}</h4>
                              <span className={`text-xs px-2 py-1 rounded-full ${
                                rec.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                                rec.status === 'accepted' ? 'bg-green-500/20 text-green-400' :
                                rec.status === 'rejected' ? 'bg-red-500/20 text-red-400' :
                                'bg-gray-500/20 text-gray-400'
                              }`}>
                                {rec.status || 'pending'}
                              </span>
                            </div>
                            <p className={`text-sm ${subtextClass} mb-2`}>{rec.description}</p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                          <div className={`p-2 rounded ${currentTheme === 'light' ? 'bg-white/50' : 'bg-black/20'}`}>
                            <div className="text-xs text-green-400 mb-1">Potential Savings</div>
                            <div className={`font-bold ${textClass}`}>{formatCurrency(rec.estimated_savings || 0)}/mo</div>
                          </div>
                          <div className={`p-2 rounded ${currentTheme === 'light' ? 'bg-white/50' : 'bg-black/20'}`}>
                            <div className="text-xs text-blue-400 mb-1">Savings %</div>
                            <div className={`font-bold ${textClass}`}>{(rec.savings_percentage || 0).toFixed(1)}%</div>
                          </div>
                          <div className={`p-2 rounded ${currentTheme === 'light' ? 'bg-white/50' : 'bg-black/20'}`}>
                            <div className="text-xs text-purple-400 mb-1">Priority</div>
                            <div className={`font-bold ${textClass}`}>{rec.priority_score || 0}/100</div>
                          </div>
                          <div className={`p-2 rounded ${currentTheme === 'light' ? 'bg-white/50' : 'bg-black/20'}`}>
                            <div className="text-xs text-orange-400 mb-1">Confidence</div>
                            <div className={`font-bold ${textClass}`}>{((rec.confidence_score || 0) * 100).toFixed(0)}%</div>
                          </div>
                        </div>

                        <div className="flex items-center justify-between pt-3 border-t border-green-500/20">
                          <div className="flex gap-3 text-xs">
                            <span className={`${subtextClass}`}>
                              Type: <span className={textClass}>{rec.recommendation_type}</span>
                            </span>
                            <span className={`${subtextClass}`}>
                              Difficulty: <span className={textClass}>{rec.implementation_difficulty}</span>
                            </span>
                            <span className={`${subtextClass}`}>
                              Quality Impact: <span className={textClass}>{rec.quality_impact}</span>
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}

                <div className="flex justify-end gap-2 mt-6 pt-4 border-t">
                  <button
                    onClick={() => setShowRecommendationsModal(false)}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Add Model Pricing Modal */}
      <AnimatePresence>
        {showPricingModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowPricingModal(false)}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
            >
              <div className={`${cardBg} border rounded-lg p-6 max-w-md w-full`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={`text-xl font-bold ${textClass}`}>Add Model Pricing</h3>
                  <button
                    onClick={() => setShowPricingModal(false)}
                    className={`p-1 rounded-lg ${
                      currentTheme === 'light' ? 'hover:bg-gray-200' : 'hover:bg-gray-700'
                    }`}
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <form onSubmit={handleAddModelPricing} className="space-y-4">
                  <div>
                    <label className={`block text-sm font-medium ${textClass} mb-1`}>
                      Provider
                    </label>
                    <input
                      type="text"
                      required
                      value={pricingForm.provider}
                      onChange={(e) => setPricingForm({ ...pricingForm, provider: e.target.value })}
                      placeholder="e.g., OpenAI, Anthropic"
                      className={`w-full px-3 py-2 rounded-lg border ${
                        currentTheme === 'light'
                          ? 'bg-white border-gray-300 text-gray-900'
                          : 'bg-gray-700 border-gray-600 text-white'
                      }`}
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-medium ${textClass} mb-1`}>
                      Model Name
                    </label>
                    <input
                      type="text"
                      required
                      value={pricingForm.model_name}
                      onChange={(e) => setPricingForm({ ...pricingForm, model_name: e.target.value })}
                      placeholder="e.g., gpt-4, claude-3-opus"
                      className={`w-full px-3 py-2 rounded-lg border ${
                        currentTheme === 'light'
                          ? 'bg-white border-gray-300 text-gray-900'
                          : 'bg-gray-700 border-gray-600 text-white'
                      }`}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={`block text-sm font-medium ${textClass} mb-1`}>
                        Input Price/Million
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        required
                        value={pricingForm.input_price_per_million}
                        onChange={(e) => setPricingForm({ ...pricingForm, input_price_per_million: e.target.value })}
                        placeholder="$"
                        className={`w-full px-3 py-2 rounded-lg border ${
                          currentTheme === 'light'
                            ? 'bg-white border-gray-300 text-gray-900'
                            : 'bg-gray-700 border-gray-600 text-white'
                        }`}
                      />
                    </div>

                    <div>
                      <label className={`block text-sm font-medium ${textClass} mb-1`}>
                        Output Price/Million
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        required
                        value={pricingForm.output_price_per_million}
                        onChange={(e) => setPricingForm({ ...pricingForm, output_price_per_million: e.target.value })}
                        placeholder="$"
                        className={`w-full px-3 py-2 rounded-lg border ${
                          currentTheme === 'light'
                            ? 'bg-white border-gray-300 text-gray-900'
                            : 'bg-gray-700 border-gray-600 text-white'
                        }`}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={`block text-sm font-medium ${textClass} mb-1`}>
                        Model Tier
                      </label>
                      <select
                        value={pricingForm.model_tier}
                        onChange={(e) => setPricingForm({ ...pricingForm, model_tier: e.target.value })}
                        className={`w-full px-3 py-2 rounded-lg border ${
                          currentTheme === 'light'
                            ? 'bg-white border-gray-300 text-gray-900'
                            : 'bg-gray-700 border-gray-600 text-white'
                        }`}
                      >
                        <option value="free">Free</option>
                        <option value="basic">Basic</option>
                        <option value="advanced">Advanced</option>
                        <option value="premium">Premium</option>
                      </select>
                    </div>

                    <div>
                      <label className={`block text-sm font-medium ${textClass} mb-1`}>
                        Quality Score (0-10)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="10"
                        value={pricingForm.quality_score}
                        onChange={(e) => setPricingForm({ ...pricingForm, quality_score: e.target.value })}
                        placeholder="Optional"
                        className={`w-full px-3 py-2 rounded-lg border ${
                          currentTheme === 'light'
                            ? 'bg-white border-gray-300 text-gray-900'
                            : 'bg-gray-700 border-gray-600 text-white'
                        }`}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="is_active"
                      checked={pricingForm.is_active}
                      onChange={(e) => setPricingForm({ ...pricingForm, is_active: e.target.checked })}
                      className="w-4 h-4 text-purple-600 rounded"
                    />
                    <label htmlFor="is_active" className={`text-sm ${textClass}`}>
                      Active
                    </label>
                  </div>

                  <div className="flex gap-2 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowPricingModal(false)}
                      className={`flex-1 px-4 py-2 rounded-lg font-medium ${
                        currentTheme === 'light'
                          ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={savingPricing}
                      className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium disabled:opacity-50"
                    >
                      {savingPricing ? 'Saving...' : 'Add Model'}
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
