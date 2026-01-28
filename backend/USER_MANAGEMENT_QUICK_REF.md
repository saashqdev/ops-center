# User Management Quick Reference

## Quick Commands

### Create Test Users

```bash
# Quick interactive menu (recommended for testing)
cd /home/ubuntu/Ops-Center-OSS/backend
./quick_create_user.sh

# Create specific user
./create_test_user.sh alice@example.com alice Alice Smith MyPassword123!

# Create admin user
./create_test_user.sh admin@test.com admin Admin User SecurePass123! professional admin
```

### API Endpoints

All endpoints require authentication with admin privileges.

```bash
BASE_URL="https://kubeworkz.io/api/v1/admin"
AUTH_HEADER="Authorization: Bearer YOUR_TOKEN"
```

#### Users
```bash
# List users
GET $BASE_URL/users?search=john&tier=professional&limit=50&offset=0

# Get user details
GET $BASE_URL/users/{user_id}

# Create user
POST $BASE_URL/users
{
  "email": "user@example.com",
  "username": "username",
  "firstName": "John",
  "lastName": "Doe",
  "password": "SecurePass123!",
  "attributes": {
    "subscription_tier": "professional"
  }
}

# Update user
PUT $BASE_URL/users/{user_id}
{
  "firstName": "Jane",
  "attributes": {
    "subscription_tier": "enterprise"
  }
}

# Delete user
DELETE $BASE_URL/users/{user_id}
```

#### Roles
```bash
# List all roles
GET $BASE_URL/roles

# Get user's roles
GET $BASE_URL/users/{user_id}/roles

# Assign role
POST $BASE_URL/users/{user_id}/roles
{
  "role_name": "admin"
}

# Remove role
DELETE $BASE_URL/users/{user_id}/roles/{role_name}
```

#### Sessions
```bash
# List user sessions
GET $BASE_URL/users/{user_id}/sessions

# Revoke specific session
DELETE $BASE_URL/users/{user_id}/sessions/{session_id}

# Revoke all sessions (force logout)
DELETE $BASE_URL/users/{user_id}/sessions
```

#### Bulk Operations
```bash
# Bulk delete
POST $BASE_URL/users/bulk/delete
{
  "user_ids": ["id1", "id2", "id3"]
}

# Bulk assign role
POST $BASE_URL/users/bulk/assign-role
{
  "user_ids": ["id1", "id2"],
  "role_name": "moderator"
}

# Bulk set tier
POST $BASE_URL/users/bulk/set-tier
{
  "user_ids": ["id1", "id2"],
  "tier": "professional"
}
```

#### Password Reset
```bash
# Email reset link
POST $BASE_URL/users/{user_id}/reset-password
{
  "mode": "email"
}

# Manual password reset
POST $BASE_URL/users/{user_id}/reset-password
{
  "mode": "manual",
  "new_password": "NewSecurePass123!",
  "temporary": false
}
```

## Subscription Tiers

- `trial` - Trial/Free tier
- `starter` - Starter plan  
- `professional` - Professional plan
- `enterprise` - Enterprise plan

## Common Roles

Check Keycloak for realm-specific roles:
- `admin` - Full admin access
- `user` - Standard user
- `moderator` - Moderation capabilities

## User Attributes

### Standard
- email (required, unique)
- username (required, unique)
- firstName
- lastName
- emailVerified (boolean)
- enabled (boolean)

### Custom
- subscription_tier
- subscription_status
- api_calls_limit
- test_user (flag)

## Organization Membership

Users are NOT automatically assigned to organizations.

### Check user's organizations:
```python
from org_manager import OrgManager
org_manager = OrgManager()
orgs = org_manager.get_user_orgs(user_id)
```

### Add user to organization:
```python
org_manager.add_user_to_org(
    org_id="org_123",
    user_id="user_456",
    role="member"  # owner, member, billing_admin
)
```

## UI Access

- **User Management**: https://kubeworkz.io/admin/system/users
- **Keycloak Admin**: https://auth.kubeworkz.io/admin
  - Username: `admin`
  - Password: `vz9cA8-kuX-oso3DC-w7`
- **API Docs**: https://kubeworkz.io/docs

## Troubleshooting

### 401 Authentication Error
```bash
# Verify Keycloak is running
docker ps | grep keycloak

# Test admin credentials
curl -k -X POST "https://auth.kubeworkz.io/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=vz9cA8-kuX-oso3DC-w7" \
  -d "grant_type=password"
```

### User Already Exists
```bash
# Check existing users
curl -X GET "https://kubeworkz.io/api/v1/admin/users?search=email@example.com"

# Delete if needed
curl -X DELETE "https://kubeworkz.io/api/v1/admin/users/{user_id}"
```

### Script Permissions
```bash
cd /home/ubuntu/Ops-Center-OSS/backend
chmod +x create_test_user.sh quick_create_user.sh
```

## Logs

```bash
# Backend logs
docker logs -f ops-center-direct

# Keycloak logs
docker logs -f keycloak

# Filter user management logs
docker logs ops-center-direct 2>&1 | grep user_management
```

## Configuration Files

- `backend/keycloak_integration.py` - Keycloak API integration
- `backend/user_management_api.py` - REST API endpoints
- `backend/org_manager.py` - Organization management
- `src/pages/UserManagement.jsx` - Frontend UI
- `docker-compose.direct.yml` - Environment config

## Environment Variables

Required in `docker-compose.direct.yml`:
```yaml
- KEYCLOAK_URL=https://auth.kubeworkz.io
- KEYCLOAK_REALM=uchub
- KEYCLOAK_ADMIN_USER=admin
- KEYCLOAK_ADMIN_PASSWORD=vz9cA8-kuX-oso3DC-w7
- KEYCLOAK_CLIENT_ID=ops-center
- KEYCLOAK_CLIENT_SECRET=vz9cA8-kuX-oso3DC-w7
```

## Testing Checklist

- [ ] Create test user via script
- [ ] Verify user in Keycloak admin console
- [ ] Login with test user credentials
- [ ] View user in management UI
- [ ] Assign role to user
- [ ] Update user details
- [ ] Test session revocation
- [ ] Test password reset
- [ ] Delete test user
- [ ] Test bulk operations

## Common Workflows

### New User Onboarding
1. Create user (via API or script)
2. Assign appropriate role
3. Set subscription tier
4. (Optional) Add to organization
5. Send welcome email

### User Offboarding
1. Revoke all sessions
2. Remove from organizations
3. Remove roles
4. Disable or delete account

### Tier Upgrade
1. Update subscription_tier attribute
2. Update api_calls_limit
3. Assign new tier roles if needed
4. Update billing in Lago/Stripe

### Security Response
1. Revoke all sessions
2. Force password reset
3. Review user activity
4. (Optional) Disable account
