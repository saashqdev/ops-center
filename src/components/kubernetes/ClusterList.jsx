import React from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  TrashIcon,
  EyeIcon,
  ChartBarIcon,
  ServerStackIcon,
  CpuChipIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';

/**
 * Epic 16: Kubernetes - Cluster List Component
 * 
 * Displays clusters as cards with health status and quick actions
 */
export default function ClusterList({ clusters, onDelete, onSync, onRefresh }) {
  const getHealthBadge = (healthStatus) => {
    switch (healthStatus) {
      case 'healthy':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
            <CheckCircleIcon className="h-4 w-4 mr-1" />
            Healthy
          </span>
        );
      case 'degraded':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
            <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
            Degraded
          </span>
        );
      case 'critical':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
            <XCircleIcon className="h-4 w-4 mr-1" />
            Critical
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
            Unknown
          </span>
        );
    }
  };

  const getProviderBadge = (provider) => {
    const colors = {
      eks: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
      gke: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      aks: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
      k3s: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      vanilla: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
    };

    const labels = {
      eks: 'AWS EKS',
      gke: 'Google GKE',
      aks: 'Azure AKS',
      k3s: 'k3s',
      vanilla: 'Kubernetes',
    };

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[provider] || 'bg-gray-100 text-gray-800'}`}>
        {labels[provider] || provider}
      </span>
    );
  };

  const getEnvironmentBadge = (environment) => {
    const colors = {
      production: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      staging: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      development: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    };

    return environment ? (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[environment] || 'bg-gray-100 text-gray-800'}`}>
        {environment}
      </span>
    ) : null;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {clusters.map((cluster) => (
        <div
          key={cluster.id}
          className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <ServerStackIcon className="h-8 w-8 text-blue-500" />
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    {cluster.name}
                  </h3>
                  {cluster.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {cluster.description}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {getHealthBadge(cluster.health_status)}
              </div>
            </div>
          </div>

          {/* Metadata */}
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50">
            <div className="flex flex-wrap gap-2">
              {getProviderBadge(cluster.provider)}
              {getEnvironmentBadge(cluster.environment)}
              {cluster.cluster_version && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                  {cluster.cluster_version}
                </span>
              )}
            </div>
          </div>

          {/* Stats Grid */}
          <div className="px-6 py-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <CpuChipIcon className="h-5 w-5 text-gray-400 mr-1" />
                  <span className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {cluster.total_nodes || 0}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Nodes</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <ServerStackIcon className="h-5 w-5 text-gray-400 mr-1" />
                  <span className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {cluster.total_deployments || 0}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Deployments</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <CubeIcon className="h-5 w-5 text-gray-400 mr-1" />
                  <span className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {cluster.total_pods || 0}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Pods</p>
              </div>
            </div>
          </div>

          {/* Last Sync */}
          <div className="px-6 py-3 bg-gray-50 dark:bg-gray-900/50">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500 dark:text-gray-400">
                Last synced: {formatDate(cluster.last_sync_at)}
              </span>
              {cluster.status === 'active' ? (
                <span className="text-green-600 dark:text-green-400">Active</span>
              ) : (
                <span className="text-gray-500 dark:text-gray-400">{cluster.status}</span>
              )}
            </div>
            {cluster.last_error && (
              <div className="mt-2 text-xs text-red-600 dark:text-red-400">
                Error: {cluster.last_error}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-end space-x-2">
              <Link
                to={`/admin/kubernetes/clusters/${cluster.id}`}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 shadow-sm text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <EyeIcon className="h-4 w-4 mr-1" />
                View Details
              </Link>
              <button
                onClick={() => onSync(cluster.id)}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 shadow-sm text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <ArrowPathIcon className="h-4 w-4 mr-1" />
                Sync Now
              </button>
              <button
                onClick={() => onDelete(cluster.id)}
                className="inline-flex items-center px-3 py-1.5 border border-red-300 dark:border-red-600 shadow-sm text-xs font-medium rounded text-red-700 dark:text-red-400 bg-white dark:bg-gray-800 hover:bg-red-50 dark:hover:bg-red-900/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <TrashIcon className="h-4 w-4 mr-1" />
                Delete
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
