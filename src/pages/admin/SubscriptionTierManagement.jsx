import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  CheckIcon,
  CurrencyDollarIcon,
  SparklesIcon,
  UserGroupIcon,
  KeyIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  DocumentDuplicateIcon,
  ArrowsRightLeftIcon,
  EyeIcon,
  EyeSlashIcon,
  AdjustmentsHorizontalIcon,
  UsersIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';

export default function SubscriptionTierManagement() {
  const { theme, currentTheme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [tiers, setTiers] = useState([]);
  const [filteredTiers, setFilteredTiers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('tiers'); // 'tiers', 'features', 'migrations', 'analytics'
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create', 'edit', 'clone'
  const [selectedTier, setSelectedTier] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [tierToDelete, setTierToDelete] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showActiveOnly, setShowActiveOnly] = useState(false);

  // Analytics state
  const [analytics, setAnalytics] = useState({
    total_tiers: 0,
    active_tiers: 0,
    total_users: 0,
    tier_distribution: {},
    revenue_by_tier: {}
  });

  // Migration state
  const [migrations, setMigrations] = useState([]);
  const [showMigrationModal, setShowMigrationModal] = useState(false);
  const [migrationData, setMigrationData] = useState({
    user_id: '',
    new_tier_code: '',
    reason: '',
    send_notification: true
  });

  // Form state for tier creation/editing
  const [formData, setFormData] = useState({
    tier_code: '',
    tier_name: '',
    description: '',
    price_monthly: 0.00,
    price_yearly: null,
    is_active: true,
    is_invite_only: false,
    sort_order: 0,
    api_calls_limit: 1000,
    team_seats: 1,
    byok_enabled: false,
    priority_support: false,
    lago_plan_code: '',
    stripe_price_monthly: '',
    stripe_price_yearly: ''
  });

  useEffect(() => {
    loadTiers();
    loadAnalytics();
    loadMigrations();
  }, []);

  useEffect(() => {
    filterTiers();
  }, [searchQuery, tiers, showActiveOnly]);

  const loadTiers = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (showActiveOnly) params.append('active_only', 'true');

      const response = await fetch(`/api/v1/admin/tiers?${params}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setTiers(data);
      } else {
        console.error('Failed to load tiers');
      }
    } catch (error) {
      console.error('Error loading tiers:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async () => {
    try {
      const response = await fetch('/api/v1/admin/tiers/analytics/summary', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Error loading analytics:', error);
    }
  };

  const loadMigrations = async (limit = 50) => {
    try {
      const response = await fetch(`/api/v1/admin/tiers/migrations?limit=${limit}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setMigrations(data);
      }
    } catch (error) {
      console.error('Error loading migrations:', error);
    }
  };

  const filterTiers = () => {
    let filtered = tiers;

    if (showActiveOnly) {
      filtered = filtered.filter(tier => tier.is_active);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(tier =>
        tier.tier_code?.toLowerCase().includes(query) ||
        tier.tier_name?.toLowerCase().includes(query) ||
        tier.description?.toLowerCase().includes(query)
      );
    }

    setFilteredTiers(filtered);
  };

  const getTierBadgeColor = (tierCode) => {
    const code = tierCode?.toLowerCase() || '';
    if (code.includes('trial')) return 'bg-blue-500';
    if (code.includes('starter')) return 'bg-green-500';
    if (code.includes('professional') || code.includes('pro')) return 'bg-purple-500';
    if (code.includes('enterprise')) return 'bg-gradient-to-r from-yellow-500 to-orange-500';
    if (code.includes('vip') || code.includes('founder')) return 'bg-pink-500';
    return 'bg-gray-500';
  };

  const openCreateModal = () => {
    setFormData({
      tier_code: '',
      tier_name: '',
      description: '',
      price_monthly: 0.00,
      price_yearly: null,
      is_active: true,
      is_invite_only: false,
      sort_order: tiers.length,
      api_calls_limit: 1000,
      team_seats: 1,
      byok_enabled: false,
      priority_support: false,
      lago_plan_code: '',
      stripe_price_monthly: '',
      stripe_price_yearly: ''
    });
    setModalMode('create');
    setSelectedTier(null);
    setShowModal(true);
  };

  const openEditModal = (tier) => {
    setFormData({
      tier_code: tier.tier_code,
      tier_name: tier.tier_name,
      description: tier.description || '',
      price_monthly: tier.price_monthly,
      price_yearly: tier.price_yearly,
      is_active: tier.is_active,
      is_invite_only: tier.is_invite_only,
      sort_order: tier.sort_order,
      api_calls_limit: tier.api_calls_limit,
      team_seats: tier.team_seats,
      byok_enabled: tier.byok_enabled,
      priority_support: tier.priority_support,
      lago_plan_code: tier.lago_plan_code || '',
      stripe_price_monthly: tier.stripe_price_monthly || '',
      stripe_price_yearly: tier.stripe_price_yearly || ''
    });
    setModalMode('edit');
    setSelectedTier(tier);
    setShowModal(true);
  };

  const openCloneModal = (tier) => {
    setFormData({
      ...tier,
      tier_code: `${tier.tier_code}_copy`,
      tier_name: `${tier.tier_name} (Copy)`,
      lago_plan_code: '',
      stripe_price_monthly: '',
      stripe_price_yearly: ''
    });
    setModalMode('clone');
    setSelectedTier(tier);
    setShowModal(true);
  };

  const handleSaveTier = async () => {
    setSaving(true);
    try {
      let url, method;

      if (modalMode === 'create' || modalMode === 'clone') {
        url = '/api/v1/admin/tiers';
        method = 'POST';
      } else {
        url = `/api/v1/admin/tiers/${selectedTier.id}`;
        method = 'PUT';
      }

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        await loadTiers();
        await loadAnalytics();
        setShowModal(false);
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to save tier'}`);
      }
    } catch (error) {
      console.error('Error saving tier:', error);
      alert('Failed to save tier');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTier = async (tierId) => {
    try {
      const response = await fetch(`/api/v1/admin/tiers/${tierId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        await loadTiers();
        await loadAnalytics();
        setShowDeleteConfirm(false);
        setTierToDelete(null);
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to delete tier'}`);
      }
    } catch (error) {
      console.error('Error deleting tier:', error);
      alert('Failed to delete tier');
    }
  };

  const handleMigrateUser = async () => {
    setSaving(true);
    try {
      const response = await fetch(`/api/v1/admin/tiers/users/${migrationData.user_id}/migrate-tier`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: migrationData.user_id,
          new_tier_code: migrationData.new_tier_code,
          reason: migrationData.reason,
          send_notification: migrationData.send_notification
        })
      });

      if (response.ok) {
        await loadMigrations();
        setShowMigrationModal(false);
        setMigrationData({
          user_id: '',
          new_tier_code: '',
          reason: '',
          send_notification: true
        });
        alert('User migrated successfully!');
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to migrate user'}`);
      }
    } catch (error) {
      console.error('Error migrating user:', error);
      alert('Failed to migrate user');
    } finally {
      setSaving(false);
    }
  };

  // Tab Navigation Component
  const TabNavigation = () => (
    <div className="flex space-x-2 mb-6 border-b" style={{ borderColor: currentTheme.border }}>
      {[
        { id: 'tiers', label: 'Subscription Tiers', icon: CurrencyDollarIcon },
        { id: 'migrations', label: 'User Migrations', icon: ArrowsRightLeftIcon },
        { id: 'analytics', label: 'Analytics', icon: ChartBarIcon }
      ].map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={`flex items-center space-x-2 px-4 py-2 border-b-2 transition-colors ${
            activeTab === tab.id
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent hover:border-gray-300'
          }`}
          style={activeTab !== tab.id ? { color: currentTheme.textSecondary } : {}}
        >
          <tab.icon className="w-5 h-5" />
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );

  // Tier Card Component
  const TierCard = ({ tier }) => (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow"
      style={{ 
        backgroundColor: currentTheme.cardBackground,
        borderColor: currentTheme.border,
        borderWidth: '1px'
      }}
    >
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getTierBadgeColor(tier.tier_code)} text-white`}>
              {tier.tier_code}
            </span>
            {!tier.is_active && (
              <span className="px-2 py-1 bg-red-500 text-white text-xs rounded">Inactive</span>
            )}
            {tier.is_invite_only && (
              <span className="px-2 py-1 bg-yellow-500 text-white text-xs rounded">Invite Only</span>
            )}
          </div>
          <h3 className="text-xl font-bold mb-1" style={{ color: currentTheme.text }}>
            {tier.tier_name}
          </h3>
          <p className="text-sm mb-3" style={{ color: currentTheme.textSecondary }}>
            {tier.description || 'No description'}
          </p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => openEditModal(tier)}
            className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title="Edit"
          >
            <PencilIcon className="w-5 h-5" style={{ color: currentTheme.textSecondary }} />
          </button>
          <button
            onClick={() => openCloneModal(tier)}
            className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title="Clone"
          >
            <DocumentDuplicateIcon className="w-5 h-5" style={{ color: currentTheme.textSecondary }} />
          </button>
          <button
            onClick={() => {
              setTierToDelete(tier);
              setShowDeleteConfirm(true);
            }}
            className="p-2 rounded hover:bg-red-100 dark:hover:bg-red-900 transition-colors"
            title="Delete"
          >
            <TrashIcon className="w-5 h-5 text-red-500" />
          </button>
        </div>
      </div>

      {/* Pricing */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="flex items-center space-x-2">
          <CurrencyDollarIcon className="w-5 h-5 text-green-500" />
          <div>
            <p className="text-xs" style={{ color: currentTheme.textSecondary }}>Monthly</p>
            <p className="font-bold" style={{ color: currentTheme.text }}>
              ${tier.price_monthly.toFixed(2)}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <CurrencyDollarIcon className="w-5 h-5 text-blue-500" />
          <div>
            <p className="text-xs" style={{ color: currentTheme.textSecondary }}>Yearly</p>
            <p className="font-bold" style={{ color: currentTheme.text }}>
              {tier.price_yearly ? `$${tier.price_yearly.toFixed(2)}` : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="flex items-center space-x-2 text-sm">
          <SparklesIcon className="w-4 h-4 text-purple-500" />
          <span style={{ color: currentTheme.textSecondary }}>
            {tier.api_calls_limit === -1 ? '∞' : tier.api_calls_limit.toLocaleString()} API calls
          </span>
        </div>
        <div className="flex items-center space-x-2 text-sm">
          <UserGroupIcon className="w-4 h-4 text-blue-500" />
          <span style={{ color: currentTheme.textSecondary }}>
            {tier.team_seats} {tier.team_seats === 1 ? 'seat' : 'seats'}
          </span>
        </div>
        {tier.byok_enabled && (
          <div className="flex items-center space-x-2 text-sm">
            <KeyIcon className="w-4 h-4 text-green-500" />
            <span style={{ color: currentTheme.textSecondary }}>BYOK Enabled</span>
          </div>
        )}
        {tier.priority_support && (
          <div className="flex items-center space-x-2 text-sm">
            <ShieldCheckIcon className="w-4 h-4 text-yellow-500" />
            <span style={{ color: currentTheme.textSecondary }}>Priority Support</span>
          </div>
        )}
      </div>

      {/* Integration Info */}
      <div className="pt-3 border-t" style={{ borderColor: currentTheme.border }}>
        <div className="grid grid-cols-2 gap-2 text-xs" style={{ color: currentTheme.textSecondary }}>
          {tier.lago_plan_code && (
            <div>
              <span className="font-semibold">Lago:</span> {tier.lago_plan_code}
            </div>
          )}
          {tier.active_user_count !== undefined && (
            <div>
              <span className="font-semibold">Users:</span> {tier.active_user_count}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );

  // Tier Form Modal
  const TierFormModal = () => (
    <AnimatePresence>
      {showModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
          onClick={() => setShowModal(false)}
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            style={{ backgroundColor: currentTheme.cardBackground }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold" style={{ color: currentTheme.text }}>
                  {modalMode === 'create' ? '➕ Create New Tier' : 
                   modalMode === 'clone' ? '📋 Clone Tier' : '✏️ Edit Tier'}
                </h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                >
                  <XMarkIcon className="w-6 h-6" style={{ color: currentTheme.textSecondary }} />
                </button>
              </div>

              <div className="space-y-4">
                {/* Basic Information */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      Tier Code *
                    </label>
                    <input
                      type="text"
                      value={formData.tier_code}
                      onChange={(e) => setFormData({ ...formData, tier_code: e.target.value.toLowerCase() })}
                      disabled={modalMode === 'edit'}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                      placeholder="e.g., professional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      Tier Name *
                    </label>
                    <input
                      type="text"
                      value={formData.tier_name}
                      onChange={(e) => setFormData({ ...formData, tier_name: e.target.value })}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                      placeholder="e.g., Professional"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 rounded border"
                    style={{
                      backgroundColor: currentTheme.inputBackground,
                      borderColor: currentTheme.border,
                      color: currentTheme.text
                    }}
                    placeholder="Brief description of this tier..."
                  />
                </div>

                {/* Pricing */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      Monthly Price ($) *
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.price_monthly}
                      onChange={(e) => setFormData({ ...formData, price_monthly: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      Yearly Price ($)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.price_yearly || ''}
                      onChange={(e) => setFormData({ ...formData, price_yearly: e.target.value ? parseFloat(e.target.value) : null })}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                      placeholder="Optional"
                    />
                  </div>
                </div>

                {/* Limits & Features */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      API Calls Limit
                    </label>
                    <input
                      type="number"
                      min="-1"
                      value={formData.api_calls_limit}
                      onChange={(e) => setFormData({ ...formData, api_calls_limit: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                    />
                    <p className="text-xs mt-1" style={{ color: currentTheme.textSecondary }}>
                      -1 for unlimited
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      Team Seats
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={formData.team_seats}
                      onChange={(e) => setFormData({ ...formData, team_seats: parseInt(e.target.value) || 1 })}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                      Sort Order
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={formData.sort_order}
                      onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 rounded border"
                      style={{
                        backgroundColor: currentTheme.inputBackground,
                        borderColor: currentTheme.border,
                        color: currentTheme.text
                      }}
                    />
                  </div>
                </div>

                {/* Feature Toggles */}
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { key: 'is_active', label: 'Active', icon: CheckIcon },
                    { key: 'is_invite_only', label: 'Invite Only', icon: ShieldCheckIcon },
                    { key: 'byok_enabled', label: 'BYOK Enabled', icon: KeyIcon },
                    { key: 'priority_support', label: 'Priority Support', icon: SparklesIcon }
                  ].map(feature => (
                    <label key={feature.key} className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData[feature.key]}
                        onChange={(e) => setFormData({ ...formData, [feature.key]: e.target.checked })}
                        className="w-4 h-4 rounded"
                      />
                      <feature.icon className="w-5 h-5" style={{ color: currentTheme.textSecondary }} />
                      <span style={{ color: currentTheme.text }}>{feature.label}</span>
                    </label>
                  ))}
                </div>

                {/* Integration Fields */}
                <div className="pt-4 border-t" style={{ borderColor: currentTheme.border }}>
                  <h3 className="text-lg font-semibold mb-3" style={{ color: currentTheme.text }}>
                    🔗 Integration Settings
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                        Lago Plan Code
                      </label>
                      <input
                        type="text"
                        value={formData.lago_plan_code}
                        onChange={(e) => setFormData({ ...formData, lago_plan_code: e.target.value })}
                        className="w-full px-3 py-2 rounded border"
                        style={{
                          backgroundColor: currentTheme.inputBackground,
                          borderColor: currentTheme.border,
                          color: currentTheme.text
                        }}
                        placeholder="e.g., professional_monthly"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                          Stripe Price ID (Monthly)
                        </label>
                        <input
                          type="text"
                          value={formData.stripe_price_monthly}
                          onChange={(e) => setFormData({ ...formData, stripe_price_monthly: e.target.value })}
                          className="w-full px-3 py-2 rounded border"
                          style={{
                            backgroundColor: currentTheme.inputBackground,
                            borderColor: currentTheme.border,
                            color: currentTheme.text
                          }}
                          placeholder="price_xxxxx"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                          Stripe Price ID (Yearly)
                        </label>
                        <input
                          type="text"
                          value={formData.stripe_price_yearly}
                          onChange={(e) => setFormData({ ...formData, stripe_price_yearly: e.target.value })}
                          className="w-full px-3 py-2 rounded border"
                          style={{
                            backgroundColor: currentTheme.inputBackground,
                            borderColor: currentTheme.border,
                            color: currentTheme.text
                          }}
                          placeholder="price_xxxxx"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 mt-6 pt-6 border-t" style={{ borderColor: currentTheme.border }}>
                <button
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded border hover:bg-gray-100 dark:hover:bg-gray-700"
                  style={{ borderColor: currentTheme.border, color: currentTheme.text }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveTier}
                  disabled={saving || !formData.tier_code || !formData.tier_name}
                  className="px-6 py-2 rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <CheckIcon className="w-5 h-5" />
                      <span>{modalMode === 'edit' ? 'Update' : 'Create'} Tier</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  // User Migration Modal
  const MigrationModal = () => (
    <AnimatePresence>
      {showMigrationModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
          onClick={() => setShowMigrationModal(false)}
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="rounded-lg shadow-xl max-w-2xl w-full"
            style={{ backgroundColor: currentTheme.cardBackground }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold flex items-center space-x-2" style={{ color: currentTheme.text }}>
                  <ArrowsRightLeftIcon className="w-7 h-7 text-blue-500" />
                  <span>Migrate User Tier</span>
                </h2>
                <button
                  onClick={() => setShowMigrationModal(false)}
                  className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                >
                  <XMarkIcon className="w-6 h-6" style={{ color: currentTheme.textSecondary }} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                    User ID (Keycloak) *
                  </label>
                  <input
                    type="text"
                    value={migrationData.user_id}
                    onChange={(e) => setMigrationData({ ...migrationData, user_id: e.target.value })}
                    className="w-full px-3 py-2 rounded border"
                    style={{
                      backgroundColor: currentTheme.inputBackground,
                      borderColor: currentTheme.border,
                      color: currentTheme.text
                    }}
                    placeholder="UUID from Keycloak"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                    New Tier *
                  </label>
                  <select
                    value={migrationData.new_tier_code}
                    onChange={(e) => setMigrationData({ ...migrationData, new_tier_code: e.target.value })}
                    className="w-full px-3 py-2 rounded border"
                    style={{
                      backgroundColor: currentTheme.inputBackground,
                      borderColor: currentTheme.border,
                      color: currentTheme.text
                    }}
                  >
                    <option value="">Select tier...</option>
                    {tiers.filter(t => t.is_active).map(tier => (
                      <option key={tier.tier_code} value={tier.tier_code}>
                        {tier.tier_name} (${tier.price_monthly}/mo)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: currentTheme.text }}>
                    Reason for Migration * (min 10 characters)
                  </label>
                  <textarea
                    value={migrationData.reason}
                    onChange={(e) => setMigrationData({ ...migrationData, reason: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 rounded border"
                    style={{
                      backgroundColor: currentTheme.inputBackground,
                      borderColor: currentTheme.border,
                      color: currentTheme.text
                    }}
                    placeholder="e.g., Customer support request, promotional upgrade, manual correction..."
                  />
                </div>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={migrationData.send_notification}
                    onChange={(e) => setMigrationData({ ...migrationData, send_notification: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <span style={{ color: currentTheme.text }}>Send email notification to user</span>
                </label>
              </div>

              <div className="flex justify-end space-x-3 mt-6 pt-6 border-t" style={{ borderColor: currentTheme.border }}>
                <button
                  onClick={() => setShowMigrationModal(false)}
                  className="px-4 py-2 rounded border hover:bg-gray-100 dark:hover:bg-gray-700"
                  style={{ borderColor: currentTheme.border, color: currentTheme.text }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleMigrateUser}
                  disabled={saving || !migrationData.user_id || !migrationData.new_tier_code || migrationData.reason.length < 10}
                  className="px-6 py-2 rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Migrating...</span>
                    </>
                  ) : (
                    <>
                      <ArrowsRightLeftIcon className="w-5 h-5" />
                      <span>Migrate User</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  // Delete Confirmation Modal
  const DeleteConfirmModal = () => (
    <AnimatePresence>
      {showDeleteConfirm && tierToDelete && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
          onClick={() => {
            setShowDeleteConfirm(false);
            setTierToDelete(null);
          }}
        >
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0.9 }}
            className="rounded-lg shadow-xl max-w-md w-full p-6"
            style={{ backgroundColor: currentTheme.cardBackground }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center space-x-3 mb-4">
              <ExclamationTriangleIcon className="w-12 h-12 text-red-500" />
              <h3 className="text-xl font-bold" style={{ color: currentTheme.text }}>
                Delete Tier?
              </h3>
            </div>
            <p className="mb-6" style={{ color: currentTheme.textSecondary }}>
              Are you sure you want to delete the tier <strong>{tierToDelete.tier_name}</strong>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setTierToDelete(null);
                }}
                className="px-4 py-2 rounded border hover:bg-gray-100 dark:hover:bg-gray-700"
                style={{ borderColor: currentTheme.border, color: currentTheme.text }}
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteTier(tierToDelete.id)}
                className="px-4 py-2 rounded bg-red-500 text-white hover:bg-red-600"
              >
                Delete
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  // Render functions for each tab
  const renderTiersTab = () => (
    <>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2" style={{ color: currentTheme.text }}>
            💳 Subscription Tier Management
          </h1>
          <p style={{ color: currentTheme.textSecondary }}>
            Manage subscription tiers, pricing, and feature flags
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-6 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white font-semibold hover:from-blue-600 hover:to-purple-600 flex items-center space-x-2 shadow-lg"
        >
          <PlusIcon className="w-5 h-5" />
          <span>Create Tier</span>
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex space-x-4 mb-6">
        <div className="flex-1 relative">
          <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2" style={{ color: currentTheme.textSecondary }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tiers..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border"
            style={{
              backgroundColor: currentTheme.inputBackground,
              borderColor: currentTheme.border,
              color: currentTheme.text
            }}
          />
        </div>
        <button
          onClick={() => setShowActiveOnly(!showActiveOnly)}
          className={`px-4 py-2 rounded-lg border flex items-center space-x-2 ${
            showActiveOnly ? 'bg-blue-500 text-white border-blue-500' : ''
          }`}
          style={!showActiveOnly ? { borderColor: currentTheme.border, color: currentTheme.text } : {}}
        >
          {showActiveOnly ? <EyeIcon className="w-5 h-5" /> : <EyeSlashIcon className="w-5 h-5" />}
          <span>{showActiveOnly ? 'Active Only' : 'Show All'}</span>
        </button>
      </div>

      {/* Tier Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredTiers.length === 0 ? (
        <div className="text-center py-20">
          <SparklesIcon className="w-16 h-16 mx-auto mb-4 opacity-30" style={{ color: currentTheme.textSecondary }} />
          <p className="text-xl" style={{ color: currentTheme.textSecondary }}>
            {searchQuery ? 'No tiers match your search' : 'No tiers created yet'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <AnimatePresence>
            {filteredTiers.map(tier => (
              <TierCard key={tier.id} tier={tier} />
            ))}
          </AnimatePresence>
        </div>
      )}
    </>
  );

  const renderMigrationsTab = () => (
    <>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-2" style={{ color: currentTheme.text }}>
            User Tier Migrations
          </h2>
          <p style={{ color: currentTheme.textSecondary }}>
            Audit log of all tier changes and manual migrations
          </p>
        </div>
        <button
          onClick={() => setShowMigrationModal(true)}
          className="px-6 py-3 rounded-lg bg-blue-500 text-white font-semibold hover:bg-blue-600 flex items-center space-x-2"
        >
          <ArrowsRightLeftIcon className="w-5 h-5" />
          <span>Migrate User</span>
        </button>
      </div>

      {migrations.length === 0 ? (
        <div className="text-center py-20">
          <ClockIcon className="w-16 h-16 mx-auto mb-4 opacity-30" style={{ color: currentTheme.textSecondary }} />
          <p className="text-xl" style={{ color: currentTheme.textSecondary }}>
            No migration history yet
          </p>
        </div>
      ) : (
        <div className="rounded-lg shadow overflow-hidden" style={{ backgroundColor: currentTheme.cardBackground }}>
          <table className="w-full">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Timestamp</th>
                <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>User</th>
                <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Change</th>
                <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Reason</th>
                <th className="px-4 py-3 text-left text-sm font-semibold" style={{ color: currentTheme.text }}>Admin</th>
              </tr>
            </thead>
            <tbody>
              {migrations.map((migration, idx) => (
                <tr key={migration.id} className="border-t" style={{ borderColor: currentTheme.border }}>
                  <td className="px-4 py-3 text-sm" style={{ color: currentTheme.textSecondary }}>
                    {new Date(migration.change_timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm" style={{ color: currentTheme.text }}>
                    <div>{migration.user_email || migration.user_id}</div>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                        {migration.old_tier_code || 'N/A'}
                      </span>
                      <ArrowsRightLeftIcon className="w-4 h-4" style={{ color: currentTheme.textSecondary }} />
                      <span className="px-2 py-1 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                        {migration.new_tier_code}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm" style={{ color: currentTheme.textSecondary }}>
                    {migration.change_reason}
                  </td>
                  <td className="px-4 py-3 text-sm" style={{ color: currentTheme.text }}>
                    {migration.changed_by}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );

  const renderAnalyticsTab = () => (
    <>
      <h2 className="text-2xl font-bold mb-6" style={{ color: currentTheme.text }}>
        Tier Analytics
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg shadow-lg p-6"
          style={{ backgroundColor: currentTheme.cardBackground }}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm mb-1" style={{ color: currentTheme.textSecondary }}>Total Tiers</p>
              <p className="text-3xl font-bold" style={{ color: currentTheme.text }}>{analytics.total_tiers}</p>
            </div>
            <CurrencyDollarIcon className="w-12 h-12 text-blue-500" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-lg shadow-lg p-6"
          style={{ backgroundColor: currentTheme.cardBackground }}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm mb-1" style={{ color: currentTheme.textSecondary }}>Active Tiers</p>
              <p className="text-3xl font-bold" style={{ color: currentTheme.text }}>{analytics.active_tiers}</p>
            </div>
            <CheckIcon className="w-12 h-12 text-green-500" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-lg shadow-lg p-6"
          style={{ backgroundColor: currentTheme.cardBackground }}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm mb-1" style={{ color: currentTheme.textSecondary }}>Total Users</p>
              <p className="text-3xl font-bold" style={{ color: currentTheme.text }}>{analytics.total_users}</p>
            </div>
            <UsersIcon className="w-12 h-12 text-purple-500" />
          </div>
        </motion.div>
      </div>

      <div className="rounded-lg shadow-lg p-6" style={{ backgroundColor: currentTheme.cardBackground }}>
        <h3 className="text-xl font-bold mb-4" style={{ color: currentTheme.text }}>
          Tier Distribution
        </h3>
        <p style={{ color: currentTheme.textSecondary }}>
          Coming soon: User distribution charts and revenue analytics
        </p>
      </div>
    </>
  );

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: currentTheme.background }}>
      <div className="max-w-7xl mx-auto">
        <TabNavigation />

        {activeTab === 'tiers' && renderTiersTab()}
        {activeTab === 'migrations' && renderMigrationsTab()}
        {activeTab === 'analytics' && renderAnalyticsTab()}

        <TierFormModal />
        <MigrationModal />
        <DeleteConfirmModal />
      </div>
    </div>
  );
}
