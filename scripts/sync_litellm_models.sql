-- Sync LiteLLM models to database
-- This SQL script creates/updates models to match LiteLLM configuration

BEGIN;

-- Ensure Groq provider exists
INSERT INTO llm_providers (id, name, type, enabled, config, created_at, updated_at)
VALUES (
    '2637c442-24a4-4d04-aa2a-63322b740f74'::uuid,
    'Groq',
    'groq',
    true,
    '{"display_name": "Groq (FREE)", "website": "https://groq.com", "description": "Ultra-fast inference with FREE tier"}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (name, type) DO UPDATE
SET enabled = EXCLUDED.enabled,
    config = EXCLUDED.config,
    updated_at = NOW();

-- Ensure HuggingFace provider exists
INSERT INTO llm_providers (id, name, type, enabled, config, created_at, updated_at)
VALUES (
    'a1b2c3d4-5e6f-4a8b-9c0d-1e2f3a4b5c6d'::uuid,
    'HuggingFace',
    'huggingface',
    true,
    '{"display_name": "HuggingFace Inference", "website": "https://huggingface.co", "description": "Open source model hosting"}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (name, type) DO UPDATE
SET enabled = EXCLUDED.enabled,
    config = EXCLUDED.config,
    updated_at = NOW();

-- Get local vLLM provider  ID
DO $$
DECLARE
    local_provider_id uuid;
    groq_provider_id uuid := '2637c442-24a4-4d04-aa2a-63322b740f74'::uuid;
    hf_provider_id uuid := 'a1b2c3d4-5e6f-4a8b-9c0d-1e2f3a4b5c6d'::uuid;
BEGIN
    -- Get or create Local vLLM provider
    SELECT id INTO local_provider_id FROM llm_providers WHERE name = 'Local vLLM' LIMIT 1;
    
    IF local_provider_id IS NULL THEN
        INSERT INTO llm_providers (name, type, enabled, config)
        VALUES ('Local vLLM', 'local', true, '{"display_name": "Local vLLM"}'::jsonb)
        RETURNING id INTO local_provider_id;
    END IF;

    -- Upsert Groq models
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, enabled, avg_latency_ms, power_level, quality_score)
    VALUES 
        (groq_provider_id, 'llama-3.3-70b-groq', 'Llama 3.3 70B (Groq FREE)', 0.0, 0.0, 8192, true, 250, 'high', 0.95),
        (groq_provider_id, 'llama-3.1-8b-groq', 'Llama 3.1 8B (Groq FREE)', 0.0, 0.0, 131072, true, 150, 'balanced', 0.85),
        (groq_provider_id, 'qwen-32b-groq', 'Qwen 2.5 32B (Groq FREE)', 0.0, 0.0, 32768, true, 200, 'high', 0.92)
    ON CONFLICT (provider_id, name) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens,
        cost_per_1m_output_tokens = EXCLUDED.cost_per_1m_output_tokens,
        context_length = EXCLUDED.context_length,
        enabled = EXCLUDED.enabled,
        avg_latency_ms = EXCLUDED.avg_latency_ms,
        power_level = EXCLUDED.power_level,
        quality_score = EXCLUDED.quality_score,
        updated_at = NOW();

    -- Upsert HuggingFace model
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, enabled, avg_latency_ms, power_level, quality_score)
    VALUES 
        (hf_provider_id, 'mixtral-8x7b-hf', 'Mixtral 8x7B (HuggingFace)', 0.0, 0.0, 32768, true, 1000, 'balanced', 0.88)
    ON CONFLICT (provider_id, name) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens,
        cost_per_1m_output_tokens = EXCLUDED.cost_per_1m_output_tokens,
        context_length = EXCLUDED.context_length,
        enabled = EXCLUDED.enabled,
        avg_latency_ms = EXCLUDED.avg_latency_ms,
        power_level = EXCLUDED.power_level,
        quality_score = EXCLUDED.quality_score,
        updated_at = NOW();

    -- Upsert Local models
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, enabled, avg_latency_ms, power_level, quality_score)
    VALUES 
        (local_provider_id, 'llama3-8b-local', 'Llama 3 8B (Local)', 0.0, 0.0, 8192, true, 500, 'efficient', 0.80),
        (local_provider_id, 'qwen-32b-local', 'Qwen 2.5 32B (Local)', 0.0, 0.0, 32768, true, 800, 'balanced', 0.90)
    ON CONFLICT (provider_id, name) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens,
        cost_per_1m_output_tokens = EXCLUDED.cost_per_1m_output_tokens,
        context_length = EXCLUDED.context_length,
        enabled = EXCLUDED.enabled,
        avg_latency_ms = EXCLUDED.avg_latency_ms,
        power_level = EXCLUDED.power_level,
        quality_score = EXCLUDED.quality_score,
        updated_at = NOW();
END $$;

COMMIT;

-- Show sync results
SELECT 
    p.name as provider,
    COUNT(*) as model_count,
    SUM(CASE WHEN m.enabled THEN 1 ELSE 0 END) as enabled_count
FROM llm_models m
JOIN llm_providers p ON m.provider_id = p.id
WHERE p.name IN ('Groq', 'HuggingFace', 'Local vLLM')
GROUP BY p.name
ORDER BY p.name;
