#!/bin/bash
#
# Open WebUI (Unicorn Chat) Installation Script
# Installs and configures Open WebUI with LiteLLM backend + Keycloak SSO
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
cat << "EOF"
   ___                    __        __   _     _   _ ___ 
  / _ \ _ __   ___ _ __   \ \      / /__| |__  | | | |_ _|
 | | | | '_ \ / _ \ '_ \   \ \ /\ / / _ \ '_ \ | | | || | 
 | |_| | |_) |  __/ | | |   \ V  V /  __/ |_) || |_| || | 
  \___/| .__/ \___|_| |_|    \_/\_/ \___|_.__/  \___/|___|
       |_|                                                
  Unicorn Chat - AI Chat Interface Installation
EOF
echo -e "${NC}"

# ── Working directory check ──────────────────────────────────
if [ ! -f "docker-compose.openwebui.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.openwebui.yml not found${NC}"
    echo "Please run this script from the Ops-Center-OSS directory"
    exit 1
fi

# ── Prerequisites ────────────────────────────────────────────
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

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl is required but not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ curl found${NC}"

# ── Docker networks ──────────────────────────────────────────
echo -e "\n${BLUE}🌐 Checking Docker networks...${NC}"
for network in web unicorn-network; do
    if ! docker network inspect $network &> /dev/null; then
        echo -e "${YELLOW}⚠️  Network '$network' not found, creating...${NC}"
        docker network create $network
        echo -e "${GREEN}✅ Created network: $network${NC}"
    else
        echo -e "${GREEN}✅ Network exists: $network${NC}"
    fi
done

# ── LiteLLM check ────────────────────────────────────────────
echo -e "\n${BLUE}🤖 Checking LiteLLM proxy...${NC}"
if docker ps --format '{{.Names}}' | grep -q "unicorn-litellm"; then
    echo -e "${GREEN}✅ LiteLLM proxy is running${NC}"
else
    echo -e "${YELLOW}⚠️  LiteLLM proxy is not running${NC}"
    echo "Open WebUI uses LiteLLM as its AI backend."
    echo "Start it first:  docker compose -f docker-compose.litellm.yml up -d"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ── Environment file ─────────────────────────────────────────
echo -e "\n${BLUE}📝 Configuring environment...${NC}"
if [ ! -f .env.openwebui ]; then
    if [ -f .env.openwebui.example ]; then
        cp .env.openwebui.example .env.openwebui
        echo -e "${GREEN}✅ Created .env.openwebui from template${NC}"
    else
        echo -e "${RED}❌ .env.openwebui.example not found${NC}"
        exit 1
    fi

    # Auto-populate from existing .env.auth if available
    if [ -f .env.auth ]; then
        echo -e "${BLUE}  Importing settings from .env.auth...${NC}"

        # Extract values from .env.auth
        AUTH_HOST=$(grep '^EXTERNAL_HOST=' .env.auth | cut -d= -f2 | tr -d ' "')
        AUTH_REALM=$(grep '^KEYCLOAK_REALM=' .env.auth | cut -d= -f2 | tr -d ' "')
        AUTH_LITELLM_KEY=$(grep '^LITELLM_MASTER_KEY=' .env.auth | cut -d= -f2)
        AUTH_KC_ADMIN=$(grep '^KEYCLOAK_ADMIN_USER=' .env.auth | cut -d= -f2 | tr -d ' "')
        AUTH_KC_PASS=$(grep '^KEYCLOAK_ADMIN_PASSWORD=' .env.auth | cut -d= -f2)

        # Apply to .env.openwebui
        [ -n "$AUTH_HOST" ] && sed -i "s|^EXTERNAL_HOST=.*|EXTERNAL_HOST=${AUTH_HOST}|" .env.openwebui
        [ -n "$AUTH_REALM" ] && sed -i "s|^KEYCLOAK_REALM=.*|KEYCLOAK_REALM=${AUTH_REALM}|" .env.openwebui
        [ -n "$AUTH_LITELLM_KEY" ] && sed -i "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=${AUTH_LITELLM_KEY}|" .env.openwebui
        [ -n "$AUTH_KC_ADMIN" ] && sed -i "s|^KEYCLOAK_ADMIN_USER=.*|KEYCLOAK_ADMIN_USER=${AUTH_KC_ADMIN}|" .env.openwebui
        [ -n "$AUTH_KC_PASS" ] && sed -i "s|^KEYCLOAK_ADMIN_PASSWORD=.*|KEYCLOAK_ADMIN_PASSWORD=${AUTH_KC_PASS}|" .env.openwebui

        # Generate a random secret key
        SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | xxd -p | tr -d '\n')
        sed -i "s|^OPENWEBUI_SECRET_KEY=.*|OPENWEBUI_SECRET_KEY=${SECRET_KEY}|" .env.openwebui

        echo -e "${GREEN}  ✅ Imported EXTERNAL_HOST, KEYCLOAK_REALM, LITELLM_MASTER_KEY${NC}"
    fi

    echo -e "${YELLOW}⚠️  Review .env.openwebui before continuing${NC}"
    echo "   Required: LITELLM_MASTER_KEY, KEYCLOAK_ADMIN_PASSWORD"
    echo ""
    read -p "Press Enter to continue after reviewing, or Ctrl+C to exit..."
else
    echo -e "${GREEN}✅ .env.openwebui already exists${NC}"
fi

# Source the env file
set -a
source .env.openwebui
set +a

# ── Keycloak OIDC Client Registration ────────────────────────
echo -e "\n${BLUE}🔑 Setting up Keycloak SSO...${NC}"

KEYCLOAK_BASE="https://auth.${EXTERNAL_HOST:-kubeworkz.io}"
KC_REALM="${KEYCLOAK_REALM:-uchub}"
KC_CLIENT_ID="open-webui"
CHAT_URL="https://chat.${EXTERNAL_HOST:-kubeworkz.io}"

# Check if we have admin credentials
if [ -n "$KEYCLOAK_ADMIN_PASSWORD" ] && [ "$KEYCLOAK_ADMIN_PASSWORD" != "" ]; then
    echo -e "${BLUE}  Obtaining admin token...${NC}"
    KC_TOKEN=$(curl -sf -X POST "${KEYCLOAK_BASE}/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${KEYCLOAK_ADMIN_USER:-admin}" \
        -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
        -d "grant_type=password" \
        -d "client_id=admin-cli" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) || true

    if [ -n "$KC_TOKEN" ]; then
        echo -e "${GREEN}  ✅ Keycloak admin authenticated${NC}"

        # Check if client already exists
        EXISTING=$(curl -sf -H "Authorization: Bearer ${KC_TOKEN}" \
            "${KEYCLOAK_BASE}/admin/realms/${KC_REALM}/clients?clientId=${KC_CLIENT_ID}" 2>/dev/null) || true

        if echo "$EXISTING" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if len(d)>0 else 1)" 2>/dev/null; then
            echo -e "${YELLOW}  ⚠️  Client '${KC_CLIENT_ID}' already exists in Keycloak${NC}"
            # Extract existing client secret
            KC_INTERNAL_ID=$(echo "$EXISTING" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null)
            if [ -n "$KC_INTERNAL_ID" ]; then
                KC_SECRET_JSON=$(curl -sf -H "Authorization: Bearer ${KC_TOKEN}" \
                    "${KEYCLOAK_BASE}/admin/realms/${KC_REALM}/clients/${KC_INTERNAL_ID}/client-secret" 2>/dev/null) || true
                KC_SECRET=$(echo "$KC_SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['value'])" 2>/dev/null) || true
                if [ -n "$KC_SECRET" ]; then
                    sed -i "s|^OPENWEBUI_OAUTH_CLIENT_SECRET=.*|OPENWEBUI_OAUTH_CLIENT_SECRET=${KC_SECRET}|" .env.openwebui
                    echo -e "${GREEN}  ✅ Retrieved existing client secret${NC}"
                fi
            fi
        else
            echo -e "${BLUE}  Creating OIDC client '${KC_CLIENT_ID}'...${NC}"
            CREATE_RESPONSE=$(curl -sf -o /dev/null -w "%{http_code}" -X POST \
                -H "Authorization: Bearer ${KC_TOKEN}" \
                -H "Content-Type: application/json" \
                "${KEYCLOAK_BASE}/admin/realms/${KC_REALM}/clients" \
                -d "{
                    \"clientId\": \"${KC_CLIENT_ID}\",
                    \"name\": \"Open WebUI - Unicorn Chat\",
                    \"enabled\": true,
                    \"protocol\": \"openid-connect\",
                    \"publicClient\": false,
                    \"standardFlowEnabled\": true,
                    \"directAccessGrantsEnabled\": false,
                    \"serviceAccountsEnabled\": false,
                    \"redirectUris\": [
                        \"${CHAT_URL}/*\",
                        \"${CHAT_URL}/oauth/oidc/callback\"
                    ],
                    \"webOrigins\": [
                        \"${CHAT_URL}\",
                        \"https://${EXTERNAL_HOST:-kubeworkz.io}\"
                    ],
                    \"attributes\": {
                        \"post.logout.redirect.uris\": \"${CHAT_URL}/*\"
                    },
                    \"protocolMappers\": [
                        {
                            \"name\": \"email\",
                            \"protocol\": \"openid-connect\",
                            \"protocolMapper\": \"oidc-usermodel-attribute-mapper\",
                            \"config\": {
                                \"claim.name\": \"email\",
                                \"user.attribute\": \"email\",
                                \"id.token.claim\": \"true\",
                                \"access.token.claim\": \"true\",
                                \"userinfo.token.claim\": \"true\"
                            }
                        }
                    ]
                }") || true

            if [ "$CREATE_RESPONSE" = "201" ]; then
                echo -e "${GREEN}  ✅ OIDC client created${NC}"

                # Retrieve the generated client secret
                CLIENTS_JSON=$(curl -sf -H "Authorization: Bearer ${KC_TOKEN}" \
                    "${KEYCLOAK_BASE}/admin/realms/${KC_REALM}/clients?clientId=${KC_CLIENT_ID}" 2>/dev/null) || true
                KC_INTERNAL_ID=$(echo "$CLIENTS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null)

                if [ -n "$KC_INTERNAL_ID" ]; then
                    KC_SECRET_JSON=$(curl -sf -H "Authorization: Bearer ${KC_TOKEN}" \
                        "${KEYCLOAK_BASE}/admin/realms/${KC_REALM}/clients/${KC_INTERNAL_ID}/client-secret" 2>/dev/null) || true
                    KC_SECRET=$(echo "$KC_SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['value'])" 2>/dev/null) || true
                    if [ -n "$KC_SECRET" ]; then
                        sed -i "s|^OPENWEBUI_OAUTH_CLIENT_SECRET=.*|OPENWEBUI_OAUTH_CLIENT_SECRET=${KC_SECRET}|" .env.openwebui
                        echo -e "${GREEN}  ✅ Client secret saved to .env.openwebui${NC}"
                    fi
                fi
            else
                echo -e "${YELLOW}  ⚠️  Could not create client (HTTP ${CREATE_RESPONSE})${NC}"
                echo "     You may need to register the client manually in Keycloak."
            fi
        fi
    else
        echo -e "${YELLOW}  ⚠️  Could not authenticate with Keycloak admin${NC}"
        echo "     Set KEYCLOAK_ADMIN_PASSWORD in .env.openwebui and re-run, or register the"
        echo "     '${KC_CLIENT_ID}' OIDC client manually in Keycloak."
    fi
else
    echo -e "${YELLOW}  ⚠️  No KEYCLOAK_ADMIN_PASSWORD set — skipping auto-registration${NC}"
    echo "     To enable SSO, register '${KC_CLIENT_ID}' manually in Keycloak at:"
    echo "     ${KEYCLOAK_BASE}/admin/master/console/#/${KC_REALM}/clients"
fi

# ── Pull image ────────────────────────────────────────────────
echo -e "\n${BLUE}📦 Pulling Open WebUI image...${NC}"
docker pull ghcr.io/open-webui/open-webui:main
echo -e "${GREEN}✅ Image pulled${NC}"

# ── Start services ────────────────────────────────────────────
echo -e "\n${BLUE}🚀 Starting Open WebUI...${NC}"
docker compose -f docker-compose.openwebui.yml --env-file .env.openwebui up -d

# ── Wait for health ───────────────────────────────────────────
echo -e "\n${BLUE}⏳ Waiting for Open WebUI to start...${NC}"
MAX_WAIT=90
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:3100/health &> /dev/null; then
        echo -e "\n${GREEN}✅ Open WebUI is healthy${NC}"
        break
    fi
    echo -n "."
    sleep 3
    WAIT_COUNT=$((WAIT_COUNT + 3))
done
echo ""

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}⚠️  Open WebUI not responding after ${MAX_WAIT}s${NC}"
    echo "  Check logs: docker logs unicorn-open-webui"
    echo "  It may still be initializing — try again in a minute."
fi

# ── Verify ────────────────────────────────────────────────────
echo -e "\n${BLUE}🔍 Verifying installation...${NC}"

if docker ps --format '{{.Names}}' | grep -q "unicorn-open-webui"; then
    echo -e "${GREEN}✅ Container: unicorn-open-webui running${NC}"
else
    echo -e "${RED}❌ Container not running — check: docker logs unicorn-open-webui${NC}"
fi

if docker ps --format '{{.Names}}' | grep -q "open-webui-redis"; then
    echo -e "${GREEN}✅ Container: open-webui-redis running${NC}"
else
    echo -e "${YELLOW}⚠️  Redis container not running${NC}"
fi

# Check Traefik config
if [ -f "traefik/dynamic/openwebui.yml" ]; then
    echo -e "${GREEN}✅ Traefik routing config exists${NC}"
else
    echo -e "${YELLOW}⚠️  traefik/dynamic/openwebui.yml not found — external access won't work${NC}"
fi

# ── DNS reminder ──────────────────────────────────────────────
echo -e "\n${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Open WebUI (Unicorn Chat) Installation Complete!${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo -e "  ${GREEN}•${NC} Local:             http://localhost:3100"
echo -e "  ${GREEN}•${NC} External:          https://chat.${EXTERNAL_HOST:-kubeworkz.io}"
echo -e "  ${GREEN}•${NC} Ops-Center:        https://${EXTERNAL_HOST:-kubeworkz.io}/admin/chat"
echo ""
echo -e "${BLUE}AI Backend:${NC}"
echo -e "  ${GREEN}•${NC} LiteLLM proxy:     http://unicorn-litellm-wilmer:4000 (internal)"
echo -e "  ${GREEN}•${NC} All LiteLLM models are available automatically"
echo ""
echo -e "${BLUE}Authentication:${NC}"
if [ -n "$KC_SECRET" ]; then
    echo -e "  ${GREEN}•${NC} Keycloak SSO:      ✅ Configured (client: ${KC_CLIENT_ID})"
else
    echo -e "  ${YELLOW}•${NC} Keycloak SSO:      ⚠️  Manual setup required"
    echo "     Register client '${KC_CLIENT_ID}' in Keycloak with redirect URI:"
    echo "     ${CHAT_URL}/oauth/oidc/callback"
fi
echo ""
echo -e "${YELLOW}DNS Setup Required:${NC}"
echo "  Add a DNS record for chat.${EXTERNAL_HOST:-kubeworkz.io}"
echo "  pointing to this server's IP address."
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  • View logs:     docker logs unicorn-open-webui -f"
echo "  • Restart:       docker compose -f docker-compose.openwebui.yml restart"
echo "  • Stop:          docker compose -f docker-compose.openwebui.yml down"
echo "  • Status:        docker compose -f docker-compose.openwebui.yml ps"
echo "  • Update:        docker compose -f docker-compose.openwebui.yml pull && \\"
echo "                   docker compose -f docker-compose.openwebui.yml up -d"
echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
