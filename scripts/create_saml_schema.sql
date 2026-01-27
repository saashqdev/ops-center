-- ============================================================================
-- EPIC 20: SAML Support - Database Schema
-- ============================================================================
-- SAML (Security Assertion Markup Language) SSO Integration
--
-- Features:
-- - Multi-provider SAML configuration
-- - SAML session management
-- - Assertion validation and storage
-- - SP (Service Provider) metadata generation
-- - IdP (Identity Provider) metadata parsing
-- - Attribute mapping
-- - JIT (Just-In-Time) user provisioning
-- ============================================================================

-- Drop existing tables if recreating
DROP TABLE IF EXISTS saml_sessions CASCADE;
DROP TABLE IF EXISTS saml_assertions CASCADE;
DROP TABLE IF EXISTS saml_attribute_mappings CASCADE;
DROP TABLE IF EXISTS saml_providers CASCADE;
DROP TABLE IF EXISTS saml_audit_log CASCADE;

-- ============================================================================
-- SAML Providers Configuration
-- ============================================================================
CREATE TABLE saml_providers (
    provider_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID, -- Optional: link to organization if org feature exists
    
    -- Provider Identity
    name VARCHAR(255) NOT NULL,
    entity_id VARCHAR(500) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    description TEXT,
    
    -- IdP Configuration
    idp_entity_id VARCHAR(500) NOT NULL,
    idp_sso_url VARCHAR(1000) NOT NULL,
    idp_slo_url VARCHAR(1000),
    idp_certificate TEXT NOT NULL, -- X.509 certificate for signature verification
    
    -- SP Configuration
    sp_entity_id VARCHAR(500) NOT NULL,
    sp_acs_url VARCHAR(1000) NOT NULL, -- Assertion Consumer Service URL
    sp_slo_url VARCHAR(1000),
    sp_private_key TEXT, -- Optional: for encrypted assertions
    sp_certificate TEXT, -- Optional: for signed requests
    
    -- SAML Settings
    name_id_format VARCHAR(255) DEFAULT 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
    authn_context VARCHAR(255) DEFAULT 'urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport',
    want_assertions_signed BOOLEAN DEFAULT true,
    want_assertions_encrypted BOOLEAN DEFAULT false,
    sign_requests BOOLEAN DEFAULT false,
    
    -- Binding Configuration
    binding_type VARCHAR(50) DEFAULT 'HTTP-POST', -- HTTP-POST, HTTP-Redirect, HTTP-Artifact
    
    -- User Provisioning
    enable_jit_provisioning BOOLEAN DEFAULT true,
    default_role VARCHAR(50) DEFAULT 'user',
    auto_create_organizations BOOLEAN DEFAULT false,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    
    -- Metadata
    metadata JSONB, -- Store full IdP metadata
    last_metadata_refresh TIMESTAMP,
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(255)
);

CREATE INDEX idx_saml_providers_org ON saml_providers(organization_id);
CREATE INDEX idx_saml_providers_entity ON saml_providers(entity_id);
CREATE INDEX idx_saml_providers_active ON saml_providers(is_active);

COMMENT ON TABLE saml_providers IS 'SAML 2.0 Identity Provider configurations';
COMMENT ON COLUMN saml_providers.idp_certificate IS 'X.509 certificate in PEM format for validating SAML assertions';
COMMENT ON COLUMN saml_providers.name_id_format IS 'Format for NameID in SAML assertions';
COMMENT ON COLUMN saml_providers.enable_jit_provisioning IS 'Just-In-Time user provisioning on first SAML login';

-- ============================================================================
-- SAML Attribute Mappings
-- ============================================================================
CREATE TABLE saml_attribute_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES saml_providers(provider_id) ON DELETE CASCADE,
    
    -- Attribute Mapping
    saml_attribute VARCHAR(255) NOT NULL, -- e.g., 'email', 'firstName', 'department'
    user_field VARCHAR(100) NOT NULL,     -- e.g., 'email', 'first_name', 'role'
    is_required BOOLEAN DEFAULT false,
    default_value TEXT,
    
    -- Transformation
    transform_type VARCHAR(50), -- 'lowercase', 'uppercase', 'trim', 'regex', 'custom'
    transform_config JSONB,
    
    -- Validation
    validation_regex VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saml_attr_provider ON saml_attribute_mappings(provider_id);

COMMENT ON TABLE saml_attribute_mappings IS 'Map SAML assertion attributes to user fields';

-- Pre-populate standard mappings for a default provider
-- These will be inserted when a provider is created
-- Example mappings:
-- email -> email (required)
-- givenName -> first_name
-- surname -> last_name
-- displayName -> display_name
-- role -> role
-- department -> department

-- ============================================================================
-- SAML Sessions
-- ============================================================================
CREATE TABLE saml_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES saml_providers(provider_id) ON DELETE CASCADE,
    
    -- Session Identity
    saml_session_id VARCHAR(255) UNIQUE, -- SessionIndex from SAML assertion
    name_id VARCHAR(500) NOT NULL,       -- NameID from SAML assertion
    name_id_format VARCHAR(255),
    
    -- User Association
    user_id UUID, -- Optional: link to user if users table exists
    email VARCHAR(255),
    
    -- Session Lifecycle
    session_start TIMESTAMP DEFAULT NOW(),
    session_expiry TIMESTAMP,
    not_on_or_after TIMESTAMP,
    
    -- Authentication Context
    authn_context VARCHAR(255),
    authn_instant TIMESTAMP,
    
    -- Session Data
    attributes JSONB, -- All SAML attributes from assertion
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    logout_requested BOOLEAN DEFAULT false,
    logout_at TIMESTAMP,
    
    -- Request Tracking
    relay_state VARCHAR(500),
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saml_sessions_provider ON saml_sessions(provider_id);
CREATE INDEX idx_saml_sessions_user ON saml_sessions(user_id);
CREATE INDEX idx_saml_sessions_saml_id ON saml_sessions(saml_session_id);
CREATE INDEX idx_saml_sessions_active ON saml_sessions(is_active);
CREATE INDEX idx_saml_sessions_expiry ON saml_sessions(session_expiry);

COMMENT ON TABLE saml_sessions IS 'Active SAML SSO sessions for authenticated users';
COMMENT ON COLUMN saml_sessions.saml_session_id IS 'SessionIndex from SAML assertion for logout';
COMMENT ON COLUMN saml_sessions.relay_state IS 'Original request URL to redirect after authentication';

-- ============================================================================
-- SAML Assertions (Audit Trail)
-- ============================================================================
CREATE TABLE saml_assertions (
    assertion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES saml_providers(provider_id) ON DELETE CASCADE,
    session_id UUID REFERENCES saml_sessions(session_id) ON DELETE SET NULL,
    
    -- Assertion Details
    assertion_xml TEXT,              -- Full SAML assertion for audit
    assertion_hash VARCHAR(64),      -- SHA-256 hash for integrity
    
    -- Validation Results
    is_valid BOOLEAN NOT NULL,
    validation_errors JSONB,
    
    -- Signature Verification
    signature_verified BOOLEAN,
    certificate_thumbprint VARCHAR(64),
    
    -- Timing
    issue_instant TIMESTAMP,
    not_before TIMESTAMP,
    not_on_or_after TIMESTAMP,
    
    -- Identity
    name_id VARCHAR(500),
    name_id_format VARCHAR(255),
    
    -- Attributes
    attributes JSONB,
    
    -- Request Info
    in_response_to VARCHAR(255),    -- ID of the original AuthnRequest
    relay_state VARCHAR(500),
    ip_address VARCHAR(45),
    
    -- Audit
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saml_assertions_provider ON saml_assertions(provider_id);
CREATE INDEX idx_saml_assertions_session ON saml_assertions(session_id);
CREATE INDEX idx_saml_assertions_received ON saml_assertions(received_at);
CREATE INDEX idx_saml_assertions_valid ON saml_assertions(is_valid);

COMMENT ON TABLE saml_assertions IS 'Audit trail of all received SAML assertions';
COMMENT ON COLUMN saml_assertions.assertion_xml IS 'Full SAML assertion XML for compliance and debugging';

-- ============================================================================
-- SAML Audit Log
-- ============================================================================
CREATE TABLE saml_audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES saml_providers(provider_id) ON DELETE SET NULL,
    session_id UUID REFERENCES saml_sessions(session_id) ON DELETE SET NULL,
    
    -- Event Details
    event_type VARCHAR(50) NOT NULL, -- 'login', 'logout', 'metadata_refresh', 'validation_error', 'config_change'
    event_status VARCHAR(20) NOT NULL, -- 'success', 'failure', 'warning'
    
    -- Context
    user_id UUID, -- Optional: link to user
    email VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Event Data
    event_data JSONB,
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saml_audit_provider ON saml_audit_log(provider_id);
CREATE INDEX idx_saml_audit_user ON saml_audit_log(user_id);
CREATE INDEX idx_saml_audit_type ON saml_audit_log(event_type);
CREATE INDEX idx_saml_audit_created ON saml_audit_log(created_at);

COMMENT ON TABLE saml_audit_log IS 'Comprehensive audit trail for SAML operations';

-- ============================================================================
-- Views for SAML Analytics
-- ============================================================================

-- Active SAML Sessions Summary
CREATE VIEW saml_active_sessions_summary AS
SELECT 
    sp.provider_id,
    sp.name AS provider_name,
    COUNT(DISTINCT ss.session_id) AS active_sessions,
    COUNT(DISTINCT ss.user_id) AS unique_users,
    MIN(ss.session_start) AS oldest_session,
    MAX(ss.session_start) AS newest_session
FROM saml_providers sp
LEFT JOIN saml_sessions ss ON sp.provider_id = ss.provider_id AND ss.is_active = true
GROUP BY sp.provider_id, sp.name;

COMMENT ON VIEW saml_active_sessions_summary IS 'Summary of active SAML sessions per provider';

-- SAML Login Activity (Last 30 days)
CREATE VIEW saml_login_activity AS
SELECT 
    sp.provider_id,
    sp.name AS provider_name,
    DATE(ss.session_start) AS login_date,
    COUNT(DISTINCT ss.session_id) AS login_count,
    COUNT(DISTINCT ss.user_id) AS unique_users
FROM saml_providers sp
LEFT JOIN saml_sessions ss ON sp.provider_id = ss.provider_id
WHERE ss.session_start >= NOW() - INTERVAL '30 days'
GROUP BY sp.provider_id, sp.name, DATE(ss.session_start)
ORDER BY login_date DESC;

COMMENT ON VIEW saml_login_activity IS 'SAML login activity for the last 30 days';

-- SAML Provider Health
CREATE VIEW saml_provider_health AS
SELECT 
    sp.provider_id,
    sp.name AS provider_name,
    sp.is_active,
    sp.last_metadata_refresh,
    COUNT(DISTINCT ss.session_id) FILTER (WHERE ss.is_active = true) AS active_sessions,
    COUNT(DISTINCT sa.assertion_id) FILTER (WHERE sa.received_at >= NOW() - INTERVAL '24 hours') AS assertions_24h,
    COUNT(DISTINCT sa.assertion_id) FILTER (WHERE sa.is_valid = false AND sa.received_at >= NOW() - INTERVAL '24 hours') AS failed_assertions_24h,
    COUNT(DISTINCT sal.log_id) FILTER (WHERE sal.event_type = 'validation_error' AND sal.created_at >= NOW() - INTERVAL '24 hours') AS errors_24h
FROM saml_providers sp
LEFT JOIN saml_sessions ss ON sp.provider_id = ss.provider_id
LEFT JOIN saml_assertions sa ON sp.provider_id = sa.provider_id
LEFT JOIN saml_audit_log sal ON sp.provider_id = sal.provider_id
GROUP BY sp.provider_id, sp.name, sp.is_active, sp.last_metadata_refresh;

COMMENT ON VIEW saml_provider_health IS 'Health metrics for SAML providers';

-- ============================================================================
-- Seed Data: Example SAML Provider Configuration
-- ============================================================================

-- Insert a template for Okta SAML provider (inactive by default)
INSERT INTO saml_providers (
    name, 
    entity_id, 
    display_name, 
    description,
    idp_entity_id,
    idp_sso_url,
    idp_certificate,
    sp_entity_id,
    sp_acs_url,
    is_active,
    enable_jit_provisioning
) VALUES (
    'okta_template',
    'https://your-ops-center.com/saml/metadata/okta',
    'Okta SSO (Template)',
    'Template configuration for Okta SAML integration. Configure with your Okta tenant details.',
    'http://www.okta.com/exk_TEMPLATE_ID',
    'https://your-okta-tenant.okta.com/app/your-app/exk_TEMPLATE_ID/sso/saml',
    '-----BEGIN CERTIFICATE-----
MIIDpDCCAoygAwIBAgIGAXXXXXXXXMA0GCSqGSIb3DQEBCwUAMIGSMQswCQYDVQQG
-- REPLACE WITH YOUR OKTA CERTIFICATE --
-----END CERTIFICATE-----',
    'https://your-ops-center.com/saml/sp',
    'https://your-ops-center.com/api/v1/saml/acs',
    false,
    true
);

-- Standard attribute mappings for Okta
INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'email',
    'email',
    true
FROM saml_providers WHERE name = 'okta_template';

INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'firstName',
    'first_name',
    false
FROM saml_providers WHERE name = 'okta_template';

INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'lastName',
    'last_name',
    false
FROM saml_providers WHERE name = 'okta_template';

INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'role',
    'role',
    false
FROM saml_providers WHERE name = 'okta_template';

-- ============================================================================
-- Seed Data: Azure AD / Entra ID SAML Template
-- ============================================================================

INSERT INTO saml_providers (
    name, 
    entity_id, 
    display_name, 
    description,
    idp_entity_id,
    idp_sso_url,
    idp_certificate,
    sp_entity_id,
    sp_acs_url,
    is_active,
    enable_jit_provisioning
) VALUES (
    'azure_ad_template',
    'https://your-ops-center.com/saml/metadata/azure',
    'Azure AD / Entra ID (Template)',
    'Template configuration for Microsoft Azure AD / Entra ID SAML integration.',
    'https://sts.windows.net/TENANT_ID/',
    'https://login.microsoftonline.com/TENANT_ID/saml2',
    '-----BEGIN CERTIFICATE-----
MIIDPjCCAiqgAwIBAgIQVWmXY/+9RqFA/OG9kFulHDAJBgUrDgMCHQUAMC0xKzAp
-- REPLACE WITH YOUR AZURE AD CERTIFICATE --
-----END CERTIFICATE-----',
    'https://your-ops-center.com/saml/sp',
    'https://your-ops-center.com/api/v1/saml/acs',
    false,
    true
);

-- Standard attribute mappings for Azure AD
INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
    'email',
    true
FROM saml_providers WHERE name = 'azure_ad_template';

INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
    'first_name',
    false
FROM saml_providers WHERE name = 'azure_ad_template';

INSERT INTO saml_attribute_mappings (provider_id, saml_attribute, user_field, is_required) 
SELECT 
    provider_id,
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
    'last_name',
    false
FROM saml_providers WHERE name = 'azure_ad_template';

-- ============================================================================
-- Functions for Session Management
-- ============================================================================

-- Function to clean up expired SAML sessions
CREATE OR REPLACE FUNCTION cleanup_expired_saml_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE saml_sessions
    SET is_active = false,
        logout_at = NOW()
    WHERE is_active = true
    AND (
        session_expiry < NOW()
        OR not_on_or_after < NOW()
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_saml_sessions IS 'Deactivate expired SAML sessions';

-- ============================================================================
-- Schema Summary
-- ============================================================================

SELECT 'SAML Schema Created Successfully!' AS status;
SELECT 'Tables Created:' AS info, COUNT(*) AS count FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'saml_%';
SELECT 'Views Created:' AS info, COUNT(*) AS count FROM information_schema.views 
WHERE table_schema = 'public' AND table_name LIKE 'saml_%';
SELECT 'Template Providers:' AS info, COUNT(*) AS count FROM saml_providers;
SELECT 'Attribute Mappings:' AS info, COUNT(*) AS count FROM saml_attribute_mappings;
