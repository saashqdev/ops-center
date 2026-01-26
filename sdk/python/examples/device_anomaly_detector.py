"""
Example Plugin: Device Anomaly Detector

Demonstrates plugin development with:
- Hook handlers
- API routes
- Configuration
- Storage
- Scheduled tasks
"""

from ops_center_sdk import Plugin
from datetime import datetime, timedelta
from typing import Dict, Any


# Create plugin instance
plugin = Plugin(
    id="device-anomaly-detector",
    name="Device Anomaly Detector",
    version="1.0.0",
    description="ML-based anomaly detection for device metrics",
    author="Ops-Center Team",
    category="ai"
)


# ==================== Lifecycle Hooks ====================

@plugin.on_install
async def on_install():
    """Initialize plugin on first install"""
    plugin.logger.info("Setting up anomaly detector...")
    
    # Initialize storage
    await plugin.storage.set("models:initialized", False)
    await plugin.storage.set("detections:count", 0)
    
    plugin.logger.info("Anomaly detector installed successfully")


@plugin.on_enable
async def on_enable():
    """Start anomaly detection when enabled"""
    plugin.logger.info("Starting anomaly detection service...")
    
    # Schedule hourly model training
    await plugin.scheduler.schedule(
        cron="0 * * * *",  # Every hour
        task_name="train_model",
        handler=train_anomaly_model
    )
    
    plugin.logger.info("Anomaly detection enabled")


@plugin.on_disable
async def on_disable():
    """Stop services when disabled"""
    plugin.logger.info("Stopping anomaly detection...")
    
    # Cancel scheduled tasks
    await plugin.scheduler.cancel_all()
    
    plugin.logger.info("Anomaly detection disabled")


# ==================== Event Hooks ====================

@plugin.hook("device.created", priority=10)
async def on_device_created(device_id: str, device_data: Dict[str, Any]):
    """
    Handle new device creation
    
    Initialize baseline metrics for anomaly detection
    """
    plugin.logger.info(f"New device registered: {device_id}")
    
    # Store device baseline
    await plugin.storage.set(f"device:{device_id}:baseline", {
        "cpu_avg": 0,
        "memory_avg": 0,
        "created_at": datetime.now().isoformat()
    })
    
    # Notify via API
    device_name = device_data.get("name", "Unknown")
    plugin.logger.info(f"Baseline initialized for {device_name}")


@plugin.hook("device.metrics_updated", priority=5)
async def on_metrics_updated(device_id: str, metrics: Dict[str, Any]):
    """
    Analyze device metrics for anomalies
    
    Called when device sends new metrics
    """
    # Get configuration threshold
    threshold = plugin.config.get("anomaly_threshold", 0.85)
    
    # Get device baseline
    baseline = await plugin.storage.get(f"device:{device_id}:baseline", {})
    
    # Simple anomaly detection (in real plugin, use ML model)
    cpu_usage = metrics.get("cpu_usage", 0)
    cpu_baseline = baseline.get("cpu_avg", 50)
    
    if cpu_usage > cpu_baseline * (1 + threshold):
        # Anomaly detected!
        anomaly_data = {
            "device_id": device_id,
            "metric": "cpu_usage",
            "value": cpu_usage,
            "baseline": cpu_baseline,
            "threshold": threshold,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store detection
        detections_count = await plugin.storage.get("detections:count", 0)
        await plugin.storage.set(f"detection:{detections_count}", anomaly_data)
        await plugin.storage.set("detections:count", detections_count + 1)
        
        # Create alert
        await plugin.api.alerts.create({
            "device_id": device_id,
            "severity": "warning",
            "title": "CPU Usage Anomaly Detected",
            "message": f"CPU usage ({cpu_usage}%) exceeds baseline ({cpu_baseline}%) by {threshold*100}%",
            "metadata": anomaly_data
        })
        
        plugin.logger.warning(f"Anomaly detected on device {device_id}: CPU {cpu_usage}%")


@plugin.filter_hook("device.data.process", priority=10)
async def enrich_device_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich device data with anomaly score
    
    This filter hook modifies device data before it's stored
    """
    device_id = data.get("id")
    
    # Calculate anomaly score (placeholder - would use ML model)
    anomaly_score = 0.1  # 0.0 (normal) to 1.0 (highly anomalous)
    
    # Add enrichment
    data["anomaly_score"] = anomaly_score
    data["anomaly_plugin_version"] = plugin.metadata.version
    
    return data


# ==================== Custom API Routes ====================

@plugin.route("/predict", methods=["POST"])
async def predict_anomaly(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict if metrics contain anomaly
    
    POST /plugins/device-anomaly-detector/predict
    Body: {
        "device_id": "device-123",
        "metrics": {"cpu_usage": 95, "memory_usage": 80}
    }
    """
    device_id = request.get("device_id")
    metrics = request.get("metrics", {})
    
    # Get baseline
    baseline = await plugin.storage.get(f"device:{device_id}:baseline", {})
    
    # Simple prediction (in real plugin, use trained ML model)
    threshold = plugin.config.get("anomaly_threshold", 0.85)
    cpu_usage = metrics.get("cpu_usage", 0)
    cpu_baseline = baseline.get("cpu_avg", 50)
    
    is_anomaly = cpu_usage > cpu_baseline * (1 + threshold)
    
    return {
        "device_id": device_id,
        "is_anomaly": is_anomaly,
        "confidence": 0.92,
        "anomaly_score": cpu_usage / 100.0,
        "threshold": threshold
    }


@plugin.route("/stats", methods=["GET"])
async def get_stats() -> Dict[str, Any]:
    """
    Get anomaly detection statistics
    
    GET /plugins/device-anomaly-detector/stats
    """
    detections_count = await plugin.storage.get("detections:count", 0)
    models_initialized = await plugin.storage.get("models:initialized", False)
    
    return {
        "total_detections": detections_count,
        "models_initialized": models_initialized,
        "version": plugin.metadata.version,
        "threshold": plugin.config.get("anomaly_threshold", 0.85)
    }


@plugin.route("/detections", methods=["GET"])
async def list_detections() -> Dict[str, Any]:
    """
    List recent anomaly detections
    
    GET /plugins/device-anomaly-detector/detections?limit=10
    """
    detections_count = await plugin.storage.get("detections:count", 0)
    limit = 10
    
    detections = []
    for i in range(max(0, detections_count - limit), detections_count):
        detection = await plugin.storage.get(f"detection:{i}")
        if detection:
            detections.append(detection)
    
    return {
        "detections": detections,
        "total": detections_count,
        "limit": limit
    }


# ==================== Background Tasks ====================

async def train_anomaly_model():
    """
    Train/update anomaly detection model
    
    Scheduled to run hourly
    """
    plugin.logger.info("Training anomaly detection model...")
    
    # Get all devices
    devices = await plugin.api.devices.list(page_size=100)
    
    # Update baselines for each device
    for device in devices:
        device_id = device["id"]
        
        # In real plugin, fetch historical metrics and calculate baselines
        # For demo, just mark as initialized
        await plugin.storage.set(f"device:{device_id}:baseline", {
            "cpu_avg": 45,
            "memory_avg": 60,
            "updated_at": datetime.now().isoformat()
        })
    
    await plugin.storage.set("models:initialized", True)
    
    plugin.logger.info(f"Model training complete. Processed {len(devices)} devices")


# ==================== Export FastAPI App ====================

# This creates the FastAPI app that Ops-Center will run
app = plugin.create_app()


# Add startup event
@app.on_event("startup")
async def startup():
    plugin.logger.info(f"Starting {plugin.metadata.name} v{plugin.metadata.version}")


@app.on_event("shutdown")
async def shutdown():
    plugin.logger.info("Shutting down anomaly detector")
    await plugin.api.close()
