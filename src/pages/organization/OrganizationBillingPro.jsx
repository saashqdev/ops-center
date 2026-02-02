import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useParams } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';
import { useOrganization } from '../../contexts/OrganizationContext';
import {
  CreditCardIcon,
  UserGroupIcon,
  ChartBarIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  XMarkIcon,
  ArrowUpIcon,
  BanknotesIcon,
  CalendarIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlusIcon,
  PencilIcon,
  ArrowTrendingUpIcon
} from '@heroicons/react/24/outline';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { duration: 0.3 }
  }
};

export default function OrganizationBillingPro() {
  const { theme, currentTheme } = useTheme();
  const { currentOrg } = useOrganization();
  const { orgId } = useParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [billingData, setBillingData] = useState(null);
  const [allocations, setAllocations] = useState([]);
  const [usage, setUsage] = useState(null);
  const [error, setError] = useState(null);
  const [showAddCreditsModal, setShowAddCreditsModal] = useState(false);
  const [showAllocateModal, setShowAllocateModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Use orgId from URL if available, otherwise fall back to currentOrg
  const effectiveOrgId = orgId || currentOrg?.id;

  // Toast notification
  const [toast, setToast] = useState({
    show: false,
    message: '',
    type: 'success'
  });

  useEffect(() => {
    if (effectiveOrgId) {
      loadBillingData();
    }
  }, [effectiveOrgId]);

  const loadBillingData = async () => {
    if (!effectiveOrgId) return;

    try {
      setLoading(true);
      setError(null);

      // Load all data in parallel
      const [billingRes, allocationsRes, usageRes] = await Promise.all([
        fetch(`/api/v1/org-billing/billing/org/${effectiveOrgId}`, {
          credentials: 'include',
          cache: 'no-store'
        }),
        fetch(`/api/v1/org-billing/credits/${effectiveOrgId}/allocations`, {
          credentials: 'include',
          cache: 'no-store'
        }),
        fetch(`/api/v1/org-billing/credits/${effectiveOrgId}/usage`, {
          credentials: 'include',
          cache: 'no-store'
        })
      ]);

      if (!billingRes.ok) throw new Error('Failed to load billing data');

      const billing = await billingRes.json();
      const allocs = allocationsRes.ok ? await allocationsRes.json() : [];
      const usageData = usageRes.ok ? await usageRes.json() : null;

      setBillingData(billing);
      setAllocations(allocs);
      setUsage(usageData);
    } catch (err) {
      console.error('Failed to load billing:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadBillingData();
    setRefreshing(false);
  };

  const showToast = (message, type = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast({ show: false, message: '', type }), 5000);
  };

  const formatCredits = (amount) => {
    if (amount === null || amount === undefined) return '0';
    return Math.floor(parseFloat(amount)).toLocaleString();
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '$0.00';
    return `$${parseFloat(amount).toFixed(2)}`;
  };

  const calculatePercent = (value, total) => {
    if (!total || total === 0) return 0;
    return Math.min((value / total) * 100, 100);
  };

  const getColorForPercent = (percent) => {
    if (percent >= 90) return 'text-red-400';
    if (percent >= 75) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getGradientForPercent = (percent) => {
    if (percent >= 90) return 'from-red-500 to-red-600';
    if (percent >= 75) return 'from-yellow-500 to-orange-500';
    return 'from-green-500 to-emerald-500';
  };

  const handleAddCredits = async (amount, purchaseAmount) => {
    try {
      const response = await fetch(`/api/v1/org-billing/credits/${effectiveOrgId}/add?credits=${amount}&purchase_amount=${purchaseAmount}`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to add credits');

      showToast(`Successfully added ${formatCredits(amount)} credits`, 'success');
      setShowAddCreditsModal(false);
      await loadBillingData();
    } catch (err) {
      showToast(`Failed to add credits: ${err.message}`, 'error');
    }
  };

  const handleAllocateCredits = async (userId, credits, resetPeriod, notes) => {
    try {
      const response = await fetch(`/api/v1/org-billing/credits/${effectiveOrgId}/allocate`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          allocated_credits: credits,
          reset_period: resetPeriod,
          notes: notes
        })
      });

      if (!response.ok) throw new Error('Failed to allocate credits');

      showToast(`Successfully allocated ${formatCredits(credits)} credits`, 'success');
      setShowAllocateModal(false);
      setSelectedUser(null);
      await loadBillingData();
    } catch (err) {
      showToast(`Failed to allocate credits: ${err.message}`, 'error');
    }
  };

  const handleUpgradeSubscription = async (newPlan) => {
    try {
      const response = await fetch(`/api/v1/org-billing/subscriptions/${effectiveOrgId}/upgrade?new_plan=${newPlan}`, {
        method: 'PUT',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to upgrade subscription');

      const result = await response.json();
      showToast(`Successfully upgraded from ${result.old_plan.toUpperCase()} to ${result.new_plan.toUpperCase()} plan`, 'success');
      setShowUpgradeModal(false);
      await loadBillingData();
    } catch (err) {
      showToast(`Failed to upgrade subscription: ${err.message}`, 'error');
    }
  };

  const handleDownloadReport = async () => {
    try {
      const response = await fetch(`/api/v1/org-billing/billing/org/${effectiveOrgId}`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to fetch billing data');

      const data = await response.json();
      
      // Generate CSV content
      let csv = 'Organization Billing Report\n\n';
      
      // Organization Info
      csv += 'Organization Information\n';
      csv += `Name,${data.organization?.name || 'N/A'}\n`;
      csv += `ID,${data.organization?.id || 'N/A'}\n`;
      csv += `Status,${data.organization?.status || 'N/A'}\n\n`;
      
      // Subscription Info
      csv += 'Subscription Details\n';
      csv += `Plan,${data.subscription?.subscription_plan?.toUpperCase() || 'N/A'}\n`;
      csv += `Monthly Cost,${data.subscription?.monthly_price || 0}\n`;
      csv += `Status,${data.subscription?.status?.toUpperCase() || 'N/A'}\n\n`;
      
      // Credit Pool
      csv += 'Credit Pool\n';
      csv += `Total Credits,${data.credit_pool?.total_credits || 0}\n`;
      csv += `Allocated Credits,${data.credit_pool?.allocated_credits || 0}\n`;
      csv += `Used Credits,${data.credit_pool?.used_credits || 0}\n`;
      csv += `Available Credits,${data.credit_pool?.available_credits || 0}\n\n`;
      
      // User Allocations
      if (allocations && allocations.length > 0) {
        csv += 'User Credit Allocations\n';
        csv += 'User ID,Allocated Credits,Used Credits,Remaining Credits,Reset Period,Active\n';
        allocations.forEach(alloc => {
          csv += `${alloc.user_id},${alloc.allocated_credits},${alloc.used_credits},${alloc.remaining_credits},${alloc.reset_period},${alloc.is_active}\n`;
        });
        csv += '\n';
      }
      
      // Usage Stats
      if (usage) {
        csv += 'Usage Statistics\n';
        csv += `Total Credits Used,${usage.total_credits_used || 0}\n`;
        csv += `Active Users,${usage.active_users || 0}\n`;
        csv += `Total Requests,${usage.total_requests || 0}\n`;
        if (usage.by_service && usage.by_service.length > 0) {
          csv += '\nUsage by Service\n';
          csv += 'Service Type,Credits Used,Request Count\n';
          usage.by_service.forEach(service => {
            csv += `${service.service_type},${service.credits_used},${service.request_count}\n`;
          });
        }
      }
      
      // Create download
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `billing-report-${effectiveOrgId}-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showToast('Billing report downloaded successfully', 'success');
    } catch (err) {
      showToast(`Failed to download report: ${err.message}`, 'error');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className={`${theme.card} rounded-xl p-8 max-w-md w-full m-4 text-center`}
        >
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <ExclamationTriangleIcon className="h-8 w-8 text-red-400" />
          </div>
          <h2 className={`text-2xl font-bold ${theme.text.primary} mb-2`}>Error Loading Data</h2>
          <p className={`${theme.text.secondary} mb-6`}>{error}</p>
          <button
            onClick={loadBillingData}
            className={`px-6 py-2 ${theme.button} rounded-lg transition-colors`}
          >
            Try Again
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 p-6"
    >
      {/* Page Header */}
      <motion.div variants={itemVariants}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-3xl font-bold ${theme.text.primary} flex items-center gap-3`}>
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
                <CreditCardIcon className="h-6 w-6 text-white" />
              </div>
              Organization Billing
            </h1>
            <p className={`${theme.text.secondary} mt-1 ml-13`}>
              Manage subscription, credits, and team allocations
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={`p-2 ${theme.button} rounded-lg transition-colors`}
          >
            <ArrowPathIcon className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </motion.div>

      {/* Subscription Plan */}
      <motion.div variants={itemVariants} className={`${theme.card} rounded-xl p-6 border border-blue-500/20`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-xl font-semibold ${theme.text.primary}`}>Subscription Plan</h2>
          <button 
            onClick={() => setShowUpgradeModal(true)}
            className={`px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm`}
          >
            Upgrade to Hybrid
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Current Plan</div>
            <div className={`text-2xl font-bold ${theme.text.primary}`}>
              {billingData?.subscription?.subscription_plan?.toUpperCase() || 'PLATFORM'}
            </div>
          </div>

          <div>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Monthly Cost</div>
            <div className={`text-2xl font-bold ${theme.text.accent}`}>
              {formatCurrency(billingData?.subscription?.monthly_price || 50)}
            </div>
          </div>

          <div>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Status</div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              billingData?.subscription?.status === 'active'
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
            }`}>
              {billingData?.subscription?.status?.toUpperCase() || 'ACTIVE'}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Credit Pool */}
      <motion.div variants={itemVariants} className={`${theme.card} rounded-xl p-6 border border-purple-500/20`}>
        <div className="flex items-center justify-between mb-6">
          <h2 className={`text-xl font-semibold ${theme.text.primary} flex items-center gap-3`}>
            <BanknotesIcon className="h-6 w-6 text-purple-500" />
            Credit Pool
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddCreditsModal(true)}
              className={`px-4 py-2 ${theme.button} rounded-lg transition-colors flex items-center gap-2`}
            >
              <PlusIcon className="h-5 w-5" />
              Add Credits
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Total Credits</div>
            <div className={`text-2xl font-bold ${theme.text.primary}`}>
              {formatCredits(billingData?.credit_pool?.total_credits || 0)}
            </div>
          </div>

          <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Allocated</div>
            <div className={`text-2xl font-bold text-blue-400`}>
              {formatCredits(billingData?.credit_pool?.allocated_credits || 0)}
            </div>
          </div>

          <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Used</div>
            <div className={`text-2xl font-bold text-yellow-400`}>
              {formatCredits(billingData?.credit_pool?.used_credits || 0)}
            </div>
          </div>

          <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
            <div className={`text-sm ${theme.text.secondary} mb-1`}>Available</div>
            <div className={`text-2xl font-bold text-green-400`}>
              {formatCredits(billingData?.credit_pool?.available_credits || 0)}
            </div>
          </div>
        </div>

        {/* Pool Usage Bar */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className={theme.text.secondary}>Pool Utilization</span>
            <span className={getColorForPercent(calculatePercent(billingData?.credit_pool?.allocated_credits, billingData?.credit_pool?.total_credits))}>
              {calculatePercent(billingData?.credit_pool?.allocated_credits, billingData?.credit_pool?.total_credits).toFixed(1)}% allocated
            </span>
          </div>
          <div className="w-full bg-gray-700/30 rounded-full h-3">
            <div
              className={`h-3 rounded-full bg-gradient-to-r ${getGradientForPercent(calculatePercent(billingData?.credit_pool?.allocated_credits, billingData?.credit_pool?.total_credits))}`}
              style={{ width: `${calculatePercent(billingData?.credit_pool?.allocated_credits, billingData?.credit_pool?.total_credits)}%` }}
            ></div>
          </div>
        </div>
      </motion.div>

      {/* Team Allocations */}
      <motion.div variants={itemVariants} className={`${theme.card} rounded-xl p-6`}>
        <div className="flex items-center justify-between mb-6">
          <h2 className={`text-xl font-semibold ${theme.text.primary} flex items-center gap-3`}>
            <UserGroupIcon className="h-6 w-6 text-blue-500" />
            Team Allocations
          </h2>
          <button
            onClick={() => setShowAllocateModal(true)}
            className={`px-4 py-2 ${theme.button} rounded-lg transition-colors flex items-center gap-2`}
          >
            <PlusIcon className="h-5 w-5" />
            Allocate Credits
          </button>
        </div>

        {allocations && allocations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={`border-b ${currentTheme === 'light' ? 'border-gray-300' : 'border-gray-700'}`}>
                  <th className={`text-left py-3 px-4 ${theme.text.secondary} font-medium`}>User</th>
                  <th className={`text-right py-3 px-4 ${theme.text.secondary} font-medium`}>Allocated</th>
                  <th className={`text-right py-3 px-4 ${theme.text.secondary} font-medium`}>Used</th>
                  <th className={`text-right py-3 px-4 ${theme.text.secondary} font-medium`}>Remaining</th>
                  <th className={`text-center py-3 px-4 ${theme.text.secondary} font-medium`}>Usage %</th>
                  <th className={`text-center py-3 px-4 ${theme.text.secondary} font-medium`}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {allocations.map((allocation) => (
                  <tr
                    key={allocation.id}
                    className={`border-b ${currentTheme === 'light' ? 'border-gray-200' : 'border-gray-800'} hover:bg-gray-800/30 transition-colors`}
                  >
                    <td className="py-3 px-4">
                      <div className={`font-medium ${theme.text.primary}`}>
                        {allocation.user_email || allocation.user_id}
                      </div>
                      <div className={`text-xs ${theme.text.secondary}`}>
                        Reset: {allocation.reset_period || 'monthly'}
                      </div>
                    </td>
                    <td className={`text-right py-3 px-4 font-semibold ${theme.text.primary}`}>
                      {formatCredits(allocation.allocated_credits)}
                    </td>
                    <td className={`text-right py-3 px-4 font-semibold text-yellow-400`}>
                      {formatCredits(allocation.used_credits)}
                    </td>
                    <td className={`text-right py-3 px-4 font-semibold text-green-400`}>
                      {formatCredits(allocation.remaining_credits)}
                    </td>
                    <td className="text-center py-3 px-4">
                      <span className={`font-semibold ${getColorForPercent(calculatePercent(allocation.used_credits, allocation.allocated_credits))}`}>
                        {calculatePercent(allocation.used_credits, allocation.allocated_credits).toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-3 px-4">
                      <button
                        onClick={() => {
                          setSelectedUser(allocation);
                          setShowAllocateModal(true);
                        }}
                        className="p-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors"
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <UserGroupIcon className="h-16 w-16 mx-auto text-gray-500 mb-4" />
            <p className={`${theme.text.secondary}`}>No credit allocations yet</p>
            <button
              onClick={() => setShowAllocateModal(true)}
              className={`mt-4 px-6 py-2 ${theme.button} rounded-lg transition-colors`}
            >
              Allocate First User
            </button>
          </div>
        )}
      </motion.div>

      {/* Usage Attribution */}
      {usage && (
        <motion.div variants={itemVariants} className={`${theme.card} rounded-xl p-6`}>
          <div className="flex items-center gap-3 mb-6">
            <ChartBarIcon className="h-6 w-6 text-purple-500" />
            <h2 className={`text-xl font-semibold ${theme.text.primary}`}>Usage Attribution (This Month)</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
              <div className={`text-sm ${theme.text.secondary} mb-2`}>Total Used</div>
              <div className={`text-3xl font-bold ${theme.text.primary}`}>
                {formatCredits(usage.total_credits_used || 0)}
              </div>
              <div className={`text-xs ${theme.text.secondary} mt-1`}>credits this month</div>
            </div>

            <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
              <div className={`text-sm ${theme.text.secondary} mb-2`}>Top User</div>
              <div className={`text-lg font-bold ${theme.text.accent} truncate`}>
                {usage.top_user?.user_email || 'N/A'}
              </div>
              <div className={`text-sm ${theme.text.secondary} mt-1`}>
                {formatCredits(usage.top_user?.credits_used || 0)} credits
              </div>
            </div>

            <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-800/50'}`}>
              <div className={`text-sm ${theme.text.secondary} mb-2`}>Top Model</div>
              <div className={`text-lg font-bold ${theme.text.accent} truncate`}>
                {usage.top_model?.service_name || 'N/A'}
              </div>
              <div className={`text-sm ${theme.text.secondary} mt-1`}>
                {formatCredits(usage.top_model?.credits_used || 0)} credits
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Billing History */}
      <motion.div variants={itemVariants} className={`${theme.card} rounded-xl p-6`}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <DocumentTextIcon className="h-6 w-6 text-green-500" />
            <h2 className={`text-xl font-semibold ${theme.text.primary}`}>Billing History</h2>
          </div>
          <button 
            onClick={handleDownloadReport}
            className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            Download Report
          </button>
        </div>

        <div className="text-center py-12">
          <DocumentTextIcon className="h-16 w-16 mx-auto text-gray-500 mb-4" />
          <p className={`${theme.text.secondary}`}>No billing history yet</p>
        </div>
      </motion.div>

      {/* Toast Notification */}
      {toast.show && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          className="fixed bottom-4 right-4 z-50"
        >
          <div className={`flex items-center gap-3 px-6 py-4 rounded-lg shadow-lg ${
            toast.type === 'success'
              ? 'bg-green-500/20 border border-green-500/30 text-green-400'
              : 'bg-red-500/20 border border-red-500/30 text-red-400'
          }`}>
            {toast.type === 'success' ? (
              <CheckCircleIcon className="h-5 w-5" />
            ) : (
              <XMarkIcon className="h-5 w-5" />
            )}
            <span>{toast.message}</span>
          </div>
        </motion.div>
      )}

      {/* Add Credits Modal */}
      {showAddCreditsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`${theme.card} rounded-xl p-6 max-w-md w-full`}
          >
            <h3 className={`text-xl font-bold ${theme.text.primary} mb-4`}>Add Credits</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              const credits = parseInt(formData.get('credits'));
              const amount = parseFloat(formData.get('amount') || '0');
              handleAddCredits(credits, amount);
            }}>
              <div className="mb-4">
                <label className={`block text-sm font-medium ${theme.text.primary} mb-2`}>
                  Credits Amount
                </label>
                <input
                  type="number"
                  name="credits"
                  required
                  min="1"
                  className={`w-full px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100 text-gray-800' : 'bg-gray-800 text-white'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                  placeholder="Enter credits amount"
                />
              </div>
              <div className="mb-6">
                <label className={`block text-sm font-medium ${theme.text.primary} mb-2`}>
                  Purchase Amount (optional)
                </label>
                <input
                  type="number"
                  name="amount"
                  step="0.01"
                  min="0"
                  className={`w-full px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100 text-gray-800' : 'bg-gray-800 text-white'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                  placeholder="Enter purchase amount"
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddCreditsModal(false)}
                  className={`flex-1 px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-200 text-gray-800' : 'bg-gray-700 text-white'} transition-colors`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                >
                  Add Credits
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Allocate Credits Modal */}
      {showAllocateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`${theme.card} rounded-xl p-6 max-w-md w-full`}
          >
            <h3 className={`text-xl font-bold ${theme.text.primary} mb-4`}>Allocate Credits</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              const userId = formData.get('userId');
              const credits = parseInt(formData.get('credits'));
              const resetPeriod = formData.get('resetPeriod');
              const notes = formData.get('notes');
              handleAllocateCredits(userId, credits, resetPeriod, notes);
            }}>
              <div className="mb-4">
                <label className={`block text-sm font-medium ${theme.text.primary} mb-2`}>
                  User ID
                </label>
                <input
                  type="text"
                  name="userId"
                  required
                  className={`w-full px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100 text-gray-800' : 'bg-gray-800 text-white'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                  placeholder="Enter user ID"
                />
              </div>
              <div className="mb-4">
                <label className={`block text-sm font-medium ${theme.text.primary} mb-2`}>
                  Credits Amount
                </label>
                <input
                  type="number"
                  name="credits"
                  required
                  min="1"
                  className={`w-full px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100 text-gray-800' : 'bg-gray-800 text-white'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                  placeholder="Enter credits amount"
                />
              </div>
              <div className="mb-4">
                <label className={`block text-sm font-medium ${theme.text.primary} mb-2`}>
                  Reset Period
                </label>
                <select
                  name="resetPeriod"
                  className={`w-full px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100 text-gray-800' : 'bg-gray-800 text-white'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                >
                  <option value="none">No Reset</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div className="mb-6">
                <label className={`block text-sm font-medium ${theme.text.primary} mb-2`}>
                  Notes (optional)
                </label>
                <textarea
                  name="notes"
                  rows="3"
                  className={`w-full px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-100 text-gray-800' : 'bg-gray-800 text-white'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                  placeholder="Enter any notes"
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowAllocateModal(false);
                    setSelectedUser(null);
                  }}
                  className={`flex-1 px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-200 text-gray-800' : 'bg-gray-700 text-white'} transition-colors`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                >
                  Allocate Credits
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Upgrade Subscription Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`${theme.card} rounded-xl p-6 max-w-md w-full`}
          >
            <h3 className={`text-xl font-bold ${theme.text.primary} mb-4 flex items-center gap-2`}>
              <ArrowTrendingUpIcon className="h-6 w-6 text-blue-400" />
              Upgrade to Hybrid Plan
            </h3>
            
            <div className="mb-6 space-y-4">
              <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-blue-50' : 'bg-blue-900/20'} border border-blue-500/30`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${theme.text.secondary}`}>Current Plan</span>
                  <span className={`font-semibold ${theme.text.primary}`}>
                    {billingData?.subscription?.subscription_plan?.toUpperCase() || 'PLATFORM'}
                  </span>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${theme.text.secondary}`}>Current Monthly Cost</span>
                  <span className={`font-semibold ${theme.text.primary}`}>
                    ${billingData?.subscription?.monthly_price?.toFixed(2) || '50.00'}
                  </span>
                </div>
                <div className="border-t border-blue-500/20 my-2"></div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${theme.text.secondary}`}>New Plan</span>
                  <span className={`font-bold text-blue-400`}>HYBRID</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={`text-sm ${theme.text.secondary}`}>New Monthly Cost</span>
                  <span className={`font-bold text-blue-400`}>$99.00</span>
                </div>
              </div>

              <div className={`p-4 rounded-lg ${currentTheme === 'light' ? 'bg-green-50' : 'bg-green-900/20'} border border-green-500/30`}>
                <h4 className={`font-semibold ${theme.text.primary} mb-2 flex items-center gap-2`}>
                  <CheckCircleIcon className="h-5 w-5 text-green-400" />
                  What's Included:
                </h4>
                <ul className={`text-sm ${theme.text.secondary} space-y-1 ml-7`}>
                  <li>• Access to all platform models</li>
                  <li>• BYOK (Bring Your Own Keys) support</li>
                  <li>• Priority support</li>
                  <li>• Advanced analytics</li>
                  <li>• Custom integrations</li>
                </ul>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowUpgradeModal(false)}
                className={`flex-1 px-4 py-2 rounded-lg ${currentTheme === 'light' ? 'bg-gray-200 text-gray-800' : 'bg-gray-700 text-white'} transition-colors`}
              >
                Cancel
              </button>
              <button
                onClick={() => handleUpgradeSubscription('hybrid')}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-semibold"
              >
                Confirm Upgrade
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}
