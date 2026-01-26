import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ServerStackIcon,
  CpuChipIcon,
  CubeIcon,
  CircleStackIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

/**
 * Epic 16: Kubernetes - Cluster Detail Page
 * 
 * Detailed view of a single Kubernetes cluster
 */
export default function ClusterDetail() {
  const { clusterId } = useParams();
  const [cluster, setCluster] = useState(null);
  const [namespaces, setNamespaces] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchClusterData();
  }, [clusterId]);

  const fetchClusterData = async () => {
    try {
      setLoading(true);
      
      // Fetch cluster details
      const clusterRes = await fetch(`/api/v1/k8s/clusters/${clusterId}`, {
        credentials: 'include',
      });
      if (!clusterRes.ok) throw new Error('Failed to fetch cluster');
      const clusterData = await clusterRes.json();
      setCluster(clusterData);

      // Fetch namespaces
      const nsRes = await fetch(`/api/v1/k8s/clusters/${clusterId}/namespaces`, {
        credentials: 'include',
      });
      if (nsRes.ok) {
        const nsData = await nsRes.json();
        setNamespaces(nsData);
      }

      // Fetch nodes
      const nodesRes = await fetch(`/api/v1/k8s/clusters/${clusterId}/nodes`, {
        credentials: 'include',
      });
      if (nodesRes.ok) {
        const nodesData = await nodesRes.json();
        setNodes(nodesData);
      }

      // Fetch health
      const healthRes = await fetch(`/api/v1/k8s/clusters/${clusterId}/health`, {
        credentials: 'include',
      });
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
      }

    } catch (err) {
      console.error('Error fetching cluster data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchClusterData();
    setRefreshing(false);
  };

  const getHealthBadge = (healthStatus) => {
    switch (healthStatus) {
      case 'healthy':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
            <CheckCircleIcon className="h-5 w-5 mr-1.5" />
            Healthy
          </span>
        );
      case 'degraded':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
            <ExclamationTriangleIcon className="h-5 w-5 mr-1.5" />
            Degraded
          </span>
        );
      case 'critical':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
            <XCircleIcon className="h-5 w-5 mr-1.5" />
            Critical
          </span>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600 dark:text-gray-400">Loading cluster details...</p>
        </div>
      </div>
    );
  }

  if (error || !cluster) {
    return (
      <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
        <p className="text-sm text-red-800 dark:text-red-400">
          Error: {error || 'Cluster not found'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/admin/kubernetes"
            className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <ArrowLeftIcon className="h-5 w-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <ServerStackIcon className="h-8 w-8 mr-3 text-blue-500" />
              {cluster.name}
            </h1>
            {cluster.description && (
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {cluster.description}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-3">
          {getHealthBadge(cluster.health_status)}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <ArrowPathIcon className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Cluster Info */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Cluster Information
        </h2>
        <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Provider</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white capitalize">
              {cluster.provider || 'Unknown'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Version</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
              {cluster.cluster_version || 'Unknown'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Environment</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white capitalize">
              {cluster.environment || 'Not set'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">API Server</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white break-all">
              {cluster.api_server_url}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Synced</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
              {cluster.last_sync_at ? new Date(cluster.last_sync_at).toLocaleString() : 'Never'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white capitalize">
              {cluster.status}
            </dd>
          </div>
        </dl>
      </div>

      {/* Resource Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <CpuChipIcon className="h-8 w-8 text-purple-500" />
            <div className="ml-5">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Nodes</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {cluster.total_nodes || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <CircleStackIcon className="h-8 w-8 text-teal-500" />
            <div className="ml-5">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Namespaces</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {cluster.total_namespaces || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <ServerStackIcon className="h-8 w-8 text-cyan-500" />
            <div className="ml-5">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Deployments</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {cluster.total_deployments || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <CubeIcon className="h-8 w-8 text-indigo-500" />
            <div className="ml-5">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Pods</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {cluster.total_pods || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Namespaces Table */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Namespaces ({namespaces.length})
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Team
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Deployments
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Pods
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Total Cost
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {namespaces.map((ns) => (
                <tr key={ns.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    <Link
                      to={`/admin/kubernetes/namespaces/${ns.id}`}
                      className="text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {ns.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      ns.status === 'Active' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                    }`}>
                      {ns.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {ns.team_name || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {ns.deployment_count || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {ns.pod_count || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    ${(ns.total_cost || 0).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Nodes Table */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Nodes ({nodes.length})
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Instance Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  CPU
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Memory
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {nodes.map((node) => (
                <tr key={node.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {node.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 capitalize">
                    {node.node_type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {node.instance_type || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {node.cpu_capacity}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {node.memory_capacity}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      node.status === 'Ready'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                    }`}>
                      {node.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
