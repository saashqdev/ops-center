/**
 * API Usage Dashboard Component - Epic 7.0
 * 
 * View API usage statistics, quotas, and daily breakdowns
 * - Current month usage summary
 * - Quota status and limits
 * - Daily usage charts (30-day history)
 * - Event type and model breakdowns
 * 
 * Backend: /api/v1/usage/* (Epic 7.0)
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  BoltIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../components/Toast';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

const COLORS = {
  tokens: '#3b82f6',
  cost: '#10b981',
  calls: '#8b5cf6',
  errors: '#ef4444'
};

const EVENT_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function APIUsageDashboard() {
  const { currentTheme } = useTheme();
  const toast = useToast();
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [quota, setQuota] = useState(null);
  const [dailyUsage, setDailyUsage] = useState([]);
  const [days, setDays] = useState(30);

  const isDark = currentTheme === 'dark' || currentTheme === 'unicorn';
  const themeClasses = {
    card: currentTheme === 'unicorn'
      ? 'bg-purple-900/50 backdrop-blur-xl border-white/20'
      : currentTheme === 'light'
      ? 'bg-white border-gray-200'
      : 'bg-slate-800 border-slate-700',
    text: isDark ? 'text-slate-100' : 'text-gray-900',
    subtext: isDark ? 'text-slate-400' : 'text-gray-600',
    button: currentTheme === 'unicorn'
      ? 'bg-purple-600 hover:bg-purple-700'
      : 'bg-blue-600 hover:bg-blue-700',
  };

  useEffect(() => {
    loadUsageData();
  }, [days]);

  const loadUsageData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        loadSummary(),
        loadQuota(),
        loadDailyUsage()
      ]);
    } catch (error) {
      console.error('Error loading usage data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const response = await fetch('/api/v1/usage/summary');
      if (!response.ok) throw new Error('Failed to load summary');
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Error loading summary:', error);
      toast?.error('Failed to load usage summary');
    }
  };

  const loadQuota = async () => {
    try {
      const response = await fetch('/api/v1/usage/quota');
      if (!response.ok) throw new Error('Failed to load quota');
      const data = await response.json();
      setQuota(data);
    } catch (error) {
      console.error('Error loading quota:', error);
      toast?.error('Failed to load quota status');
    }
  };

  const loadDailyUsage = async () => {
    try {
      const response = await fetch(`/api/v1/usage/daily?days=${days}`);
      if (!response.ok) throw new Error('Failed to load daily usage');
      const data = await response.json();
      setDailyUsage(data.daily_usage || []);
    } catch (error) {
      console.error('Error loading daily usage:', error);
      toast?.error('Failed to load daily usage');
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadUsageData();
    setRefreshing(false);
    toast?.success('Usage data refreshed');
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num?.toLocaleString() || '0';
  };

  const formatCost = (cost) => {
    return `$${(cost || 0).toFixed(4)}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const calculatePercentage = (used, total) => {
    if (!total || total === 0) return 0;
    return Math.min(100, Math.round((used / total) * 100));
  };

  // Transform event breakdown for pie chart
  const eventBreakdownData = summary?.event_breakdown
    ? Object.entries(summary.event_breakdown).map(([name, value]) => ({
        name: name.replace('_', ' ').toUpperCase(),
        value: value
      }))
    : [];

  // Transform model breakdown for pie chart
  const modelBreakdownData = summary?.model_breakdown
    ? Object.entries(summary.model_breakdown).map(([name, value]) => ({
        name,
        value: value
      }))
    : [];

  if (loading) {
    return (
      <div className="min-h-screen p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className={`mt-4 ${themeClasses.subtext}`}>Loading usage data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-3xl font-bold ${themeClasses.text} flex items-center gap-3`}>
              <ChartBarIcon className="h-8 w-8" />
              API Usage Dashboard
            </h1>
            <p className={`mt-2 ${themeClasses.subtext}`}>
              Monitor your API usage, quotas, and performance metrics
            </p>
          </div>
          <button
            onClick={refreshData}
            disabled={refreshing}
            className={`${themeClasses.button} text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all disabled:opacity-50`}
          >
            <ArrowPathIcon className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Quota Status */}
        {quota && (
          <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
            <h2 className={`text-xl font-bold ${themeClasses.text} mb-4`}>
              Monthly Quota Status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className={`text-sm ${themeClasses.subtext} mb-2`}>Usage</p>
                <p className={`text-3xl font-bold ${themeClasses.text}`}>
                  {formatNumber(quota.usage_count)}
                </p>
                <p className={`text-sm ${themeClasses.subtext} mt-1`}>
                  of {quota.quota_limit ? formatNumber(quota.quota_limit) : 'unlimited'}
                </p>
              </div>
              <div>
                <p className={`text-sm ${themeClasses.subtext} mb-2`}>Remaining</p>
                <p className={`text-3xl font-bold ${quota.remaining > 1000 ? 'text-green-500' : 'text-yellow-500'}`}>
                  {quota.quota_limit ? formatNumber(quota.remaining) : '∞'}
                </p>
                {quota.quota_limit && (
                  <div className="mt-2 w-full bg-slate-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        quota.usage_percentage > 90 ? 'bg-red-500' :
                        quota.usage_percentage > 70 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${quota.usage_percentage}%` }}
                    />
                  </div>
                )}
              </div>
              <div>
                <p className={`text-sm ${themeClasses.subtext} mb-2`}>Reset Date</p>
                <p className={`text-xl font-semibold ${themeClasses.text}`}>
                  {quota.reset_date ? formatDate(quota.reset_date) : 'N/A'}
                </p>
                {quota.exceeded && (
                  <p className="text-sm text-red-400 mt-1 flex items-center gap-1">
                    <ExclamationTriangleIcon className="h-4 w-4" />
                    Quota exceeded
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${themeClasses.subtext}`}>Total Requests</p>
                  <p className={`text-2xl font-bold ${themeClasses.text} mt-1`}>
                    {formatNumber(summary.total_requests)}
                  </p>
                </div>
                <BoltIcon className="h-10 w-10 text-blue-500" />
              </div>
            </div>

            <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${themeClasses.subtext}`}>Tokens Used</p>
                  <p className={`text-2xl font-bold ${themeClasses.text} mt-1`}>
                    {formatNumber(summary.total_tokens)}
                  </p>
                </div>
                <ChartBarIcon className="h-10 w-10 text-green-500" />
              </div>
            </div>

            <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${themeClasses.subtext}`}>Total Cost</p>
                  <p className={`text-2xl font-bold ${themeClasses.text} mt-1`}>
                    {formatCost(summary.total_cost)}
                  </p>
                </div>
                <span className="text-3xl">💰</span>
              </div>
            </div>

            <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${themeClasses.subtext}`}>Avg Response Time</p>
                  <p className={`text-2xl font-bold ${themeClasses.text} mt-1`}>
                    {summary.avg_response_time ? `${summary.avg_response_time.toFixed(0)}ms` : 'N/A'}
                  </p>
                </div>
                <ClockIcon className="h-10 w-10 text-purple-500" />
              </div>
            </div>
          </div>
        )}

        {/* Daily Usage Chart */}
        <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
          <div className="flex items-center justify-between mb-6">
            <h2 className={`text-xl font-bold ${themeClasses.text}`}>
              Daily Usage Trend
            </h2>
            <select
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value))}
              className={`${isDark ? 'bg-slate-900 border-slate-600 text-slate-100' : 'bg-gray-50 border-gray-300 text-gray-900'} border rounded-lg px-3 py-1 text-sm`}
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>

          {dailyUsage.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyUsage}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#e5e7eb'} />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  stroke={isDark ? '#9ca3af' : '#6b7280'}
                  style={{ fontSize: '12px' }}
                />
                <YAxis 
                  stroke={isDark ? '#9ca3af' : '#6b7280'}
                  style={{ fontSize: '12px' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#1e293b' : '#ffffff',
                    border: `1px solid ${isDark ? '#475569' : '#e5e7eb'}`,
                    borderRadius: '8px',
                    color: isDark ? '#f1f5f9' : '#111827'
                  }}
                  labelFormatter={(label) => `Date: ${formatDate(label)}`}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="total_requests" 
                  stroke={COLORS.calls} 
                  strokeWidth={2}
                  name="Requests"
                  dot={false}
                />
                <Line 
                  type="monotone" 
                  dataKey="total_tokens" 
                  stroke={COLORS.tokens} 
                  strokeWidth={2}
                  name="Tokens"
                  dot={false}
                />
                <Line 
                  type="monotone" 
                  dataKey="total_cost" 
                  stroke={COLORS.cost} 
                  strokeWidth={2}
                  name="Cost ($)"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center">
              <p className={themeClasses.subtext}>No usage data available</p>
            </div>
          )}
        </div>

        {/* Event & Model Breakdowns */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Event Type Breakdown */}
            {eventBreakdownData.length > 0 && (
              <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
                <h2 className={`text-xl font-bold ${themeClasses.text} mb-4`}>
                  Usage by Event Type
                </h2>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={eventBreakdownData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {eventBreakdownData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={EVENT_COLORS[index % EVENT_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: isDark ? '#1e293b' : '#ffffff',
                        border: `1px solid ${isDark ? '#475569' : '#e5e7eb'}`,
                        borderRadius: '8px'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Model Breakdown */}
            {modelBreakdownData.length > 0 && (
              <div className={`border rounded-xl p-6 ${themeClasses.card}`}>
                <h2 className={`text-xl font-bold ${themeClasses.text} mb-4`}>
                  Usage by Model
                </h2>
                <div className="space-y-3">
                  {modelBreakdownData.slice(0, 5).map((model, index) => {
                    const total = modelBreakdownData.reduce((sum, m) => sum + m.value, 0);
                    const percentage = ((model.value / total) * 100).toFixed(1);
                    return (
                      <div key={model.name}>
                        <div className="flex justify-between items-center mb-1">
                          <span className={`text-sm ${themeClasses.text}`}>{model.name}</span>
                          <span className={`text-sm ${themeClasses.subtext}`}>
                            {formatNumber(model.value)} ({percentage}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="h-2 rounded-full bg-blue-500"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
