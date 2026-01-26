# Epic 11: Plugin/Extension Architecture - System Specification

**Epic Owner:** Platform Architecture Team  
**Status:** 🚧 In Progress  
**Priority:** High  
**Timeline:** 3-4 weeks  
**Version:** 1.0  
**Created:** January 26, 2026

---

## 📋 Executive Summary

Epic 11 implements a comprehensive **Plugin/Extension Architecture** that transforms Ops-Center into an extensible platform. This system enables developers to build, distribute, and monetize plugins that add new capabilities to Ops-Center without modifying the core codebase.

### Key Objectives

- ✅ **Plugin Lifecycle Management**: Install, enable, disable, update, uninstall
- ✅ **Plugin Marketplace**: Browse, search, and install community plugins
- ✅ **Plugin SDK**: Developer-friendly toolkit for building plugins
- ✅ **Security Sandbox**: Isolated execution with permission model
- ✅ **Plugin Registry**: Central repository for plugin metadata
- ✅ **Hook System**: Event-driven plugin integration points
- ✅ **Multi-Tenant Support**: Per-tenant plugin enablement
- ✅ **Version Management**: Semantic versioning and compatibility checks

### Business Value

| Benefit | Impact |
|---------|--------|
| **Extensibility** | Add features without core code changes |
| **Community Growth** | Third-party developers extend platform |
| **Revenue Stream** | Marketplace fees, premium plugins |
| **Customization** | Tenants can tailor Ops-Center to needs |
| **Innovation** | Rapid feature delivery via plugins |
| **Integration** | Connect to any third-party service |

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Ops-Center Core Platform                       │
│                                                                      │
│  ┌──────────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │  Plugin Runtime  │  │  Hook System  │  │  Security Sandbox  │  │
│  │   - Loader       │  │  - Events     │  │  - Permissions     │  │
│  │   - Lifecycle    │  │  - Filters    │  │  - Resource Limits │  │
│  │   - Isolation    │  │  - Actions    │  │  - API Rate Limit  │  │
│  └──────────────────┘  └───────────────┘  └────────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │ Plugin Registry  │  │  API Gateway  │  │  Storage Manager   │  │
│  │  - Metadata      │  │  - REST API   │  │  - Plugin Data     │  │
│  │  - Versions      │  │  - GraphQL    │  │  - Static Assets   │  │
│  │  - Dependencies  │  │  - WebSocket  │  │  - File Uploads    │  │
│  └──────────────────┘  └───────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
        ┌────────▼────────┐ ┌────▼──────┐ ┌──────▼────────┐
        │  Python Plugin  │ │  JS Plugin│ │  Docker Plugin│
        │   (Backend)     │ │ (Frontend)│ │  (Container)  │
        │                 │ │           │ │               │
        │ - FastAPI       │ │ - React   │ │ - Any Stack   │
        │ - Hooks         │ │ - Hooks   │ │ - Compose     │
        │ - API Access    │ │ - UI Slots│ │ - Networking  │
        └─────────────────┘ └───────────┘ └───────────────┘
```

### Plugin Types

| Type | Language | Use Case | Example |
|------|----------|----------|---------|
| **Backend Plugin** | Python | API extensions, data processing | Custom analytics, ML models |
| **Frontend Plugin** | JavaScript/React | UI components, dashboards | Custom widgets, themes |
| **Hybrid Plugin** | Python + JS | Full-stack features | Complete modules |
| **Container Plugin** | Any (Docker) | Standalone services | Monitoring tools, databases |
| **Theme Plugin** | CSS/SCSS | Visual customization | Dark mode, branding |

---

## 💾 Database Schema

### Plugin Registry Tables

```sql
-- Core plugin metadata
CREATE TABLE plugins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,  -- URL-safe identifier
    name VARCHAR(200) NOT NULL,
    description TEXT,
    author VARCHAR(200) NOT NULL,
    author_email VARCHAR(255),
    author_url VARCHAR(500),
    icon_url VARCHAR(500),
    category VARCHAR(50) NOT NULL,  -- ai, monitoring, integration, analytics, etc.
    type VARCHAR(50) NOT NULL,  -- backend, frontend, hybrid, container, theme
    license VARCHAR(100),  -- MIT, Apache-2.0, GPL-3.0, Commercial
    homepage_url VARCHAR(500),
    repository_url VARCHAR(500),
    documentation_url VARCHAR(500),
    is_official BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_published BOOLEAN DEFAULT FALSE,
    min_platform_version VARCHAR(20),  -- Minimum Ops-Center version
    max_platform_version VARCHAR(20),  -- Maximum compatible version
    total_installs INTEGER DEFAULT 0,
    total_downloads INTEGER DEFAULT 0,
    rating_average DECIMAL(3,2),  -- 0.00 to 5.00
    rating_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    
    -- Metadata
    tags TEXT[],  -- Array of tags for search
    keywords TEXT[],  -- SEO keywords
    screenshots TEXT[],  -- Array of screenshot URLs
    
    -- Pricing
    is_free BOOLEAN DEFAULT TRUE,
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),
    price_lifetime DECIMAL(10,2),
    
    CONSTRAINT valid_slug CHECK (slug ~ '^[a-z0-9-]+$'),
    CONSTRAINT valid_rating CHECK (rating_average >= 0 AND rating_average <= 5)
);

-- Plugin versions
CREATE TABLE plugin_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,  -- Semantic version: 1.2.3
    changelog TEXT,
    download_url VARCHAR(500) NOT NULL,
    file_size BIGINT,  -- Bytes
    checksum VARCHAR(64),  -- SHA-256 hash
    is_stable BOOLEAN DEFAULT TRUE,
    is_deprecated BOOLEAN DEFAULT FALSE,
    
    -- Compatibility
    min_platform_version VARCHAR(20),
    max_platform_version VARCHAR(20),
    python_version VARCHAR(20),  -- e.g., ">=3.9,<4.0"
    node_version VARCHAR(20),
    
    -- Requirements
    python_dependencies JSONB,  -- {"requests": ">=2.28.0", "pydantic": "^2.0"}
    npm_dependencies JSONB,
    docker_image VARCHAR(500),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    downloads INTEGER DEFAULT 0,
    
    UNIQUE(plugin_id, version)
);

-- Plugin installations per tenant
CREATE TABLE plugin_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES plugin_versions(id) ON DELETE CASCADE,
    
    status VARCHAR(50) NOT NULL DEFAULT 'installed',  -- installed, enabled, disabled, error, updating
    enabled BOOLEAN DEFAULT TRUE,
    auto_update BOOLEAN DEFAULT TRUE,
    
    -- Configuration
    config JSONB DEFAULT '{}'::jsonb,
    permissions JSONB DEFAULT '[]'::jsonb,  -- Granted permissions
    
    -- Lifecycle
    installed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    installed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_enabled_at TIMESTAMPTZ,
    last_disabled_at TIMESTAMPTZ,
    
    -- Health
    error_message TEXT,
    last_health_check TIMESTAMPTZ,
    health_status VARCHAR(50),  -- healthy, degraded, unhealthy
    
    UNIQUE(tenant_id, plugin_id)
);

-- Plugin dependencies
CREATE TABLE plugin_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    depends_on_plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    version_constraint VARCHAR(100),  -- e.g., ">=1.0.0,<2.0.0"
    is_optional BOOLEAN DEFAULT FALSE,
    
    UNIQUE(plugin_id, depends_on_plugin_id)
);

-- Plugin permissions
CREATE TABLE plugin_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    permission_type VARCHAR(100) NOT NULL,  -- api:read, api:write, storage:read, etc.
    description TEXT NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    
    UNIQUE(plugin_id, permission_type)
);

-- Plugin hooks (event registration)
CREATE TABLE plugin_hooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    hook_name VARCHAR(200) NOT NULL,  -- e.g., "device.created", "user.login"
    handler_function VARCHAR(200) NOT NULL,  -- Python function path
    priority INTEGER DEFAULT 10,  -- Lower runs first
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(plugin_id, hook_name, handler_function)
);

-- Plugin reviews
CREATE TABLE plugin_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200),
    review_text TEXT,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(plugin_id, user_id)
);

-- Plugin analytics
CREATE TABLE plugin_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,  -- download, install, uninstall, enable, disable, error
    event_data JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT
);

-- Indexes for performance
CREATE INDEX idx_plugins_slug ON plugins(slug);
CREATE INDEX idx_plugins_category ON plugins(category);
CREATE INDEX idx_plugins_type ON plugins(type);
CREATE INDEX idx_plugins_published ON plugins(is_published, is_official, is_verified);
CREATE INDEX idx_plugins_rating ON plugins(rating_average DESC, rating_count DESC);
CREATE INDEX idx_plugin_versions_plugin_id ON plugin_versions(plugin_id, version);
CREATE INDEX idx_plugin_installations_tenant ON plugin_installations(tenant_id, enabled);
CREATE INDEX idx_plugin_installations_status ON plugin_installations(status, health_status);
CREATE INDEX idx_plugin_analytics_plugin ON plugin_analytics(plugin_id, timestamp DESC);
CREATE INDEX idx_plugin_analytics_tenant ON plugin_analytics(tenant_id, event_type, timestamp DESC);

-- Full-text search
CREATE INDEX idx_plugins_search ON plugins USING gin(
    to_tsvector('english', name || ' ' || description || ' ' || COALESCE(array_to_string(tags, ' '), ''))
);
```

---

## 🔌 Plugin API Endpoints

### Marketplace API

```
GET    /api/v1/plugins/marketplace              # Browse marketplace
GET    /api/v1/plugins/marketplace/{slug}       # Plugin details
GET    /api/v1/plugins/marketplace/{slug}/versions  # Available versions
POST   /api/v1/plugins/marketplace/{slug}/reviews   # Submit review
GET    /api/v1/plugins/marketplace/categories   # List categories
GET    /api/v1/plugins/marketplace/featured     # Featured plugins
GET    /api/v1/plugins/marketplace/trending     # Trending plugins
GET    /api/v1/plugins/marketplace/search       # Search plugins
```

### Installation API

```
GET    /api/v1/plugins/installed                # List installed plugins
POST   /api/v1/plugins/install                  # Install plugin
POST   /api/v1/plugins/{id}/uninstall           # Uninstall plugin
POST   /api/v1/plugins/{id}/enable              # Enable plugin
POST   /api/v1/plugins/{id}/disable             # Disable plugin
POST   /api/v1/plugins/{id}/update              # Update plugin
PUT    /api/v1/plugins/{id}/config              # Update config
GET    /api/v1/plugins/{id}/health              # Health check
GET    /api/v1/plugins/{id}/logs                # Plugin logs
```

### Developer API

```
POST   /api/v1/plugins/register                 # Register new plugin
PUT    /api/v1/plugins/{id}                     # Update plugin
POST   /api/v1/plugins/{id}/versions            # Upload new version
DELETE /api/v1/plugins/{id}                     # Delete plugin
GET    /api/v1/plugins/{id}/analytics           # Plugin analytics
POST   /api/v1/plugins/{id}/publish             # Publish to marketplace
POST   /api/v1/plugins/{id}/verify              # Request verification
```

### Admin API

```
GET    /api/v1/admin/plugins                    # All plugins (admin view)
PUT    /api/v1/admin/plugins/{id}/verify        # Verify plugin
PUT    /api/v1/admin/plugins/{id}/feature       # Mark as featured
DELETE /api/v1/admin/plugins/{id}/ban           # Ban malicious plugin
GET    /api/v1/admin/plugins/analytics          # Platform analytics
GET    /api/v1/admin/plugins/pending-review     # Plugins pending review
```

---

## 🛡️ Security Model

### Permission System

Plugins must declare required permissions in `plugin.yaml`:

```yaml
permissions:
  - api:devices:read       # Read device data
  - api:devices:write      # Modify devices
  - api:users:read         # Read user data (sensitive)
  - storage:read           # Read files
  - storage:write          # Write files
  - network:outbound       # Make external HTTP requests
  - cron:schedule          # Schedule background jobs
  - hooks:device.created   # Listen to device creation events
```

### Permission Categories

| Category | Description | Risk Level |
|----------|-------------|------------|
| `api:*:read` | Read data via API | Low |
| `api:*:write` | Modify data via API | Medium |
| `api:*:delete` | Delete data via API | High |
| `storage:*` | File system access | Medium |
| `network:*` | External network access | Medium |
| `admin:*` | Administrative operations | Critical |
| `tenant:*` | Cross-tenant access | Critical |

### Sandbox Restrictions

```python
# Resource Limits per Plugin
PLUGIN_LIMITS = {
    "memory": "512MB",           # Maximum RAM usage
    "cpu": "0.5",                # CPU cores (0.5 = 50%)
    "disk": "1GB",               # Disk storage
    "network_rate": "10MB/s",    # Network bandwidth
    "api_calls": 1000,           # API calls per hour
    "cron_jobs": 5,              # Max scheduled jobs
    "http_timeout": 30,          # External HTTP timeout (seconds)
    "execution_timeout": 300,    # Max execution time (seconds)
}
```

### Code Signing

All plugins must be signed with developer's private key:

```bash
# Sign plugin
ops-center plugin sign my-plugin-1.0.0.zip --key ~/.ops-center/dev-key.pem

# Verify signature
ops-center plugin verify my-plugin-1.0.0.zip --public-key https://marketplace/keys/dev123.pub
```

---

## 📦 Plugin Structure

### Directory Layout

```
my-awesome-plugin/
├── plugin.yaml                 # Plugin manifest (REQUIRED)
├── README.md                   # Documentation
├── LICENSE                     # License file
├── CHANGELOG.md               # Version history
│
├── backend/                   # Python backend code
│   ├── __init__.py
│   ├── main.py               # Entry point
│   ├── hooks.py              # Hook handlers
│   ├── api.py                # API endpoints
│   ├── models.py             # Pydantic models
│   └── requirements.txt      # Python dependencies
│
├── frontend/                  # React frontend code
│   ├── package.json
│   ├── src/
│   │   ├── index.tsx         # Entry point
│   │   ├── components/       # React components
│   │   ├── hooks/            # React hooks
│   │   └── styles/           # CSS/SCSS
│   └── public/
│       └── icon.svg          # Plugin icon
│
├── docker/                    # Container-based plugins
│   ├── docker-compose.yml
│   └── Dockerfile
│
├── migrations/                # Database migrations
│   ├── 001_initial.sql
│   └── 002_add_indexes.sql
│
├── assets/                    # Static assets
│   ├── screenshots/
│   └── docs/
│
└── tests/                     # Unit tests
    ├── test_backend.py
    └── test_frontend.test.tsx
```

### Plugin Manifest (`plugin.yaml`)

```yaml
# Required fields
id: my-awesome-plugin
name: My Awesome Plugin
version: 1.2.3
description: A plugin that does awesome things
author: John Doe
author_email: john@example.com
license: MIT

# Plugin type
type: hybrid  # backend | frontend | hybrid | container | theme

# Compatibility
min_platform_version: "2.5.0"
max_platform_version: "3.0.0"
python_version: ">=3.9,<4.0"
node_version: ">=18.0.0"

# Category
category: ai  # ai, monitoring, integration, analytics, automation, security, etc.

# Tags for search
tags:
  - machine-learning
  - predictions
  - analytics

# Entry points
entry_points:
  backend: backend/main.py:PluginApp
  frontend: frontend/src/index.tsx
  cli: backend/cli.py:cli_app

# Dependencies
dependencies:
  plugins:
    - slug: auth-plugin
      version: ">=1.0.0"
  python:
    - requests>=2.28.0
    - pydantic>=2.0.0
    - scikit-learn>=1.0.0
  npm:
    - react: "^18.0.0"
    - axios: "^1.0.0"

# Permissions
permissions:
  - api:devices:read
  - api:devices:write
  - storage:write
  - network:outbound
  - cron:schedule

# Hooks (event listeners)
hooks:
  - name: device.created
    handler: backend.hooks:on_device_created
    priority: 10
  - name: user.login
    handler: backend.hooks:on_user_login
    priority: 5

# API Routes
api_routes:
  - path: /plugins/my-plugin/predict
    method: POST
    handler: backend.api:predict_endpoint
    auth_required: true
  - path: /plugins/my-plugin/status
    method: GET
    handler: backend.api:status_endpoint

# Frontend UI Slots (where plugin renders)
ui_slots:
  - dashboard-widget      # Main dashboard
  - device-detail-tab     # Device details page
  - settings-page         # Settings menu

# Configuration schema
config_schema:
  type: object
  properties:
    api_key:
      type: string
      description: External API key
      required: true
      sensitive: true
    threshold:
      type: number
      description: Prediction threshold
      default: 0.85
      min: 0
      max: 1
    enabled_features:
      type: array
      items:
        type: string
      default: ["feature1", "feature2"]

# Resource limits
resources:
  memory: 256MB
  cpu: 0.25
  disk: 500MB
  network_rate: 5MB/s

# Database migrations
migrations:
  - migrations/001_initial.sql
  - migrations/002_add_indexes.sql

# Cron schedules
cron:
  - name: daily-cleanup
    schedule: "0 0 * * *"  # Midnight daily
    handler: backend.jobs:cleanup_old_data
  - name: hourly-sync
    schedule: "0 * * * *"  # Every hour
    handler: backend.jobs:sync_external_data

# External services
external_services:
  - name: prediction-api
    url: https://api.example.com/ml
    auth: api_key
  - name: webhook-receiver
    url: ${WEBHOOK_URL}  # Environment variable

# Pricing (optional)
pricing:
  free: false
  monthly: 29.99
  yearly: 299.99
  trial_days: 14

# Links
homepage: https://github.com/user/my-plugin
repository: https://github.com/user/my-plugin
documentation: https://docs.example.com
support: https://support.example.com
```

---

## 🔧 Plugin SDK

### Python SDK

```python
from ops_center_sdk import Plugin, Hook, APIRoute, ConfigField

# Define plugin
plugin = Plugin(
    id="my-plugin",
    name="My Plugin",
    version="1.0.0"
)

# Register hook
@plugin.hook("device.created")
async def on_device_created(device_id: str, device_data: dict):
    """Called when a device is created"""
    print(f"New device: {device_id}")
    
    # Access plugin config
    threshold = plugin.config.get("threshold", 0.5)
    
    # Access Ops-Center APIs
    user = await plugin.api.users.get(device_data["user_id"])
    
    # Store plugin data
    await plugin.storage.set(f"device:{device_id}:score", 0.95)
    
    # Schedule background job
    await plugin.scheduler.run_at(
        datetime.now() + timedelta(hours=1),
        "check_device_health",
        device_id=device_id
    )
    
    return {"processed": True}

# Add API route
@plugin.route("/predict", methods=["POST"])
async def predict_endpoint(request: dict):
    """Custom API endpoint"""
    data = request["body"]
    
    # ML prediction logic
    result = await run_prediction(data)
    
    # Emit custom event
    await plugin.emit("prediction.completed", {
        "result": result,
        "confidence": 0.92
    })
    
    return {"prediction": result, "confidence": 0.92}

# Configuration schema
plugin.config_schema = {
    "api_key": ConfigField(
        type="string",
        required=True,
        sensitive=True,
        description="External API key"
    ),
    "threshold": ConfigField(
        type="number",
        default=0.85,
        min=0,
        max=1
    )
}

# Plugin lifecycle hooks
@plugin.on_install
async def on_install():
    """Run once when plugin is installed"""
    await plugin.db.execute("CREATE TABLE IF NOT EXISTS my_plugin_data (...)")

@plugin.on_enable
async def on_enable():
    """Run when plugin is enabled"""
    await plugin.logger.info("Plugin enabled")

@plugin.on_disable
async def on_disable():
    """Run when plugin is disabled"""
    await plugin.scheduler.cancel_all()

@plugin.on_uninstall
async def on_uninstall():
    """Run when plugin is uninstalled"""
    await plugin.db.execute("DROP TABLE my_plugin_data")

# Export plugin
app = plugin.create_app()
```

### JavaScript/React SDK

```typescript
import { Plugin, usePluginAPI, PluginComponent } from '@ops-center/plugin-sdk';

// Create plugin
const plugin = new Plugin({
  id: 'my-plugin',
  name: 'My Plugin',
  version: '1.0.0'
});

// React component for dashboard widget
export const DashboardWidget: PluginComponent = () => {
  const { config, api } = usePluginAPI();
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    // Fetch data from Ops-Center API
    api.devices.list().then(setDevices);
  }, []);

  return (
    <div className="plugin-widget">
      <h3>My Plugin Dashboard</h3>
      <DeviceList devices={devices} />
    </div>
  );
};

// Register component in UI slot
plugin.registerComponent('dashboard-widget', DashboardWidget);

// Listen to events
plugin.on('device.created', (device) => {
  console.log('New device:', device);
  // Update UI
});

// Add settings page
export const SettingsPage: PluginComponent = () => {
  const { config, updateConfig } = usePluginAPI();

  const handleSave = async (newConfig) => {
    await updateConfig(newConfig);
  };

  return (
    <PluginSettings onSave={handleSave}>
      <TextField
        label="API Key"
        value={config.api_key}
        type="password"
      />
      <Slider
        label="Threshold"
        value={config.threshold}
        min={0}
        max={1}
        step={0.01}
      />
    </PluginSettings>
  );
};

plugin.registerComponent('settings-page', SettingsPage);

export default plugin;
```

---

## 🎯 Hook System

### Available Hooks

#### Device Hooks
```python
# Device lifecycle
"device.created"          # New device added
"device.updated"          # Device modified
"device.deleted"          # Device removed
"device.status_changed"   # Online/offline state
"device.heartbeat"        # Heartbeat received
"device.alert"            # Device alert triggered

# Handler signature
async def on_device_created(
    device_id: str,
    device_data: dict,
    user_id: str,
    tenant_id: str
) -> dict | None:
    pass
```

#### User Hooks
```python
"user.created"            # New user registered
"user.updated"            # User profile updated
"user.deleted"            # User account deleted
"user.login"              # User logged in
"user.logout"             # User logged out
"user.password_changed"   # Password reset
```

#### Organization Hooks
```python
"org.created"             # Organization created
"org.updated"             # Org settings changed
"org.deleted"             # Organization removed
"org.member_added"        # User joined org
"org.member_removed"      # User left org
```

#### Webhook Hooks
```python
"webhook.created"         # Webhook registered
"webhook.triggered"       # Webhook fired
"webhook.failed"          # Webhook delivery failed
```

#### Tenant Hooks
```python
"tenant.created"          # New tenant onboarded
"tenant.upgraded"         # Tier upgrade
"tenant.downgraded"       # Tier downgrade
"tenant.suspended"        # Tenant suspended
```

#### API Hooks
```python
"api.request.before"      # Before API request processed
"api.request.after"       # After API response
"api.error"               # API error occurred
```

### Filter Hooks

Modify data before processing:

```python
@plugin.filter("device.data.process")
async def process_device_data(data: dict) -> dict:
    """Transform device data before saving"""
    data["processed_at"] = datetime.now()
    data["plugin_metadata"] = {"source": "my-plugin"}
    return data

@plugin.filter("api.response.transform")
async def transform_response(response: dict) -> dict:
    """Modify API responses"""
    response["enhanced"] = True
    return response
```

---

## 🎨 UI Integration

### Plugin Slots

Frontend plugins can render in predefined slots:

```typescript
// Dashboard widgets
plugin.registerSlot('dashboard-widget', MyWidget);

// Device detail tabs
plugin.registerSlot('device-detail-tab', DeviceAnalytics);

// Settings pages
plugin.registerSlot('settings-page', PluginSettings);

// Navigation menu items
plugin.registerSlot('nav-menu-item', {
  label: 'My Plugin',
  icon: 'ExtensionIcon',
  path: '/plugins/my-plugin'
});

// Alert detail views
plugin.registerSlot('alert-detail', AlertEnhancer);

// User profile sections
plugin.registerSlot('user-profile-section', CustomFields);
```

### Dynamic Routes

```typescript
plugin.registerRoute({
  path: '/plugins/my-plugin',
  component: MyPluginPage,
  title: 'My Plugin',
  auth: true
});

plugin.registerRoute({
  path: '/plugins/my-plugin/reports/:id',
  component: ReportDetail,
  title: 'Report Detail'
});
```

---

## 📊 Plugin Analytics

### Track Events

```python
# Backend tracking
await plugin.analytics.track("prediction_made", {
    "model": "v2",
    "confidence": 0.95,
    "processing_time_ms": 123
})

await plugin.analytics.track("error", {
    "error_type": "api_timeout",
    "endpoint": "/external-service"
})
```

```typescript
// Frontend tracking
plugin.analytics.track('button_clicked', {
  button: 'generate_report',
  location: 'dashboard'
});

plugin.analytics.track('page_view', {
  page: '/plugins/my-plugin/settings'
});
```

### Analytics Dashboard

Plugin developers get access to:
- Total installations
- Active installations
- Daily active users
- Event tracking
- Error rates
- Performance metrics
- Revenue (for paid plugins)

---

## 🔄 Plugin Lifecycle

### State Machine

```
┌─────────────┐
│  Available  │  (In marketplace, not installed)
└──────┬──────┘
       │ install
       ▼
┌─────────────┐
│ Installing  │  (Downloading, validating)
└──────┬──────┘
       │ success
       ▼
┌─────────────┐
│  Installed  │  (Installed but disabled)
└──────┬──────┘
       │ enable
       ▼
┌─────────────┐
│   Enabled   │◄──┐ (Active and running)
└──────┬──────┘   │
       │          │ restart
       │ disable  │
       ▼          │
┌─────────────┐   │
│  Disabled   │───┘
└──────┬──────┘
       │ uninstall
       ▼
┌─────────────┐
│Uninstalling │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Removed    │
└─────────────┘
```

### Lifecycle Hooks

```python
class PluginLifecycle:
    async def on_install(self):
        """First-time setup"""
        pass
    
    async def on_enable(self):
        """Start plugin services"""
        pass
    
    async def on_disable(self):
        """Stop plugin services"""
        pass
    
    async def on_update(self, old_version: str, new_version: str):
        """Handle version migration"""
        pass
    
    async def on_uninstall(self):
        """Cleanup before removal"""
        pass
    
    async def on_config_change(self, old_config: dict, new_config: dict):
        """React to configuration updates"""
        pass
```

---

## 🧪 Testing Framework

### Plugin Test Template

```python
import pytest
from ops_center_sdk.testing import PluginTestCase

class TestMyPlugin(PluginTestCase):
    plugin_id = "my-plugin"
    
    async def test_hook_handler(self):
        """Test device.created hook"""
        # Trigger hook
        result = await self.emit_hook("device.created", {
            "device_id": "test-123",
            "device_data": {"name": "Test Device"}
        })
        
        assert result["processed"] == True
    
    async def test_api_endpoint(self):
        """Test custom API endpoint"""
        response = await self.client.post(
            "/plugins/my-plugin/predict",
            json={"data": [1, 2, 3]}
        )
        
        assert response.status_code == 200
        assert "prediction" in response.json()
    
    async def test_permissions(self):
        """Test permission enforcement"""
        # Should fail without permission
        with pytest.raises(PermissionError):
            await self.plugin.api.users.list()
        
        # Grant permission
        await self.grant_permission("api:users:read")
        
        # Should succeed
        users = await self.plugin.api.users.list()
        assert isinstance(users, list)
```

---

## 📝 Plugin Manifest

See detailed `plugin.yaml` specification above in **Plugin Structure** section.

---

## 🚀 Deployment & Distribution

### Build Plugin

```bash
# Install Ops-Center CLI
npm install -g @ops-center/cli

# Initialize plugin
ops-center plugin init my-awesome-plugin

# Build plugin (compiles, bundles, validates)
ops-center plugin build

# Output: my-awesome-plugin-1.0.0.zip
```

### Publish to Marketplace

```bash
# Login to marketplace
ops-center login

# Validate plugin
ops-center plugin validate my-awesome-plugin-1.0.0.zip

# Publish
ops-center plugin publish my-awesome-plugin-1.0.0.zip \
  --category ai \
  --tags "machine-learning,predictions" \
  --price 29.99

# Output:
# ✓ Plugin uploaded successfully
# ✓ Validation passed
# ✓ Published to marketplace
# 
# View at: https://marketplace.ops-center.com/plugins/my-awesome-plugin
```

### Private Registry

For enterprise internal plugins:

```bash
# Configure private registry
ops-center config set registry https://registry.company.com

# Publish privately
ops-center plugin publish my-plugin.zip --private
```

---

## 💰 Monetization

### Pricing Models

| Model | Description | Example |
|-------|-------------|---------|
| **Free** | No cost | Community plugins |
| **Freemium** | Free with paid upgrades | Limited features free |
| **One-time** | Single purchase | Lifetime license |
| **Subscription** | Monthly/yearly | $9.99/mo |
| **Usage-based** | Pay per use | $0.01 per API call |
| **Enterprise** | Custom pricing | Contact sales |

### Revenue Share

- **Free plugins**: 100% free (encouraged)
- **Paid plugins**: 70/30 split (Developer/Platform)
- **Enterprise licensing**: 85/15 split

### Payment Processing

```yaml
# In plugin.yaml
pricing:
  model: subscription
  monthly: 29.99
  yearly: 299.99
  trial_days: 14
  stripe_product_id: prod_ABC123
  
# Webhook for subscription events
payment_webhook:
  url: https://my-server.com/webhook
  events:
    - subscription.created
    - subscription.cancelled
    - payment.succeeded
    - payment.failed
```

---

## 🔐 Security Best Practices

### Code Review Process

1. **Automated Scanning**: All plugins scanned for malware, vulnerabilities
2. **Manual Review**: Official/verified plugins manually reviewed
3. **Community Reports**: Users can flag suspicious plugins
4. **Version Audits**: Each version independently reviewed

### Security Checklist

```yaml
security_checks:
  - ✓ No hardcoded secrets or API keys
  - ✓ Input validation on all endpoints
  - ✓ SQL injection prevention (parameterized queries)
  - ✓ XSS prevention (sanitized outputs)
  - ✓ CSRF tokens on state-changing operations
  - ✓ Rate limiting on API endpoints
  - ✓ Dependency vulnerability scan (Snyk, Dependabot)
  - ✓ Code signing with developer certificate
  - ✓ Permission declarations accurate
  - ✓ Error messages don't leak sensitive data
  - ✓ Logging doesn't expose PII
  - ✓ HTTPS for all external requests
```

### Vulnerability Disclosure

```bash
# Report security issue
ops-center security report \
  --plugin my-plugin \
  --severity critical \
  --description "SQL injection in /api/predict"

# Platform response time SLA:
# - Critical: 24 hours
# - High: 7 days
# - Medium: 30 days
```

---

## 📚 Example Plugins

### 1. Slack Integration Plugin

```yaml
id: slack-integration
name: Slack Notifications
description: Send device alerts to Slack channels
category: integration
type: backend

permissions:
  - api:devices:read
  - api:alerts:read
  - network:outbound

config_schema:
  webhook_url:
    type: string
    required: true
    description: Slack webhook URL

hooks:
  - name: device.alert
    handler: send_slack_notification
```

### 2. ML Anomaly Detection

```yaml
id: ml-anomaly-detection
name: ML Anomaly Detection
description: Detect unusual device behavior using machine learning
category: ai
type: hybrid

permissions:
  - api:devices:read
  - api:devices:write
  - storage:write
  - cron:schedule

dependencies:
  python:
    - scikit-learn>=1.0.0
    - pandas>=1.5.0

cron:
  - name: train-model
    schedule: "0 0 * * 0"  # Weekly
    handler: train_anomaly_model
```

### 3. Custom Dashboard Theme

```yaml
id: dark-theme-pro
name: Dark Theme Pro
description: Professional dark theme with customization
category: theme
type: frontend

pricing:
  monthly: 4.99
  yearly: 49.99

config_schema:
  primary_color:
    type: color
    default: "#1976d2"
  accent_color:
    type: color
    default: "#dc004e"
```

---

## 📈 Success Metrics

### Platform KPIs

- Total plugins published
- Total plugin installations
- Active plugin developers
- Marketplace revenue
- Average plugin rating
- Security incidents (target: 0)

### Developer KPIs

- Plugin installations
- Active users
- Rating score
- Revenue (if paid)
- Support ticket volume
- Update frequency

---

## 🗺️ Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- ✅ Database schema and migrations
- ✅ Plugin registry backend
- ✅ Basic lifecycle manager
- ✅ Permission system
- ✅ SDK scaffolding

### Phase 2: Marketplace (Week 2-3)
- ✅ Marketplace API endpoints
- ✅ Plugin upload and validation
- ✅ Search and discovery
- ✅ Reviews and ratings
- ✅ Analytics tracking

### Phase 3: Runtime & SDK (Week 3-4)
- ✅ Hook system implementation
- ✅ Python SDK with API client
- ✅ JavaScript/React SDK
- ✅ Plugin sandbox and isolation
- ✅ Resource limits enforcement

### Phase 4: UI & Distribution (Week 4)
- ✅ Marketplace UI (browse, search, install)
- ✅ Plugin management dashboard
- ✅ Developer portal
- ✅ CLI tools for publishing
- ✅ Documentation and examples

---

## 🎯 Next Steps

1. **Review this specification** - Approve architecture and scope
2. **Create database migration** - Set up plugin registry tables
3. **Implement backend APIs** - Plugin CRUD, marketplace, lifecycle
4. **Build SDK libraries** - Python and JavaScript SDKs
5. **Create marketplace UI** - Browse and install plugins
6. **Develop example plugins** - Showcase capabilities
7. **Write developer docs** - Comprehensive plugin development guide
8. **Beta testing** - Launch with select developers
9. **Public launch** - Open marketplace to community

---

## 📞 Questions?

**Architecture**: Platform Architecture Team  
**SDK Development**: Developer Experience Team  
**Security**: Security Engineering Team  
**Marketplace**: Product Team  

---

**Epic 11 Status:** Ready for implementation 🚀
