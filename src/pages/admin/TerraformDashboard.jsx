import React, { useState, useEffect } from 'react';
import {
  CloudIcon,
  CubeIcon,
  ServerIcon,
  CodeBracketIcon,
  PlayIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  LockClosedIcon,
  DocumentTextIcon,
  PlusIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

/**
 * Terraform/IaC Integration Dashboard - Epic 19
 * 
 * Features:
 * - Workspace management (create, list, lock/unlock)
 * - Resource tracking with status indicators
 * - Execution history (plan/apply/destroy)
 * - Template library browser
 * - Drift detection alerts
 * - Multi-cloud support (AWS, Azure, GCP, K8s)
 */

export default function TerraformDashboard() {
  const [stats, setStats] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [resources, setResources] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [drifts, setDrifts] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  // Load initial data
  useEffect(() => {
    loadDashboardData();
  }, []);

  useEffect(() => {
    if (selectedWorkspace) {
      loadWorkspaceDetails(selectedWorkspace.workspace_id);
    }
  }, [selectedWorkspace]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [statsRes, workspacesRes, templatesRes] = await Promise.all([
        fetch('/api/v1/terraform/dashboard/statistics'),
        fetch('/api/v1/terraform/workspaces'),
        fetch('/api/v1/terraform/templates')
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (workspacesRes.ok) {
        const workspaceData = await workspacesRes.json();
        setWorkspaces(workspaceData);
        if (workspaceData.length > 0) {
          setSelectedWorkspace(workspaceData[0]);
        }
      }
      if (templatesRes.ok) setTemplates(await templatesRes.json());
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadWorkspaceDetails = async (workspaceId) => {
    try {
      const [resourcesRes, executionsRes, driftsRes] = await Promise.all([
        fetch(`/api/v1/terraform/workspaces/${workspaceId}/resources`),
        fetch(`/api/v1/terraform/workspaces/${workspaceId}/executions?limit=10`),
        fetch(`/api/v1/terraform/workspaces/${workspaceId}/drifts?resolved=false`)
      ]);

      if (resourcesRes.ok) setResources(await resourcesRes.json());
      if (executionsRes.ok) setExecutions(await executionsRes.json());
      if (driftsRes.ok) setDrifts(await driftsRes.json());
    } catch (error) {
      console.error('Failed to load workspace details:', error);
    }
  };

  const getCloudIcon = (provider) => {
    const icons = {
      aws: '☁️',
      azure: '🔷',
      gcp: '🔵',
      kubernetes: '☸️',
      digitalocean: '🌊',
      multi: '🌐'
    };
    return icons[provider] || '☁️';
  };

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-800',
      tainted: 'bg-yellow-100 text-yellow-800',
      destroyed: 'bg-gray-100 text-gray-800',
      pending: 'bg-blue-100 text-blue-800'
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  const getExecutionStatusIcon = (status) => {
    if (status === 'success') return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    if (status === 'failed') return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
    return <ClockIcon className="h-5 w-5 text-blue-500" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading Terraform dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <ServerIcon className="h-8 w-8 text-indigo-600" />
          Terraform / IaC Management
        </h1>
        <p className="mt-2 text-gray-600">
          Infrastructure as Code management across multiple cloud providers
        </p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Workspaces</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_workspaces || 0}</p>
              </div>
              <CloudIcon className="h-12 w-12 text-blue-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Resources</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_resources || 0}</p>
              </div>
              <CubeIcon className="h-12 w-12 text-green-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Drift Detections</p>
                <p className="text-3xl font-bold text-gray-900">{stats.unresolved_drifts || 0}</p>
              </div>
              <ExclamationTriangleIcon className="h-12 w-12 text-yellow-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Templates</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_templates || 0}</p>
              </div>
              <DocumentTextIcon className="h-12 w-12 text-purple-500 opacity-20" />
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {[
              { id: 'overview', label: 'Overview', icon: ServerIcon },
              { id: 'workspaces', label: 'Workspaces', icon: CloudIcon },
              { id: 'resources', label: 'Resources', icon: CubeIcon },
              { id: 'executions', label: 'Executions', icon: PlayIcon },
              { id: 'templates', label: 'Templates', icon: CodeBracketIcon },
              { id: 'drifts', label: 'Drift Detections', icon: ExclamationTriangleIcon }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Workspaces */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Recent Workspaces</h3>
                  <div className="space-y-2">
                    {workspaces.slice(0, 5).map((ws) => (
                      <div key={ws.workspace_id} className="bg-white rounded-lg p-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{getCloudIcon(ws.cloud_provider)}</span>
                          <div>
                            <p className="font-medium text-gray-900">{ws.name}</p>
                            <p className="text-sm text-gray-500">{ws.environment} • {ws.resource_count} resources</p>
                          </div>
                        </div>
                        {ws.locked && <LockClosedIcon className="h-5 w-5 text-yellow-500" />}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Popular Templates */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Popular Templates</h3>
                  <div className="space-y-2">
                    {templates.slice(0, 5).map((template) => (
                      <div key={template.template_id} className="bg-white rounded-lg p-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{getCloudIcon(template.cloud_provider)}</span>
                          <div>
                            <p className="font-medium text-gray-900">{template.name}</p>
                            <p className="text-sm text-gray-500">{template.category} • {template.downloads_count} downloads</p>
                          </div>
                        </div>
                        <CodeBracketIcon className="h-5 w-5 text-gray-400" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Workspaces Tab */}
          {activeTab === 'workspaces' && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Workspaces</h3>
                <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                  <PlusIcon className="h-5 w-5" />
                  Create Workspace
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {workspaces.map((ws) => (
                  <div
                    key={ws.workspace_id}
                    onClick={() => setSelectedWorkspace(ws)}
                    className={`bg-white border-2 rounded-lg p-4 cursor-pointer transition-all ${
                      selectedWorkspace?.workspace_id === ws.workspace_id
                        ? 'border-indigo-500 shadow-lg'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-3xl">{getCloudIcon(ws.cloud_provider)}</span>
                        <div>
                          <h4 className="font-semibold text-gray-900">{ws.name}</h4>
                          <p className="text-sm text-gray-500">{ws.environment}</p>
                        </div>
                      </div>
                      {ws.locked && <LockClosedIcon className="h-5 w-5 text-yellow-500" />}
                    </div>
                    <div className="flex justify-between text-sm text-gray-600">
                      <span>{ws.resource_count} resources</span>
                      <span>{ws.drift_count} drifts</span>
                    </div>
                    {ws.last_apply_at && (
                      <p className="text-xs text-gray-400 mt-2">
                        Last apply: {new Date(ws.last_apply_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Resources Tab */}
          {activeTab === 'resources' && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Resources</h3>
              {selectedWorkspace ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Resource</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {resources.map((resource) => (
                        <tr key={resource.resource_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">{resource.name || resource.address}</td>
                          <td className="px-6 py-4 text-sm text-gray-500">{resource.resource_type}</td>
                          <td className="px-6 py-4 text-sm text-gray-500">{resource.provider}</td>
                          <td className="px-6 py-4 text-sm">{getStatusBadge(resource.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Select a workspace to view resources</p>
              )}
            </div>
          )}

          {/* Executions Tab */}
          {activeTab === 'executions' && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Execution History</h3>
              {selectedWorkspace ? (
                <div className="space-y-3">
                  {executions.map((exec) => (
                    <div key={exec.execution_id} className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        {getExecutionStatusIcon(exec.status)}
                        <div>
                          <p className="font-medium text-gray-900">{exec.execution_type.toUpperCase()}</p>
                          <p className="text-sm text-gray-500">
                            {new Date(exec.triggered_at).toLocaleString()}
                            {exec.duration_seconds && ` • ${exec.duration_seconds}s`}
                          </p>
                        </div>
                      </div>
                      <div className="text-right text-sm text-gray-600">
                        {exec.resources_created > 0 && <p>+{exec.resources_created} created</p>}
                        {exec.resources_changed > 0 && <p>~{exec.resources_changed} changed</p>}
                        {exec.resources_destroyed > 0 && <p>-{exec.resources_destroyed} destroyed</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Select a workspace to view executions</p>
              )}
            </div>
          )}

          {/* Templates Tab */}
          {activeTab === 'templates' && (
            <div>
              <h3 className="text-lg font-semibold mb-4">IaC Template Library</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {templates.map((template) => (
                  <div key={template.template_id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{getCloudIcon(template.cloud_provider)}</span>
                        <div>
                          <h4 className="font-semibold text-gray-900">{template.name}</h4>
                          <p className="text-sm text-gray-500">{template.category}</p>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{template.downloads_count} downloads</span>
                      <span>v{template.version}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Drifts Tab */}
          {activeTab === 'drifts' && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Drift Detections</h3>
              {selectedWorkspace ? (
                <div className="space-y-3">
                  {drifts.length > 0 ? (
                    drifts.map((drift) => (
                      <div key={drift.drift_id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <div className="flex items-start gap-3">
                          <ExclamationTriangleIcon className="h-6 w-6 text-yellow-500 flex-shrink-0" />
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{drift.drift_type}</p>
                            <p className="text-sm text-gray-600 mt-1">{drift.description}</p>
                            <p className="text-xs text-gray-500 mt-2">
                              Detected: {new Date(drift.detected_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <CheckCircleIcon className="h-12 w-12 text-green-500 mx-auto mb-2" />
                      <p className="text-gray-500">No drift detected</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Select a workspace to view drift detections</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
