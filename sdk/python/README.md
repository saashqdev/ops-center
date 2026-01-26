# Ops-Center Plugin SDK (Python)

Build powerful plugins for Ops-Center using Python. This SDK provides everything you need to extend Ops-Center with custom functionality.

## Features

- 🎣 **Hook System** - React to events like device creation, metrics updates, alerts
- 🛣️ **Custom Routes** - Add REST API endpoints to your plugin
- 💾 **Storage API** - Persist plugin data with simple key-value storage
- ⏰ **Scheduler** - Run background tasks on schedules or timers
- ⚙️ **Configuration** - YAML-based configuration with schema validation
- 🔌 **API Client** - Access Ops-Center APIs (devices, users, alerts, etc.)
- 🧪 **Testing Utils** - Mock fixtures for unit testing plugins
- 🛠️ **CLI Tools** - Scaffold, build, and publish plugins

## Quick Start

### Installation

```bash
pip install ops-center-plugin-sdk
```

### Create Your First Plugin

```bash
# Initialize new plugin
ops-center-plugin init my-plugin \
  --name "My Awesome Plugin" \
  --description "Does something awesome" \
  --author "Your Name" \
  --category monitoring

cd my-plugin

# Install dependencies
pip install -r requirements.txt

# Validate plugin
ops-center-plugin validate

# Build for distribution
ops-center-plugin build
```

## Plugin Development

### Basic Plugin Structure

```python
from ops_center_sdk import Plugin
from typing import Dict, Any

# Create plugin instance
plugin = Plugin(
    id="my-plugin",
    name="My Plugin",
    version="1.0.0",
    description="My awesome plugin",
    author="Your Name",
    category="monitoring"
)


# ==================== Lifecycle Hooks ====================

@plugin.on_install
async def on_install():
    """Called when plugin is first installed"""
    plugin.logger.info("Installing plugin...")
    await plugin.storage.set("installed_at", datetime.now().isoformat())


@plugin.on_enable
async def on_enable():
    """Called when plugin is enabled"""
    plugin.logger.info("Starting plugin services...")
    
    # Schedule background task
    await plugin.scheduler.schedule(
        cron="*/5 * * * *",  # Every 5 minutes
        task_name="check_devices",
        handler=check_devices
    )


@plugin.on_disable
async def on_disable():
    """Called when plugin is disabled"""
    await plugin.scheduler.cancel_all()


# ==================== Event Hooks ====================

@plugin.hook("device.created", priority=10)
async def on_device_created(device_id: str, device_data: Dict[str, Any]):
    """React to device creation events"""
    plugin.logger.info(f"New device: {device_id}")
    
    # Store device in plugin storage
    await plugin.storage.set(f"device:{device_id}", device_data)
    
    # Call Ops-Center API
    await plugin.api.alerts.create({
        "device_id": device_id,
        "severity": "info",
        "title": "Device Registered",
        "message": f"New device {device_data['name']} added"
    })


@plugin.filter_hook("device.data.process", priority=10)
async def enrich_device_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Modify device data before storage"""
    data["plugin_processed"] = True
    data["processed_at"] = datetime.now().isoformat()
    return data


# ==================== Custom API Routes ====================

@plugin.route("/status", methods=["GET"])
async def get_status() -> Dict[str, Any]:
    """
    GET /plugins/my-plugin/status
    
    Returns plugin status
    """
    devices_count = len(await plugin.storage.list_keys("device:*"))
    
    return {
        "status": "running",
        "version": plugin.metadata.version,
        "devices_tracked": devices_count
    }


@plugin.route("/devices/{device_id}/stats", methods=["GET"])
async def get_device_stats(device_id: str) -> Dict[str, Any]:
    """
    GET /plugins/my-plugin/devices/123/stats
    
    Returns stats for specific device
    """
    device_data = await plugin.storage.get(f"device:{device_id}")
    
    if not device_data:
        return {"error": "Device not found"}, 404
    
    return {
        "device_id": device_id,
        "tracked_since": device_data.get("tracked_at"),
        "last_updated": device_data.get("updated_at")
    }


# ==================== Background Tasks ====================

async def check_devices():
    """Background task - runs on schedule"""
    plugin.logger.info("Checking devices...")
    
    devices = await plugin.api.devices.list(status="online")
    
    for device in devices:
        # Process each device
        await plugin.storage.set(
            f"device:{device['id']}:last_check",
            datetime.now().isoformat()
        )


# ==================== Export FastAPI App ====================

# This is required - creates the FastAPI app that Ops-Center runs
app = plugin.create_app()
```

## SDK Components

### Plugin Class

Main entry point for plugin development.

```python
from ops_center_sdk import Plugin

plugin = Plugin(
    id="unique-plugin-id",
    name="Display Name",
    version="1.0.0",
    description="What your plugin does",
    author="Your Name",
    category="monitoring"  # monitoring, ai, security, integration, analytics
)
```

### API Client

Access Ops-Center APIs:

```python
# Devices
devices = await plugin.api.devices.list(page=1, status="online")
device = await plugin.api.devices.get("device-123")
await plugin.api.devices.create({"name": "New Device", "type": "server"})
await plugin.api.devices.update("device-123", {"status": "maintenance"})
await plugin.api.devices.delete("device-123")

# Users
users = await plugin.api.users.list()
user = await plugin.api.users.get("user-456")

# Organizations
orgs = await plugin.api.organizations.list()
org = await plugin.api.organizations.get("org-789")

# Alerts
alerts = await plugin.api.alerts.list(severity="critical", status="active")
await plugin.api.alerts.create({
    "device_id": "device-123",
    "severity": "warning",
    "title": "High CPU Usage",
    "message": "CPU usage is above 90%"
})
await plugin.api.alerts.acknowledge("alert-123")

# Webhooks
webhooks = await plugin.api.webhooks.list()
await plugin.api.webhooks.create({
    "url": "https://example.com/webhook",
    "events": ["device.created", "alert.created"]
})
```

### Storage

Persist plugin data:

```python
# Store data
await plugin.storage.set("key", {"data": "value"})
await plugin.storage.set("counter", 42)

# Retrieve data
value = await plugin.storage.get("key")
counter = await plugin.storage.get("counter", default=0)

# Check existence
if await plugin.storage.exists("key"):
    print("Key exists")

# List keys with pattern
keys = await plugin.storage.list_keys("device:*")

# Delete
await plugin.storage.delete("key")

# Clear all
await plugin.storage.clear()
```

### Scheduler

Run background tasks:

```python
from datetime import datetime, timedelta

# Run once at specific time
run_time = datetime.now() + timedelta(hours=1)
await plugin.scheduler.run_at(run_time, my_handler, arg1="value")

# Run once after delay
await plugin.scheduler.run_in(timedelta(minutes=5), my_handler)

# Run on schedule (cron)
await plugin.scheduler.schedule(
    cron="0 */6 * * *",  # Every 6 hours
    task_name="sync_data",
    handler=sync_handler
)

# Cancel task
await plugin.scheduler.cancel(task_id)

# Cancel all tasks
await plugin.scheduler.cancel_all()

# List active tasks
tasks = plugin.scheduler.get_tasks()
```

### Configuration

Manage plugin configuration:

```python
# Get config value
threshold = plugin.config.get("threshold", default=0.8)
enabled = plugin.config.get("enabled")

# Set config value
plugin.config.set("threshold", 0.9)

# Get all config
all_config = plugin.config.all()

# Save changes
await plugin.config.save()

# Reload from disk
await plugin.config.reload()
```

### Logger

Structured logging:

```python
plugin.logger.debug("Debug message")
plugin.logger.info("Info message")
plugin.logger.warning("Warning message")
plugin.logger.error("Error message")
plugin.logger.critical("Critical message")
```

## Hooks and Events

### Available Hooks

- `device.created` - Device created
- `device.updated` - Device updated
- `device.deleted` - Device deleted
- `device.metrics_updated` - Device metrics received
- `alert.created` - Alert created
- `alert.updated` - Alert updated
- `alert.resolved` - Alert resolved
- `user.created` - User created
- `user.updated` - User updated
- `organization.created` - Organization created

### Action Hooks

React to events:

```python
@plugin.hook("device.created", priority=10)
async def handle_device_created(device_id: str, device_data: dict):
    """React to device creation"""
    plugin.logger.info(f"Device created: {device_id}")
```

Priority: Higher values run first (default: 10)

### Filter Hooks

Modify data in pipeline:

```python
@plugin.filter_hook("device.data.process", priority=10)
async def enrich_data(data: dict) -> dict:
    """Modify device data before storage"""
    data["enriched"] = True
    return data
```

## Testing

### Unit Testing

```python
from ops_center_sdk.testing import create_test_plugin, trigger_hook
import pytest


@pytest.mark.asyncio
async def test_device_hook():
    # Create test plugin with mocks
    plugin = create_test_plugin("test-plugin")
    
    # Register your hook
    @plugin.hook("device.created")
    async def on_device_created(device_id: str, device_data: dict):
        await plugin.storage.set(f"device:{device_id}", device_data)
    
    # Trigger the hook
    await trigger_hook(
        plugin,
        "device.created",
        device_id="device-123",
        device_data={"name": "Test Device"}
    )
    
    # Verify behavior
    stored = await plugin.storage.get("device:device-123")
    assert stored["name"] == "Test Device"


@pytest.mark.asyncio
async def test_api_calls():
    plugin = create_test_plugin("test-plugin")
    
    # Create mock device
    device = await plugin.api.devices.create({
        "name": "Test Device",
        "type": "server"
    })
    
    # Verify
    assert device["name"] == "Test Device"
    
    # Check API was called
    requests = plugin.api.get_requests(method="POST", endpoint="/devices")
    assert len(requests) == 1
```

### Available Mocks

- `MockAPIClient` - Mock Ops-Center API
- `MockStorage` - Mock key-value storage
- `MockScheduler` - Mock task scheduler
- `MockConfig` - Mock configuration
- `MockLogger` - Mock logger with log inspection

### Pytest Fixtures

```python
def test_with_fixtures(plugin, mock_api, mock_storage):
    """Use pytest fixtures"""
    assert plugin.metadata.id == "test-plugin"
```

## CLI Commands

### Initialize Plugin

```bash
ops-center-plugin init my-plugin \
  --name "My Plugin" \
  --description "Plugin description" \
  --author "Your Name" \
  --category monitoring \
  --type backend
```

### Validate Plugin

```bash
ops-center-plugin validate
```

Checks:
- plugin.yaml is valid
- Required files exist
- Permissions are valid
- Hooks reference existing handlers

### Build Plugin

```bash
ops-center-plugin build
```

Creates:
- `dist/my-plugin-1.0.0.tar.gz` - Plugin package
- `dist/my-plugin-1.0.0.tar.gz.sha256` - Checksum file

### Publish Plugin

```bash
export OPS_CENTER_API_URL=https://ops.example.com
export OPS_CENTER_API_KEY=your_api_key

ops-center-plugin publish
```

## Plugin Manifest

The `plugin.yaml` file defines plugin metadata:

```yaml
id: my-plugin
name: My Awesome Plugin
version: 1.0.0
description: Does something awesome
author: Your Name
type: backend  # backend, frontend, hybrid, container
category: monitoring  # monitoring, ai, security, integration, analytics
homepage: https://github.com/yourorg/my-plugin
repository: https://github.com/yourorg/my-plugin
license: MIT
keywords:
  - monitoring
  - devices
  - automation

pricing:
  model: free  # free, one-time, subscription
  price: 0

permissions:
  - devices:read
  - devices:write
  - alerts:write
  - users:read

hooks:
  - event: device.created
    handler: on_device_created
  - event: device.metrics_updated
    handler: on_metrics_updated

routes:
  - path: /status
    methods: [GET]
    handler: get_status
  - path: /devices/{device_id}/stats
    methods: [GET]
    handler: get_device_stats

config_schema:
  type: object
  properties:
    threshold:
      type: number
      default: 0.8
      description: Anomaly detection threshold
    enabled:
      type: boolean
      default: true
      description: Enable/disable plugin

runtime:
  type: python
  version: "3.11+"
  entrypoint: main.py
```

## Best Practices

### 1. Error Handling

```python
@plugin.hook("device.created")
async def on_device_created(device_id: str, device_data: dict):
    try:
        # Your logic
        await process_device(device_data)
    except Exception as e:
        plugin.logger.error(f"Error processing device: {e}")
        # Don't let exceptions crash the plugin
```

### 2. Async/Await

All plugin methods should be async:

```python
# Good
async def my_handler():
    data = await plugin.storage.get("key")
    return data

# Bad
def my_handler():
    # Won't work with async storage
    data = plugin.storage.get("key")
```

### 3. Resource Cleanup

Always clean up in `on_disable`:

```python
@plugin.on_disable
async def on_disable():
    # Cancel background tasks
    await plugin.scheduler.cancel_all()
    
    # Close connections
    await plugin.api.close()
    
    # Clear caches
    await plugin.storage.clear()
```

### 4. Configuration

Use config for user-settable values:

```python
# Don't hardcode thresholds
threshold = 0.8  # Bad

# Use config
threshold = plugin.config.get("threshold", default=0.8)  # Good
```

### 5. Logging

Use appropriate log levels:

```python
plugin.logger.debug("Detailed debug info")  # Development
plugin.logger.info("Normal operation")      # Production
plugin.logger.warning("Recoverable issue")  # Attention needed
plugin.logger.error("Error occurred")       # Serious problem
```

## Examples

See `examples/` directory for complete examples:

- `device_anomaly_detector.py` - ML-based anomaly detection
- More examples coming soon!

## API Reference

Full API documentation: [https://docs.ops-center.com/plugins/sdk](https://docs.ops-center.com/plugins/sdk)

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - see [LICENSE](LICENSE)

## Support

- Documentation: https://docs.ops-center.com/plugins
- Issues: https://github.com/ops-center/plugin-sdk/issues
- Discussions: https://github.com/ops-center/plugin-sdk/discussions
