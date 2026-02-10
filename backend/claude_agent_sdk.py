"""
Claude Agent SDK Integration
Handles agent flow creation, execution, and management

This module provides:
- Agent flow execution using Claude API
- Multi-agent orchestration
- Tool and MCP server integration
- Streaming support for real-time responses
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, AsyncIterator
from datetime import datetime
import asyncio

try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic SDK not installed. Run: pip install anthropic")

logger = logging.getLogger(__name__)


class ClaudeAgentManager:
    """Manages Claude Agent SDK workflows and executions"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude Agent Manager
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic SDK is not installed")
        
        self.api_key = api_key
        self.model = model
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
    
    async def execute_flow(
        self,
        flow_config: Dict[str, Any],
        user_input: str,
        context: Optional[Dict] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Execute an agent flow
        
        Args:
            flow_config: Flow configuration with agents, tools, etc.
            user_input: User's input/prompt
            context: Additional context for execution
            stream: Whether to stream responses
            
        Returns:
            Execution result with output, tokens used, etc.
        """
        start_time = time.time()
        
        try:
            # Extract flow configuration
            system_prompt = flow_config.get('system_prompt', 'You are a helpful AI assistant.')
            max_tokens = flow_config.get('max_tokens', 4096)
            temperature = flow_config.get('temperature', 1.0)
            tools = flow_config.get('tools', [])
            
            # Build messages
            messages = [{"role": "user", "content": user_input}]
            
            # Add context if provided
            if context and context.get('conversation_history'):
                messages = context['conversation_history'] + messages
            
            # Execute with Claude API
            if stream:
                return await self._execute_streaming(
                    messages, system_prompt, max_tokens, temperature, tools
                )
            else:
                response = await self.async_client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools if tools else None
                )
                
                # Extract response
                output_text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        output_text += block.text
                
                execution_time = int((time.time() - start_time) * 1000)
                
                return {
                    "status": "completed",
                    "output": output_text,
                    "tokens_used": {
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens
                    },
                    "execution_time_ms": execution_time,
                    "model": self.model,
                    "completed_at": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error executing flow: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_time_ms": execution_time,
                "completed_at": datetime.utcnow().isoformat()
            }
    
    async def _execute_streaming(
        self,
        messages: List[Dict],
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        tools: List[Dict]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute flow with streaming responses"""
        try:
            async with self.async_client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None
            ) as stream:
                async for text in stream.text_stream:
                    yield {
                        "type": "content",
                        "text": text
                    }
                
                # Get final message for token counts
                final_message = await stream.get_final_message()
                yield {
                    "type": "complete",
                    "tokens_used": {
                        "input": final_message.usage.input_tokens,
                        "output": final_message.usage.output_tokens
                    }
                }
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def validate_flow_config(self, flow_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate flow configuration
        
        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        if not isinstance(flow_config, dict):
            return False, "Flow config must be a dictionary"
        
        # Validate tools if present
        if 'tools' in flow_config:
            if not isinstance(flow_config['tools'], list):
                return False, "Tools must be a list"
            
            for tool in flow_config['tools']:
                if not isinstance(tool, dict):
                    return False, "Each tool must be a dictionary"
                if 'name' not in tool:
                    return False, "Each tool must have a 'name' field"
        
        # Validate parameters
        if 'max_tokens' in flow_config:
            if not isinstance(flow_config['max_tokens'], int) or flow_config['max_tokens'] < 1:
                return False, "max_tokens must be a positive integer"
        
        if 'temperature' in flow_config:
            temp = flow_config['temperature']
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                return False, "temperature must be between 0 and 2"
        
        return True, None
    
    async def create_agent_chain(
        self,
        agents: List[Dict[str, Any]],
        initial_input: str
    ) -> Dict[str, Any]:
        """
        Create a multi-agent chain where output of one feeds into next
        
        Args:
            agents: List of agent configurations
            initial_input: Initial user input
            
        Returns:
            Final output and execution details
        """
        current_input = initial_input
        results = []
        
        for i, agent_config in enumerate(agents):
            logger.info(f"Executing agent {i+1}/{len(agents)}: {agent_config.get('name', 'unnamed')}")
            
            result = await self.execute_flow(
                flow_config=agent_config,
                user_input=current_input
            )
            
            results.append({
                "agent_name": agent_config.get('name', f'agent_{i}'),
                "result": result
            })
            
            if result['status'] == 'failed':
                logger.error(f"Agent chain failed at step {i+1}")
                break
            
            # Use output as input for next agent
            current_input = result.get('output', '')
        
        return {
            "chain_results": results,
            "final_output": results[-1]['result'].get('output') if results else None,
            "total_agents": len(agents),
            "completed_agents": len(results)
        }


# Helper functions for API key encryption
def encrypt_api_key(api_key: str, encryption_key: str) -> str:
    """Encrypt API key for storage"""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(encryption_key.encode())
        return f.encrypt(api_key.encode()).decode()
    except ImportError:
        logger.warning("cryptography package not installed, storing key as base64")
        import base64
        return base64.b64encode(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str, encryption_key: str) -> str:
    """Decrypt API key from storage"""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(encryption_key.encode())
        return f.decrypt(encrypted_key.encode()).decode()
    except ImportError:
        import base64
        return base64.b64decode(encrypted_key.encode()).decode()
