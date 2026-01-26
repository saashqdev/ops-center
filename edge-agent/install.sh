#!/bin/bash
#
# Ops-Center Edge Agent Installation Script
# Epic 7.1: Edge Device Management
#
# Usage: curl -fsSL https://your-domain.com/install-edge-agent.sh | bash -s <REGISTRATION_TOKEN>
#

set -e

REGISTRATION_TOKEN="${1:-}"
CLOUD_URL="${CLOUD_URL:-https://your-domain.com}"
INSTALL_DIR="/opt/edge-agent"
SERVICE_NAME="ops-center-edge-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use sudo)"
    exit 1
fi

# Validate registration token
if [ -z "$REGISTRATION_TOKEN" ]; then
    log_error "Registration token required"
    echo "Usage: $0 <REGISTRATION_TOKEN>"
    exit 1
fi

log_info "Installing Ops-Center Edge Agent..."
log_info "Cloud URL: $CLOUD_URL"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    log_error "Cannot detect OS"
    exit 1
fi

log_info "Detected OS: $OS $VERSION"

# Install dependencies
log_info "Installing dependencies..."

if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    apt-get update
    apt-get install -y python3 python3-pip python3-venv curl
elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "fedora" ]]; then
    yum install -y python3 python3-pip curl
else
    log_warn "Unsupported OS: $OS"
    log_info "Attempting to continue anyway..."
fi

# Create installation directory
log_info "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download edge agent
log_info "Downloading edge agent..."

# For development, we'll create it from the local version
# In production, this would download from GitHub releases or your CDN
cat > edge_agent.py << 'EDGE_AGENT_SCRIPT'
#!/usr/bin/env python3
# Edge agent script will be embedded here in production
# For now, this is a placeholder
import sys
print("Edge agent placeholder - replace with actual agent code")
sys.exit(0)
EDGE_AGENT_SCRIPT

chmod +x edge_agent.py

# Create Python virtual environment
log_info "Creating Python virtual environment..."
python3 -m venv venv

# Install Python dependencies
log_info "Installing Python packages..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install aiohttp psutil

# Create systemd service
log_info "Creating systemd service..."

cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Ops-Center Edge Agent
After=network.target docker.service
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/edge_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Register device
log_info "Registering device with Ops-Center..."

${INSTALL_DIR}/venv/bin/python3 << EOF
import asyncio
import aiohttp
import platform
import json
import uuid
from pathlib import Path

async def register():
    hardware_id = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 48, 8)])
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "${CLOUD_URL}/api/v1/edge/devices/register",
                json={
                    "hardware_id": hardware_id,
                    "registration_token": "${REGISTRATION_TOKEN}",
                    "firmware_version": platform.platform(),
                    "metadata": {
                        "hostname": platform.node(),
                        "architecture": platform.machine(),
                        "os": platform.system()
                    }
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Save credentials
                    creds_dir = Path("/etc/edge-agent")
                    creds_dir.mkdir(parents=True, exist_ok=True)
                    
                    with open(creds_dir / "credentials.json", 'w') as f:
                        json.dump({
                            "device_id": data['device_id'],
                            "auth_token": data['auth_token'],
                            "cloud_url": "${CLOUD_URL}"
                        }, f)
                    
                    print(f"SUCCESS: Device registered as {data['device_name']}")
                    return 0
                else:
                    error = await resp.text()
                    print(f"ERROR: Registration failed: {error}")
                    return 1
        except Exception as e:
            print(f"ERROR: {e}")
            return 1

exit(asyncio.run(register()))
EOF

if [ $? -ne 0 ]; then
    log_error "Device registration failed"
    exit 1
fi

log_info "Device registered successfully!"

# Set permissions
chmod 600 /etc/edge-agent/credentials.json

# Enable and start service
log_info "Enabling and starting service..."
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

# Check status
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "✓ Edge agent installed and running!"
    log_info ""
    log_info "Service status: systemctl status ${SERVICE_NAME}"
    log_info "View logs: journalctl -u ${SERVICE_NAME} -f"
    log_info "Device credentials: /etc/edge-agent/credentials.json"
else
    log_error "Service failed to start"
    log_info "Check logs: journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi

log_info ""
log_info "Installation complete!"
