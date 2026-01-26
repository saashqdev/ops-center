# Example Plugins

This directory contains example plugins demonstrating various plugin capabilities.

## Backend Plugins (Python)

### 1. Device Anomaly Detector
**File:** `device_anomaly_detector.py`  
**Type:** Backend (AI/ML)  
**Category:** Monitoring

Demonstrates ML-based anomaly detection for device metrics.

**Features:**
- Lifecycle hooks (install, enable, disable)
- Event hooks (device.created, device.metrics_updated)
- Filter hooks (device.data.process)
- Custom API routes (/predict, /stats, /detections)
- Background tasks (scheduled model training)
- Storage usage
- Configuration management
- Alert creation

**Usage:**
```bash
cd sdk/python
pip install -r requirements.txt
python examples/device_anomaly_detector.py
```

### 2. Slack Integration
**File:** `slack_integration.py`  
**Type:** Backend (Integration)  
**Category:** Integration

Sends Ops-Center notifications to Slack channels.

**Features:**
- External API integration (Slack webhooks)
- Event hooks for devices, alerts, users
- Configurable notification filters
- Custom message sending API
- Request statistics tracking
- Webhook testing endpoint

**Configuration:**
```yaml
webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
notify_device_events: true
notify_alert_events: true
alert_severity_filter: ["warning", "error", "critical"]
channel_overrides:
  device-123: "https://hooks.slack.com/services/DEVICE/CHANNEL"
```

**API Endpoints:**
- `POST /plugins/slack-integration/test` - Test webhook
- `GET /plugins/slack-integration/stats` - Get statistics
- `POST /plugins/slack-integration/send` - Send custom message

### 3. Automated Backup
**File:** `automated_backup.py`  
**Type:** Backend (Utility)  
**Category:** Security

Automated backups of device configurations and system data.

**Features:**
- Scheduled backups (cron-based)
- Compression (tar.gz)
- Retention policy (automatic cleanup)
- Backup device configs, alerts, users
- File operations
- Manual backup trigger
- Backup listing and statistics

**Configuration:**
```yaml
backup_schedule: "0 2 * * *"  # Daily at 2 AM
backup_path: "/var/backups/ops-center"
retention_days: 30
compress_backups: true
backup_device_configs: true
backup_alerts: true
backup_users: false
max_backup_size_mb: 1024
```

**API Endpoints:**
- `POST /plugins/automated-backup/backup/now` - Trigger immediate backup
- `GET /plugins/automated-backup/backups` - List all backups
- `GET /plugins/automated-backup/stats` - Get backup statistics

## Frontend Plugins (React)

### 4. Device Status Widget
**File:** `device-status-widget/index.tsx`  
**Type:** Frontend (Dashboard Widget)  
**Category:** Monitoring

Dashboard widget showing device status overview.

**Features:**
- Real-time device stats
- Auto-refresh
- Device filtering
- Settings panel
- Event subscriptions
- Professional UI with Card, Badge components

**Configuration:**
```json
{
  "refreshInterval": 30000,
  "showOfflineDevices": true,
  "maxDevices": 10
}
```

### 5. Metrics Dashboard
**File:** `metrics-dashboard/index.tsx`  
**Type:** Frontend (Visualization)  
**Category:** Analytics

Advanced metrics visualization with custom charts.

**Features:**
- Real-time metric charts (CPU, Memory, Network)
- Multiple chart types (line, bar, area)
- Device selector
- Configurable refresh rate
- Multiple slot registration (dashboard + device detail)
- Custom SVG charts (no external dependencies)

**Configuration:**
```json
{
  "refreshInterval": 5000,
  "showCpuChart": true,
  "showMemoryChart": true,
  "showNetworkChart": true,
  "chartType": "line",
  "maxDataPoints": 20
}
```

## Running Examples

### Python Examples

```bash
# Install SDK
pip install ops-center-plugin-sdk

# Run example
cd sdk/python/examples
python device_anomaly_detector.py
# or
python slack_integration.py
# or
python automated_backup.py
```

### JavaScript Examples

```bash
# Install SDK
npm install @ops-center/plugin-sdk react react-dom

# Build example
cd sdk/javascript/examples/device-status-widget
npm install
npm run build

# Or for metrics dashboard
cd sdk/javascript/examples/metrics-dashboard
npm install
npm run build
```

## Testing Examples

### Python

```bash
cd sdk/python
pytest tests/test_example_plugin.py
```

### JavaScript

```bash
cd sdk/javascript
npm test
```

## Plugin Comparison

| Plugin | Type | Language | LOC | Key Feature |
|--------|------|----------|-----|-------------|
| Device Anomaly Detector | Backend | Python | 300 | ML-based anomaly detection |
| Slack Integration | Backend | Python | 300 | External API integration |
| Automated Backup | Backend | Python | 350 | Scheduled file operations |
| Device Status Widget | Frontend | React/TS | 250 | Dashboard widget |
| Metrics Dashboard | Frontend | React/TS | 400 | Data visualization |

## Learning Path

**Beginner:**
1. Start with **Device Status Widget** - Simple frontend plugin
2. Then try **Slack Integration** - Simple backend integration

**Intermediate:**
3. Explore **Device Anomaly Detector** - Complex backend logic
4. Try **Metrics Dashboard** - Advanced UI components

**Advanced:**
5. Study **Automated Backup** - File operations and scheduling
6. Build your own hybrid plugin combining backend + frontend

## Next Steps

- Modify these examples for your use case
- Combine features from multiple examples
- Build your own custom plugins
- Share your plugins with the community!
