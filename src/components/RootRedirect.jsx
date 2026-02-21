import React, { useEffect, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { useSystem } from '../contexts/SystemContext';
import MarketplaceLanding from '../pages/public/MarketplaceLanding';
import EmailVerificationNotice from './EmailVerificationNotice';
import LoadingScreen from './LoadingScreen';

/**
 * RootRedirect - Smart router for the root path (/)
 *
 * Logic:
 * 1. Check if user is authenticated (via localStorage authToken or SystemContext)
 * 2. If authenticated → redirect to /admin/dashboard
 * 3. If NOT authenticated → Check landing_page_mode setting from backend
 *    - 'direct_sso' → redirect to /auth/login (Keycloak SSO)
 *    - 'public_marketplace' → show MarketplaceLanding component
 *    - 'custom' → show CustomLandingPage (future feature)
 *
 * Backend API Expected:
 * GET /api/v1/system/settings should return:
 * {
 *   "landing_page_mode": "direct_sso" | "public_marketplace" | "custom",
 *   "branding": {
 *     "company_name": "Unicorn Commander",
 *     "logo_url": "/assets/logo.svg",
 *     "primary_color": "#7c3aed"
 *   }
 * }
 */
export default function RootRedirect() {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [landingMode, setLandingMode] = useState('direct_sso');
  const [searchParams] = useSearchParams();
  const errorParam = searchParams.get('error');

  useEffect(() => {
    const checkAuth = async () => {
      // Check for authToken in localStorage
      const token = localStorage.getItem('authToken');

      if (token) {
        setAuthenticated(true);
        setLoading(false);
        return;
      }

      // Check for OAuth session
      try {
        const response = await fetch('/api/v1/auth/session');
        if (response.ok) {
          const data = await response.json();
          if (data.authenticated) {
            setAuthenticated(true);
            setLoading(false);
            return;
          }
        }
      } catch (error) {
        console.error('Failed to check auth session:', error);
      }

      // User is NOT authenticated - fetch landing page mode
      // Note: System settings endpoint may not exist, default to direct_sso
      try {
        const response = await fetch('/api/v1/system/settings');
        if (response.ok) {
          const data = await response.json();
          setLandingMode(data.landing_page_mode || 'direct_sso');
        } else if (response.status === 404) {
          // Endpoint doesn't exist, use default
          setLandingMode('direct_sso');
        }
      } catch (error) {
        // Network error or endpoint unavailable - use default
        console.debug('Landing page mode unavailable, using default SSO redirect');
        setLandingMode('direct_sso');
      }

      setAuthenticated(false);
      setLoading(false);
    };

    checkAuth();
  }, []);

  // If redirected with email_not_verified error, show verification notice
  // Check BEFORE loading to avoid any race with auth check redirecting to Keycloak
  if (errorParam === 'email_not_verified') {
    return <EmailVerificationNotice />;
  }

  // If user just logged out or auth failed, show the landing page instead of
  // immediately bouncing back to Keycloak SSO
  // Check BEFORE loading to prevent the direct_sso redirect from firing
  const loggedOut = searchParams.get('logged_out');
  if (errorParam === 'authentication_failed' || loggedOut) {
    return <MarketplaceLanding />;
  }

  // Show loading screen while checking auth
  if (loading) {
    return <LoadingScreen />;
  }

  // If authenticated, check for a saved redirect target (e.g. user was sent to login from /admin/chat)
  // Then redirect to user landing page (search bar, apps, user dropdown)
  if (authenticated) {
    const redirectTarget = sessionStorage.getItem('redirect_after_login');
    if (redirectTarget && redirectTarget !== '/' && redirectTarget !== '/dashboard') {
      sessionStorage.removeItem('redirect_after_login');
      return <Navigate to={redirectTarget} replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }

  // User is NOT authenticated - show appropriate landing page
  switch (landingMode) {
    case 'public_marketplace':
      return <MarketplaceLanding />;

    case 'custom':
      // TODO: Implement custom landing page feature
      // For now, fallback to marketplace
      return <MarketplaceLanding />;

    case 'direct_sso':
    default:
      // Use window.location.replace() for immediate redirect without history
      // This prevents React from continuing to render and make API calls
      if (typeof window !== 'undefined') {
        window.location.replace('/auth/login');
      }
      // Return null to stop rendering immediately
      return null;
  }
}
