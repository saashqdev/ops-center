"""
Colonel Backend Service

Main service coordinating The Colonel AI agent operations.
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from uuid import UUID
import asyncio
from fastapi import HTTPException
import anthropic
import openai

from backend.database import get_db_session
from backend.auth_dependencies import get_current_user
from backend.audit_logger import log_audit_event


class ColonelService:
    """
    Main service for The Colonel AI agent.
    
    Responsibilities:
    - Conversation management
    - Message routing to AI providers
    - Tool execution coordination
    - Audit logging
    """
    
    def __init__(self):
        self.anthropic_client = None
        self.openai_client = None
        self._initialize_ai_clients()
    
    def _initialize_ai_clients(self):
        """Initialize AI provider clients"""
        import os
        
        # Anthropic (Claude)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
        
        # OpenAI (GPT)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = openai.AsyncOpenAI(api_key=openai_key)
    
    # ==================== Conversation Management ====================
    
    async def create_conversation(
        self,
        user_id: UUID,
        organization_id: Optional[UUID] = None,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-5-sonnet-20241022",
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation.
        
        Args:
            user_id: User creating the conversation
            organization_id: Optional organization context
            model_provider: 'anthropic' or 'openai'
            model_name: Specific model to use
            system_prompt: Custom system prompt (uses default if None)
        
        Returns:
            Conversation object
        """
        async with get_db_session() as db:
            # Get default system prompt if not provided
            if system_prompt is None:
                result = await db.execute(
                    "SELECT prompt_template FROM colonel_system_prompts WHERE is_default = true LIMIT 1"
                )
                row = result.fetchone()
                system_prompt = row[0] if row else self._get_fallback_system_prompt()
            
            # Create conversation
            result = await db.execute(
                """
                INSERT INTO colonel_conversations 
                (user_id, organization_id, model_provider, model_name, system_prompt, title, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'active')
                RETURNING id, created_at
                """,
                user_id, organization_id, model_provider, model_name, system_prompt, "New Conversation"
            )
            row = result.fetchone()
            
            await db.commit()
            
            return {
                "id": row[0],
                "user_id": user_id,
                "organization_id": organization_id,
                "model_provider": model_provider,
                "model_name": model_name,
                "system_prompt": system_prompt,
                "title": "New Conversation",
                "status": "active",
                "created_at": row[1],
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tool_calls": 0
            }
    
    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Get conversation by ID (with permission check).
        
        Args:
            conversation_id: Conversation UUID
            user_id: User requesting conversation
        
        Returns:
            Conversation object
        
        Raises:
            HTTPException: If not found or unauthorized
        """
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT id, user_id, organization_id, title, model_provider, model_name,
                       system_prompt, total_input_tokens, total_output_tokens, total_tool_calls,
                       status, created_at, updated_at, last_message_at
                FROM colonel_conversations
                WHERE id = $1 AND user_id = $2
                """,
                conversation_id, user_id
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            return {
                "id": row[0],
                "user_id": row[1],
                "organization_id": row[2],
                "title": row[3],
                "model_provider": row[4],
                "model_name": row[5],
                "system_prompt": row[6],
                "total_input_tokens": row[7],
                "total_output_tokens": row[8],
                "total_tool_calls": row[9],
                "status": row[10],
                "created_at": row[11],
                "updated_at": row[12],
                "last_message_at": row[13]
            }
    
    async def list_conversations(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """
        List user's conversations.
        
        Args:
            user_id: User ID
            limit: Max conversations to return
            offset: Pagination offset
            status: Filter by status (active, archived, deleted)
        
        Returns:
            List of conversation objects
        """
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT id, title, model_provider, model_name, total_input_tokens,
                       total_output_tokens, total_tool_calls, status, created_at, last_message_at
                FROM colonel_conversations
                WHERE user_id = $1 AND status = $2
                ORDER BY last_message_at DESC NULLS LAST, created_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id, status, limit, offset
            )
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "model_provider": row[2],
                    "model_name": row[3],
                    "total_input_tokens": row[4],
                    "total_output_tokens": row[5],
                    "total_tool_calls": row[6],
                    "status": row[7],
                    "created_at": row[8],
                    "last_message_at": row[9]
                }
                for row in rows
            ]
    
    async def update_conversation_title(
        self,
        conversation_id: UUID,
        user_id: UUID,
        title: str
    ) -> None:
        """Update conversation title"""
        async with get_db_session() as db:
            await db.execute(
                """
                UPDATE colonel_conversations
                SET title = $1, updated_at = NOW()
                WHERE id = $2 AND user_id = $3
                """,
                title, conversation_id, user_id
            )
            await db.commit()
    
    async def archive_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> None:
        """Archive conversation"""
        async with get_db_session() as db:
            await db.execute(
                """
                UPDATE colonel_conversations
                SET status = 'archived', updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                """,
                conversation_id, user_id
            )
            await db.commit()
    
    async def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> None:
        """Delete conversation (soft delete)"""
        async with get_db_session() as db:
            await db.execute(
                """
                UPDATE colonel_conversations
                SET status = 'deleted', updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                """,
                conversation_id, user_id
            )
            await db.commit()
    
    # ==================== Message Management ====================
    
    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: Conversation UUID
            limit: Max messages to return
        
        Returns:
            List of message objects
        """
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT id, role, content, tool_calls, tool_results, 
                       input_tokens, output_tokens, thinking_time_ms, error_message, created_at
                FROM colonel_messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
                LIMIT $2
                """,
                conversation_id, limit
            )
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "role": row[1],
                    "content": row[2],
                    "tool_calls": row[3],
                    "tool_results": row[4],
                    "input_tokens": row[5],
                    "output_tokens": row[6],
                    "thinking_time_ms": row[7],
                    "error_message": row[8],
                    "created_at": row[9]
                }
                for row in rows
            ]
    
    async def save_message(
        self,
        conversation_id: UUID,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        thinking_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> UUID:
        """
        Save a message to the database.
        
        Args:
            conversation_id: Conversation UUID
            role: Message role (user, assistant, system, tool)
            content: Message content
            tool_calls: Tool calls made by AI
            tool_results: Results from tool executions
            input_tokens: Token count for input
            output_tokens: Token count for output
            thinking_time_ms: AI reasoning time
            error_message: Error if any
        
        Returns:
            Message UUID
        """
        import json
        
        async with get_db_session() as db:
            # Save message
            result = await db.execute(
                """
                INSERT INTO colonel_messages
                (conversation_id, role, content, tool_calls, tool_results, 
                 input_tokens, output_tokens, thinking_time_ms, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                conversation_id, role, content,
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(tool_results) if tool_results else None,
                input_tokens, output_tokens, thinking_time_ms, error_message
            )
            message_id = result.fetchone()[0]
            
            # Update conversation stats and last_message_at
            await db.execute(
                """
                UPDATE colonel_conversations
                SET total_input_tokens = total_input_tokens + COALESCE($1, 0),
                    total_output_tokens = total_output_tokens + COALESCE($2, 0),
                    total_tool_calls = total_tool_calls + COALESCE($3, 0),
                    last_message_at = NOW(),
                    updated_at = NOW()
                WHERE id = $4
                """,
                input_tokens or 0,
                output_tokens or 0,
                len(tool_calls) if tool_calls else 0,
                conversation_id
            )
            
            # Auto-generate title from first user message
            if role == "user" and content:
                await self._maybe_generate_title(db, conversation_id, content)
            
            await db.commit()
            
            return message_id
    
    async def _maybe_generate_title(self, db, conversation_id: UUID, first_message: str):
        """Generate conversation title from first message"""
        # Check if title is still default
        result = await db.execute(
            "SELECT title FROM colonel_conversations WHERE id = $1",
            conversation_id
        )
        row = result.fetchone()
        
        if row and row[0] == "New Conversation":
            # Generate simple title from first 50 chars
            title = first_message[:50]
            if len(first_message) > 50:
                title += "..."
            
            await db.execute(
                "UPDATE colonel_conversations SET title = $1 WHERE id = $2",
                title, conversation_id
            )
    
    # ==================== AI Provider Integration ====================
    
    async def process_message_stream(
        self,
        conversation_id: UUID,
        user_id: UUID,
        user_message: str,
        tool_executor
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and stream AI response.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User ID
            user_message: User's message
            tool_executor: Tool executor instance
        
        Yields:
            Stream events (text chunks, tool calls, etc.)
        """
        start_time = datetime.now()
        
        # Get conversation details
        conversation = await self.get_conversation(conversation_id, user_id)
        
        # Save user message
        await self.save_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message
        )
        
        # Get conversation history
        messages = await self.get_conversation_messages(conversation_id)
        
        # Route to appropriate AI provider
        if conversation["model_provider"] == "anthropic":
            async for event in self._process_with_claude(
                conversation, messages, user_message, tool_executor
            ):
                yield event
        elif conversation["model_provider"] == "openai":
            async for event in self._process_with_gpt(
                conversation, messages, user_message, tool_executor
            ):
                yield event
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model provider: {conversation['model_provider']}"
            )
        
        # Log to audit
        thinking_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await self._log_audit(
            conversation_id=conversation_id,
            user_id=user_id,
            organization_id=conversation["organization_id"],
            action="query",
            details={
                "query": user_message,
                "model_provider": conversation["model_provider"],
                "model_name": conversation["model_name"],
                "thinking_time_ms": thinking_time_ms
            }
        )
    
    async def _process_with_claude(
        self,
        conversation: Dict[str, Any],
        messages: List[Dict[str, Any]],
        user_message: str,
        tool_executor
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message with Claude (Anthropic)"""
        if not self.anthropic_client:
            raise HTTPException(
                status_code=503,
                detail="Anthropic API not configured"
            )
        
        # Build message history for Claude
        claude_messages = self._build_claude_messages(messages)
        
        # Get available tools
        tools = tool_executor.get_tool_definitions()
        
        # Stream response from Claude
        input_tokens = 0
        output_tokens = 0
        assistant_content = ""
        tool_calls = []
        
        try:
            with self.anthropic_client.messages.stream(
                model=conversation["model_name"],
                max_tokens=4096,
                system=conversation["system_prompt"],
                messages=claude_messages,
                tools=tools
            ) as stream:
                for event in stream:
                    if event.type == "message_start":
                        input_tokens = event.message.usage.input_tokens
                        
                    elif event.type == "content_block_start":
                        if event.content_block.type == "text":
                            yield {"type": "text_start"}
                        elif event.content_block.type == "tool_use":
                            tool_calls.append({
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": {}
                            })
                            yield {
                                "type": "tool_call_start",
                                "tool_name": event.content_block.name
                            }
                    
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            assistant_content += event.delta.text
                            yield {
                                "type": "text_delta",
                                "text": event.delta.text
                            }
                        elif event.delta.type == "input_json_delta":
                            # Tool input being streamed
                            pass
                    
                    elif event.type == "message_delta":
                        output_tokens = event.usage.output_tokens
                    
                    elif event.type == "message_stop":
                        # Message complete
                        pass
            
            # Execute tools if any
            tool_results = []
            if tool_calls:
                for tool_call in tool_calls:
                    yield {
                        "type": "tool_execution",
                        "tool_name": tool_call["name"]
                    }
                    
                    result = await tool_executor.execute_tool(
                        conversation_id=conversation["id"],
                        tool_name=tool_call["name"],
                        tool_input=tool_call["input"],
                        user_id=conversation["user_id"]
                    )
                    
                    tool_results.append(result)
                    
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_call["name"],
                        "success": result["status"] == "success"
                    }
            
            # Save assistant message
            await self.save_message(
                conversation_id=conversation["id"],
                role="assistant",
                content=assistant_content,
                tool_calls=tool_calls if tool_calls else None,
                tool_results=tool_results if tool_results else None,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            yield {"type": "done"}
            
        except Exception as e:
            # Save error message
            await self.save_message(
                conversation_id=conversation["id"],
                role="assistant",
                error_message=str(e)
            )
            
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def _process_with_gpt(
        self,
        conversation: Dict[str, Any],
        messages: List[Dict[str, Any]],
        user_message: str,
        tool_executor
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message with GPT (OpenAI)"""
        # Similar implementation to Claude but using OpenAI API
        # Placeholder for now
        yield {
            "type": "error",
            "error": "OpenAI integration not yet implemented"
        }
    
    def _build_claude_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert database messages to Claude format"""
        claude_messages = []
        
        for msg in messages:
            if msg["role"] in ["user", "assistant"]:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"] or ""
                })
        
        return claude_messages
    
    # ==================== Utility Methods ====================
    
    async def _log_audit(
        self,
        conversation_id: UUID,
        user_id: UUID,
        organization_id: Optional[UUID],
        action: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log to audit table"""
        import json
        
        async with get_db_session() as db:
            await db.execute(
                """
                INSERT INTO colonel_audit_log
                (conversation_id, user_id, organization_id, action, details, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                conversation_id, user_id, organization_id, action,
                json.dumps(details), ip_address, user_agent
            )
            await db.commit()
    
    def _get_fallback_system_prompt(self) -> str:
        """Fallback system prompt if none in database"""
        return """You are The Colonel, an AI infrastructure assistant for Ops-Center.
Your role is to help users monitor and understand their infrastructure.
You have READ-ONLY access to system APIs.
Always use tools to get real data - never make up information."""


# Global service instance
colonel_service = ColonelService()
