#!/bin/bash
#
# Unicorn Brigade Installation Script
# Installs and configures the Brigade multi-agent AI platform
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
cat << "EOF"
  _   _       _                       ____       _                 _      
 | | | |_ __ (_) ___ ___  _ __ _ __  | __ ) _ __(_) __ _  __ _  __| | ___ 
 | | | | '_ \| |/ __/ _ \| '__| '_ \ |  _ \| '__| |/ _` |/ _` |/ _` |/ _ \
 | |_| | | | | | (_| (_) | |  | | | || |_) | |  | | (_| | (_| | (_| |  __/
  \___/|_| |_|_|\___\___/|_|  |_| |_||____/|_|  |_|\__, |\__,_|\__,_|\___|
                                                    |___/                  
  Multi-Agent AI Platform Installation
EOF
echo -e "${NC}"

# Check if running from the correct directory
if [ ! -f "docker-compose.brigade.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.brigade.yml not found${NC}"
    echo "Please run this script from the Ops-Center-OSS directory"
    exit 1
fi

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is required but not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✅ Docker found${NC}"

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is required but not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose found${NC}"

# Check if networks exist
echo -e "\n${BLUE}🌐 Checking Docker networks...${NC}"
for network in web unicorn-network uchub-network; do
    if ! docker network inspect $network &> /dev/null; then
        echo -e "${YELLOW}⚠️  Network '$network' not found, creating...${NC}"
        docker network create $network
        echo -e "${GREEN}✅ Created network: $network${NC}"
    else
        echo -e "${GREEN}✅ Network exists: $network${NC}"
    fi
done

# Create environment file if it doesn't exist
if [ ! -f .env.brigade ]; then
    echo -e "\n${YELLOW}📝 Creating .env.brigade from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env.brigade
    fi
    echo -e "${YELLOW}⚠️  Please edit .env.brigade and configure:${NC}"
    echo "   - API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)"
    echo "   - EXTERNAL_HOST (your domain)"
    echo "   - BRIGADE_SECRET_KEY (random string)"
    echo ""
    read -p "Press Enter to continue after configuring .env.brigade, or Ctrl+C to exit..."
fi

# Check if PostgreSQL container is running
echo -e "\n${BLUE}🗄️  Checking PostgreSQL...${NC}"
if ! docker ps | grep -q "ops-center-postgresql"; then
    echo -e "${YELLOW}⚠️  PostgreSQL container not running${NC}"
    echo "Brigade requires PostgreSQL. Please start it first:"
    echo "  docker compose -f docker-compose.direct.yml up -d postgresql"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is running${NC}"

# Check if Redis container is running
echo -e "\n${BLUE}📦 Checking Redis...${NC}"
if ! docker ps | grep -q "unicorn-lago-redis"; then
    echo -e "${YELLOW}⚠️  Redis container not running${NC}"
    echo "Brigade requires Redis. Please start it first:"
    echo "  docker compose -f docker-compose.direct.yml up -d unicorn-lago-redis"
    exit 1
fi
echo -e "${GREEN}✅ Redis is running${NC}"

# Initialize Brigade database
echo -e "\n${BLUE}🗄️  Initializing Brigade database...${NC}"
if docker exec ops-center-postgresql psql -U unicorn -d postgres -lqt | cut -d \| -f 1 | grep -qw brigade; then
    echo -e "${YELLOW}⚠️  Database 'brigade' already exists${NC}"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker exec ops-center-postgresql psql -U unicorn -d postgres -c "DROP DATABASE IF EXISTS brigade;"
        docker exec ops-center-postgresql psql -U unicorn -d postgres -c "CREATE DATABASE brigade;"
        echo -e "${GREEN}✅ Database recreated${NC}"
    fi
else
    docker exec ops-center-postgresql psql -U unicorn -d postgres -c "CREATE DATABASE brigade;"
    echo -e "${GREEN}✅ Database created${NC}"
fi

# Check for Brigade Docker image
echo -e "\n${BLUE}📦 Checking Brigade image...${NC}"
if docker images | grep -q "brigade-ai"; then
    echo -e "${GREEN}✅ Brigade image found${NC}"
else
    echo -e "${YELLOW}⚠️  Brigade image not found${NC}"
    echo "You have two options:"
    echo "  1. Build from source (if you have the Brigade repository)"
    echo "  2. Pull from a registry (if available)"
    echo ""
    read -p "Do you want to build from source? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d "./brigade" ]; then
            echo -e "${BLUE}🔨 Building Brigade image...${NC}"
            docker compose -f docker-compose.brigade.yml build
        else
            echo -e "${RED}❌ Brigade source directory not found at ./brigade${NC}"
            echo "Please either:"
            echo "  1. Clone the Brigade repository to ./brigade"
            echo "  2. Provide the Brigade image manually"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  Please provide the Brigade image manually${NC}"
        echo "You can either:"
        echo "  - docker pull <brigade-image>"
        echo "  - docker tag <your-image> brigade-ai:latest"
        exit 1
    fi
fi

# Start Brigade service
echo -e "\n${BLUE}🚀 Starting Unicorn Brigade...${NC}"
docker compose -f docker-compose.brigade.yml --env-file .env.brigade up -d

# Wait for service to be ready
echo -e "\n${BLUE}⏳ Waiting for Brigade to start...${NC}"
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -f http://localhost:8112/health &> /dev/null; then
        echo -e "${GREEN}✅ Brigade API is responding${NC}"
        break
    fi
    echo -n "."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done
echo ""

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}⚠️  Brigade API not responding after ${MAX_WAIT}s${NC}"
    echo "Check logs: docker logs unicorn-brigade"
else
    # Verify installation
    echo -e "\n${BLUE}✅ Verifying installation...${NC}"
    
    # Check API health
    if curl -f http://localhost:8112/health &> /dev/null; then
        echo -e "${GREEN}✅ Brigade API: http://localhost:8112${NC}"
    else
        echo -e "${RED}❌ Brigade API not responding${NC}"
    fi
    
    # Check UI
    if curl -f http://localhost:8102 &> /dev/null; then
        echo -e "${GREEN}✅ Brigade UI: http://localhost:8102${NC}"
    else
        echo -e "${YELLOW}⚠️  Brigade UI not responding (may still be starting)${NC}"
    fi
    
    # Check container status
    if docker ps | grep -q unicorn-brigade; then
        echo -e "${GREEN}✅ Brigade container is running${NC}"
    else
        echo -e "${RED}❌ Brigade container is not running${NC}"
    fi
fi

# Display access information
echo -e "\n${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Brigade Installation Complete!${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo -e "  ${GREEN}•${NC} Brigade API:        http://localhost:8112"
echo -e "  ${GREEN}•${NC} Brigade Web UI:     http://localhost:8102"
echo -e "  ${GREEN}•${NC} Ops-Center Menu:    http://localhost:8084/admin/brigade"
echo ""
echo -e "${BLUE}External URL:${NC}"
echo "  • https://brigade.your-domain.com (configure DNS & update .env.brigade)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Configure API keys in .env.brigade"
echo "  2. Set up DNS for brigade.your-domain.com"
echo "  3. Restart Brigade: docker compose -f docker-compose.brigade.yml restart"
echo "  4. Access from Ops-Center: Navigate to 🦄 Unicorn Brigade menu"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  • View logs:     docker logs unicorn-brigade -f"
echo "  • Restart:       docker compose -f docker-compose.brigade.yml restart"
echo "  • Stop:          docker compose -f docker-compose.brigade.yml down"
echo "  • Status:        docker compose -f docker-compose.brigade.yml ps"
echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
