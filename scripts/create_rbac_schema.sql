-- Epic 17: Advanced RBAC System
-- Fine-grained permissions and resource-based access control
-- Created: 2026-01-27

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PERMISSIONS TABLE
-- Defines granular permissions (e.g., "users:create", "billing:read")
-- ============================================================================
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(50) NOT NULL, -- users, billing, servers, etc.
    action VARCHAR(50) NOT NULL,   -- create, read, update, delete, execute
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_resource_action UNIQUE(resource, action)
);

CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_action ON permissions(action);

-- ============================================================================
-- ROLES TABLE (Enhanced)
-- Extends existing role system with custom roles
-- ============================================================================
CREATE TABLE IF NOT EXISTS custom_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    organization_id VARCHAR(36), -- NULL for system-wide roles
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE, -- admin, user, etc. are system roles
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_custom_roles_org ON custom_roles(organization_id);
CREATE INDEX idx_custom_roles_system ON custom_roles(is_system_role);

-- ============================================================================
-- ROLE PERMISSIONS (Junction Table)
-- Maps roles to their permissions
-- ============================================================================
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES custom_roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(255),
    CONSTRAINT unique_role_permission UNIQUE(role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);

-- ============================================================================
-- USER ROLES (Junction Table)
-- Maps users to their roles
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    role_id INTEGER REFERENCES custom_roles(id) ON DELETE CASCADE,
    organization_id VARCHAR(36), -- Scope role to specific org
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(255),
    expires_at TIMESTAMP, -- Optional: time-limited roles
    CONSTRAINT unique_user_role_org UNIQUE(user_email, role_id, organization_id)
);

CREATE INDEX idx_user_roles_email ON user_roles(user_email);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_user_roles_org ON user_roles(organization_id);
CREATE INDEX idx_user_roles_expires ON user_roles(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- RESOURCE POLICIES
-- Define access policies for specific resources
-- ============================================================================
CREATE TABLE IF NOT EXISTS resource_policies (
    id SERIAL PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL, -- server, organization, billing_account, etc.
    resource_id VARCHAR(100) NOT NULL,
    policy_document JSONB NOT NULL, -- JSON policy definition
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_resource_policy UNIQUE(resource_type, resource_id)
);

CREATE INDEX idx_resource_policies_type ON resource_policies(resource_type);
CREATE INDEX idx_resource_policies_resource ON resource_policies(resource_id);
CREATE INDEX idx_resource_policies_document ON resource_policies USING GIN(policy_document);

-- ============================================================================
-- PERMISSION INHERITANCE
-- Define permission inheritance hierarchy (e.g., admin inherits from user)
-- ============================================================================
CREATE TABLE IF NOT EXISTS role_inheritance (
    id SERIAL PRIMARY KEY,
    parent_role_id INTEGER REFERENCES custom_roles(id) ON DELETE CASCADE,
    child_role_id INTEGER REFERENCES custom_roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_role_inheritance UNIQUE(parent_role_id, child_role_id),
    CONSTRAINT no_self_inheritance CHECK(parent_role_id != child_role_id)
);

CREATE INDEX idx_role_inheritance_parent ON role_inheritance(parent_role_id);
CREATE INDEX idx_role_inheritance_child ON role_inheritance(child_role_id);

-- ============================================================================
-- AUDIT LOG FOR RBAC CHANGES
-- Track all permission and role changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS rbac_audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- role_created, permission_granted, etc.
    actor_email VARCHAR(255) NOT NULL,
    target_user_email VARCHAR(255),
    role_id INTEGER,
    permission_id INTEGER,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rbac_audit_event ON rbac_audit_log(event_type);
CREATE INDEX idx_rbac_audit_actor ON rbac_audit_log(actor_email);
CREATE INDEX idx_rbac_audit_target ON rbac_audit_log(target_user_email);
CREATE INDEX idx_rbac_audit_created ON rbac_audit_log(created_at);

-- ============================================================================
-- SEED DEFAULT PERMISSIONS
-- ============================================================================

-- User Management Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('users:create', 'users', 'create', 'Create new users'),
    ('users:read', 'users', 'read', 'View user information'),
    ('users:update', 'users', 'update', 'Update user details'),
    ('users:delete', 'users', 'delete', 'Delete users'),
    ('users:list', 'users', 'list', 'List all users')
ON CONFLICT (resource, action) DO NOTHING;

-- Organization Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('organizations:create', 'organizations', 'create', 'Create organizations'),
    ('organizations:read', 'organizations', 'read', 'View organization details'),
    ('organizations:update', 'organizations', 'update', 'Update organization settings'),
    ('organizations:delete', 'organizations', 'delete', 'Delete organizations'),
    ('organizations:list', 'organizations', 'list', 'List organizations'),
    ('organizations:members', 'organizations', 'members', 'Manage organization members')
ON CONFLICT (resource, action) DO NOTHING;

-- Billing Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('billing:read', 'billing', 'read', 'View billing information'),
    ('billing:update', 'billing', 'update', 'Update billing settings'),
    ('billing:invoices', 'billing', 'invoices', 'Access invoices'),
    ('billing:payments', 'billing', 'payments', 'Manage payment methods')
ON CONFLICT (resource, action) DO NOTHING;

-- Server Management Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('servers:create', 'servers', 'create', 'Register new servers'),
    ('servers:read', 'servers', 'read', 'View server details'),
    ('servers:update', 'servers', 'update', 'Update server configuration'),
    ('servers:delete', 'servers', 'delete', 'Delete servers'),
    ('servers:restart', 'servers', 'restart', 'Restart servers'),
    ('servers:logs', 'servers', 'logs', 'View server logs')
ON CONFLICT (resource, action) DO NOTHING;

-- API Key Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('api_keys:create', 'api_keys', 'create', 'Create API keys'),
    ('api_keys:read', 'api_keys', 'read', 'View API keys'),
    ('api_keys:revoke', 'api_keys', 'revoke', 'Revoke API keys'),
    ('api_keys:delete', 'api_keys', 'delete', 'Delete API keys')
ON CONFLICT (resource, action) DO NOTHING;

-- Analytics Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('analytics:read', 'analytics', 'read', 'View analytics data'),
    ('analytics:export', 'analytics', 'export', 'Export analytics reports')
ON CONFLICT (resource, action) DO NOTHING;

-- Settings Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('settings:read', 'settings', 'read', 'View system settings'),
    ('settings:update', 'settings', 'update', 'Update system settings')
ON CONFLICT (resource, action) DO NOTHING;

-- Webhook Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('webhooks:create', 'webhooks', 'create', 'Create webhooks'),
    ('webhooks:read', 'webhooks', 'read', 'View webhooks'),
    ('webhooks:update', 'webhooks', 'update', 'Update webhooks'),
    ('webhooks:delete', 'webhooks', 'delete', 'Delete webhooks')
ON CONFLICT (resource, action) DO NOTHING;

-- ============================================================================
-- SEED DEFAULT ROLES
-- ============================================================================

-- System Roles
INSERT INTO custom_roles (name, description, is_system_role) VALUES
    ('super_admin', 'Full system access with all permissions', true),
    ('org_admin', 'Organization administrator with full org access', true),
    ('org_manager', 'Organization manager with limited admin capabilities', true),
    ('org_member', 'Standard organization member', true),
    ('billing_admin', 'Billing and payment management only', true),
    ('developer', 'API access and development tools', true),
    ('analyst', 'Read-only access to analytics and reports', true),
    ('support', 'Support team with read access and limited actions', true)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- ASSIGN PERMISSIONS TO DEFAULT ROLES
-- ============================================================================

-- Super Admin: ALL permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM custom_roles WHERE name = 'super_admin'),
    id
FROM permissions
ON CONFLICT DO NOTHING;

-- Org Admin: All permissions except system-level operations
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM custom_roles WHERE name = 'org_admin'),
    id
FROM permissions
WHERE resource IN ('users', 'organizations', 'billing', 'api_keys', 'analytics', 'webhooks')
ON CONFLICT DO NOTHING;

-- Org Manager: User management + read access
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM custom_roles WHERE name = 'org_manager'),
    id
FROM permissions
WHERE name IN (
    'users:read', 'users:list', 'users:update',
    'organizations:read', 'organizations:members',
    'billing:read', 'analytics:read'
)
ON CONFLICT DO NOTHING;

-- Developer: API and development tools
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM custom_roles WHERE name = 'developer'),
    id
FROM permissions
WHERE resource IN ('api_keys', 'webhooks', 'servers')
   OR name IN ('analytics:read', 'organizations:read')
ON CONFLICT DO NOTHING;

-- Analyst: Read-only access
INSERT INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM custom_roles WHERE name = 'analyst'),
    id
FROM permissions
WHERE action IN ('read', 'list')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: User permissions with role expansion
CREATE OR REPLACE VIEW user_effective_permissions AS
SELECT DISTINCT
    ur.user_email,
    ur.organization_id,
    p.name AS permission_name,
    p.resource,
    p.action,
    cr.name AS role_name
FROM user_roles ur
JOIN custom_roles cr ON ur.role_id = cr.id
JOIN role_permissions rp ON cr.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP);

-- View: Role summary with permission counts
CREATE OR REPLACE VIEW role_summary AS
SELECT 
    cr.id,
    cr.name,
    cr.description,
    cr.is_system_role,
    COUNT(rp.permission_id) AS permission_count,
    COUNT(DISTINCT ur.user_email) AS user_count,
    cr.created_at
FROM custom_roles cr
LEFT JOIN role_permissions rp ON cr.id = rp.role_id
LEFT JOIN user_roles ur ON cr.id = ur.role_id
GROUP BY cr.id, cr.name, cr.description, cr.is_system_role, cr.created_at;

COMMENT ON TABLE permissions IS 'Granular permissions for resource-based access control';
COMMENT ON TABLE custom_roles IS 'User-defined and system roles';
COMMENT ON TABLE role_permissions IS 'Permissions assigned to roles';
COMMENT ON TABLE user_roles IS 'Roles assigned to users';
COMMENT ON TABLE resource_policies IS 'Resource-specific access policies (JSON-based)';
COMMENT ON TABLE role_inheritance IS 'Role inheritance hierarchy';
COMMENT ON TABLE rbac_audit_log IS 'Audit trail for all RBAC changes';
