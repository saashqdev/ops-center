# User Management Implementation Summary

## Overview
Complete user management system with Keycloak integration, providing full CRUD operations, role management, session management, and bulk operations for the Ops-Center platform.

## Components Implemented

### 1. Backend API (`user_management_api.py`)
Full REST API for user management at `/api/v1/admin/users`

#### User CRUD Operations
- **POST /api/v1/admin/users** - Create new user
  - Email validation
  - Username uniqueness check
  - Password strength validation
  - Custom attributes (subscription tier, status, limits)
  - Automatic email verification
  
- **GET /api/v1/admin/users** - List users with filters
  - Search by email, username, first name, last name
  - Filter by subscription tier
  - Pagination support
  
- **GET /api/v1/admin/users/{user_id}** - Get user details
  - Complete user profile
  - Custom attributes
  - Realm roles
  
- **PUT /api/v1/admin/users/{user_id}** - Update user
  - Partial updates supported
  - Update profile information
  - Change subscription tier
  - Modify custom attributes
  
- **DELETE /api/v1/admin/users/{user_id}** - Delete user
  - Complete removal from Keycloak
  - Audit logging

#### Role Management
- **GET /api/v1/admin/users/{user_id}/roles** - List user's realm roles
- **POST /api/v1/admin/users/{user_id}/roles** - Assign role to user
- **DELETE /api/v1/admin/users/{user_id}/roles/{role_name}** - Remove role from user
- **GET /api/v1/admin/roles** - List all available realm roles

#### Session Management
- **GET /api/v1/admin/users/{user_id}/sessions** - List active sessions
- **DELETE /api/v1/admin/users/{user_id}/sessions/{session_id}** - Revoke specific session
- **DELETE /api/v1/admin/users/{user_id}/sessions** - Revoke all sessions (force logout)

#### Bulk Operations
- **POST /api/v1/admin/users/bulk/delete** - Delete multiple users
- **POST /api/v1/admin/users/bulk/assign-role** - Assign role to multiple users
- **POST /api/v1/admin/users/bulk/set-tier** - Change subscription tier for multiple users

#### Password Management
- **POST /api/v1/admin/users/{user_id}/reset-password** - Reset user password
  - Email mode: Sends Keycloak password reset email
  - Manual mode: Admin sets new password directly

### 2. Keycloak Integration (`keycloak_integration.py`)
Enhanced with comprehensive admin operations

#### New Functions Added
- `delete_user_by_id(user_id)` - Delete user
- `update_user_by_id(user_id, updates)` - Update user profile
- `get_realm_roles()` - List all realm roles
- `get_user_realm_roles(user_id)` - Get user's roles
- `assign_realm_role_to_user(user_id, role_name)` - Assign role
- `remove_realm_role_from_user(user_id, role_name)` - Remove role
- `get_user_sessions(user_id)` - List user sessions
- `logout_user_session(user_id, session_id)` - Revoke specific session
- `logout_all_user_sessions(user_id)` - Revoke all sessions

#### Authentication Fix
- Fixed admin authentication to use `admin-cli` client for Keycloak admin operations
- Corrected password configuration: `vz9cA8-kuX-oso3DC-w7`
- Updated `docker-compose.direct.yml` to use correct admin password

### 3. Frontend Integration (`src/pages/UserManagement.jsx`)
- Updated error handling for new API response format
- Handles `error.detail` and `error.message` from FastAPI
- Existing role and session management handlers already compatible

### 4. Test User Creation Scripts

#### `create_test_user.py` - Python CLI Script
- Comprehensive user creation with all options
- Features:
  - Custom email, username, first name, last name
  - Password setting (non-temporary)
  - Subscription tier assignment
  - Role assignment
  - Email verification control
  - Custom attributes (subscription_tier, subscription_status, api_calls_limit)
  - Test user flag for easy identification
  - Progress output with success/failure indicators

#### `create_test_user.sh` - Bash Wrapper
- Simple wrapper for easier invocation
- Auto-injects correct Keycloak admin password
- Colored output with clear success/failure messages
- Positional arguments for quick testing

#### `quick_create_user.sh` - Interactive Menu
- 5 preset scenarios:
  1. Basic trial user
  2. Professional user
  3. Admin user (professional + admin role)
  4. Bulk create 5 users
  5. Custom user (manual input)
- Auto-generates unique timestamps for emails/usernames
- Perfect for quick testing and demos

## Configuration

### Environment Variables
Required for all operations:
```bash
KEYCLOAK_URL=https://auth.kubeworkz.io
KEYCLOAK_REALM=uchub
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=vz9cA8-kuX-oso3DC-w7
KEYCLOAK_CLIENT_ID=ops-center
KEYCLOAK_CLIENT_SECRET=vz9cA8-kuX-oso3DC-w7
```

### Keycloak Client Configuration
- **Admin Operations**: Uses `admin-cli` client in master realm
- **User Operations**: Uses `ops-center` client in uchub realm
- **Authentication**: Password grant type for admin token

## Organization Membership

Users created through the system are **not automatically assigned to organizations**.

### Multi-Tenant Architecture
- Users can exist without organization membership
- System returns `null` for `org_id`, `org_name`, `org_role` when no org assigned
- All features work for users without organizations
- Organization assignment is optional

### Adding Users to Organizations
If needed, users can be added to organizations via:
1. **API**: Using organization management endpoints
2. **Code**: `org_manager.add_user_to_org(org_id, user_id, role)`
3. **UI**: Through admin interface

### Organization Management Files
- `org_manager.py` - Organization CRUD and membership
- `org_api.py` - Organization REST API
- Database table: `organization_members` (org_id, user_id, role)

## User Attributes

### Standard Attributes
- email
- username  
- firstName
- lastName
- emailVerified
- enabled

### Custom Attributes
- subscription_tier: trial, starter, professional, enterprise
- subscription_status: active, cancelled, expired
- api_calls_limit: Monthly API call limit (tier-based)
- test_user: Flag for test users (true/false)

## Security Features

### Authentication & Authorization
- Admin token caching with automatic refresh
- Role-based access control (RBAC)
- Session validation
- Audit logging for all operations

### Password Management
- Keycloak password policies enforced
- Non-temporary passwords by default
- Email-based reset via Keycloak
- Manual admin reset capability

### Data Validation
- Email format validation
- Username uniqueness checks
- Required field validation
- Type validation for all inputs

## Usage Examples

### Creating a User
```bash
# Via wrapper script
cd /home/ubuntu/Ops-Center-OSS/backend
./create_test_user.sh alice@example.com alice Alice Smith

# Via Python script
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" \
  ops-center-direct python3 /app/create_test_user.py \
  --email bob@example.com \
  --username bob \
  --tier professional \
  --role admin
```

### Via API
```bash
# Create user
curl -X POST https://kubeworkz.io/api/v1/admin/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "newuser",
    "firstName": "John",
    "lastName": "Doe",
    "password": "SecurePass123!",
    "attributes": {
      "subscription_tier": "professional"
    }
  }'

# Assign role
curl -X POST https://kubeworkz.io/api/v1/admin/users/{user_id}/roles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_name": "admin"}'

# Revoke all sessions
curl -X DELETE https://kubeworkz.io/api/v1/admin/users/{user_id}/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Testing

### Test User Creation
```bash
# Quick test user
./quick_create_user.sh
# Select option 1 for trial user

# Multiple test users
./quick_create_user.sh
# Select option 4 for 5 users

# Verify users created
curl -X GET https://kubeworkz.io/api/v1/admin/users?search=trial
```

### Test User Management UI
1. Navigate to `https://kubeworkz.io/admin/system/users`
2. Create test user via UI
3. Edit user details
4. Assign roles
5. View/revoke sessions
6. Delete user

## Audit Logging

All operations are logged with:
- Operation type (create, update, delete, etc.)
- User ID performing the operation
- Target user ID
- Timestamp
- Success/failure status
- Error details if failed

Logs are available in Docker container logs:
```bash
docker logs ops-center-direct | grep "user_management"
```

## API Documentation

Full API documentation available at:
- Swagger UI: `https://kubeworkz.io/docs`
- ReDoc: `https://kubeworkz.io/redoc`

## Files Modified/Created

### New Files
- `backend/user_management_api.py` - User management REST API
- `backend/create_test_user.py` - Python test user creation script
- `backend/create_test_user.sh` - Bash wrapper script
- `backend/quick_create_user.sh` - Interactive menu script
- `backend/TEST_USER_CREATION.md` - Script documentation
- `backend/USER_MANAGEMENT_SUMMARY.md` - This file

### Modified Files
- `backend/keycloak_integration.py` - Enhanced with admin operations
- `backend/server.py` - Includes user_management_api routes
- `src/pages/UserManagement.jsx` - Updated error handling
- `docker-compose.direct.yml` - Fixed KEYCLOAK_ADMIN_PASSWORD

## Next Steps (Optional Enhancements)

### Organization Integration
- Extend test scripts to optionally create/assign organizations
- Add org_id parameter to user creation
- Auto-create default organization for new users

### Email Notifications
- Welcome emails for new users
- Password reset confirmations
- Role assignment notifications

### User Import/Export
- Bulk import from CSV
- Export user data
- Backup/restore functionality

### Advanced Features
- User groups management
- Custom attributes editor
- User activity tracking
- Login history

## Troubleshooting

### Authentication Issues
If getting 401 errors:
1. Verify Keycloak is running: `docker ps | grep keycloak`
2. Check admin password in docker-compose.direct.yml
3. Use wrapper scripts which include correct password
4. Test Keycloak directly: `curl -k https://auth.kubeworkz.io/realms/uchub`

### User Creation Failures
1. Check unique constraints (email, username)
2. Verify password strength requirements
3. Ensure tier is valid value
4. Check Keycloak admin console for errors

### Script Execution Issues
1. Ensure execute permissions: `chmod +x *.sh`
2. Run from correct directory: `/home/ubuntu/Ops-Center-OSS/backend`
3. Verify Docker container is running: `docker ps | grep ops-center-direct`

## Support

For issues or questions:
1. Check documentation: `TEST_USER_CREATION.md`
2. Review API docs: `https://kubeworkz.io/docs`
3. Check logs: `docker logs ops-center-direct`
4. Inspect Keycloak: `https://auth.kubeworkz.io/admin`
