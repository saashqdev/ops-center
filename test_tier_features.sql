-- Test Data: Feature Flags for Subscription Tiers
-- This script populates tier_features for Epic 4.4 testing

-- Clear existing features (for clean testing)
TRUNCATE tier_features;

-- ============================================
-- TRIAL TIER - Limited features for testing
-- ============================================
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'chat_access', 'true', true FROM subscription_tiers WHERE tier_code = 'trial';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'search_enabled', 'false', false FROM subscription_tiers WHERE tier_code = 'trial';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'llama_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'trial';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'api_access', 'false', false FROM subscription_tiers WHERE tier_code = 'trial';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'max_file_upload_mb', '5', true FROM subscription_tiers WHERE tier_code = 'trial';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'rate_limit_per_minute', '10', true FROM subscription_tiers WHERE tier_code = 'trial';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'support_level', 'community', true FROM subscription_tiers WHERE tier_code = 'trial';

-- ============================================
-- STARTER TIER - Basic production features
-- ============================================
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'chat_access', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'search_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'tts_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'litellm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gpt4_enabled', 'false', false FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'claude_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'llama_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'api_access', 'true', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'webhooks_enabled', 'false', false FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'max_file_upload_mb', '25', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'rate_limit_per_minute', '60', true FROM subscription_tiers WHERE tier_code = 'starter';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'support_level', 'standard', true FROM subscription_tiers WHERE tier_code = 'starter';

-- ============================================
-- PROFESSIONAL TIER - Advanced features
-- ============================================
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'chat_access', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'search_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'tts_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'stt_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'brigade_access', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'litellm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'vllm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'embeddings_access', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gpt4_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'claude_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gemini_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'llama_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'mistral_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'api_access', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'webhooks_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'advanced_analytics', 'true', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'max_file_upload_mb', '100', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'max_concurrent_requests', '10', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'rate_limit_per_minute', '300', true FROM subscription_tiers WHERE tier_code = 'professional';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'support_level', 'priority', true FROM subscription_tiers WHERE tier_code = 'professional';

-- ============================================
-- ENTERPRISE TIER - All features unlocked
-- ============================================
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'chat_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'search_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'tts_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'stt_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'brigade_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'litellm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'vllm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'embeddings_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'forgejo_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'magicdeck_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gpt4_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'claude_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gemini_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'llama_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'mistral_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'api_access', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'webhooks_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'custom_branding', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'sso_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'audit_logs', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'advanced_analytics', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'team_management', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'max_file_upload_mb', '500', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'max_concurrent_requests', '50', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'rate_limit_per_minute', '1000', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'support_level', 'dedicated', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'sla_guarantee', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'dedicated_support', 'true', true FROM subscription_tiers WHERE tier_code = 'enterprise';

-- ============================================
-- VIP FOUNDER TIER - Lifetime unlimited
-- ============================================
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'chat_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'search_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'tts_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'stt_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'brigade_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'litellm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'vllm_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'embeddings_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'forgejo_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'magicdeck_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gpt4_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'claude_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'gemini_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'llama_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'mistral_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'api_access', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'webhooks_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'custom_branding', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'sso_enabled', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'audit_logs', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'advanced_analytics', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'team_management', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'support_level', 'dedicated', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'sla_guarantee', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT id, 'dedicated_support', 'true', true FROM subscription_tiers WHERE tier_code = 'vip_founder';

-- Success message
SELECT 'Feature flags populated successfully!' as status;
SELECT tier_code, COUNT(*) as feature_count 
FROM subscription_tiers st
LEFT JOIN tier_features tf ON st.id = tf.tier_id
WHERE tier_code IN ('trial', 'starter', 'professional', 'enterprise', 'vip_founder')
GROUP BY tier_code
ORDER BY tier_code;
