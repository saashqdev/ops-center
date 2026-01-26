# DNS Configuration Guide for Multi-Tenant Subdomain Routing

This guide explains how to configure DNS for wildcard subdomain support, enabling tenant-specific URLs like `acme.ops-center.com`, `contoso.ops-center.com`, etc.

## Prerequisites

- A domain name (e.g., `ops-center.com`, `yourdomain.com`)
- Access to your DNS provider's control panel
- Server public IP address
- Traefik reverse proxy (included in Ops-Center setup)

---

## DNS Configuration Options

### Option 1: Cloudflare (Recommended)

Cloudflare provides free DNS with wildcard support and automatic SSL certificates.

#### Step 1: Add Your Domain to Cloudflare
1. Sign up at [cloudflare.com](https://cloudflare.com)
2. Click "Add Site" and enter your domain
3. Follow the wizard to change your nameservers

#### Step 2: Create DNS Records
Add the following DNS records in Cloudflare dashboard:

```
Type    Name    Content                 Proxy Status    TTL
A       @       YOUR_SERVER_IP          Proxied         Auto
A       *       YOUR_SERVER_IP          Proxied         Auto
A       api     YOUR_SERVER_IP          Proxied         Auto
A       auth    YOUR_SERVER_IP          Proxied         Auto
```

**Explanation:**
- `@` → Main domain (ops-center.com)
- `*` → Wildcard for all subdomains (*.ops-center.com)
- `api` → API subdomain (api.ops-center.com)
- `auth` → Keycloak authentication (auth.ops-center.com)

#### Step 3: Enable SSL
1. Go to SSL/TLS → Overview
2. Set encryption mode to **Full (strict)**
3. Enable **Always Use HTTPS**
4. Enable **Automatic HTTPS Rewrites**

#### Step 4: Configure Cloudflare Proxy (Optional)
- **Proxied (Orange Cloud)**: Routes traffic through Cloudflare (DDoS protection, CDN)
- **DNS Only (Gray Cloud)**: Direct connection to your server

For multi-tenant, **Proxied** is recommended for security.

---

### Option 2: AWS Route 53

#### Step 1: Create Hosted Zone
```bash
aws route53 create-hosted-zone \
  --name ops-center.com \
  --caller-reference $(date +%s)
```

#### Step 2: Create DNS Records
Create `dns-records.json`:
```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "ops-center.com",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "YOUR_SERVER_IP"}]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "*.ops-center.com",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "YOUR_SERVER_IP"}]
      }
    }
  ]
}
```

Apply changes:
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch file://dns-records.json
```

---

### Option 3: DigitalOcean DNS

#### Step 1: Add Domain
```bash
doctl compute domain create ops-center.com
```

#### Step 2: Create Records
```bash
# Main domain
doctl compute domain records create ops-center.com \
  --record-type A \
  --record-name @ \
  --record-data YOUR_SERVER_IP

# Wildcard subdomain
doctl compute domain records create ops-center.com \
  --record-type A \
  --record-name "*" \
  --record-data YOUR_SERVER_IP
```

---

### Option 4: Generic DNS Provider

For any DNS provider (Namecheap, GoDaddy, etc.), add these records:

| Type | Host/Name | Value/Points To | TTL |
|------|-----------|-----------------|-----|
| A    | @         | YOUR_SERVER_IP  | 300 |
| A    | *         | YOUR_SERVER_IP  | 300 |
| A    | api       | YOUR_SERVER_IP  | 300 |
| A    | auth      | YOUR_SERVER_IP  | 300 |

**Note:** Some providers use different terminology:
- Host: `*`, `@`, `api`, `auth`
- Points to / Value: Your server IP
- TTL: 300 seconds (5 minutes) or Auto

---

## Traefik Configuration for Wildcard Domains

### Update docker-compose.direct.yml

Edit your Traefik labels to support wildcard routing:

```yaml
services:
  ops-center-direct:
    # ... existing config ...
    labels:
      # Main domain routing
      - "traefik.http.routers.ops-center-root.rule=Host(`${APP_DOMAIN:-ops-center.com}`)"
      - "traefik.http.routers.ops-center-root.entrypoints=websecure"
      - "traefik.http.routers.ops-center-root.tls.certresolver=letsencrypt"
      
      # Wildcard subdomain routing (tenant subdomains)
      - "traefik.http.routers.ops-center-wildcard.rule=HostRegexp(`{subdomain:[a-z0-9-]+}.${APP_DOMAIN:-ops-center.com}`)"
      - "traefik.http.routers.ops-center-wildcard.entrypoints=websecure"
      - "traefik.http.routers.ops-center-wildcard.tls.certresolver=letsencrypt"
      - "traefik.http.routers.ops-center-wildcard.tls.domains[0].main=${APP_DOMAIN:-ops-center.com}"
      - "traefik.http.routers.ops-center-wildcard.tls.domains[0].sans=*.${APP_DOMAIN:-ops-center.com}"
      - "traefik.http.routers.ops-center-wildcard.priority=90"
      
      # API subdomain
      - "traefik.http.routers.ops-center-api.rule=Host(`api.${APP_DOMAIN:-ops-center.com}`)"
      - "traefik.http.routers.ops-center-api.entrypoints=websecure"
      - "traefik.http.routers.ops-center-api.tls.certresolver=letsencrypt"
      - "traefik.http.routers.ops-center-api.priority=100"
```

### Priority Explanation
- Priority 100: Specific routes (api.ops-center.com) - highest priority
- Priority 90: Wildcard routes (*.ops-center.com)
- Default: Main domain (ops-center.com)

---

## Let's Encrypt SSL Certificates

### Wildcard Certificate Setup

Traefik can automatically obtain wildcard SSL certificates using DNS-01 challenge.

#### For Cloudflare

Edit your Traefik configuration to use Cloudflare DNS:

```yaml
# traefik/traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@ops-center.com
      storage: /letsencrypt/acme.json
      dnsChallenge:
        provider: cloudflare
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"
```

Add Cloudflare credentials to environment:
```yaml
# docker-compose.direct.yml
services:
  traefik:
    environment:
      - CF_API_EMAIL=your-cloudflare-email@example.com
      - CF_API_KEY=your-cloudflare-api-key
```

#### For AWS Route 53

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@ops-center.com
      storage: /letsencrypt/acme.json
      dnsChallenge:
        provider: route53
```

Environment:
```yaml
services:
  traefik:
    environment:
      - AWS_ACCESS_KEY_ID=your-access-key
      - AWS_SECRET_ACCESS_KEY=your-secret-key
      - AWS_REGION=us-east-1
```

---

## Environment Variables

Create or update `.env` file:

```bash
# Domain Configuration
APP_DOMAIN=ops-center.com
BASE_DOMAIN=ops-center.com

# SSL/TLS
ACME_EMAIL=admin@ops-center.com

# Cloudflare (if using)
CF_API_EMAIL=your-email@example.com
CF_API_KEY=your-cloudflare-api-key

# AWS (if using)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

---

## Backend Configuration

The tenant isolation middleware automatically extracts tenant from subdomain. No additional backend configuration needed!

### How It Works

```python
# backend/tenant_isolation.py (already implemented)
class TenantIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract subdomain from Host header
        host = request.headers.get('host', '')
        if '.' in host:
            subdomain = host.split('.')[0]
            # Query database for organization with this subdomain
            tenant_id = await get_org_by_subdomain(subdomain)
            if tenant_id:
                TenantContext.set(tenant_id)
        
        return await call_next(request)
```

---

## Testing DNS Configuration

### 1. Verify DNS Propagation

```bash
# Check main domain
dig ops-center.com +short

# Check wildcard
dig acme.ops-center.com +short
dig test.ops-center.com +short

# All should return your server IP
```

### 2. Test Subdomain Resolution

```bash
# Should all resolve to same IP
nslookup ops-center.com
nslookup acme.ops-center.com
nslookup anyname.ops-center.com
```

### 3. Test HTTPS

```bash
# Main domain
curl -I https://ops-center.com

# Wildcard subdomain
curl -I https://test.ops-center.com

# Should return 200 or redirect, not SSL error
```

### 4. Create Test Tenant

```bash
# Create tenant with subdomain
curl -X POST https://ops-center.com/api/v1/admin/tenants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Tenant",
    "subdomain": "test",
    "tier": "trial",
    "admin_email": "admin@test.com",
    "admin_name": "Test Admin",
    "admin_password": "SecurePass123!"
  }'

# Access tenant-specific URL
curl https://test.ops-center.com/api/v1/health
```

---

## Troubleshooting

### DNS Not Resolving

**Issue:** `dig *.ops-center.com` returns nothing

**Solutions:**
1. Wait 5-60 minutes for DNS propagation
2. Verify wildcard record exists: `*` → `YOUR_SERVER_IP`
3. Check nameservers: `dig ops-center.com NS`
4. Clear local DNS cache: `sudo systemd-resolve --flush-caches` (Linux)

### SSL Certificate Errors

**Issue:** Browser shows "Invalid Certificate"

**Solutions:**
1. Check Traefik logs: `docker logs ops-center-traefik`
2. Verify ACME email in Traefik config
3. Ensure port 80/443 open: `sudo ufw allow 80/tcp && sudo ufw allow 443/tcp`
4. Check Let's Encrypt rate limits (max 50 certs/week)
5. Use DNS-01 challenge for wildcard certs (HTTP-01 doesn't support wildcards)

### Subdomain Routes to Wrong Tenant

**Issue:** `acme.ops-center.com` shows wrong organization

**Solutions:**
1. Check subdomain in database: `SELECT * FROM organizations WHERE subdomain = 'acme';`
2. Verify middleware is registered in `backend/server.py`
3. Check Traefik routing priority (wildcard should be <100)
4. Review backend logs for tenant resolution

### Cloudflare "Error 525: SSL Handshake Failed"

**Solutions:**
1. Set Cloudflare SSL to **Full (strict)**, not Flexible
2. Ensure Traefik is generating valid SSL cert
3. Check origin server port is 443 (HTTPS)

---

## Production Checklist

- [ ] DNS records created (A, wildcard)
- [ ] Nameservers updated (if using new DNS provider)
- [ ] DNS propagation complete (24-48 hours max)
- [ ] Traefik wildcard routing configured
- [ ] SSL certificate resolver configured (Cloudflare/Route53)
- [ ] Environment variables set (APP_DOMAIN, etc.)
- [ ] Firewall rules: port 80, 443 open
- [ ] Test main domain: `https://ops-center.com`
- [ ] Test API subdomain: `https://api.ops-center.com`
- [ ] Test wildcard: `https://test.ops-center.com`
- [ ] Create test tenant with subdomain
- [ ] Verify tenant isolation (User A can't see User B's data)
- [ ] Monitor Traefik logs for SSL/routing issues

---

## Quick Setup Script

Save as `setup-dns.sh`:

```bash
#!/bin/bash
set -e

echo "🌐 Ops-Center DNS Configuration Setup"
echo "======================================"
echo ""

# Prompt for configuration
read -p "Enter your domain (e.g., ops-center.com): " DOMAIN
read -p "Enter your server IP address: " SERVER_IP
read -p "Enter your email for SSL certificates: " ACME_EMAIL

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cat > .env <<EOF
# Domain Configuration
APP_DOMAIN=$DOMAIN
BASE_DOMAIN=$DOMAIN

# SSL/TLS
ACME_EMAIL=$ACME_EMAIL

# Database (keep existing or set defaults)
POSTGRES_USER=unicorn
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=unicorn_db

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 32)
EOF
    echo "✓ Created .env file"
else
    echo "⚠ .env file exists, updating domain settings..."
    sed -i "s/^APP_DOMAIN=.*/APP_DOMAIN=$DOMAIN/" .env
    sed -i "s/^ACME_EMAIL=.*/ACME_EMAIL=$ACME_EMAIL/" .env
fi

echo ""
echo "📋 DNS Records to Add:"
echo "====================="
echo ""
echo "Add these records in your DNS provider:"
echo ""
echo "Type    Name    Value           TTL"
echo "----    ----    -----           ---"
echo "A       @       $SERVER_IP      300"
echo "A       *       $SERVER_IP      300"
echo "A       api     $SERVER_IP      300"
echo "A       auth    $SERVER_IP      300"
echo ""
echo "For Cloudflare CLI (optional):"
echo "------------------------------"
echo "cloudflare-cli dns create-record $DOMAIN A @ $SERVER_IP"
echo "cloudflare-cli dns create-record $DOMAIN A \"*\" $SERVER_IP"
echo ""
echo "✓ Configuration complete!"
echo ""
echo "Next steps:"
echo "1. Add DNS records shown above"
echo "2. Wait 5-60 minutes for DNS propagation"
echo "3. Run: docker-compose -f docker-compose.direct.yml up -d"
echo "4. Test: curl https://$DOMAIN"
```

Make executable and run:
```bash
chmod +x setup-dns.sh
./setup-dns.sh
```

---

## Additional Resources

- [Traefik Wildcard Certificates](https://doc.traefik.io/traefik/https/acme/#wildcard-domains)
- [Let's Encrypt DNS-01 Challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)
- [Cloudflare DNS API](https://developers.cloudflare.com/api/operations/dns-records-for-a-zone-create-dns-record)
- [AWS Route 53 Documentation](https://docs.aws.amazon.com/route53/)

---

**Questions?** Open an issue on GitHub or check the [Epic 10 Documentation](EPIC_10_MULTITENANT_COMPLETE.md).
