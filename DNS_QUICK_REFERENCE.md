# 🌐 Multi-Tenant DNS Quick Reference

## 🚀 Quick Start (5 minutes)

```bash
# 1. Run DNS setup
./setup-dns.sh

# 2. Add DNS records (shown by script)
# Go to your DNS provider and add:
#   A    @     YOUR_IP
#   A    *     YOUR_IP
#   A    api   YOUR_IP  
#   A    auth  YOUR_IP

# 3. Configure Traefik reverse proxy
./setup-traefik.sh

# 4. Wait for DNS propagation (5-60 min)
./verify-dns.sh yourdomain.com

# 5. Test
curl https://yourdomain.com
curl https://test.yourdomain.com
```

---

## 📋 DNS Records Checklist

- [ ] **Root domain**: `A @ YOUR_IP` → ops-center.com
- [ ] **Wildcard**: `A * YOUR_IP` → *.ops-center.com  
- [ ] **API**: `A api YOUR_IP` → api.ops-center.com
- [ ] **Auth**: `A auth YOUR_IP` → auth.ops-center.com

---

## 🔧 Configuration Files Updated

| File | What Changed |
|------|-------------|
| `docker-compose.traefik-standalone.yml` | **NEW** Traefik reverse proxy |
| `traefik/traefik.yml` | **NEW** Traefik static config |
| `traefik/dynamic/middleware.yml` | **NEW** Rate limiting, CORS, security |
| `nginx.conf` | Multi-tenant subdomain support |
| `docker-compose.direct.yml` | Wildcard routing labels |
| `.env` | APP_DOMAIN, DNS credentials |
| `setup-dns.sh` | Interactive DNS wizard |
| `setup-traefik.sh` | **NEW** Interactive Traefik wizard |
| `verify-dns.sh` | DNS verification tool |
| `dns-records.json` | AWS Route53 template |

---

## 🧪 Testing Commands

```bash
# DNS resolution
dig ops-center.com +short
dig acme.ops-center.com +short
dig test.ops-center.com +short

# HTTPS connectivity
curl -I https://ops-center.com
curl -I https://api.ops-center.com
curl -I https://test.ops-center.com

# Create test tenant
curl -X POST https://ops-center.com/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test","subdomain":"test","tier":"trial",...}'

# Access tenant subdomain
curl https://test.ops-center.com/api/v1/health
```

---

## 🔑 Environment Variables

```bash
# Required in .env
APP_DOMAIN=ops-center.com          # Your domain
ACME_EMAIL=admin@ops-center.com    # SSL cert email

# Optional (Cloudflare)
CF_API_EMAIL=you@example.com
CF_API_KEY=your-cloudflare-key

# Optional (AWS Route53)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

---

## 🎯 Traefik Routing Priority

```
Priority 100: Specific paths    /admin, /api, /auth
Priority 90:  API subdomain     api.ops-center.com
Priority 80:  Auth subdomain    auth.ops-center.com
Priority 50:  Wildcard tenants  *.ops-center.com
Priority 1:   Root domain       ops-center.com
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| DNS not resolving | Wait 60min, check wildcard record `*` |
| SSL error | Use DNS-01 challenge (HTTP-01 doesn't support wildcard) |
| Wrong tenant loads | Check subdomain in DB, verify middleware |
| Cloudflare 525 error | Set SSL to "Full (strict)" not "Flexible" |

---

## 📚 Full Documentation

- **Setup Guide**: [docs/DNS_SETUP_GUIDE.md](docs/DNS_SETUP_GUIDE.md)
- **Epic 10**: [EPIC_10_MULTITENANT_COMPLETE.md](EPIC_10_MULTITENANT_COMPLETE.md)
- **Traefik Docs**: https://doc.traefik.io/traefik/routing/routers/

---

## 🎬 Example Workflow

```bash
# Scenario: Deploy Ops-Center for "acme.com"

# 1. Setup
./setup-dns.sh
# Enter: acme.com, 1.2.3.4, admin@acme.com

# 2. Configure DNS provider
# Add 4 A records (shown by script)

# 3. Wait & verify
sleep 300  # 5 minutes
./verify-dns.sh acme.com

# 4. Deploy
docker-compose -f docker-compose.direct.yml up -d

# 5. Create tenant
curl -X POST https://acme.com/api/v1/admin/tenants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer One",
    "subdomain": "customer1",
    "tier": "professional",
    "admin_email": "admin@customer1.com",
    "admin_name": "Admin User",
    "admin_password": "SecurePass123!"
  }'

# 6. Customer accesses their subdomain
# https://customer1.acme.com
```

---

**Need help?** Open an issue or see full guide in `docs/DNS_SETUP_GUIDE.md`
