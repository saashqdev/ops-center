#!/bin/bash
#
# Test User Creation Script - Wrapper
# 
# Creates a test user in Keycloak via Docker container
#
# Usage:
#   ./create_test_user.sh                                    # Create with defaults
#   ./create_test_user.sh testuser@example.com testuser      # Custom email and username
#

set -e

# Keycloak admin password (must match the actual Keycloak server password)
KEYCLOAK_ADMIN_PASSWORD="vz9cA8-kuX-oso3DC-w7"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
EMAIL="${1:-testuser-$(date +%Y%m%d-%H%M%S)@example.com}"
USERNAME="${2:-testuser-$(date +%Y%m%d-%H%M%S)}"
FIRST_NAME="${3:-Test}"
LAST_NAME="${4:-User}"
PASSWORD="${5:-TestPassword123!}"
TIER="${6:-professional}"
ROLE="${7:-}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Creating Test User in Keycloak${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "Email:      ${GREEN}${EMAIL}${NC}"
echo -e "Username:   ${GREEN}${USERNAME}${NC}"
echo -e "Name:       ${GREEN}${FIRST_NAME} ${LAST_NAME}${NC}"
echo -e "Password:   ${GREEN}${PASSWORD}${NC}"
echo -e "Tier:       ${GREEN}${TIER}${NC}"
if [ -n "$ROLE" ]; then
    echo -e "Role:       ${GREEN}${ROLE}${NC}"
fi
echo ""
echo -e "${YELLOW}Running script in Docker container...${NC}"
echo ""

# Build command
CMD="python3 /app/create_test_user.py --email \"${EMAIL}\" --username \"${USERNAME}\" --first-name \"${FIRST_NAME}\" --last-name \"${LAST_NAME}\" --password \"${PASSWORD}\" --tier \"${TIER}\""

if [ -n "$ROLE" ]; then
    CMD="${CMD} --role \"${ROLE}\""
fi

# Execute in Docker container with correct admin password
if docker exec -e KEYCLOAK_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD" ops-center-direct bash -c "$CMD"; then
    echo ""
    echo -e "${GREEN}✅ Success! Test user created.${NC}"
    echo ""
    echo -e "${BLUE}Login credentials:${NC}"
    echo -e "  Email/Username: ${GREEN}${EMAIL}${NC} or ${GREEN}${USERNAME}${NC}"
    echo -e "  Password:       ${GREEN}${PASSWORD}${NC}"
    echo ""
    echo -e "${BLUE}Access user management at:${NC}"
    echo -e "  ${GREEN}https://kubeworkz.io/admin/system/users${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Failed to create test user${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  1. Check Keycloak is running: ${GREEN}docker ps | grep keycloak${NC}"
    echo -e "  2. Verify KEYCLOAK_ADMIN_PASSWORD is set in environment"
    echo -e "  3. Check logs: ${GREEN}docker logs ops-center-direct${NC}"
    echo ""
    exit 1
fi
