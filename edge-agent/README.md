# Ops-Center Edge Agent

The Edge Agent is a lightweight Python application that runs on edge devices to connect them to Ops-Center for centralized management.

## Features

- **Automatic Heartbeat**: Sends device status every 30 seconds
- **Configuration Management**: Receives and applies configuration updates from Ops-Center
- **Metrics Collection**: Reports CPU, memory, disk, network, and GPU metrics
- **Log Streaming**: Forwards device logs to central logging
- **Service Monitoring**: Tracks Docker container status
- **OTA Updates**: Supports over-the-air firmware updates

## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://your-domain.com/install-edge-agent.sh | sudo bash -s <REGISTRATION_TOKEN>
```

Replace `<REGISTRATION_TOKEN>` with the token generated from Ops-Center admin panel.

### Manual Installation

1. **Install Dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv
   ```

2. **Create Installation Directory**:
   ```bash
   sudo mkdir -p /opt/edge-agent
   cd /opt/edge-agent
   ```

3. **Download Edge Agent**:
   ```bash
   curl -fsSL https://your-domain.com/downloads/edge-agent.tar.gz | tar -xz
   ```

4. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

5. **Register Device**:
   ```bash
   sudo ./venv/bin/python3 edge_agent.py --register --token <REGISTRATION_TOKEN> --cloud-url https://your-domain.com
   ```

6. **Install Systemd Service**:
   ```bash
   sudo cp edge-agent.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable edge-agent
   sudo systemctl start edge-agent
   ```

## Configuration

Configuration is automatically managed by Ops-Center, but you can manually edit:

- **Credentials**: `/etc/edge-agent/credentials.json`
- **Config**: `/etc/edge-agent/config.json`

## Usage

### Start/Stop Service

```bash
# Start
sudo systemctl start edge-agent

# Stop
sudo systemctl stop edge-agent

# Restart
sudo systemctl restart edge-agent

# Status
sudo systemctl status edge-agent
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u edge-agent -f

# View last 100 lines
sudo journalctl -u edge-agent -n 100

# View logs since boot
sudo journalctl -u edge-agent -b
```

### Manual Registration

If you need to re-register a device:

```bash
cd /opt/edge-agent
sudo ./venv/bin/python3 edge_agent.py --register --token <NEW_TOKEN> --cloud-url https://your-domain.com
sudo systemctl restart edge-agent
```

## System Requirements

- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **Python**: 3.8 or higher
- **RAM**: 128MB minimum
- **Disk**: 500MB minimum
- **Network**: Outbound HTTPS (443) to Ops-Center

## Architecture

```
┌─────────────────────────────┐
│      Edge Device Agent      │
│                             │
│  ┌──────────────────────┐  │
│  │  Heartbeat Loop      │  │──┐
│  │  (Every 30s)         │  │  │
│  └──────────────────────┘  │  │
│                             │  │
│  ┌──────────────────────┐  │  │
│  │  Config Watcher      │  │  │
│  │  (Every 60s)         │  │  │
│  └──────────────────────┘  │  │  HTTPS/TLS 1.3
│                             │  │
│  ┌──────────────────────┐  │  │
│  │  Metrics Collector   │  │  │
│  │  (Every 5m)          │  │  │
│  └──────────────────────┘  │  │
│                             │  │
└─────────────────────────────┘  │
                                 │
                                 ▼
                    ┌────────────────────┐
                    │    Ops-Center      │
                    │  (Cloud/Central)   │
                    └────────────────────┘
```

## Metrics Collected

### System Metrics
- CPU utilization (%)
- Memory usage (%)
- Disk usage (%)
- Network I/O (bytes)

### GPU Metrics (if available)
- GPU utilization (%)
- GPU memory used (MB)
- GPU temperature (°C)

### Service Metrics
- Docker container status
- Service health checks
- Uptime tracking

## Troubleshooting

### Agent Not Starting

```bash
# Check service status
sudo systemctl status edge-agent

# Check logs for errors
sudo journalctl -u edge-agent -n 50

# Verify credentials exist
sudo cat /etc/edge-agent/credentials.json
```

### Cannot Connect to Ops-Center

```bash
# Test connectivity
curl -v https://your-domain.com/api/health

# Check firewall
sudo ufw status
sudo iptables -L

# Verify DNS resolution
nslookup your-domain.com
```

### High CPU/Memory Usage

The edge agent is designed to be lightweight (<50MB RAM, <1% CPU). If you see high usage:

```bash
# Check what's using resources
top -p $(pidof python3)

# Restart agent
sudo systemctl restart edge-agent
```

## Security

- All communication uses TLS 1.3
- Device authentication via JWT tokens
- Credentials stored with 600 permissions
- No inbound ports required
- Systemd security hardening enabled

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CLOUD_URL=http://localhost:8000
export DEVICE_ID=test-device
export AUTH_TOKEN=test-token

# Run
python edge_agent.py
```

### Testing

```bash
# Mock registration
python edge_agent.py --register --token test-token --cloud-url http://localhost:8000
```

## License

Same as Ops-Center main project.

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/ops-center/issues
- Documentation: https://docs.your-domain.com
- Discord: https://discord.gg/your-server
