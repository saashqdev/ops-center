/**
 * OpenWebUI - Unicorn Chat Management Page
 * 
 * Embedded Open WebUI chat interface with status dashboard.
 * Features: iframe embed, health status, model count, user stats, quick-launch.
 * 
 * Backend: /api/v1/openwebui (proxies to Open WebUI container)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
  ChatBubbleLeftRightIcon,
  ArrowTopRightOnSquareIcon,
  ServerIcon,
  CpuChipIcon,
  UsersIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  SparklesIcon,
  GlobeAltIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  WrenchScrewdriverIcon,
  ArrowsRightLeftIcon,
} from '@heroicons/react/24/outline';

const FEATURES = [
  { icon: CpuChipIcon, label: 'Multi-model chat', desc: 'Switch between all LiteLLM models' },
  { icon: DocumentTextIcon, label: 'RAG / Documents', desc: 'Upload files for context-aware chat' },
  { icon: ShieldCheckIcon, label: 'SSO Login', desc: 'Single sign-on via Keycloak' },
  { icon: ClockIcon, label: 'History', desc: 'Persistent conversation history' },
  { icon: SparklesIcon, label: 'Markdown & Code', desc: 'Rich rendering and syntax highlighting' },
  { icon: UsersIcon, label: 'Multi-user', desc: 'Shared workspace with role-based access' },
];

export default function OpenWebUI() {
  const { currentTheme } = useTheme();

  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [models, setModels] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showIframe, setShowIframe] = useState(true);
  const [chatUrl, setChatUrl] = useState('');
  const [adminAction, setAdminAction] = useState(null); // 'seeding' | 'syncing' | null
  const [actionResult, setActionResult] = useState(null);

  // Theme colors
  const tc = {
    bg: currentTheme === 'unicorn' ? 'bg-purple-950/50' : currentTheme === 'light' ? 'bg-gray-50' : 'bg-slate-900',
    card: currentTheme === 'unicorn' ? 'bg-purple-900/50 backdrop-blur-xl border-white/20' : currentTheme === 'light' ? 'bg-white border-gray-200' : 'bg-slate-800 border-slate-700',
    text: currentTheme === 'unicorn' ? 'text-purple-100' : currentTheme === 'light' ? 'text-gray-900' : 'text-slate-100',
    subtext: currentTheme === 'unicorn' ? 'text-purple-300' : currentTheme === 'light' ? 'text-gray-600' : 'text-slate-400',
    muted: currentTheme === 'unicorn' ? 'text-purple-400' : currentTheme === 'light' ? 'text-gray-500' : 'text-slate-500',
    accent: currentTheme === 'unicorn' ? 'bg-purple-600 hover:bg-purple-700' : currentTheme === 'light' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-emerald-600 hover:bg-emerald-700',
    badge: currentTheme === 'unicorn' ? 'bg-purple-700/50 text-purple-200' : currentTheme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-slate-700 text-slate-300',
    border: currentTheme === 'unicorn' ? 'border-white/10' : currentTheme === 'light' ? 'border-gray-200' : 'border-slate-700',
  };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, configRes, modelsRes, statsRes] = await Promise.all([
        fetch('/api/v1/openwebui/status', { credentials: 'include' }).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/v1/openwebui/config', { credentials: 'include' }).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/v1/openwebui/models', { credentials: 'include' }).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/v1/openwebui/stats', { credentials: 'include' }).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      setStatus(statusRes);
      setConfig(configRes);
      setModels(modelsRes);
      setStats(statsRes);
      if (configRes?.chat_url) {
        setChatUrl(configRes.chat_url);
      }
    } catch (err) {
      console.error('Error fetching Open WebUI data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const openExternal = () => {
    if (chatUrl) {
      window.open(chatUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const seedAppRecords = async () => {
    setAdminAction('seeding');
    setActionResult(null);
    try {
      const res = await fetch('/api/v1/openwebui/seed', { method: 'POST', credentials: 'include' });
      const data = await res.json();
      setActionResult({ type: 'seed', success: res.ok, data });
    } catch (err) {
      setActionResult({ type: 'seed', success: false, data: { error: err.message } });
    } finally {
      setAdminAction(null);
    }
  };

  const syncModels = async () => {
    setAdminAction('syncing');
    setActionResult(null);
    try {
      const res = await fetch('/api/v1/openwebui/sync-models', { method: 'POST', credentials: 'include' });
      const data = await res.json();
      setActionResult({ type: 'sync', success: res.ok, data });
    } catch (err) {
      setActionResult({ type: 'sync', success: false, data: { error: err.message } });
    } finally {
      setAdminAction(null);
    }
  };

  const StatusIcon = ({ healthy }) => {
    if (healthy === true) return <CheckCircleIcon className="w-5 h-5 text-emerald-400" />;
    if (healthy === false) return <XCircleIcon className="w-5 h-5 text-red-400" />;
    return <ExclamationTriangleIcon className="w-5 h-5 text-amber-400" />;
  };

  return (
    <div className={`min-h-screen ${tc.bg} p-4 md:p-6`}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl ${tc.accent} text-white`}>
            <ChatBubbleLeftRightIcon className="w-7 h-7" />
          </div>
          <div>
            <h1 className={`text-2xl font-bold ${tc.text}`}>Unicorn Chat</h1>
            <p className={`text-sm ${tc.subtext}`}>AI Chat Interface powered by Open WebUI + LiteLLM</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchAll}
            className={`px-3 py-2 rounded-lg border ${tc.border} ${tc.subtext} hover:opacity-80 transition-all flex items-center gap-2 text-sm`}
          >
            <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowIframe(!showIframe)}
            className={`px-3 py-2 rounded-lg border ${tc.border} ${tc.subtext} hover:opacity-80 transition-all text-sm`}
          >
            {showIframe ? 'Dashboard' : 'Chat View'}
          </button>
          <button
            onClick={openExternal}
            className={`px-4 py-2 rounded-lg ${tc.accent} text-white font-medium transition-all flex items-center gap-2 text-sm`}
          >
            <ArrowTopRightOnSquareIcon className="w-4 h-4" />
            Open Full Chat
          </button>
        </div>
      </div>

      {showIframe && chatUrl ? (
        /* ── Embedded Chat View ──────────────────────────── */
        <div className={`rounded-xl border ${tc.border} overflow-hidden shadow-2xl`} style={{ height: 'calc(100vh - 160px)' }}>
          <iframe
            src={chatUrl}
            title="Unicorn Chat - Open WebUI"
            className="w-full h-full"
            style={{ border: 'none' }}
            allow="clipboard-read; clipboard-write; microphone"
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-downloads"
          />
        </div>
      ) : (
        /* ── Dashboard View ──────────────────────────────── */
        <div className="space-y-6">
          {/* Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Service Status */}
            <div className={`rounded-xl border p-4 ${tc.card}`}>
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-medium ${tc.muted}`}>Status</span>
                <StatusIcon healthy={status?.healthy} />
              </div>
              <p className={`text-xl font-bold ${tc.text}`}>
                {status?.healthy === true ? 'Online' : status?.healthy === false ? 'Offline' : 'Unknown'}
              </p>
              {status?.response_time_ms && (
                <p className={`text-xs ${tc.muted} mt-1`}>{status.response_time_ms}ms response</p>
              )}
            </div>

            {/* Models */}
            <div className={`rounded-xl border p-4 ${tc.card}`}>
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-medium ${tc.muted}`}>Models</span>
                <CpuChipIcon className={`w-5 h-5 ${tc.muted}`} />
              </div>
              <p className={`text-xl font-bold ${tc.text}`}>
                {models?.total ?? '—'}
              </p>
              <p className={`text-xs ${tc.muted} mt-1`}>via LiteLLM proxy</p>
            </div>

            {/* External URL */}
            <div className={`rounded-xl border p-4 ${tc.card}`}>
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-medium ${tc.muted}`}>URL</span>
                <GlobeAltIcon className={`w-5 h-5 ${tc.muted}`} />
              </div>
              <a
                href={chatUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={`text-sm font-medium ${currentTheme === 'unicorn' ? 'text-purple-300 hover:text-purple-100' : currentTheme === 'light' ? 'text-blue-600 hover:text-blue-800' : 'text-blue-400 hover:text-blue-300'} truncate block`}
              >
                {chatUrl || '—'}
              </a>
              <p className={`text-xs ${tc.muted} mt-1`}>Traefik reverse proxy</p>
            </div>

            {/* Version */}
            <div className={`rounded-xl border p-4 ${tc.card}`}>
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-medium ${tc.muted}`}>Version</span>
                <ServerIcon className={`w-5 h-5 ${tc.muted}`} />
              </div>
              <p className={`text-xl font-bold ${tc.text}`}>
                {status?.version?.version || '—'}
              </p>
              <p className={`text-xs ${tc.muted} mt-1`}>Open WebUI</p>
            </div>
          </div>

          {/* Features Grid */}
          <div className={`rounded-xl border p-6 ${tc.card}`}>
            <h2 className={`text-lg font-semibold ${tc.text} mb-4`}>Features</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {FEATURES.map(({ icon: Icon, label, desc }) => (
                <div key={label} className={`flex items-start gap-3 p-3 rounded-lg ${currentTheme === 'unicorn' ? 'bg-purple-800/30' : currentTheme === 'light' ? 'bg-gray-50' : 'bg-slate-700/50'}`}>
                  <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${currentTheme === 'unicorn' ? 'text-purple-300' : currentTheme === 'light' ? 'text-blue-500' : 'text-emerald-400'}`} />
                  <div>
                    <p className={`text-sm font-medium ${tc.text}`}>{label}</p>
                    <p className={`text-xs ${tc.muted}`}>{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Models List */}
          {models?.models?.length > 0 && (
            <div className={`rounded-xl border p-6 ${tc.card}`}>
              <h2 className={`text-lg font-semibold ${tc.text} mb-4`}>Available Models ({models.total})</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {models.models.map((m) => (
                  <div key={m.id} className={`flex items-center gap-2 p-2 rounded-lg ${currentTheme === 'unicorn' ? 'bg-purple-800/20' : currentTheme === 'light' ? 'bg-gray-50' : 'bg-slate-700/30'}`}>
                    <CpuChipIcon className={`w-4 h-4 flex-shrink-0 ${tc.muted}`} />
                    <div className="truncate">
                      <p className={`text-sm font-mono truncate ${tc.text}`}>{m.name || m.id}</p>
                      {m.owned_by && <p className={`text-xs ${tc.muted}`}>{m.owned_by}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Usage Stats */}
          {stats && (stats.total_chats > 0 || stats.total_messages > 0) && (
            <div className={`rounded-xl border p-6 ${tc.card}`}>
              <h2 className={`text-lg font-semibold ${tc.text} mb-4 flex items-center gap-2`}>
                <ChartBarIcon className="w-5 h-5" /> Your Usage
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                <div className={`p-4 rounded-lg ${currentTheme === 'unicorn' ? 'bg-purple-800/30' : currentTheme === 'light' ? 'bg-gray-50' : 'bg-slate-700/50'}`}>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-1`}>Total Chats</p>
                  <p className={`text-2xl font-bold ${tc.text}`}>{stats.total_chats}</p>
                </div>
                <div className={`p-4 rounded-lg ${currentTheme === 'unicorn' ? 'bg-purple-800/30' : currentTheme === 'light' ? 'bg-gray-50' : 'bg-slate-700/50'}`}>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-1`}>Total Messages</p>
                  <p className={`text-2xl font-bold ${tc.text}`}>{stats.total_messages}</p>
                </div>
              </div>
              {stats.recent_activity?.length > 0 && (
                <div>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-2`}>Recent Activity</p>
                  <div className="space-y-1">
                    {stats.recent_activity.slice(0, 5).map((a, i) => (
                      <div key={i} className={`flex items-center justify-between text-xs ${tc.subtext} py-1`}>
                        <span className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full ${a.event === 'message' ? 'bg-emerald-400' : 'bg-blue-400'}`} />
                          {a.event} {a.model && `(${a.model})`}
                        </span>
                        <span className={tc.muted}>
                          {a.timestamp ? new Date(a.timestamp).toLocaleString() : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Admin Actions */}
          <div className={`rounded-xl border p-6 ${tc.card}`}>
            <h2 className={`text-lg font-semibold ${tc.text} mb-4 flex items-center gap-2`}>
              <WrenchScrewdriverIcon className="w-5 h-5" /> Admin Actions
            </h2>

            {/* Action result banner */}
            {actionResult && (
              <div className={`mb-4 p-3 rounded-lg text-sm ${actionResult.success
                ? (currentTheme === 'light' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-emerald-900/30 text-emerald-300 border border-emerald-700/50')
                : (currentTheme === 'light' ? 'bg-red-50 text-red-800 border border-red-200' : 'bg-red-900/30 text-red-300 border border-red-700/50')
              }`}>
                <div className="flex items-center justify-between">
                  <span>
                    {actionResult.type === 'seed' && actionResult.success && (
                      <>App records: {actionResult.data?.records?.app_definitions} / Add-ons: {actionResult.data?.records?.add_ons}</>
                    )}
                    {actionResult.type === 'sync' && actionResult.success && (
                      <>{actionResult.data?.synced} models synced from list "{actionResult.data?.list_slug || 'N/A'}"</>
                    )}
                    {!actionResult.success && (actionResult.data?.detail || actionResult.data?.error || 'Action failed')}
                  </span>
                  <button onClick={() => setActionResult(null)} className="ml-2 opacity-60 hover:opacity-100">✕</button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={seedAppRecords}
                disabled={adminAction === 'seeding'}
                className={`p-3 rounded-lg border ${tc.border} ${tc.text} hover:opacity-80 transition-all text-sm flex items-center gap-2 disabled:opacity-40`}
              >
                <CurrencyDollarIcon className="w-4 h-4" />
                {adminAction === 'seeding' ? 'Seeding...' : 'Seed App Records'}
              </button>
              <button
                onClick={syncModels}
                disabled={adminAction === 'syncing'}
                className={`p-3 rounded-lg border ${tc.border} ${tc.text} hover:opacity-80 transition-all text-sm flex items-center gap-2 disabled:opacity-40`}
              >
                <ArrowsRightLeftIcon className="w-4 h-4" />
                {adminAction === 'syncing' ? 'Syncing...' : 'Sync Model List'}
              </button>
              <button
                onClick={openExternal}
                className={`p-3 rounded-lg border ${tc.border} ${tc.text} hover:opacity-80 transition-all text-sm flex items-center gap-2`}
              >
                <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                Open WebUI Admin
              </button>
            </div>
            <p className={`text-xs ${tc.muted} mt-3`}>
              Seed registers Open WebUI in the app marketplace. Sync verifies model lists match the curated DB list.
            </p>
          </div>

          {/* Quick Launch */}
          <div className={`rounded-xl border p-6 ${tc.card} text-center`}>
            <ChatBubbleLeftRightIcon className={`w-12 h-12 mx-auto mb-3 ${tc.muted}`} />
            <h2 className={`text-lg font-semibold ${tc.text} mb-2`}>Start Chatting</h2>
            <p className={`text-sm ${tc.subtext} mb-4`}>
              Open the full chat interface to start conversations with any of your {models?.total || ''} available AI models.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setShowIframe(true)}
                className={`px-5 py-2.5 rounded-lg border ${tc.border} ${tc.text} hover:opacity-80 transition-all text-sm font-medium`}
              >
                Embed Here
              </button>
              <button
                onClick={openExternal}
                className={`px-5 py-2.5 rounded-lg ${tc.accent} text-white font-medium transition-all flex items-center gap-2 text-sm`}
              >
                <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                Open Full Window
              </button>
            </div>
          </div>

          {/* Configuration Info */}
          {config && (
            <div className={`rounded-xl border p-6 ${tc.card}`}>
              <h2 className={`text-lg font-semibold ${tc.text} mb-4`}>Configuration</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-1`}>Backend</p>
                  <p className={`text-sm ${tc.text}`}>{config.backend}</p>
                </div>
                <div>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-1`}>SSO Provider</p>
                  <p className={`text-sm ${tc.text}`}>{config.sso_enabled ? config.sso_provider : 'Disabled'}</p>
                </div>
                <div>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-1`}>Chat URL</p>
                  <p className={`text-sm font-mono ${tc.text}`}>{config.chat_url}</p>
                </div>
                <div>
                  <p className={`text-xs font-medium uppercase tracking-wider ${tc.muted} mb-1`}>Container</p>
                  <p className={`text-sm font-mono ${tc.text}`}>{status?.container || 'unicorn-open-webui'}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
