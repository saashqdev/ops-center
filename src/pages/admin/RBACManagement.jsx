import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheckIcon,
  UserGroupIcon,
  KeyIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import axios from 'axios';

export default function RBACManagement() {
  const [activeTab, setActiveTab] = useState('roles');
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [showAssignRole, setShowAssignRole] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'roles') {
        const { data } = await axios.get('/api/v1/rbac/roles');
        setRoles(data.roles || []);
      } else if (activeTab === 'permissions') {
        const { data } = await axios.get('/api/v1/rbac/permissions');
        setPermissions(data.permissions || []);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load RBAC data');
    } finally {
      setLoading(false);
    }
  };

  const createRole = async (roleData) => {
    try {
      await axios.post('/api/v1/rbac/roles', roleData);
      toast.success('Role created successfully');
      setShowCreateRole(false);
      loadData();
    } catch (error) {
      console.error('Failed to create role:', error);
      toast.error(error.response?.data?.detail || 'Failed to create role');
    }
  };

  const deleteRole = async (roleId) => {
    if (!confirm('Are you sure you want to delete this role?')) return;

    try {
      await axios.delete(`/api/v1/rbac/roles/${roleId}`);
      toast.success('Role deleted successfully');
      loadData();
    } catch (error) {
      console.error('Failed to delete role:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete role');
    }
  };

  const assignPermissionToRole = async (roleId, permissionName) => {
    try {
      await axios.post(`/api/v1/rbac/roles/${roleId}/permissions`, {
        permission_name: permissionName
      });
      toast.success('Permission assigned successfully');
      loadRolePermissions(roleId);
    } catch (error) {
      console.error('Failed to assign permission:', error);
      toast.error(error.response?.data?.detail || 'Failed to assign permission');
    }
  };

  const revokePermissionFromRole = async (roleId, permissionName) => {
    try {
      await axios.delete(`/api/v1/rbac/roles/${roleId}/permissions/${permissionName}`);
      toast.success('Permission revoked successfully');
      loadRolePermissions(roleId);
    } catch (error) {
      console.error('Failed to revoke permission:', error);
      toast.error(error.response?.data?.detail || 'Failed to revoke permission');
    }
  };

  const loadRolePermissions = async (roleId) => {
    try {
      const { data } = await axios.get(`/api/v1/rbac/roles/${roleId}/permissions`);
      setSelectedRole(prev => ({ ...prev, permissions: data.permissions || [] }));
    } catch (error) {
      console.error('Failed to load role permissions:', error);
    }
  };

  const assignRoleToUser = async (roleId, userEmail, orgId = null, expiresInDays = null) => {
    try {
      await axios.post(`/api/v1/rbac/roles/${roleId}/users`, {
        user_email: userEmail,
        organization_id: orgId,
        expires_in_days: expiresInDays
      });
      toast.success('Role assigned to user successfully');
      setShowAssignRole(false);
    } catch (error) {
      console.error('Failed to assign role to user:', error);
      toast.error(error.response?.data?.detail || 'Failed to assign role to user');
    }
  };

  const filteredRoles = roles.filter(role =>
    role.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    role.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredPermissions = permissions.filter(perm =>
    perm.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    perm.resource?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    perm.action?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <ShieldCheckIcon className="w-10 h-10 text-indigo-600 dark:text-indigo-400" />
            Advanced RBAC Management
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Manage roles, permissions, and user access across your organization
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-4 mb-6 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('roles')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'roles'
                ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            <UserGroupIcon className="w-5 h-5 inline mr-2" />
            Roles
          </button>
          <button
            onClick={() => setActiveTab('permissions')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'permissions'
                ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            <KeyIcon className="w-5 h-5 inline mr-2" />
            Permissions
          </button>
        </div>

        {/* Search and Actions */}
        <div className="flex justify-between items-center mb-6">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder={`Search ${activeTab}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          
          {activeTab === 'roles' && (
            <button
              onClick={() => setShowCreateRole(true)}
              className="ml-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-2 transition-colors"
            >
              <PlusIcon className="w-5 h-5" />
              Create Role
            </button>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        ) : (
          <div>
            {activeTab === 'roles' && <RolesTab roles={filteredRoles} onDelete={deleteRole} onSelect={setSelectedRole} />}
            {activeTab === 'permissions' && <PermissionsTab permissions={filteredPermissions} />}
          </div>
        )}

        {/* Create Role Modal */}
        {showCreateRole && (
          <CreateRoleModal
            onClose={() => setShowCreateRole(false)}
            onCreate={createRole}
          />
        )}

        {/* Role Details Modal */}
        {selectedRole && (
          <RoleDetailsModal
            role={selectedRole}
            onClose={() => setSelectedRole(null)}
            onAssignPermission={assignPermissionToRole}
            onRevokePermission={revokePermissionFromRole}
            allPermissions={permissions}
          />
        )}
      </div>
    </div>
  );
}

function RolesTab({ roles, onDelete, onSelect }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {roles.map((role) => (
        <motion.div
          key={role.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
          onClick={() => onSelect(role)}
        >
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                {role.name}
                {role.is_system_role && (
                  <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                    System
                  </span>
                )}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {role.description}
              </p>
            </div>
            {!role.is_system_role && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(role.id);
                }}
                className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
              >
                <TrashIcon className="w-5 h-5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-1">
              <KeyIcon className="w-4 h-4" />
              <span>{role.permission_count || 0} permissions</span>
            </div>
            <div className="flex items-center gap-1">
              <UserGroupIcon className="w-4 h-4" />
              <span>{role.user_count || 0} users</span>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function PermissionsTab({ permissions }) {
  const groupedByResource = permissions.reduce((acc, perm) => {
    const resource = perm.resource || 'other';
    if (!acc[resource]) acc[resource] = [];
    acc[resource].push(perm);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {Object.entries(groupedByResource).map(([resource, perms]) => (
        <div key={resource} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 capitalize">
            {resource} Permissions
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {perms.map((perm) => (
              <div
                key={perm.id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
              >
                <div className="font-mono text-sm text-indigo-600 dark:text-indigo-400">
                  {perm.name}
                </div>
                {perm.description && (
                  <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {perm.description}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function CreateRoleModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    organization_id: null
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreate(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
      >
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Create New Role
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Role Name
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g., customer_support"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              required
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              rows={3}
              placeholder="Describe this role's purpose and responsibilities..."
            />
          </div>

          <div className="flex gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
            >
              Create Role
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

function RoleDetailsModal({ role, onClose, onAssignPermission, onRevokePermission, allPermissions }) {
  const [rolePermissions, setRolePermissions] = useState([]);
  const [showAddPermission, setShowAddPermission] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPermissions();
  }, [role.id]);

  const loadPermissions = async () => {
    try {
      const { data } = await axios.get(`/api/v1/rbac/roles/${role.id}/permissions`);
      setRolePermissions(data.permissions || []);
    } catch (error) {
      console.error('Failed to load permissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const availablePermissions = allPermissions.filter(
    perm => !rolePermissions.some(rp => rp.name === perm.name)
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {role.name}
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {role.description}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Assigned Permissions ({rolePermissions.length})
            </h3>
            {!role.is_system_role && (
              <button
                onClick={() => setShowAddPermission(!showAddPermission)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-2 transition-colors text-sm"
              >
                <PlusIcon className="w-4 h-4" />
                Add Permission
              </button>
            )}
          </div>

          {showAddPermission && (
            <div className="mb-4 p-4 border border-indigo-200 dark:border-indigo-800 rounded-lg bg-indigo-50 dark:bg-indigo-900/20">
              <h4 className="font-medium text-gray-900 dark:text-white mb-3">
                Available Permissions
              </h4>
              <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                {availablePermissions.map((perm) => (
                  <button
                    key={perm.id}
                    onClick={() => {
                      onAssignPermission(role.id, perm.name);
                      setShowAddPermission(false);
                      loadPermissions();
                    }}
                    className="text-left px-3 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div className="font-mono text-sm text-indigo-600 dark:text-indigo-400">
                      {perm.name}
                    </div>
                    {perm.description && (
                      <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        {perm.description}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {rolePermissions.map((perm) => (
                <div
                  key={perm.id}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 flex justify-between items-start"
                >
                  <div className="flex-1">
                    <div className="font-mono text-sm text-indigo-600 dark:text-indigo-400">
                      {perm.name}
                    </div>
                    {perm.description && (
                      <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        {perm.description}
                      </div>
                    )}
                  </div>
                  {!role.is_system_role && (
                    <button
                      onClick={() => {
                        onRevokePermission(role.id, perm.name);
                        loadPermissions();
                      }}
                      className="ml-2 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
