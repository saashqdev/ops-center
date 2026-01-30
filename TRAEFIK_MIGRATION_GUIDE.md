# Traefik Migration Guide

## Overview

This guide will help you migrate from direct port binding to Traefik-managed reverse proxy for the entire Ops Center stack.

## Benefits

- ✅ **Unified HTTPS** - All services automatically get Let's Encrypt SSL certificates
- ✅ **Clean URLs** - Use subdomains instead of ports:
  - `kubeworkz.io` → Main application
  - `auth.kubeworkz.io` → Keycloak
  - `docs.kubeworkz.io` → Documentation
  - `traefik.kubeworkz.io` → Traefik dashboard
- ✅ **Security** - No exposed ports except 80/443, internal network communication
- ✅ **Professional** - Enterprise-grade reverse proxy setup
- ✅ **Automatic Discovery** - Services register themselves via Docker labels

## Prerequisites

1. **DNS Records Required**:
   ```
   A    kubeworkz.io         → Your server IP
   A    *.kubeworkz.io       → Your server IP (wildcard)
   
   OR individual records:
   A    auth.kubeworkz.io    → Your server IP
   A    docs.kubeworkz.io    → Your server IP
   A    traefik.kubeworkz.io → Your server IP
   ```

2. **Cloudflare API Token** (for automatic SSL):
   - Login to Cloudflare
   - Go to: My Profile → API Tokens → Create Token
   - Use template: "Edit zone DNS"
   - Permissions: Zone - DNS - Edit
   - Zone Resources: Include - Specific zone - kubeworkz.io
   - Copy the token

3. **Environment Variables**:
   Add to your `.env` file:
   ```bash
   # Cloudflare credentials for Let's Encrypt DNS challenge
   CF_DNS_API_TOKEN=your_cloudflare_api_token_here
   CF_API_EMAIL=your@email.com
   
   # ACME (Let's Encrypt) email
   ACME_EMAIL=admin@kubeworkz.io
   
   # Your domain
   APP_DOMAIN=kubeworkz.io
   ```

## Migration Steps

### Step 1: Stop Current Services

```bash
cd /home/ubuntu/Ops-Center-OSS

# Stop current direct-port stack
docker-compose -f docker-compose.direct.yml down

# Stop docs if running separately
cd admin-docs && docker-compose down && cd ..
```

### Step 2: Update Traefik Configuration

The `traefik/traefik.yml` file is already configured. Verify it matches your domain:

```bash
# Check the configuration
cat traefik/traefik.yml
```

### Step 3: Set Permissions for Let's Encrypt Storage

```bash
# Create letsencrypt directory if it doesn't exist
mkdir -p traefik/letsencrypt

# Set proper permissions (Traefik needs to write acme.json)
chmod 600 traefik/letsencrypt/acme.json 2>/dev/null || touch traefik/letsencrypt/acme.json && chmod 600 traefik/letsencrypt/acme.json
```

### Step 4: Start Traefik-Integrated Stack

```bash
# Start the complete stack with Traefik
docker-compose -f docker-compose.traefik-integrated.yml up -d

# Watch the logs
docker-compose -f docker-compose.traefik-integrated.yml logs -f traefik
```

### Step 5: Verify Services

Wait 1-2 minutes for Let's Encrypt certificates to be issued, then check:

```bash
# Check all services are running
docker ps

# Test endpoints
curl -I https://kubeworkz.io
curl -I https://auth.kubeworkz.io
curl -I https://docs.kubeworkz.io
curl -I https://traefik.kubeworkz.io  # Dashboard (requires auth)
```

### Step 6: Update Frontend Link

The documentation link in HelpPanel.jsx should be updated from `http://kubeworkz.io:8087` to `https://docs.kubeworkz.io`:

```bash
# Rebuild frontend with new link
npm run build
```

## Traefik Dashboard

Access the Traefik dashboard at: `https://traefik.kubeworkz.io`

Default credentials:
- Username: `admin`
- Password: `admin`

**⚠️ SECURITY**: Change the password immediately!

Generate new hash:
```bash
# Install htpasswd if needed
sudo apt-get install apache2-utils

# Generate new password hash
htpasswd -nb admin your-new-password

# Update the label in docker-compose.traefik-integrated.yml:
# - "traefik.http.middlewares.dashboard-auth.basicauth.users=admin:$$apr1$$..."
```

## Troubleshooting

### DNS Not Resolving
```bash
# Check DNS propagation
nslookup docs.kubeworkz.io
nslookup auth.kubeworkz.io
```

### SSL Certificate Issues
```bash
# Check Traefik logs
docker logs ops-center-traefik

# Check ACME JSON (should have certificates)
cat traefik/letsencrypt/acme.json | jq .

# If using staging (for testing), switch to production in traefik.yml
# Remove this line: caServer: https://acme-staging-v02.api.letsencrypt.org/directory
```

### Service Not Accessible
```bash
# Check if service is registered with Traefik
docker exec ops-center-traefik wget -qO- http://localhost:8080/api/http/routers | jq .

# Check service labels
docker inspect <container_name> | grep traefik
```

### Port 80/443 Already in Use
```bash
# Check what's using the ports
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting services
sudo systemctl stop nginx  # if you have system nginx
sudo systemctl stop apache2
```

## Rollback

If you need to rollback to direct port binding:

```bash
# Stop Traefik stack
docker-compose -f docker-compose.traefik-integrated.yml down

# Start direct port stack
docker-compose -f docker-compose.direct.yml up -d
cd admin-docs && docker-compose up -d && cd ..
```

## Next Steps

After successful migration:

1. ✅ Update all internal links to use new subdomain URLs
2. ✅ Test all services thoroughly
3. ✅ Configure Traefik dashboard authentication
4. ✅ Set up monitoring/metrics for Traefik
5. ✅ Configure rate limiting if needed
6. ✅ Add additional services (Lago, etc.) to Traefik

## Additional Services

To add more services to Traefik, just add these labels to any container:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.myservice.rule=Host(`myservice.${APP_DOMAIN}`)"
  - "traefik.http.routers.myservice.entrypoints=websecure"
  - "traefik.http.routers.myservice.tls.certresolver=letsencrypt"
  - "traefik.http.services.myservice.loadbalancer.server.port=8080"
```

## Support

- Traefik Documentation: https://doc.traefik.io/traefik/
- Let's Encrypt Rate Limits: https://letsencrypt.org/docs/rate-limits/
- Cloudflare DNS API: https://developers.cloudflare.com/api/operations/dns-records-for-a-zone-list-dns-records
