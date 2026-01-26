# Epic 16: Kubernetes Integration

**Status**: 🚧 In Progress  
**Priority**: High  
**Complexity**: High  
**Dependencies**: Epic 15 (Multi-Server Fleet Management)

---

## 📋 Overview

Extend Ops-Center with comprehensive Kubernetes cluster management capabilities, enabling monitoring, deployment management, resource optimization, and cost tracking across multiple K8s clusters.

### Business Value

- **Multi-Cluster Management**: Monitor and manage multiple K8s clusters from one dashboard
- **Resource Optimization**: Track pod/node resource usage and identify optimization opportunities
- **Deployment Control**: GitOps-style deployment tracking and health monitoring
- **Cost Visibility**: Attribute cloud costs to specific namespaces, teams, and applications
- **Integration with Fleet**: Unified view of bare metal servers + K8s clusters

### Success Criteria

- ✅ Register and monitor multiple K8s clusters
- ✅ Real-time cluster health and resource metrics
- ✅ Namespace-level cost attribution
- ✅ Deployment and pod status tracking
- ✅ Helm release management
- ✅ Resource quota and limit recommendations
- ✅ Integration with existing fleet dashboard

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Ops-Center Frontend                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Fleet      │  │  Kubernetes  │  │   Resource   │      │
│  │  Dashboard   │  │   Dashboard  │  │ Optimization │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Ops-Center Backend (FastAPI)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Kubernetes Management API                   │   │
│  │  • Cluster Registration    • Deployment Tracking     │   │
│  │  • Health Monitoring       • Helm Management         │   │
│  │  • Resource Metrics        • Cost Attribution        │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Background Workers (asyncio)                  │   │
│  │  • Cluster Sync Worker (30s) - Health & Metrics      │   │
│  │  • Event Watcher (real-time) - Pod/Deploy Events     │   │
│  │  • Cost Calculator (hourly) - Resource Cost Tracking │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│  • k8s_clusters         • k8s_deployments                    │
│  • k8s_namespaces       • k8s_pods (partitioned)             │
│  • k8s_nodes            • k8s_resource_metrics (partitioned) │
│  • k8s_events           • k8s_helm_releases                  │
│  • k8s_cost_attribution                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              External Kubernetes Clusters                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Cluster 1 │  │  Cluster 2 │  │  Cluster N │            │
│  │   (kubeconfig) (kubeconfig) (kubeconfig)   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Cluster Registration**: Admin provides kubeconfig → Encrypted storage → Initial sync
2. **Health Monitoring**: Background worker polls clusters every 30s → Update metrics
3. **Event Watching**: Real-time event streams → Store pod/deployment changes
4. **Cost Attribution**: Hourly job → Calculate namespace costs → Update dashboard
5. **User Queries**: Frontend → API → Database → Kubernetes API (if needed)

---

## 🗄️ Phase 1: Database Schema

### Core Tables

#### 1. `k8s_clusters`
Registered Kubernetes clusters

```sql
CREATE TABLE k8s_clusters (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Connection Details (encrypted)
    kubeconfig_encrypted TEXT NOT NULL,  -- Encrypted with BYOK
    context_name VARCHAR(255),
    api_server_url VARCHAR(500) NOT NULL,
    
    -- Cluster Metadata
    cluster_version VARCHAR(50),
    provider VARCHAR(100),  -- eks, gke, aks, k3s, vanilla
    region VARCHAR(100),
    environment VARCHAR(50),  -- production, staging, development
    
    -- Health Status
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, unreachable, error, maintenance
    health_status VARCHAR(50) DEFAULT 'unknown',  -- healthy, degraded, critical
    last_sync_at TIMESTAMP,
    last_error TEXT,
    
    -- Resource Counts (cached for performance)
    total_nodes INTEGER DEFAULT 0,
    total_namespaces INTEGER DEFAULT 0,
    total_pods INTEGER DEFAULT 0,
    total_deployments INTEGER DEFAULT 0,
    
    -- Cost Tracking
    estimated_monthly_cost DECIMAL(10,2),
    cost_currency VARCHAR(10) DEFAULT 'USD',
    
    -- Organization & Tagging
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(36),
    
    CONSTRAINT fk_k8s_cluster_org FOREIGN KEY (organization_id) 
        REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX idx_k8s_clusters_org ON k8s_clusters(organization_id);
CREATE INDEX idx_k8s_clusters_status ON k8s_clusters(status);
CREATE INDEX idx_k8s_clusters_health ON k8s_clusters(health_status);
CREATE INDEX idx_k8s_clusters_env ON k8s_clusters(environment);
CREATE INDEX idx_k8s_clusters_tags ON k8s_clusters USING gin(tags);
```

#### 2. `k8s_namespaces`
Namespaces within clusters

```sql
CREATE TABLE k8s_namespaces (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    cluster_id VARCHAR(36) NOT NULL,
    organization_id VARCHAR(36) NOT NULL,
    
    -- Namespace Info
    name VARCHAR(255) NOT NULL,
    namespace_uid VARCHAR(100) NOT NULL,  -- K8s UID
    status VARCHAR(50) DEFAULT 'Active',
    
    -- Resource Quotas
    cpu_limit VARCHAR(50),
    memory_limit VARCHAR(50),
    pod_limit INTEGER,
    
    -- Current Usage
    cpu_usage_cores DECIMAL(10,3),
    memory_usage_bytes BIGINT,
    pod_count INTEGER DEFAULT 0,
    
    -- Cost Attribution
    team_name VARCHAR(255),
    cost_center VARCHAR(255),
    estimated_daily_cost DECIMAL(10,2),
    
    -- Metadata
    labels JSONB DEFAULT '{}',
    annotations JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sync_at TIMESTAMP,
    
    CONSTRAINT fk_k8s_ns_cluster FOREIGN KEY (cluster_id) 
        REFERENCES k8s_clusters(id) ON DELETE CASCADE,
    CONSTRAINT uk_k8s_ns_cluster_name UNIQUE(cluster_id, name)
);

CREATE INDEX idx_k8s_ns_cluster ON k8s_namespaces(cluster_id);
CREATE INDEX idx_k8s_ns_org ON k8s_namespaces(organization_id);
CREATE INDEX idx_k8s_ns_team ON k8s_namespaces(team_name);
CREATE INDEX idx_k8s_ns_labels ON k8s_namespaces USING gin(labels);
```

#### 3. `k8s_nodes`
Cluster nodes

```sql
CREATE TABLE k8s_nodes (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    cluster_id VARCHAR(36) NOT NULL,
    
    -- Node Info
    name VARCHAR(255) NOT NULL,
    node_uid VARCHAR(100) NOT NULL,
    node_type VARCHAR(50),  -- master, worker
    instance_type VARCHAR(100),  -- t3.large, n1-standard-4, etc.
    
    -- Capacity
    cpu_capacity VARCHAR(50),
    memory_capacity VARCHAR(50),
    pod_capacity INTEGER,
    
    -- Allocatable (after system reserves)
    cpu_allocatable VARCHAR(50),
    memory_allocatable VARCHAR(50),
    
    -- Current Usage
    cpu_usage_cores DECIMAL(10,3),
    memory_usage_bytes BIGINT,
    pod_count INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(50) DEFAULT 'Ready',
    conditions JSONB DEFAULT '[]',
    
    -- Metadata
    labels JSONB DEFAULT '{}',
    taints JSONB DEFAULT '[]',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sync_at TIMESTAMP,
    
    CONSTRAINT fk_k8s_node_cluster FOREIGN KEY (cluster_id) 
        REFERENCES k8s_clusters(id) ON DELETE CASCADE,
    CONSTRAINT uk_k8s_node_cluster_name UNIQUE(cluster_id, name)
);

CREATE INDEX idx_k8s_nodes_cluster ON k8s_nodes(cluster_id);
CREATE INDEX idx_k8s_nodes_status ON k8s_nodes(status);
CREATE INDEX idx_k8s_nodes_type ON k8s_nodes(node_type);
```

#### 4. `k8s_deployments`
Deployment tracking

```sql
CREATE TABLE k8s_deployments (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    cluster_id VARCHAR(36) NOT NULL,
    namespace_id VARCHAR(36) NOT NULL,
    organization_id VARCHAR(36) NOT NULL,
    
    -- Deployment Info
    name VARCHAR(255) NOT NULL,
    deployment_uid VARCHAR(100) NOT NULL,
    
    -- Spec
    replicas_desired INTEGER,
    replicas_current INTEGER,
    replicas_ready INTEGER,
    replicas_available INTEGER,
    replicas_unavailable INTEGER,
    
    -- Container Info
    containers JSONB DEFAULT '[]',  -- [{name, image, resources}]
    
    -- Status
    status VARCHAR(50) DEFAULT 'Running',
    health_status VARCHAR(50) DEFAULT 'healthy',  -- healthy, degraded, failed
    
    -- Strategy
    strategy VARCHAR(50),  -- RollingUpdate, Recreate
    
    -- Metadata
    labels JSONB DEFAULT '{}',
    annotations JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sync_at TIMESTAMP,
    
    CONSTRAINT fk_k8s_deploy_cluster FOREIGN KEY (cluster_id) 
        REFERENCES k8s_clusters(id) ON DELETE CASCADE,
    CONSTRAINT fk_k8s_deploy_ns FOREIGN KEY (namespace_id) 
        REFERENCES k8s_namespaces(id) ON DELETE CASCADE,
    CONSTRAINT uk_k8s_deploy_ns_name UNIQUE(namespace_id, name)
);

CREATE INDEX idx_k8s_deploy_cluster ON k8s_deployments(cluster_id);
CREATE INDEX idx_k8s_deploy_ns ON k8s_deployments(namespace_id);
CREATE INDEX idx_k8s_deploy_org ON k8s_deployments(organization_id);
CREATE INDEX idx_k8s_deploy_status ON k8s_deployments(status);
CREATE INDEX idx_k8s_deploy_health ON k8s_deployments(health_status);
```

#### 5. `k8s_pods` (Partitioned by month)
Pod instance tracking

```sql
CREATE TABLE k8s_pods (
    id VARCHAR(36) DEFAULT gen_random_uuid()::text,
    cluster_id VARCHAR(36) NOT NULL,
    namespace_id VARCHAR(36) NOT NULL,
    deployment_id VARCHAR(36),
    
    -- Pod Info
    name VARCHAR(255) NOT NULL,
    pod_uid VARCHAR(100) NOT NULL,
    node_name VARCHAR(255),
    
    -- Status
    phase VARCHAR(50),  -- Pending, Running, Succeeded, Failed, Unknown
    status VARCHAR(50),
    reason TEXT,
    
    -- Container Status
    containers JSONB DEFAULT '[]',
    init_containers JSONB DEFAULT '[]',
    
    -- Resource Requests/Limits
    cpu_request VARCHAR(50),
    memory_request VARCHAR(50),
    cpu_limit VARCHAR(50),
    memory_limit VARCHAR(50),
    
    -- Timestamps
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for 2026
CREATE TABLE k8s_pods_2026_01 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE k8s_pods_2026_02 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE k8s_pods_2026_03 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE k8s_pods_2026_04 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE k8s_pods_2026_05 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE k8s_pods_2026_06 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE k8s_pods_2026_07 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE k8s_pods_2026_08 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE k8s_pods_2026_09 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE k8s_pods_2026_10 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE k8s_pods_2026_11 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE k8s_pods_2026_12 PARTITION OF k8s_pods
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE INDEX idx_k8s_pods_cluster ON k8s_pods(cluster_id, created_at);
CREATE INDEX idx_k8s_pods_ns ON k8s_pods(namespace_id, created_at);
CREATE INDEX idx_k8s_pods_deploy ON k8s_pods(deployment_id, created_at);
CREATE INDEX idx_k8s_pods_phase ON k8s_pods(phase, created_at);
CREATE INDEX idx_k8s_pods_node ON k8s_pods(node_name, created_at);
```

#### 6. `k8s_resource_metrics` (Partitioned by month)
Time-series resource usage metrics

```sql
CREATE TABLE k8s_resource_metrics (
    id BIGSERIAL,
    cluster_id VARCHAR(36) NOT NULL,
    namespace_id VARCHAR(36),
    deployment_id VARCHAR(36),
    pod_id VARCHAR(36),
    node_id VARCHAR(36),
    
    -- Resource Type
    resource_type VARCHAR(50) NOT NULL,  -- cluster, namespace, deployment, pod, node
    
    -- Metrics
    cpu_usage_cores DECIMAL(10,3),
    memory_usage_bytes BIGINT,
    network_rx_bytes BIGINT,
    network_tx_bytes BIGINT,
    storage_usage_bytes BIGINT,
    
    -- Pod-specific
    restarts INTEGER,
    oom_kills INTEGER,
    
    -- Timestamp
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, collected_at)
) PARTITION BY RANGE (collected_at);

-- Create monthly partitions for 2026
CREATE TABLE k8s_resource_metrics_2026_01 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE k8s_resource_metrics_2026_02 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE k8s_resource_metrics_2026_03 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE k8s_resource_metrics_2026_04 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE k8s_resource_metrics_2026_05 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE k8s_resource_metrics_2026_06 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE k8s_resource_metrics_2026_07 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE k8s_resource_metrics_2026_08 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE k8s_resource_metrics_2026_09 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE k8s_resource_metrics_2026_10 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE k8s_resource_metrics_2026_11 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE k8s_resource_metrics_2026_12 PARTITION OF k8s_resource_metrics
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE INDEX idx_k8s_metrics_cluster ON k8s_resource_metrics(cluster_id, collected_at);
CREATE INDEX idx_k8s_metrics_ns ON k8s_resource_metrics(namespace_id, collected_at);
CREATE INDEX idx_k8s_metrics_type ON k8s_resource_metrics(resource_type, collected_at);
```

#### 7. `k8s_helm_releases`
Helm chart deployments

```sql
CREATE TABLE k8s_helm_releases (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    cluster_id VARCHAR(36) NOT NULL,
    namespace_id VARCHAR(36) NOT NULL,
    
    -- Release Info
    name VARCHAR(255) NOT NULL,
    chart_name VARCHAR(255) NOT NULL,
    chart_version VARCHAR(50),
    
    -- Status
    status VARCHAR(50),  -- deployed, failed, pending-install, pending-upgrade
    revision INTEGER,
    
    -- Values
    values_yaml TEXT,
    
    -- Timestamps
    first_deployed_at TIMESTAMP,
    last_deployed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_k8s_helm_cluster FOREIGN KEY (cluster_id) 
        REFERENCES k8s_clusters(id) ON DELETE CASCADE,
    CONSTRAINT fk_k8s_helm_ns FOREIGN KEY (namespace_id) 
        REFERENCES k8s_namespaces(id) ON DELETE CASCADE,
    CONSTRAINT uk_k8s_helm_ns_name UNIQUE(namespace_id, name)
);

CREATE INDEX idx_k8s_helm_cluster ON k8s_helm_releases(cluster_id);
CREATE INDEX idx_k8s_helm_ns ON k8s_helm_releases(namespace_id);
CREATE INDEX idx_k8s_helm_status ON k8s_helm_releases(status);
```

#### 8. `k8s_cost_attribution`
Namespace cost tracking

```sql
CREATE TABLE k8s_cost_attribution (
    id BIGSERIAL PRIMARY KEY,
    cluster_id VARCHAR(36) NOT NULL,
    namespace_id VARCHAR(36) NOT NULL,
    organization_id VARCHAR(36) NOT NULL,
    
    -- Time Period
    date DATE NOT NULL,
    hour INTEGER,  -- NULL for daily aggregation, 0-23 for hourly
    
    -- Resource Costs
    cpu_cost DECIMAL(10,4),
    memory_cost DECIMAL(10,4),
    storage_cost DECIMAL(10,4),
    network_cost DECIMAL(10,4),
    total_cost DECIMAL(10,4),
    
    -- Resource Usage
    cpu_core_hours DECIMAL(12,3),
    memory_gb_hours DECIMAL(12,3),
    storage_gb_hours DECIMAL(12,3),
    network_gb DECIMAL(12,3),
    
    -- Attribution
    team_name VARCHAR(255),
    cost_center VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_k8s_cost_cluster FOREIGN KEY (cluster_id) 
        REFERENCES k8s_clusters(id) ON DELETE CASCADE,
    CONSTRAINT fk_k8s_cost_ns FOREIGN KEY (namespace_id) 
        REFERENCES k8s_namespaces(id) ON DELETE CASCADE,
    CONSTRAINT uk_k8s_cost_ns_date_hour UNIQUE(namespace_id, date, hour)
);

CREATE INDEX idx_k8s_cost_cluster_date ON k8s_cost_attribution(cluster_id, date);
CREATE INDEX idx_k8s_cost_ns_date ON k8s_cost_attribution(namespace_id, date);
CREATE INDEX idx_k8s_cost_org_date ON k8s_cost_attribution(organization_id, date);
CREATE INDEX idx_k8s_cost_team ON k8s_cost_attribution(team_name, date);
```

### Views for Dashboards

```sql
-- Cluster Health Summary
CREATE VIEW v_k8s_cluster_health AS
SELECT 
    c.id,
    c.organization_id,
    c.name,
    c.health_status,
    c.total_nodes,
    c.total_namespaces,
    c.total_pods,
    COUNT(DISTINCT n.id) FILTER (WHERE n.status = 'Ready') as healthy_nodes,
    COUNT(DISTINCT d.id) FILTER (WHERE d.health_status = 'healthy') as healthy_deployments,
    SUM(m.cpu_usage_cores) as total_cpu_usage,
    SUM(m.memory_usage_bytes) as total_memory_usage,
    c.last_sync_at
FROM k8s_clusters c
LEFT JOIN k8s_nodes n ON c.id = n.cluster_id
LEFT JOIN k8s_deployments d ON c.id = d.cluster_id
LEFT JOIN LATERAL (
    SELECT cpu_usage_cores, memory_usage_bytes
    FROM k8s_resource_metrics
    WHERE cluster_id = c.id 
      AND resource_type = 'cluster'
    ORDER BY collected_at DESC
    LIMIT 1
) m ON true
GROUP BY c.id, c.organization_id, c.name, c.health_status, 
         c.total_nodes, c.total_namespaces, c.total_pods, 
         m.cpu_usage_cores, m.memory_usage_bytes, c.last_sync_at;

-- Namespace Cost Summary (Last 30 days)
CREATE VIEW v_k8s_namespace_costs AS
SELECT 
    n.id as namespace_id,
    n.cluster_id,
    n.organization_id,
    n.name as namespace_name,
    n.team_name,
    SUM(ca.total_cost) as cost_last_30d,
    AVG(ca.total_cost) as avg_daily_cost,
    SUM(ca.cpu_core_hours) as cpu_hours_last_30d,
    SUM(ca.memory_gb_hours) as memory_gb_hours_last_30d
FROM k8s_namespaces n
LEFT JOIN k8s_cost_attribution ca ON n.id = ca.namespace_id
WHERE ca.date >= CURRENT_DATE - INTERVAL '30 days'
  AND ca.hour IS NULL  -- Daily aggregation only
GROUP BY n.id, n.cluster_id, n.organization_id, n.name, n.team_name;
```

---

## 🔧 Phase 2: Backend Implementation

### File Structure

```
backend/
├── k8s_cluster_manager.py      # Core K8s cluster operations
├── k8s_sync_worker.py           # Background sync worker (30s)
├── k8s_cost_calculator.py       # Cost attribution logic
├── k8s_api.py                   # REST API endpoints
└── requirements.txt             # Add kubernetes, kubernetes-asyncio
```

### Dependencies

```txt
kubernetes==29.0.0
kubernetes-asyncio==29.0.0
pyyaml==6.0.1
cryptography==42.0.0
```

### 1. `k8s_cluster_manager.py`

Core business logic for K8s cluster management.

**Key Methods:**
- `register_cluster(kubeconfig, name, org_id)` - Add new cluster
- `sync_cluster(cluster_id)` - Full cluster sync
- `get_cluster_health(cluster_id)` - Health check
- `list_namespaces(cluster_id)` - Get all namespaces
- `list_deployments(cluster_id, namespace)` - Get deployments
- `list_pods(cluster_id, namespace)` - Get pods
- `get_node_metrics(cluster_id)` - Node resource usage
- `delete_cluster(cluster_id)` - Remove cluster

### 2. `k8s_sync_worker.py`

Background worker for continuous cluster synchronization.

**Features:**
- Runs every 30 seconds
- Batch processing (5 clusters at a time)
- Syncs: cluster health, node status, deployment status, pod counts
- Collects metrics for time-series storage
- Graceful error handling per cluster

### 3. `k8s_cost_calculator.py`

Cost attribution engine.

**Features:**
- Hourly job to calculate namespace costs
- Based on resource requests/usage
- Configurable pricing (per vCPU-hour, GB-hour, GB storage, GB network)
- Team/cost-center attribution from namespace labels
- Daily and monthly rollups

### 4. `k8s_api.py`

REST API endpoints (19 endpoints).

**Endpoints:**
- `POST /api/v1/k8s/clusters` - Register cluster
- `GET /api/v1/k8s/clusters` - List clusters
- `GET /api/v1/k8s/clusters/{id}` - Get cluster details
- `DELETE /api/v1/k8s/clusters/{id}` - Delete cluster
- `POST /api/v1/k8s/clusters/{id}/sync` - Trigger sync
- `GET /api/v1/k8s/clusters/{id}/health` - Health status
- `GET /api/v1/k8s/clusters/{id}/namespaces` - List namespaces
- `GET /api/v1/k8s/clusters/{id}/nodes` - List nodes
- `GET /api/v1/k8s/namespaces/{id}/deployments` - List deployments
- `GET /api/v1/k8s/namespaces/{id}/pods` - List pods
- `GET /api/v1/k8s/namespaces/{id}/costs` - Cost breakdown
- `GET /api/v1/k8s/deployments/{id}` - Deployment details
- `GET /api/v1/k8s/deployments/{id}/pods` - Deployment pods
- `GET /api/v1/k8s/pods/{id}` - Pod details
- `GET /api/v1/k8s/pods/{id}/logs` - Pod logs (proxy to K8s)
- `GET /api/v1/k8s/helm/releases` - List Helm releases
- `GET /api/v1/k8s/metrics/cluster/{id}` - Cluster metrics time-series
- `GET /api/v1/k8s/metrics/namespace/{id}` - Namespace metrics
- `GET /api/v1/k8s/workers/status` - Worker health (admin)

---

## 🎨 Phase 3: Frontend Dashboard

### File Structure

```
src/pages/kubernetes/
├── KubernetesDashboard.jsx      # Main dashboard
├── ClusterList.jsx               # Cluster cards
├── ClusterDetail.jsx             # Single cluster view
├── NamespaceList.jsx             # Namespace cards
├── NamespaceDetail.jsx           # Namespace detail + costs
├── DeploymentList.jsx            # Deployments table
├── PodList.jsx                   # Pods table
├── PodLogs.jsx                   # Log viewer
├── HelmReleases.jsx              # Helm charts
└── RegisterClusterModal.jsx      # Add cluster form
```

### Dashboard Features

#### Main Dashboard View

```
┌──────────────────────────────────────────────────────────────┐
│  Kubernetes Dashboard                        🔄 Refresh       │
├──────────────────────────────────────────────────────────────┤
│  Summary Cards                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 8 Clusters│ │ 142 Nodes│ │ 1.2K Pods│ │$4.5K/mo  │        │
│  │  6 Healthy│ │ 138 Ready│ │ 98% Ready│ │ Costs    │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
├──────────────────────────────────────────────────────────────┤
│  Clusters                                      + Add Cluster  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🟢 prod-us-east-1    │ 24 Nodes │ 456 Pods │ $1.8K/mo │  │
│  │    GKE 1.28.5        │ 98% CPU  │ 78% Mem  │ EKS      │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ 🟢 staging-eu-west-1 │ 12 Nodes │ 234 Pods │ $890/mo  │  │
│  │    AKS 1.27.3        │ 45% CPU  │ 52% Mem  │ Azure    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ 🟡 dev-cluster       │ 4 Nodes  │ 89 Pods  │ $120/mo  │  │
│  │    k3s 1.28.1        │ 23% CPU  │ 41% Mem  │ On-Prem  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### Cluster Detail View

```
┌──────────────────────────────────────────────────────────────┐
│  ← Back  prod-us-east-1                           🔄 Sync    │
├──────────────────────────────────────────────────────────────┤
│  Cluster Health: 🟢 Healthy    │  Provider: GKE              │
│  Version: 1.28.5               │  Region: us-east-1          │
│  Nodes: 24 (24 Ready)          │  Cost: $1,845/month         │
├──────────────────────────────────────────────────────────────┤
│  Tabs: Namespaces | Nodes | Deployments | Pods | Metrics    │
├──────────────────────────────────────────────────────────────┤
│  Namespaces (showing top 10 by cost)                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ production      │ 12 Deploys │ 145 Pods │ $850/mo     │  │
│  │ Team: Platform  │ CPU: 12.5  │ Mem: 48GB│             │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ api-services    │ 8 Deploys  │ 89 Pods  │ $620/mo     │  │
│  │ Team: Backend   │ CPU: 8.2   │ Mem: 32GB│             │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### Namespace Cost Breakdown

```
┌──────────────────────────────────────────────────────────────┐
│  Namespace: production                Cost Center: Platform  │
├──────────────────────────────────────────────────────────────┤
│  Cost Breakdown (Last 30 Days)                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Total: $850.42                                      │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │    │
│  │  │CPU $520│ │Mem $280│ │Net $35 │ │Disk $15│       │    │
│  │  │  61%   │ │  33%   │ │   4%   │ │   2%   │       │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  📊 Cost Trend (Last 30 Days)                                │
│  [Line chart showing daily costs]                            │
│                                                               │
│  Top Deployments by Cost                                     │
│  1. api-gateway       $245/mo  (28.8%)                       │
│  2. worker-pool       $198/mo  (23.3%)                       │
│  3. cache-redis       $156/mo  (18.3%)                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Implementation Plan

### Phase 1: Database & Core (Week 1)
- [ ] Create Alembic migration for all tables
- [ ] Execute migration on PostgreSQL
- [ ] Create `k8s_cluster_manager.py` with core CRUD
- [ ] Implement kubeconfig encryption/decryption
- [ ] Basic cluster registration endpoint

### Phase 2: Sync Worker (Week 1-2)
- [ ] Create `k8s_sync_worker.py`
- [ ] Implement cluster health checks
- [ ] Implement namespace sync
- [ ] Implement node sync
- [ ] Implement deployment/pod sync
- [ ] Integrate with server.py startup/shutdown

### Phase 3: API Endpoints (Week 2)
- [ ] Create `k8s_api.py` with 19 endpoints
- [ ] Add authentication/authorization
- [ ] Register router in server.py
- [ ] Test with Postman/curl

### Phase 4: Cost Attribution (Week 2-3)
- [ ] Create `k8s_cost_calculator.py`
- [ ] Implement cost calculation logic
- [ ] Create hourly background job
- [ ] Add cost configuration (pricing per resource)

### Phase 5: Frontend Dashboard (Week 3)
- [ ] Create `KubernetesDashboard.jsx` main view
- [ ] Create cluster list/detail components
- [ ] Create namespace list/detail with costs
- [ ] Create deployment/pod list components
- [ ] Add charts for metrics visualization

### Phase 6: Advanced Features (Week 4)
- [ ] Pod log viewer with streaming
- [ ] Helm release management
- [ ] Real-time event watching
- [ ] Resource optimization recommendations
- [ ] Integration with Fleet Dashboard

### Phase 7: Testing & Documentation (Week 4)
- [ ] Unit tests for manager and workers
- [ ] Integration tests for API
- [ ] Frontend component tests
- [ ] User documentation
- [ ] API documentation

---

## 🎯 Success Metrics

- **Performance**: Sync 100+ clusters with <30s latency
- **Reliability**: 99.9% uptime for monitoring workers
- **Accuracy**: Cost attribution within 5% of cloud bills
- **Usability**: Users can register cluster in <2 minutes
- **Visibility**: 95% of clusters show healthy status within 1 minute of sync

---

## 🔐 Security Considerations

1. **Kubeconfig Encryption**: Store kubeconfigs encrypted with BYOK
2. **RBAC**: Cluster management restricted to admins
3. **Namespace Isolation**: Users only see namespaces in their org
4. **API Proxy**: Don't expose K8s API directly, proxy through backend
5. **Audit Logging**: Log all cluster operations

---

## 🔄 Future Enhancements

- **GitOps Integration**: Sync with ArgoCD/Flux
- **Autoscaling Recommendations**: HPA/VPA suggestions
- **Security Scanning**: Integration with Trivy/Falco
- **Multi-Cloud Cost Optimization**: Cross-cluster workload placement
- **Disaster Recovery**: Backup/restore for cluster configs

---

**Ready to proceed with Phase 1: Database Schema?**
