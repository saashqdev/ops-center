"""
Webhook API Endpoints
Epic 8.1: Webhook System

REST API for managing webhooks and viewing delivery logs.
"""

import logging
import secrets
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field, HttpUrl

from auth_dependencies import require_admin_user, require_authenticated_user
from webhook_manager import webhook_manager, WebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


# ==================== Request/Response Models ====================

class CreateWebhookRequest(BaseModel):
    """Request to create a webhook"""
    url: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., description="List of event types to subscribe to")
    description: Optional[str] = Field(None, description="Optional description")
    enabled: bool = Field(default=True, description="Whether webhook is active")


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook"""
    url: Optional[str] = Field(None, description="Webhook endpoint URL")
    events: Optional[List[str]] = Field(None, description="List of event types")
    secret: Optional[str] = Field(None, description="New secret key")
    description: Optional[str] = Field(None, description="Description")
    enabled: Optional[bool] = Field(None, description="Enabled status")


class WebhookResponse(BaseModel):
    """Webhook response"""
    webhook_id: str
    organization_id: str
    url: str
    events: List[str]
    description: Optional[str]
    enabled: bool
    created_at: str
    updated_at: Optional[str]
    last_triggered_at: Optional[str]
    success_count: int
    failure_count: int


class WebhookCreatedResponse(BaseModel):
    """Response when webhook is created"""
    webhook_id: str
    url: str
    events: List[str]
    secret: str  # Only returned on creation
    enabled: bool
    description: Optional[str]
    created_at: str


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log entry"""
    delivery_id: str
    event_type: str
    payload: dict
    attempt: int
    status: str
    status_code: Optional[int]
    error_message: Optional[str]
    duration_ms: Optional[int]
    created_at: str
    delivered_at: Optional[str]


class TestWebhookRequest(BaseModel):
    """Request to test a webhook"""
    event_type: str = Field(default="test.webhook", description="Event type for test")
    test_data: dict = Field(default_factory=dict, description="Test payload data")


class AvailableEventsResponse(BaseModel):
    """Available webhook events"""
    events: List[dict]


# ==================== Webhook Management ====================

@router.post("", response_model=WebhookCreatedResponse, dependencies=[Depends(require_admin_user)])
async def create_webhook(
    request: CreateWebhookRequest,
    user: dict = Depends(require_admin_user)
) -> WebhookCreatedResponse:
    """
    Create a new webhook subscription.
    
    The webhook will receive POST requests for subscribed events with an HMAC signature.
    A secret key is automatically generated and returned (only on creation).
    
    **Webhook Request Format:**
    ```json
    {
      "event": "user.created",
      "timestamp": "2026-01-26T10:00:00Z",
      "data": {
        "user_id": "123",
        "email": "user@example.com"
      }
    }
    ```
    
    **Headers:**
    - `X-Webhook-Signature`: HMAC-SHA256 signature
    - `X-Webhook-Event`: Event type
    - `Content-Type`: application/json
    """
    try:
        # Generate secret key
        secret = secrets.token_urlsafe(32)
        
        result = await webhook_manager.create_webhook(
            organization_id=UUID(user['organization_id']),
            url=request.url,
            events=request.events,
            secret=secret,
            description=request.description,
            enabled=request.enabled,
            created_by=UUID(user['user_id'])
        )
        
        # Include secret in response (only time it's shown)
        result['secret'] = secret
        
        return WebhookCreatedResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create webhook")


@router.get("", dependencies=[Depends(require_admin_user)])
async def list_webhooks(
    user: dict = Depends(require_admin_user),
    enabled_only: bool = Query(False, description="Only show enabled webhooks")
) -> List[WebhookResponse]:
    """
    List all webhooks for the organization.
    
    Returns webhook configuration and statistics (success/failure counts).
    """
    try:
        webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id']),
            enabled_only=enabled_only
        )
        
        return [WebhookResponse(**webhook) for webhook in webhooks]
    
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list webhooks")


@router.get("/{webhook_id}", response_model=WebhookResponse, dependencies=[Depends(require_admin_user)])
async def get_webhook(
    webhook_id: str,
    user: dict = Depends(require_admin_user)
) -> WebhookResponse:
    """Get details of a specific webhook"""
    try:
        webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id'])
        )
        
        webhook = next((w for w in webhooks if w['webhook_id'] == webhook_id), None)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return WebhookResponse(**webhook)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get webhook")


@router.patch("/{webhook_id}", response_model=WebhookResponse, dependencies=[Depends(require_admin_user)])
async def update_webhook(
    webhook_id: str,
    request: UpdateWebhookRequest,
    user: dict = Depends(require_admin_user)
) -> WebhookResponse:
    """
    Update webhook configuration.
    
    Can update URL, events, secret, description, or enabled status.
    """
    try:
        # Verify ownership
        webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id'])
        )
        
        webhook = next((w for w in webhooks if w['webhook_id'] == webhook_id), None)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Update webhook
        result = await webhook_manager.update_webhook(
            webhook_id=UUID(webhook_id),
            url=request.url,
            events=request.events,
            secret=request.secret,
            description=request.description,
            enabled=request.enabled
        )
        
        # Fetch updated webhook data
        updated_webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id'])
        )
        updated_webhook = next((w for w in updated_webhooks if w['webhook_id'] == webhook_id), None)
        
        return WebhookResponse(**updated_webhook)
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update webhook")


@router.delete("/{webhook_id}", dependencies=[Depends(require_admin_user)])
async def delete_webhook(
    webhook_id: str,
    user: dict = Depends(require_admin_user)
) -> dict:
    """Delete a webhook"""
    try:
        # Verify ownership
        webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id'])
        )
        
        webhook = next((w for w in webhooks if w['webhook_id'] == webhook_id), None)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Delete webhook
        success = await webhook_manager.delete_webhook(UUID(webhook_id))
        
        if success:
            return {"status": "success", "message": "Webhook deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete webhook")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete webhook")


# ==================== Webhook Logs ====================

@router.get("/{webhook_id}/deliveries", dependencies=[Depends(require_admin_user)])
async def get_webhook_deliveries(
    webhook_id: str,
    user: dict = Depends(require_admin_user),
    limit: int = Query(100, ge=1, le=500, description="Max number of logs to return"),
    status: Optional[str] = Query(None, description="Filter by status (success, failed, pending)")
) -> List[WebhookDeliveryResponse]:
    """
    Get delivery logs for a webhook.
    
    Shows delivery attempts with status, timing, and error information.
    """
    try:
        # Verify ownership
        webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id'])
        )
        
        webhook = next((w for w in webhooks if w['webhook_id'] == webhook_id), None)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Get delivery logs
        logs = await webhook_manager.get_webhook_logs(
            webhook_id=UUID(webhook_id),
            limit=limit,
            status=status
        )
        
        return [WebhookDeliveryResponse(**log) for log in logs]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook deliveries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get webhook deliveries")


# ==================== Testing ====================

@router.post("/{webhook_id}/test", dependencies=[Depends(require_admin_user)])
async def test_webhook(
    webhook_id: str,
    request: TestWebhookRequest,
    user: dict = Depends(require_admin_user)
) -> dict:
    """
    Test a webhook by sending a test event.
    
    Sends a test payload to the webhook endpoint to verify configuration.
    """
    try:
        # Verify ownership
        webhooks = await webhook_manager.list_webhooks(
            organization_id=UUID(user['organization_id'])
        )
        
        webhook = next((w for w in webhooks if w['webhook_id'] == webhook_id), None)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Trigger test event
        test_payload = {
            "test": True,
            "webhook_id": webhook_id,
            "user_id": user['user_id'],
            **request.test_data
        }
        
        await webhook_manager.trigger_event(
            event_type=request.event_type,
            organization_id=UUID(user['organization_id']),
            payload=test_payload
        )
        
        return {
            "status": "success",
            "message": f"Test event '{request.event_type}' sent to webhook"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to test webhook")


# ==================== Available Events ====================

@router.get("/events/available", response_model=AvailableEventsResponse, dependencies=[Depends(require_authenticated_user)])
async def get_available_events() -> AvailableEventsResponse:
    """
    Get list of available webhook event types.
    
    Returns all event types that can be subscribed to.
    """
    events = [
        # User events
        {"event": WebhookEvent.USER_CREATED, "category": "user", "description": "User account created"},
        {"event": WebhookEvent.USER_UPDATED, "category": "user", "description": "User account updated"},
        {"event": WebhookEvent.USER_DELETED, "category": "user", "description": "User account deleted"},
        
        # Organization events
        {"event": WebhookEvent.ORG_CREATED, "category": "organization", "description": "Organization created"},
        {"event": WebhookEvent.ORG_UPDATED, "category": "organization", "description": "Organization updated"},
        {"event": WebhookEvent.ORG_DELETED, "category": "organization", "description": "Organization deleted"},
        
        # Subscription events
        {"event": WebhookEvent.SUBSCRIPTION_CREATED, "category": "subscription", "description": "Subscription created"},
        {"event": WebhookEvent.SUBSCRIPTION_UPDATED, "category": "subscription", "description": "Subscription updated"},
        {"event": WebhookEvent.SUBSCRIPTION_CANCELLED, "category": "subscription", "description": "Subscription cancelled"},
        {"event": WebhookEvent.SUBSCRIPTION_RENEWED, "category": "subscription", "description": "Subscription renewed"},
        
        # Billing events
        {"event": WebhookEvent.PAYMENT_SUCCEEDED, "category": "billing", "description": "Payment succeeded"},
        {"event": WebhookEvent.PAYMENT_FAILED, "category": "billing", "description": "Payment failed"},
        {"event": WebhookEvent.INVOICE_CREATED, "category": "billing", "description": "Invoice created"},
        
        # Usage events
        {"event": WebhookEvent.USAGE_THRESHOLD_REACHED, "category": "usage", "description": "Usage threshold reached"},
        {"event": WebhookEvent.QUOTA_EXCEEDED, "category": "usage", "description": "Quota exceeded"},
        {"event": WebhookEvent.CREDIT_LOW, "category": "usage", "description": "Credit balance low"},
        
        # Service events
        {"event": WebhookEvent.SERVICE_STARTED, "category": "service", "description": "Service started"},
        {"event": WebhookEvent.SERVICE_STOPPED, "category": "service", "description": "Service stopped"},
        {"event": WebhookEvent.SERVICE_FAILED, "category": "service", "description": "Service failed"},
        
        # Edge device events
        {"event": WebhookEvent.DEVICE_REGISTERED, "category": "device", "description": "Edge device registered"},
        {"event": WebhookEvent.DEVICE_ONLINE, "category": "device", "description": "Edge device came online"},
        {"event": WebhookEvent.DEVICE_OFFLINE, "category": "device", "description": "Edge device went offline"},
        {"event": WebhookEvent.DEVICE_UPDATED, "category": "device", "description": "Edge device updated"},
        
        # Alert events
        {"event": WebhookEvent.ALERT_TRIGGERED, "category": "alert", "description": "Alert triggered"},
        {"event": WebhookEvent.ALERT_RESOLVED, "category": "alert", "description": "Alert resolved"},
        
        # OTA events
        {"event": WebhookEvent.OTA_DEPLOYMENT_STARTED, "category": "ota", "description": "OTA deployment started"},
        {"event": WebhookEvent.OTA_DEPLOYMENT_COMPLETED, "category": "ota", "description": "OTA deployment completed"},
        {"event": WebhookEvent.OTA_DEPLOYMENT_FAILED, "category": "ota", "description": "OTA deployment failed"},
    ]
    
    return AvailableEventsResponse(events=events)


# Export router
__all__ = ['router']
