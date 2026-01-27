# High Availability Architecture - Epic 17
# Ops-Center OSS Enterprise-Grade HA Design

## Overview

This document outlines the High Availability (HA) architecture for Ops-Center OSS, designed to provide:
- **99.9% uptime SLA** (8.76 hours downtime/year)
- **Zero-downtime deployments** via blue-green strategy
- **Automatic failover** for all critical services
- **Multi-region disaster recovery** with RPO < 5 minutes
- **Horizontal scalability** for all stateless components

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Global Load Balancer                        │
│                    (Traefik / CloudFlare)                        │
│                  Health checks every 5s                          │
└────────────┬───────────────────────────┬────────────────────────┘
             │                           │
      ┌──────▼──────┐            ┌──────▼──────┐
      │  Region 1   │            │  Region 2   │
      │  (Primary)  │◄───────────►│  (Standby) │
      └─────────────┘   Sync      └─────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼───┐
│Frontend│      │Backend │
│  x3    │      │  x3    │
│Replicas│      │Replicas│
└────────┘      └────────┘
```

## Component Availability

### 1. Frontend (React SPA)
**Target: 99.9% uptime**

Strategy:
- Deploy 3 replicas with anti-affinity
- Nginx reverse proxy with round-robin
- Static asset caching via CDN (optional)
- Session persistence via Redis

Configuration:
```yaml
# docker-compose.ha.yml
frontend:
  image: kubeworkz/ops_center:frontend
  deploy:
    replicas: 3
    restart_policy:
      condition: on-failure
      max_attempts: 3
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
      reservations:
        cpus: '0.25'
        memory: 256M
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:80/health"]
    interval: 10s
    timeout: 3s
    retries: 3
    start_period: 30s
```

### 2. Backend (FastAPI)
**Target: 99.95% uptime**

Strategy:
- Deploy 3 replicas with sticky sessions
- Circuit breaker for external dependencies
- Graceful shutdown with 30s drain period
- Auto-scaling based on CPU (threshold: 70%)

Configuration:
```yaml
backend:
  image: kubeworkz/ops_center:backend
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 30s
      order: start-first  # Blue-green deployment
    restart_policy:
      condition: on-failure
      max_attempts: 5
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 60s
  environment:
    - GRACEFUL_SHUTDOWN_TIMEOUT=30
```

### 3. PostgreSQL (Primary Database)
**Target: 99.99% uptime**

Strategy:
- PostgreSQL 16 with streaming replication
- Primary-Standby setup with automatic failover
- Point-in-time recovery (PITR) enabled
- Daily backups with 30-day retention

Configuration:
```yaml
# Primary
postgresql-primary:
  image: postgres:16-alpine
  command: >
    postgres
    -c wal_level=replica
    -c max_wal_senders=10
    -c max_replication_slots=10
    -c hot_standby=on
    -c synchronous_commit=on
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - postgres_wal:/var/lib/postgresql/wal
  environment:
    POSTGRES_REPLICATION_MODE: master
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U unicorn"]
    interval: 10s
    timeout: 5s
    retries: 5

# Standby (Hot Standby for read queries + failover)
postgresql-standby:
  image: postgres:16-alpine
  command: >
    postgres
    -c hot_standby=on
  environment:
    POSTGRES_REPLICATION_MODE: slave
    POSTGRES_MASTER_HOST: postgresql-primary
    POSTGRES_MASTER_PORT: 5432
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
  depends_on:
    - postgresql-primary
```

Failover Script (Patroni Alternative):
```bash
#!/bin/bash
# scripts/postgres_failover.sh

PRIMARY_HOST="postgresql-primary"
STANDBY_HOST="postgresql-standby"
HEALTH_CHECK_INTERVAL=5

check_primary() {
  docker exec postgresql-primary pg_isready -U unicorn > /dev/null 2>&1
  return $?
}

promote_standby() {
  echo "Primary is down. Promoting standby..."
  docker exec postgresql-standby pg_ctl promote -D /var/lib/postgresql/data
  
  # Update Traefik to point to new primary
  docker exec ops-center-traefik \
    traefik config set --entryPoint=postgres --address=$STANDBY_HOST:5432
  
  echo "Failover complete. Standby is now primary."
}

while true; do
  if ! check_primary; then
    echo "Primary health check failed."
    sleep 10
    if ! check_primary; then
      promote_standby
      exit 0
    fi
  fi
  sleep $HEALTH_CHECK_INTERVAL
done
```

### 4. Redis (Cache & Session Store)
**Target: 99.9% uptime**

Strategy:
- Redis Sentinel for automatic failover
- 1 master + 2 replicas + 3 sentinels
- AOF persistence for durability
- Connection pooling in backend

Configuration:
```yaml
redis-master:
  image: redis:7-alpine
  command: >
    redis-server
    --appendonly yes
    --appendfsync everysec
    --save 900 1
    --save 300 10
  volumes:
    - redis_master_data:/data

redis-replica-1:
  image: redis:7-alpine
  command: redis-server --replicaof redis-master 6379
  depends_on:
    - redis-master

redis-replica-2:
  image: redis:7-alpine
  command: redis-server --replicaof redis-master 6379
  depends_on:
    - redis-master

redis-sentinel-1:
  image: redis:7-alpine
  command: >
    redis-sentinel /etc/redis/sentinel.conf
    --sentinel monitor mymaster redis-master 6379 2
    --sentinel down-after-milliseconds mymaster 5000
    --sentinel parallel-syncs mymaster 1
    --sentinel failover-timeout mymaster 10000
```

### 5. Traefik (Load Balancer & Reverse Proxy)
**Target: 99.99% uptime**

Strategy:
- 2 Traefik instances (active-active)
- Keepalived for VIP failover
- Let's Encrypt with HTTP-01 challenge
- Circuit breaker for unhealthy backends

Configuration:
```yaml
traefik-1:
  image: traefik:v3.0
  command:
    - --api.dashboard=true
    - --providers.docker=true
    - --providers.docker.swarmMode=true
    - --entrypoints.web.address=:80
    - --entrypoints.websecure.address=:443
    - --certificatesresolvers.letsencrypt.acme.httpchallenge=true
    - --certificatesresolvers.letsencrypt.acme.email=admin@example.com
    - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
    - --metrics.prometheus=true
    - --log.level=INFO
    - --accesslog=true
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - traefik_certs:/letsencrypt
  healthcheck:
    test: ["CMD", "traefik", "healthcheck", "--ping"]
    interval: 10s
    timeout: 3s
    retries: 3

traefik-2:
  # Identical to traefik-1
```

Keepalived VIP:
```bash
# /etc/keepalived/keepalived.conf
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 101
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass SuperSecretPassword
    }
    virtual_ipaddress {
        192.168.1.100/24
    }
}
```

## Monitoring & Alerting

### Health Check Endpoints

1. **Backend Health** (`/health`)
```python
# backend/health_check.py
@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # PostgreSQL
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["checks"]["postgres"] = "healthy"
    except:
        checks["checks"]["postgres"] = "unhealthy"
        checks["status"] = "unhealthy"
    
    # Redis
    try:
        await redis_client.ping()
        checks["checks"]["redis"] = "healthy"
    except:
        checks["checks"]["redis"] = "unhealthy"
        checks["status"] = "unhealthy"
    
    return checks
```

2. **Readiness Check** (`/ready`)
```python
@app.get("/ready")
async def readiness_check():
    """Check if service is ready to accept traffic"""
    # Wait for migrations
    if not await migrations_complete():
        raise HTTPException(503, "Migrations in progress")
    
    # Check database connection pool
    if db_pool.get_size() < 2:
        raise HTTPException(503, "Database pool not ready")
    
    return {"status": "ready"}
```

### Prometheus Metrics

```python
# backend/metrics.py
from prometheus_client import Counter, Histogram, Gauge

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)
```

### Alerting Rules (Prometheus)

```yaml
# prometheus/alerts.yml
groups:
  - name: ops_center_ha
    interval: 30s
    rules:
      - alert: BackendDown
        expr: up{job="backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Backend instance down"
          description: "Backend {{ $labels.instance }} has been down for 1 minute"
      
      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_active > 8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near limit"
      
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High HTTP error rate detected"
```

## Deployment Strategy

### Blue-Green Deployment

```bash
#!/bin/bash
# scripts/deploy_blue_green.sh

GREEN_STACK="ops-center-green"
BLUE_STACK="ops-center-blue"
ACTIVE_STACK=$(docker stack ls | grep "ops-center-" | grep "active" | awk '{print $1}')

echo "Current active stack: $ACTIVE_STACK"

# Deploy new version to inactive stack
if [[ "$ACTIVE_STACK" == "$BLUE_STACK" ]]; then
  NEW_STACK=$GREEN_STACK
else
  NEW_STACK=$BLUE_STACK
fi

echo "Deploying to $NEW_STACK..."
docker stack deploy -c docker-compose.ha.yml $NEW_STACK

# Wait for health checks
echo "Waiting for services to be healthy..."
sleep 60

# Check health
HEALTH=$(docker service ps ${NEW_STACK}_backend --format "{{.CurrentState}}" | grep -c Running)
REPLICAS=$(docker service ls --filter "name=${NEW_STACK}_backend" --format "{{.Replicas}}")

if [[ "$HEALTH" -eq 3 ]] && [[ "$REPLICAS" == "3/3" ]]; then
  echo "New stack is healthy. Switching traffic..."
  
  # Update Traefik to point to new stack
  docker service update --label-add traefik.docker.network=active ${NEW_STACK}_backend
  docker service update --label-rm traefik.docker.network ${ACTIVE_STACK}_backend
  
  # Wait for traffic drain
  sleep 30
  
  # Remove old stack
  echo "Removing old stack: $ACTIVE_STACK"
  docker stack rm $ACTIVE_STACK
  
  echo "Deployment complete!"
else
  echo "Health check failed. Rolling back..."
  docker stack rm $NEW_STACK
  exit 1
fi
```

## Disaster Recovery

### Backup Strategy

1. **PostgreSQL**
   - Daily full backups (pg_dump)
   - Continuous WAL archiving to S3
   - Retention: 30 days
   - RPO: 5 minutes (WAL replay)

```bash
#!/bin/bash
# scripts/backup_postgres.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="postgres_backup_${TIMESTAMP}.sql.gz"

docker exec postgresql-primary pg_dump -U unicorn unicorn_db | gzip > /backups/${BACKUP_FILE}

# Upload to S3
aws s3 cp /backups/${BACKUP_FILE} s3://ops-center-backups/postgres/

# WAL archiving
docker exec postgresql-primary bash -c "
  tar -czf - /var/lib/postgresql/wal/*.wal |
  aws s3 cp - s3://ops-center-backups/wal/wal_${TIMESTAMP}.tar.gz
"
```

2. **Redis**
   - AOF persistence
   - RDB snapshots every 15 minutes
   - S3 sync every hour

3. **Configuration**
   - Git repository with all configs
   - Encrypted secrets in Vault/AWS Secrets Manager

### Recovery Procedures

**RTO Target: 15 minutes**

1. **Database Recovery**
```bash
# Restore from backup
LATEST_BACKUP=$(aws s3 ls s3://ops-center-backups/postgres/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://ops-center-backups/postgres/${LATEST_BACKUP} /tmp/
gunzip /tmp/${LATEST_BACKUP}
docker exec -i postgresql-primary psql -U unicorn < /tmp/${LATEST_BACKUP%.gz}

# Apply WAL logs for PITR
# ... (WAL replay procedure)
```

2. **Full Site Recovery**
```bash
#!/bin/bash
# scripts/disaster_recovery.sh

# 1. Provision new infrastructure
terraform apply -auto-approve

# 2. Restore database
./scripts/restore_postgres.sh

# 3. Restore Redis
docker run -v redis_data:/data -v /backups:/backups redis:7-alpine \
  redis-cli --rdb /backups/latest.rdb

# 4. Deploy application stack
docker stack deploy -c docker-compose.ha.yml ops-center

# 5. Verify health
./scripts/health_check_all.sh
```

## Scaling Configuration

### Horizontal Scaling

Auto-scaling rules:
```yaml
# docker-compose.ha.yml
backend:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: '2'
        memory: 2G
    restart_policy:
      condition: on-failure
    # Note: For true auto-scaling, migrate to Kubernetes
```

### Vertical Scaling

Resource allocation per component:
- **Frontend**: 0.5 CPU, 512 MB RAM (per replica)
- **Backend**: 2 CPU, 2 GB RAM (per replica)
- **PostgreSQL Primary**: 4 CPU, 8 GB RAM
- **PostgreSQL Standby**: 2 CPU, 4 GB RAM
- **Redis Master**: 1 CPU, 2 GB RAM
- **Traefik**: 1 CPU, 1 GB RAM

## Multi-Region Architecture

### Active-Passive Configuration

```
Region 1 (us-east-1) - ACTIVE
├── Backend x3
├── Frontend x3
├── PostgreSQL Primary
├── Redis Master
└── Traefik x2

Region 2 (us-west-2) - STANDBY
├── Backend x1 (cold standby)
├── Frontend x1 (cold standby)
├── PostgreSQL Standby (replicating)
├── Redis Replica (replicating)
└── Traefik x1 (monitoring primary)

Global DNS:
- Route53 with health checks
- Failover to Region 2 if Region 1 unhealthy
- TTL: 60 seconds
```

### Cross-Region Replication

```yaml
# docker-compose.region1.yml
postgresql:
  environment:
    POSTGRES_REPLICATION_HOSTS: postgresql-region2.example.com

# docker-compose.region2.yml
postgresql:
  command: >
    postgres
    -c hot_standby=on
  environment:
    POSTGRES_MASTER_HOST: postgresql-region1.example.com
```

## Cost Estimation

**Monthly costs for HA setup:**
- Compute (6 backend, 6 frontend, 2 DB, 4 Redis, 4 Traefik): ~$800/month
- Storage (PostgreSQL data + backups + WAL): ~$100/month
- Bandwidth (multi-region replication): ~$50/month
- **Total: ~$950/month** for 99.9% uptime

## Implementation Checklist

- [x] PostgreSQL streaming replication
- [x] Redis Sentinel setup
- [x] Traefik health checks
- [x] Prometheus monitoring
- [x] Alertmanager notifications
- [x] Blue-green deployment scripts
- [x] Backup automation
- [x] Disaster recovery procedures
- [ ] Multi-region DNS failover
- [ ] Kubernetes migration (future)
- [ ] Chaos engineering tests (future)

## Next Steps

1. **Immediate (Week 1)**
   - Implement PostgreSQL replication
   - Set up Redis Sentinel
   - Configure health checks

2. **Short-term (Month 1)**
   - Deploy Prometheus + Grafana
   - Implement blue-green deployments
   - Set up automated backups

3. **Long-term (Quarter 1)**
   - Multi-region setup
   - Kubernetes migration
   - Chaos engineering
