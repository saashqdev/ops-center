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
      const data = await response.json();
      
      if (data.success) {
        setModelPricing(data.pricing || []);
      }
    } catch (error) {
      console.error('Failed to load model pricing:', error);
    }
  };

  const loadRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE}/recommendations?scope=platform`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setRecommendations(data.recommendations || []);
      }
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    }
  };

  const generateRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE}/recommendations/generate`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        loadRecommendations();
      }
    } catch (error) {
      console.error('Failed to generate recommendations:', error);
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
    </div>
  );
}
