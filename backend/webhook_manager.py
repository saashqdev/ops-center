"""
Webhook Manager
Epic 8.1: Webhook System

Manages webhook subscriptions and delivers event notifications to external endpoints.

Features:
- Event-driven webhook delivery
- Retry logic with exponential backoff
- HMAC signature security
- Webhook logs and monitoring
- Support for multiple event types
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import httpx

from database import get_db_connection

logger = logging.getLogger(__name__)


class WebhookEvent:
    """Webhook event types"""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Organization events
    ORG_CREATED = "organization.created"
    ORG_UPDATED = "organization.updated"
    ORG_DELETED = "organization.deleted"
    
    # Subscription events
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    
    # Billing events
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    INVOICE_CREATED = "invoice.created"
    
    # Usage events
    USAGE_THRESHOLD_REACHED = "usage.threshold_reached"
    QUOTA_EXCEEDED = "quota.exceeded"
    CREDIT_LOW = "credit.low"
    
    # Service events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_FAILED = "service.failed"
    
    # Edge device events
    DEVICE_REGISTERED = "device.registered"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_UPDATED = "device.updated"
    
    # Alert events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    
    # OTA events
    OTA_DEPLOYMENT_STARTED = "ota.deployment_started"
    OTA_DEPLOYMENT_COMPLETED = "ota.deployment_completed"
    OTA_DEPLOYMENT_FAILED = "ota.deployment_failed"


class WebhookManager:
    """Manages webhook subscriptions and delivery"""
    
    def __init__(self):
        self.max_retries = 5
        self.retry_delays = [60, 300, 900, 3600, 7200]  # 1m, 5m, 15m, 1h, 2h
        self.timeout_seconds = 30
    
    async def create_webhook(
        self,
        organization_id: UUID,
        url: str,
        events: List[str],
        secret: str,
        description: Optional[str] = None,
        enabled: bool = True,
        created_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Create a new webhook subscription.
        
        Args:
            organization_id: Organization ID
            url: Webhook endpoint URL
            events: List of event types to subscribe to
            secret: Secret key for HMAC signature
            description: Optional description
            enabled: Whether webhook is active
            created_by: User who created the webhook
            
        Returns:
            Webhook data
        """
        async with await get_db_connection() as conn:
            webhook_id = await conn.fetchval(
                """
                INSERT INTO webhooks (
                    organization_id, url, events, secret, description, 
                    enabled, created_by
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                organization_id,
                url,
                events,
                secret,
                description,
                enabled,
                created_by
            )
            
            logger.info(
                f"Created webhook {webhook_id} for org {organization_id}: "
                f"{url} (events: {', '.join(events)})"
            )
            
            return {
                "webhook_id": str(webhook_id),
                "url": url,
                "events": events,
                "enabled": enabled,
                "description": description,
                "created_at": datetime.utcnow().isoformat()
            }
    
    async def update_webhook(
        self,
        webhook_id: UUID,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update webhook configuration"""
        async with await get_db_connection() as conn:
            updates = []
            params = []
            param_idx = 1
            
            if url is not None:
                updates.append(f"url = ${param_idx}")
                params.append(url)
                param_idx += 1
            
            if events is not None:
                updates.append(f"events = ${param_idx}")
                params.append(events)
                param_idx += 1
            
            if secret is not None:
                updates.append(f"secret = ${param_idx}")
                params.append(secret)
                param_idx += 1
            
            if description is not None:
                updates.append(f"description = ${param_idx}")
                params.append(description)
                param_idx += 1
            
            if enabled is not None:
                updates.append(f"enabled = ${param_idx}")
                params.append(enabled)
                param_idx += 1
            
            if not updates:
                raise ValueError("No updates provided")
            
            updates.append(f"updated_at = NOW()")
            
            query = f"""
                UPDATE webhooks
                SET {', '.join(updates)}
                WHERE id = ${param_idx}
                RETURNING id, url, events, enabled, description, updated_at
            """
            params.append(webhook_id)
            
            result = await conn.fetchrow(query, *params)
            
            if not result:
                raise ValueError(f"Webhook {webhook_id} not found")
            
            logger.info(f"Updated webhook {webhook_id}")
            
            return {
                "webhook_id": str(result['id']),
                "url": result['url'],
                "events": result['events'],
                "enabled": result['enabled'],
                "description": result['description'],
                "updated_at": result['updated_at'].isoformat()
            }
            
    
    async def delete_webhook(self, webhook_id: UUID) -> bool:
        """Delete a webhook"""
        async with await get_db_connection() as conn:
            result = await conn.execute(
                "DELETE FROM webhooks WHERE id = $1",
                webhook_id
            )
            
            deleted = result == "DELETE 1"
            
            if deleted:
                logger.info(f"Deleted webhook {webhook_id}")
            
            return deleted
            
    
    async def list_webhooks(
        self,
        organization_id: Optional[UUID] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List webhooks"""
        async with await get_db_connection() as conn:
            filters = []
            params = []
            param_idx = 1
            
            if organization_id:
                filters.append(f"organization_id = ${param_idx}")
                params.append(organization_id)
                param_idx += 1
            
            if enabled_only:
                filters.append(f"enabled = ${param_idx}")
                params.append(True)
                param_idx += 1
            
            where_clause = " AND ".join(filters) if filters else "TRUE"
            
            rows = await conn.fetch(
                f"""
                SELECT 
                    id, organization_id, url, events, description, enabled,
                    created_at, updated_at, last_triggered_at, 
                    success_count, failure_count
                FROM webhooks
                WHERE {where_clause}
                ORDER BY created_at DESC
                """,
                *params
            )
            
            return [
                {
                    "webhook_id": str(row['id']),
                    "organization_id": str(row['organization_id']),
                    "url": row['url'],
                    "events": row['events'],
                    "description": row['description'],
                    "enabled": row['enabled'],
                    "created_at": row['created_at'].isoformat(),
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "last_triggered_at": row['last_triggered_at'].isoformat() if row['last_triggered_at'] else None,
                    "success_count": row['success_count'],
                    "failure_count": row['failure_count']
                }
                for row in rows
            ]
    
    async def trigger_event(
        self,
        event_type: str,
        organization_id: UUID,
        payload: Dict[str, Any]
    ):
        """
        Trigger a webhook event.
        
        This method finds all webhooks subscribed to the event type and
        delivers the payload to each endpoint.
        
        Args:
            event_type: Event type (e.g., "user.created")
            organization_id: Organization ID
            payload: Event data to send
        """
        async with await get_db_connection() as conn:
            # Find all webhooks subscribed to this event
            webhooks = await conn.fetch(
                """
                SELECT id, url, secret, events
                FROM webhooks
                WHERE organization_id = $1
                  AND enabled = TRUE
                  AND $2 = ANY(events)
                """,
                organization_id,
                event_type
            )
            
            if not webhooks:
                logger.debug(
                    f"No webhooks subscribed to {event_type} "
                    f"for org {organization_id}"
                )
                return
            
            logger.info(
                f"Triggering {event_type} event for {len(webhooks)} webhook(s)"
            )
            
            # Deliver to each webhook asynchronously
            tasks = []
            for webhook in webhooks:
                task = self._deliver_webhook(
                    webhook_id=webhook['id'],
                    url=webhook['url'],
                    secret=webhook['secret'],
                    event_type=event_type,
                    payload=payload
                )
                tasks.append(task)
            
            # Fire and forget - don't wait for delivery
            asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
            
    
    async def _deliver_webhook(
        self,
        webhook_id: UUID,
        url: str,
        secret: str,
        event_type: str,
        payload: Dict[str, Any],
        attempt: int = 1
    ):
        """
        Deliver webhook to endpoint with retry logic.
        
        Args:
            webhook_id: Webhook ID
            url: Endpoint URL
            secret: HMAC secret
            event_type: Event type
            payload: Event data
            attempt: Current attempt number (for retries)
        """
        # Prepare webhook payload
        webhook_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }
        
        # Generate HMAC signature
        payload_json = json.dumps(webhook_payload, sort_keys=True)
        signature = self._generate_signature(payload_json, secret)
        
        # Log the delivery attempt
        async with await get_db_connection() as conn:
            delivery_id = await conn.fetchval(
                """
                INSERT INTO webhook_deliveries (
                    webhook_id, event_type, payload, attempt, status
                )
                VALUES ($1, $2, $3, $4, 'pending')
                RETURNING id
                """,
                webhook_id,
                event_type,
                webhook_payload,
                attempt
            )
        
        # Attempt delivery
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    url,
                    json=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": event_type,
                        "User-Agent": "Ops-Center-Webhook/1.0"
                    }
                )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Consider 2xx status codes as success
                if 200 <= response.status_code < 300:
                    await self._log_delivery_success(
                        delivery_id,
                        webhook_id,
                        response.status_code,
                        duration_ms
                    )
                    logger.info(
                        f"Webhook {webhook_id} delivered successfully: "
                        f"{url} ({response.status_code})"
                    )
                else:
                    # Non-2xx response - schedule retry
                    await self._log_delivery_failure(
                        delivery_id,
                        webhook_id,
                        response.status_code,
                        response.text,
                        duration_ms
                    )
                    
                    # Retry if not exceeded max retries
                    if attempt < self.max_retries:
                        await self._schedule_retry(
                            webhook_id, url, secret, event_type, 
                            payload, attempt
                        )
                    else:
                        logger.error(
                            f"Webhook {webhook_id} failed after {attempt} attempts"
                        )
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            await self._log_delivery_failure(
                delivery_id,
                webhook_id,
                0,
                str(e),
                duration_ms
            )
            
            logger.error(
                f"Webhook {webhook_id} delivery failed (attempt {attempt}): {e}"
            )
            
            # Retry if not exceeded max retries
            if attempt < self.max_retries:
                await self._schedule_retry(
                    webhook_id, url, secret, event_type, 
                    payload, attempt
                )
    
    async def _schedule_retry(
        self,
        webhook_id: UUID,
        url: str,
        secret: str,
        event_type: str,
        payload: Dict[str, Any],
        current_attempt: int
    ):
        """Schedule a retry with exponential backoff"""
        next_attempt = current_attempt + 1
        delay = self.retry_delays[current_attempt - 1]
        
        logger.info(
            f"Scheduling retry for webhook {webhook_id} "
            f"(attempt {next_attempt}/{self.max_retries}) in {delay}s"
        )
        
        # Schedule retry using asyncio
        async def retry_task():
            await asyncio.sleep(delay)
            await self._deliver_webhook(
                webhook_id, url, secret, event_type, 
                payload, next_attempt
            )
        
        asyncio.create_task(retry_task())
    
    async def _log_delivery_success(
        self,
        delivery_id: UUID,
        webhook_id: UUID,
        status_code: int,
        duration_ms: int
    ):
        """Log successful webhook delivery"""
        async with await get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE webhook_deliveries
                SET status = 'success',
                    status_code = $1,
                    duration_ms = $2,
                    delivered_at = NOW()
                WHERE id = $3
                """,
                status_code,
                duration_ms,
                delivery_id
            )
            
            # Update webhook stats
            await conn.execute(
                """
                UPDATE webhooks
                SET success_count = success_count + 1,
                    last_triggered_at = NOW()
                WHERE id = $1
                """,
                webhook_id
            )
    
    async def _log_delivery_failure(
        self,
        delivery_id: UUID,
        webhook_id: UUID,
        status_code: int,
        error_message: str,
        duration_ms: int
    ):
        """Log failed webhook delivery"""
        async with await get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE webhook_deliveries
                SET status = 'failed',
                    status_code = $1,
                    error_message = $2,
                    duration_ms = $3,
                    delivered_at = NOW()
                WHERE id = $4
                """,
                status_code,
                error_message[:1000],  # Truncate long error messages
                duration_ms,
                delivery_id
            )
            
            # Update webhook stats
            await conn.execute(
                """
                UPDATE webhooks
                SET failure_count = failure_count + 1,
                    last_triggered_at = NOW()
                WHERE id = $1
                """,
                webhook_id
            )
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    async def get_webhook_logs(
        self,
        webhook_id: UUID,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get delivery logs for a webhook"""
        async with await get_db_connection() as conn:
            filters = ["webhook_id = $1"]
            params = [webhook_id]
            param_idx = 2
            
            if status:
                filters.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1
            
            where_clause = " AND ".join(filters)
            
            rows = await conn.fetch(
                f"""
                SELECT 
                    id, event_type, payload, attempt, status,
                    status_code, error_message, duration_ms,
                    created_at, delivered_at
                FROM webhook_deliveries
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
                """,
                *params, limit
            )
            
            return [
                {
                    "delivery_id": str(row['id']),
                    "event_type": row['event_type'],
                    "payload": row['payload'],
                    "attempt": row['attempt'],
                    "status": row['status'],
                    "status_code": row['status_code'],
                    "error_message": row['error_message'],
                    "duration_ms": row['duration_ms'],
                    "created_at": row['created_at'].isoformat(),
                    "delivered_at": row['delivered_at'].isoformat() if row['delivered_at'] else None
                }
                for row in rows
            ]
            


# Global webhook manager instance
webhook_manager = WebhookManager()


# Helper function to trigger events from anywhere in the codebase
async def trigger_webhook_event(
    event_type: str,
    organization_id: UUID,
    payload: Dict[str, Any]
):
    """
    Trigger a webhook event.
    
    Usage:
        from webhook_manager import trigger_webhook_event, WebhookEvent
        
        await trigger_webhook_event(
            WebhookEvent.USER_CREATED,
            organization_id,
            {
                "user_id": str(user_id),
                "email": email,
                "role": role
            }
        )
    """
    try:
        await webhook_manager.trigger_event(event_type, organization_id, payload)
    except Exception as e:
        logger.error(f"Failed to trigger webhook event {event_type}: {e}")
