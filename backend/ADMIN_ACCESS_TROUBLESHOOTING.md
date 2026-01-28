# Admin Dashboard Access - Troubleshooting Guide

## Issue: Cannot Access /admin Routes - Redirects to /dashboard

### Symptom
User is logged in successfully but when accessing `/admin/*` routes (like `/admin/system/users`), gets redirected back to `/dashboard`.

### Root Cause
The application uses role-based access control (RBAC). System admin routes require the `admin` role in Keycloak.

**Route Protection Rules (from [src/config/routes.js](src/config/routes.js)):**
- **Personal routes** (`/admin/account/*`, `/admin/subscription/*`) - All authenticated users
- **Organization routes** (`/admin/org/*`) - Requires `org_role: admin` or `owner`
- **System routes** (`/admin/system/*`) - Requires `role: admin`

---

## Quick Fix

### 1. Check User's Current Role

```bash
# Get user details
curl -k -X GET "https://auth.kubeworkz.io/admin/realms/uchub/users?email=USER_EMAIL" \
  -H "Authorization: Bearer $(curl -k -s -X POST "https://auth.kubeworkz.io/realms/master/protocol/openid-connect/token" \
    -d "client_id=admin-cli" \
    -d "username=admin" \
    -d "password=vz9cA8-kuX-oso3DC-w7" \
    -d "grant_type=password" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)" | jq '.[0].id'

# Check roles (replace USER_ID with actual ID)
curl -k -X GET "https://auth.kubeworkz.io/admin/realms/uchub/users/USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer TOKEN" | jq .
```

### 2. Assign Admin Role (Option A: Using Script)

```bash
cd /home/ubuntu/Ops-Center-OSS/backend

# Assign admin role by email
./assign_admin_role.sh dave@gridworkz.com

# Or by user ID
./assign_admin_role.sh 81ea800e-7370-4885-a450-0c7839cf9358

# Assign different role
./assign_admin_role.sh dave@gridworkz.com power_user
```

### 3. Assign Admin Role (Option B: Manual)

```bash
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from keycloak_integration import get_user_by_email, assign_realm_role_to_user

async def assign_admin():
    user = await get_user_by_email('dave@gridworkz.com')
    if user:
        await assign_realm_role_to_user(user['id'], 'admin')
        print(f\"✅ Assigned admin role to {user['email']}\")
    else:
        print('❌ User not found')

asyncio.run(assign_admin())
"
```

### 4. User Must Re-Login

**CRITICAL:** After role assignment, the user MUST:
1. Log out completely
2. Log back in
3. New role will be in the session

The session stores the role at login time and doesn't auto-refresh.

---

## Available Roles

### Platform Roles (set in Keycloak realm roles)

| Role | Access Level | Permissions |
|------|--------------|-------------|
| `admin` | System Administrator | Full access to all routes including `/admin/system/*` |
| `power_user` | Power User | Extended access (models, extensions, logs) |
| `user` | Standard User | Basic dashboard and personal account |
| `viewer` | Read-Only | Dashboard view only |

### Organization Roles (set in org membership)

| Role | Access Level |
|------|--------------|
| `owner` | Full org control including billing |
| `admin` | Org administration, team management |
| `member` | Basic org member access |

---

## Common Scenarios

### Scenario 1: New User Needs Admin Access

```bash
# Create user with admin role
cd /home/ubuntu/Ops-Center-OSS/backend
./create_test_user.sh admin@company.com admin "Admin" "User" "SecurePass123!" professional admin

# Or assign admin to existing user
./assign_admin_role.sh existing.user@company.com admin
```

### Scenario 2: User Has Wrong Role

```bash
# Check current role
./assign_admin_role.sh user@example.com

# Will show current roles in output
# Then assign correct role
./assign_admin_role.sh user@example.com admin
```

### Scenario 3: Admin Can't Access Organization Routes

Organization routes require **both**:
- Platform role (any)
- Organization role (`admin` or `owner`)

Check organization membership:
```bash
docker exec ops-center-direct python3 -c "
import sys
sys.path.insert(0, '/app')
from org_manager import OrgManager

org_manager = OrgManager()
orgs = org_manager.get_user_orgs('USER_ID')
for org in orgs:
    print(f'Org: {org.name} (ID: {org.id})')
    role = org_manager.get_user_role_in_org(org.id, 'USER_ID')
    print(f'Role: {role}')
"
```

---

## Debugging Steps

### 1. Check Browser Console

When redirected, check browser console (F12) for:
```
DEBUG Layout: userInfo from localStorage: {role: "user", ...}
DEBUG Layout: userRole: user
```

If `userRole` is not "admin", that's the issue.

### 2. Check Session

```bash
# In browser console
localStorage.getItem('userInfo')
// Should show: {"role":"admin", ...}
```

### 3. Verify Route Protection

Routes are protected in [src/config/routes.js](src/config/routes.js):
```javascript
system: {
  roles: ['admin'],  // Only admin role can access
  children: {
    users: {
      path: '/admin/system/users',
      component: 'UserManagement',
      roles: ['admin']
    }
  }
}
```

### 4. Check Backend Session

```bash
docker logs ops-center-direct 2>&1 | grep "DEBUG: User role from session"
```

Should show:
```
DEBUG: User role from session: admin
```

---

## Session Management

### Force Session Refresh

If role was changed but user already logged in:

**Option 1: Revoke all sessions (forces re-login)**
```bash
curl -X DELETE "https://kubeworkz.io/api/v1/admin/users/USER_ID/sessions" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Option 2: User logout**
- User clicks logout
- Logs back in
- New session will have updated role

### Session Storage

The session stores:
- `role` - Platform role (admin, power_user, user, viewer)
- `org_role` - Organization role (owner, admin, member)
- `username`, `email`, `name`

Session is created during OAuth callback and stored in Redis.

---

## Role Assignment via API

### Using User Management API

```bash
# Get user ID
GET https://kubeworkz.io/api/v1/admin/users?search=dave@gridworkz.com

# Assign realm role
POST https://kubeworkz.io/api/v1/admin/users/{user_id}/roles
{
  "role_name": "admin"
}

# Verify roles
GET https://kubeworkz.io/api/v1/admin/users/{user_id}/roles
```

---

## Keycloak Admin Console

### Manual Role Assignment

1. Access Keycloak: https://auth.kubeworkz.io/admin
2. Login: `admin` / `vz9cA8-kuX-oso3DC-w7`
3. Select realm: `uchub`
4. Go to **Users**
5. Search for user by email
6. Click on user
7. Go to **Role Mappings** tab
8. Under **Realm Roles**, select `admin`
9. Click **Assign**

---

## Files Reference

### Scripts
- `backend/assign_admin_role.sh` - Quick role assignment script
- `backend/create_test_user.sh` - Create user with role
- `backend/quick_create_user.sh` - Interactive user creation

### Code
- `src/config/routes.js` - Route definitions and role requirements
- `src/components/Layout.jsx` - Role-based navigation rendering
- `backend/keycloak_integration.py` - Keycloak role management
- `backend/server.py` - Session endpoint with role mapping

---

## Prevention

### Setting Default Admin User

When creating users that need admin access:

```bash
# Always specify role during creation
./create_test_user.sh \
  admin@company.com \
  admin \
  "Admin" \
  "User" \
  "SecurePass123!" \
  "professional" \
  "admin"  # <-- Admin role

# Or use quick create option 3 (Admin user)
./quick_create_user.sh
# Select: 3
```

### Onboarding Checklist

For new admin users:
- [ ] Create user with admin role
- [ ] Verify role in Keycloak
- [ ] Test login
- [ ] Verify access to `/admin/system/users`
- [ ] Add to organization if needed

---

## Support

If issues persist:
1. Check Keycloak admin console for role assignments
2. Review browser console for role information
3. Check backend logs for session details
4. Verify user logged out and back in after role change
5. Test with a new incognito window to ensure fresh session
