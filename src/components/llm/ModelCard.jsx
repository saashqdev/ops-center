import React from 'react';
import { getGlassmorphismStyles } from '../../styles/glassmorphism';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * ModelCard Component
 *
 * Displays individual model information with status, usage, and actions.
 * Uses Marketplace glassmorphism card styling for consistent look.
 */
export default function ModelCard({ model, onEdit, onDelete, onTest }) {
  const { theme, currentTheme } = useTheme();
  const glassStyles = getGlassmorphismStyles(currentTheme);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return { bg: 'bg-green-500/20', text: 'text-green-400', dot: 'bg-green-400', label: 'Active' };
      case 'inactive':
        return { bg: 'bg-gray-500/20', text: 'text-gray-400', dot: 'bg-gray-400', label: 'Inactive' };
      case 'error':
        return { bg: 'bg-red-500/20', text: 'text-red-400', dot: 'bg-red-400', label: 'Error' };
      case 'testing':
        return { bg: 'bg-yellow-500/20', text: 'text-yellow-400', dot: 'bg-yellow-400', label: 'Testing' };
      default:
        return { bg: 'bg-gray-500/20', text: 'text-gray-400', dot: 'bg-gray-400', label: status || 'Unknown' };
    }
  };

  const getProviderGradient = (provider) => {
    const p = (provider || '').toLowerCase();
    if (p.includes('openai')) return 'from-green-500 to-emerald-600';
    if (p.includes('anthropic') || p.includes('claude')) return 'from-orange-500 to-amber-600';
    if (p.includes('groq')) return 'from-blue-500 to-cyan-600';
    if (p.includes('openrouter')) return 'from-purple-500 to-indigo-600';
    if (p.includes('local') || p.includes('vllm')) return 'from-pink-500 to-rose-600';
    if (p.includes('together')) return 'from-indigo-500 to-violet-600';
    if (p.includes('hugging')) return 'from-yellow-500 to-orange-500';
    if (p.includes('mistral')) return 'from-sky-500 to-blue-600';
    return 'from-purple-600 to-indigo-600';
  };

  const statusBadge = getStatusBadge(model.status);
  const providerGradient = getProviderGradient(model.provider);
  const contextK = model.context_length ? `${Math.round(model.context_length / 1024)}K` : '—';
  const inputCost = (model.cost_per_input_token || 0);
  const outputCost = (model.cost_per_output_token || 0);
  const isFree = inputCost === 0 && outputCost === 0;

  return (
    <div
      className={`relative h-full flex flex-col ${glassStyles.card} rounded-2xl p-6 shadow-xl transition-all duration-300 hover:shadow-2xl hover:-translate-y-1`}
    >
      {/* Provider gradient accent bar */}
      <div className={`absolute top-0 left-6 right-6 h-1 rounded-b-full bg-gradient-to-r ${providerGradient}`} />

      {/* Header: Icon + Status */}
      <div className="flex items-start justify-between mb-4 pt-1">
        <div className={`w-12 h-12 bg-gradient-to-br ${providerGradient} rounded-xl flex items-center justify-center shadow-lg flex-shrink-0`}>
          <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611l-.772.13A18.053 18.053 0 0 1 12 21.06c-2.646 0-5.2-.404-7.6-1.157" />
          </svg>
        </div>
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusBadge.bg} ${statusBadge.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
          {statusBadge.label}
        </span>
      </div>

      {/* Model Name & Provider */}
      <div className="mb-4 min-h-[3.5rem]">
        <h3 className={`text-base font-bold ${theme.text.primary} mb-1 line-clamp-2 leading-tight`}>
          {model.name}
        </h3>
        <p className={`text-xs ${theme.text.secondary}`}>
          {model.provider}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className={`${glassStyles.card} rounded-lg px-3 py-2`}>
          <p className={`text-[10px] uppercase tracking-wider ${theme.text.secondary} mb-0.5`}>Context</p>
          <p className={`text-sm font-semibold ${theme.text.primary}`}>{contextK}</p>
        </div>
        <div className={`${glassStyles.card} rounded-lg px-3 py-2`}>
          <p className={`text-[10px] uppercase tracking-wider ${theme.text.secondary} mb-0.5`}>Latency</p>
          <p className={`text-sm font-semibold ${theme.text.primary}`}>
            {model.latency_avg_ms ? `${Math.round(model.latency_avg_ms)}ms` : '—'}
          </p>
        </div>
      </div>

      {/* Pricing */}
      <div className="mb-4">
        {isFree ? (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-green-500/20 text-green-400">
            Free
          </span>
        ) : (
          <div className={`text-xs ${theme.text.secondary} space-y-0.5`}>
            <p>Input: <span className={`font-medium ${theme.text.primary}`}>${inputCost.toFixed(6)}</span>/tok</p>
            <p>Output: <span className={`font-medium ${theme.text.primary}`}>${outputCost.toFixed(6)}</span>/tok</p>
          </div>
        )}
      </div>

      {/* Usage bar */}
      <div className="mb-4 mt-auto">
        <div className="flex justify-between items-center mb-1">
          <p className={`text-[10px] uppercase tracking-wider ${theme.text.secondary}`}>Usage</p>
          <p className={`text-xs ${theme.text.secondary}`}>{(model.usage_count || 0).toLocaleString()} reqs</p>
        </div>
        <div className="w-full bg-gray-700/30 rounded-full h-2">
          <div
            className={`h-2 rounded-full bg-gradient-to-r ${providerGradient} transition-all duration-500`}
            style={{ width: `${Math.min(((model.usage_count || 0) / 1000) * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-white/10">
        <button
          onClick={() => onTest(model)}
          className="flex-1 py-2 px-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white rounded-lg text-xs font-semibold transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-1.5"
        >
          <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M6.3 2.841A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
          </svg>
          Test
        </button>
        <button
          onClick={() => onEdit(model)}
          className={`p-2 ${glassStyles.card} rounded-lg hover:bg-white/20 transition-colors`}
          title="Edit"
        >
          <svg className={`h-4 w-4 ${theme.text.secondary}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z" />
          </svg>
        </button>
        <button
          onClick={() => onDelete(model)}
          className={`p-2 ${glassStyles.card} rounded-lg hover:bg-red-500/20 transition-colors`}
          title="Delete"
        >
          <svg className="h-4 w-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
          </svg>
        </button>
      </div>
    </div>
  );
}
