# Test User Creation Scripts

Three scripts are provided for creating test users in Keycloak:

## Scripts

### 1. `create_test_user.py` - Python Script (Direct)
Full-featured Python script with extensive options.

**Usage:**
```bash
# Inside Docker container with correct admin password
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 /app/create_test_user.py [OPTIONS]
```

**Options:**
```
--email EMAIL              User email address (default: auto-generated)
--username USERNAME        Username (default: auto-generated)
--first-name FIRST_NAME    First name (default: Test)
--last-name LAST_NAME      Last name (default: User)
--password PASSWORD        User password (default: TestPassword123!)
--tier TIER                Subscription tier: trial, starter, professional, enterprise
--role ROLE                Realm role to assign (e.g., admin, user, moderator)
--email-verified           Mark email as verified (default)
--email-not-verified       Mark email as NOT verified
```

**Examples:**
```bash
# Create basic test user with defaults
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 /app/create_test_user.py

# Create user with custom email and username
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 /app/create_test_user.py \
  --email john@example.com --username johndoe

# Create admin user with professional tier
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 /app/create_test_user.py \
  --email admin@test.com --username admin --role admin --tier professional

# Create user with custom name and password
docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 /app/create_test_user.py \
  --first-name "John" --last-name "Doe" --password "SecurePass123!"
```

### 2. `create_test_user.sh` - Bash Wrapper (Simple)
Simplified wrapper script for quick testing. This script includes the correct admin password automatically.

**Usage:**
```bash
cd /home/ubuntu/Ops-Center-OSS/backend

# Create with auto-generated email/username
./create_test_user.sh

# Create with custom values
./create_test_user.sh EMAIL USERNAME [FIRST_NAME] [LAST_NAME] [PASSWORD] [TIER] [ROLE]
```

**Examples:**
```bash
# Create with auto-generated values
./create_test_user.sh

# Custom email and username
./create_test_user.sh jane@example.com jane

# Full customization
./create_test_user.sh \
  admin@test.com \
  admin \
  "Admin" \
  "User" \
  "SecurePass123!" \
  "professional" \
  "admin"
```

### 3. `quick_create_user.sh` - Interactive Menu
Interactive menu for common scenarios.

**Usage:**
```bash
cd /home/ubuntu/Ops-Center-OSS/backend
./quick_create_user.sh
```

**Scenarios:**
1. Basic trial user (default tier)
2. Professional user
3. Admin user (professional tier with admin role)
4. Create 5 test users at once
5. Custom user (manual input for all fields)

## Organization Membership

**Important:** Users created with these scripts are NOT automatically assigned to an organization. 

In this multi-tenant system:
- Users can exist without organization membership
- System returns `org_id: null`, `org_name: null`, `org_role: null` for users without orgs
- All features work for users without organizations
- You can add users to organizations later via:
  - The organization management API
  - Using `org_manager.add_user_to_org(org_id, user_id, role)`
  - Through the admin UI

If you need to create users with organization membership, you can extend the scripts to call `org_manager.add_user_to_org()` after user creation.

## Subscription Tiers

- `trial` - Trial tier (default)
- `starter` - Starter tier
- `professional` - Professional tier
- `enterprise` - Enterprise tier

## Common Realm Roles

Check your Keycloak realm for available roles. Common roles include:
- `admin` - Full system access
- `user` - Standard user access
- `moderator` - Moderation capabilities
- `developer` - Developer access

## Prerequisites

1. **Keycloak must be running:**
   ```bash
   docker ps | grep keycloak
   ```

2. **Backend container must be running:**
   ```bash
   docker ps | grep ops-center-direct
   ```

3. **Environment variables must be set:**
   - `KEYCLOAK_URL`
   - `KEYCLOAK_REALM`
   - `KEYCLOAK_ADMIN_USER`
   - `KEYCLOAK_ADMIN_PASSWORD`

## Troubleshooting

### "Failed to authenticate with Keycloak: 401"

**Cause:** Keycloak admin credentials are not configured correctly.

**Solution:**
1. The correct admin password is `vz9cA8-kuX-oso3DC-w7` (configured in docker-compose.direct.yml)

2. If using `create_test_user.py` directly, pass the password as environment variable:
   ```bash
   docker exec -e KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7" ops-center-direct python3 /app/create_test_user.py
   ```

3. If using the wrapper scripts (`create_test_user.sh` or `quick_create_user.sh`), the password is already included.

4. Verify Keycloak is accessible:
   ```bash
   curl -k https://auth.kubeworkz.io/realms/uchub
   ```

### "User already exists"

**Solution:** 
Use a different email/username or delete the existing user first via:
- Web UI: `https://kubeworkz.io/admin/system/users`
- API: `DELETE /api/v1/admin/users/{user_id}`
- Keycloak Admin Console: `https://auth.kubeworkz.io/admin`

### Script not found

**Solution:**
Ensure you're in the correct directory:
```bash
cd /home/ubuntu/Ops-Center-OSS/backend
ls -la create_test_user.*
```

## Output Example

```
============================================================
Creating Test User in Keycloak
============================================================
Keycloak URL: https://auth.kubeworkz.io
Realm: uchub
============================================================

1. Checking if user already exists...
   ✓ User does not exist, proceeding with creation

2. Creating user in Keycloak...
   Email: testuser@example.com
   Username: testuser
   Name: Test User
   Tier: professional
   Email Verified: True
   ✓ User created successfully!
   User ID: 12345678-1234-1234-1234-123456789abc

3. Setting user password...
   ✓ Password set successfully

============================================================
✅ Test User Created Successfully!
============================================================
User ID:       12345678-1234-1234-1234-123456789abc
Email:         testuser@example.com
Username:      testuser
Password:      TestPassword123!
Tier:          professional
Role:          None
Email Verified: True
============================================================

You can now login with:
  Email/Username: testuser@example.com or testuser
  Password: TestPassword123!

Access user management at:
  https://kubeworkz.io/admin/system/users
============================================================
```

## Integration with User Management

Once created, test users can be managed via:

1. **Web UI:** `https://kubeworkz.io/admin/system/users`
   - View user details
   - Update user information
   - Manage roles
   - View sessions
   - Reset password
   - Delete user

2. **API Endpoints:**
   - `GET /api/v1/admin/users` - List users
   - `GET /api/v1/admin/users/{user_id}` - Get user details
   - `PUT /api/v1/admin/users/{user_id}` - Update user
   - `DELETE /api/v1/admin/users/{user_id}` - Delete user
   - `POST /api/v1/admin/users/{user_id}/roles/assign` - Assign role
   - `GET /api/v1/admin/users/{user_id}/sessions` - View sessions

## Security Notes

- **Default Password:** The default password is `TestPassword123!` - change this for production testing
- **Test Users:** Mark test users with the `test_user` attribute for easy identification
- **Cleanup:** Remember to delete test users after testing
- **Production:** Never use these scripts to create production users - use the web UI or proper onboarding flow
