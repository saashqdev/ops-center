-- Epic 19: Terraform/IaC Integration Database Schema
-- Infrastructure as Code management with Terraform state tracking

-- Terraform workspaces for isolated state management
CREATE TABLE IF NOT EXISTS terraform_workspaces (
    workspace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    cloud_provider TEXT NOT NULL, -- aws, azure, gcp, digitalocean, kubernetes, multi
    environment TEXT NOT NULL, -- dev, staging, production, test
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_apply_at TIMESTAMP,
    state_version INTEGER DEFAULT 0,
    locked BOOLEAN DEFAULT false,
    locked_by TEXT,
    locked_at TIMESTAMP,
    auto_apply BOOLEAN DEFAULT false,
    terraform_version TEXT DEFAULT '1.6.0',
    UNIQUE(name, environment)
);

-- Terraform state files (encrypted storage)
CREATE TABLE IF NOT EXISTS terraform_states (
    state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES terraform_workspaces(workspace_id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    serial INTEGER NOT NULL,
    lineage TEXT NOT NULL,
    state_data JSONB NOT NULL, -- Encrypted Terraform state
    resources_count INTEGER DEFAULT 0,
    outputs JSONB,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    terraform_version TEXT,
    is_current BOOLEAN DEFAULT true,
    UNIQUE(workspace_id, version)
);

CREATE INDEX idx_terraform_states_workspace ON terraform_states(workspace_id);
CREATE INDEX idx_terraform_states_current ON terraform_states(workspace_id, is_current);

-- Infrastructure resources tracked by Terraform
CREATE TABLE IF NOT EXISTS terraform_resources (
    resource_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES terraform_workspaces(workspace_id) ON DELETE CASCADE,
    state_id UUID REFERENCES terraform_states(state_id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL, -- aws_instance, azurerm_vm, google_compute_instance, etc.
    resource_name TEXT NOT NULL,
    provider TEXT NOT NULL, -- aws, azurerm, google, digitalocean, kubernetes
    address TEXT NOT NULL, -- Full Terraform address (e.g., module.web.aws_instance.server[0])
    attributes JSONB, -- Resource attributes
    dependencies TEXT[], -- Resource dependencies
    status TEXT DEFAULT 'active', -- active, tainted, destroyed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    destroyed_at TIMESTAMP,
    UNIQUE(workspace_id, address)
);

CREATE INDEX idx_terraform_resources_workspace ON terraform_resources(workspace_id);
CREATE INDEX idx_terraform_resources_type ON terraform_resources(resource_type);
CREATE INDEX idx_terraform_resources_status ON terraform_resources(status);

-- Terraform execution history (plan, apply, destroy)
CREATE TABLE IF NOT EXISTS terraform_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES terraform_workspaces(workspace_id) ON DELETE CASCADE,
    execution_type TEXT NOT NULL, -- plan, apply, destroy, refresh, import
    status TEXT DEFAULT 'running', -- running, success, failed, cancelled
    triggered_by TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    plan_output JSONB, -- Changes to be made
    resources_to_add INTEGER DEFAULT 0,
    resources_to_change INTEGER DEFAULT 0,
    resources_to_destroy INTEGER DEFAULT 0,
    error_message TEXT,
    exit_code INTEGER,
    log_file TEXT, -- Path to execution logs
    auto_applied BOOLEAN DEFAULT false
);

CREATE INDEX idx_terraform_executions_workspace ON terraform_executions(workspace_id);
CREATE INDEX idx_terraform_executions_type ON terraform_executions(execution_type);
CREATE INDEX idx_terraform_executions_status ON terraform_executions(status);

-- IaC templates library
CREATE TABLE IF NOT EXISTS iac_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT, -- compute, networking, storage, database, security, kubernetes, monitoring
    cloud_provider TEXT NOT NULL, -- aws, azure, gcp, digitalocean, kubernetes, multi
    template_type TEXT DEFAULT 'terraform', -- terraform, cloudformation, arm, pulumi
    source_code TEXT NOT NULL, -- Terraform/IaC code
    variables JSONB, -- Template variables schema
    outputs JSONB, -- Expected outputs
    version TEXT DEFAULT '1.0.0',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT false,
    downloads_count INTEGER DEFAULT 0,
    tags TEXT[]
);

CREATE INDEX idx_iac_templates_provider ON iac_templates(cloud_provider);
CREATE INDEX idx_iac_templates_category ON iac_templates(category);
CREATE INDEX idx_iac_templates_public ON iac_templates(is_public);

-- Workspace variables (Terraform variables)
CREATE TABLE IF NOT EXISTS terraform_variables (
    variable_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES terraform_workspaces(workspace_id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT, -- Encrypted for sensitive values
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    is_hcl BOOLEAN DEFAULT false, -- Whether value is HCL (complex types)
    category TEXT DEFAULT 'terraform', -- terraform, environment
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_id, key, category)
);

CREATE INDEX idx_terraform_variables_workspace ON terraform_variables(workspace_id);

-- Resource drift detection
CREATE TABLE IF NOT EXISTS terraform_drift_detections (
    drift_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES terraform_workspaces(workspace_id) ON DELETE CASCADE,
    resource_id UUID REFERENCES terraform_resources(resource_id) ON DELETE CASCADE,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    drift_type TEXT, -- modified, deleted, external_creation
    expected_state JSONB,
    actual_state JSONB,
    differences JSONB, -- Detailed diff
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP,
    resolved_by TEXT
);

CREATE INDEX idx_drift_detections_workspace ON terraform_drift_detections(workspace_id);
CREATE INDEX idx_drift_detections_resolved ON terraform_drift_detections(resolved);

-- Cloud provider credentials (encrypted)
CREATE TABLE IF NOT EXISTS cloud_credentials (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    provider TEXT NOT NULL, -- aws, azure, gcp, digitalocean, kubernetes
    credentials JSONB NOT NULL, -- Encrypted credentials
    region TEXT,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    is_default BOOLEAN DEFAULT false,
    UNIQUE(name, provider)
);

CREATE INDEX idx_cloud_credentials_provider ON cloud_credentials(provider);

-- Workspace to credentials mapping
CREATE TABLE IF NOT EXISTS workspace_credentials (
    workspace_id UUID REFERENCES terraform_workspaces(workspace_id) ON DELETE CASCADE,
    credential_id UUID REFERENCES cloud_credentials(credential_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, credential_id)
);

-- Seed some example templates
INSERT INTO iac_templates (name, description, category, cloud_provider, source_code, variables, outputs, tags) VALUES
('AWS EC2 Instance', 'Basic AWS EC2 instance with security group', 'compute', 'aws', 
'terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "AMI ID"
  type        = string
}

resource "aws_instance" "main" {
  ami           = var.ami_id
  instance_type = var.instance_type

  tags = {
    Name = "terraform-instance"
  }
}

output "instance_id" {
  value = aws_instance.main.id
}

output "public_ip" {
  value = aws_instance.main.public_ip
}',
'{"instance_type": {"type": "string", "default": "t3.micro"}, "ami_id": {"type": "string", "required": true}}'::jsonb,
'{"instance_id": "string", "public_ip": "string"}'::jsonb,
ARRAY['aws', 'compute', 'ec2']),

('Kubernetes Namespace', 'Create Kubernetes namespace with resource quotas', 'kubernetes', 'kubernetes',
'terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

variable "namespace_name" {
  description = "Namespace name"
  type        = string
}

variable "cpu_limit" {
  description = "CPU limit"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit"
  type        = string
  default     = "4Gi"
}

resource "kubernetes_namespace" "main" {
  metadata {
    name = var.namespace_name
  }
}

resource "kubernetes_resource_quota" "main" {
  metadata {
    name      = "${var.namespace_name}-quota"
    namespace = kubernetes_namespace.main.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.cpu_limit
      "requests.memory" = var.memory_limit
      "limits.cpu"      = var.cpu_limit
      "limits.memory"   = var.memory_limit
    }
  }
}

output "namespace" {
  value = kubernetes_namespace.main.metadata[0].name
}',
'{"namespace_name": {"type": "string", "required": true}, "cpu_limit": {"type": "string", "default": "2"}, "memory_limit": {"type": "string", "default": "4Gi"}}'::jsonb,
'{"namespace": "string"}'::jsonb,
ARRAY['kubernetes', 'namespace', 'quota']),

('Azure VM', 'Azure Virtual Machine with managed disk', 'compute', 'azure',
'terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "vm_size" {
  description = "VM size"
  type        = string
  default     = "Standard_B2s"
}

resource "azurerm_resource_group" "main" {
  name     = "rg-terraform"
  location = var.location
}

resource "azurerm_virtual_network" "main" {
  name                = "vnet-main"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_subnet" "main" {
  name                 = "subnet-main"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

output "resource_group_id" {
  value = azurerm_resource_group.main.id
}',
'{"location": {"type": "string", "default": "eastus"}, "vm_size": {"type": "string", "default": "Standard_B2s"}}'::jsonb,
'{"resource_group_id": "string"}'::jsonb,
ARRAY['azure', 'compute', 'vm']),

('GCP Compute Instance', 'Google Cloud Compute Engine instance', 'compute', 'gcp',
'terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Machine type"
  type        = string
  default     = "e2-micro"
}

resource "google_compute_instance" "main" {
  name         = "terraform-instance"
  machine_type = var.machine_type
  zone         = var.zone
  project      = var.project_id

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
  }
}

output "instance_id" {
  value = google_compute_instance.main.instance_id
}',
'{"project_id": {"type": "string", "required": true}, "zone": {"type": "string", "default": "us-central1-a"}, "machine_type": {"type": "string", "default": "e2-micro"}}'::jsonb,
'{"instance_id": "string"}'::jsonb,
ARRAY['gcp', 'compute', 'instance']),

('S3 Bucket with Versioning', 'AWS S3 bucket with versioning and encryption', 'storage', 'aws',
'terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning"
  type        = bool
  default     = true
}

resource "aws_s3_bucket" "main" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "bucket_id" {
  value = aws_s3_bucket.main.id
}

output "bucket_arn" {
  value = aws_s3_bucket.main.arn
}',
'{"bucket_name": {"type": "string", "required": true}, "enable_versioning": {"type": "bool", "default": true}}'::jsonb,
'{"bucket_id": "string", "bucket_arn": "string"}'::jsonb,
ARRAY['aws', 'storage', 's3', 'security']);

-- Update timestamps automatically
UPDATE iac_templates SET updated_at = CURRENT_TIMESTAMP;

-- Views for dashboard
CREATE OR REPLACE VIEW terraform_workspace_summary AS
SELECT 
    w.workspace_id,
    w.name,
    w.environment,
    w.cloud_provider,
    w.locked,
    w.last_apply_at,
    COUNT(DISTINCT r.resource_id) as resource_count,
    COUNT(DISTINCT CASE WHEN r.status = 'active' THEN r.resource_id END) as active_resources,
    COUNT(DISTINCT d.drift_id) as drift_count,
    MAX(e.triggered_at) as last_execution_at
FROM terraform_workspaces w
LEFT JOIN terraform_resources r ON w.workspace_id = r.workspace_id
LEFT JOIN terraform_drift_detections d ON w.workspace_id = d.workspace_id AND d.resolved = false
LEFT JOIN terraform_executions e ON w.workspace_id = e.workspace_id
GROUP BY w.workspace_id;

CREATE OR REPLACE VIEW recent_terraform_executions AS
SELECT 
    e.execution_id,
    e.workspace_id,
    w.name as workspace_name,
    e.execution_type,
    e.status,
    e.triggered_by,
    e.triggered_at,
    e.duration_seconds,
    e.resources_to_add,
    e.resources_to_change,
    e.resources_to_destroy
FROM terraform_executions e
JOIN terraform_workspaces w ON e.workspace_id = w.workspace_id
ORDER BY e.triggered_at DESC
LIMIT 100;

CREATE OR REPLACE VIEW resource_type_distribution AS
SELECT 
    provider,
    resource_type,
    COUNT(*) as count,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count
FROM terraform_resources
GROUP BY provider, resource_type
ORDER BY count DESC;

COMMENT ON TABLE terraform_workspaces IS 'Terraform workspaces for isolated infrastructure state';
COMMENT ON TABLE terraform_states IS 'Terraform state files with version history';
COMMENT ON TABLE terraform_resources IS 'Infrastructure resources managed by Terraform';
COMMENT ON TABLE terraform_executions IS 'History of Terraform plan/apply/destroy executions';
COMMENT ON TABLE iac_templates IS 'Reusable IaC templates library';
COMMENT ON TABLE terraform_variables IS 'Workspace-specific Terraform variables';
COMMENT ON TABLE terraform_drift_detections IS 'Infrastructure drift detection results';
COMMENT ON TABLE cloud_credentials IS 'Cloud provider credentials for Terraform';
