-- Epic 4.5: Custom Branding & White-Label
-- Organization-level branding and customization

-- Platform-wide settings table (if not exists)
CREATE TABLE IF NOT EXISTS platform_settings (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(category, key)
);

CREATE INDEX IF NOT EXISTS idx_platform_settings_category ON platform_settings(category);

-- Organization branding configuration
CREATE TABLE IF NOT EXISTS organization_branding (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL UNIQUE,
    org_name VARCHAR(200) NOT NULL,
    
    -- Logo & Visual Assets
    logo_url TEXT,                        -- URL to uploaded logo
    logo_dark_url TEXT,                   -- Dark mode logo variant
    favicon_url TEXT,                     -- Custom favicon
    background_image_url TEXT,            -- Custom background image
    
    -- Color Scheme
    primary_color VARCHAR(7) DEFAULT '#3B82F6',     -- Primary brand color
    secondary_color VARCHAR(7) DEFAULT '#1E40AF',   -- Secondary color
    accent_color VARCHAR(7) DEFAULT '#10B981',      -- Accent color
    text_color VARCHAR(7) DEFAULT '#1F2937',        -- Primary text color
    background_color VARCHAR(7) DEFAULT '#FFFFFF',  -- Background color
    
    -- Typography
    font_family VARCHAR(100),             -- Custom font (e.g., 'Inter', 'Roboto')
    heading_font VARCHAR(100),            -- Heading font
    
    -- Company Information
    company_name VARCHAR(200),
    tagline TEXT,
    description TEXT,
    support_email VARCHAR(255),
    support_phone VARCHAR(50),
    website_url TEXT,
    
    -- Social Media Links
    twitter_url TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    discord_url TEXT,
    
    -- Custom Domain
    custom_domain VARCHAR(255),           -- e.g., 'portal.acme.com'
    custom_domain_verified BOOLEAN DEFAULT FALSE,
    custom_domain_ssl_enabled BOOLEAN DEFAULT FALSE,
    
    -- Legal Documents
    terms_of_service_url TEXT,
    privacy_policy_url TEXT,
    custom_terms_text TEXT,               -- Custom inline terms
    custom_privacy_text TEXT,             -- Custom inline privacy policy
    
    -- Email Branding
    email_from_name VARCHAR(200),         -- "Acme Corp Support"
    email_from_address VARCHAR(255),      -- support@acme.com
    email_logo_url TEXT,                  -- Logo for emails
    email_footer_text TEXT,               -- Custom email footer
    
    -- Feature Flags (tier-based)
    custom_logo_enabled BOOLEAN DEFAULT FALSE,
    custom_colors_enabled BOOLEAN DEFAULT FALSE,
    custom_domain_enabled BOOLEAN DEFAULT FALSE,
    custom_email_enabled BOOLEAN DEFAULT FALSE,
    white_label_enabled BOOLEAN DEFAULT FALSE,    -- Full white-label (hide "Powered by")
    
    -- Metadata
    tier_code VARCHAR(50),                -- Which tier this org is on
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Constraints
    CONSTRAINT fk_org_tier FOREIGN KEY (tier_code) 
        REFERENCES subscription_tiers(tier_code) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_org_branding_org_id ON organization_branding(org_id);
CREATE INDEX IF NOT EXISTS idx_org_branding_tier ON organization_branding(tier_code);
CREATE INDEX IF NOT EXISTS idx_org_branding_domain ON organization_branding(custom_domain) WHERE custom_domain IS NOT NULL;

-- Branding assets table (uploaded files)
CREATE TABLE IF NOT EXISTS branding_assets (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,     -- 'logo', 'favicon', 'background', 'email_logo'
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,             -- Path on disk or S3
    file_size INTEGER,                   -- Size in bytes
    mime_type VARCHAR(100),
    width INTEGER,                       -- Image dimensions
    height INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by VARCHAR(255),
    
    CONSTRAINT fk_asset_org FOREIGN KEY (org_id) 
        REFERENCES organization_branding(org_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_branding_assets_org ON branding_assets(org_id);
CREATE INDEX IF NOT EXISTS idx_branding_assets_type ON branding_assets(asset_type);

-- Branding tier limits (what each tier gets)
CREATE TABLE IF NOT EXISTS branding_tier_limits (
    id SERIAL PRIMARY KEY,
    tier_code VARCHAR(50) NOT NULL UNIQUE,
    
    -- Allowed Features
    max_logo_size_mb NUMERIC(5,2) DEFAULT 2.0,
    max_assets INTEGER DEFAULT 5,
    custom_colors BOOLEAN DEFAULT FALSE,
    custom_fonts BOOLEAN DEFAULT FALSE,
    custom_domain BOOLEAN DEFAULT FALSE,
    custom_email_branding BOOLEAN DEFAULT FALSE,
    remove_powered_by BOOLEAN DEFAULT FALSE,   -- Hide "Powered by Ops-Center"
    custom_login_page BOOLEAN DEFAULT FALSE,
    custom_css BOOLEAN DEFAULT FALSE,
    api_white_label BOOLEAN DEFAULT FALSE,     -- Remove branding from API responses
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_branding_tier FOREIGN KEY (tier_code) 
        REFERENCES subscription_tiers(tier_code) ON DELETE CASCADE
);

-- Insert default tier limits
INSERT INTO branding_tier_limits (tier_code, max_logo_size_mb, max_assets, custom_colors, custom_fonts, custom_domain, custom_email_branding, remove_powered_by, custom_login_page, custom_css, api_white_label)
VALUES 
    ('trial', 1.0, 2, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE),
    ('starter', 2.0, 5, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE),
    ('professional', 5.0, 10, TRUE, TRUE, TRUE, TRUE, FALSE, TRUE, FALSE, FALSE),
    ('enterprise', 10.0, 20, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE),
    ('vip_founder', 10.0, 50, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE)
ON CONFLICT (tier_code) DO NOTHING;

-- Audit log for branding changes
CREATE TABLE IF NOT EXISTS branding_audit_log (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,          -- 'update_logo', 'update_colors', 'verify_domain'
    changes JSONB,                        -- What changed
    performed_by VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_branding_audit_org ON branding_audit_log(org_id);
CREATE INDEX IF NOT EXISTS idx_branding_audit_time ON branding_audit_log(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_organization_branding_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER organization_branding_updated
    BEFORE UPDATE ON organization_branding
    FOR EACH ROW
    EXECUTE FUNCTION update_organization_branding_timestamp();

-- Comments
COMMENT ON TABLE organization_branding IS 'Organization-level branding and white-label configuration (Epic 4.5)';
COMMENT ON TABLE branding_assets IS 'Uploaded branding assets (logos, favicons, etc.)';
COMMENT ON TABLE branding_tier_limits IS 'Branding feature limits per subscription tier';
COMMENT ON TABLE branding_audit_log IS 'Audit trail for branding configuration changes';
