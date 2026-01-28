# Logout Redirect Loop - Fixed

## Issue
When logging out as dave@gridworkz.com (or any user), the browser would cycle/loop on https://kubeworkz.io instead of completing the logout flow.

## Root Cause

The logout flow had multiple issues causing a redirect loop:

1. **Frontend logout handlers** were redirecting to `/` after logout
2. **Root redirect** (`/`) checks authentication
3. If **Keycloak session still active**, root redirect sends user back to `/dashboard`
4. This creates an infinite loop: logout → `/` → check auth → still authenticated → `/dashboard` → logout → repeat

## Fix Applied

### 1. Backend - Updated Logout Redirect URL
**File:** `backend/server.py`

Changed the default post-logout redirect from `/auth/callback` to `/auth/logged-out`:

```python
logout_confirmation_url = os.getenv(
    "KEYCLOAK_LOGOUT_REDIRECT",
    f"{external_protocol}://{external_host}/auth/logged-out"  # Changed from /auth/callback
)
```

### 2. Frontend - Use Keycloak Logout URL
**Files:** 
- `src/components/Layout.jsx`
- `src/components/MobileNavigation.jsx`
- `src/pages/PublicLanding.jsx`

Updated all logout handlers to:
1. Call `/api/v1/auth/logout` API
2. Use the returned `logout_url` to redirect to Keycloak
3. Fallback to `/auth/logged-out` (not `/`)

```javascript
const handleLogout = async () => {
  const response = await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'include'
  });

  if (response.ok) {
    const data = await response.json();
    
    // Clear local storage
    localStorage.removeItem('authToken');
    localStorage.removeItem('userInfo');
    localStorage.removeItem('user');
    localStorage.removeItem('token');

    // Redirect to Keycloak logout URL
    if (data.logout_url) {
      window.location.href = data.logout_url;
      return;
    }
  }

  // Fallback: redirect to logout confirmation page
  window.location.href = '/auth/logged-out';
};
```

### 3. Logout Confirmation Page
**File:** `backend/server.py` - `/auth/logged-out` endpoint

Updated to redirect to `/auth/login` (not `/`):

```javascript
setTimeout(() => {
    window.location.href = '/auth/login';  // Changed from '/'
}, 2000);
```

This prevents the loop because `/auth/login` initiates OAuth flow instead of checking existing auth.

## Logout Flow (Fixed)

```
User clicks logout
    ↓
Frontend calls /api/v1/auth/logout
    ↓
Backend:
  - Deletes session from Redis
  - Returns Keycloak logout URL with id_token_hint
    ↓
Frontend redirects to Keycloak logout URL
    ↓
Keycloak:
  - Terminates SSO session
  - Redirects to: https://kubeworkz.io/auth/logged-out
    ↓
/auth/logged-out page:
  - Shows "Logged out successfully" message
  - Waits 2 seconds
  - Redirects to /auth/login
    ↓
User sees login page (clean logout complete)
```

## Environment Configuration

**File:** `docker-compose.direct.yml`

```yaml
- KEYCLOAK_LOGOUT_REDIRECT=https://${APP_DOMAIN:-kubeworkz.io}/auth/logged-out
```

This ensures the backend uses the correct logout redirect URL.

## Testing

### Test Logout Flow

1. Login as any user (e.g., dave@gridworkz.com)
2. Click logout from:
   - Mobile navigation menu
   - Desktop user dropdown
   - Any logout button
3. Should see:
   - Brief Keycloak redirect
   - "Logged out successfully" confirmation page
   - Auto-redirect to login page after 2 seconds

### Verify No Loop

- User should **not** see cycling between pages
- User should **not** end up back on dashboard
- Session should be completely cleared from:
  - Browser localStorage
  - Backend Redis
  - Keycloak SSO session

## Files Modified

1. `backend/server.py`
   - Changed default logout redirect to `/auth/logged-out`
   - Fixed logout confirmation page redirect

2. `src/components/Layout.jsx`
   - Use Keycloak logout URL from API response
   - Fallback to `/auth/logged-out` instead of `/`

3. `src/components/MobileNavigation.jsx`
   - Use Keycloak logout URL from API response
   - Fallback to `/auth/logged-out` instead of `/`

4. `src/pages/PublicLanding.jsx`
   - Use Keycloak logout URL from API response
   - Fallback to `/auth/logged-out` instead of `/`

## Related Configuration

### Keycloak Client Settings

The `ops-center` client in Keycloak realm `uchub` has these redirect URIs configured:
- `https://kubeworkz.io/*` (allows all paths including `/auth/logged-out`)
- `http://localhost:*` (for local development)

### Session Management

Sessions are stored in Redis with the key pattern:
- `session_token` cookie → Redis session data
- Contains: `user`, `id_token`, `access_token`, etc.

On logout:
1. Redis session is deleted
2. Cookie is cleared
3. Keycloak session is terminated

## Troubleshooting

### Still seeing redirect loop?

1. **Clear browser cache and cookies**
   ```
   - Press Ctrl+Shift+Delete
   - Clear all cookies for kubeworkz.io
   - Clear cached files
   ```

2. **Check backend logs**
   ```bash
   docker logs -f ops-center-direct | grep logout
   ```

3. **Verify logout URL**
   Look for in logs:
   ```
   Logout URL: https://auth.kubeworkz.io/realms/uchub/protocol/openid-connect/logout?id_token_hint=...&post_logout_redirect_uri=https://kubeworkz.io/auth/logged-out
   ```

4. **Test in incognito window**
   - Open incognito/private browsing
   - Login
   - Logout
   - Should work without cached session issues

### Logout returns error?

Check that:
- Backend service is running: `docker ps | grep ops-center-direct`
- Redis is accessible
- Keycloak is reachable from backend
- Environment variables are set correctly

## Prevention

For future logout implementations:

1. ✅ Always use the API-provided logout URL
2. ✅ Never redirect to `/` after logout (creates auth check loop)
3. ✅ Use dedicated logout confirmation page
4. ✅ Clear all session data (localStorage, cookies, Redis, Keycloak)
5. ✅ Test logout in fresh browser session
