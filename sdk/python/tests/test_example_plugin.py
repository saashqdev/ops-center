"""
Tests for example device anomaly detector plugin
"""

import pytest
from datetime import datetime
from ops_center_sdk.testing import create_test_plugin, trigger_hook, trigger_filter


@pytest.fixture
def plugin():
    """Create test plugin instance"""
    return create_test_plugin(
        "device-anomaly-detector",
        name="Device Anomaly Detector",
        version="1.0.0",
        config={
            "anomaly_threshold": 0.85,
            "enabled": True
        }
    )


@pytest.mark.asyncio
async def test_plugin_installation(plugin):
    """Test plugin installation lifecycle"""
    # Simulate install
    await plugin.storage.set("models:initialized", False)
    await plugin.storage.set("detections:count", 0)
    
    # Verify storage
    initialized = await plugin.storage.get("models:initialized")
    count = await plugin.storage.get("detections:count")
    
    assert initialized is False
    assert count == 0


@pytest.mark.asyncio
async def test_device_created_hook(plugin):
    """Test device creation hook handler"""
    device_id = "device-123"
    device_data = {
        "id": device_id,
        "name": "Test Server",
        "type": "server"
    }
    
    # Define hook handler (would normally be in plugin file)
    @plugin.hook("device.created")
    async def on_device_created(device_id: str, device_data: dict):
        await plugin.storage.set(f"device:{device_id}:baseline", {
            "cpu_avg": 0,
            "memory_avg": 0,
            "created_at": datetime.now().isoformat()
        })
    
    # Trigger hook
    await trigger_hook(plugin, "device.created", device_id=device_id, device_data=device_data)
    
    # Verify baseline was stored
    baseline = await plugin.storage.get(f"device:{device_id}:baseline")
    assert baseline is not None
    assert baseline["cpu_avg"] == 0
    assert "created_at" in baseline


@pytest.mark.asyncio
async def test_metrics_anomaly_detection(plugin):
    """Test anomaly detection in metrics hook"""
    device_id = "device-456"
    
    # Set baseline
    await plugin.storage.set(f"device:{device_id}:baseline", {
        "cpu_avg": 50,
        "memory_avg": 60
    })
    
    # Define metrics hook
    @plugin.hook("device.metrics_updated")
    async def on_metrics_updated(device_id: str, metrics: dict):
        threshold = plugin.config.get("anomaly_threshold", 0.85)
        baseline = await plugin.storage.get(f"device:{device_id}:baseline", {})
        
        cpu_usage = metrics.get("cpu_usage", 0)
        cpu_baseline = baseline.get("cpu_avg", 50)
        
        if cpu_usage > cpu_baseline * (1 + threshold):
            # Anomaly detected
            detections_count = await plugin.storage.get("detections:count", 0)
            
            anomaly_data = {
                "device_id": device_id,
                "metric": "cpu_usage",
                "value": cpu_usage,
                "baseline": cpu_baseline,
                "threshold": threshold,
                "timestamp": datetime.now().isoformat()
            }
            
            await plugin.storage.set(f"detection:{detections_count}", anomaly_data)
            await plugin.storage.set("detections:count", detections_count + 1)
            
            # Create alert
            await plugin.api.alerts.create({
                "device_id": device_id,
                "severity": "warning",
                "title": "CPU Usage Anomaly Detected",
                "message": f"CPU usage ({cpu_usage}%) exceeds baseline"
            })
    
    # Trigger with normal metrics
    await trigger_hook(
        plugin,
        "device.metrics_updated",
        device_id=device_id,
        metrics={"cpu_usage": 60}
    )
    
    # Should not create detection
    count = await plugin.storage.get("detections:count", 0)
    assert count == 0
    
    # Trigger with anomalous metrics
    await trigger_hook(
        plugin,
        "device.metrics_updated",
        device_id=device_id,
        metrics={"cpu_usage": 95}  # 95% > 50 * 1.85
    )
    
    # Should create detection
    count = await plugin.storage.get("detections:count", 0)
    assert count == 1
    
    detection = await plugin.storage.get("detection:0")
    assert detection["value"] == 95
    assert detection["baseline"] == 50
    
    # Verify alert was created
    alerts = plugin.api.get_requests(endpoint="/alerts")
    assert len(alerts) == 1


@pytest.mark.asyncio
async def test_device_data_filter(plugin):
    """Test filter hook for enriching device data"""
    
    @plugin.filter_hook("device.data.process")
    async def enrich_device_data(data: dict) -> dict:
        data["anomaly_score"] = 0.1
        data["anomaly_plugin_version"] = plugin.metadata.version
        return data
    
    # Original data
    device_data = {
        "id": "device-789",
        "name": "Test Device",
        "status": "online"
    }
    
    # Apply filter
    enriched = await trigger_filter(plugin, "device.data.process", device_data)
    
    # Verify enrichment
    assert enriched["anomaly_score"] == 0.1
    assert enriched["anomaly_plugin_version"] == "1.0.0"
    assert enriched["name"] == "Test Device"  # Original data preserved


@pytest.mark.asyncio
async def test_api_predict_endpoint(plugin):
    """Test prediction API endpoint"""
    device_id = "device-999"
    
    # Set baseline
    await plugin.storage.set(f"device:{device_id}:baseline", {
        "cpu_avg": 45,
        "memory_avg": 60
    })
    
    # Simulate prediction request
    request_data = {
        "device_id": device_id,
        "metrics": {
            "cpu_usage": 95,
            "memory_usage": 80
        }
    }
    
    # This would be the handler logic
    baseline = await plugin.storage.get(f"device:{device_id}:baseline", {})
    threshold = plugin.config.get("anomaly_threshold", 0.85)
    
    cpu_usage = request_data["metrics"]["cpu_usage"]
    cpu_baseline = baseline["cpu_avg"]
    
    is_anomaly = cpu_usage > cpu_baseline * (1 + threshold)
    
    # Verify prediction
    assert is_anomaly is True
    assert cpu_usage == 95
    assert cpu_baseline == 45


@pytest.mark.asyncio
async def test_stats_endpoint(plugin):
    """Test stats API endpoint"""
    # Set up some data
    await plugin.storage.set("detections:count", 42)
    await plugin.storage.set("models:initialized", True)
    
    # Simulate stats request
    detections_count = await plugin.storage.get("detections:count", 0)
    models_initialized = await plugin.storage.get("models:initialized", False)
    
    stats = {
        "total_detections": detections_count,
        "models_initialized": models_initialized,
        "version": plugin.metadata.version,
        "threshold": plugin.config.get("anomaly_threshold", 0.85)
    }
    
    # Verify stats
    assert stats["total_detections"] == 42
    assert stats["models_initialized"] is True
    assert stats["version"] == "1.0.0"
    assert stats["threshold"] == 0.85


@pytest.mark.asyncio
async def test_list_detections_endpoint(plugin):
    """Test listing detections"""
    # Create some detections
    for i in range(15):
        await plugin.storage.set(f"detection:{i}", {
            "device_id": f"device-{i}",
            "value": 90 + i,
            "timestamp": datetime.now().isoformat()
        })
    
    await plugin.storage.set("detections:count", 15)
    
    # Simulate list request
    detections_count = await plugin.storage.get("detections:count", 0)
    limit = 10
    
    detections = []
    for i in range(max(0, detections_count - limit), detections_count):
        detection = await plugin.storage.get(f"detection:{i}")
        if detection:
            detections.append(detection)
    
    # Should return last 10 detections
    assert len(detections) == 10
    assert detections[0]["device_id"] == "device-5"
    assert detections[-1]["device_id"] == "device-14"


@pytest.mark.asyncio
async def test_scheduled_model_training(plugin):
    """Test background model training task"""
    # Create mock devices
    await plugin.api.devices.create({"id": "device-1", "name": "Device 1"})
    await plugin.api.devices.create({"id": "device-2", "name": "Device 2"})
    await plugin.api.devices.create({"id": "device-3", "name": "Device 3"})
    
    # Simulate model training task
    devices = await plugin.api.devices.list(page_size=100)
    
    for device in devices:
        device_id = device["id"]
        await plugin.storage.set(f"device:{device_id}:baseline", {
            "cpu_avg": 45,
            "memory_avg": 60,
            "updated_at": datetime.now().isoformat()
        })
    
    await plugin.storage.set("models:initialized", True)
    
    # Verify baselines created
    baseline1 = await plugin.storage.get("device:device-1:baseline")
    baseline2 = await plugin.storage.get("device:device-2:baseline")
    baseline3 = await plugin.storage.get("device:device-3:baseline")
    
    assert baseline1 is not None
    assert baseline2 is not None
    assert baseline3 is not None
    
    initialized = await plugin.storage.get("models:initialized")
    assert initialized is True


@pytest.mark.asyncio
async def test_configuration_usage(plugin):
    """Test plugin configuration"""
    # Default threshold
    threshold = plugin.config.get("anomaly_threshold", 0.85)
    assert threshold == 0.85
    
    # Update threshold
    plugin.config.set("anomaly_threshold", 0.9)
    new_threshold = plugin.config.get("anomaly_threshold")
    assert new_threshold == 0.9
    
    # Get all config
    all_config = plugin.config.all()
    assert "anomaly_threshold" in all_config
    assert "enabled" in all_config


@pytest.mark.asyncio
async def test_logger_usage(plugin):
    """Test plugin logging"""
    # Log messages
    plugin.logger.info("Test info message")
    plugin.logger.warning("Test warning message")
    plugin.logger.error("Test error message")
    
    # Verify logs were recorded
    logs = plugin.logger.get_logs()
    assert len(logs) == 3
    
    # Check specific log levels
    info_logs = plugin.logger.get_logs(level="INFO")
    warning_logs = plugin.logger.get_logs(level="WARNING")
    error_logs = plugin.logger.get_logs(level="ERROR")
    
    assert len(info_logs) == 1
    assert len(warning_logs) == 1
    assert len(error_logs) == 1
    
    assert info_logs[0]["message"] == "Test info message"
