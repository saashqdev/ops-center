-- SOC2 Compliance Reporting Schema - Epic 18
-- Comprehensive compliance tracking and evidence collection
--
-- SOC2 Trust Service Criteria Coverage:
-- - Security (CC6.x): Access controls, authentication, authorization
-- - Availability (A1.x): System uptime, monitoring, incident response
-- - Processing Integrity (PI1.x): Data validation, error handling
-- - Confidentiality (C1.x): Encryption, access restrictions
-- - Privacy (P1.x): Data handling, retention, deletion

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== COMPLIANCE CONTROLS ====================

-- SOC2 compliance controls and their status
CREATE TABLE IF NOT EXISTS compliance_controls (
    id SERIAL PRIMARY KEY,
    control_id VARCHAR(50) UNIQUE NOT NULL,  -- e.g., CC6.1, A1.2
    category VARCHAR(50) NOT NULL,  -- Security, Availability, Processing Integrity, Confidentiality, Privacy
    title VARCHAR(255) NOT NULL,
    description TEXT,
    implementation_status VARCHAR(50) DEFAULT 'not_implemented',  -- not_implemented, in_progress, implemented, verified
    automated BOOLEAN DEFAULT false,  -- Can this control be automatically checked?
    check_frequency VARCHAR(50),  -- hourly, daily, weekly, monthly
    last_check_at TIMESTAMP,
    last_check_status VARCHAR(50),  -- passed, failed, warning, not_checked
    last_check_result JSONB,  -- Detailed check results
    evidence_required TEXT[],  -- Types of evidence needed
    assigned_to VARCHAR(255),  -- Email of responsible person
    target_completion_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_compliance_controls_category ON compliance_controls(category);
CREATE INDEX idx_compliance_controls_status ON compliance_controls(implementation_status);
CREATE INDEX idx_compliance_controls_automated ON compliance_controls(automated);

COMMENT ON TABLE compliance_controls IS 'SOC2 compliance controls and their implementation status';

-- ==================== COMPLIANCE EVIDENCE ====================

-- Evidence collected for compliance audits
CREATE TABLE IF NOT EXISTS compliance_evidence (
    id SERIAL PRIMARY KEY,
    evidence_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    control_id VARCHAR(50) REFERENCES compliance_controls(control_id),
    evidence_type VARCHAR(100) NOT NULL,  -- audit_log, configuration, screenshot, document, policy
    title VARCHAR(255) NOT NULL,
    description TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    collected_by VARCHAR(255),  -- Email of collector
    collection_method VARCHAR(50),  -- manual, automated
    data JSONB,  -- Evidence data
    file_path TEXT,  -- Path to file evidence (if applicable)
    file_hash VARCHAR(64),  -- SHA-256 hash for integrity
    retention_period_days INTEGER DEFAULT 2555,  -- 7 years default for SOC2
    expires_at TIMESTAMP,
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_compliance_evidence_control ON compliance_evidence(control_id);
CREATE INDEX idx_compliance_evidence_type ON compliance_evidence(evidence_type);
CREATE INDEX idx_compliance_evidence_collected ON compliance_evidence(collected_at);
CREATE INDEX idx_compliance_evidence_expires ON compliance_evidence(expires_at);

COMMENT ON TABLE compliance_evidence IS 'Evidence collected for SOC2 compliance audits';

-- ==================== COMPLIANCE REPORTS ====================

-- Generated compliance reports
CREATE TABLE IF NOT EXISTS compliance_reports (
    id SERIAL PRIMARY KEY,
    report_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    report_type VARCHAR(50) NOT NULL,  -- soc2_readiness, audit_summary, control_status, security_incidents
    title VARCHAR(255) NOT NULL,
    description TEXT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(255),  -- Email of generator
    format VARCHAR(20) DEFAULT 'pdf',  -- pdf, json, csv, html
    status VARCHAR(50) DEFAULT 'draft',  -- draft, final, approved, archived
    file_path TEXT,
    file_size_bytes BIGINT,
    findings_summary JSONB,  -- Summary of findings
    controls_passed INTEGER,
    controls_failed INTEGER,
    controls_warning INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_compliance_reports_type ON compliance_reports(report_type);
CREATE INDEX idx_compliance_reports_period ON compliance_reports(period_start, period_end);
CREATE INDEX idx_compliance_reports_generated ON compliance_reports(generated_at);

COMMENT ON TABLE compliance_reports IS 'Generated SOC2 compliance reports';

-- ==================== SECURITY INCIDENTS ====================

-- Security incidents for compliance tracking
CREATE TABLE IF NOT EXISTS security_incidents (
    id SERIAL PRIMARY KEY,
    incident_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(50) NOT NULL,  -- critical, high, medium, low, info
    incident_type VARCHAR(100) NOT NULL,  -- unauthorized_access, data_breach, ddos, malware, policy_violation
    status VARCHAR(50) DEFAULT 'open',  -- open, investigating, contained, resolved, closed
    detected_at TIMESTAMP NOT NULL,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reported_by VARCHAR(255),
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    affected_systems TEXT[],
    affected_users TEXT[],
    affected_data_types TEXT[],
    estimated_impact VARCHAR(50),  -- none, low, medium, high, critical
    root_cause TEXT,
    remediation_steps TEXT[],
    lessons_learned TEXT,
    evidence_ids UUID[],  -- References to compliance_evidence
    related_controls VARCHAR(50)[],  -- Related compliance controls
    notification_required BOOLEAN DEFAULT false,
    notification_sent BOOLEAN DEFAULT false,
    notification_sent_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_security_incidents_severity ON security_incidents(severity);
CREATE INDEX idx_security_incidents_status ON security_incidents(status);
CREATE INDEX idx_security_incidents_detected ON security_incidents(detected_at);
CREATE INDEX idx_security_incidents_type ON security_incidents(incident_type);

COMMENT ON TABLE security_incidents IS 'Security incidents for SOC2 compliance tracking';

-- ==================== COMPLIANCE SCHEDULES ====================

-- Scheduled compliance checks and reviews
CREATE TABLE IF NOT EXISTS compliance_schedules (
    id SERIAL PRIMARY KEY,
    schedule_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    control_id VARCHAR(50) REFERENCES compliance_controls(control_id),
    schedule_type VARCHAR(50) NOT NULL,  -- automated_check, manual_review, evidence_collection
    frequency VARCHAR(50) NOT NULL,  -- hourly, daily, weekly, monthly, quarterly, annually
    next_run_at TIMESTAMP NOT NULL,
    last_run_at TIMESTAMP,
    last_run_status VARCHAR(50),
    enabled BOOLEAN DEFAULT true,
    notification_emails TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_compliance_schedules_control ON compliance_schedules(control_id);
CREATE INDEX idx_compliance_schedules_next_run ON compliance_schedules(next_run_at);
CREATE INDEX idx_compliance_schedules_enabled ON compliance_schedules(enabled);

COMMENT ON TABLE compliance_schedules IS 'Scheduled compliance checks and evidence collection';

-- ==================== POLICY ACKNOWLEDGMENTS ====================

-- Track user acknowledgment of policies
CREATE TABLE IF NOT EXISTS policy_acknowledgments (
    id SERIAL PRIMARY KEY,
    acknowledgment_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    policy_version VARCHAR(50) NOT NULL,
    policy_content_hash VARCHAR(64),  -- SHA-256 of policy content
    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    acknowledgment_method VARCHAR(50),  -- ui, email, api
    expires_at TIMESTAMP,  -- For policies requiring periodic re-acknowledgment
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_policy_ack_user ON policy_acknowledgments(user_email);
CREATE INDEX idx_policy_ack_policy ON policy_acknowledgments(policy_name);
CREATE INDEX idx_policy_ack_date ON policy_acknowledgments(acknowledged_at);
CREATE INDEX idx_policy_ack_expires ON policy_acknowledgments(expires_at);

COMMENT ON TABLE policy_acknowledgments IS 'User acknowledgments of security and compliance policies';

-- ==================== DATA RETENTION POLICIES ====================

-- Data retention and deletion policies
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id SERIAL PRIMARY KEY,
    policy_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    data_type VARCHAR(100) NOT NULL,  -- audit_logs, user_data, backups, evidence
    retention_period_days INTEGER NOT NULL,
    deletion_method VARCHAR(50) DEFAULT 'soft_delete',  -- soft_delete, hard_delete, archive
    legal_hold BOOLEAN DEFAULT false,
    legal_hold_reason TEXT,
    compliance_basis VARCHAR(100),  -- SOC2, GDPR, HIPAA, PCI-DSS
    last_purge_at TIMESTAMP,
    next_purge_at TIMESTAMP,
    auto_purge_enabled BOOLEAN DEFAULT true,
    notification_before_days INTEGER DEFAULT 30,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_retention_data_type ON data_retention_policies(data_type);
CREATE INDEX idx_retention_next_purge ON data_retention_policies(next_purge_at);

COMMENT ON TABLE data_retention_policies IS 'Data retention and deletion policies for compliance';

-- ==================== COMPLIANCE METRICS ====================

-- Time-series metrics for compliance monitoring
CREATE TABLE IF NOT EXISTS compliance_metrics (
    id SERIAL PRIMARY KEY,
    metric_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_category VARCHAR(50),  -- security, availability, integrity, confidentiality, privacy
    metric_value NUMERIC,
    metric_unit VARCHAR(50),
    threshold_warning NUMERIC,
    threshold_critical NUMERIC,
    status VARCHAR(50),  -- ok, warning, critical
    dimensions JSONB,  -- Additional dimensions (e.g., {"service": "backend", "region": "us-east"})
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_compliance_metrics_name ON compliance_metrics(metric_name);
CREATE INDEX idx_compliance_metrics_category ON compliance_metrics(metric_category);
CREATE INDEX idx_compliance_metrics_collected ON compliance_metrics(collected_at);
CREATE INDEX idx_compliance_metrics_status ON compliance_metrics(status);

COMMENT ON TABLE compliance_metrics IS 'Time-series compliance metrics for monitoring';

-- ==================== SEED DATA: SOC2 CONTROLS ====================

-- Security Controls (CC6.x - Common Criteria)
INSERT INTO compliance_controls (control_id, category, title, description, automated, check_frequency, evidence_required) VALUES
('CC6.1', 'Security', 'Logical and Physical Access Controls', 'The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet the entity objectives.', true, 'daily', ARRAY['access_logs', 'authentication_logs', 'rbac_configuration']),
('CC6.2', 'Security', 'Prior to Issuing System Credentials', 'Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users whose access is administered by the entity.', true, 'daily', ARRAY['user_registration_logs', 'approval_workflows']),
('CC6.3', 'Security', 'User Access Removal', 'The entity removes access to the system when access is no longer required or when there is a change in job responsibilities.', true, 'daily', ARRAY['deprovisioning_logs', 'access_review_reports']),
('CC6.6', 'Security', 'Logical Access Restrictions', 'The entity implements logical access security measures to protect against threats from sources outside its system boundaries.', true, 'hourly', ARRAY['firewall_logs', 'intrusion_detection_logs']),
('CC6.7', 'Security', 'Encryption in Transit', 'The entity restricts the transmission, movement, and removal of information to authorized internal and external users and processes.', true, 'daily', ARRAY['ssl_configuration', 'encryption_status']),
('CC6.8', 'Security', 'Encryption at Rest', 'The entity implements controls to prevent or detect and act upon the introduction of unauthorized or malicious software.', true, 'daily', ARRAY['encryption_configuration', 'key_management_logs']),

-- Availability Controls (A1.x)
('A1.1', 'Availability', 'System Availability Monitoring', 'The entity maintains, monitors, and evaluates current processing capacity and use of system components.', true, 'hourly', ARRAY['uptime_reports', 'monitoring_dashboards']),
('A1.2', 'Availability', 'System Recovery Procedures', 'The entity authorizes, designs, develops or acquires, implements, operates, approves, maintains, and monitors environmental protections, software, data backup processes, and recovery infrastructure.', true, 'daily', ARRAY['backup_logs', 'recovery_test_results']),
('A1.3', 'Availability', 'Incident Response', 'The entity provides for the identification, reporting, and remediation of system availability issues in a timely manner.', true, 'hourly', ARRAY['incident_logs', 'response_times']),

-- Processing Integrity Controls (PI1.x)
('PI1.1', 'Processing Integrity', 'Data Validation', 'The entity implements policies and procedures over system inputs, including those for data or other inputs from vendors and business partners.', true, 'daily', ARRAY['validation_logs', 'input_schemas']),
('PI1.2', 'Processing Integrity', 'Error Detection', 'The entity implements policies and procedures to manage system processing.', true, 'hourly', ARRAY['error_logs', 'exception_reports']),
('PI1.4', 'Processing Integrity', 'Data Output Accuracy', 'The entity implements policies and procedures to make available or deliver output completely, accurately, and timely.', true, 'daily', ARRAY['output_validation_logs', 'accuracy_reports']),

-- Confidentiality Controls (C1.x)
('C1.1', 'Confidentiality', 'Confidential Data Identification', 'The entity identifies and maintains confidential information to meet the entity objectives related to confidentiality.', false, 'quarterly', ARRAY['data_classification', 'inventory_reports']),
('C1.2', 'Confidentiality', 'Confidential Data Access', 'The entity disposes of confidential information to meet the entity objectives related to confidentiality.', true, 'daily', ARRAY['access_logs', 'authorization_logs']),

-- Privacy Controls (P1.x)
('P1.1', 'Privacy', 'Data Collection Notice', 'The entity provides notice to data subjects about its privacy practices.', false, 'quarterly', ARRAY['privacy_policy', 'user_notifications']),
('P1.2', 'Privacy', 'Data Subject Rights', 'The entity provides data subjects with the ability to exercise rights related to their personal information.', false, 'monthly', ARRAY['data_access_requests', 'deletion_requests']),
('P3.1', 'Privacy', 'Data Retention and Disposal', 'The entity retains personal information consistent with its objectives related to privacy.', true, 'weekly', ARRAY['retention_policies', 'disposal_logs'])
ON CONFLICT (control_id) DO NOTHING;

-- Update timestamps for controls
UPDATE compliance_controls SET updated_at = CURRENT_TIMESTAMP;

-- ==================== VIEWS ====================

-- Compliance overview dashboard view
CREATE OR REPLACE VIEW compliance_overview AS
SELECT 
    category,
    COUNT(*) as total_controls,
    COUNT(*) FILTER (WHERE implementation_status = 'implemented') as implemented,
    COUNT(*) FILTER (WHERE implementation_status = 'verified') as verified,
    COUNT(*) FILTER (WHERE implementation_status = 'in_progress') as in_progress,
    COUNT(*) FILTER (WHERE implementation_status = 'not_implemented') as not_implemented,
    COUNT(*) FILTER (WHERE automated = true) as automated_controls,
    COUNT(*) FILTER (WHERE last_check_status = 'passed') as checks_passed,
    COUNT(*) FILTER (WHERE last_check_status = 'failed') as checks_failed,
    COUNT(*) FILTER (WHERE last_check_status = 'warning') as checks_warning
FROM compliance_controls
GROUP BY category;

-- Recent security incidents view
CREATE OR REPLACE VIEW recent_security_incidents AS
SELECT 
    incident_id,
    title,
    severity,
    incident_type,
    status,
    detected_at,
    assigned_to,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - detected_at)) / 3600 as hours_open
FROM security_incidents
WHERE status IN ('open', 'investigating', 'contained')
ORDER BY detected_at DESC
LIMIT 100;

-- Compliance readiness score view
CREATE OR REPLACE VIEW compliance_readiness_score AS
SELECT 
    ROUND(
        (COUNT(*) FILTER (WHERE implementation_status IN ('implemented', 'verified'))::NUMERIC / 
         COUNT(*)::NUMERIC) * 100, 
        2
    ) as overall_readiness_percentage,
    COUNT(*) as total_controls,
    COUNT(*) FILTER (WHERE implementation_status IN ('implemented', 'verified')) as controls_ready,
    COUNT(*) FILTER (WHERE automated = true AND last_check_status = 'passed') as automated_checks_passed,
    COUNT(*) FILTER (WHERE automated = true) as total_automated_checks
FROM compliance_controls;

COMMENT ON VIEW compliance_overview IS 'Compliance status overview by category';
COMMENT ON VIEW recent_security_incidents IS 'Recent open security incidents';
COMMENT ON VIEW compliance_readiness_score IS 'Overall SOC2 readiness score';
