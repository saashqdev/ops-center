import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ServerStackIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
  CpuChipIcon,
  CloudIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  SignalIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';
import MetricCard from '../../components/analytics/MetricCard';

export default function FleetDashboard() {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fleetSummary, setFleetSummary] = useState(null);
  const [servers, setServers] = useState([]);
  const [workerStatus, setWorkerStatus] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterHealth, setFilterHealth] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedServer, setSelectedServer] = useState(null);

  const fetchFleetData = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    try {
      // Fetch fleet summary
      const summaryResponse = await fetch('/api/v1/fleet/summary', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (summaryResponse.ok) {
        const data = await summaryResponse.json();
        setFleetSummary(data.summary);
      }

      // Fetch servers list
      const serversResponse = await fetch('/api/v1/fleet/servers?limit=500', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (serversResponse.ok) {
        const data = await serversResponse.json();
        setServers(data.servers || []);
      }

      // Fetch worker status (admin only)
      try {
        const workerResponse = await fetch('/api/v1/fleet/workers/status', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (workerResponse.ok) {
          const data = await workerResponse.json();
          setWorkerStatus(data);
        }
      } catch (err) {
        // Not admin or endpoint unavailable
        setWorkerStatus(null);
      }

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch fleet data:', error);
      setLoading(false);
    } finally {
      if (showRefreshing) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchFleetData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => fetchFleetData(false), 30000);
    return () => clearInterval(interval);
  }, [fetchFleetData]);

  const handleRefresh = () => {
    fetchFleetData(true);
  };

  const handleServerClick = (server) => {
    setSelectedServer(server);
  };

  const handleHealthCheck = async (serverId) => {
    try {
      const response = await fetch(`/api/v1/fleet/servers/${serverId}/health-check`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        // Refresh data to show updated health
        fetchFleetData(false);
      }
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500" />;
      case 'critical':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      case 'unreachable':
        return <XCircleIcon className="w-5 h-5 text-gray-400" />;
      default:
        return <ClockIcon className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
      maintenance: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status] || colors.inactive}`}>
        {status}
      </span>
    );
  };

  const filteredServers = servers.filter(server => {
    const matchesStatus = filterStatus === 'all' || server.status === filterStatus;
    const matchesHealth = filterHealth === 'all' || server.health_status === filterHealth;
    const matchesSearch = !searchQuery || 
      server.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (server.region && server.region.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (server.environment && server.environment.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesHealth && matchesSearch;
  });

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Fleet Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Multi-server management and monitoring
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            <PlusIcon className="w-4 h-4" />
            Register Server
          </button>
        </div>
      </div>

      {/* Fleet Summary Cards */}
      {fleetSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Total Servers"
            value={fleetSummary.total_servers || 0}
            icon={ServerStackIcon}
            iconColor="text-blue-600"
            iconBgColor="bg-blue-100 dark:bg-blue-900"
          />
          <MetricCard
            title="Healthy Servers"
            value={fleetSummary.healthy_servers || 0}
            subtitle={`${fleetSummary.degraded_servers || 0} degraded`}
            icon={CheckCircleIcon}
            iconColor="text-green-600"
            iconBgColor="bg-green-100 dark:bg-green-900"
          />
          <MetricCard
            title="Critical Issues"
            value={fleetSummary.critical_servers || 0}
            subtitle={`${fleetSummary.unreachable_servers || 0} unreachable`}
            icon={ExclamationTriangleIcon}
            iconColor="text-red-600"
            iconBgColor="bg-red-100 dark:bg-red-900"
          />
          <MetricCard
            title="Active Servers"
            value={fleetSummary.active_servers || 0}
            subtitle={`${fleetSummary.regions_count || 0} regions`}
            icon={CloudIcon}
            iconColor="text-purple-600"
            iconBgColor="bg-purple-100 dark:bg-purple-900"
          />
        </div>
      )}

      {/* Worker Status (Admin Only) */}
      {workerStatus && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <Cog6ToothIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Background Workers
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Health Worker */}
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Health Check Worker
                </span>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${workerStatus.health_worker?.running ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {workerStatus.health_worker?.running ? 'Running' : 'Stopped'}
                  </span>
                </div>
              </div>
              <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                <div className="flex justify-between">
                  <span>Interval:</span>
                  <span className="font-medium">{workerStatus.health_worker?.interval_seconds}s</span>
                </div>
                <div className="flex justify-between">
                  <span>Success Rate:</span>
                  <span className="font-medium">{workerStatus.health_worker?.success_rate?.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Checks:</span>
                  <span className="font-medium">{workerStatus.health_worker?.checks_performed || 0}</span>
                </div>
                {workerStatus.health_worker?.last_run && (
                  <div className="flex justify-between">
                    <span>Last Run:</span>
                    <span className="font-medium">{formatTimestamp(workerStatus.health_worker.last_run)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Metrics Worker */}
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Metrics Collection Worker
                </span>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${workerStatus.metrics_worker?.running ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {workerStatus.metrics_worker?.running ? 'Running' : 'Stopped'}
                  </span>
                </div>
              </div>
              <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                <div className="flex justify-between">
                  <span>Interval:</span>
                  <span className="font-medium">{workerStatus.metrics_worker?.interval_seconds}s</span>
                </div>
                <div className="flex justify-between">
                  <span>Success Rate:</span>
                  <span className="font-medium">{workerStatus.metrics_worker?.success_rate?.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Collections:</span>
                  <span className="font-medium">{workerStatus.metrics_worker?.collections_performed || 0}</span>
                </div>
                {workerStatus.metrics_worker?.last_run && (
                  <div className="flex justify-between">
                    <span>Last Run:</span>
                    <span className="font-medium">{formatTimestamp(workerStatus.metrics_worker.last_run)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Filters and Search */}
      <div className="flex flex-wrap gap-4 items-center bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search servers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        
        <div className="flex gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="maintenance">Maintenance</option>
          </select>
          
          <select
            value={filterHealth}
            onChange={(e) => setFilterHealth(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          >
            <option value="all">All Health</option>
            <option value="healthy">Healthy</option>
            <option value="degraded">Degraded</option>
            <option value="critical">Critical</option>
            <option value="unreachable">Unreachable</option>
          </select>
        </div>
      </div>

      {/* Server List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Servers ({filteredServers.length})
          </h2>
        </div>

        {filteredServers.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
            <ServerStackIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No servers found</p>
            {(filterStatus !== 'all' || filterHealth !== 'all' || searchQuery) && (
              <button
                onClick={() => {
                  setFilterStatus('all');
                  setFilterHealth('all');
                  setSearchQuery('');
                }}
                className="mt-2 text-blue-600 hover:text-blue-700 text-sm"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Server
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Health
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Region / Environment
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Last Seen
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredServers.map((server) => (
                  <motion.tr
                    key={server.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                    onClick={() => handleServerClick(server)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <CpuChipIcon className="w-5 h-5 text-gray-400 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {server.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {server.hostname}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(server.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getHealthIcon(server.health_status)}
                        <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                          {server.health_status || 'Unknown'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                      <div>{server.region || '-'}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-500">
                        {server.environment || '-'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                      {formatTimestamp(server.last_seen_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleHealthCheck(server.id);
                          }}
                          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                          title="Check Health"
                        >
                          <SignalIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleServerClick(server);
                          }}
                          className="text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                          title="View Details"
                        >
                          <ChartBarIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Server Details Modal (Placeholder) */}
      {selectedServer && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedServer(null)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedServer.name}
              </h3>
              <button
                onClick={() => setSelectedServer(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <XCircleIcon className="w-6 h-6" />
              </button>
            </div>
            
            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Hostname:</span>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedServer.hostname}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">API URL:</span>
                  <p className="font-medium text-gray-900 dark:text-white text-xs break-all">{selectedServer.api_url}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Region:</span>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedServer.region || '-'}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Environment:</span>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedServer.environment || '-'}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Status:</span>
                  <p className="font-medium text-gray-900 dark:text-white">{getStatusBadge(selectedServer.status)}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Health:</span>
                  <div className="flex items-center gap-2 mt-1">
                    {getHealthIcon(selectedServer.health_status)}
                    <span className="font-medium text-gray-900 dark:text-white capitalize">
                      {selectedServer.health_status || 'Unknown'}
                    </span>
                  </div>
                </div>
              </div>
              
              {selectedServer.tags && selectedServer.tags.length > 0 && (
                <div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">Tags:</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedServer.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedServer.description && (
                <div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">Description:</span>
                  <p className="mt-1 text-sm text-gray-900 dark:text-white">{selectedServer.description}</p>
                </div>
              )}
              
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => handleHealthCheck(selectedServer.id)}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Run Health Check
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
