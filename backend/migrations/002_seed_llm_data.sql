-- Epic 3.1: LiteLLM Seed Data - Initial Providers and Models
-- Author: AI Assistant
-- Date: January 25, 2026
-- Description: Seeds initial provider and model data for multi-provider routing

-- ============================================================================
-- Seed Providers
-- ============================================================================

-- Insert providers (note: api_key_encrypted should be set via API in production)
INSERT INTO llm_providers (name, type, api_base_url, enabled, priority, config) VALUES
-- Tier 1: Free/Local Providers (Highest Priority for Eco)
('Local vLLM', 'local', 'http://unicorn-vllm:8000', true, 100, '{"timeout": 60000}'),
('Groq', 'groq', 'https://api.groq.com', true, 95, '{"timeout": 30000}'),

-- Tier 2: OpenRouter (Best Value)
('OpenRouter', 'openrouter', 'https://openrouter.ai/api', true, 90, '{"timeout": 30000, "site_url": "https://kubeworkz.io", "app_name": "Ops-Center"}'),

-- Tier 3: Direct Providers (Premium)
('Platform OpenAI', 'openai', 'https://api.openai.com', true, 80, '{"timeout": 30000}'),
('Platform Anthropic', 'anthropic', 'https://api.anthropic.com', true, 80, '{"timeout": 30000}'),
('Together AI', 'together', 'https://api.together.xyz', true, 70, '{"timeout": 30000}'),
('Hugging Face', 'huggingface', 'https://api-inference.huggingface.co', true, 60, '{"timeout": 45000}')
ON CONFLICT (name, type) DO UPDATE SET
    api_base_url = EXCLUDED.api_base_url,
    priority = EXCLUDED.priority,
    config = EXCLUDED.config,
    updated_at = NOW();

-- ============================================================================
-- Seed Models for Each Provider
-- ============================================================================

-- Get provider IDs for model insertion
DO $$
DECLARE
    local_id UUID;
    groq_id UUID;
    openrouter_id UUID;
    openai_id UUID;
    anthropic_id UUID;
    together_id UUID;
    hf_id UUID;
BEGIN
    -- Get provider IDs
    SELECT id INTO local_id FROM llm_providers WHERE type = 'local' LIMIT 1;
    SELECT id INTO groq_id FROM llm_providers WHERE type = 'groq' LIMIT 1;
    SELECT id INTO openrouter_id FROM llm_providers WHERE type = 'openrouter' LIMIT 1;
    SELECT id INTO openai_id FROM llm_providers WHERE type = 'openai' LIMIT 1;
    SELECT id INTO anthropic_id FROM llm_providers WHERE type = 'anthropic' LIMIT 1;
    SELECT id INTO together_id FROM llm_providers WHERE type = 'together' LIMIT 1;
    SELECT id INTO hf_id FROM llm_providers WHERE type = 'huggingface' LIMIT 1;

    -- Local vLLM Models (ECO - Free, Fast)
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, quality_score, avg_latency_ms, power_level) VALUES
    (local_id, 'qwen-32b-awq', 'Qwen 2.5 32B (Local)', 0.00, 0.00, 32768, 0.85, 500, 'eco'),
    (local_id, 'llama-3.1-8b-instruct', 'Llama 3.1 8B (Local)', 0.00, 0.00, 131072, 0.80, 300, 'eco')
    ON CONFLICT (provider_id, name) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens,
        cost_per_1m_output_tokens = EXCLUDED.cost_per_1m_output_tokens,
        updated_at = NOW();

    -- Groq Models (ECO - Free, Very Fast)
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, quality_score, avg_latency_ms, power_level) VALUES
    (groq_id, 'llama-3.1-70b-versatile', 'Llama 3.1 70B (Groq)', 0.00, 0.00, 131072, 0.88, 200, 'balanced'),
    (groq_id, 'mixtral-8x7b-32768', 'Mixtral 8x7B (Groq)', 0.00, 0.00, 32768, 0.82, 150, 'eco'),
    (groq_id, 'gemma2-9b-it', 'Gemma 2 9B (Groq)', 0.00, 0.00, 8192, 0.78, 100, 'eco')
    ON CONFLICT (provider_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = NOW();

    -- OpenRouter Models (BALANCED - Best Value)
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, quality_score, avg_latency_ms, power_level) VALUES
    (openrouter_id, 'openai/gpt-4o-mini', 'GPT-4o Mini (OpenRouter)', 0.15, 0.60, 128000, 0.85, 800, 'balanced'),
    (openrouter_id, 'anthropic/claude-3.5-sonnet', 'Claude 3.5 Sonnet (OpenRouter)', 3.00, 15.00, 200000, 0.98, 1500, 'precision'),
    (openrouter_id, 'google/gemini-pro-1.5', 'Gemini 1.5 Pro (OpenRouter)', 1.25, 5.00, 2000000, 0.92, 1200, 'precision'),
    (openrouter_id, 'meta-llama/llama-3.1-405b-instruct', 'Llama 3.1 405B (OpenRouter)', 2.70, 2.70, 131072, 0.95, 2000, 'precision'),
    (openrouter_id, 'mistralai/mixtral-8x22b-instruct', 'Mixtral 8x22B (OpenRouter)', 0.65, 0.65, 65536, 0.87, 1000, 'balanced'),
    (openrouter_id, 'qwen/qwen-2.5-72b-instruct', 'Qwen 2.5 72B (OpenRouter)', 0.35, 0.35, 131072, 0.86, 900, 'balanced')
    ON CONFLICT (provider_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens, updated_at = NOW();

    -- OpenAI Models (PRECISION - Direct API)
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, quality_score, avg_latency_ms, power_level) VALUES
    (openai_id, 'gpt-4o', 'GPT-4o', 5.00, 15.00, 128000, 0.95, 1800, 'precision'),
    (openai_id, 'gpt-4o-mini', 'GPT-4o Mini', 0.15, 0.60, 128000, 0.85, 800, 'balanced'),
    (openai_id, 'gpt-4-turbo', 'GPT-4 Turbo', 10.00, 30.00, 128000, 0.93, 2200, 'precision'),
    (openai_id, 'o1-preview', 'O1 Preview (Reasoning)', 15.00, 60.00, 128000, 0.97, 5000, 'precision')
    ON CONFLICT (provider_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens, updated_at = NOW();

    -- Anthropic Models (PRECISION - Direct API)
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, quality_score, avg_latency_ms, power_level) VALUES
    (anthropic_id, 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 3.00, 15.00, 200000, 0.98, 1800, 'precision'),
    (anthropic_id, 'claude-3-opus-20240229', 'Claude 3 Opus', 15.00, 75.00, 200000, 0.99, 3000, 'precision'),
    (anthropic_id, 'claude-3-haiku-20240307', 'Claude 3 Haiku', 0.25, 1.25, 200000, 0.83, 600, 'balanced')
    ON CONFLICT (provider_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, cost_per_1m_input_tokens = EXCLUDED.cost_per_1m_input_tokens, updated_at = NOW();

    -- Together AI Models (BALANCED)
    INSERT INTO llm_models (provider_id, name, display_name, cost_per_1m_input_tokens, cost_per_1m_output_tokens, context_length, quality_score, avg_latency_ms, power_level) VALUES
    (together_id, 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo', 'Llama 3.1 405B Turbo', 3.50, 3.50, 131072, 0.94, 1600, 'precision'),
    (together_id, 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo', 'Llama 3.1 70B Turbo', 0.88, 0.88, 131072, 0.88, 800, 'balanced'),
    (together_id, 'mistralai/Mixtral-8x22B-Instruct-v0.1', 'Mixtral 8x22B', 1.20, 1.20, 65536, 0.87, 1200, 'balanced')
    ON CONFLICT (provider_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = NOW();

    RAISE NOTICE 'Seed data inserted successfully!';
    RAISE NOTICE 'Providers: %, Models: %', 
        (SELECT COUNT(*) FROM llm_providers),
        (SELECT COUNT(*) FROM llm_models);
END $$;

-- ============================================================================
-- Power Level Summary
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== POWER LEVEL SUMMARY ===';
    RAISE NOTICE 'ECO: Free models (Groq, Local) - $0.00-0.10/1M tokens';
    RAISE NOTICE 'BALANCED: Best value models - $0.10-3.00/1M tokens';
    RAISE NOTICE 'PRECISION: Premium models - $3.00-75.00/1M tokens';
    RAISE NOTICE '';
    RAISE NOTICE 'Total ECO models: %', (SELECT COUNT(*) FROM llm_models WHERE power_level = 'eco');
    RAISE NOTICE 'Total BALANCED models: %', (SELECT COUNT(*) FROM llm_models WHERE power_level = 'balanced');
    RAISE NOTICE 'Total PRECISION models: %', (SELECT COUNT(*) FROM llm_models WHERE power_level = 'precision');
END $$;
