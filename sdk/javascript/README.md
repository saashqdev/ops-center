# Ops-Center Plugin SDK (JavaScript/React)

Build powerful frontend plugins for Ops-Center using React and TypeScript.

## 🚀 Features

- 🎣 **React Hooks** - Access devices, users, alerts, and more with simple hooks
- 🧩 **UI Slots** - Inject components anywhere in Ops-Center UI
- 🎨 **Components** - Pre-built components (Card, Badge, Button, Alert, etc.)
- 💾 **Storage** - Browser localStorage with namespacing
- ⚙️ **Configuration** - Schema-based config with validation
- 📡 **API Client** - Type-safe Ops-Center API access
- 🧪 **Testing** - Comprehensive testing utilities
- 📦 **TypeScript** - Full type safety and IntelliSense

## 📦 Installation

```bash
npm install @ops-center/plugin-sdk react react-dom
# or
yarn add @ops-center/plugin-sdk react react-dom
# or
pnpm add @ops-center/plugin-sdk react react-dom
```

## 🎯 Quick Start

### Create a Plugin

```typescript
import { Plugin } from '@ops-center/plugin-sdk';
import { PluginProvider, useDevices, Card } from '@ops-center/plugin-sdk/react';

// Create plugin instance
const plugin = new Plugin({
  id: 'my-widget',
  name: 'My Widget',
  version: '1.0.0',
  description: 'My awesome widget',
  author: 'Your Name',
  type: 'frontend',
  category: 'monitoring'
});

// Create widget component
function MyWidget() {
  const { data: devices, loading } = useDevices();

  if (loading) return <div>Loading...</div>;

  return (
    <Card title="My Widget">
      <p>Total devices: {devices?.length || 0}</p>
    </Card>
  );
}

// Register in dashboard slot
plugin.registerSlot('dashboard.widget', () => (
  <PluginProvider plugin={plugin}>
    <MyWidget />
  </PluginProvider>
));

export default plugin;
```

## 📚 Core Concepts

### Plugin Class

Main entry point for plugin development.

```typescript
import { Plugin } from '@ops-center/plugin-sdk';

const plugin = new Plugin({
  id: 'unique-id',
  name: 'Display Name',
  version: '1.0.0',
  description: 'What your plugin does',
  author: 'Your Name',
  type: 'frontend',  // or 'hybrid'
  category: 'monitoring'  // monitoring, ai, security, integration, analytics
});
```

### React Hooks

#### useDevices

Fetch all devices with optional filtering.

```typescript
import { useDevices } from '@ops-center/plugin-sdk/react';

function DeviceList() {
  const { data: devices, loading, error, refetch } = useDevices({ status: 'online' });

  if (loading) return <Loading />;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {devices.map(device => (
        <div key={device.id}>{device.name}</div>
      ))}
      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

#### useDevice

Fetch a single device by ID.

```typescript
import { useDevice } from '@ops-center/plugin-sdk/react';

function DeviceDetail({ deviceId }: { deviceId: string }) {
  const { data: device, loading } = useDevice(deviceId);

  if (loading) return <Loading />;
  if (!device) return <div>Device not found</div>;

  return (
    <Card title={device.name}>
      <p>Type: {device.type}</p>
      <p>Status: {device.status}</p>
    </Card>
  );
}
```

#### useStorage

Persist data in browser localStorage.

```typescript
import { useStorage } from '@ops-center/plugin-sdk/react';

function SettingsPanel() {
  const [theme, setTheme, removeTheme] = useStorage('theme', 'light');

  return (
    <div>
      <select value={theme} onChange={(e) => setTheme(e.target.value)}>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
      <button onClick={removeTheme}>Reset</button>
    </div>
  );
}
```

#### useConfig

Manage plugin configuration with schema validation.

```typescript
import { useConfig } from '@ops-center/plugin-sdk/react';

// Set schema first
plugin.config.setSchema({
  type: 'object',
  properties: {
    refreshInterval: {
      type: 'number',
      default: 30000,
      minimum: 5000,
      maximum: 300000
    }
  }
});

function Settings() {
  const [interval, setInterval] = useConfig('refreshInterval', 30000);

  return (
    <input
      type="number"
      value={interval}
      onChange={(e) => setInterval(Number(e.target.value))}
      min="5000"
      max="300000"
    />
  );
}
```

#### useMutation

Perform create/update/delete operations.

```typescript
import { useMutation } from '@ops-center/plugin-sdk/react';

function CreateDeviceForm() {
  const { mutate: createDevice, loading } = useMutation(
    (api, data) => api.createDevice(data),
    {
      onSuccess: (device) => {
        console.log('Device created:', device);
      }
    }
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    createDevice({ name: 'New Device', type: 'server' });
  };

  return (
    <form onSubmit={handleSubmit}>
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Device'}
      </button>
    </form>
  );
}
```

### Components

#### Card

Container with title, subtitle, and actions.

```typescript
import { Card, Button } from '@ops-center/plugin-sdk/react';

<Card
  title="Device Status"
  subtitle="5 online / 10 total"
  actions={<Button size="small">Refresh</Button>}
>
  <p>Content goes here</p>
</Card>
```

#### Badge

Status indicator with color variants.

```typescript
import { Badge } from '@ops-center/plugin-sdk/react';

<Badge variant="success">Online</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="error">Offline</Badge>
```

#### Button

Customizable button with variants and sizes.

```typescript
import { Button } from '@ops-center/plugin-sdk/react';

<Button variant="primary" size="medium" onClick={handleClick}>
  Click Me
</Button>

<Button variant="success" loading={isLoading}>
  Save
</Button>
```

#### Alert

Display messages with different severity levels.

```typescript
import { Alert } from '@ops-center/plugin-sdk/react';

<Alert type="info" title="Information">
  This is an informational message
</Alert>

<Alert type="error" onClose={() => setShowAlert(false)}>
  An error occurred
</Alert>
```

#### Loading

Show loading spinner.

```typescript
import { Loading } from '@ops-center/plugin-sdk/react';

<Loading text="Loading devices..." size="medium" />
```

#### EmptyState

Display when no data is available.

```typescript
import { EmptyState, Button } from '@ops-center/plugin-sdk/react';

<EmptyState
  title="No Devices"
  description="You haven't added any devices yet"
  icon="📱"
  action={<Button onClick={handleAdd}>Add Device</Button>}
/>
```

### UI Slots

Register components in specific UI locations.

```typescript
// Dashboard widget
plugin.registerSlot('dashboard.widget', MyWidget, 10);

// Sidebar menu item
plugin.registerSlot('sidebar.menu', MyMenuItem, 5);

// Device detail tab
plugin.registerSlot('device.detail.tab', MyDeviceTab, 8);

// Alert list item
plugin.registerSlot('alert.list.item', MyAlertItem, 7);
```

**Available Slots:**
- `dashboard.widget` - Dashboard widgets
- `sidebar.menu` - Sidebar navigation items
- `device.detail.tab` - Device detail tabs
- `device.list.actions` - Device list action buttons
- `alert.list.item` - Alert list customization
- `user.profile.tab` - User profile tabs
- `settings.tab` - Settings page tabs

### Routes

Register custom pages.

```typescript
plugin.registerRoute('/my-page', MyPageComponent, true);
plugin.registerRoute('/device/:id/custom', DeviceCustomView, true);
```

Access at: `/plugins/my-plugin/my-page`

### Event Hooks

React to system events.

```typescript
import { useEvent } from '@ops-center/plugin-sdk/react';

function MyComponent() {
  useEvent('device.created', (device) => {
    console.log('New device:', device);
  });

  useEvent('alert.created', (alert) => {
    console.log('New alert:', alert);
  });

  return <div>Listening for events...</div>;
}
```

**Available Events:**
- `device.created` - Device created
- `device.updated` - Device updated
- `device.deleted` - Device deleted
- `device.metrics_updated` - Metrics received
- `alert.created` - Alert created
- `alert.acknowledged` - Alert acknowledged
- `alert.resolved` - Alert resolved
- `user.created` - User created

## 🧪 Testing

### Setup

```bash
npm install --save-dev @testing-library/react @testing-library/react-hooks jest
```

### Test Plugin

```typescript
import { createTestPlugin, mockDevice } from '@ops-center/plugin-sdk/testing';
import { renderHook, waitFor } from '@testing-library/react-hooks';
import { useDevices } from '@ops-center/plugin-sdk/react';

describe('Device Widget', () => {
  it('should load devices', async () => {
    const plugin = createTestPlugin();
    
    // Add mock data
    (plugin.api as any).setMockDevice(mockDevice({ id: 'device-1', name: 'Test Device' }));

    // Render hook
    const wrapper = ({ children }) => (
      <PluginProvider plugin={plugin}>{children}</PluginProvider>
    );

    const { result } = renderHook(() => useDevices(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data[0].name).toBe('Test Device');
  });
});
```

### Test Components

```typescript
import { render, screen, fireEvent } from '@ops-center/plugin-sdk/testing';
import { PluginProvider } from '@ops-center/plugin-sdk/react';

test('renders button and handles click', () => {
  const plugin = createTestPlugin();
  const handleClick = jest.fn();

  render(
    <PluginProvider plugin={plugin}>
      <Button onClick={handleClick}>Click Me</Button>
    </PluginProvider>
  );

  const button = screen.getByText('Click Me');
  fireEvent.click(button);

  expect(handleClick).toHaveBeenCalledTimes(1);
});
```

## 📖 API Reference

### Plugin

```typescript
class Plugin {
  constructor(metadata: PluginMetadata);
  
  // Properties
  readonly metadata: PluginMetadata;
  readonly api: APIClient;
  readonly storage: Storage;
  readonly config: Config;
  readonly events: EventEmitter;

  // Methods
  hook(event: string, handler: Function, priority?: number): void;
  filter(name: string, handler: Function, priority?: number): void;
  registerSlot(name: string, component: React.Component, priority?: number): void;
  registerRoute(path: string, component: React.Component, exact?: boolean): void;
  emit(event: string, ...args: any[]): Promise<void>;
  applyFilter<T>(name: string, data: T, ...args: any[]): Promise<T>;
  
  // Lifecycle
  onInstall(): Promise<void>;
  onEnable(): Promise<void>;
  onDisable(): Promise<void>;
  onUninstall(): Promise<void>;
  onConfigChange(key: string, value: any): Promise<void>;
}
```

### APIClient

```typescript
class APIClient {
  // Devices
  getDevices(params?: { page?: number; status?: string }): Promise<Device[]>;
  getDevice(id: string): Promise<Device>;
  createDevice(data: Partial<Device>): Promise<Device>;
  updateDevice(id: string, data: Partial<Device>): Promise<Device>;
  deleteDevice(id: string): Promise<void>;
  getDeviceMetrics(id: string, params?: { start?: string; end?: string }): Promise<any>;

  // Users
  getUsers(): Promise<User[]>;
  getUser(id: string): Promise<User>;
  getCurrentUser(): Promise<User>;

  // Alerts
  getAlerts(params?: { severity?: string; status?: string }): Promise<Alert[]>;
  getAlert(id: string): Promise<Alert>;
  createAlert(data: Partial<Alert>): Promise<Alert>;
  acknowledgeAlert(id: string): Promise<Alert>;
  resolveAlert(id: string): Promise<Alert>;

  // Plugin APIs
  callPluginAPI<T>(pluginId: string, endpoint: string, options?: any): Promise<T>;
  getPluginConfig(pluginId: string): Promise<Record<string, any>>;
  updatePluginConfig(pluginId: string, config: Record<string, any>): Promise<any>;
}
```

## 🎨 Examples

See [examples/device-status-widget](examples/device-status-widget) for a complete example plugin.

## 📝 Plugin Manifest

Create `plugin.json`:

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "My awesome plugin",
  "author": "Your Name",
  "type": "frontend",
  "category": "monitoring",
  "permissions": ["devices:read", "alerts:write"],
  "slots": [
    {
      "name": "dashboard.widget",
      "component": "MyWidget",
      "priority": 10
    }
  ],
  "routes": [
    {
      "path": "/settings",
      "component": "Settings",
      "exact": true
    }
  ],
  "config_schema": {
    "type": "object",
    "properties": {
      "theme": {
        "type": "string",
        "default": "light",
        "enum": ["light", "dark"]
      }
    }
  }
}
```

## 🚀 Building & Publishing

### Build

```bash
npm run build
```

Creates production bundle in `dist/`.

### Publish to Ops-Center

```bash
# Package plugin
tar -czf my-plugin-1.0.0.tar.gz dist/ plugin.json README.md

# Upload to Ops-Center marketplace
# (Use Ops-Center admin panel or API)
```

## 📚 TypeScript Support

Full TypeScript support with type definitions included.

```typescript
import type { Plugin, Device, Alert } from '@ops-center/plugin-sdk';
import type { UseAPIOptions } from '@ops-center/plugin-sdk/react';
```

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

MIT - see [LICENSE](LICENSE)

## 🔗 Links

- [Documentation](https://docs.ops-center.com/plugins)
- [Examples](examples/)
- [GitHub](https://github.com/ops-center/plugin-sdk)
- [npm](https://www.npmjs.com/package/@ops-center/plugin-sdk)
