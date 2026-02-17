/**
 * RequireAdmin - Route guard that restricts access to system administrators.
 *
 * Wraps route elements to prevent org-admin users from accessing system-level
 * pages (System, Infrastructure, Monitoring, etc.). Non-admin users are
 * redirected to the org dashboard instead.
 *
 * Usage in App.jsx:
 *   <Route path="system/resources" element={<RequireAdmin><System /></RequireAdmin>} />
 *
 * Created: February 2026 — Phase 3 Isolation
 */

import React from 'react';
import { Navigate } from 'react-router-dom';

export default function RequireAdmin({ children }) {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
  const role = userInfo.role || '';

  const isSystemAdmin = role === 'admin' || role === 'system_admin';

  if (!isSystemAdmin) {
    // Redirect non-system-admins to org dashboard (their home)
    return <Navigate to="/admin/org/dashboard" replace />;
  }

  return children;
}
