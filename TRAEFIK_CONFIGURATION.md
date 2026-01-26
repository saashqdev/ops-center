# 🔧 Traefik Reverse Proxy Configuration Complete

## Overview

Your Ops-Center now has a **production-ready Traefik reverse proxy** configured for multi-tenant subdomain routing with automatic SSL certificates.

---

## 📦 Files Created

### Traefik Configuration

1. **[docker-compose.traefik-standalone.yml](docker-compose.traefik-standalone.yml)**
   - Traefik v2.10 container configuration
   - Port mappings: 80 (HTTP), 443 (HTTPS), 8080 (Dashboard)
   - Environment variables for DNS API credentials
   - Security middlewares and labels

2. **[traefik/traefik.yml](traefik/traefik.yml)**
   - Static configuration
   - Entry points (HTTP → HTTPS redirect)
   - Let's Encrypt certificate resolver
   - DNS-01 challenge for wildcard certs
   - Docker provider for service discovery
   - Logging and metrics

3. **[traefik/dynamic/middleware.yml](traefik/dynamic/middleware.yml)**
   - Rate limiting (global and per-IP)
   - Compression
   - CORS headers
   - Security headers
   - TLS configuration

4. **[setup-traefik.sh](setup-traefik.sh)** (Executable)
   - Interactive Traefik setup wizard
   - DNS provider configuration
   - Dashboard authentication
   - Firewall configuration
   - Automated deployment

### Nginx Updates

5. **[nginx.conf](nginx.conf)** (Updated)
   - Multi-tenant subdomain support
   - Real IP from Traefik
   - Subdomain extraction
   - Optimized caching
   - Security headers
   - SPA routing

---

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run interactive setup
./setup-traefik.sh
```

This will:
1. ✅ Create required directories
2. ✅ Configure DNS provider (Cloudflare/AWS/DO)
3. ✅ Set up dashboard authentication
4. ✅ Check/configure firewall
5. ✅ Deploy Traefik + Ops-Center
6. ✅ Generate SSL certificates

### Option 2: Manual Setup

```bash
# 1. Create directories
mkdir -p traefik/letsencrypt traefik/dynamic
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json

# 2. Create web network
docker network create web

# 3. Configure .env (add DNS credentials)
# For Cloudflare:
echo "CF_API_EMAIL=your@email.com" >> .env
echo "CF_API_KEY=your-api-key" >> .env

# 4. Start Traefik
docker-compose -f docker-compose.traefik-standalone.yml up -d

# 5. Start Ops-Center
docker-compose -f docker-compose.direct.yml up -d
```

---

## 🌐 Architecture

### Request Flow

```
User → DNS → Traefik → Backend/Nginx
                ↓
          SSL Termination
                ↓
          Subdomain Routing
                ↓
          Tenant Context
```

### Port Mapping

| Port | Service | Purpose |
|------|---------|---------|
| 80 | Traefik | HTTP (redirects to 443) |
| 443 | Traefik | HTTPS (SSL termination) |
| 8080 | Traefik | Dashboard (auth required) |
| 8084 | Backend | Ops-Center API |

### Network Topology

```
┌─────────────────────────────────────────────┐
│         Internet (Port 80, 443)             │
└────────────────┬────────────────────────────┘
                 │
         ┌───────▼────────┐
         │    Traefik     │  Network: web
         │  (SSL, Routing)│
         └───────┬────────┘
                 │
      ┏━━━━━━━━━┻━━━━━━━━━┓
      ▼                    ▼
┌─────────────┐    ┌─────────────┐
│ Ops-Center  │    │   Keycloak  │
│   Backend   │    │    Auth     │
│  :8084      │    │   :8080     │
└─────────────┘    └─────────────┘
      │                    │
      └────────┬───────────┘
               │
        ┌──────▼──────┐
        │  PostgreSQL │
        │    :5432    │
        └─────────────┘
```

---

## 🔒 SSL Certificate Configuration

### Wildcard Certificates

Traefik automatically obtains Let's Encrypt wildcard certificates using DNS-01 challenge:

**Supports:**
- `ops-center.com` → Main domain
- `*.ops-center.com` → All subdomains
- Automatic renewal every 60 days

### DNS Providers

#### Cloudflare (Recommended)

```yaml
# .env
CF_API_EMAIL=your@email.com
CF_API_KEY=your-global-api-key

# Or use API token:
CF_DNS_API_TOKEN=your-api-token
```

**Get API Key:**
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Use "Global API Key" or create scoped token
3. Token needs `Zone:DNS:Edit` permission

#### AWS Route53

```yaml
# .env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

**IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:GetChange",
        "route53:ListHostedZonesByName"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "arn:aws:route53:::hostedzone/*"
    }
  ]
}
```

#### DigitalOcean

```yaml
# .env
DO_AUTH_TOKEN=your-digitalocean-api-token
```

Edit `traefik/traefik.yml`:
```yaml
dnsChallenge:
  provider: digitalocean
```

---

## 📊 Traefik Dashboard

Access at: **https://traefik.yourdomain.com**

**Default Credentials:**
- Username: `admin`
- Password: Set during `./setup-traefik.sh`

**Features:**
- Real-time request statistics
- Service health status
- Router configuration
- Certificate status
- Middleware monitoring

**Change Password:**
```bash
# Generate new hash
htpasswd -nb admin newpassword

# Or use Docker:
docker run --rm httpd:alpine htpasswd -nb admin newpassword

# Update docker-compose.traefik-standalone.yml
# Replace: basicauth.users=...
```

---

## 🎯 Routing Configuration

### Priority System

Traefik routes by priority (higher = first match):

| Priority | Route | Example |
|----------|-------|---------|
| 100 | Admin paths | `ops-center.com/admin` |
| 90 | API paths | `ops-center.com/api` |
| 80 | Auth paths | `auth.ops-center.com` |
| 50 | Wildcard subdomains | `*.ops-center.com` |
| 1 | Root domain | `ops-center.com` |

### Docker Labels (docker-compose.direct.yml)

```yaml
services:
  ops-center-direct:
    labels:
      # Enable Traefik
      - "traefik.enable=true"
      
      # Service definition
      - "traefik.http.services.ops-center-svc.loadbalancer.server.port=8084"
      
      # Wildcard subdomain router (NEW)
      - "traefik.http.routers.ops-center-wildcard.rule=HostRegexp(`{subdomain:[a-z0-9-]+}.${APP_DOMAIN}`)"
      - "traefik.http.routers.ops-center-wildcard.priority=50"
      - "traefik.http.routers.ops-center-wildcard.entrypoints=websecure"
      - "traefik.http.routers.ops-center-wildcard.tls.certresolver=letsencrypt"
      - "traefik.http.routers.ops-center-wildcard.service=ops-center-svc"
```

### Static Routes (traefik.yml)

```yaml
entryPoints:
  websecure:
    address: ":443"
    http:
      tls:
        certResolver: letsencrypt
        domains:
          - main: ops-center.com
            sans:
              - "*.ops-center.com"
```

---

## 🛡️ Security Features

### Automatic HTTPS

- HTTP → HTTPS redirect (all requests)
- HSTS headers (31536000 seconds)
- TLS 1.2+ only
- Strong cipher suites

### Rate Limiting

**Global:**
- 100 requests/second average
- 200 burst

**Per IP:**
- 20 requests/second average
- 50 burst

**Configure in:** `traefik/dynamic/middleware.yml`

### Security Headers

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`
- `Referrer-Policy`

### Dashboard Protection

- Basic authentication required
- HTTPS only
- Configurable credentials

---

## 🧪 Testing

### Check Traefik Status

```bash
# Container status
docker ps | grep traefik

# Logs
docker logs ops-center-traefik -f

# Health check
curl -I https://yourdomain.com
```

### Certificate Verification

```bash
# Check certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com | grep -A5 "Certificate chain"

# Check wildcard
openssl s_client -connect test.yourdomain.com:443 -servername test.yourdomain.com | grep -A5 "Certificate chain"

# View stored certificates
ls -la traefik/letsencrypt/
cat traefik/letsencrypt/acme.json | jq .
```

### Routing Test

```bash
# Main domain
curl -I https://yourdomain.com
# Should return: 200 OK

# API subdomain
curl -I https://api.yourdomain.com/api/v1/health
# Should return: 200 OK

# Wildcard subdomain
curl -I https://test.yourdomain.com
# Should return: 200 OK

# Wrong subdomain (should still work)
curl -I https://nonexistent.yourdomain.com
# Should return: 200 OK (serves main app)
```

### Dashboard Access

```bash
# Access dashboard
open https://traefik.yourdomain.com/dashboard/
# Or: curl -u admin:password https://traefik.yourdomain.com/api/http/routers
```

---

## 🐛 Troubleshooting

### SSL Certificate Not Generated

**Symptoms:**
- `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`
- Certificate not found

**Solutions:**

1. **Check Traefik logs:**
```bash
docker logs ops-center-traefik 2>&1 | grep -i "error\|certificate"
```

2. **Verify DNS API credentials:**
```bash
# For Cloudflare
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CF_DNS_API_TOKEN"
```

3. **Check acme.json permissions:**
```bash
chmod 600 traefik/letsencrypt/acme.json
docker-compose -f docker-compose.traefik-standalone.yml restart
```

4. **Use Let's Encrypt staging (testing):**
```yaml
# traefik/traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory
```

### Wildcard Routes Not Working

**Check:**

1. **Docker labels:**
```bash
docker inspect ops-center-direct | grep -A20 "Labels"
```

2. **Traefik routing:**
```bash
curl http://localhost:8080/api/http/routers | jq .
```

3. **DNS resolution:**
```bash
dig test.yourdomain.com +short
# Should return your server IP
```

### Rate Limit Errors

**Symptoms:**
- `429 Too Many Requests`

**Solutions:**

1. **Adjust limits in** `traefik/dynamic/middleware.yml`:
```yaml
middlewares:
  rate-limit-per-ip:
    rateLimit:
      average: 50  # Increase from 20
      burst: 100    # Increase from 50
```

2. **Disable rate limiting temporarily:**
```yaml
# Comment out middleware in router
```

### Dashboard Access Denied

**Solutions:**

1. **Reset credentials:**
```bash
docker run --rm httpd:alpine htpasswd -nb admin newpassword
# Update docker-compose labels
```

2. **Check firewall:**
```bash
sudo ufw status
sudo ufw allow 8080/tcp  # If needed
```

3. **Verify TLS:**
```bash
curl -k -u admin:password https://traefik.yourdomain.com/dashboard/
```

---

## 📈 Performance Optimization

### Connection Pooling

```yaml
# traefik/traefik.yml (add to providers.docker)
providers:
  docker:
    network: web
    exposedByDefault: false
    watch: true
    httpClientTimeout: 30
```

### Compression

Already enabled in `traefik/dynamic/middleware.yml`:
```yaml
middlewares:
  compress:
    compress: {}
```

Apply to routers:
```yaml
- "traefik.http.routers.ops-center-wildcard.middlewares=compress"
```

### Caching (Optional)

Install Traefik plugin for HTTP caching:
```yaml
# traefik/traefik.yml
experimental:
  plugins:
    cache:
      moduleName: github.com/traefik/plugin-simplecache
      version: v0.2.1
```

---

## 🔄 Maintenance

### Update Traefik

```bash
# Pull latest image
docker pull traefik:v2.10

# Recreate container
docker-compose -f docker-compose.traefik-standalone.yml up -d --force-recreate
```

### Renew Certificates

Traefik automatically renews certificates 30 days before expiration.

**Manual renewal:**
```bash
# Delete acme.json
rm traefik/letsencrypt/acme.json
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json

# Restart Traefik
docker-compose -f docker-compose.traefik-standalone.yml restart
```

### Backup Configuration

```bash
# Backup critical files
tar -czf traefik-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.traefik-standalone.yml \
  traefik/traefik.yml \
  traefik/dynamic/ \
  traefik/letsencrypt/acme.json \
  .env
```

### Monitor Logs

```bash
# Follow logs
docker logs ops-center-traefik -f

# Search for errors
docker logs ops-center-traefik 2>&1 | grep -i error

# View access logs
docker exec ops-center-traefik cat /var/log/traefik/access.log
```

---

## 📚 Additional Resources

- **Traefik Docs**: https://doc.traefik.io/traefik/
- **DNS Providers**: https://doc.traefik.io/traefik/https/acme/#providers
- **Let's Encrypt**: https://letsencrypt.org/docs/
- **Ops-Center DNS Guide**: [docs/DNS_SETUP_GUIDE.md](docs/DNS_SETUP_GUIDE.md)
- **Epic 10 Multi-Tenant**: [EPIC_10_MULTITENANT_COMPLETE.md](EPIC_10_MULTITENANT_COMPLETE.md)

---

## ✅ Configuration Checklist

- [ ] Run `./setup-traefik.sh` or manual setup
- [ ] Configure DNS provider credentials
- [ ] Create `web` network
- [ ] Set dashboard credentials
- [ ] Open firewall ports 80, 443
- [ ] Start Traefik container
- [ ] Verify SSL certificate generation
- [ ] Test main domain HTTPS
- [ ] Test wildcard subdomain
- [ ] Access Traefik dashboard
- [ ] Configure rate limiting (if needed)
- [ ] Set up monitoring/alerts
- [ ] Backup acme.json

---

**🎉 Traefik is production-ready!**

Run `./setup-traefik.sh` to get started, or manually deploy with:

```bash
docker-compose -f docker-compose.traefik-standalone.yml up -d
```

Questions? Check [docs/DNS_SETUP_GUIDE.md](docs/DNS_SETUP_GUIDE.md)
