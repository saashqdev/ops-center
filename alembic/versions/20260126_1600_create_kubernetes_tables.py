"""Create Kubernetes integration tables

Epic 16: Kubernetes Integration - Phase 1

Revision ID: 20260126_1600
Revises: 20260126_1500
Create Date: 2026-01-26 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_1600'
down_revision = '20260126_1500'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create all tables for Kubernetes integration:
    - 8 core tables
    - 24 partitions (12 pods + 12 metrics for 2026)
    - 2 views for dashboards
    """
    
    # =====================================================================
    # TABLE 1: k8s_clusters
    # =====================================================================
    op.execute("""
        CREATE TABLE k8s_clusters (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            organization_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            
            -- Connection Details (encrypted)
            kubeconfig_encrypted TEXT NOT NULL,
            context_name VARCHAR(255),
            api_server_url VARCHAR(500) NOT NULL,
            
            -- Cluster Metadata
            cluster_version VARCHAR(50),
            provider VARCHAR(100),
            region VARCHAR(100),
            environment VARCHAR(50),
            
            -- Health Status
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            health_status VARCHAR(50) DEFAULT 'unknown',
            last_sync_at TIMESTAMP,
            last_error TEXT,
            
            -- Resource Counts (cached)
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
    """)
    
    # Indexes for k8s_clusters
    op.execute("CREATE INDEX idx_k8s_clusters_org ON k8s_clusters(organization_id);")
    op.execute("CREATE INDEX idx_k8s_clusters_status ON k8s_clusters(status);")
    op.execute("CREATE INDEX idx_k8s_clusters_health ON k8s_clusters(health_status);")
    op.execute("CREATE INDEX idx_k8s_clusters_env ON k8s_clusters(environment);")
    op.execute("CREATE INDEX idx_k8s_clusters_tags ON k8s_clusters USING gin(tags);")
    op.execute("CREATE INDEX idx_k8s_clusters_provider ON k8s_clusters(provider);")
    
    # =====================================================================
    # TABLE 2: k8s_namespaces
    # =====================================================================
    op.execute("""
        CREATE TABLE k8s_namespaces (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            cluster_id VARCHAR(36) NOT NULL,
            organization_id VARCHAR(36) NOT NULL,
            
            -- Namespace Info
            name VARCHAR(255) NOT NULL,
            namespace_uid VARCHAR(100) NOT NULL,
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
    """)
    
    # Indexes for k8s_namespaces
    op.execute("CREATE INDEX idx_k8s_ns_cluster ON k8s_namespaces(cluster_id);")
    op.execute("CREATE INDEX idx_k8s_ns_org ON k8s_namespaces(organization_id);")
    op.execute("CREATE INDEX idx_k8s_ns_team ON k8s_namespaces(team_name);")
    op.execute("CREATE INDEX idx_k8s_ns_cost_center ON k8s_namespaces(cost_center);")
    op.execute("CREATE INDEX idx_k8s_ns_labels ON k8s_namespaces USING gin(labels);")
    
    # =====================================================================
    # TABLE 3: k8s_nodes
    # =====================================================================
    op.execute("""
        CREATE TABLE k8s_nodes (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            cluster_id VARCHAR(36) NOT NULL,
            
            -- Node Info
            name VARCHAR(255) NOT NULL,
            node_uid VARCHAR(100) NOT NULL,
            node_type VARCHAR(50),
            instance_type VARCHAR(100),
            
            -- Capacity
            cpu_capacity VARCHAR(50),
            memory_capacity VARCHAR(50),
            pod_capacity INTEGER,
            
            -- Allocatable
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
    """)
    
    # Indexes for k8s_nodes
    op.execute("CREATE INDEX idx_k8s_nodes_cluster ON k8s_nodes(cluster_id);")
    op.execute("CREATE INDEX idx_k8s_nodes_status ON k8s_nodes(status);")
    op.execute("CREATE INDEX idx_k8s_nodes_type ON k8s_nodes(node_type);")
    op.execute("CREATE INDEX idx_k8s_nodes_instance ON k8s_nodes(instance_type);")
    
    # =====================================================================
    # TABLE 4: k8s_deployments
    # =====================================================================
    op.execute("""
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
            containers JSONB DEFAULT '[]',
            
            -- Status
            status VARCHAR(50) DEFAULT 'Running',
            health_status VARCHAR(50) DEFAULT 'healthy',
            
            -- Strategy
            strategy VARCHAR(50),
            
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
    """)
    
    # Indexes for k8s_deployments
    op.execute("CREATE INDEX idx_k8s_deploy_cluster ON k8s_deployments(cluster_id);")
    op.execute("CREATE INDEX idx_k8s_deploy_ns ON k8s_deployments(namespace_id);")
    op.execute("CREATE INDEX idx_k8s_deploy_org ON k8s_deployments(organization_id);")
    op.execute("CREATE INDEX idx_k8s_deploy_status ON k8s_deployments(status);")
    op.execute("CREATE INDEX idx_k8s_deploy_health ON k8s_deployments(health_status);")
    
    # =====================================================================
    # TABLE 5: k8s_pods (PARTITIONED by month)
    # =====================================================================
    op.execute("""
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
            phase VARCHAR(50),
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
    """)
    
    # Create monthly partitions for 2026
    months = [
        ('2026_01', '2026-01-01', '2026-02-01'),
        ('2026_02', '2026-02-01', '2026-03-01'),
        ('2026_03', '2026-03-01', '2026-04-01'),
        ('2026_04', '2026-04-01', '2026-05-01'),
        ('2026_05', '2026-05-01', '2026-06-01'),
        ('2026_06', '2026-06-01', '2026-07-01'),
        ('2026_07', '2026-07-01', '2026-08-01'),
        ('2026_08', '2026-08-01', '2026-09-01'),
        ('2026_09', '2026-09-01', '2026-10-01'),
        ('2026_10', '2026-10-01', '2026-11-01'),
        ('2026_11', '2026-11-01', '2026-12-01'),
        ('2026_12', '2026-12-01', '2027-01-01'),
    ]
    
    for suffix, start_date, end_date in months:
        op.execute(f"""
            CREATE TABLE k8s_pods_{suffix} PARTITION OF k8s_pods
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    # Indexes for k8s_pods (on parent table)
    op.execute("CREATE INDEX idx_k8s_pods_cluster ON k8s_pods(cluster_id, created_at);")
    op.execute("CREATE INDEX idx_k8s_pods_ns ON k8s_pods(namespace_id, created_at);")
    op.execute("CREATE INDEX idx_k8s_pods_deploy ON k8s_pods(deployment_id, created_at);")
    op.execute("CREATE INDEX idx_k8s_pods_phase ON k8s_pods(phase, created_at);")
    op.execute("CREATE INDEX idx_k8s_pods_node ON k8s_pods(node_name, created_at);")
    
    # =====================================================================
    # TABLE 6: k8s_resource_metrics (PARTITIONED by month)
    # =====================================================================
    op.execute("""
        CREATE TABLE k8s_resource_metrics (
            id BIGSERIAL,
            cluster_id VARCHAR(36) NOT NULL,
            namespace_id VARCHAR(36),
            deployment_id VARCHAR(36),
            pod_id VARCHAR(36),
            node_id VARCHAR(36),
            
            -- Resource Type
            resource_type VARCHAR(50) NOT NULL,
            
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
    """)
    
    # Create monthly partitions for 2026
    for suffix, start_date, end_date in months:
        op.execute(f"""
            CREATE TABLE k8s_resource_metrics_{suffix} PARTITION OF k8s_resource_metrics
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    # Indexes for k8s_resource_metrics
    op.execute("CREATE INDEX idx_k8s_metrics_cluster ON k8s_resource_metrics(cluster_id, collected_at);")
    op.execute("CREATE INDEX idx_k8s_metrics_ns ON k8s_resource_metrics(namespace_id, collected_at);")
    op.execute("CREATE INDEX idx_k8s_metrics_type ON k8s_resource_metrics(resource_type, collected_at);")
    op.execute("CREATE INDEX idx_k8s_metrics_deploy ON k8s_resource_metrics(deployment_id, collected_at);")
    
    # =====================================================================
    # TABLE 7: k8s_helm_releases
    # =====================================================================
    op.execute("""
        CREATE TABLE k8s_helm_releases (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            cluster_id VARCHAR(36) NOT NULL,
            namespace_id VARCHAR(36) NOT NULL,
            
            -- Release Info
            name VARCHAR(255) NOT NULL,
            chart_name VARCHAR(255) NOT NULL,
            chart_version VARCHAR(50),
            
            -- Status
            status VARCHAR(50),
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
    """)
    
    # Indexes for k8s_helm_releases
    op.execute("CREATE INDEX idx_k8s_helm_cluster ON k8s_helm_releases(cluster_id);")
    op.execute("CREATE INDEX idx_k8s_helm_ns ON k8s_helm_releases(namespace_id);")
    op.execute("CREATE INDEX idx_k8s_helm_status ON k8s_helm_releases(status);")
    op.execute("CREATE INDEX idx_k8s_helm_chart ON k8s_helm_releases(chart_name);")
    
    # =====================================================================
    # TABLE 8: k8s_cost_attribution
    # =====================================================================
    op.execute("""
        CREATE TABLE k8s_cost_attribution (
            id BIGSERIAL PRIMARY KEY,
            cluster_id VARCHAR(36) NOT NULL,
            namespace_id VARCHAR(36) NOT NULL,
            organization_id VARCHAR(36) NOT NULL,
            
            -- Time Period
            date DATE NOT NULL,
            hour INTEGER,
            
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
    """)
    
    # Indexes for k8s_cost_attribution
    op.execute("CREATE INDEX idx_k8s_cost_cluster_date ON k8s_cost_attribution(cluster_id, date);")
    op.execute("CREATE INDEX idx_k8s_cost_ns_date ON k8s_cost_attribution(namespace_id, date);")
    op.execute("CREATE INDEX idx_k8s_cost_org_date ON k8s_cost_attribution(organization_id, date);")
    op.execute("CREATE INDEX idx_k8s_cost_team ON k8s_cost_attribution(team_name, date);")
    op.execute("CREATE INDEX idx_k8s_cost_center ON k8s_cost_attribution(cost_center, date);")
    
    # =====================================================================
    # VIEW 1: v_k8s_cluster_health
    # =====================================================================
    op.execute("""
        CREATE VIEW v_k8s_cluster_health AS
        SELECT 
            c.id,
            c.organization_id,
            c.name,
            c.health_status,
            c.total_nodes,
            c.total_namespaces,
            c.total_pods,
            c.provider,
            c.environment,
            COUNT(DISTINCT n.id) FILTER (WHERE n.status = 'Ready') as healthy_nodes,
            COUNT(DISTINCT d.id) FILTER (WHERE d.health_status = 'healthy') as healthy_deployments,
            COALESCE(m.cpu_usage_cores, 0) as total_cpu_usage,
            COALESCE(m.memory_usage_bytes, 0) as total_memory_usage,
            c.estimated_monthly_cost,
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
                 c.provider, c.environment,
                 m.cpu_usage_cores, m.memory_usage_bytes, 
                 c.estimated_monthly_cost, c.last_sync_at;
    """)
    
    # =====================================================================
    # VIEW 2: v_k8s_namespace_costs
    # =====================================================================
    op.execute("""
        CREATE VIEW v_k8s_namespace_costs AS
        SELECT 
            n.id as namespace_id,
            n.cluster_id,
            n.organization_id,
            n.name as namespace_name,
            n.team_name,
            n.cost_center,
            COALESCE(SUM(ca.total_cost), 0) as cost_last_30d,
            COALESCE(AVG(ca.total_cost), 0) as avg_daily_cost,
            COALESCE(SUM(ca.cpu_core_hours), 0) as cpu_hours_last_30d,
            COALESCE(SUM(ca.memory_gb_hours), 0) as memory_gb_hours_last_30d,
            COALESCE(SUM(ca.storage_gb_hours), 0) as storage_gb_hours_last_30d,
            COALESCE(SUM(ca.network_gb), 0) as network_gb_last_30d
        FROM k8s_namespaces n
        LEFT JOIN k8s_cost_attribution ca ON n.id = ca.namespace_id
            AND ca.date >= CURRENT_DATE - INTERVAL '30 days'
            AND ca.hour IS NULL
        GROUP BY n.id, n.cluster_id, n.organization_id, n.name, 
                 n.team_name, n.cost_center;
    """)
    
    print("✅ Created 8 Kubernetes tables")
    print("✅ Created 24 partitions (12 pods + 12 metrics for 2026)")
    print("✅ Created 2 views (cluster_health, namespace_costs)")
    print("✅ Created 30+ indexes for performance")


def downgrade():
    """Drop all Kubernetes tables and views"""
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS v_k8s_namespace_costs;")
    op.execute("DROP VIEW IF EXISTS v_k8s_cluster_health;")
    
    # Drop tables (cascades to partitions)
    op.execute("DROP TABLE IF EXISTS k8s_cost_attribution CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_helm_releases CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_resource_metrics CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_pods CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_deployments CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_nodes CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_namespaces CASCADE;")
    op.execute("DROP TABLE IF EXISTS k8s_clusters CASCADE;")
    
    print("✅ Dropped all Kubernetes tables and views")
