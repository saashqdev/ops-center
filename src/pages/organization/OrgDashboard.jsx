/**
 * OrgDashboard - Organization Overview & Self-Service Hub
 *
 * Allows any authenticated user to:
 * - View their organizations and roles within each
 * - Create a new organization
 * - Switch active organization
 * - Navigate to org management pages
 *
 * Created: February 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BuildingOfficeIcon,
  PlusIcon,
  UsersIcon,
  CogIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
  StarIcon,
  TrashIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';
import { useOrganization } from '../../contexts/OrganizationContext';
import { useToast } from '../../components/Toast';

const MAX_ORGS_DISPLAY = 20;

// Role badge colors
const roleBadgeColors = {
  owner: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  admin: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  member: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
  billing_admin: 'bg-green-500/20 text-green-300 border-green-500/30',
};

// Role labels
const roleLabels = {
  owner: 'Owner',
  admin: 'Admin',
  member: 'Member',
  billing_admin: 'Billing Admin',
};

export default function OrgDashboard() {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const toast = useToast();
  const {
    organizations,
    currentOrg,
    currentOrgId,
    switchOrganization,
    setCurrentOrg,
    refreshOrganizations,
    loading: orgLoading,
  } = useOrganization();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(null);
  const [showEditModal, setShowEditModal] = useState(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [editOrgName, setEditOrgName] = useState('');
  const [error, setError] = useState(null);

  const handleCreateOrg = async (e) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;

    setCreating(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/org', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newOrgName.trim() }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create organization');
      }

      const data = await response.json();
      toast.success(`Organization "${newOrgName}" created successfully!`);
      setNewOrgName('');
      setShowCreateModal(false);

      // Refresh org list and switch to new org
      await refreshOrganizations();
      if (data.organization?.id) {
        setCurrentOrg(data.organization.id);
      }
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteOrg = async (orgId, orgName) => {
    setDeleting(true);
    try {
      const response = await fetch(`/api/v1/org/${orgId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete organization');
      }

      toast.success(`Organization "${orgName}" deleted`);
      setShowDeleteModal(null);
      await refreshOrganizations();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeleting(false);
    }
  };

  const handleEditOrg = async (e, orgId) => {
    e.preventDefault();
    if (!editOrgName.trim()) return;

    setEditing(true);
    try {
      const response = await fetch(`/api/v1/org/${orgId}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editOrgName.trim() }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update organization');
      }

      toast.success('Organization updated');
      setShowEditModal(null);
      await refreshOrganizations();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setEditing(false);
    }
  };

  const handleSwitchOrg = (orgId) => {
    setCurrentOrg(orgId);
    toast.success('Switched organization');
  };

  if (orgLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${theme.text.primary}`}>
            My Organizations
          </h1>
          <p className={`mt-1 ${theme.text.secondary}`}>
            Create and manage your organizations, invite team members, and configure settings.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors font-medium"
        >
          <PlusIcon className="h-5 w-5" />
          New Organization
        </button>
      </div>

      {/* Organization Cards */}
      {organizations.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-800/40 border border-gray-700/50 rounded-2xl p-12 text-center"
        >
          <BuildingOfficeIcon className="h-16 w-16 text-gray-600 mx-auto mb-4" />
          <h2 className={`text-xl font-semibold mb-2 ${theme.text.primary}`}>
            No Organizations Yet
          </h2>
          <p className={`mb-6 ${theme.text.secondary}`}>
            Create your first organization to start managing teams and resources.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors font-medium"
          >
            <PlusIcon className="h-5 w-5" />
            Create Organization
          </button>
        </motion.div>
      ) : (
        <div className="grid gap-4">
          {organizations.slice(0, MAX_ORGS_DISPLAY).map((org, index) => (
            <motion.div
              key={org.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`bg-gray-800/40 border rounded-xl p-6 transition-all hover:border-purple-500/50 ${
                currentOrgId === org.id
                  ? 'border-purple-500/70 ring-1 ring-purple-500/20'
                  : 'border-gray-700/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Org Icon */}
                  <div className={`p-3 rounded-xl ${
                    currentOrgId === org.id
                      ? 'bg-purple-500/20'
                      : 'bg-gray-700/50'
                  }`}>
                    <BuildingOfficeIcon className={`h-6 w-6 ${
                      currentOrgId === org.id ? 'text-purple-400' : 'text-gray-400'
                    }`} />
                  </div>

                  {/* Org Info */}
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className={`text-lg font-semibold ${theme.text.primary}`}>
                        {org.name}
                      </h3>
                      {currentOrgId === org.id && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded-full border border-purple-500/30">
                          <CheckCircleIcon className="h-3 w-3" />
                          Active
                        </span>
                      )}
                      <span className={`px-2 py-0.5 text-xs rounded-full border ${
                        roleBadgeColors[org.role] || roleBadgeColors.member
                      }`}>
                        {roleLabels[org.role] || org.role}
                      </span>
                    </div>
                    <div className={`flex items-center gap-4 mt-1 text-sm ${theme.text.secondary}`}>
                      <span className="flex items-center gap-1">
                        <UsersIcon className="h-4 w-4" />
                        {org.member_count || 0} member{(org.member_count || 0) !== 1 ? 's' : ''}
                      </span>
                      <span>Plan: {org.plan_tier || 'Free'}</span>
                      {org.status && org.status !== 'active' && (
                        <span className="text-yellow-400">{org.status}</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {currentOrgId !== org.id && (
                    <button
                      onClick={() => handleSwitchOrg(org.id)}
                      className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                    >
                      Switch
                    </button>
                  )}

                  {(org.role === 'admin' || org.role === 'owner') && (
                    <button
                      onClick={() => {
                        if (currentOrgId !== org.id) setCurrentOrg(org.id);
                        navigate('/admin/org/team');
                      }}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                      title="Manage Team"
                    >
                      <UsersIcon className="h-4 w-4" />
                    </button>
                  )}

                  {(org.role === 'admin' || org.role === 'owner') && (
                    <button
                      onClick={() => {
                        if (currentOrgId !== org.id) setCurrentOrg(org.id);
                        navigate('/admin/org/settings');
                      }}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                      title="Settings"
                    >
                      <CogIcon className="h-4 w-4" />
                    </button>
                  )}

                  {org.role === 'owner' && (
                    <>
                      <button
                        onClick={() => {
                          setEditOrgName(org.name);
                          setShowEditModal(org);
                        }}
                        className="p-2 text-gray-400 hover:text-blue-400 hover:bg-gray-700 rounded-lg transition-colors"
                        title="Edit Organization"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setShowDeleteModal(org)}
                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition-colors"
                        title="Delete Organization"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Create Organization Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-800 rounded-xl shadow-2xl max-w-md w-full border border-gray-700"
            >
              <div className="flex items-center justify-between p-6 border-b border-gray-700">
                <h2 className={`text-lg font-semibold ${theme.text.primary}`}>
                  Create Organization
                </h2>
                <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-white">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleCreateOrg} className="p-6 space-y-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${theme.text.secondary}`}>
                    Organization Name
                  </label>
                  <input
                    type="text"
                    value={newOrgName}
                    onChange={(e) => setNewOrgName(e.target.value)}
                    placeholder="e.g., Acme Corp"
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    autoFocus
                    required
                    minLength={2}
                    maxLength={200}
                  />
                </div>

                {error && (
                  <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300 text-sm">
                    <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
                    {error}
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating || !newOrgName.trim()}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {creating ? 'Creating...' : 'Create'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Edit Organization Modal */}
      <AnimatePresence>
        {showEditModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-800 rounded-xl shadow-2xl max-w-md w-full border border-gray-700"
            >
              <div className="flex items-center justify-between p-6 border-b border-gray-700">
                <h2 className={`text-lg font-semibold ${theme.text.primary}`}>
                  Edit Organization
                </h2>
                <button onClick={() => setShowEditModal(null)} className="text-gray-400 hover:text-white">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={(e) => handleEditOrg(e, showEditModal.id)} className="p-6 space-y-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${theme.text.secondary}`}>
                    Organization Name
                  </label>
                  <input
                    type="text"
                    value={editOrgName}
                    onChange={(e) => setEditOrgName(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    autoFocus
                    required
                    minLength={2}
                    maxLength={200}
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowEditModal(null)}
                    className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={editing || !editOrgName.trim()}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {editing ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {showDeleteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-800 rounded-xl shadow-2xl max-w-md w-full border border-red-500/50"
            >
              <div className="flex items-center gap-3 p-6 border-b border-gray-700">
                <ExclamationTriangleIcon className="h-6 w-6 text-red-500" />
                <h2 className={`text-lg font-semibold ${theme.text.primary}`}>
                  Delete Organization
                </h2>
              </div>

              <div className="p-6 space-y-4">
                <p className={theme.text.secondary}>
                  Are you sure you want to delete <span className="font-semibold text-white">{showDeleteModal.name}</span>?
                  This will permanently remove all members, settings, and data associated with this organization.
                </p>
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <p className="text-red-300 text-sm font-medium">This action cannot be undone.</p>
                </div>
              </div>

              <div className="flex justify-end gap-3 p-6 border-t border-gray-700">
                <button
                  onClick={() => setShowDeleteModal(null)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDeleteOrg(showDeleteModal.id, showDeleteModal.name)}
                  disabled={deleting}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors disabled:opacity-50"
                >
                  {deleting ? 'Deleting...' : 'Delete Organization'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
