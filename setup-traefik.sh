#!/bin/bash
set -e

echo "🔧 Traefik Multi-Tenant Subdomain Configuration"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Warning: Running as root. Consider using a non-root user with sudo."
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Run ./setup-dns.sh first."
    exit 1
fi

# Source .env
set -a
source .env
set +a

echo "📋 Configuration Summary"
echo "======================="
echo "Domain: ${APP_DOMAIN:-not set}"
echo "Email: ${ACME_EMAIL:-not set}"
echo ""

# Validate required variables
if [ -z "$APP_DOMAIN" ]; then
    echo "❌ Error: APP_DOMAIN not set in .env"
    exit 1
fi

if [ -z "$ACME_EMAIL" ]; then
    echo "❌ Error: ACME_EMAIL not set in .env"
    exit 1
fi

# Create required directories
echo "📁 Creating Traefik directories..."
mkdir -p traefik/letsencrypt
mkdir -p traefik/dynamic
chmod 600 traefik/letsencrypt || true

# Create acme.json with correct permissions
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json

echo "✓ Traefik directories created"
echo ""

# Check if web network exists
if ! docker network ls | grep -q "^.*web"; then
    echo "🌐 Creating 'web' network for Traefik..."
    docker network create web
    echo "✓ Network 'web' created"
else
    echo "✓ Network 'web' already exists"
fi
echo ""

# Ask about DNS provider for wildcard SSL
echo "🔒 SSL Certificate Configuration"
echo "================================"
echo ""
echo "For wildcard SSL certificates (*.${APP_DOMAIN}), Traefik needs DNS API access."
echo ""
echo "Select your DNS provider:"
echo "1) Cloudflare (recommended)"
echo "2) AWS Route53"
echo "3) DigitalOcean"
echo "4) Skip (configure manually later)"
echo ""
read -p "Choice [1-4]: " dns_choice

case $dns_choice in
    1)
        echo ""
        echo "Cloudflare Configuration"
        echo "-----------------------"
        read -p "Cloudflare Email: " cf_email
        read -p "Cloudflare API Key (Global API Key from cloudflare.com/profile/api-tokens): " cf_key
        
        # Add to .env if not present
        if ! grep -q "^CF_API_EMAIL=" .env; then
            echo "CF_API_EMAIL=$cf_email" >> .env
        else
            sed -i "s|^CF_API_EMAIL=.*|CF_API_EMAIL=$cf_email|" .env
        fi
        
        if ! grep -q "^CF_API_KEY=" .env; then
            echo "CF_API_KEY=$cf_key" >> .env
        else
            sed -i "s|^CF_API_KEY=.*|CF_API_KEY=$cf_key|" .env
        fi
        
        echo "✓ Cloudflare credentials saved to .env"
        ;;
    2)
        echo ""
        echo "AWS Route53 Configuration"
        echo "------------------------"
        read -p "AWS Access Key ID: " aws_key
        read -p "AWS Secret Access Key: " aws_secret
        read -p "AWS Region [us-east-1]: " aws_region
        aws_region=${aws_region:-us-east-1}
        
        if ! grep -q "^AWS_ACCESS_KEY_ID=" .env; then
            echo "AWS_ACCESS_KEY_ID=$aws_key" >> .env
        else
            sed -i "s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$aws_key|" .env
        fi
        
        if ! grep -q "^AWS_SECRET_ACCESS_KEY=" .env; then
            echo "AWS_SECRET_ACCESS_KEY=$aws_secret" >> .env
        else
            sed -i "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$aws_secret|" .env
        fi
        
        if ! grep -q "^AWS_REGION=" .env; then
            echo "AWS_REGION=$aws_region" >> .env
        else
            sed -i "s|^AWS_REGION=.*|AWS_REGION=$aws_region|" .env
        fi
        
        # Update traefik.yml to use route53
        sed -i 's|provider: cloudflare|provider: route53|' traefik/traefik.yml
        
        echo "✓ AWS credentials saved to .env"
        ;;
    3)
        echo ""
        echo "DigitalOcean Configuration"
        echo "-------------------------"
        read -p "DigitalOcean API Token: " do_token
        
        if ! grep -q "^DO_AUTH_TOKEN=" .env; then
            echo "DO_AUTH_TOKEN=$do_token" >> .env
        else
            sed -i "s|^DO_AUTH_TOKEN=.*|DO_AUTH_TOKEN=$do_token|" .env
        fi
        
        # Update traefik.yml to use digitalocean
        sed -i 's|provider: cloudflare|provider: digitalocean|' traefik/traefik.yml
        
        echo "✓ DigitalOcean token saved to .env"
        ;;
    4)
        echo "⚠️  Skipping DNS configuration. You'll need to configure manually."
        echo "   Edit traefik/traefik.yml and set your DNS provider."
        ;;
    *)
        echo "Invalid choice. Skipping DNS configuration."
        ;;
esac

echo ""
echo "🔐 Traefik Dashboard Authentication"
echo "===================================="
echo ""
echo "The Traefik dashboard will be accessible at: https://traefik.${APP_DOMAIN}"
echo ""
read -p "Set dashboard username [admin]: " dashboard_user
dashboard_user=${dashboard_user:-admin}

read -sp "Set dashboard password: " dashboard_pass
echo ""

# Generate htpasswd hash
if command -v htpasswd &> /dev/null; then
    dashboard_hash=$(htpasswd -nb "$dashboard_user" "$dashboard_pass")
elif command -v docker &> /dev/null; then
    # Use httpd docker image to generate hash
    dashboard_hash=$(docker run --rm httpd:alpine htpasswd -nb "$dashboard_user" "$dashboard_pass")
else
    echo "⚠️  Warning: htpasswd not found. Using default credentials (admin/admin)"
    dashboard_hash='admin:$apr1$8EVjn/nj$GiLUZqcbueTFeD23SuB6x0'
fi

# Escape $ for docker-compose
dashboard_hash_escaped=$(echo "$dashboard_hash" | sed 's/\$/\$\$/g')

# Update docker-compose with new credentials
sed -i "s|basicauth.users=.*|basicauth.users=$dashboard_hash_escaped\"|" docker-compose.traefik-standalone.yml

echo "✓ Dashboard credentials configured"
echo ""

# Check firewall status
echo "🔥 Firewall Configuration"
echo "========================"
echo ""

if command -v ufw &> /dev/null; then
    ufw_status=$(ufw status | grep -i "Status: active" || echo "inactive")
    if [ "$ufw_status" = "inactive" ]; then
        echo "ℹ️  UFW firewall is inactive"
    else
        echo "UFW is active. Checking required ports..."
        
        if ! ufw status | grep -q "80/tcp.*ALLOW"; then
            read -p "Open port 80 (HTTP)? [y/N]: " open_80
            if [ "$open_80" = "y" ] || [ "$open_80" = "Y" ]; then
                sudo ufw allow 80/tcp
                echo "✓ Port 80 opened"
            fi
        else
            echo "✓ Port 80 already open"
        fi
        
        if ! ufw status | grep -q "443/tcp.*ALLOW"; then
            read -p "Open port 443 (HTTPS)? [y/N]: " open_443
            if [ "$open_443" = "y" ] || [ "$open_443" = "Y" ]; then
                sudo ufw allow 443/tcp
                echo "✓ Port 443 opened"
            fi
        else
            echo "✓ Port 443 already open"
        fi
    fi
else
    echo "ℹ️  UFW not installed. Ensure ports 80 and 443 are open."
fi

echo ""
echo "📦 Docker Compose Services"
echo "=========================="
echo ""
echo "Select deployment mode:"
echo "1) Traefik only (manage services separately)"
echo "2) Traefik + Ops-Center (recommended)"
echo ""
read -p "Choice [1-2]: " deploy_choice

case $deploy_choice in
    1)
        echo ""
        echo "Starting Traefik only..."
        docker-compose -f docker-compose.traefik-standalone.yml up -d
        ;;
    2)
        echo ""
        echo "Starting Traefik + Ops-Center..."
        
        # Start Traefik first
        docker-compose -f docker-compose.traefik-standalone.yml up -d
        sleep 5
        
        # Start main stack
        docker-compose -f docker-compose.direct.yml up -d
        ;;
    *)
        echo "Invalid choice. Skipping deployment."
        echo "Start services manually with:"
        echo "  docker-compose -f docker-compose.traefik-standalone.yml up -d"
        ;;
esac

echo ""
echo "✅ Traefik Configuration Complete!"
echo ""
echo "📊 Service Status"
echo "================"
docker-compose -f docker-compose.traefik-standalone.yml ps

echo ""
echo "🌐 Access Points"
echo "==============="
echo "Main App:      https://${APP_DOMAIN}"
echo "API:           https://api.${APP_DOMAIN}"
echo "Auth:          https://auth.${APP_DOMAIN}"
echo "Traefik:       https://traefik.${APP_DOMAIN}"
echo "               Username: $dashboard_user"
echo ""
echo "Tenant Examples:"
echo "  https://acme.${APP_DOMAIN}"
echo "  https://demo.${APP_DOMAIN}"
echo ""

echo "📝 Next Steps"
echo "============"
echo "1. Verify DNS records are configured (run ./verify-dns.sh)"
echo "2. Wait for SSL certificate generation (1-5 minutes)"
echo "3. Check Traefik logs: docker logs ops-center-traefik"
echo "4. Create test tenant via API or UI"
echo "5. Test subdomain access"
echo ""

echo "🐛 Troubleshooting"
echo "================="
echo "View logs:        docker logs ops-center-traefik -f"
echo "View certificates: ls -la traefik/letsencrypt/"
echo "Test DNS:         ./verify-dns.sh $APP_DOMAIN"
echo "Restart:          docker-compose -f docker-compose.traefik-standalone.yml restart"
echo ""

echo "Full documentation: docs/DNS_SETUP_GUIDE.md"
