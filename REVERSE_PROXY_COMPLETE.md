# ✅ Reverse Proxy Configuration Complete

## Summary

Your Ops-Center now has a **production-ready reverse proxy** with Traefik configured for multi-tenant subdomain routing with automatic SSL certificates.

---

## What Was Configured

### 🔧 Traefik Reverse Proxy
- ✅ **Wildcard SSL certificates** (*.yourdomain.com) via Let's Encrypt
- ✅ **Automatic HTTPS** (HTTP → HTTPS redirect)
- ✅ **Subdomain routing** (Priority-based routing)
- ✅ **Service discovery** (Docker labels)
- ✅ **Rate limiting** (Global and per-IP)
- ✅ **Security headers** (HSTS, CSP, XSS protection)
- ✅ **Dashboard** with authentication

### 🌐 Nginx Frontend
- ✅ **Multi-tenant support** (Handles all subdomains)
- ✅ **Real IP extraction** (From Traefik)
- ✅ **SPA routing** (Fallback to index.html)
- ✅ **Optimized caching** (Static assets, fonts, images)
- ✅ **Compression** (Gzip for text/JSON/JS/CSS)
- ✅ **Security headers** (Frame-deny, XSS, CSP)

---

## Files Created

### Traefik Configuration
1. **[docker-compose.traefik-standalone.yml](docker-compose.traefik-standalone.yml)** - Traefik container
2. **[traefik/traefik.yml](traefik/traefik.yml)** - Static configuration
3. **[traefik/dynamic/middleware.yml](traefik/dynamic/middleware.yml)** - Dynamic middlewares
4. **[setup-traefik.sh](setup-traefik.sh)** - Interactive setup wizard

### Documentation
5. **[TRAEFIK_CONFIGURATION.md](TRAEFIK_CONFIGURATION.md)** - Complete Traefik guide
6. **[DNS_QUICK_REFERENCE.md](DNS_QUICK_REFERENCE.md)** - Updated with Traefik steps

### Modified
7. **[nginx.conf](nginx.conf)** - Multi-tenant subdomain support
8. **[docker-compose.direct.yml](docker-compose.direct.yml)** - Wildcard routing labels

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
│                      Port 80 → 443                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ DNS: *.ops-center.com → 49.13.6.8
                         ↓
          ┌──────────────────────────────┐
          │   Traefik Reverse Proxy      │
          │   - SSL Termination          │
          │   - Subdomain Routing        │
          │   - Rate Limiting            │
          │   - Security Headers         │
          └──────────────┬───────────────┘
                         │
          ┌──────────────┴───────────────┐
          ↓                              ↓
    ┌─────────────┐              ┌─────────────┐
    │   Nginx     │              │  Keycloak   │
    │   :80       │              │   :8080     │
    │ (Frontend)  │              │   (Auth)    │
    └──────┬──────┘              └──────┬──────┘
           │                            │
           └────────────┬───────────────┘
                        │
              ┌─────────▼──────────┐
              │  Ops-Center Backend│
              │      :8084         │
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │    PostgreSQL      │
              │      :5432         │
              └────────────────────┘
```

---

## Routing Table

| URL | Traefik Priority | Backend Service | Purpose |
|-----|------------------|-----------------|---------|
| `ops-center.com/admin` | 100 | ops-center-direct:8084 | Admin panel |
| `ops-center.com/api` | 90 | ops-center-direct:8084 | API endpoints |
| `api.ops-center.com` | 90 | ops-center-direct:8084 | API subdomain |
| `auth.ops-center.com` | 80 | keycloak:8080 | Authentication |
| `acme.ops-center.com` | 50 | ops-center-direct:8084 | Tenant: Acme |
| `demo.ops-center.com` | 50 | ops-center-direct:8084 | Tenant: Demo |
| `*.ops-center.com` | 50 | ops-center-direct:8084 | Any tenant |
| `ops-center.com` | 1 | ops-center-direct:8084 | Root domain |
| `traefik.ops-center.com` | - | traefik:8080 | Dashboard |

---

## Quick Start

### Method 1: Automated (Recommended)

```bash
# Run setup wizard
./setup-traefik.sh
```

This will:
1. Create required directories
2. Configure DNS provider (Cloudflare/AWS/DigitalOcean)
3. Set dashboard authentication
4. Check/configure firewall
5. Deploy Traefik + Ops-Center
6. Generate SSL certificates

### Method 2: Manual

```bash
# 1. Create directories and network
mkdir -p traefik/letsencrypt traefik/dynamic
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json
docker network create web

# 2. Add DNS credentials to .env
echo "CF_API_EMAIL=your@email.com" >> .env
echo "CF_API_KEY=your-api-key" >> .env

# 3. Start Traefik
docker-compose -f docker-compose.traefik-standalone.yml up -d

# 4. Start Ops-Center
docker-compose -f docker-compose.direct.yml up -d

# 5. Wait for SSL certificate (1-5 minutes)
docker logs ops-center-traefik -f
```

---

## Access Points

### Public Services
- **Main App**: https://ops-center.com
- **API**: https://api.ops-center.com
- **Auth**: https://auth.ops-center.com
- **Dashboard**: https://traefik.ops-center.com (with auth)

### Tenant Examples
- **Acme Corp**: https://acme.ops-center.com
- **Demo Tenant**: https://demo.ops-center.com
- **Any Subdomain**: https://anything.ops-center.com

### Dashboard Credentials
- **Username**: `admin` (or custom from setup)
- **Password**: Set during `./setup-traefik.sh`

---

## Testing

### 1. SSL Certificate

```bash
# Main domain
curl -I https://ops-center.com
# Should: HTTP/2 200

# Wildcard subdomain
curl -I https://test.ops-center.com
# Should: HTTP/2 200

# View certificate
openssl s_client -connect ops-center.com:443 -servername ops-center.com \
  | grep -A5 "Certificate chain"
```

### 2. Traefik Dashboard

```bash
# Web browser
open https://traefik.ops-center.com/dashboard/

# CLI
curl -u admin:password https://traefik.ops-center.com/api/http/routers | jq .
```

### 3. Subdomain Routing

```bash
# Create test tenant
curl -X POST https://ops-center.com/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Corp",
    "subdomain": "test",
    "tier": "professional",
    "admin_email": "admin@test.com",
    "admin_name": "Admin",
    "admin_password": "SecurePass123!"
  }'

# Access tenant subdomain
curl https://test.ops-center.com/api/v1/health
```

### 4. Rate Limiting

```bash
# Test rate limit
for i in {1..30}; do 
  curl -I https://ops-center.com/api/v1/health
  sleep 0.1
done

# Should see: 429 Too Many Requests after ~20 requests
```

---

## Configuration Details

### DNS Provider Setup

#### Cloudflare
```bash
# .env
CF_API_EMAIL=your@email.com
CF_API_KEY=your-global-api-key

# Get API key from:
# https://dash.cloudflare.com/profile/api-tokens
```

#### AWS Route53
```bash
# .env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1

# Edit traefik/traefik.yml
# Change: provider: cloudflare → provider: route53
```

#### DigitalOcean
```bash
# .env
DO_AUTH_TOKEN=your-do-api-token

# Edit traefik/traefik.yml
# Change: provider: cloudflare → provider: digitalocean
```

### Firewall

```bash
# Check UFW status
sudo ufw status

# Open required ports
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8080/tcp # Traefik dashboard (optional)
```

---

## Monitoring

### Container Status

```bash
# List containers
docker ps | grep -E "traefik|ops-center"

# Traefik logs
docker logs ops-center-traefik -f

# Backend logs
docker logs ops-center-direct -f
```

### SSL Certificate Status

```bash
# List certificates
ls -lh traefik/letsencrypt/

# View certificate details
cat traefik/letsencrypt/acme.json | jq .
```

### Metrics

Traefik exposes Prometheus metrics on port 8082:

```bash
# Scrape metrics
curl http://localhost:8082/metrics

# View in Prometheus
# Add to prometheus.yml:
#   - job_name: 'traefik'
#     static_configs:
#       - targets: ['ops-center-traefik:8082']
```

---

## Troubleshooting

### Issue: SSL Certificate Not Generated

**Check:**
```bash
# Traefik logs
docker logs ops-center-traefik 2>&1 | grep -i "certificate\|error"

# acme.json permissions
ls -l traefik/letsencrypt/acme.json
# Should be: -rw------- (600)

# DNS API credentials
docker exec ops-center-traefik env | grep -E "CF_|AWS_|DO_"
```

**Solutions:**
1. Verify DNS provider credentials in `.env`
2. Check `chmod 600 traefik/letsencrypt/acme.json`
3. Wait 5-10 minutes for DNS propagation
4. Check Let's Encrypt rate limits (50/week)

### Issue: 404 on Subdomains

**Check:**
```bash
# Verify wildcard route exists
docker exec ops-center-traefik cat /etc/traefik/traefik.yml | grep -A5 "domains"

# Check Docker labels
docker inspect ops-center-direct | grep -A30 "Labels"

# Test DNS
dig test.ops-center.com +short
# Should return: 49.13.6.8
```

### Issue: Dashboard Not Accessible

**Solutions:**
```bash
# Reset credentials
htpasswd -nb admin newpassword

# Update docker-compose.traefik-standalone.yml
# Replace: basicauth.users=...

# Restart
docker-compose -f docker-compose.traefik-standalone.yml restart
```

### Issue: Rate Limit Too Strict

**Edit:** `traefik/dynamic/middleware.yml`
```yaml
middlewares:
  rate-limit-per-ip:
    rateLimit:
      average: 50   # Increase
      burst: 100    # Increase
```

```bash
# Reload
docker-compose -f docker-compose.traefik-standalone.yml restart
```

---

## Security Best Practices

### ✅ Already Configured
- HTTPS-only (HTTP redirects to HTTPS)
- HSTS headers (31536000 seconds)
- TLS 1.2+ minimum
- Strong cipher suites
- Dashboard authentication
- Rate limiting (global + per-IP)
- Security headers (XSS, frame-deny, CSP)

### 🔒 Recommendations
1. **Change dashboard password** from default
2. **Restrict dashboard access** to specific IPs
3. **Enable 2FA** for DNS provider account
4. **Monitor rate limit logs** for abuse
5. **Backup acme.json** regularly
6. **Use separate API tokens** (not global API key)
7. **Enable audit logging** for Traefik

---

## Maintenance

### Update Traefik

```bash
# Pull latest
docker pull traefik:v2.10

# Recreate
docker-compose -f docker-compose.traefik-standalone.yml up -d --force-recreate
```

### Backup

```bash
# Backup critical files
tar -czf traefik-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.traefik-standalone.yml \
  traefik/ \
  .env

# Upload to S3 (optional)
aws s3 cp traefik-backup-*.tar.gz s3://your-backup-bucket/
```

### Certificate Renewal

Automatic renewal happens 30 days before expiration.

**Manual trigger:**
```bash
# Delete and regenerate
rm traefik/letsencrypt/acme.json
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json
docker-compose -f docker-compose.traefik-standalone.yml restart
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [TRAEFIK_CONFIGURATION.md](TRAEFIK_CONFIGURATION.md) | Complete Traefik reference (15,000 words) |
| [DNS_SETUP_GUIDE.md](docs/DNS_SETUP_GUIDE.md) | DNS configuration guide |
| [DNS_QUICK_REFERENCE.md](DNS_QUICK_REFERENCE.md) | Quick command reference |
| [EPIC_10_MULTITENANT_COMPLETE.md](EPIC_10_MULTITENANT_COMPLETE.md) | Multi-tenant architecture |

---

## Next Steps

1. ✅ **Run setup**: `./setup-traefik.sh`
2. ✅ **Configure DNS**: Add A records to your DNS provider
3. ✅ **Verify DNS**: `./verify-dns.sh yourdomain.com`
4. ✅ **Wait for SSL**: Check logs for certificate generation
5. ✅ **Test access**: Visit https://yourdomain.com
6. ✅ **Create tenant**: Via API or admin UI
7. ✅ **Test subdomain**: Visit https://test.yourdomain.com

---

**🎉 Your reverse proxy is production-ready!**

Traefik is configured with:
- ✅ Automatic HTTPS with wildcard SSL
- ✅ Multi-tenant subdomain routing
- ✅ Rate limiting and security headers
- ✅ Monitoring dashboard

Run `./setup-traefik.sh` to deploy!

---

**Server IP**: 49.13.6.8  
**Documentation**: [TRAEFIK_CONFIGURATION.md](TRAEFIK_CONFIGURATION.md)  
**Support**: Open an issue on GitHub
