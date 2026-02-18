import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowTopRightOnSquareIcon,
  GlobeAltIcon,
  BuildingOfficeIcon,
  ServerIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { getGlassmorphismStyles } from '../styles/glassmorphism';
import { useTheme } from '../contexts/ThemeContext';

/**
 * AppsLauncher - Tier-Filtered Apps Dashboard
 *
 * Shows ONLY apps the user's subscription tier includes.
 * Fetches from /api/v1/my-apps/authorized (tier-filtered backend endpoint)
 *
 * Apps can be hosted ANYWHERE:
 * - Same domain (your-domain.com/admin)
 * - Different subdomain (chat.your-domain.com)
 * - Completely different domain (search.centerdeep.online)
 *
 * launch_url is the source of truth for where the app lives.
 */
const getCategoryGradient = (category) => {
  const gradients = {
    'AI & Chat': 'from-blue-500 to-cyan-500',
    'Search & Research': 'from-green-500 to-emerald-600',
    'Development': 'from-purple-500 to-indigo-600',
    'AI Agents': 'from-purple-600 to-pink-600',
    'Productivity': 'from-orange-500 to-amber-600',
    'Voice Services': 'from-pink-500 to-rose-600'
  };
  return gradients[category] || 'from-gray-500 to-slate-600';
};

const getHostBadge = (launch_url) => {
  try {
    const url = new URL(launch_url);
    const host = url.hostname;
    if (host.includes('kubeworkz.io') || host.includes('gridworkz.com')) {
      return { label: 'Federated', icon: GlobeAltIcon, color: 'bg-cyan-500/20 text-cyan-300 border-cyan-400/30' };
    }
    return { label: 'External', icon: GlobeAltIcon, color: 'bg-purple-500/20 text-purple-300 border-purple-400/30' };
  } catch (e) {
    return { label: 'External', icon: GlobeAltIcon, color: 'bg-gray-500/20 text-gray-300 border-gray-400/30' };
  }
};

const AppsLauncher = () => {
  const { theme, currentTheme } = useTheme();
  const glassStyles = getGlassmorphismStyles(currentTheme);
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchApps();
  }, []);

  const fetchApps = async () => {
    try {
      const response = await fetch('/api/v1/my-apps/authorized', { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to fetch apps');
      const data = await response.json();
      setApps(data);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching apps:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const handleLaunch = (app) => {
    window.open(app.launch_url, '_blank', 'noopener,noreferrer');
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-200">
          Error loading apps: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className={`text-3xl font-bold ${theme.text.primary} mb-2`}>
          My Apps
        </h1>
        <p className="text-purple-400">
          Apps included in your subscription tier
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {apps.map((app, index) => {
          const gradient = getCategoryGradient(app.category);
          const hostBadge = getHostBadge(app.launch_url);
          const BadgeIcon = hostBadge.icon;

          return (
            <motion.div
              key={app.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.05 * index }}
              whileHover={{ scale: 1.02, y: -4 }}
              className={`${glassStyles.card} rounded-2xl overflow-hidden shadow-xl h-full flex flex-col cursor-pointer`}
              onClick={() => handleLaunch(app)}
            >
              {/* App Icon/Image Header - fixed height like marketplace */}
              <div className={`h-40 bg-gradient-to-br ${gradient} flex items-center justify-center relative`}>
                {/* Host Badge */}
                <div className="absolute top-3 right-3 z-10">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${hostBadge.color}`}>
                    <BadgeIcon className="h-3.5 w-3.5" />
                    {hostBadge.label}
                  </span>
                </div>

                {app.icon_url ? (
                  <img
                    src={app.icon_url}
                    alt={app.name}
                    className="h-24 w-24 object-contain"
                  />
                ) : (
                  <ServerIcon className="h-24 w-24 text-white opacity-90" />
                )}
              </div>

              {/* App Content */}
              <div className="p-6 flex-1 flex flex-col">
                <h3 className={`text-xl font-bold ${theme.text.primary} mb-2 text-center`}>
                  {app.name}
                </h3>

                <p className={`text-sm ${theme.text.secondary} line-clamp-2 mb-4 text-center flex-1`}>
                  {app.description || '\u00A0'}
                </p>

                {/* Launch Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleLaunch(app);
                  }}
                  className="w-full py-3 px-4 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white rounded-lg font-semibold transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2 mt-auto"
                >
                  <ArrowTopRightOnSquareIcon className="h-5 w-5" />
                  Launch App
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>

      {apps.length === 0 && (
        <div className="text-center py-16">
          <SparklesIcon className="h-16 w-16 text-purple-400 mx-auto mb-4 opacity-50" />
          <h3 className={`text-xl font-semibold ${theme.text.primary} mb-2`}>
            No apps in your tier
          </h3>
          <p className={`${theme.text.secondary} mb-6`}>
            Upgrade your subscription to access more apps
          </p>
          <a
            href="/admin/apps/marketplace"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-semibold hover:from-purple-600 hover:to-pink-600 transition-all"
          >
            Browse Marketplace
          </a>
        </div>
      )}
    </div>
  );
};

export default AppsLauncher;
