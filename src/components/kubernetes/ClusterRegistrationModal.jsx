import React, { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

/**
 * Epic 16: Kubernetes - Cluster Registration Modal
 * 
 * Modal for registering a new Kubernetes cluster with kubeconfig upload
 */
export default function ClusterRegistrationModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    environment: 'production',
    kubeconfig: '',
    tags: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setFormData({ ...formData, kubeconfig: event.target.result });
      };
      reader.readAsText(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      // Validate kubeconfig
      if (!formData.kubeconfig.trim()) {
        throw new Error('Kubeconfig is required');
      }

      // Parse tags
      const tags = formData.tags
        ? formData.tags.split(',').map(t => t.trim()).filter(Boolean)
        : [];

      const response = await fetch('/api/v1/k8s/clusters', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || null,
          environment: formData.environment,
          kubeconfig: formData.kubeconfig,
          tags: tags.length > 0 ? tags : null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to register cluster');
      }

      onSuccess();
    } catch (err) {
      console.error('Error registering cluster:', err);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Register Kubernetes Cluster
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
                <p className="text-sm text-red-800 dark:text-red-400">{error}</p>
              </div>
            )}

            {/* Cluster Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Cluster Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                placeholder="my-production-cluster"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                placeholder="Production EKS cluster for main workloads"
              />
            </div>

            {/* Environment */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Environment *
              </label>
              <select
                required
                value={formData.environment}
                onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
              >
                <option value="production">Production</option>
                <option value="staging">Staging</option>
                <option value="development">Development</option>
              </select>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={formData.tags}
                onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                placeholder="prod, us-east-1, team-platform"
              />
            </div>

            {/* Kubeconfig Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Kubeconfig File *
              </label>
              <div className="mt-1 flex items-center space-x-4">
                <input
                  type="file"
                  accept=".yaml,.yml,.config"
                  onChange={handleFileUpload}
                  className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900/30 dark:file:text-blue-400"
                />
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Upload your kubeconfig file. This will be encrypted at rest.
              </p>
            </div>

            {/* Kubeconfig Text Area (alternative to file upload) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Or paste kubeconfig content *
              </label>
              <textarea
                required={!formData.kubeconfig}
                value={formData.kubeconfig}
                onChange={(e) => setFormData({ ...formData, kubeconfig: e.target.value })}
                rows={8}
                className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm font-mono text-xs"
                placeholder="apiVersion: v1&#10;kind: Config&#10;clusters:&#10;..."
              />
            </div>

            {/* Security Warning */}
            <div className="rounded-md bg-yellow-50 dark:bg-yellow-900/20 p-4">
              <p className="text-sm text-yellow-800 dark:text-yellow-400">
                <strong>Security Note:</strong> Your kubeconfig will be encrypted using your organization's
                encryption key and stored securely. It will never be exposed in API responses.
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Registering...' : 'Register Cluster'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
