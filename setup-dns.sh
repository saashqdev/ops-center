#!/bin/bash
set -e

echo "🌐 Ops-Center DNS Configuration Setup"
echo "======================================"
echo ""

# Prompt for configuration
read -p "Enter your domain (e.g., ops-center.com): " DOMAIN
read -p "Enter your server IP address: " SERVER_IP
read -p "Enter your email for SSL certificates: " ACME_EMAIL

# Validate inputs
if [ -z "$DOMAIN" ] || [ -z "$SERVER_IP" ] || [ -z "$ACME_EMAIL" ]; then
    echo "❌ Error: All fields are required"
    exit 1
fi

# Validate IP format
if ! [[ $SERVER_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "❌ Error: Invalid IP address format"
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cat > .env <<EOF
# Domain Configuration
APP_DOMAIN=$DOMAIN
BASE_DOMAIN=$DOMAIN

# SSL/TLS
ACME_EMAIL=$ACME_EMAIL

# Database
POSTGRES_USER=unicorn
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=unicorn_db

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 32)
EOF
    echo "✓ Created .env file with generated passwords"
else
    echo "⚠ .env file exists, updating domain settings..."
    
    # Update or add domain settings
    if grep -q "^APP_DOMAIN=" .env; then
        sed -i "s|^APP_DOMAIN=.*|APP_DOMAIN=$DOMAIN|" .env
    else
        echo "APP_DOMAIN=$DOMAIN" >> .env
    fi
    
    if grep -q "^BASE_DOMAIN=" .env; then
        sed -i "s|^BASE_DOMAIN=.*|BASE_DOMAIN=$DOMAIN|" .env
    else
        echo "BASE_DOMAIN=$DOMAIN" >> .env
    fi
    
    if grep -q "^ACME_EMAIL=" .env; then
        sed -i "s|^ACME_EMAIL=.*|ACME_EMAIL=$ACME_EMAIL|" .env
    else
        echo "ACME_EMAIL=$ACME_EMAIL" >> .env
    fi
    
    echo "✓ Updated .env file"
fi

# Display current server IP
CURRENT_IP=$(curl -s ifconfig.me || echo "Unable to detect")
echo ""
echo "📡 Server Information:"
echo "====================="
echo "Current Server IP: $CURRENT_IP"
echo "Configured IP: $SERVER_IP"
if [ "$CURRENT_IP" != "$SERVER_IP" ] && [ "$CURRENT_IP" != "Unable to detect" ]; then
    echo "⚠ Warning: IPs don't match. Make sure $SERVER_IP is correct."
fi

echo ""
echo "📋 DNS Records to Add:"
echo "====================="
echo ""
echo "Add these records in your DNS provider's control panel:"
echo ""
printf "%-8s %-12s %-20s %-6s\n" "Type" "Name" "Value" "TTL"
printf "%-8s %-12s %-20s %-6s\n" "----" "----" "-----" "---"
printf "%-8s %-12s %-20s %-6s\n" "A" "@" "$SERVER_IP" "300"
printf "%-8s %-12s %-20s %-6s\n" "A" "*" "$SERVER_IP" "300"
printf "%-8s %-12s %-20s %-6s\n" "A" "api" "$SERVER_IP" "300"
printf "%-8s %-12s %-20s %-6s\n" "A" "auth" "$SERVER_IP" "300"

echo ""
echo "🔧 DNS Provider Quick Commands:"
echo "================================"
echo ""
echo "Cloudflare CLI:"
echo "  # Install: npm install -g cloudflare-cli"
echo "  cloudflare-cli dns create-record $DOMAIN A @ $SERVER_IP"
echo "  cloudflare-cli dns create-record $DOMAIN A \"*\" $SERVER_IP"
echo "  cloudflare-cli dns create-record $DOMAIN A api $SERVER_IP"
echo "  cloudflare-cli dns create-record $DOMAIN A auth $SERVER_IP"
echo ""
echo "AWS Route 53:"
echo "  # Install: apt-get install awscli"
echo "  aws route53 change-resource-record-sets --hosted-zone-id YOUR_ZONE_ID --change-batch file://dns-records.json"
echo ""
echo "DigitalOcean:"
echo "  # Install: snap install doctl"
echo "  doctl compute domain create $DOMAIN"
echo "  doctl compute domain records create $DOMAIN --record-type A --record-name @ --record-data $SERVER_IP"
echo "  doctl compute domain records create $DOMAIN --record-type A --record-name \"*\" --record-data $SERVER_IP"
echo ""

# Create AWS Route53 template
cat > dns-records.json <<EOF
{
  "Comment": "Ops-Center DNS records for multi-tenant subdomains",
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "$DOMAIN",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "$SERVER_IP"}]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "*.$DOMAIN",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "$SERVER_IP"}]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.$DOMAIN",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "$SERVER_IP"}]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "auth.$DOMAIN",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "$SERVER_IP"}]
      }
    }
  ]
}
EOF

echo "✓ Created dns-records.json for AWS Route 53"
echo ""

# Create DNS verification script
cat > verify-dns.sh <<'VERIFY_SCRIPT'
#!/bin/bash

DOMAIN=${1:-$APP_DOMAIN}

if [ -z "$DOMAIN" ]; then
    echo "Usage: ./verify-dns.sh <domain>"
    echo "Or set APP_DOMAIN in .env"
    exit 1
fi

echo "🔍 Verifying DNS configuration for $DOMAIN"
echo "==========================================="
echo ""

check_dns() {
    local name=$1
    local expected_ip=$2
    
    echo -n "Checking $name... "
    
    result=$(dig +short "$name" A | head -1)
    
    if [ -z "$result" ]; then
        echo "❌ No DNS record found"
        return 1
    elif [ "$result" = "$expected_ip" ]; then
        echo "✓ $result"
        return 0
    else
        echo "⚠ $result (expected $expected_ip)"
        return 1
    fi
}

# Get expected IP from .env or user
if [ -f .env ]; then
    source .env
    read -p "Expected IP [$SERVER_IP]: " INPUT_IP
    SERVER_IP=${INPUT_IP:-$SERVER_IP}
else
    read -p "Expected IP: " SERVER_IP
fi

echo ""
echo "Testing DNS records:"
echo ""

check_dns "$DOMAIN" "$SERVER_IP"
check_dns "api.$DOMAIN" "$SERVER_IP"
check_dns "auth.$DOMAIN" "$SERVER_IP"
check_dns "test.$DOMAIN" "$SERVER_IP"
check_dns "demo.$DOMAIN" "$SERVER_IP"

echo ""
echo "Testing HTTPS connectivity:"
echo ""

test_https() {
    local url=$1
    echo -n "Testing $url... "
    
    if curl -sI --max-time 5 "$url" > /dev/null 2>&1; then
        echo "✓ Accessible"
    else
        echo "❌ Not accessible (may need to wait for SSL cert)"
    fi
}

test_https "https://$DOMAIN"
test_https "https://api.$DOMAIN"

echo ""
echo "Note: If DNS shows correct IP but HTTPS fails, wait a few minutes"
echo "for Let's Encrypt SSL certificate generation."
VERIFY_SCRIPT

chmod +x verify-dns.sh
echo "✓ Created verify-dns.sh script"
echo ""

echo "✅ Setup complete!"
echo ""
echo "📝 Next Steps:"
echo "============="
echo "1. Add the DNS records shown above to your DNS provider"
echo "2. Wait 5-60 minutes for DNS propagation"
echo "3. Verify DNS: ./verify-dns.sh $DOMAIN"
echo "4. Restart services: docker-compose -f docker-compose.direct.yml restart"
echo "5. Test main domain: curl https://$DOMAIN"
echo "6. Test wildcard: curl https://test.$DOMAIN"
echo ""
echo "📚 For detailed instructions, see: docs/DNS_SETUP_GUIDE.md"
echo ""
echo "Environment file location: $(pwd)/.env"
echo "DNS verification script: $(pwd)/verify-dns.sh"
echo "AWS Route53 config: $(pwd)/dns-records.json"
