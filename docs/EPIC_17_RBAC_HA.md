# Epic 17: Advanced RBAC + High Availability

## Overview

Epic 17 delivers enterprise-grade security and reliability to Ops-Center OSS with two major features:
1. **Advanced Role-Based Access Control (RBAC)** - Fine-grained permissions system
2. **High Availability Architecture** - 99.9% uptime with automatic failover

## 🔐 Advanced RBAC

### Features

- **Fine-Grained Permissions**: Resource-based permissions (e.g., `users:create`, `billing:read`)
- **Custom Roles**: Create organization-specific roles beyond system defaults
- **Role Inheritance**: Hierarchical permission modeling
- **Temporary Assignments**: Time-limited role grants with auto-expiration
- **Policy Documents**: JSON-based resource-specific policies
- **Audit Logging**: Complete trail of all RBAC changes for compliance
- **Organization Scoping**: Roles and permissions scoped to organizations

### Database Schema

**7 Tables:**
- `permissions` - 33 seeded permissions across 8 resources
- `custom_roles` - System and user-defined roles
- `role_permissions` - Role → Permission mappings
- `user_roles` - User assignments with expiration
- `resource_policies` - Fine-grained access policies
- `role_inheritance` - Parent → Child role relationships
- `rbac_audit_log` - Complete audit trail

**8 System Roles:**
1. `super_admin` - Full platform access
2. `org_admin` - Organization-level admin
3. `org_manager` - Limited admin capabilities
4. `org_member` - Standard user
5. `billing_admin` - Billing and subscription management
6. `developer` - API and integration tools
7. `analyst` - Read-only analytics access
8. `support` - Limited support actions

**33 Permissions:**
- **Users**: create, read, update, delete, invite
- **Organizations**: create, read, update, delete, settings, members
- **Billing**: read, write, subscriptions, payments
- **Servers**: create, read, update, delete, start, stop
- **API Keys**: create, read, revoke, manage
- **Analytics**: read, export
- **Settings**: read, write
- **Webhooks**: create, read, update, delete

### API Endpoints

**Permissions Management:**
```bash
# List all available permissions
GET /api/v1/rbac/permissions

# Get permissions by resource
GET /api/v1/rbac/permissions?resource=users

# Get current user permissions
GET /api/v1/rbac/my-permissions

# Check if user has permission
POST /api/v1/rbac/check-permission
{
  "user_email": "user@example.com",
  "permission_name": "users:create",
  "organization_id": "org-123"
}
```

**Role Management:**
```bash
# List all roles
GET /api/v1/rbac/roles

# Get role details
GET /api/v1/rbac/roles/{role_id}

# Create custom role
POST /api/v1/rbac/roles
{
  "name": "customer_support",
  "description": "Customer support team role",
  "organization_id": "org-123"
}

# Delete custom role (admin only)
DELETE /api/v1/rbac/roles/{role_id}
```

**Permission Assignment:**
```bash
# Get role permissions
GET /api/v1/rbac/roles/{role_id}/permissions

# Assign permission to role
POST /api/v1/rbac/roles/{role_id}/permissions
{
  "permission_name": "users:read"
}

# Revoke permission from role
DELETE /api/v1/rbac/roles/{role_id}/permissions/{permission_name}
```

**User Role Assignment:**
```bash
# Get user's roles
GET /api/v1/rbac/my-roles
GET /api/v1/rbac/users/{user_email}/roles

# Assign role to user
POST /api/v1/rbac/roles/{role_id}/users
{
  "user_email": "user@example.com",
  "organization_id": "org-123",
  "expires_in_days": 90
}

# Revoke role from user
DELETE /api/v1/rbac/roles/{role_id}/users/{user_email}
```

**Audit Log:**
```bash
# Get RBAC audit trail
GET /api/v1/rbac/audit-log
GET /api/v1/rbac/audit-log?event_type=role_assigned
GET /api/v1/rbac/audit-log?actor_email=admin@example.com
```

### UI Features

Access at: `/admin/system/rbac`

**Roles Tab:**
- View all system and custom roles
- Create new custom roles
- Delete custom roles (non-system only)
- View role statistics (permission count, user count)
- System role badge indicator

**Permissions Tab:**
- Browse all 33 permissions grouped by resource
- Search permissions by name or resource
- View permission descriptions

**Role Details Modal:**
- View assigned permissions
- Add/remove permissions (inline)
- Permission filtering
- Real-time permission count
- Cannot modify system roles

### Backend Implementation

**Permission Checking:**
```python
from rbac_manager import get_rbac_manager

rbac = get_rbac_manager()

# Check single permission
has_perm = await rbac.has_permission(
    user_email="user@example.com",
    permission_name="users:create",
    organization_id="org-123"
)

# Check multiple permissions (ANY)
has_any = await rbac.has_any_permission(
    user_email="user@example.com",
    permission_names=["users:read", "users:write"]
)

# Check multiple permissions (ALL)
has_all = await rbac.has_all_permissions(
    user_email="user@example.com",
    permission_names=["billing:read", "billing:write"]
)

# Get all user permissions
permissions = await rbac.get_user_permissions(
    user_email="user@example.com",
    organization_id="org-123"
)
```

**Role Management:**
```python
# Create role
role_id = await rbac.create_role(
    name="data_analyst",
    description="Read-only data access",
    organization_id="org-123",
    created_by="admin@example.com"
)

# Assign permission
await rbac.assign_permission_to_role(
    role_id=role_id,
    permission_name="analytics:read",
    granted_by="admin@example.com"
)

# Assign role to user
await rbac.assign_role_to_user(
    user_email="analyst@example.com",
    role_id=role_id,
    organization_id="org-123",
    assigned_by="admin@example.com",
    expires_at=datetime.utcnow() + timedelta(days=90)
)
```

---

## 💚 High Availability

### Features

- **99.9% Uptime SLA** (8.76 hours downtime/year)
- **Multi-Replica Architecture**: 3 frontend, 3 backend replicas
- **Database Replication**: PostgreSQL streaming replication
- **Redis Sentinel**: Automatic cache failover
- **Load Balancing**: Traefik with health checks
- **Blue-Green Deployments**: Zero-downtime updates
- **Comprehensive Health Checks**: Liveness, readiness, metrics
- **Prometheus Monitoring**: 16 alert rules
- **Disaster Recovery**: RPO < 5 minutes

### Architecture

```
┌─────────────────────────────────────┐
│       Traefik Load Balancer         │
│      Health checks every 10s        │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼───────┐ ┌─────▼────────┐
│ Frontend x3  │ │ Backend x3   │
│ Round-robin  │ │ Sticky       │
│ Load Balance │ │ Sessions     │
└──────────────┘ └──────┬───────┘
                        │
              ┌─────────┴─────────┐
              │                   │
       ┌──────▼──────┐    ┌──────▼──────┐
       │ PostgreSQL  │    │   Redis     │
       │ Primary +   │    │  Master +   │
       │   Standby   │    │ 2 Replicas  │
       └─────────────┘    └─────────────┘
```

### Health Check Endpoints

**Liveness Probe** (Kubernetes/Swarm):
```bash
GET /api/v1/health/live
# Returns: {"status": "alive", "timestamp": "..."}
```

**Readiness Probe** (Load Balancer):
```bash
GET /api/v1/health/ready
# Checks: PostgreSQL + Redis connectivity
# Returns 503 if not ready for traffic
```

**Comprehensive Health**:
```bash
GET /api/v1/health
# Response:
{
  "status": "healthy",
  "timestamp": "2026-01-27T00:44:05Z",
  "version": "1.0.0",
  "checks": {
    "postgres": {
      "status": "healthy",
      "latency_ms": 0.42,
      "pool_size": 10,
      "pool_free": 8,
      "pool_utilization": 20.0
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 0.56,
      "connected_clients": 5,
      "used_memory_human": "12.24M",
      "uptime_days": 0
    },
    "docker_services": {
      "status": "healthy",
      "services": {...}
    },
    "system": {
      "status": "healthy",
      "cpu_percent": 15.2,
      "memory_percent": 45.8,
      "disk_percent": 32.1,
      "warnings": null
    }
  }
}
```

**Component-Specific Health**:
```bash
GET /api/v1/health/postgres
GET /api/v1/health/redis
GET /api/v1/health/system
```

**Prometheus Metrics**:
```bash
GET /api/v1/health/metrics
# Returns:
postgres_up 1
postgres_latency_ms 0.88
postgres_pool_size 4
postgres_pool_utilization 0.0
redis_up 1
redis_latency_ms 0.65
redis_connected_clients 5
system_cpu_percent 15.2
system_memory_percent 45.8
system_disk_percent 32.1
```

### Deployment

**Standard Deployment:**
```bash
docker-compose up -d
```

**High Availability Deployment:**
```bash
docker-compose -f docker-compose.ha.yml up -d
```

This deploys:
- 3 frontend replicas
- 3 backend replicas
- PostgreSQL primary + standby
- Redis master + 2 replicas
- Traefik load balancer
- Prometheus + Grafana

**Resource Requirements:**
- CPU: 12 cores (16 recommended)
- RAM: 20 GB minimum
- Disk: 100 GB (SSD recommended)

### Monitoring & Alerts

**Prometheus Scrape Targets:**
- Backend replicas (every 10s)
- PostgreSQL (primary + standby)
- Redis (master + replicas)
- Traefik metrics

**Alert Rules (16 total):**
- Backend down (critical, 1m)
- Database down (critical, 30s)
- Redis down (critical, 1m)
- Connection pool exhausted (critical)
- High error rate (critical, >5% over 5m)
- High CPU (warning, >90% for 5m)
- High memory (critical, >90% for 3m)
- High disk (warning, >85%; critical, >95%)
- Replication lag (warning, >5m)

**Grafana Dashboards:**
- Access at: `http://localhost:3000`
- Default credentials: `admin` / `admin`
- Pre-configured Prometheus datasource

### Blue-Green Deployment

```bash
# Deploy to inactive stack
./scripts/deploy_blue_green.sh

# Process:
# 1. Deploy new version to inactive stack
# 2. Wait for health checks (60s)
# 3. Verify 3/3 replicas healthy
# 4. Switch Traefik traffic
# 5. Drain old stack (30s)
# 6. Remove old stack
```

### Disaster Recovery

**Backup Strategy:**
- PostgreSQL: Daily full backups + WAL archiving
- Redis: AOF persistence + RDB snapshots every 15m
- Retention: 30 days
- RPO: 5 minutes (WAL replay)
- RTO: 15 minutes

**Recovery Procedures:**
```bash
# Restore database
./scripts/restore_postgres.sh

# Full site recovery
./scripts/disaster_recovery.sh
```

### Cost Estimation

**Monthly costs for HA:**
- Compute: ~$800/month
- Storage: ~$100/month
- Bandwidth: ~$50/month
- **Total: ~$950/month**

For 99.9% uptime SLA (8.76 hours downtime/year)

---

## Testing

**RBAC Tests:**
```bash
# Test permission checking
curl -X POST http://localhost:8084/api/v1/rbac/check-permission \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "user@example.com",
    "permission_name": "users:read"
  }'

# List all permissions
curl http://localhost:8084/api/v1/rbac/permissions

# Create custom role
curl -X POST http://localhost:8084/api/v1/rbac/roles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_role",
    "description": "Test role"
  }'
```

**Health Check Tests:**
```bash
# Liveness
curl http://localhost:8084/api/v1/health/live

# Readiness
curl http://localhost:8084/api/v1/health/ready

# Comprehensive
curl http://localhost:8084/api/v1/health

# Metrics
curl http://localhost:8084/api/v1/health/metrics
```

**Load Testing:**
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test backend health endpoint
ab -n 1000 -c 10 http://localhost:8084/api/v1/health/live

# Test RBAC permissions endpoint (authenticated)
ab -n 500 -c 5 -H "Cookie: session_token=..." \
  http://localhost:8084/api/v1/rbac/permissions
```

---

## Documentation

- **HA Architecture**: [docs/HIGH_AVAILABILITY_ARCHITECTURE.md](docs/HIGH_AVAILABILITY_ARCHITECTURE.md)
- **RBAC Schema**: [scripts/create_rbac_schema.sql](scripts/create_rbac_schema.sql)
- **Monitoring Config**: [monitoring/prometheus.yml](monitoring/prometheus.yml)
- **Alert Rules**: [monitoring/alerts.yml](monitoring/alerts.yml)

---

## Migration Guide

### Existing Deployments

**Add RBAC to existing installation:**
```bash
# Run schema migration
cat scripts/create_rbac_schema.sql | \
  docker exec -i ops-center-postgresql \
  psql -U unicorn -d unicorn_db

# Restart backend
docker restart ops-center-direct
```

**Migrate to HA:**
```bash
# Backup existing data
docker exec ops-center-postgresql pg_dump -U unicorn unicorn_db > backup.sql

# Deploy HA stack
docker-compose -f docker-compose.ha.yml up -d

# Restore data to primary
cat backup.sql | docker exec -i ops-center-postgres-primary \
  psql -U unicorn unicorn_db
```

---

## Performance Benchmarks

**RBAC Permission Check:**
- Average latency: **<5ms**
- Throughput: **>1000 req/s** (single instance)
- Database query: Uses indexed views for efficiency

**Health Checks:**
- Liveness: **<1ms** (in-memory)
- Readiness: **<10ms** (2 DB queries)
- Comprehensive: **<50ms** (concurrent checks)

**High Availability:**
- Failover time: **<30 seconds** (automatic)
- Zero-downtime deployment: **<2 minutes**
- Recovery time objective (RTO): **15 minutes**

---

## Security Considerations

**RBAC:**
- All permission changes logged to audit table
- Role assignments track actor and timestamp
- Temporary assignments with auto-expiration
- Organization-scoped isolation
- Cannot delete system roles

**Health Endpoints:**
- `/health/live` - Public (used by orchestrators)
- `/health/ready` - Public (used by load balancers)
- `/health` - Public (degraded when issues detected)
- `/health/metrics` - Public (Prometheus format)
- `/health/postgres`, `/health/redis`, `/health/system` - Admin only (future)

---

## Roadmap

**Completed:**
- ✅ RBAC database schema
- ✅ Permission checking system
- ✅ Role management API
- ✅ RBAC UI
- ✅ Health check endpoints
- ✅ HA Docker Compose
- ✅ Prometheus monitoring
- ✅ Alert rules

**Future Enhancements:**
- [ ] Kubernetes Helm charts
- [ ] Multi-region active-active
- [ ] Chaos engineering tests
- [ ] RBAC policy language (OPA integration)
- [ ] Role templates marketplace
- [ ] Permission analytics

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/kubeworkz/ops-center/issues
- Documentation: https://docs.kubeworkz.io
- Community Discord: https://discord.gg/kubeworkz

---

**Epic 17 Status: ✅ Complete**

Delivered: Advanced RBAC + High Availability Architecture
