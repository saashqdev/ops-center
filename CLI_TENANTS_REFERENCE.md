# 🏢 Tenant Management CLI Commands

Complete command reference for managing multi-tenant organizations via the Ops-Center CLI.

---

## Installation

The `ops-center tenants` commands are included in the Ops-Center CLI (Epic 9.1).

```bash
# Install/update CLI
pip install -e .

# Or use the install script
./install-cli.sh

# Verify installation
ops-center tenants --help
```

---

## Command Overview

| Command | Purpose | Example |
|---------|---------|---------|
| `tenants list` | List all tenants | `ops-center tenants list --tier professional` |
| `tenants create` | Create new tenant | `ops-center tenants create --name "Acme"` |
| `tenants get` | Get tenant details | `ops-center tenants get <tenant-id> --quota` |
| `tenants update` | Update tenant | `ops-center tenants update <id> --tier enterprise` |
| `tenants delete` | Delete tenant | `ops-center tenants delete <id> --permanent` |
| `tenants stats` | Usage statistics | `ops-center tenants stats <tenant-id>` |
| `tenants quota` | Quota status | `ops-center tenants quota <tenant-id>` |
| `tenants platform-stats` | Platform overview | `ops-center tenants platform-stats` |

---

## Commands

### `ops-center tenants list`

List all tenants with filtering and pagination.

**Usage:**
```bash
ops-center tenants list [OPTIONS]
```

**Options:**
- `--tier <tier>` - Filter by subscription tier (trial, starter, professional, enterprise)
- `--active-only / --all` - Show only active tenants (default: active only)
- `--search <text>` - Search by name or subdomain
- `--page <num>` - Page number (default: 1)
- `--page-size <num>` - Results per page (default: 20)
- `-o, --output <format>` - Output format: table, json, yaml

**Examples:**

```bash
# List all tenants (table format)
ops-center tenants list

# List only professional tier tenants
ops-center tenants list --tier professional

# Search for tenants
ops-center tenants list --search "acme"

# Show all tenants including inactive
ops-center tenants list --all

# JSON output for scripting
ops-center tenants list -o json

# Pagination
ops-center tenants list --page 2 --page-size 50
```

**Output (Table):**
```
                              Tenants (Page 1, Total: 142)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ ID       ┃ Name             ┃ Subdomain  ┃ Tier         ┃ Members ┃ Status   ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ 550e8400 │ Acme Corporation │ acme       │ professional │      45 │ 🟢 Active│
│ 6ba7b810 │ Contoso Ltd      │ contoso    │ enterprise   │     128 │ 🟢 Active│
│ 7c9e6679 │ Demo Company     │ demo       │ trial        │       3 │ 🟢 Active│
└──────────┴──────────────────┴────────────┴──────────────┴─────────┴──────────┘
```

---

### `ops-center tenants create`

Create a new tenant organization with admin user.

**Usage:**
```bash
ops-center tenants create [OPTIONS]
```

**Options:**
- `--name <name>` - Organization name (required)
- `--subdomain <subdomain>` - Subdomain (required, e.g., "acme" for acme.ops-center.com)
- `--tier <tier>` - Subscription tier: trial, starter, professional, enterprise (default: trial)
- `--custom-domain <domain>` - Custom domain (optional)
- `--admin-email <email>` - Admin user email (required)
- `--admin-name <name>` - Admin user name (required)
- `--admin-password` - Admin password (prompted securely)

**Examples:**

```bash
# Create trial tenant (interactive password prompt)
ops-center tenants create \
  --name "Acme Corporation" \
  --subdomain "acme" \
  --tier trial \
  --admin-email "admin@acme.com" \
  --admin-name "John Admin"

# Create professional tenant with custom domain
ops-center tenants create \
  --name "Contoso Ltd" \
  --subdomain "contoso" \
  --tier professional \
  --custom-domain "portal.contoso.com" \
  --admin-email "admin@contoso.com" \
  --admin-name "Jane Admin"

# Create enterprise tenant
ops-center tenants create \
  --name "Enterprise Corp" \
  --subdomain "enterprise" \
  --tier enterprise \
  --admin-email "admin@enterprise.com" \
  --admin-name "Admin User"
```

**Output:**
```
╭─────────────────── Tenant Created ────────────────────╮
│ ✓ Tenant created successfully!                        │
│                                                        │
│ Organization: Acme Corporation                         │
│ ID: 550e8400-e29b-41d4-a716-446655440000              │
│ Subdomain: acme.ops-center.com                        │
│ Tier: professional                                     │
│ Admin Email: admin@acme.com                           │
│                                                        │
│ Access URL: https://acme.ops-center.com               │
╰────────────────────────────────────────────────────────╯
```

---

### `ops-center tenants get`

Get detailed information about a specific tenant.

**Usage:**
```bash
ops-center tenants get TENANT_ID [OPTIONS]
```

**Arguments:**
- `TENANT_ID` - Tenant UUID or subdomain

**Options:**
- `--quota / --no-quota` - Include quota information (default: no)
- `-o, --output <format>` - Output format: table, json, yaml

**Examples:**

```bash
# Get tenant details
ops-center tenants get 550e8400-e29b-41d4-a716-446655440000

# Get with quota information
ops-center tenants get acme --quota

# JSON output
ops-center tenants get acme -o json
```

**Output:**
```
Tenant Details

ID              550e8400-e29b-41d4-a716-446655440000
Name            Acme Corporation
Subdomain       acme
Custom Domain   Not configured
Tier            professional
Members         45
Status          🟢 Active
Created         2026-01-15T10:30:00Z

Resource Quotas

┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━┓
┃ Resource  ┃ Current ┃   Max ┃  Usage ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━┩
│ Users     │      45 │   100 │  45.0% │
│ Devices   │     234 │   500 │  46.8% │
│ Webhooks  │      12 │   100 │  12.0% │
└───────────┴─────────┴───────┴────────┘
```

---

### `ops-center tenants update`

Update tenant configuration.

**Usage:**
```bash
ops-center tenants update TENANT_ID [OPTIONS]
```

**Options:**
- `--name <name>` - Update organization name
- `--tier <tier>` - Update subscription tier
- `--subdomain <subdomain>` - Update subdomain
- `--custom-domain <domain>` - Update custom domain
- `--activate / --deactivate` - Activate or deactivate tenant

**Examples:**

```bash
# Upgrade tier
ops-center tenants update acme --tier professional

# Update subdomain
ops-center tenants update acme --subdomain acme-corp

# Set custom domain
ops-center tenants update acme --custom-domain portal.acme.com

# Deactivate tenant (soft delete)
ops-center tenants update acme --deactivate

# Reactivate tenant
ops-center tenants update acme --activate

# Update multiple fields
ops-center tenants update acme \
  --name "Acme Corporation Inc" \
  --tier enterprise \
  --custom-domain portal.acme.com
```

**Output:**
```
✓ Tenant updated successfully
  Name: Acme Corporation Inc
  Tier: enterprise
  Custom Domain: portal.acme.com
```

---

### `ops-center tenants delete`

Delete or deactivate a tenant.

**Usage:**
```bash
ops-center tenants delete TENANT_ID [OPTIONS]
```

**Options:**
- `--permanent` - Permanently delete (hard delete) all data
- `-y, --yes` - Skip confirmation prompt

**Examples:**

```bash
# Soft delete (deactivate, preserve data)
ops-center tenants delete acme

# Hard delete (permanent, cannot be undone)
ops-center tenants delete acme --permanent

# Skip confirmation
ops-center tenants delete acme --permanent -y
```

**Output (Soft Delete):**
```
This will deactivate 'Acme Corporation'
Data will be preserved and can be reactivated later.

Are you sure you want to deactivate this tenant? [y/N]: y
✓ Tenant deactivated
Reactivate with: ops-center tenants update 550e8400 --activate
```

**Output (Hard Delete):**
```
⚠️  WARNING: This will PERMANENTLY delete all data for 'Acme Corporation'
This action CANNOT be undone!

Are you sure you want to PERMANENTLY DELETE this tenant? [y/N]: y
✓ Tenant permanently deleted
```

---

### `ops-center tenants stats`

Get usage statistics for a tenant.

**Usage:**
```bash
ops-center tenants stats TENANT_ID
```

**Examples:**

```bash
# Get tenant statistics
ops-center tenants stats acme

# JSON output for monitoring
ops-center tenants stats acme -o json
```

**Output:**
```
Tenant Statistics

Total Users          45
Total Devices        234
Total Webhooks       12
Storage Used         12.45 GB
API Calls (30d)      125,890
Active Users (7d)    38
```

---

### `ops-center tenants quota`

Get current quota status for a tenant.

**Usage:**
```bash
ops-center tenants quota TENANT_ID
```

**Examples:**

```bash
# Check quota status
ops-center tenants quota acme

# JSON output
ops-center tenants quota acme -o json
```

**Output:**
```
Quota Status

┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Resource  ┃ Current ┃   Maximum ┃ Available ┃  Usage ┃ Status ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ Users     │      45 │       100 │        55 │  45.0% │   🟢   │
│ Devices   │     234 │       500 │       266 │  46.8% │   🟢   │
│ Webhooks  │      12 │       100 │        88 │  12.0% │   🟢   │
│ Api Keys  │      28 │        50 │        22 │  56.0% │   🟢   │
│ Alerts    │     456 │       500 │        44 │  91.2% │   🟡   │
└───────────┴─────────┴───────────┴───────────┴────────┴────────┘

Status: 🟢 OK  🟡 Warning (>80%)  🔴 At Limit  ⚪ Unlimited
```

---

### `ops-center tenants platform-stats`

Get platform-wide statistics across all tenants.

**Usage:**
```bash
ops-center tenants platform-stats
```

**Examples:**

```bash
# View platform overview
ops-center tenants platform-stats

# JSON output for dashboards
ops-center tenants platform-stats -o json
```

**Output:**
```
Platform Statistics

Total Tenants         142
Active Tenants        138
Total Users          3,589
Total Devices       12,467
Total Webhooks         856
Growth (30d)           18

Tier Distribution

┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Tier         ┃ Count ┃ Percentage ┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ Trial        │    65 │      45.8% │
│ Starter      │    48 │      33.8% │
│ Professional │    24 │      16.9% │
│ Enterprise   │     5 │       3.5% │
└──────────────┴───────┴────────────┘
```

---

## Global Options

All tenant commands support global CLI options:

```bash
ops-center [GLOBAL OPTIONS] tenants COMMAND [OPTIONS]
```

**Global Options:**
- `--config, -c <path>` - Path to config file (default: ~/.ops-center/config.yaml)
- `--api-url <url>` - Override API URL from config
- `--api-key <key>` - Override API key from config
- `--output, -o <format>` - Output format: table, json, yaml (default: table)
- `--version` - Show CLI version
- `--help` - Show help message

**Examples:**

```bash
# Use custom config file
ops-center -c ~/custom-config.yaml tenants list

# Override API URL
ops-center --api-url https://api.myops.com tenants list

# JSON output
ops-center -o json tenants list

# Combine options
ops-center --api-url https://api.myops.com -o json tenants stats acme
```

---

## Output Formats

### Table (Default)

Human-readable formatted tables with colors and icons.

```bash
ops-center tenants list
```

### JSON

Machine-readable JSON for scripting and automation.

```bash
ops-center tenants list -o json
```

**Output:**
```json
{
  "tenants": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Acme Corporation",
      "subdomain": "acme",
      "subscription_tier": "professional",
      "member_count": 45,
      "is_active": true
    }
  ],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```

### YAML

Human-readable structured format.

```bash
ops-center tenants list -o yaml
```

**Output:**
```yaml
tenants:
  - id: 550e8400-e29b-41d4-a716-446655440000
    name: Acme Corporation
    subdomain: acme
    subscription_tier: professional
    member_count: 45
    is_active: true
total: 142
page: 1
page_size: 20
```

---

## Scripting Examples

### Create Multiple Tenants

```bash
#!/bin/bash
# create-tenants.sh

TENANTS=(
  "acme,Acme Corporation,professional,admin@acme.com"
  "contoso,Contoso Ltd,enterprise,admin@contoso.com"
  "demo,Demo Company,trial,admin@demo.com"
)

for tenant in "${TENANTS[@]}"; do
  IFS=',' read -r subdomain name tier email <<< "$tenant"
  
  echo "Creating tenant: $name"
  
  ops-center tenants create \
    --name "$name" \
    --subdomain "$subdomain" \
    --tier "$tier" \
    --admin-email "$email" \
    --admin-name "Admin User" \
    --admin-password "TempPassword123!" \
    -o json
done
```

### Monitor Quota Usage

```bash
#!/bin/bash
# check-quotas.sh

# Get all tenants
TENANTS=$(ops-center tenants list -o json | jq -r '.tenants[].id')

echo "Checking quota for all tenants..."

for tenant_id in $TENANTS; do
  # Get quota status
  quota=$(ops-center tenants quota "$tenant_id" -o json)
  
  # Check for tenants exceeding 80%
  exceeding=$(echo "$quota" | jq -r 'to_entries[] | select(.value.percentage_used > 80) | "\(.key): \(.value.percentage_used)%"')
  
  if [ -n "$exceeding" ]; then
    tenant_name=$(ops-center tenants get "$tenant_id" -o json | jq -r '.name')
    echo "⚠️  $tenant_name ($tenant_id):"
    echo "$exceeding"
  fi
done
```

### Export Platform Statistics

```bash
#!/bin/bash
# export-stats.sh

DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="platform-stats-$DATE.json"

# Get platform stats
ops-center tenants platform-stats -o json > "$OUTPUT_FILE"

echo "Platform statistics exported to: $OUTPUT_FILE"

# Upload to S3 (optional)
# aws s3 cp "$OUTPUT_FILE" "s3://my-bucket/stats/"
```

### Bulk Tier Upgrades

```bash
#!/bin/bash
# upgrade-trials.sh

# Find trial tenants older than 30 days
TRIAL_TENANTS=$(ops-center tenants list --tier trial -o json | \
  jq -r '.tenants[] | select(.created_at < (now - 2592000)) | .id')

for tenant_id in $TRIAL_TENANTS; do
  echo "Upgrading tenant $tenant_id to starter tier"
  
  ops-center tenants update "$tenant_id" \
    --tier starter \
    -o json
done
```

---

## Environment Variables

Configure CLI behavior with environment variables:

```bash
# API configuration
export OPS_CENTER_API_URL="https://api.ops-center.com"
export OPS_CENTER_API_KEY="your-api-key"

# Config file location
export OPS_CENTER_CONFIG="~/.ops-center/config.yaml"

# Use in commands
ops-center tenants list
```

---

## Integration with Other Tools

### Prometheus Metrics Export

```bash
#!/bin/bash
# prometheus-exporter.sh

while true; do
  # Get platform stats
  stats=$(ops-center tenants platform-stats -o json)
  
  # Export metrics
  echo "# HELP ops_center_total_tenants Total number of tenants"
  echo "# TYPE ops_center_total_tenants gauge"
  echo "ops_center_total_tenants $(echo $stats | jq '.total_tenants')"
  
  echo "# HELP ops_center_active_tenants Active tenants"
  echo "# TYPE ops_center_active_tenants gauge"
  echo "ops_center_active_tenants $(echo $stats | jq '.active_tenants')"
  
  sleep 60
done > /var/lib/prometheus/node_exporter/ops_center.prom
```

### Grafana Dashboard Data

```bash
# Get time-series data for dashboard
ops-center tenants platform-stats -o json | \
  jq '{
    total: .total_tenants,
    active: .active_tenants,
    growth: .growth_last_30_days,
    tiers: .tier_distribution
  }' | curl -X POST http://grafana:3000/api/datasources/1 -d @-
```

---

## Troubleshooting

### Authentication Errors

```bash
# Verify API key
ops-center config

# Test connection
ops-center server status

# Re-initialize config
ops-center init
```

### Permission Errors

Tenant commands require admin privileges:

```bash
# Ensure you're using an admin API key
# Generate at: https://ops-center.com/admin/api-keys
```

### Output Parsing Issues

```bash
# Use jq for JSON parsing
ops-center tenants list -o json | jq '.tenants[0].name'

# Use yq for YAML
ops-center tenants list -o yaml | yq '.tenants[0].name'
```

---

## Best Practices

1. **Use JSON output for scripts**: `-o json` for reliable parsing
2. **Store API keys securely**: Use environment variables or config file
3. **Implement error handling**: Check exit codes in scripts
4. **Monitor quota usage**: Set up automated alerts
5. **Test with `--yes` cautiously**: Only use `-y` in trusted automated scripts
6. **Backup before bulk operations**: Export data before mass changes
7. **Use pagination**: Don't fetch all tenants at once in large deployments

---

## Related Commands

- `ops-center orgs` - Legacy organization management
- `ops-center users` - User management within tenants
- `ops-center devices` - Device management per tenant
- `ops-center webhooks` - Webhook management per tenant

---

## Documentation

- **CLI Overview**: [README-CLI.md](README-CLI.md)
- **Multi-Tenant Architecture**: [EPIC_10_MULTITENANT_COMPLETE.md](EPIC_10_MULTITENANT_COMPLETE.md)
- **API Documentation**: `https://ops-center.com/docs`

---

**Questions?** Run `ops-center tenants --help` or open an issue on GitHub.
