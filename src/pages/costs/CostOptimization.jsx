import React, { useState, useEffect } from 'react';
import {
  ChartPieIcon,
  BanknotesIcon,
  LightBulbIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  CpuChipIcon,
  UserIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';
import { useTheme } from '../../contexts/ThemeContext';
import MetricCard from '../../components/analytics/MetricCard';

/**
 * Cost Optimization - Personal Cost Dashboard
 * 
 * User-facing cost analysis and optimization recommendations.
 * Helps users understand their LLM spending and find savings opportunities.
 * 
 * Epic: 14 - Cost Optimization Dashboard
 * Features:
 * - Personal cost breakdown
 * - Budget tracking
 * - Model cost comparison
 * - Savings recommendations
 */
export default function CostOptimization() {
  const { currentTheme } = useTheme();
  const [costAnalysis, setCostAnalysis] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [timeRange, setTimeRange] = useState('7d'); // 1h, 6h, 24h, 7d, 30d
  const [loading, setLoading] = useState(true);

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
    loadCostAnalysis();
    loadBudgets();
    loadRecommendations();
  }, [timeRange]);

  const loadCostAnalysis = async () => {
    try {
      const response = await fetch(`${API_BASE}/analysis?time_range=${timeRange}`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setCostAnalysis(data.analysis);
      }
    } catch (error) {
      console.error('Failed to load cost analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadBudgets = async () => {
    try {
      const response = await fetch(`${API_BASE}/budgets?scope=user`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setBudgets(data.budgets || []);
      }
    } catch (error) {
      console.error('Failed to load budgets:', error);
    }
  };

  const loadRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE}/recommendations`, {
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

  const acceptRecommendation = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/recommendations/${id}/accept`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        loadRecommendations();
      }
    } catch (error) {
      console.error('Failed to accept recommendation:', error);
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

  const getBudgetStatus = (budget) => {
    const percent = (budget.current_spend / budget.total_limit) * 100;
    if (percent >= 100) return { color: 'red', status: 'Exceeded' };
    if (percent >= 95) return { color: 'red', status: 'Critical' };
    if (percent >= 80) return { color: 'yellow', status: 'Warning' };
    return { color: 'green', status: 'Healthy' };
  };

  return (
    <div className={`min-h-screen ${bgClass} p-6`}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg">
                <ChartPieIcon className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className={`text-3xl font-bold ${textClass}`}>Cost Optimization</h1>
                <p className={`${subtextClass}`}>Track your LLM spending and find savings</p>
              </div>
            </div>

            {/* Time Range Selector */}
            <div className="flex gap-2">
              {['24h', '7d', '30d', '90d'].map((range) => (
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

        {/* Cost Summary Cards */}
        {costAnalysis && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              icon={BanknotesIcon}
              label="Total Cost"
              value={formatCurrency(costAnalysis.total_cost || 0)}
              trend={costAnalysis.trend > 0 ? 'up' : 'down'}
              trendValue={`${Math.abs(costAnalysis.trend || 0)}%`}
              color="purple"
            />
            <MetricCard
              icon={CpuChipIcon}
              label="Requests"
              value={(costAnalysis.total_requests || 0).toLocaleString()}
              color="blue"
            />
            <MetricCard
              icon={ChartPieIcon}
              label="Avg Cost/Request"
              value={formatCurrency(costAnalysis.avg_cost_per_request || 0)}
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Model Breakdown */}
          <div className={`${cardBg} border rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${textClass} mb-4`}>Cost by Model</h2>
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto"></div>
              </div>
            ) : costAnalysis?.models && costAnalysis.models.length > 0 ? (
              <div className="space-y-3">
                {costAnalysis.models.map((model, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className={`p-3 rounded-lg ${
                      currentTheme === 'light' ? 'bg-gray-50' : 'bg-gray-700/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`font-medium ${textClass}`}>{model.model_name}</span>
                      <span className={`font-bold ${textClass}`}>{formatCurrency(model.cost)}</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className={subtextClass}>{model.requests.toLocaleString()} requests</span>
                      <span className={subtextClass}>•</span>
                      <span className={subtextClass}>{model.percentage.toFixed(1)}% of total</span>
                    </div>
                    <div className="mt-2 bg-gray-600 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full"
                        style={{ width: `${model.percentage}%` }}
                      ></div>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <p className={`text-center py-8 ${subtextClass}`}>No cost data available</p>
            )}
          </div>

          {/* Active Budgets */}
          <div className={`${cardBg} border rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${textClass} mb-4`}>Active Budgets</h2>
            {budgets.length > 0 ? (
              <div className="space-y-4">
                {budgets.map((budget) => {
                  const status = getBudgetStatus(budget);
                  const percent = (budget.current_spend / budget.total_limit) * 100;
                  
                  return (
                    <div key={budget.id} className={`p-4 rounded-lg border ${
                      currentTheme === 'light' ? 'bg-gray-50 border-gray-200' : 'bg-gray-700/50 border-gray-600'
                    }`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-medium ${textClass}`}>{budget.name}</span>
                        <span className={`px-2 py-1 text-xs rounded-full bg-${status.color}-500/20 text-${status.color}-400`}>
                          {status.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className={subtextClass}>
                          {formatCurrency(budget.current_spend)} / {formatCurrency(budget.total_limit)}
                        </span>
                        <span className={textClass}>{percent.toFixed(1)}%</span>
                      </div>
                      <div className="bg-gray-600 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            status.color === 'red' ? 'bg-red-500' :
                            status.color === 'yellow' ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${Math.min(percent, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <ExclamationTriangleIcon className="w-12 h-12 text-yellow-500 mx-auto mb-3" />
                <p className={`${textClass} mb-2`}>No active budgets</p>
                <p className={`text-sm ${subtextClass}`}>Set up a budget to track your spending</p>
              </div>
            )}
          </div>
        </div>

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className={`${cardBg} border rounded-lg p-6 mt-6`}>
            <div className="flex items-center gap-2 mb-4">
              <LightBulbIcon className="w-6 h-6 text-yellow-400" />
              <h2 className={`text-xl font-bold ${textClass}`}>Savings Recommendations</h2>
            </div>
            <div className="space-y-4">
              {recommendations.map((rec) => (
                <motion.div
                  key={rec.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-4 rounded-lg border ${
                    currentTheme === 'light' ? 'bg-green-50 border-green-200' : 'bg-green-900/20 border-green-500/30'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h3 className={`font-semibold ${textClass} mb-1`}>{rec.title}</h3>
                      <p className={`text-sm ${subtextClass} mb-2`}>{rec.description}</p>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-green-400">
                          Save {formatCurrency(rec.potential_savings)}/month
                        </span>
                        <span className={`text-sm ${subtextClass}`}>Priority: {rec.priority_score}/100</span>
                      </div>
                    </div>
                    <button
                      onClick={() => acceptRecommendation(rec.id)}
                      className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Accept
                    </button>
                  </div>
                  {rec.alternative_model && (
                    <div className="mt-3 pt-3 border-t border-green-500/30">
                      <div className="text-sm">
                        <span className={subtextClass}>Switch to: </span>
                        <span className={textClass}>{rec.alternative_model}</span>
                        <span className={`ml-2 ${subtextClass}`}>
                          ({rec.quality_delta > 0 ? '+' : ''}{rec.quality_delta}% quality change)
                        </span>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
