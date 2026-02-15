/**
 * CenterDeepSearch - Privacy-focused AI Metasearch Engine
 * 
 * In-app search interface powered by SearXNG with 70+ search engines.
 * Features: category tabs, autocomplete, search history, engine stats.
 * 
 * Backend: /api/v1/search (proxies to SearXNG)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../contexts/ThemeContext';
import {
  MagnifyingGlassIcon,
  GlobeAltIcon,
  PhotoIcon,
  VideoCameraIcon,
  NewspaperIcon,
  AcademicCapIcon,
  CommandLineIcon,
  ClockIcon,
  XMarkIcon,
  ArrowTopRightOnSquareIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FunnelIcon,
  ShieldCheckIcon,
  BoltIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const CATEGORIES = [
  { id: 'general', name: 'Web', icon: GlobeAltIcon },
  { id: 'images', name: 'Images', icon: PhotoIcon },
  { id: 'videos', name: 'Videos', icon: VideoCameraIcon },
  { id: 'news', name: 'News', icon: NewspaperIcon },
  { id: 'science', name: 'Science', icon: AcademicCapIcon },
  { id: 'it', name: 'Dev', icon: CommandLineIcon },
];

const TIME_RANGES = [
  { id: '', name: 'Any time' },
  { id: 'day', name: 'Past 24h' },
  { id: 'week', name: 'Past week' },
  { id: 'month', name: 'Past month' },
  { id: 'year', name: 'Past year' },
];

export default function CenterDeepSearch() {
  const { currentTheme } = useTheme();
  
  // Search state
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [infoboxes, setInfoboxes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  
  // Filters
  const [activeCategory, setActiveCategory] = useState('general');
  const [timeRange, setTimeRange] = useState('');
  const [safesearch, setSafesearch] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  
  // Pagination
  const [page, setPage] = useState(1);
  
  // Stats
  const [searchMeta, setSearchMeta] = useState(null);
  const [recentSearches, setRecentSearches] = useState([]);
  const [showRecent, setShowRecent] = useState(false);
  
  // Autocomplete
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const suggestTimeout = useRef(null);
  const searchInputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Theme
  const tc = {
    bg: currentTheme === 'unicorn' ? 'bg-purple-950/50' : currentTheme === 'light' ? 'bg-gray-50' : 'bg-slate-900',
    card: currentTheme === 'unicorn' ? 'bg-purple-900/50 backdrop-blur-xl border-white/20' : currentTheme === 'light' ? 'bg-white border-gray-200' : 'bg-slate-800 border-slate-700',
    text: currentTheme === 'unicorn' ? 'text-purple-100' : currentTheme === 'light' ? 'text-gray-900' : 'text-slate-100',
    subtext: currentTheme === 'unicorn' ? 'text-purple-300' : currentTheme === 'light' ? 'text-gray-600' : 'text-slate-400',
    muted: currentTheme === 'unicorn' ? 'text-purple-400' : currentTheme === 'light' ? 'text-gray-500' : 'text-slate-500',
    input: currentTheme === 'unicorn' ? 'bg-purple-900/60 border-white/20 text-purple-100 placeholder-purple-400' : currentTheme === 'light' ? 'bg-white border-gray-300 text-gray-900 placeholder-gray-400' : 'bg-slate-800 border-slate-600 text-slate-100 placeholder-slate-500',
    hover: currentTheme === 'unicorn' ? 'hover:bg-purple-800/50' : currentTheme === 'light' ? 'hover:bg-gray-100' : 'hover:bg-slate-700/50',
    link: currentTheme === 'unicorn' ? 'text-purple-300 hover:text-purple-100' : currentTheme === 'light' ? 'text-blue-600 hover:text-blue-800' : 'text-blue-400 hover:text-blue-300',
    urlColor: currentTheme === 'unicorn' ? 'text-green-400' : currentTheme === 'light' ? 'text-green-700' : 'text-green-400',
    accent: currentTheme === 'unicorn' ? 'bg-purple-600 hover:bg-purple-700' : currentTheme === 'light' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-emerald-600 hover:bg-emerald-700',
    badge: currentTheme === 'unicorn' ? 'bg-purple-700/50 text-purple-200' : currentTheme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-slate-700 text-slate-300',
  };

  const [searchParams] = useSearchParams();

  // Load recent searches on mount + auto-search from ?q= param
  useEffect(() => {
    loadRecentSearches();
    const initialQuery = searchParams.get('q');
    if (initialQuery) {
      setQuery(initialQuery);
      performSearch(initialQuery);
    }
  }, []);

  // Close suggestions on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target) &&
          searchInputRef.current && !searchInputRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadRecentSearches = async () => {
    try {
      const res = await fetch('/api/v1/search/stats', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setRecentSearches(data.recent_searches || []);
      }
    } catch (e) {
      // Stats not critical
    }
  };

  const fetchSuggestions = useCallback(async (q) => {
    if (q.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    try {
      const res = await fetch(`/api/v1/search/suggestions?q=${encodeURIComponent(q)}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setSuggestions(Array.isArray(data) ? data.slice(0, 8) : []);
        setShowSuggestions(true);
      }
    } catch (e) {
      // Suggestions not critical
    }
  }, []);

  const handleQueryChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    setActiveSuggestion(-1);

    if (suggestTimeout.current) clearTimeout(suggestTimeout.current);
    suggestTimeout.current = setTimeout(() => fetchSuggestions(val), 300);
  };

  const performSearch = async (searchQuery = query, searchPage = 1, category = activeCategory) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);
    setShowSuggestions(false);
    setPage(searchPage);

    try {
      const params = new URLSearchParams({
        q: searchQuery.trim(),
        categories: category,
        page: searchPage.toString(),
        safesearch: safesearch.toString(),
      });
      if (timeRange) params.set('time_range', timeRange);

      const res = await fetch(`/api/v1/search?${params}`, { credentials: 'include' });
      
      if (!res.ok) {
        if (res.status === 401) {
          setError('Please log in to use Center-Deep Search.');
        } else {
          const err = await res.json().catch(() => ({}));
          setError(err.detail || 'Search failed. Please try again.');
        }
        setResults([]);
        return;
      }

      const data = await res.json();
      setResults(data.results || []);
      setAnswers(data.answers || []);
      setInfoboxes(data.infoboxes || []);
      setSearchMeta({
        total: data.total_results,
        engines: data.engines_used || [],
        time: data.response_time_ms,
        querySuggestions: data.suggestions || [],
      });

      // Refresh recent searches
      loadRecentSearches();
    } catch (e) {
      setError('Network error. Please check your connection.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    performSearch(query, 1, activeCategory);
  };

  const handleCategoryChange = (catId) => {
    setActiveCategory(catId);
    if (hasSearched && query.trim()) {
      performSearch(query, 1, catId);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    performSearch(suggestion, 1, activeCategory);
  };

  const handleRecentClick = (q) => {
    setQuery(q);
    setShowRecent(false);
    performSearch(q, 1, activeCategory);
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSuggestion(prev => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSuggestion(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && activeSuggestion >= 0) {
      e.preventDefault();
      handleSuggestionClick(suggestions[activeSuggestion]);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const formatUrl = (url) => {
    try {
      const u = new URL(url);
      return u.hostname + (u.pathname !== '/' ? u.pathname : '');
    } catch {
      return url;
    }
  };

  const getDomain = (url) => {
    try {
      return new URL(url).hostname;
    } catch {
      return '';
    }
  };

  const getFaviconUrl = (url) => {
    const domain = getDomain(url);
    return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=32` : null;
  };

  // ===== RENDER: Landing (no search yet) =====
  if (!hasSearched && !loading) {
    return (
      <div className={`min-h-[80vh] flex flex-col items-center justify-center px-4 ${tc.bg}`}>
        {/* Logo & Title */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className={`w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shadow-xl`}>
            <MagnifyingGlassIcon className="h-10 w-10 text-white" />
          </div>
          <h1 className={`text-4xl font-bold ${tc.text} mb-2`}>Center-Deep Search</h1>
          <p className={`text-lg ${tc.subtext}`}>Privacy-focused AI search across 70+ engines</p>
        </motion.div>

        {/* Search Bar */}
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          onSubmit={handleSubmit}
          className="w-full max-w-2xl relative"
        >
          <div className="relative">
            <MagnifyingGlassIcon className={`absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 ${tc.muted}`} />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={handleQueryChange}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                if (query.length >= 2 && suggestions.length > 0) setShowSuggestions(true);
                if (!query && recentSearches.length > 0) setShowRecent(true);
              }}
              placeholder="Search the web privately..."
              style={{ paddingLeft: '3rem', textIndent: '16px' }}
              className={`w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 ${tc.input} focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all shadow-lg`}
              autoFocus
            />
            {query && (
              <button type="button" onClick={() => { setQuery(''); setSuggestions([]); }}
                className={`absolute right-14 top-1/2 -translate-y-1/2 p-1 rounded-full ${tc.hover}`}>
                <XMarkIcon className={`h-5 w-5 ${tc.muted}`} />
              </button>
            )}
            <button type="submit"
              className={`absolute right-2 top-1/2 -translate-y-1/2 p-2.5 rounded-xl ${tc.accent} text-white transition-colors`}>
              <MagnifyingGlassIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Autocomplete Suggestions */}
          <AnimatePresence>
            {showSuggestions && suggestions.length > 0 && (
              <motion.div
                ref={suggestionsRef}
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                className={`absolute w-full mt-1 rounded-xl border shadow-xl overflow-hidden z-50 ${tc.card}`}
              >
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => handleSuggestionClick(s)}
                    className={`w-full text-left px-4 py-2.5 flex items-center gap-3 ${tc.text} ${tc.hover} ${i === activeSuggestion ? (currentTheme === 'light' ? 'bg-gray-100' : 'bg-slate-700/70') : ''}`}>
                    <MagnifyingGlassIcon className={`h-4 w-4 ${tc.muted} flex-shrink-0`} />
                    <span className="truncate">{s}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Recent Searches */}
          <AnimatePresence>
            {showRecent && !query && recentSearches.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                className={`absolute w-full mt-1 rounded-xl border shadow-xl overflow-hidden z-50 ${tc.card}`}
              >
                <div className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider ${tc.muted} border-b ${currentTheme === 'light' ? 'border-gray-200' : 'border-slate-700'}`}>
                  Recent Searches
                </div>
                {recentSearches.slice(0, 6).map((r, i) => (
                  <button key={i} onClick={() => handleRecentClick(r.query)}
                    className={`w-full text-left px-4 py-2.5 flex items-center gap-3 ${tc.text} ${tc.hover}`}>
                    <ClockIcon className={`h-4 w-4 ${tc.muted} flex-shrink-0`} />
                    <span className="truncate">{r.query}</span>
                    <span className={`ml-auto text-xs ${tc.muted}`}>{r.result_count} results</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.form>

        {/* Category Pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex gap-2 mt-6 flex-wrap justify-center"
        >
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                activeCategory === cat.id
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                  : `${tc.badge} ${tc.hover}`
              }`}
            >
              <cat.icon className="h-4 w-4" />
              {cat.name}
            </button>
          ))}
        </motion.div>

        {/* Privacy Badge */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className={`mt-8 flex items-center gap-6 ${tc.muted} text-sm`}
        >
          <span className="flex items-center gap-1.5">
            <ShieldCheckIcon className="h-4 w-4 text-emerald-500" />
            No tracking
          </span>
          <span className="flex items-center gap-1.5">
            <BoltIcon className="h-4 w-4 text-emerald-500" />
            70+ engines
          </span>
          <span className="flex items-center gap-1.5">
            <SparklesIcon className="h-4 w-4 text-emerald-500" />
            AI-powered
          </span>
        </motion.div>
      </div>
    );
  }

  // ===== RENDER: Search Results =====
  return (
    <div className={`min-h-screen ${tc.bg}`}>
      {/* Search Header */}
      <div className={`sticky top-0 z-40 border-b shadow-sm ${tc.card}`}>
        <div className="max-w-5xl mx-auto px-4 py-3">
          {/* Search bar row */}
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <div className="flex items-center gap-2 flex-shrink-0 cursor-pointer" onClick={() => { setHasSearched(false); setResults([]); setQuery(''); }}>
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center">
                <MagnifyingGlassIcon className="h-4 w-4 text-white" />
              </div>
            </div>
            <div className="relative flex-1">
              <input
                ref={searchInputRef}
                type="text"
                value={query}
                onChange={handleQueryChange}
                onKeyDown={handleKeyDown}
                onFocus={() => query.length >= 2 && suggestions.length > 0 && setShowSuggestions(true)}
                placeholder="Search..."
                style={{ marginLeft: '16px' }}
                className={`w-full px-4 py-2 rounded-xl border ${tc.input} focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-sm`}
              />
              {query && (
                <button type="button" onClick={() => setQuery('')}
                  className={`absolute right-3 top-1/2 -translate-y-1/2 ${tc.muted}`}>
                  <XMarkIcon className="h-4 w-4" />
                </button>
              )}
              {/* Autocomplete in results view */}
              <AnimatePresence>
                {showSuggestions && suggestions.length > 0 && (
                  <motion.div
                    ref={suggestionsRef}
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    className={`absolute w-full mt-1 rounded-xl border shadow-xl overflow-hidden z-50 ${tc.card}`}
                  >
                    {suggestions.map((s, i) => (
                      <button key={i} onClick={() => handleSuggestionClick(s)}
                        className={`w-full text-left px-4 py-2 flex items-center gap-2 text-sm ${tc.text} ${tc.hover} ${i === activeSuggestion ? (currentTheme === 'light' ? 'bg-gray-100' : 'bg-slate-700/70') : ''}`}>
                        <MagnifyingGlassIcon className={`h-3.5 w-3.5 ${tc.muted}`} />
                        {s}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <button type="submit"
              className={`ml-2 px-4 py-2 rounded-xl ${tc.accent} text-white text-sm font-medium transition-colors flex-shrink-0`}>
              Search
            </button>
            <button type="button" onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded-lg border ${tc.card} ${tc.hover} transition-colors ${showFilters ? 'ring-2 ring-emerald-500' : ''}`}>
              <FunnelIcon className={`h-4 w-4 ${tc.muted}`} />
            </button>
          </form>

          {/* Category Tabs */}
          <div className="flex gap-1 mt-2 overflow-x-auto no-scrollbar">
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => handleCategoryChange(cat.id)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  activeCategory === cat.id
                    ? 'bg-emerald-600 text-white'
                    : `${tc.muted} ${tc.hover}`
                }`}
              >
                <cat.icon className="h-3.5 w-3.5" />
                {cat.name}
              </button>
            ))}
          </div>

          {/* Filters Panel */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className={`flex items-center gap-4 pt-3 mt-2 border-t ${currentTheme === 'light' ? 'border-gray-200' : 'border-slate-700'}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${tc.muted}`}>Time:</span>
                    <select
                      value={timeRange}
                      onChange={(e) => { setTimeRange(e.target.value); if (hasSearched) performSearch(query, 1, activeCategory); }}
                      className={`text-xs px-2 py-1 rounded-lg border ${tc.input} focus:outline-none`}
                    >
                      {TIME_RANGES.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${tc.muted}`}>SafeSearch:</span>
                    <select
                      value={safesearch}
                      onChange={(e) => { setSafesearch(Number(e.target.value)); if (hasSearched) performSearch(query, 1, activeCategory); }}
                      className={`text-xs px-2 py-1 rounded-lg border ${tc.input} focus:outline-none`}
                    >
                      <option value={0}>Off</option>
                      <option value={1}>Moderate</option>
                      <option value={2}>Strict</option>
                    </select>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Results Area */}
      <div className="max-w-5xl mx-auto px-4 py-4">
        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="relative">
              <div className="w-12 h-12 border-4 border-emerald-500/20 rounded-full animate-spin border-t-emerald-500"></div>
            </div>
            <p className={`mt-4 text-sm ${tc.muted}`}>Searching across {activeCategory === 'general' ? '70+' : '20+'} engines...</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className={`rounded-xl border p-6 text-center ${currentTheme === 'light' ? 'bg-red-50 border-red-200' : 'bg-red-900/20 border-red-500/30'}`}>
            <ExclamationTriangleIcon className="h-8 w-8 text-red-400 mx-auto mb-2" />
            <p className="text-red-400 font-medium">{error}</p>
          </div>
        )}

        {/* Results */}
        {!loading && !error && results.length > 0 && (
          <>
            {/* Meta info */}
            {searchMeta && (
              <div className={`mb-4 text-xs ${tc.muted} flex items-center gap-3 flex-wrap`}>
                <span>{searchMeta.total} results</span>
                <span>·</span>
                <span>{searchMeta.engines.length} engines</span>
                <span>·</span>
                <span>{searchMeta.time}ms</span>
                {searchMeta.engines.length > 0 && (
                  <>
                    <span>·</span>
                    <span className="truncate max-w-xs" title={searchMeta.engines.join(', ')}>
                      via {searchMeta.engines.slice(0, 4).join(', ')}{searchMeta.engines.length > 4 ? ` +${searchMeta.engines.length - 4}` : ''}
                    </span>
                  </>
                )}
              </div>
            )}

            {/* Answers */}
            {answers.length > 0 && (
              <div className={`rounded-xl border p-4 mb-4 ${currentTheme === 'light' ? 'bg-emerald-50 border-emerald-200' : 'bg-emerald-900/20 border-emerald-500/30'}`}>
                <p className={`text-sm font-medium ${tc.text}`}>{answers[0]}</p>
              </div>
            )}

            {/* Search Suggestions */}
            {searchMeta?.querySuggestions?.length > 0 && (
              <div className={`flex items-center gap-2 mb-4 flex-wrap`}>
                <span className={`text-xs ${tc.muted}`}>Related:</span>
                {searchMeta.querySuggestions.slice(0, 5).map((s, i) => (
                  <button key={i} onClick={() => { setQuery(s); performSearch(s, 1, activeCategory); }}
                    className={`text-xs px-2.5 py-1 rounded-full ${tc.badge} ${tc.hover} transition-colors`}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* Infoboxes */}
            {infoboxes.length > 0 && (
              <div className={`rounded-xl border p-4 mb-4 ${tc.card}`}>
                <h3 className={`font-semibold ${tc.text} mb-2`}>{infoboxes[0].infobox}</h3>
                <p className={`text-sm ${tc.subtext}`}>{infoboxes[0].content}</p>
                {infoboxes[0].urls && infoboxes[0].urls.length > 0 && (
                  <div className="mt-2 flex gap-2">
                    {infoboxes[0].urls.slice(0, 3).map((u, i) => (
                      <a key={i} href={u.url} target="_blank" rel="noopener noreferrer"
                        className={`text-xs ${tc.link}`}>
                        {u.title}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Results List */}
            {activeCategory === 'images' ? (
              /* Image Grid */
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {results.map((r) => (
                  <a key={r.id} href={r.url} target="_blank" rel="noopener noreferrer"
                    className={`group rounded-xl border overflow-hidden ${tc.card} ${tc.hover} transition-all`}>
                    <div className="aspect-square bg-slate-800 overflow-hidden">
                      <img src={r.img_src || r.thumbnail || ''} alt={r.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        loading="lazy"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    </div>
                    <div className="p-2">
                      <p className={`text-xs ${tc.text} truncate`}>{r.title}</p>
                      <p className={`text-xs ${tc.muted} truncate`}>{getDomain(r.url)}</p>
                    </div>
                  </a>
                ))}
              </div>
            ) : (
              /* Standard Results */
              <div className="space-y-5">
                {results.map((r) => (
                  <motion.div
                    key={r.id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: r.id * 0.02 }}
                    className="group"
                  >
                    {/* URL line */}
                    <div className="flex items-center gap-2 mb-0.5">
                      {getFaviconUrl(r.url) && (
                        <img src={getFaviconUrl(r.url)} alt="" className="w-4 h-4 rounded-sm"
                          onError={(e) => { e.target.style.display = 'none'; }} />
                      )}
                      <span className={`text-xs ${tc.urlColor} truncate`}>
                        {formatUrl(r.url)}
                      </span>
                      {r.engines && r.engines.length > 1 && (
                        <span className={`text-xs px-1.5 py-0.5 rounded ${tc.badge}`}>
                          {r.engines.length} sources
                        </span>
                      )}
                    </div>
                    {/* Title */}
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                      className={`text-lg font-medium ${tc.link} leading-snug block`}>
                      {r.title}
                      <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5 inline ml-1 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                    {/* Snippet */}
                    {r.content && (
                      <p className={`text-sm ${tc.subtext} mt-0.5 leading-relaxed line-clamp-2`}
                        dangerouslySetInnerHTML={{ __html: r.content }}>
                      </p>
                    )}
                    {/* Date */}
                    {r.publishedDate && (
                      <span className={`text-xs ${tc.muted} mt-1 inline-block`}>
                        {new Date(r.publishedDate).toLocaleDateString()}
                      </span>
                    )}
                  </motion.div>
                ))}
              </div>
            )}

            {/* Pagination */}
            <div className="flex items-center justify-center gap-3 mt-8 mb-4">
              <button
                onClick={() => performSearch(query, page - 1, activeCategory)}
                disabled={page <= 1}
                className={`flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  page <= 1 ? `${tc.muted} cursor-not-allowed opacity-50` : `${tc.badge} ${tc.hover}`
                }`}
              >
                <ChevronLeftIcon className="h-4 w-4" />
                Previous
              </button>
              <span className={`text-sm ${tc.text} font-medium`}>Page {page}</span>
              <button
                onClick={() => performSearch(query, page + 1, activeCategory)}
                disabled={results.length < 10}
                className={`flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  results.length < 10 ? `${tc.muted} cursor-not-allowed opacity-50` : `${tc.badge} ${tc.hover}`
                }`}
              >
                Next
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </>
        )}

        {/* No Results */}
        {!loading && !error && hasSearched && results.length === 0 && (
          <div className="text-center py-20">
            <MagnifyingGlassIcon className={`h-12 w-12 mx-auto mb-3 ${tc.muted}`} />
            <p className={`text-lg font-medium ${tc.text}`}>No results found</p>
            <p className={`text-sm ${tc.subtext} mt-1`}>Try different keywords or another category</p>
          </div>
        )}
      </div>
    </div>
  );
}
