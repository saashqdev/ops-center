import React, { useState, useEffect } from 'react';
import {
  ShieldCheckIcon,
  KeyIcon,
  UserGroupIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon,
  ArrowPathIcon,
  CloudIcon,
  DocumentTextIcon,
  LockClosedIcon
} from '@heroicons/react/24/outline';

/**
 * SAML SSO Configuration Dashboard - Epic 20
 * 
 * Features:
 * - SAML provider configuration (Okta, Azure AD, Google, OneLogin)
 * - Active session management
 * - SSO statistics and analytics
 * - SP metadata download
 * - Attribute mapping configuration
 */

export default function SAMLDashboard() {
  const [stats, setStats] = useState(null);
  const [providers, setProviders] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [showAddProvider, setShowAddProvider] = useState(false);

  // Load initial data
  useEffect(() => {
    loadDashboardData();
  }, []);

  useEffect(() => {
    if (selectedProvider) {
      loadProviderSessions(selectedProvider.provider_id);
    }
  }, [selectedProvider]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [statsRes, providersRes, sessionsRes] = await Promise.all([
        fetch('/api/v1/saml/statistics'),
        fetch('/api/v1/saml/providers'),
        fetch('/api/v1/saml/sessions')
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (providersRes.ok) {
        const providerData = await providersRes.json();
        setProviders(providerData);
        if (providerData.length > 0) {
          setSelectedProvider(providerData[0]);
        }
      }
      if (sessionsRes.ok) setSessions(await sessionsRes.json());
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadProviderSessions = async (providerId) => {
    try {
      const response = await fetch(`/api/v1/saml/sessions?provider_id=${providerId}`);
      if (response.ok) {
        setSessions(await response.json());
      }
    } catch (error) {
      console.error('Failed to load provider sessions:', error);
    }
  };

  const downloadMetadata = async (providerId) => {
    try {
      const response = await fetch(`/api/v1/saml/metadata/${providerId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sp-metadata-${providerId}.xml`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Failed to download metadata:', error);
    }
  };

  const getProviderIcon = (name) => {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('okta')) return '🔵';
    if (lowerName.includes('azure') || lowerName.includes('microsoft')) return '🔷';
    if (lowerName.includes('google')) return '🔴';
    if (lowerName.includes('onelogin')) return '🟠';
    return '🔐';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading SAML dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <ShieldCheckIcon className="h-8 w-8 text-indigo-600" />
          SAML Single Sign-On
        </h1>
        <p className="mt-2 text-gray-600">
          Enterprise SSO configuration and session management
        </p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Providers</p>
                <p className="text-3xl font-bold text-gray-900">{stats.active_providers || 0}</p>
              </div>
              <CloudIcon className="h-12 w-12 text-blue-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Sessions</p>
                <p className="text-3xl font-bold text-gray-900">{stats.active_sessions || 0}</p>
              </div>
              <UserGroupIcon className="h-12 w-12 text-green-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Logins (24h)</p>
                <p className="text-3xl font-bold text-gray-900">{stats.logins_24h || 0}</p>
              </div>
              <KeyIcon className="h-12 w-12 text-purple-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Users</p>
                <p className="text-3xl font-bold text-gray-900">{stats.active_users || 0}</p>
              </div>
              <ShieldCheckIcon className="h-12 w-12 text-yellow-500 opacity-20" />
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {[
              { id: 'overview', label: 'Overview', icon: ShieldCheckIcon },
              { id: 'providers', label: 'Providers', icon: CloudIcon },
              { id: 'sessions', label: 'Active Sessions', icon: UserGroupIcon },
              { id: 'settings', label: 'Settings', icon: KeyIcon }
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
                {/* Configured Providers */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Configured Providers</h3>
                  <div className="space-y-2">
                    {providers.slice(0, 5).map((provider) => (
                      <div key={provider.provider_id} className="bg-white rounded-lg p-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{getProviderIcon(provider.name)}</span>
                          <div>
                            <p className="font-medium text-gray-900">{provider.display_name || provider.name}</p>
                            <p className="text-sm text-gray-500">{provider.entity_id}</p>
                          </div>
                        </div>
                        {provider.is_active ? (
                          <CheckCircleIcon className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircleIcon className="h-5 w-5 text-gray-400" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent Sessions */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Recent Sessions</h3>
                  <div className="space-y-2">
                    {sessions.slice(0, 5).map((session) => (
                      <div key={session.session_id} className="bg-white rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">{session.email}</p>
                            <p className="text-sm text-gray-500">
                              {new Date(session.session_start).toLocaleString()}
                            </p>
                          </div>
                          {session.is_active && (
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                              Active
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Quick Setup Guide */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-blue-900 mb-2">Quick Setup Guide</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
                  <li>Create a new SAML provider configuration</li>
                  <li>Download SP metadata and upload to your IdP (Okta, Azure AD, etc.)</li>
                  <li>Copy IdP metadata URL or certificate into provider settings</li>
                  <li>Configure attribute mappings for user provisioning</li>
                  <li>Test SSO login flow</li>
                </ol>
              </div>
            </div>
          )}

          {/* Providers Tab */}
          {activeTab === 'providers' && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">SAML Providers</h3>
                <button
                  onClick={() => setShowAddProvider(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  <PlusIcon className="h-5 w-5" />
                  Add Provider
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {providers.map((provider) => (
                  <div
                    key={provider.provider_id}
                    onClick={() => setSelectedProvider(provider)}
                    className={`bg-white border-2 rounded-lg p-4 cursor-pointer transition-all ${
                      selectedProvider?.provider_id === provider.provider_id
                        ? 'border-indigo-500 shadow-lg'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-3xl">{getProviderIcon(provider.name)}</span>
                        <div>
                          <h4 className="font-semibold text-gray-900">{provider.display_name || provider.name}</h4>
                          <p className="text-xs text-gray-500">{provider.idp_entity_id}</p>
                        </div>
                      </div>
                      {provider.is_active ? (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                          Inactive
                        </span>
                      )}
                    </div>

                    <div className="space-y-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadMetadata(provider.provider_id);
                        }}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm"
                      >
                        <DocumentTextIcon className="h-4 w-4" />
                        Download SP Metadata
                      </button>

                      <a
                        href={`/api/v1/saml/sso/${provider.provider_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 text-sm"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <LockClosedIcon className="h-4 w-4" />
                        Test SSO Login
                      </a>
                    </div>

                    {provider.description && (
                      <p className="text-xs text-gray-600 mt-3">{provider.description}</p>
                    )}
                  </div>
                ))}
              </div>

              {providers.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  <ShieldCheckIcon className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium">No SAML providers configured</p>
                  <p className="text-sm mt-2">Add your first provider to enable SSO</p>
                </div>
              )}
            </div>
          )}

          {/* Sessions Tab */}
          {activeTab === 'sessions' && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Active SAML Sessions</h3>
              {sessions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Session Start</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {sessions.map((session) => (
                        <tr key={session.session_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">{session.email}</td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {providers.find(p => p.provider_id === session.provider_id)?.display_name || 'Unknown'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {new Date(session.session_start).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">{session.ip_address || 'N/A'}</td>
                          <td className="px-6 py-4 text-sm">
                            {session.is_active ? (
                              <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                                Active
                              </span>
                            ) : (
                              <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                                Expired
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <UserGroupIcon className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium">No active sessions</p>
                </div>
              )}
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">SAML Configuration</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Service Provider Entity ID
                    </label>
                    <input
                      type="text"
                      value="https://your-ops-center.com/saml/sp"
                      readOnly
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Assertion Consumer Service (ACS) URL
                    </label>
                    <input
                      type="text"
                      value="https://your-ops-center.com/api/v1/saml/acs"
                      readOnly
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Single Logout (SLO) URL
                    </label>
                    <input
                      type="text"
                      value="https://your-ops-center.com/api/v1/saml/logout"
                      readOnly
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-yellow-900 mb-2">Security Notice</h4>
                <p className="text-sm text-yellow-800">
                  Always use HTTPS for SAML endpoints. Ensure IdP certificates are valid and up-to-date. 
                  Enable assertion signing and encryption for production environments.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
