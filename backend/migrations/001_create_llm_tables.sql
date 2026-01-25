-- Epic 3.1: LiteLLM Multi-Provider Routing Database Schema
-- Author: AI Assistant
-- Date: January 25, 2026
-- Description: Creates tables for multi-provider LLM routing with BYOK support

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- Table 1: llm_providers - Available LLM Providers
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT,
    api_base_url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}',
    health_status VARCHAR(20) DEFAULT 'unknown',
    last_health_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, type)
);

CREATE INDEX IF NOT EXISTS idx_llm_providers_enabled ON llm_providers(enabled);
CREATE INDEX IF NOT EXISTS idx_llm_providers_priority ON llm_providers(priority DESC);
CREATE INDEX IF NOT EXISTS idx_llm_providers_health ON llm_providers(health_status);

COMMENT ON TABLE llm_providers IS 'LLM provider configurations (admin-managed)';
COMMENT ON COLUMN llm_providers.type IS 'Provider type: openrouter, openai, anthropic, groq, together, local';
COMMENT ON COLUMN llm_providers.priority IS 'Routing priority (higher = preferred)';
COMMENT ON COLUMN llm_providers.health_status IS 'Health status: healthy, unhealthy, unknown';

-- ============================================================================
-- Table 2: llm_models - Available Models with Metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES llm_providers(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    display_name VARCHAR(200),
    cost_per_1m_input_tokens DECIMAL(10, 4),
    cost_per_1m_output_tokens DECIMAL(10, 4),
    context_length INTEGER,
    enabled BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    avg_latency_ms INTEGER,
    quality_score DECIMAL(3, 2),
    power_level VARCHAR(20) DEFAULT 'balanced',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider_id, name)
);

CREATE INDEX IF NOT EXISTS idx_llm_models_enabled ON llm_models(enabled);
CREATE INDEX IF NOT EXISTS idx_llm_models_provider ON llm_models(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_models_cost ON llm_models(cost_per_1m_input_tokens);
CREATE INDEX IF NOT EXISTS idx_llm_models_quality ON llm_models(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_llm_models_power_level ON llm_models(power_level);

COMMENT ON TABLE llm_models IS 'Available LLM models with cost and performance metadata';
COMMENT ON COLUMN llm_models.power_level IS 'Suitable power level: eco, balanced, precision';
COMMENT ON COLUMN llm_models.quality_score IS 'Model quality rating (0.00-1.00)';

-- ============================================================================
-- Table 3: user_provider_keys - User BYOK Keys
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_user_provider_keys_user ON user_provider_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_provider_keys_enabled ON user_provider_keys(user_id, enabled);

COMMENT ON TABLE user_provider_keys IS 'User-provided API keys (BYOK)';
COMMENT ON COLUMN user_provider_keys.api_key_encrypted IS 'Fernet-encrypted API key';

-- ============================================================================
-- Table 4: user_llm_settings - User Preferences
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_llm_settings (
    user_id VARCHAR(100) PRIMARY KEY,
    power_level VARCHAR(20) DEFAULT 'balanced',
    credit_balance DECIMAL(10, 2) DEFAULT 0,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_llm_settings_power ON user_llm_settings(power_level);

COMMENT ON TABLE user_llm_settings IS 'Per-user LLM preferences and settings';
COMMENT ON COLUMN user_llm_settings.power_level IS 'User power level: eco, balanced, precision';
COMMENT ON COLUMN user_llm_settings.credit_balance IS 'Remaining LLM credits';

-- ============================================================================
-- Table 5: llm_routing_rules - Routing Configuration
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_routing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy VARCHAR(50) NOT NULL DEFAULT 'balanced',
    fallback_providers UUID[] DEFAULT '{}',
    model_aliases JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE llm_routing_rules IS 'Global routing rules and strategies';
COMMENT ON COLUMN llm_routing_rules.strategy IS 'Routing strategy: cost, latency, balanced, custom';
COMMENT ON COLUMN llm_routing_rules.config IS 'Strategy-specific config (cost_weight, latency_weight, etc.)';

-- Insert default routing rule
INSERT INTO llm_routing_rules (strategy, config) VALUES
('balanced', '{
  "cost_weight": 0.4,
  "latency_weight": 0.4,
  "quality_weight": 0.2,
  "max_retries": 3,
  "retry_delay_ms": 500,
  "timeout_ms": 30000
}')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Table 6: llm_usage_logs - Usage Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    provider_id UUID REFERENCES llm_providers(id),
    model_name VARCHAR(200),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10, 6),
    latency_ms INTEGER,
    power_level VARCHAR(20),
    status VARCHAR(20),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_user ON llm_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider ON llm_usage_logs(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_status ON llm_usage_logs(status);

COMMENT ON TABLE llm_usage_logs IS 'LLM request usage tracking for billing and analytics';
COMMENT ON COLUMN llm_usage_logs.status IS 'Request status: success, error, timeout';

-- ============================================================================
-- Success message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Epic 3.1 LiteLLM tables created successfully!';
    RAISE NOTICE 'Tables: llm_providers, llm_models, user_provider_keys, user_llm_settings, llm_routing_rules, llm_usage_logs';
END $$;
