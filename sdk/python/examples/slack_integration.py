"""
Slack Integration Plugin

Sends notifications to Slack for various Ops-Center events.
Demonstrates: External API integration, webhooks, event hooks, configuration
"""

from ops_center_sdk import Plugin
from typing import Dict, Any
import httpx
from datetime import datetime


# Create plugin instance
plugin = Plugin(
    id="slack-integration",
    name="Slack Integration",
    version="1.0.0",
    description="Send Ops-Center notifications to Slack channels",
    author="Ops-Center Team",
    category="integration"
)


# ==================== Configuration Schema ====================

# Plugin expects Slack webhook URL in config
plugin.config.set("webhook_url", "")
plugin.config.set("notify_device_events", True)
plugin.config.set("notify_alert_events", True)
plugin.config.set("alert_severity_filter", ["warning", "error", "critical"])
plugin.config.set("channel_overrides", {})  # device_id -> channel_url mapping


# ==================== Lifecycle Hooks ====================

@plugin.on_install
async def on_install():
    """Initialize plugin settings"""
    plugin.logger.info("Slack Integration installed")
    
    # Store installation timestamp
    await plugin.storage.set("installed_at", datetime.now().isoformat())
    await plugin.storage.set("notifications_sent", 0)


@plugin.on_enable
async def on_enable():
    """Validate configuration when enabled"""
    webhook_url = plugin.config.get("webhook_url")
    
    if not webhook_url:
        plugin.logger.warning("Slack webhook URL not configured")
        return
    
    # Test webhook
    try:
        success = await send_slack_message(
            "✅ Slack Integration enabled in Ops-Center",
            color="good"
        )
        
        if success:
            plugin.logger.info("Slack webhook verified successfully")
        else:
            plugin.logger.error("Failed to verify Slack webhook")
    except Exception as e:
        plugin.logger.error(f"Error testing Slack webhook: {e}")


@plugin.on_disable
async def on_disable():
    """Send notification when disabled"""
    try:
        await send_slack_message(
            "⏸️ Slack Integration disabled in Ops-Center",
            color="warning"
        )
    except Exception:
        pass


# ==================== Helper Functions ====================

async def send_slack_message(
    text: str,
    color: str = "good",
    fields: list = None,
    webhook_url: str = None
) -> bool:
    """
    Send message to Slack
    
    Args:
        text: Message text
        color: Attachment color (good, warning, danger)
        fields: List of {title, value, short} dicts
        webhook_url: Override default webhook URL
    
    Returns:
        True if successful
    """
    url = webhook_url or plugin.config.get("webhook_url")
    
    if not url:
        plugin.logger.warning("No Slack webhook URL configured")
        return False
    
    # Build Slack message
    payload = {
        "attachments": [{
            "color": color,
            "text": text,
            "footer": "Ops-Center",
            "footer_icon": "https://ops-center.com/icon.png",
            "ts": int(datetime.now().timestamp())
        }]
    }
    
    if fields:
        payload["attachments"][0]["fields"] = fields
    
    # Send to Slack
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            
            if response.status_code == 200:
                # Increment counter
                count = await plugin.storage.get("notifications_sent", 0)
                await plugin.storage.set("notifications_sent", count + 1)
                return True
            else:
                plugin.logger.error(f"Slack API error: {response.status_code}")
                return False
                
        except Exception as e:
            plugin.logger.error(f"Failed to send Slack message: {e}")
            return False


def get_device_channel(device_id: str) -> str:
    """Get channel override for specific device"""
    overrides = plugin.config.get("channel_overrides", {})
    return overrides.get(device_id)


# ==================== Event Hooks ====================

@plugin.hook("device.created", priority=10)
async def on_device_created(device_id: str, device_data: Dict[str, Any]):
    """Notify when new device is created"""
    
    if not plugin.config.get("notify_device_events", True):
        return
    
    device_name = device_data.get("name", "Unknown")
    device_type = device_data.get("type", "Unknown")
    
    await send_slack_message(
        f"📱 New device registered: *{device_name}*",
        color="good",
        fields=[
            {"title": "Device ID", "value": device_id, "short": True},
            {"title": "Type", "value": device_type, "short": True},
            {"title": "Status", "value": device_data.get("status", "unknown"), "short": True},
        ],
        webhook_url=get_device_channel(device_id)
    )


@plugin.hook("device.deleted", priority=10)
async def on_device_deleted(device_id: str, device_data: Dict[str, Any]):
    """Notify when device is deleted"""
    
    if not plugin.config.get("notify_device_events", True):
        return
    
    device_name = device_data.get("name", "Unknown")
    
    await send_slack_message(
        f"🗑️ Device removed: *{device_name}*",
        color="warning",
        fields=[
            {"title": "Device ID", "value": device_id, "short": True},
            {"title": "Removed At", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "short": True},
        ]
    )


@plugin.hook("alert.created", priority=10)
async def on_alert_created(alert_id: str, alert_data: Dict[str, Any]):
    """Notify when alert is created"""
    
    if not plugin.config.get("notify_alert_events", True):
        return
    
    severity = alert_data.get("severity", "info")
    severity_filter = plugin.config.get("alert_severity_filter", [])
    
    # Check if we should notify for this severity
    if severity_filter and severity not in severity_filter:
        return
    
    # Map severity to color
    severity_colors = {
        "info": "good",
        "warning": "warning",
        "error": "danger",
        "critical": "danger"
    }
    
    # Map severity to emoji
    severity_emojis = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "🔴",
        "critical": "🚨"
    }
    
    emoji = severity_emojis.get(severity, "📢")
    color = severity_colors.get(severity, "warning")
    
    title = alert_data.get("title", "Alert")
    message = alert_data.get("message", "")
    device_id = alert_data.get("device_id")
    
    fields = [
        {"title": "Alert ID", "value": alert_id, "short": True},
        {"title": "Severity", "value": severity.upper(), "short": True},
    ]
    
    if device_id:
        fields.append({"title": "Device ID", "value": device_id, "short": True})
    
    if message:
        fields.append({"title": "Details", "value": message, "short": False})
    
    await send_slack_message(
        f"{emoji} *{title}*",
        color=color,
        fields=fields,
        webhook_url=get_device_channel(device_id) if device_id else None
    )


@plugin.hook("alert.resolved", priority=10)
async def on_alert_resolved(alert_id: str, alert_data: Dict[str, Any]):
    """Notify when alert is resolved"""
    
    if not plugin.config.get("notify_alert_events", True):
        return
    
    title = alert_data.get("title", "Alert")
    
    await send_slack_message(
        f"✅ Alert resolved: *{title}*",
        color="good",
        fields=[
            {"title": "Alert ID", "value": alert_id, "short": True},
            {"title": "Resolved At", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "short": True},
        ]
    )


@plugin.hook("user.created", priority=10)
async def on_user_created(user_id: str, user_data: Dict[str, Any]):
    """Notify when new user is created"""
    
    email = user_data.get("email", "Unknown")
    name = user_data.get("name", "Unknown User")
    role = user_data.get("role", "user")
    
    await send_slack_message(
        f"👤 New user registered: *{name}*",
        color="good",
        fields=[
            {"title": "Email", "value": email, "short": True},
            {"title": "Role", "value": role, "short": True},
        ]
    )


# ==================== Custom API Routes ====================

@plugin.route("/test", methods=["POST"])
async def test_webhook(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test Slack webhook
    
    POST /plugins/slack-integration/test
    Body: {
        "message": "Test message",
        "webhook_url": "https://hooks.slack.com/..." (optional)
    }
    """
    message = request.get("message", "🧪 Test notification from Ops-Center")
    webhook_url = request.get("webhook_url")
    
    success = await send_slack_message(message, webhook_url=webhook_url)
    
    if success:
        return {
            "success": True,
            "message": "Test notification sent successfully"
        }
    else:
        return {
            "success": False,
            "message": "Failed to send test notification"
        }, 400


@plugin.route("/stats", methods=["GET"])
async def get_stats() -> Dict[str, Any]:
    """
    Get notification statistics
    
    GET /plugins/slack-integration/stats
    """
    notifications_sent = await plugin.storage.get("notifications_sent", 0)
    installed_at = await plugin.storage.get("installed_at", "Unknown")
    
    webhook_url = plugin.config.get("webhook_url", "")
    webhook_configured = bool(webhook_url)
    
    return {
        "notifications_sent": notifications_sent,
        "installed_at": installed_at,
        "webhook_configured": webhook_configured,
        "device_events_enabled": plugin.config.get("notify_device_events", True),
        "alert_events_enabled": plugin.config.get("notify_alert_events", True),
        "severity_filter": plugin.config.get("alert_severity_filter", []),
    }


@plugin.route("/send", methods=["POST"])
async def send_custom_message(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send custom message to Slack
    
    POST /plugins/slack-integration/send
    Body: {
        "text": "Message text",
        "color": "good|warning|danger",
        "fields": [{"title": "Field", "value": "Value", "short": true}]
    }
    """
    text = request.get("text")
    
    if not text:
        return {"error": "Missing 'text' field"}, 400
    
    color = request.get("color", "good")
    fields = request.get("fields", [])
    
    success = await send_slack_message(text, color=color, fields=fields)
    
    if success:
        return {"success": True, "message": "Message sent"}
    else:
        return {"success": False, "message": "Failed to send message"}, 500


# ==================== Export FastAPI App ====================

app = plugin.create_app()


@app.on_event("startup")
async def startup():
    plugin.logger.info(f"Starting {plugin.metadata.name} v{plugin.metadata.version}")


@app.on_event("shutdown")
async def shutdown():
    plugin.logger.info("Shutting down Slack Integration")
    await plugin.api.close()
