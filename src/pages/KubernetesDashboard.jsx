import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ServerStackIcon,
  PlusIcon,
  ArrowPathIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  CubeIcon,
  CircleStackIcon,
  CpuChipIcon,
  CloudIcon,
} from '@heroicons/react/24/outline';
import ClusterList from '../components/kubernetes/ClusterList';
import ClusterRegistrationModal from '../components/kubernetes/ClusterRegistrationModal';

/**
 * Epic 16: Kubernetes Integration - Main Dashboard
 * 
 * Features:
 * - Multi-cluster overview
 * - Health monitoring
 * - Cost tracking
 * - Quick actions
 */
export default function KubernetesDashboard() {
  const [clusters, setClusters] = useState([]);
  const [stats, setStats] = useState({
    total_clusters: 0,
    healthy_clusters: 0,
    total_nodes: 0,
    total_pods: 0,
    total_deployments: 0,
    total_namespaces: 0,
    monthly_cost: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchClusters();
    fetchStats();
  }, []);

  const fetchClusters = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/k8s/clusters', {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch clusters');
      }

      const data = await response.json();
      setClusters(data);
    } catch (err) {
      console.error('Error fetching clusters:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      // Aggregate stats from clusters
      const response = await fetch('/api/v1/k8s/clusters', {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch stats');
      }

      const clusters = await response.json();
      
      const aggregated = {
        total_clusters: clusters.length,
        healthy_clusters: clusters.filter(c => c.health_status === 'healthy').length,
        total_nodes: clusters.reduce((sum, c) => sum + (c.total_nodes || 0), 0),
        total_pods: clusters.reduce((sum, c) => sum + (c.total_pods || 0), 0),
        total_deployments: clusters.reduce((sum, c) => sum + (c.total_deployments || 0), 0),
        total_namespaces: clusters.reduce((sum, c) => sum + (c.total_namespaces || 0), 0),
        monthly_cost: 0, // Will be calculated from cost API
      };

      setStats(aggregated);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchClusters(), fetchStats()]);
    setRefreshing(false);
  };

  const handleRegisterSuccess = () => {
    setShowRegisterModal(false);
    handleRefresh();
  };

  const handleDeleteCluster = async (clusterId) => {
    if (!confirm('Are you sure you want to delete this cluster? This will remove all associated data.')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/k8s/clusters/${clusterId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to delete cluster');
      }

      handleRefresh();
    } catch (err) {
      console.error('Error deleting cluster:', err);
      alert('Failed to delete cluster: ' + err.message);
    }
  };

  const handleTriggerSync = async (clusterId) => {
    try {
      const response = await fetch(`/api/v1/k8s/clusters/${clusterId}/sync`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to trigger sync');
      }

      alert('Cluster sync triggered successfully');
    } catch (err) {
      console.error('Error triggering sync:', err);
      alert('Failed to trigger sync: ' + err.message);
    }
  };

  const StatCard = ({ icon: Icon, label, value, color = 'blue', trend }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 rounded-md bg-${color}-500 p-3`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
              {label}
            </dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                {value}
              </div>
              {trend && (
                <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                  trend > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trend > 0 ? '+' : ''}{trend}%
                </div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  );

  if (loading && clusters.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600 dark:text-gray-400">Loading Kubernetes clusters...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <ServerStackIcon className="h-8 w-8 mr-3 text-blue-500" />
            Kubernetes Clusters
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage and monitor your Kubernetes infrastructure
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <ArrowPathIcon className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowRegisterModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Register Cluster
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-400">
                Error loading clusters
              </h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                {error}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={CloudIcon}
          label="Total Clusters"
          value={stats.total_clusters}
          color="blue"
        />
        <StatCard
          icon={CheckCircleIcon}
          label="Healthy Clusters"
          value={stats.healthy_clusters}
          color="green"
        />
        <StatCard
          icon={CpuChipIcon}
          label="Total Nodes"
          value={stats.total_nodes}
          color="purple"
        />
        <StatCard
          icon={CubeIcon}
          label="Total Pods"
          value={stats.total_pods}
          color="indigo"
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          icon={ServerStackIcon}
          label="Deployments"
          value={stats.total_deployments}
          color="cyan"
        />
        <StatCard
          icon={CircleStackIcon}
          label="Namespaces"
          value={stats.total_namespaces}
          color="teal"
        />
        <StatCard
          icon={ChartBarIcon}
          label="Monthly Cost"
          value={`$${stats.monthly_cost.toFixed(2)}`}
          color="yellow"
        />
      </div>

      {/* Clusters List */}
      {clusters.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <ServerStackIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No Kubernetes clusters
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Get started by registering your first Kubernetes cluster
          </p>
          <div className="mt-6">
            <button
              onClick={() => setShowRegisterModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              Register Cluster
            </button>
          </div>
        </div>
      ) : (
        <ClusterList
          clusters={clusters}
          onDelete={handleDeleteCluster}
          onSync={handleTriggerSync}
          onRefresh={handleRefresh}
        />
      )}

      {/* Registration Modal */}
      {showRegisterModal && (
        <ClusterRegistrationModal
          onClose={() => setShowRegisterModal(false)}
          onSuccess={handleRegisterSuccess}
        />
      )}
    </div>
  );
}
