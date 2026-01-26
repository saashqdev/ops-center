# Ops-Center CLI

Command-line interface for managing your Ops-Center infrastructure from the terminal.

## Features

- 🖥️ **Server Management** - Check health, view logs, monitor metrics
- 👥 **User Management** - Create, update, delete users; view usage stats
- 🏢 **Organization Management** - Manage organizations and members
- 📡 **Edge Device Management** - Register, monitor, and control edge devices
- 🔔 **Webhook Management** - Configure and test webhooks
- 📊 **Rich Output** - Beautiful tables and formatted output
- 🔧 **Scriptable** - JSON/YAML output for automation
- ⚡ **Fast** - Optimized API calls and caching

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/ops-center.git
cd ops-center

# Install CLI
chmod +x install-cli.sh
./install-cli.sh

# Or install manually
pip install .
```

### Using pip (when published)

```bash
pip install ops-center-cli
```

## Quick Start

### 1. Initialize Configuration

```bash
ops-center init
```

This will prompt you for:
- API URL (e.g., `http://localhost:8084`)
- API key (generate at `/admin/api-keys`)
- Default organization ID (optional)

Configuration is saved to `~/.ops-center/config.yaml`

### 2. Check Server Status

```bash
ops-center server status
```

### 3. List Users

```bash
ops-center users list
```

## Usage

### Global Options

```bash
ops-center --help
ops-center --version
ops-center --output json    # Output as JSON
ops-center --api-url <url>  # Override API URL
ops-center --api-key <key>  # Override API key
```

### Server Commands

```bash
# Check server health
ops-center server status

# View server information
ops-center server info

# View server metrics
ops-center server metrics

# View server logs (admin only)
ops-center server logs
ops-center server logs --level ERROR
ops-center server logs --lines 100
```

### User Commands

```bash
# List all users
ops-center users list
ops-center users list --tier professional
ops-center users list --limit 100

# Get user details
ops-center users get user@example.com

# Create a new user
ops-center users create

# Update user
ops-center users update user@example.com --tier professional
ops-center users update user@example.com --active
ops-center users update user@example.com --inactive

# Delete user
ops-center users delete user@example.com

# View user usage statistics
ops-center users usage user@example.com
```

### Organization Commands

```bash
# List organizations
ops-center orgs list

# Get organization details
ops-center orgs get <org-id>

# Create organization
ops-center orgs create --name "Acme Corp" --plan professional

# Update organization
ops-center orgs update <org-id> --name "New Name"
ops-center orgs update <org-id> --plan enterprise

# Delete organization
ops-center orgs delete <org-id>

# List organization members
ops-center orgs members <org-id>
```

### Edge Device Commands

```bash
# List devices
ops-center devices list
ops-center devices list --org <org-id>
ops-center devices list --status online

# Get device details
ops-center devices get <device-id>

# Register new device
ops-center devices register
ops-center devices register --name "Sensor-01" --hardware-id "AA:BB:CC:DD:EE:FF"

# Update device
ops-center devices update <device-id> --name "New Name"
ops-center devices update <device-id> --firmware "2.0.0"

# Delete device
ops-center devices delete <device-id>

# View device logs
ops-center devices logs <device-id>
ops-center devices logs <device-id> --lines 50

# View device metrics
ops-center devices metrics <device-id>
```

### Webhook Commands

```bash
# List webhooks
ops-center webhooks list
ops-center webhooks list --active
ops-center webhooks list --org <org-id>

# Get webhook details
ops-center webhooks get <webhook-id>

# Create webhook
ops-center webhooks create
ops-center webhooks create \
  --url "https://webhook.site/your-url" \
  --events "user.created,device.online" \
  --description "My webhook"

# Update webhook
ops-center webhooks update <webhook-id> --active
ops-center webhooks update <webhook-id> --url "https://new-url.com"
ops-center webhooks update <webhook-id> --events "user.created,user.login"

# Delete webhook
ops-center webhooks delete <webhook-id>

# Test webhook
ops-center webhooks test <webhook-id>

# View webhook deliveries
ops-center webhooks deliveries <webhook-id>
ops-center webhooks deliveries <webhook-id> --status failed
ops-center webhooks deliveries <webhook-id> --limit 50

# List available events
ops-center webhooks events
```

### Log Commands

```bash
# View server logs
ops-center logs server --lines 100
ops-center logs server --level ERROR

# View device logs
ops-center logs device <device-id> --lines 50
```

## Output Formats

The CLI supports multiple output formats for scripting and automation:

### Table (default)
```bash
ops-center users list
```

### JSON
```bash
ops-center users list --output json
ops-center users list -o json
```

### YAML
```bash
ops-center users list --output yaml
ops-center users list -o yaml
```

## Configuration

### Config File Location

Default: `~/.ops-center/config.yaml`

Override with: `--config /path/to/config.yaml`

### Config File Format

```yaml
api_url: http://localhost:8084
api_key: your-api-key-here
default_org: org-id-optional
output_format: table
```

### View Current Config

```bash
ops-center config
```

### Environment Variables

Override config with environment variables:

```bash
export OPS_CENTER_API_URL=http://localhost:8084
export OPS_CENTER_API_KEY=your-api-key
export OPS_CENTER_CONFIG=/path/to/config.yaml

ops-center server status
```

## Advanced Usage

### Scripting Examples

**Create users from CSV:**
```bash
#!/bin/bash
while IFS=, read -r email name tier; do
  echo "Creating user: $email"
  ops-center users create \
    --email "$email" \
    --name "$name" \
    --tier "$tier" \
    --password "TempPass123!"
done < users.csv
```

**Export all users to JSON:**
```bash
ops-center users list --output json > users.json
```

**Monitor device status:**
```bash
#!/bin/bash
while true; do
  clear
  ops-center devices list --status offline
  sleep 30
done
```

**Webhook delivery monitoring:**
```bash
# Get failed deliveries in last hour
ops-center webhooks deliveries <webhook-id> \
  --status failed \
  --output json | \
  jq '.[] | select(.created_at > (now - 3600))'
```

### CI/CD Integration

```yaml
# .github/workflows/deploy.yml
- name: Check Ops-Center health
  run: |
    ops-center server status
    
- name: Create deployment webhook
  run: |
    ops-center webhooks create \
      --url "${{ secrets.WEBHOOK_URL }}" \
      --events "deployment.started,deployment.completed" \
      --description "GitHub Actions deployment webhook"
```

## Troubleshooting

### Connection Errors

```bash
# Test connection
ops-center server status

# Check config
ops-center config

# Use verbose mode (add DEBUG logging)
ops-center --api-url http://localhost:8084 server status
```

### Authentication Issues

```bash
# Re-initialize config
ops-center init

# Or set via environment
export OPS_CENTER_API_KEY=your-new-key
ops-center server status
```

### Command Not Found

```bash
# Check installation
which ops-center

# Reinstall
pip install --force-reinstall ops-center-cli

# Or add to PATH
export PATH=$PATH:~/.local/bin
```

## Development

### Setup Development Environment

```bash
# Clone repo
git clone https://github.com/yourusername/ops-center.git
cd ops-center

# Install in editable mode with dev dependencies
./install-cli.sh --dev

# Or manually
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
pytest tests/ --cov=cli
```

### Code Quality

```bash
# Format code
black cli/

# Lint
flake8 cli/

# Type checking
mypy cli/
```

## Requirements

- Python 3.8 or higher
- Ops-Center API server running and accessible
- API key with appropriate permissions

## Dependencies

- **click** - Command-line interface framework
- **rich** - Beautiful terminal output
- **requests** - HTTP client
- **PyYAML** - YAML parsing

## Security

- API keys are stored with `0600` permissions (owner read/write only)
- Config file is created in user's home directory
- Sensitive data (passwords, keys) masked in output
- HTTPS recommended for production API connections

## License

MIT License - see LICENSE file for details

## Support

- Documentation: https://ops-center.readthedocs.io
- Issues: https://github.com/yourusername/ops-center/issues
- Discussions: https://github.com/yourusername/ops-center/discussions

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Changelog

See CHANGELOG.md for version history.
