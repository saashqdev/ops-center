#!/usr/bin/env python3
"""
Sync models from LiteLLM proxy to the Ops Center database

This script:
1. Fetches models from LiteLLM proxy (/v1/models endpoint)
2. Updates the llm_models table in the database
3. Creates provider records if they don't exist
4. Sets appropriate pricing and metadata
"""

import asyncio
import asyncpg
import httpx
import os
import sys
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

# Configuration
LITELLM_PROXY_URL = os.getenv('LITELLM_PROXY_URL', 'http://localhost:4000')
LITELLM_MASTER_KEY = os.getenv('LITELLM_MASTER_KEY', 'd85bcec2690d3f12779c0690d26d16370e434c0d7422bef5c5105f0a39b36a3a')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://unicorn:change-me@localhost:5432/unicorn_db')

# Provider mapping
PROVIDER_MAPPINGS = {
    'groq': {
        'name': 'Groq',
        'type': 'groq',
        'display_name': 'Groq (FREE)',
        'enabled': True
    },
    'huggingface': {
        'name': 'HuggingFace',
        'type': 'huggingface',
        'display_name': 'HuggingFace Inference',
        'enabled': True
    },
    'local': {
        'name': 'Local vLLM',
        'type': 'local',
        'display_name': 'Local vLLM',
        'enabled': True
    },
}

# Model metadata and pricing
MODEL_METADATA = {
    'llama-3.3-70b-groq': {
        'display_name': 'Llama 3.3 70B (Groq FREE)',
        'provider': 'groq',
        'input_cost': 0.0,
        'output_cost': 0.0,
        'context_length': 8192,
        'avg_latency_ms': 250,
        'power_level': 'high',
        'quality_score': 0.95
    },
    'llama-3.1-8b-groq': {
        'display_name': 'Llama 3.1 8B (Groq FREE)',
        'provider': 'groq',
        'input_cost': 0.0,
        'output_cost': 0.0,
        'context_length': 131072,
        'avg_latency_ms': 150,
        'power_level': 'balanced',
        'quality_score': 0.85
    },
    'qwen-32b-groq': {
        'display_name': 'Qwen 2.5 32B (Groq FREE)',
        'provider': 'groq',
        'input_cost': 0.0,
        'output_cost': 0.0,
        'context_length': 32768,
        'avg_latency_ms': 200,
        'power_level': 'high',
        'quality_score': 0.92
    },
    'mixtral-8x7b-hf': {
        'display_name': 'Mixtral 8x7B (HuggingFace)',
        'provider': 'huggingface',
        'input_cost': 0.0,
        'output_cost': 0.0,
        'context_length': 32768,
        'avg_latency_ms': 1000,
        'power_level': 'balanced',
        'quality_score': 0.88
    },
    'llama3-8b-local': {
        'display_name': 'Llama 3 8B (Local)',
        'provider': 'local',
        'input_cost': 0.0,
        'output_cost': 0.0,
        'context_length': 8192,
        'avg_latency_ms': 500,
        'power_level': 'efficient',
        'quality_score': 0.80
    },
    'qwen-32b-local': {
        'display_name': 'Qwen 2.5 32B (Local)',
        'provider': 'local',
        'input_cost': 0.0,
        'output_cost': 0.0,
        'context_length': 32768,
        'avg_latency_ms': 800,
        'power_level': 'balanced',
        'quality_score': 0.90
    },
}


async def fetch_litellm_models() -> List[Dict]:
    """Fetch models from LiteLLM proxy"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{LITELLM_PROXY_URL}/v1/models",
                headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}"},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except httpx.HTTPError as e:
            print(f"❌ Error fetching models from LiteLLM: {e}")
            sys.exit(1)


async def get_or_create_provider(conn, provider_type: str) -> UUID:
    """Get or create provider record"""
    provider_config = PROVIDER_MAPPINGS.get(provider_type, {
        'name': provider_type.title(),
        'type': provider_type,
        'display_name': provider_type.title(),
        'enabled': True
    })
    
    # Check if provider exists
    existing = await conn.fetchrow(
        "SELECT id FROM llm_providers WHERE name = $1",
        provider_config['name']
    )
    
    if existing:
        return existing['id']
    
    # Create new provider
    provider_id = await conn.fetchval(
        """
        INSERT INTO llm_providers (name, type, enabled, metadata)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        provider_config['name'],
        provider_config['type'],
        provider_config['enabled'],
        {'display_name': provider_config['display_name']}
    )
    
    print(f"  ✅ Created provider: {provider_config['name']}")
    return provider_id


async def upsert_model(conn, model_id: str, provider_id: UUID):
    """Insert or update a model in the database"""
    metadata = MODEL_METADATA.get(model_id, {})
    
    # Default values if not in metadata
    display_name = metadata.get('display_name', model_id.replace('-', ' ').title())
    input_cost = metadata.get('input_cost', 0.0)
    output_cost = metadata.get('output_cost', 0.0)
    context_length = metadata.get('context_length', 8192)
    avg_latency_ms = metadata.get('avg_latency_ms', 500)
    power_level = metadata.get('power_level', 'balanced')
    quality_score = metadata.get('quality_score', 0.85)
    
    # Check if model exists
    existing = await conn.fetchrow(
        "SELECT id FROM llm_models WHERE name = $1",
        model_id
    )
    
    if existing:
        # Update existing model
        await conn.execute(
            """
            UPDATE llm_models
            SET provider_id = $1,
                display_name = $2,
                cost_per_1m_input_tokens = $3,
                cost_per_1m_output_tokens = $4,
                context_length = $5,
                enabled = $6,
                avg_latency_ms = $7,
                power_level = $8,
                quality_score = $9,
                updated_at = $10
            WHERE name = $11
            """,
            provider_id,
            display_name,
            input_cost,
            output_cost,
            context_length,
            True,
            avg_latency_ms,
            power_level,
            quality_score,
            datetime.now(),
            model_id
        )
        print(f"  ✓ Updated: {model_id}")
    else:
        # Insert new model
        await conn.execute(
            """
            INSERT INTO llm_models (
                provider_id, name, display_name,
                cost_per_1m_input_tokens, cost_per_1m_output_tokens,
                context_length, enabled, avg_latency_ms,
                power_level, quality_score
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            provider_id,
            model_id,
            display_name,
            input_cost,
            output_cost,
            context_length,
            True,
            avg_latency_ms,
            power_level,
            quality_score
        )
        print(f"  ✅ Created: {model_id}")


async def sync_models():
    """Main sync function"""
    print("🔄 Starting LiteLLM model sync...")
    print()
    
    # Fetch models from LiteLLM
    print("📡 Fetching models from LiteLLM proxy...")
    litellm_models = await fetch_litellm_models()
    print(f"   Found {len(litellm_models)} models in LiteLLM")
    print()
    
    # Connect to database
    print("🔌 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("✅ Connected")
        print()
        
        # Create providers
        print("👥 Ensuring providers exist...")
        provider_ids = {}
        for provider_type in ['groq', 'huggingface', 'local']:
            provider_ids[provider_type] = await get_or_create_provider(conn, provider_type)
        print()
        
        # Sync models
        print(f"📊 Syncing {len(litellm_models)} models...")
        for model in litellm_models:
            model_id = model['id']
            
            # Determine provider from model metadata
            provider_type = MODEL_METADATA.get(model_id, {}).get('provider', 'local')
            provider_id = provider_ids.get(provider_type, provider_ids['local'])
            
            await upsert_model(conn, model_id, provider_id)
        
        print()
        print("✅ Sync complete!")
        print()
        
        # Show summary
        total_models = await conn.fetchval("SELECT COUNT(*) FROM llm_models")
        enabled_models = await conn.fetchval("SELECT COUNT(*) FROM llm_models WHERE enabled = true")
        total_providers = await conn.fetchval("SELECT COUNT(*) FROM llm_providers")
        
        print("📈 Database Summary:")
        print(f"   Total models: {total_models}")
        print(f"   Enabled models: {enabled_models}")
        print(f"   Total providers: {total_providers}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(sync_models())
