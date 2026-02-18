-- ================================================================
-- Migration: Add Default Apps for New Users
-- ================================================================
-- Adds is_default column to add_ons table and seeds Claude Agents
-- as a new app. Marks Unicorn Chat (Open-WebUI) and Claude Agents
-- as default apps for all newly registered users.
--
-- Date: 2026-02-17
-- ================================================================

-- Step 1: Add is_default column to add_ons table
ALTER TABLE add_ons ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE;
COMMENT ON COLUMN add_ons.is_default IS 'When TRUE, this app is automatically granted to all newly registered users regardless of their subscription tier.';

-- Step 2: Mark Unicorn Chat (Open-WebUI) as a default app
UPDATE add_ons
SET is_default = TRUE
WHERE slug = 'open-webui';

-- Step 3: Insert Claude Agents into add_ons catalog (if not exists)
INSERT INTO add_ons (
    name,
    slug,
    description,
    icon_url,
    launch_url,
    category,
    feature_key,
    base_price,
    billing_type,
    is_active,
    is_default,
    is_featured,
    sort_order,
    features
)
SELECT
    'Claude Agents',
    'claude-agents',
    'AI agent workflows powered by Claude — build, orchestrate, and execute multi-step agent pipelines',
    '/logos/claude-agents.png',
    '/admin/claude-agents',
    'AI Agents',
    'claude_agents_access',
    0.00,
    'included',
    TRUE,
    TRUE,
    TRUE,
    11,
    '{"highlights": ["Multi-step agent flows", "API key management", "Execution history", "Streaming output", "Claude SDK integration"], "use_cases": ["Automated workflows", "Code generation pipelines", "Research agents", "Data processing"]}'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM add_ons WHERE slug = 'claude-agents'
);

-- If Claude Agents already exists, just make sure is_default is TRUE
UPDATE add_ons
SET is_default = TRUE
WHERE slug = 'claude-agents';

-- Step 4: Add claude_agents_access to tier_feature_definitions (if not exists)
INSERT INTO tier_feature_definitions (feature_key, feature_name, description, value_type, default_value, category, is_system)
SELECT 'claude_agents_access', 'Claude Agents', 'Access to Claude Agent workflow builder', 'boolean', 'true', 'services', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM tier_feature_definitions WHERE feature_key = 'claude_agents_access'
);

-- Step 5: Enable claude_agents_access for ALL existing tiers
-- (so every tier gets Claude Agents by default)
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT st.id, 'claude_agents_access', 'true', TRUE
FROM subscription_tiers st
WHERE NOT EXISTS (
    SELECT 1 FROM tier_features tf
    WHERE tf.tier_id = st.id AND tf.feature_key = 'claude_agents_access'
);

-- Step 6: Ensure chat_access is enabled for ALL tiers too
-- (Unicorn Chat should be available to everyone)
INSERT INTO tier_features (tier_id, feature_key, feature_value, enabled)
SELECT st.id, 'chat_access', 'true', TRUE
FROM subscription_tiers st
WHERE NOT EXISTS (
    SELECT 1 FROM tier_features tf
    WHERE tf.tier_id = st.id AND tf.feature_key = 'chat_access'
);

-- Step 7: Auto-provision default apps for ALL existing users
-- Creates user_add_ons records so existing users also get the default apps
INSERT INTO user_add_ons (user_id, add_on_id, status, purchased_at)
SELECT DISTINCT u.keycloak_id, ao.id, 'active', NOW()
FROM users u
CROSS JOIN add_ons ao
WHERE ao.is_default = TRUE
  AND ao.is_active = TRUE
  AND u.keycloak_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM user_add_ons ua
      WHERE ua.user_id = u.keycloak_id AND ua.add_on_id = ao.id
  );

-- ================================================================
-- Verification
-- ================================================================
DO $$
DECLARE
    default_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO default_count FROM add_ons WHERE is_default = TRUE;
    RAISE NOTICE 'Default apps configured: % (expected: 2 — Unicorn Chat, Claude Agents)', default_count;
END $$;
