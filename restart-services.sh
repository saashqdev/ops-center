#!/bin/bash
#
# Ops-Center Service Restart Script
# Restarts all critical services in the correct order
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Ops-Center Service Restart${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ] && ! groups | grep -q docker; then
    echo -e "${YELLOW}Warning: You may need sudo or docker group membership${NC}"
fi

# Function to check container health
check_container() {
    local container_name=$1
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo -e "${GREEN}✓${NC} $container_name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $container_name is not running"
        return 1
    fi
}

# 1. Start PostgreSQL
echo -e "${BLUE}1. Starting PostgreSQL...${NC}"
if docker ps -a --format '{{.Names}}' | grep -q "ops-center-postgresql\|9d909efb7e23_ops-center-postgresql"; then
    POSTGRES_CONTAINER=$(docker ps -a --format '{{.Names}}' | grep "ops-center-postgresql" | head -1)
    docker start $POSTGRES_CONTAINER 2>/dev/null || echo "Already running"
    sleep 2
    check_container "$POSTGRES_CONTAINER" || echo -e "${YELLOW}  PostgreSQL may need attention${NC}"
else
    echo -e "${YELLOW}  No PostgreSQL container found - may need docker-compose up${NC}"
fi

# 2. Start Redis
echo ""
echo -e "${BLUE}2. Starting Redis...${NC}"
if docker ps --format '{{.Names}}' | grep -q "^unicorn-lago-redis$"; then
    echo -e "${GREEN}✓${NC} Redis already running"
elif docker ps -a --format '{{.Names}}' | grep -q "^unicorn-lago-redis$"; then
    docker start unicorn-lago-redis
    sleep 2
    check_container "unicorn-lago-redis"
else
    echo -e "${YELLOW}  Creating new Redis container...${NC}"
    docker run -d \
        --name unicorn-lago-redis \
        --network ops-center-oss_unicorn-network \
        -p 6379:6379 \
        --health-cmd="redis-cli ping" \
        --health-interval=10s \
        redis:7-alpine
    sleep 2
    check_container "unicorn-lago-redis"
fi

# 3. Start Backend
echo ""
echo -e "${BLUE}3. Starting Backend (ops-center-direct)...${NC}"
if docker ps --format '{{.Names}}' | grep -q "^ops-center-direct$"; then
    echo -e "${YELLOW}  Backend is running but may be unhealthy, restarting...${NC}"
    docker restart ops-center-direct
else
    docker start ops-center-direct 2>/dev/null || echo -e "${YELLOW}  Container may need to be recreated${NC}"
fi

echo -e "${YELLOW}  Waiting for backend to start...${NC}"
sleep 8

# 4. Check backend health
echo ""
echo -e "${BLUE}4. Checking service health...${NC}"
check_container "ops-center-direct"

# Test backend responsiveness
if curl -s http://localhost:8084/ -o /dev/null -w "%{http_code}" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} Backend is responding (HTTP 200)"
else
    echo -e "${RED}✗${NC} Backend may not be healthy"
    echo -e "${YELLOW}  Check logs: docker logs --tail 50 ops-center-direct${NC}"
fi

# 5. Test external access
echo ""
echo -e "${BLUE}5. Testing external access...${NC}"
if curl -k -s https://kubeworkz.io/ -o /dev/null -w "%{http_code}" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} Site is accessible at https://kubeworkz.io"
else
    echo -e "${YELLOW}  Site may not be accessible externally${NC}"
    echo -e "${YELLOW}  Check Traefik/proxy logs${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Status Summary${NC}"
echo -e "${BLUE}========================================${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|redis|postgres|ops-center"

echo ""
echo -e "${GREEN}✓ Service restart complete!${NC}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  Check backend logs:  ${GREEN}docker logs -f ops-center-direct${NC}"
echo -e "  Check all services:  ${GREEN}docker ps${NC}"
echo -e "  Restart this script: ${GREEN}./restart-services.sh${NC}"
echo ""
