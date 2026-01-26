-- API Keys and Usage Tracking Schema
-- Epic 7.0: Usage Metering & API Key Management

-- Drop existing tables if they exist (for clean slate)
DROP TABLE IF EXISTS rate_limits CASCADE;
DROP TABLE IF EXISTS usage_aggregates CASCADE;
DROP TABLE IF EXISTS usage_events_2026_02 CASCADE;
DROP TABLE IF EXISTS usage_events_2026_01 CASCADE;
DROP TABLE IF EXISTS usage_events CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;

-- API Keys Table
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,  -- First 8 chars for identification
    
    -- Ownership
    email VARCHAR(255) NOT NULL,  -- Email-based association
    subscription_id INTEGER REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    
    -- Key details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_at TIMESTAMP,
    revoked_reason TEXT,
    
    -- Usage limits (NULL = inherit from subscription)
    rate_limit_per_minute INTEGER,
    rate_limit_per_hour INTEGER,
    rate_limit_per_day INTEGER,
    monthly_quota INTEGER,
    
    -- Permissions (for future use)
    scopes JSONB DEFAULT '["all"]',
    
    -- Metadata
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,
    
    -- Tracking
    total_requests BIGINT NOT NULL DEFAULT 0,
    metadata JSONB
);

-- Usage Events Table (detailed tracking) - Parent partitioned table
CREATE TABLE usage_events (
    id BIGSERIAL,
    
    -- Request identification
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,  -- api_call, chat_completion, search_query, etc.
    endpoint VARCHAR(255),
    method VARCHAR(10),
    
    -- Metering
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    
    -- Response
    status_code INTEGER,
    response_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    
    -- Metadata
    model VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (id, created_at)  -- Include partition key in PK
) PARTITION BY RANGE (created_at);

-- Create partitions for current and next month
CREATE TABLE usage_events_2026_01 PARTITION OF usage_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE usage_events_2026_02 PARTITION OF usage_events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Usage Aggregates Table (pre-computed summaries)
CREATE TABLE usage_aggregates (
    id SERIAL PRIMARY KEY,
    
    -- Aggregation scope
    subscription_id INTEGER REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
    
    -- Time period
    period_type VARCHAR(20) NOT NULL,  -- hour, day, month
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Aggregated metrics
    total_requests BIGINT NOT NULL DEFAULT 0,
    successful_requests BIGINT NOT NULL DEFAULT 0,
    failed_requests BIGINT NOT NULL DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10, 2) DEFAULT 0,
    
    -- By event type
    event_type_breakdown JSONB,  -- {"api_call": 100, "chat": 50}
    model_breakdown JSONB,  -- {"gpt-4": 80, "claude": 20}
    
    -- Performance
    avg_response_time_ms INTEGER,
    p95_response_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(subscription_id, period_type, period_start, api_key_id)
);

-- Rate Limit Tracking (in-memory Redis preferred, but SQL fallback)
CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    
    -- Identifier
    api_key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    window_type VARCHAR(20) NOT NULL,  -- minute, hour, day
    window_start TIMESTAMP NOT NULL,
    
    -- Counter
    request_count INTEGER NOT NULL DEFAULT 0,
    
    -- Auto-cleanup
    expires_at TIMESTAMP NOT NULL,
    
    UNIQUE(api_key_id, window_type, window_start)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_email ON api_keys(email);
CREATE INDEX IF NOT EXISTS idx_api_keys_subscription ON api_keys(subscription_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active, is_revoked) WHERE is_active = true AND is_revoked = false;
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

CREATE INDEX IF NOT EXISTS idx_usage_events_api_key ON usage_events(api_key_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_subscription ON usage_events(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_email ON usage_events(email);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON usage_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_type ON usage_events(event_type);

CREATE INDEX IF NOT EXISTS idx_usage_agg_subscription ON usage_aggregates(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_agg_period ON usage_aggregates(period_type, period_start);
CREATE INDEX IF NOT EXISTS idx_usage_agg_email ON usage_aggregates(email);

CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(api_key_id, window_type, window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limits_expires ON rate_limits(expires_at);

-- Comments
COMMENT ON TABLE api_keys IS 'API keys for programmatic access with usage tracking';
COMMENT ON TABLE usage_events IS 'Detailed event-level usage tracking (partitioned by month)';
COMMENT ON TABLE usage_aggregates IS 'Pre-computed usage summaries for fast dashboard queries';
COMMENT ON TABLE rate_limits IS 'Rate limit counters per API key (prefer Redis in production)';

COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the API key for secure storage';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8 characters for user identification (e.g., sk_live_abcd1234)';
COMMENT ON COLUMN api_keys.scopes IS 'Permission scopes for API key (for future fine-grained access control)';
COMMENT ON COLUMN usage_events.tokens_used IS 'Number of tokens consumed (for LLM calls)';
COMMENT ON COLUMN usage_events.cost_usd IS 'Estimated cost in USD for this request';
