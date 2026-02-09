# Unicorn Brigade Installation Guide

## 🦄 Overview

Unicorn Brigade is a multi-agent AI platform with 47+ pre-built domain specialists, integrated into Ops-Center for seamless access and management.

## 📋 Prerequisites

- **Docker** & **Docker Compose** installed
- **PostgreSQL** database (unicorn-postgresql container)
- **Redis** (unicorn-redis container)
- **LLM API Keys** (at least one):
  - Anthropic (Claude models)
  - OpenAI (GPT models)
  - Groq (fast inference)
  - OpenRouter (multi-provider)

## 🚀 Quick Install

```bash
# Navigate to Ops-Center directory
cd /home/ubuntu/Ops-Center-OSS

# Run installation script
chmod +x install-brigade.sh
./install-brigade.sh
```

The script will:
1. ✅ Check prerequisites (Docker, networks)
2. 🗄️ Create Brigade database
3. 📦 Verify/build Brigade image
4. 🚀 Deploy Brigade container
5. ✅ Verify installation

## 📝 Manual Installation

### Step 1: Configure Environment

```bash
# Copy environment template
cp .env.brigade .env.brigade.local

# Edit configuration
nano .env.brigade.local
```

**Required Settings:**
```bash
# LLM API Keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GROQ_API_KEY=gsk_xxxxx

# Domain (for production)
EXTERNAL_HOST=your-domain.com
BRIGADE_EXTERNAL_URL=https://brigade.your-domain.com

# Security
BRIGADE_SECRET_KEY=your-random-secret-key-here
```

### Step 2: Initialize Database

```bash
# Create Brigade database
docker exec unicorn-postgresql psql -U postgres -c "CREATE DATABASE brigade;"
```

### Step 3: Start Services

```bash
# Using the configured environment file
docker compose -f docker-compose.brigade.yml --env-file .env.brigade.local up -d
```

### Step 4: Verify Installation

```bash
# Check container status
docker ps | grep unicorn-brigade

# View logs
docker logs unicorn-brigade -f

# Test API
curl http://localhost:8112/health

# Test UI
curl http://localhost:8102
```

## 🌐 Access Points

### Local Development
- **API**: http://localhost:8112
- **Web UI**: http://localhost:8102
- **Ops-Center Integration**: http://localhost:8084/admin/brigade

### Production (with Traefik)
- **Brigade UI**: https://brigade.your-domain.com
- **Brigade API**: https://brigade.your-domain.com/api
- **Ops-Center Menu**: https://ops.your-domain.com/admin/brigade

## 🔧 Configuration

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Brigade API | 8112 | REST API endpoints |
| Brigade UI | 8102 | Web interface |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRIGADE_LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `BRIGADE_MAX_AGENTS` | `47` | Maximum number of agents |
| `BRIGADE_ENABLE_GUNNY` | `true` | Enable Gunny conversational agent builder |
| `BRIGADE_SECRET_KEY` | - | Secret key for sessions (required) |
| `ANTHROPIC_API_KEY` | - | Anthropic API key for Claude models |
| `OPENAI_API_KEY` | - | OpenAI API key for GPT models |
| `GROQ_API_KEY` | - | Groq API key for fast inference |

### Advanced Configuration

```bash
# Rate Limiting
BRIGADE_RATE_LIMIT_ENABLED=true
BRIGADE_RATE_LIMIT_REQUESTS=100
BRIGADE_RATE_LIMIT_PERIOD=60

# Memory Management
BRIGADE_MAX_MEMORY_MB=4096
BRIGADE_CACHE_SIZE=1000

# Agent Configuration
BRIGADE_AGENT_TIMEOUT=300
BRIGADE_MAX_CONCURRENT_TASKS=10
```

## 🐳 Docker Networks

Brigade connects to three networks:
- **web** - Traefik reverse proxy
- **unicorn-network** - Internal services (PostgreSQL, Redis)
- **uchub-network** - Authentication (Keycloak/Authentik)

Ensure these networks exist:
```bash
docker network create web
docker network create unicorn-network
docker network create uchub-network
```

## 🔐 Security Setup

### 1. Generate Secret Key

```bash
# Generate a random secret key
openssl rand -hex 32
# Add to .env.brigade as BRIGADE_SECRET_KEY
```

### 2. Configure CORS (if needed)

```bash
BRIGADE_CORS_ENABLED=false  # Enable only for development
BRIGADE_CORS_ORIGINS=http://localhost:8084,http://localhost:5173
```

### 3. Session Management

```bash
BRIGADE_SESSION_TIMEOUT=3600  # 1 hour
BRIGADE_SESSION_COOKIE_SECURE=true  # HTTPS only
```

## 📊 Integration with Ops-Center

Brigade is integrated into Ops-Center through:

1. **Menu Item**: 🦄 Unicorn Brigade in main navigation
2. **Embedded Dashboard**: iframe integration in Brigade.jsx
3. **API Proxy**: `/api/v1/brigade/*` endpoints
4. **Service Discovery**: Automatic URL resolution

### Accessing from Ops-Center

Navigate to the Brigade menu item in Ops-Center to:
- View usage statistics
- Execute agent tasks
- Access the full Brigade UI
- Monitor task history

## 🔍 Troubleshooting

### Brigade Container Won't Start

```bash
# Check logs
docker logs unicorn-brigade --tail 100

# Common issues:
# 1. Database not available
docker ps | grep unicorn-postgresql

# 2. Redis not available
docker ps | grep unicorn-redis

# 3. Missing API keys
docker exec unicorn-brigade env | grep API_KEY
```

### API Not Responding

```bash
# Check health endpoint
curl -v http://localhost:8112/health

# Verify container is running
docker ps | grep unicorn-brigade

# Check network connectivity
docker exec unicorn-brigade ping ops-center-direct
```

### Database Connection Issues

```bash
# Test database connection
docker exec unicorn-brigade psql "postgresql://postgres:postgres@unicorn-postgresql:5432/brigade" -c "SELECT 1;"

# Check database exists
docker exec unicorn-postgresql psql -U postgres -l | grep brigade
```

### UI Not Loading

```bash
# Check UI port
curl -I http://localhost:8102

# Check Traefik routing (production)
docker logs traefik | grep brigade

# Verify domain DNS
dig brigade.your-domain.com
```

## 📚 Common Commands

### Start/Stop/Restart

```bash
# Start Brigade
docker compose -f docker-compose.brigade.yml up -d

# Stop Brigade
docker compose -f docker-compose.brigade.yml down

# Restart Brigade
docker compose -f docker-compose.brigade.yml restart

# View status
docker compose -f docker-compose.brigade.yml ps
```

### Logs and Monitoring

```bash
# Follow logs
docker logs unicorn-brigade -f

# Last 100 lines
docker logs unicorn-brigade --tail 100

# Search logs
docker logs unicorn-brigade 2>&1 | grep ERROR

# Container stats
docker stats unicorn-brigade
```

### Database Management

```bash
# Access Brigade database
docker exec -it unicorn-postgresql psql -U postgres -d brigade

# Backup database
docker exec unicorn-postgresql pg_dump -U postgres brigade > brigade_backup.sql

# Restore database
cat brigade_backup.sql | docker exec -i unicorn-postgresql psql -U postgres -d brigade
```

### Updates and Maintenance

```bash
# Pull latest image
docker pull brigade-ai:latest

# Rebuild from source
docker compose -f docker-compose.brigade.yml build --no-cache

# Recreate container
docker compose -f docker-compose.brigade.yml up -d --force-recreate
```

## 🌟 Usage Examples

### Execute Agent Task via API

```bash
curl -X POST http://localhost:8112/api/v1/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "research",
    "task": "Research the latest developments in quantum computing"
  }'
```

### Get Usage Statistics

```bash
curl http://localhost:8112/api/v1/agents/usage
```

### List Available Agents

```bash
curl http://localhost:8112/api/v1/agents
```

## 🔗 Related Documentation

- **Ops-Center Integration**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **API Documentation**: http://localhost:8112/docs (when running)
- **Service Discovery**: [backend/service_discovery.py](backend/service_discovery.py)
- **Brigade API Proxy**: [backend/brigade_api.py](backend/brigade_api.py)

## 💡 Tips & Best Practices

1. **API Keys**: Store sensitive keys in `.env.brigade.local` (gitignored)
2. **Production**: Always use HTTPS with valid SSL certificates
3. **Monitoring**: Enable health checks and monitor logs regularly
4. **Resources**: Allocate sufficient memory (4GB+ recommended)
5. **Backups**: Regularly backup the Brigade database
6. **Updates**: Keep Brigade image up to date for security patches

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker logs unicorn-brigade -f`
2. Verify configuration: Review `.env.brigade`
3. Test connectivity: `curl http://localhost:8112/health`
4. Check dependencies: PostgreSQL and Redis must be running
5. Review documentation in `docs/` directory

## 📝 Version Information

- Brigade API Port: 8112
- Brigade UI Port: 8102
- Default Agents: 47+
- Supported LLM Providers: Anthropic, OpenAI, Groq, OpenRouter
- Database: PostgreSQL 15+
- Cache: Redis 7+

---

**Last Updated**: February 8, 2026  
**Maintainer**: Ops-Center Development Team
