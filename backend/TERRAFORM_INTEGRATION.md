# Epic 19: Terraform/IaC Integration

## Overview
Complete Infrastructure as Code management system for multi-cloud provisioning, state management, and drift detection.

## Features

### Core Capabilities
- **Workspace Management**: Isolated Terraform environments with locking
- **State Management**: State file versioning with rollback capability
- **Resource Tracking**: Real-time infrastructure resource monitoring
- **Execution History**: Plan/apply/destroy operation tracking
- **Template Library**: Pre-built IaC templates for common infrastructure
- **Variable Management**: Workspace-specific variables with sensitive masking
- **Drift Detection**: Infrastructure configuration drift tracking

### Multi-Cloud Support
- AWS
- Azure
- Google Cloud Platform (GCP)
- DigitalOcean
- Kubernetes
- Multi-cloud deployments

## Database Schema

### Tables (9)

1. **terraform_workspaces**
   - Isolated Terraform environments
   - Workspace locking to prevent concurrent modifications
   - Cloud provider and environment categorization
   - Auto-apply configuration
   - State version tracking

2. **terraform_states**
   - State file versioning
   - `is_current` flag for rollback capability
   - Serial and lineage tracking
   - JSONB state data storage

3. **terraform_resources**
   - Infrastructure resource catalog
   - Resource type and provider tracking
   - Status tracking (active, tainted, destroyed)
   - Dependencies mapping
   - Attributes storage in JSONB

4. **terraform_executions**
   - Plan/apply/destroy history
   - Execution duration calculation
   - Resource change counts (created, changed, destroyed)
   - Plan output and error logging
   - Exit code tracking

5. **iac_templates**
   - Template library
   - Category-based organization (compute, networking, storage, etc.)
   - Variables and outputs definition
   - Download counter
   - Version tracking
   - Tags for searchability

6. **terraform_variables**
   - Workspace-specific variables
   - Sensitive value masking
   - HCL vs. string value distinction
   - Description field

7. **terraform_drift_detections**
   - Drift type categorization (configuration, state, manual)
   - Expected vs. actual state comparison
   - Differences tracking in JSONB
   - Resolution status

8. **cloud_credentials**
   - Encrypted credential storage
   - Multi-provider support
   - Region-specific configurations

9. **workspace_credentials**
   - Many-to-many mapping
   - Workspace to credentials association

### Views (3)

1. **terraform_workspace_summary**: Aggregated workspace statistics
2. **recent_terraform_executions**: Latest 100 executions across all workspaces
3. **resource_type_distribution**: Resource counts by provider and type

## API Endpoints

All endpoints are prefixed with `/api/v1/terraform`

### Workspace Management
- `POST /workspaces` - Create new workspace
- `GET /workspaces` - List workspaces (filterable by provider, environment)
- `GET /workspaces/{id}` - Get workspace details
- `POST /workspaces/{id}/lock` - Lock workspace
- `POST /workspaces/{id}/unlock` - Unlock workspace

### State Management
- `GET /workspaces/{id}/state` - Get current Terraform state

### Resource Management
- `GET /workspaces/{id}/resources` - List workspace resources (filterable by type)

### Execution History
- `GET /workspaces/{id}/executions` - Get workspace execution history
- `GET /executions/recent` - Get recent executions across all workspaces

### Template Library
- `GET /templates` - List IaC templates (filterable by provider, category)
- `GET /templates/{id}` - Get template details

### Variable Management
- `POST /workspaces/{id}/variables` - Set workspace variable
- `GET /workspaces/{id}/variables` - List workspace variables

### Drift Detection
- `GET /workspaces/{id}/drifts` - Get drift detections

### Dashboard
- `GET /dashboard/statistics` - Get Terraform dashboard statistics

## Frontend Components

### TerraformDashboard.jsx
Location: `/src/pages/admin/TerraformDashboard.jsx`

**Tabs:**
1. **Overview**: Recent workspaces and popular templates
2. **Workspaces**: Workspace cards with selection
3. **Resources**: Resource table with type and status
4. **Executions**: Execution history with status indicators
5. **Templates**: Template library browser
6. **Drift Detections**: Configuration drift alerts

**Navigation**: Admin → System → Terraform / IaC

## Pre-Seeded Templates

1. **AWS EC2 Instance**
   - Category: compute
   - Variables: instance_type, ami_id
   - Outputs: instance_id, public_ip

2. **Kubernetes Namespace**
   - Category: kubernetes
   - Variables: namespace_name, cpu_limit, memory_limit
   - Resource quotas included

3. **Azure Virtual Machine**
   - Category: compute
   - Variables: location, vm_size
   - Managed disk configuration

4. **GCP Compute Instance**
   - Category: compute
   - Variables: project_id, zone, machine_type

5. **AWS S3 Bucket**
   - Category: storage
   - Variables: bucket_name, enable_versioning
   - Encryption enabled by default

## Backend Components

### TerraformManager (`backend/terraform_manager.py`)

**Global Singleton:**
```python
from terraform_manager import get_terraform_manager

tm = get_terraform_manager()
```

**Key Methods:**
- `create_workspace(name, cloud_provider, environment, ...)` - Creates workspace and filesystem directory
- `lock_workspace(workspace_id, locked_by)` - Prevents concurrent modifications
- `unlock_workspace(workspace_id)` - Releases workspace lock
- `save_state(workspace_id, state_data, created_by)` - Versions state file
- `get_current_state(workspace_id)` - Returns active state
- `sync_resources(workspace_id, state_id, resources)` - Syncs resources from Terraform state
- `get_resources(workspace_id, resource_type, status)` - Filtered resource list
- `create_execution(workspace_id, execution_type, triggered_by)` - Creates execution record
- `update_execution(execution_id, status, plan_output, ...)` - Updates execution with results
- `get_templates(cloud_provider, category)` - Template library
- `set_variable(workspace_id, key, value, is_sensitive)` - UPSERT variable
- `get_variables(workspace_id, include_sensitive)` - Masks sensitive values
- `record_drift(workspace_id, resource_id, drift_type, ...)` - Records drift detection
- `get_statistics()` - Dashboard aggregated metrics

**Terraform Directory:** `/var/lib/terraform/{workspace_id}/`

## Configuration

### Initialization
The Terraform manager is initialized in `backend/server.py` during startup:

```python
from terraform_manager import init_terraform_manager
init_terraform_manager(db_pool)
```

### Environment-Specific Settings
- **Development**: dev environment workspaces
- **Staging**: staging environment workspaces
- **Production**: production environment workspaces
- **Test**: test environment workspaces

## Usage Examples

### Creating a Workspace
```bash
curl -X POST http://localhost:8000/api/v1/terraform/workspaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-aws-infrastructure",
    "cloud_provider": "aws",
    "environment": "production",
    "description": "Production AWS infrastructure",
    "terraform_version": "1.6.0",
    "auto_apply": false
  }'
```

### Listing Templates
```bash
curl http://localhost:8000/api/v1/terraform/templates?cloud_provider=aws
```

### Setting Variables
```bash
curl -X POST http://localhost:8000/api/v1/terraform/workspaces/{workspace_id}/variables \
  -H "Content-Type: application/json" \
  -d '{
    "key": "aws_access_key_id",
    "value": "AKIAIOSFODNN7EXAMPLE",
    "is_sensitive": true,
    "description": "AWS access key"
  }'
```

## Security Features

### Credential Protection
- Cloud credentials stored with encryption
- Sensitive variables masked by default
- Workspace locking prevents concurrent state modifications

### Access Control
- Requires authenticated user (via `require_authenticated_user`)
- Workspace isolation
- Audit trail via execution history

## Future Enhancements

### Phase 2 (Planned)
- Terraform CLI integration (actual plan/apply/destroy execution)
- State file encryption at rest
- Remote state backend configuration (S3, Azure Blob, GCS)
- Drift detection scheduler (automated periodic checks)
- Resource visualization (dependency graphs)
- Workspace creation wizard
- Template import/export
- Terraform module registry
- Cost estimation integration
- Policy as Code (OPA/Sentinel)

## Files Created

1. **Database**
   - `/home/ubuntu/Ops-Center-OSS/scripts/create_terraform_schema.sql` (~550 lines)

2. **Backend**
   - `/home/ubuntu/Ops-Center-OSS/backend/terraform_manager.py` (~650 lines)
   - `/home/ubuntu/Ops-Center-OSS/backend/terraform_api.py` (~550 lines)

3. **Frontend**
   - `/home/ubuntu/Ops-Center-OSS/src/pages/admin/TerraformDashboard.jsx` (~600 lines)

4. **Configuration**
   - Updated: `backend/server.py` (import, router, initialization)
   - Updated: `src/components/Layout.jsx` (menu item)
   - Updated: `src/App.jsx` (route)

## Deployment Status

✅ **Epic 19 Complete**
- Database schema created and executed
- Backend manager implemented
- REST API endpoints deployed
- Frontend dashboard built and bundled (12.30 kB gzipped)
- Navigation menu item added
- System initialized and operational

**Logs Confirm:**
```
INFO:server:🏗️  Terraform/IaC API registered at /api/v1/terraform (Epic 19)
INFO:terraform_manager:TerraformManager initialized
INFO:server:Terraform Manager initialized successfully
```

## Access

Navigate to: **Admin → System → Terraform / IaC**

API Documentation: `http://localhost:8000/api/docs#/terraform`
