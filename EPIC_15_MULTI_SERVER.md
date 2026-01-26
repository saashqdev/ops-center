# Epic 15: Multi-Server Management - Fleet Dashboard

**Phase:** 3 - Scale  
**Status:** In Specification  
**Priority:** High  
**Estimated Effort:** 4-6 weeks  
**Target Release:** v3.3

---

## 🎯 Executive Summary

Epic 15 enables Ops-Center to manage multiple server instances from a single control plane. This transforms Ops-Center from a single-server management tool into a fleet orchestration platform capable of managing dozens or hundreds of distributed servers.

**Key Capabilities:**
- Register and manage multiple Ops-Center servers
- Unified fleet dashboard with cross-server metrics
- Server grouping, tagging, and filtering
- Bulk operations across server groups
- Health monitoring and alerting for the entire fleet
- Cross-server resource aggregation

**Business Value:**
- Enables enterprise customers with distributed infrastructure
- Reduces operational overhead for multi-region deployments
- Foundation for multi-server orchestration (Colonel v2)
- Enables managed service provider use cases

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│               Primary Ops-Center (Control Plane)            │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Fleet        │───▶│  Server      │───▶│  Metrics     │  │
│  │ Dashboard UI │    │  Manager API │    │  Aggregator  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                              │                               │
│                      ┌───────┴────────┐                     │
│                      │   PostgreSQL    │                     │
│                      │  - servers      │                     │
│                      │  - server_groups│                     │
│                      │  - metrics_agg  │                     │
│                      └─────────────────┘                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┬──────────────┐
         │                │                │              │
         │ HTTPS          │ HTTPS          │ HTTPS        │
         │                │                │              │
    ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐   ┌────▼─────┐
    │ Server 1 │    │ Server 2 │    │ Server 3 │   │ Server N │
    │ us-east  │    │ us-west  │    │ eu-west  │   │ ap-south │
    │          │    │          │    │          │   │          │
    │ ┌──────┐ │    │ ┌──────┐ │    │ ┌──────┐ │   │ ┌──────┐ │
    │ │Agent │ │    │ │Agent │ │    │ │Agent │ │   │ │Agent │ │
    │ │API   │ │    │ │API   │ │    │ │API   │ │   │ │API   │ │
    │ └──────┘ │    │ └──────┘ │    │ └──────┘ │   │ └──────┘ │
    └──────────┘    └──────────┘    └──────────┘   └──────────┘
```

### Communication Model

**Pull-based Architecture:**
- Control plane polls managed servers for metrics
- Reduces complexity (no reverse tunnels)
- Each server exposes health/metrics API endpoint
- Authentication via API tokens

**Data Flow:**
1. Control plane discovers servers via registration
2. Periodic health checks (30s interval)
3. Metrics collection (configurable: 1m, 5m, 15m)
4. Aggregation and storage in control plane DB
5. Real-time display in fleet dashboard

---

## 📊 Database Schema

### Core Tables

```sql
-- Registered servers
CREATE TABLE managed_servers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    hostname VARCHAR(255) NOT NULL,
    api_url VARCHAR(512) NOT NULL,
    api_token_hash VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    region VARCHAR(100),
    environment VARCHAR(50), -- production, staging, development
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, inactive, unreachable, maintenance
    health_status VARCHAR(50), -- healthy, degraded, critical, unknown
    last_seen_at TIMESTAMPTZ,
    last_health_check_at TIMESTAMPTZ,
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Organization (multi-tenant)
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_managed_servers_org ON managed_servers(organization_id);
CREATE INDEX idx_managed_servers_status ON managed_servers(status);
CREATE INDEX idx_managed_servers_health ON managed_servers(health_status);
CREATE INDEX idx_managed_servers_region ON managed_servers(region);
CREATE INDEX idx_managed_servers_tags ON managed_servers USING GIN(tags);

-- Server groups for logical organization
CREATE TABLE server_groups (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7), -- Hex color for UI
    
    -- Filter criteria
    tags JSONB DEFAULT '[]',
    regions JSONB DEFAULT '[]',
    environments JSONB DEFAULT '[]',
    
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Many-to-many: servers can be in multiple groups
CREATE TABLE server_group_members (
    server_id VARCHAR(36) REFERENCES managed_servers(id) ON DELETE CASCADE,
    group_id VARCHAR(36) REFERENCES server_groups(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (server_id, group_id)
);

-- Aggregated metrics across time
CREATE TABLE server_metrics_aggregated (
    id BIGSERIAL PRIMARY KEY,
    server_id VARCHAR(36) REFERENCES managed_servers(id) ON DELETE CASCADE,
    
    timestamp TIMESTAMPTZ NOT NULL,
    period VARCHAR(20) NOT NULL, -- 1m, 5m, 15m, 1h, 1d
    
    -- Resource metrics
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    disk_percent DECIMAL(5,2),
    network_rx_bytes BIGINT,
    network_tx_bytes BIGINT,
    
    -- Service metrics
    active_services INTEGER,
    failed_services INTEGER,
    total_services INTEGER,
    
    -- LLM metrics
    llm_requests BIGINT,
    llm_cost_usd DECIMAL(10,2),
    
    -- User metrics
    active_users INTEGER,
    total_users INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

CREATE INDEX idx_server_metrics_server_time ON server_metrics_aggregated(server_id, timestamp DESC);
CREATE INDEX idx_server_metrics_period ON server_metrics_aggregated(period, timestamp DESC);

-- Create monthly partitions (example for 2026)
CREATE TABLE server_metrics_aggregated_2026_01 PARTITION OF server_metrics_aggregated
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE server_metrics_aggregated_2026_02 PARTITION OF server_metrics_aggregated
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
-- ... (continue for all months)

-- Health check results
CREATE TABLE server_health_checks (
    id BIGSERIAL PRIMARY KEY,
    server_id VARCHAR(36) REFERENCES managed_servers(id) ON DELETE CASCADE,
    
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Health status
    status VARCHAR(50), -- healthy, degraded, critical, unreachable
    response_time_ms INTEGER,
    
    -- Component health
    database_healthy BOOLEAN,
    redis_healthy BOOLEAN,
    services_healthy BOOLEAN,
    
    -- Error details
    error_message TEXT,
    error_details JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Audit log for bulk operations
CREATE TABLE fleet_operations (
    id VARCHAR(36) PRIMARY KEY,
    operation_type VARCHAR(100) NOT NULL, -- restart_services, update_config, deploy_update
    
    -- Target scope
    server_ids JSONB, -- Array of server IDs
    group_ids JSONB, -- Array of group IDs
    filter_criteria JSONB, -- Tags, regions, etc.
    
    -- Operation details
    parameters JSONB,
    initiated_by VARCHAR(36) REFERENCES users(id),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, partial
    total_servers INTEGER,
    completed_servers INTEGER,
    failed_servers INTEGER,
    
    -- Results
    results JSONB, -- Per-server results
    error_summary TEXT,
    
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fleet_ops_status ON fleet_operations(status, created_at DESC);
CREATE INDEX idx_fleet_ops_initiated_by ON fleet_operations(initiated_by, created_at DESC);
```

---

## 🔌 Backend API

### Server Manager (`backend/multi_server_manager.py`)

```python
class MultiServerManager:
    """Manages fleet of Ops-Center servers"""
    
    # Registration
    async def register_server(
        self, 
        name: str,
        api_url: str,
        api_token: str,
        organization_id: str,
        region: Optional[str] = None,
        environment: str = "production",
        tags: List[str] = [],
        metadata: dict = {}
    ) -> Server
    
    async def update_server(
        self, 
        server_id: str, 
        updates: dict
    ) -> Server
    
    async def delete_server(self, server_id: str) -> bool
    
    # Discovery & Health
    async def check_server_health(self, server_id: str) -> HealthStatus
    async def check_all_servers_health(self, organization_id: str) -> List[HealthStatus]
    async def get_server_info(self, server_id: str) -> ServerInfo
    
    # Metrics Collection
    async def collect_server_metrics(
        self, 
        server_id: str
    ) -> ServerMetrics
    
    async def aggregate_metrics(
        self, 
        server_ids: List[str],
        period: str = "1h"
    ) -> AggregatedMetrics
    
    # Groups
    async def create_group(
        self, 
        name: str, 
        filters: dict,
        organization_id: str
    ) -> ServerGroup
    
    async def add_server_to_group(
        self, 
        server_id: str, 
        group_id: str
    ) -> bool
    
    async def get_group_servers(
        self, 
        group_id: str
    ) -> List[Server]
    
    # Bulk Operations
    async def execute_bulk_operation(
        self,
        operation: str,
        target_servers: List[str],
        parameters: dict,
        user_id: str
    ) -> OperationResult
    
    async def get_operation_status(
        self, 
        operation_id: str
    ) -> OperationStatus
    
    # Fleet Statistics
    async def get_fleet_summary(
        self, 
        organization_id: str
    ) -> FleetSummary
    
    async def get_fleet_metrics(
        self,
        organization_id: str,
        time_range: str = "24h"
    ) -> FleetMetrics
```

### REST API Endpoints (`backend/multi_server_api.py`)

```
POST   /api/v1/fleet/servers                    # Register new server
GET    /api/v1/fleet/servers                    # List servers (with filters)
GET    /api/v1/fleet/servers/{id}               # Get server details
PUT    /api/v1/fleet/servers/{id}               # Update server
DELETE /api/v1/fleet/servers/{id}               # Remove server

GET    /api/v1/fleet/servers/{id}/health        # Check server health
POST   /api/v1/fleet/servers/{id}/check         # Force health check
GET    /api/v1/fleet/servers/{id}/metrics       # Get server metrics

POST   /api/v1/fleet/groups                     # Create server group
GET    /api/v1/fleet/groups                     # List groups
GET    /api/v1/fleet/groups/{id}                # Get group details
PUT    /api/v1/fleet/groups/{id}                # Update group
DELETE /api/v1/fleet/groups/{id}                # Delete group

POST   /api/v1/fleet/groups/{id}/servers        # Add server to group
DELETE /api/v1/fleet/groups/{id}/servers/{sid}  # Remove from group

POST   /api/v1/fleet/operations                 # Execute bulk operation
GET    /api/v1/fleet/operations                 # List operations
GET    /api/v1/fleet/operations/{id}            # Get operation status
POST   /api/v1/fleet/operations/{id}/cancel     # Cancel operation

GET    /api/v1/fleet/summary                    # Fleet summary stats
GET    /api/v1/fleet/metrics/aggregated         # Aggregated metrics
GET    /api/v1/fleet/health/overview            # Health overview
```

---

## 🎨 Frontend Components

### Fleet Dashboard (`src/pages/fleet/FleetDashboard.jsx`)

**Main View:**
- Fleet health overview cards
- Server status distribution (pie chart)
- Regional distribution map
- Recent alerts/issues
- Quick actions toolbar

**Features:**
- Real-time status updates (WebSocket)
- Multi-select for bulk operations
- Advanced filtering (region, status, tags, environment)
- Saved filter presets
- Export fleet report (CSV/PDF)

### Server Details View (`src/pages/fleet/ServerDetails.jsx`)

**Tabs:**
1. **Overview** - Current status, version, uptime
2. **Metrics** - CPU, Memory, Disk, Network charts
3. **Services** - Running services list
4. **Users** - Active users count, usage stats
5. **Alerts** - Recent alerts from this server
6. **Logs** - Recent system logs
7. **Configuration** - Server-specific settings

### Group Management (`src/pages/fleet/GroupManagement.jsx`)

**Features:**
- Create/edit/delete groups
- Drag-and-drop servers to groups
- Dynamic groups based on tags/filters
- Group-level bulk operations
- Visual color coding

### Bulk Operations Modal (`src/components/fleet/BulkOperationsModal.jsx`)

**Operations:**
- Restart services
- Update configuration
- Deploy update
- Run health check
- Collect diagnostics

**UI Flow:**
1. Select operation type
2. Review affected servers
3. Configure parameters
4. Confirm execution
5. Monitor progress
6. Review results

---

## 🔄 Background Jobs

### Health Check Worker (`backend/fleet_health_worker.py`)

```python
async def health_check_worker():
    """Background task to check all server health"""
    while True:
        servers = await get_all_active_servers()
        
        for server in servers:
            try:
                health = await check_server_health(server.id)
                await update_health_status(server.id, health)
                
                # Trigger alerts if degraded/critical
                if health.status in ['degraded', 'critical']:
                    await trigger_alert(server.id, health)
                    
            except Exception as e:
                await mark_server_unreachable(server.id, str(e))
        
        await asyncio.sleep(30)  # Check every 30 seconds
```

### Metrics Collection Worker (`backend/fleet_metrics_worker.py`)

```python
async def metrics_collection_worker():
    """Background task to collect metrics from all servers"""
    while True:
        servers = await get_all_active_servers()
        
        for server in servers:
            try:
                metrics = await fetch_server_metrics(server.id)
                await store_metrics(server.id, metrics)
                
            except Exception as e:
                logger.error(f"Failed to collect metrics from {server.id}: {e}")
        
        await asyncio.sleep(60)  # Collect every 1 minute
```

---

## 🔐 Security

### API Token Management
- Each managed server has unique API token
- Tokens stored hashed in control plane DB
- Token rotation support
- Scoped permissions (read-only vs full access)

### Network Security
- TLS/HTTPS required for all server communication
- Certificate validation
- IP allowlist support
- Rate limiting per server

### Access Control
- Organization-scoped server access
- RBAC for fleet operations:
  - `fleet:viewer` - View servers and metrics
  - `fleet:operator` - Execute bulk operations
  - `fleet:admin` - Register/remove servers

---

## 📈 Metrics & Monitoring

### Fleet-Level Metrics
- Total servers (active/inactive/unreachable)
- Average CPU/Memory/Disk across fleet
- Total LLM requests/cost across fleet
- Total users across fleet
- Health distribution (healthy/degraded/critical)

### Per-Server Metrics
- Resource utilization trends
- Service health trends
- User activity trends
- Cost trends

### Alerting
- Server unreachable > 5 minutes
- Server health degraded/critical
- Resource utilization > threshold
- Service failures
- Bulk operation failures

---

## 🧪 Testing Strategy

### Unit Tests
- Server registration/update/deletion
- Health check logic
- Metrics aggregation
- Group management
- Bulk operations orchestration

### Integration Tests
- Multi-server communication
- Metrics collection from multiple servers
- Bulk operation execution
- WebSocket updates
- Alert triggering

### Load Tests
- 100+ servers polling scenario
- Concurrent bulk operations
- Metrics storage performance
- UI rendering with large server count

---

## 📋 Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Database schema and migrations
- [ ] Server registration API
- [ ] Basic health checking
- [ ] Server manager core logic
- [ ] Unit tests

### Phase 2: Metrics & Monitoring (Week 2-3)
- [ ] Metrics collection worker
- [ ] Aggregation logic
- [ ] Time-series storage
- [ ] Health check worker
- [ ] Alert integration

### Phase 3: Frontend Dashboard (Week 3-4)
- [ ] Fleet dashboard layout
- [ ] Server list with filtering
- [ ] Server details view
- [ ] Real-time status updates
- [ ] Charts and visualizations

### Phase 4: Groups & Bulk Ops (Week 4-5)
- [ ] Server group management
- [ ] Group assignment logic
- [ ] Bulk operations framework
- [ ] Operation progress tracking
- [ ] Results reporting

### Phase 5: Polish & Testing (Week 5-6)
- [ ] Integration testing
- [ ] Load testing
- [ ] Documentation
- [ ] Security audit
- [ ] Performance optimization

---

## 🎯 Success Criteria

- [ ] Successfully register and manage 50+ servers
- [ ] Health checks complete in < 5 seconds per server
- [ ] Metrics collection with < 1% data loss
- [ ] Bulk operations execute reliably across 20+ servers
- [ ] UI responsive with 100+ servers
- [ ] Zero downtime during server registration/removal
- [ ] Comprehensive documentation and examples

---

## 🚀 Future Enhancements

### Epic 15.1: Advanced Features
- Server auto-discovery
- Predictive maintenance (ML-based)
- Capacity planning recommendations
- Cost optimization across fleet
- Geographic traffic routing
- Automated failover orchestration

### Epic 15.2: Integration
- Kubernetes cluster management
- Terraform state integration
- Multi-cloud provider support
- Container orchestration
- Service mesh integration

---

## 📚 Related Epics

- **Epic 12**: The Colonel Agent (will use fleet data)
- **Epic 16**: The Colonel v2 (multi-server orchestration)
- **Epic 17**: Kubernetes Integration (cluster management)
- **Epic 18**: Terraform/IaC Integration (infrastructure provisioning)

---

**Status**: Ready for Implementation  
**Next Step**: Create database migration for managed_servers tables
