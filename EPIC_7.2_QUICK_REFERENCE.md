# Epic 7.2: OTA Updates - Quick Reference Guide

## 🎯 Quick Start

### Creating an OTA Deployment (UI)

1. **Navigate to OTA Deployments**
   - Go to `/admin/edge/ota` in the Ops-Center UI
   - Click "New Deployment"

2. **Step 1: Basic Info**
   ```
   Deployment Name:    "Firmware Update v2.1.0"
   Target Version:     "v2.1.0"
   Rollout Strategy:   [Canary]
   Canary Percentage:  20%
   ```

3. **Step 2: Target Devices**
   ```
   Device Type:        "raspberry_pi" (optional)
   Version Operator:   !=
   Current Version:    "v2.0.0"
   Device Status:      Online only
   ```

4. **Step 3: Update Package**
   ```
   Update Package URL: "https://cdn.example.com/updates/v2.1.0.tar.gz"
   SHA256 Checksum:    "abc123def456..."
   Release Notes:      "Bug fixes and performance improvements"
   ```

5. **Step 4: Review and Create**
   - Review settings
   - Click "Create Deployment"
   - Deployment starts in PENDING status

6. **Start Deployment**
   - Click deployment in list
   - Click "Start" button
   - Monitor progress in real-time

---

## 🔧 API Quick Reference

### Create Deployment (cURL)

```bash
curl -X POST http://localhost:8084/api/v1/admin/ota/deployments \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_name": "Firmware Update v2.1.0",
    "target_version": "v2.1.0",
    "rollout_strategy": "canary",
    "rollout_percentage": 20,
    "device_filters": {
      "device_type": "raspberry_pi",
      "current_version": "v2.0.0",
      "version_operator": "!=",
      "status": "online"
    },
    "update_package_url": "https://cdn.example.com/updates/v2.1.0.tar.gz",
    "checksum": "sha256:abc123...",
    "release_notes": "Bug fixes and performance improvements"
  }'
```

### Start Deployment

```bash
curl -X POST \
  http://localhost:8084/api/v1/admin/ota/deployments/DEPLOYMENT_ID/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Deployment Status

```bash
curl -X GET \
  http://localhost:8084/api/v1/admin/ota/deployments/DEPLOYMENT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Pause Deployment

```bash
curl -X POST \
  http://localhost:8084/api/v1/admin/ota/deployments/DEPLOYMENT_ID/pause \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Resume Deployment

```bash
curl -X POST \
  http://localhost:8084/api/v1/admin/ota/deployments/DEPLOYMENT_ID/resume \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Cancel Deployment

```bash
curl -X POST \
  http://localhost:8084/api/v1/admin/ota/deployments/DEPLOYMENT_ID/cancel \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Rollback Device

```bash
curl -X POST \
  http://localhost:8084/api/v1/admin/ota/deployments/DEPLOYMENT_ID/devices/DEVICE_ID/rollback \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"previous_version": "v2.0.0"}'
```

---

## 📦 Update Package Format

Your update package should be a `.tar.gz` file with this structure:

```
update-v2.1.0.tar.gz
├── install.sh              # Installation script (required)
├── edge_agent.py           # Updated agent binary (optional)
├── firmware/
│   ├── kernel.img
│   └── bootloader.bin
└── config/
    └── default-config.json
```

### Example install.sh

```bash
#!/bin/bash
set -e

echo "Installing update v2.1.0..."

# Backup current agent
cp /usr/local/bin/edge_agent.py /usr/local/bin/edge_agent.py.backup

# Copy new agent
if [ -f "edge_agent.py" ]; then
    cp edge_agent.py /usr/local/bin/edge_agent.py
    chmod +x /usr/local/bin/edge_agent.py
fi

# Update firmware
if [ -d "firmware" ]; then
    cp -r firmware/* /boot/firmware/
fi

# Update config
if [ -d "config" ]; then
    cp config/* /etc/edge-agent/
fi

echo "Installation complete!"
```

### Generate Checksum

```bash
sha256sum update-v2.1.0.tar.gz
# Output: abc123def456... update-v2.1.0.tar.gz
```

---

## 🎛️ Rollout Strategies

### 1. Manual
- **Use Case:** Critical updates, specific devices
- **Behavior:** Admin manually selects devices via filters
- **Risk:** Low (full control)

### 2. Immediate
- **Use Case:** Non-critical updates, urgent fixes
- **Behavior:** All matching devices updated simultaneously
- **Risk:** High (no gradual rollout)

### 3. Canary
- **Use Case:** Production-wide updates
- **Behavior:** 
  1. Deploy to X% of devices (configurable)
  2. Monitor results
  3. Manually expand to 100% if successful
- **Risk:** Medium (test on subset first)
- **Example:** 20% canary → monitor → 100% rollout

### 4. Rolling
- **Use Case:** Large-scale gradual deployment
- **Behavior:**
  1. Deploy to batch 1 (20% or min 5 devices)
  2. Wait for completion
  3. Automatically deploy to batch 2
  4. Continue until all updated
- **Risk:** Medium (automatic gradual rollout)

---

## 🔍 Device Filters

### Filter by Device Type
```json
{
  "device_type": "raspberry_pi"
}
```

### Filter by Version
```json
{
  "current_version": "v2.0.0",
  "version_operator": "!="  // Options: <, <=, !=, =
}
```

### Filter by Status
```json
{
  "status": "online"  // Options: "", "online", "offline"
}
```

### Combine Filters
```json
{
  "device_filters": {
    "device_type": "raspberry_pi",
    "current_version": "v2.0.0",
    "version_operator": "!=",
    "status": "online"
  }
}
```

---

## 📊 Status Reference

### Deployment Statuses
- `pending` - Created but not started
- `in_progress` - Currently deploying
- `completed` - All devices updated successfully
- `failed` - One or more devices failed
- `paused` - Manually paused by admin
- `cancelled` - Manually cancelled

### Device Update Statuses
- `pending` - Waiting for update
- `downloading` - Downloading update package
- `installing` - Installing update
- `verifying` - Running health checks
- `completed` - Update successful
- `failed` - Update failed
- `skipped` - Deployment cancelled
- `rolled_back` - Rolled back to previous version

---

## 🚨 Troubleshooting

### Problem: Devices not receiving updates
**Solution:**
1. Check deployment status is `in_progress`
2. Verify devices are online
3. Check device filters aren't too restrictive
4. Verify edge agent is running and checking for updates

### Problem: Update fails during installation
**Solution:**
1. Check installation logs in deployment details
2. Verify update package format
3. Check install.sh script for errors
4. Try manual rollback

### Problem: Checksum verification fails
**Solution:**
1. Regenerate checksum: `sha256sum update.tar.gz`
2. Update deployment with correct checksum
3. Verify update package wasn't corrupted during upload

### Problem: Deployment stuck at 0%
**Solution:**
1. Check if deployment was started (click "Start")
2. Verify devices are online and checking for updates
3. Check backend logs for errors
4. Restart deployment if needed

---

## 🔐 Security Best Practices

1. **Always use checksums**
   - Never deploy without SHA256 verification
   - Prevents corrupted or tampered packages

2. **Test in canary mode**
   - Start with 10-20% canary deployment
   - Monitor for issues before full rollout

3. **HTTPS-only package URLs**
   - Never use HTTP for update downloads
   - Prevents man-in-the-middle attacks

4. **Verify before rollout**
   - Test update package on test device first
   - Create backups before deployment

5. **Monitor actively**
   - Watch first batch of updates closely
   - Be ready to pause if issues arise

---

## 📱 Edge Agent Integration

Your edge agent automatically handles OTA updates. No configuration needed!

### Update Check Interval
- Default: Every 5 minutes
- Customizable in edge agent config

### Automatic Features
- ✅ Update package download
- ✅ Checksum verification
- ✅ Automatic installation
- ✅ Health verification
- ✅ Automatic rollback on failure
- ✅ Status reporting to cloud

---

## 📈 Monitoring

### Key Metrics
- **Success Rate:** % of devices updated successfully
- **Average Duration:** Time from download to completion
- **Rollback Rate:** % of updates that failed and rolled back
- **Compliance:** % of devices on target version

### Real-Time Monitoring
- View in OTA Deployment UI
- Click deployment for detailed progress
- Per-device status in table view

---

## 🎯 Common Use Cases

### Use Case 1: Urgent Security Patch
```
Strategy: Immediate
Filters: status=online
Rollout: All devices at once
```

### Use Case 2: Major Version Upgrade
```
Strategy: Canary (20%)
Filters: current_version!=v2.0.0, status=online
Rollout: Test on 20% → Monitor → Expand to 100%
```

### Use Case 3: Specific Device Type Update
```
Strategy: Rolling
Filters: device_type=nvidia_jetson, status=online
Rollout: Gradual batch deployment
```

### Use Case 4: Individual Device Update
```
Strategy: Manual
Filters: None (select specific device)
Rollout: Single device
```

---

**For detailed documentation, see [EPIC_7.2_COMPLETE.md](EPIC_7.2_COMPLETE.md)**

**UI Access:** `/admin/edge/ota`  
**API Docs:** `/api/v1/admin/ota/` (admin), `/api/v1/ota/` (devices)
