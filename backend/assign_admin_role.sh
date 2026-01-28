#!/bin/bash
#
# Assign Admin Role to User
#
# Usage: ./assign_admin_role.sh EMAIL_OR_USER_ID [ROLE_NAME]
#
# Examples:
#   ./assign_admin_role.sh dave@example.com
#   ./assign_admin_role.sh dave@example.com admin
#   ./assign_admin_role.sh 81ea800e-7370-4885-a450-0c7839cf9358 power_user
#

set -e

# Keycloak admin password
KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

USER_INPUT="${1}"
ROLE_NAME="${2:-admin}"

if [ -z "$USER_INPUT" ]; then
    echo -e "${RED}Error: Please provide email or user ID${NC}"
    echo "Usage: $0 EMAIL_OR_USER_ID [ROLE_NAME]"
    echo "Example: $0 dave@example.com admin"
    exit 1
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Assigning Role to User${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if input is UUID (user_id) or email
if [[ "$USER_INPUT" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    USER_ID="$USER_INPUT"
    echo -e "User ID:    ${GREEN}${USER_ID}${NC}"
else
    EMAIL="$USER_INPUT"
    echo -e "Email:      ${GREEN}${EMAIL}${NC}"
    echo -e "${YELLOW}Looking up user ID...${NC}"
    
    # Get user ID from email
    USER_ID=$(docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from keycloak_integration import get_user_by_email

async def get_user():
    try:
        user = await get_user_by_email('$EMAIL')
        if user:
            print(user['id'])
        else:
            sys.exit(1)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(get_user())
" 2>&1)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ User not found: $EMAIL${NC}"
        exit 1
    fi
    
    echo -e "User ID:    ${GREEN}${USER_ID}${NC}"
fi

echo -e "Role:       ${GREEN}${ROLE_NAME}${NC}"
echo ""
echo -e "${YELLOW}Assigning role...${NC}"

# Assign the role
docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from keycloak_integration import assign_realm_role_to_user

async def assign_role():
    try:
        result = await assign_realm_role_to_user('$USER_ID', '$ROLE_NAME')
        if result:
            print('✅ Success')
        else:
            print('❌ Failed', file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f'❌ Error: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(assign_role())
"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Successfully assigned '${ROLE_NAME}' role!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "  1. User must ${YELLOW}log out${NC} and ${YELLOW}log back in${NC} for role to take effect"
    echo -e "  2. User can then access role-protected routes"
    echo ""
    echo -e "${BLUE}Available roles:${NC}"
    echo -e "  - ${GREEN}admin${NC}       - Full system administration"
    echo -e "  - ${GREEN}power_user${NC}  - Extended user privileges"
    echo -e "  - ${GREEN}user${NC}        - Standard user access"
    echo -e "  - ${GREEN}viewer${NC}      - Read-only access"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Failed to assign role${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  - Check that the role exists in Keycloak"
    echo -e "  - Verify Keycloak is running"
    echo -e "  - Check logs: ${GREEN}docker logs ops-center-direct${NC}"
    exit 1
fi
