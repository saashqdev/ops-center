#!/bin/bash

# Traefik Deployment Script for Ops Center
# This script helps you deploy the complete Traefik-integrated stack

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Ops Center - Traefik Integration Deployment              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Created .env file. Please edit it with your values."
    else
        echo "❌ No .env.example found. Please create .env manually."
        exit 1
    fi
fi

# Source .env to check required variables
set -a
source .env
set +a

echo "🔍 Checking prerequisites..."
echo ""

# Check required environment variables
REQUIRED_VARS=("APP_DOMAIN" "CF_DNS_API_TOKEN" "ACME_EMAIL")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please add these to your .env file:"
    echo ""
    echo "APP_DOMAIN=kubeworkz.io"
    echo "CF_DNS_API_TOKEN=your_cloudflare_api_token"
    echo "CF_API_EMAIL=your@email.com"
    echo "ACME_EMAIL=admin@kubeworkz.io"
    echo ""
    exit 1
fi

echo "✓ Environment variables configured"
echo "  - Domain: $APP_DOMAIN"
echo "  - ACME Email: $ACME_EMAIL"
echo ""

# Check DNS configuration
echo "🌐 Checking DNS configuration for $APP_DOMAIN..."

check_dns() {
    local subdomain=$1
    local full_domain="${subdomain}.${APP_DOMAIN}"
    
    if [ "$subdomain" = "@" ]; then
        full_domain="$APP_DOMAIN"
    fi
    
    if nslookup "$full_domain" >/dev/null 2>&1; then
        echo "  ✓ $full_domain resolves"
        return 0
    else
        echo "  ⚠️  $full_domain does not resolve yet"
        return 1
    fi
}

DNS_OK=true
check_dns "@" || DNS_OK=false
check_dns "auth" || DNS_OK=false
check_dns "docs" || DNS_OK=false
check_dns "traefik" || DNS_OK=false

if [ "$DNS_OK" = false ]; then
    echo ""
    echo "⚠️  Some DNS records are not configured yet."
    echo "   You need these A records pointing to your server IP:"
    echo ""
    echo "   $APP_DOMAIN         → $(curl -s ifconfig.me)"
    echo "   auth.$APP_DOMAIN    → $(curl -s ifconfig.me)"
    echo "   docs.$APP_DOMAIN    → $(curl -s ifconfig.me)"
    echo "   traefik.$APP_DOMAIN → $(curl -s ifconfig.me)"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for port conflicts
echo ""
echo "🔌 Checking for port conflicts..."

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  ⚠️  Port $port is in use:"
        lsof -Pi :$port -sTCP:LISTEN | grep -v "^COMMAND" | awk '{print "     " $1 " (PID: " $2 ")"}'
        return 1
    else
        echo "  ✓ Port $port is available"
        return 0
    fi
}

PORTS_OK=true
check_port 80 || PORTS_OK=false
check_port 443 || PORTS_OK=false

if [ "$PORTS_OK" = false ]; then
    echo ""
    echo "⚠️  Ports 80 and/or 443 are in use. Traefik needs these ports."
    read -p "Stop existing services and continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Prepare Traefik directories
echo ""
echo "📁 Preparing Traefik directories..."

mkdir -p traefik/letsencrypt
mkdir -p traefik/dynamic

# Create or set permissions for acme.json
if [ ! -f traefik/letsencrypt/acme.json ]; then
    touch traefik/letsencrypt/acme.json
fi
chmod 600 traefik/letsencrypt/acme.json

echo "✓ Traefik directories ready"

# Stop existing services
echo ""
echo "🛑 Stopping existing services..."

# Stop direct port binding stack if running
if docker ps -a --format '{{.Names}}' | grep -q "ops-center-direct"; then
    echo "  Stopping direct port stack..."
    docker-compose -f docker-compose.direct.yml down 2>/dev/null || true
fi

# Stop standalone docs if running
if docker ps -a --format '{{.Names}}' | grep -q "uc1-admin-docs"; then
    echo "  Stopping standalone docs..."
    (cd admin-docs && docker-compose down 2>/dev/null) || true
fi

echo "✓ Existing services stopped"

# Build frontend if needed
echo ""
echo "🏗️  Building frontend..."

if [ -f package.json ]; then
    npm run build
    echo "✓ Frontend built"
else
    echo "⚠️  No package.json found, skipping frontend build"
fi

# Start Traefik-integrated stack
echo ""
echo "🚀 Starting Traefik-integrated stack..."
echo ""

docker-compose -f docker-compose.traefik-integrated.yml up -d

echo ""
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.traefik-integrated.yml ps

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Deployment Complete! 🎉                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Your services should be available at:"
echo ""
echo "  🌐 Main App:      https://$APP_DOMAIN"
echo "  🔐 Keycloak:      https://auth.$APP_DOMAIN"
echo "  📚 Documentation: https://docs.$APP_DOMAIN"
echo "  🎛️  Traefik:       https://traefik.$APP_DOMAIN (user: admin, pass: admin)"
echo ""
echo "⚠️  IMPORTANT:"
echo "  1. Change Traefik dashboard password immediately!"
echo "  2. SSL certificates may take 1-2 minutes to be issued"
echo "  3. Check logs if services aren't accessible:"
echo "     docker-compose -f docker-compose.traefik-integrated.yml logs -f"
echo ""
echo "Next steps:"
echo "  - Test all endpoints above"
echo "  - Update Traefik dashboard password"
echo "  - Configure additional services"
echo ""
