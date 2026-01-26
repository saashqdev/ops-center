import React, { useState, useEffect } from 'react';
import {
  BellAlertIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  AdjustmentsHorizontalIcon,
  FunnelIcon
} from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../../contexts/ThemeContext';
import MetricCard from '../../components/analytics/MetricCard';

/**
 * Smart Alerts - AI-Powered Alert System
 * 
 * Intelligent alerting with anomaly detection, noise reduction, and predictions.
 * Reduces alert fatigue by filtering false positives and providing actionable insights.
 * 
 * Epic: 13 - Smart Alerts
 * Features:
 * - Anomaly detection with ML
 * - Alert noise reduction (90%+ reduction)
 * - Predictive alerting
 * - Root cause analysis
 * - Alert grouping and correlation
 */
export default function SmartAlerts() {
  const { currentTheme } = useTheme();
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, active, resolved, muted
  const [severityFilter, setSeverityFilter] = useState('all'); // all, critical, warning, info

  const API_BASE = '/api/v1/smart-alerts';

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
    loadAlerts();
    loadStats();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      loadAlerts();
      loadStats();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [filter, severityFilter]);

  const loadAlerts = async () => {
    try {
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      if (severityFilter !== 'all') params.append('severity', severityFilter);
      
      const response = await fetch(`${API_BASE}/alerts?${params}`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to load alerts:', error);
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/stats`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setStats(data.stats);
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      const response = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        loadAlerts();
      }
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const muteAlert = async (alertId) => {
    try {
      const response = await fetch(`${API_BASE}/alerts/${alertId}/mute`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        loadAlerts();
      }
    } catch (error) {
      console.error('Failed to mute alert:', error);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'warning': return 'yellow';
      case 'info': return 'blue';
      default: return 'gray';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical': return XCircleIcon;
      case 'warning': return ExclamationTriangleIcon;
      case 'info': return CheckCircleIcon;
      default: return BellAlertIcon;
    }
  };

  return (
    <div className={`min-h-screen ${bgClass} p-6`}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-gradient-to-br from-orange-500 to-red-500 rounded-lg">
              <BellAlertIcon className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className={`text-3xl font-bold ${textClass}`}>Smart Alerts</h1>
              <p className={`${subtextClass}`}>AI-powered anomaly detection and intelligent alerting</p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              icon={BellAlertIcon}
              label="Active Alerts"
              value={stats.active_alerts || 0}
              color="red"
            />
            <MetricCard
              icon={CheckCircleIcon}
              label="Resolved (24h)"
              value={stats.resolved_24h || 0}
              color="green"
            />
            <MetricCard
              icon={ChartBarIcon}
              label="Noise Reduction"
              value={stats.noise_reduction_percent || 0}
              suffix="%"
              color="purple"
            />
            <MetricCard
              icon={ExclamationTriangleIcon}
              label="Anomalies Detected"
              value={stats.anomalies_detected || 0}
              color="yellow"
            />
          </div>
        )}

        {/* Filters */}
        <div className={`${cardBg} border rounded-lg p-4 mb-6`}>
          <div className="flex flex-wrap gap-4 items-center">
            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <FunnelIcon className={`w-5 h-5 ${subtextClass}`} />
              <span className={`text-sm font-medium ${textClass}`}>Status:</span>
              <div className="flex gap-2">
                {['all', 'active', 'resolved', 'muted'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setFilter(status)}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      filter === status
                        ? 'bg-purple-600 text-white'
                        : currentTheme === 'light'
                        ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Severity Filter */}
            <div className="flex items-center gap-2">
              <AdjustmentsHorizontalIcon className={`w-5 h-5 ${subtextClass}`} />
              <span className={`text-sm font-medium ${textClass}`}>Severity:</span>
              <div className="flex gap-2">
                {['all', 'critical', 'warning', 'info'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      severityFilter === sev
                        ? 'bg-purple-600 text-white'
                        : currentTheme === 'light'
                        ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {sev.charAt(0).toUpperCase() + sev.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Alerts List */}
        <div className="space-y-4">
          {loading ? (
            <div className={`${cardBg} border rounded-lg p-8 text-center`}>
              <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className={subtextClass}>Loading alerts...</p>
            </div>
          ) : alerts.length === 0 ? (
            <div className={`${cardBg} border rounded-lg p-8 text-center`}>
              <CheckCircleIcon className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <p className={`text-lg font-medium ${textClass} mb-2`}>No alerts found</p>
              <p className={subtextClass}>All systems operating normally</p>
            </div>
          ) : (
            <AnimatePresence>
              {alerts.map((alert) => {
                const SeverityIcon = getSeverityIcon(alert.severity);
                const severityColor = getSeverityColor(alert.severity);
                
                return (
                  <motion.div
                    key={alert.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={`${cardBg} border rounded-lg p-6`}
                  >
                    <div className="flex items-start gap-4">
                      {/* Severity Icon */}
                      <div className={`p-3 rounded-lg bg-${severityColor}-500/20 flex-shrink-0`}>
                        <SeverityIcon className={`w-6 h-6 text-${severityColor}-400`} />
                      </div>

                      {/* Alert Content */}
                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h3 className={`text-lg font-semibold ${textClass}`}>{alert.title}</h3>
                            <div className="flex items-center gap-3 mt-1">
                              <span className={`px-2 py-1 text-xs rounded-full bg-${severityColor}-500/20 text-${severityColor}-400`}>
                                {alert.severity}
                              </span>
                              <span className={`text-xs ${subtextClass} flex items-center gap-1`}>
                                <ClockIcon className="w-4 h-4" />
                                {new Date(alert.timestamp).toLocaleString()}
                              </span>
                            </div>
                          </div>

                          {/* Actions */}
                          {alert.status === 'active' && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => acknowledgeAlert(alert.id)}
                                className="px-3 py-1 text-sm bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded-lg border border-green-500/30 transition-colors"
                              >
                                Acknowledge
                              </button>
                              <button
                                onClick={() => muteAlert(alert.id)}
                                className="px-3 py-1 text-sm bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 rounded-lg border border-gray-500/30 transition-colors"
                              >
                                Mute
                              </button>
                            </div>
                          )}
                        </div>

                        <p className={`${subtextClass} mb-3`}>{alert.message}</p>

                        {/* Anomaly Details */}
                        {alert.anomaly_score && (
                          <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 mb-3">
                            <div className="flex items-center gap-2 mb-2">
                              <ChartBarIcon className="w-4 h-4 text-purple-400" />
                              <span className="text-sm font-medium text-purple-300">Anomaly Detection</span>
                            </div>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                              <div>
                                <div className={subtextClass}>Score</div>
                                <div className={textClass}>{alert.anomaly_score.toFixed(2)}</div>
                              </div>
                              {alert.baseline && (
                                <div>
                                  <div className={subtextClass}>Baseline</div>
                                  <div className={textClass}>{alert.baseline}</div>
                                </div>
                              )}
                              {alert.current_value && (
                                <div>
                                  <div className={subtextClass}>Current</div>
                                  <div className={textClass}>{alert.current_value}</div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Root Cause */}
                        {alert.root_cause && (
                          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                            <div className="text-sm font-medium text-blue-300 mb-1">💡 Root Cause Analysis</div>
                            <p className="text-sm text-blue-200">{alert.root_cause}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  );
}
