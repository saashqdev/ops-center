/**
 * Device Status Dashboard Widget
 * 
 * Example frontend plugin that displays device status in a dashboard widget
 */

import React, { useState, useEffect } from 'react';
import { Plugin } from '@ops-center/plugin-sdk';
import {
  PluginProvider,
  useDevices,
  useConfig,
  useInterval,
  Card,
  Badge,
  Loading,
  EmptyState,
  Button,
} from '@ops-center/plugin-sdk/react';

// Create plugin instance
export const plugin = new Plugin({
  id: 'device-status-widget',
  name: 'Device Status Widget',
  version: '1.0.0',
  description: 'Dashboard widget showing device status overview',
  author: 'Ops-Center Team',
  type: 'frontend',
  category: 'monitoring',
});

// ==================== Configuration ====================

// Set default config
plugin.config.setSchema({
  type: 'object',
  properties: {
    refreshInterval: {
      type: 'number',
      default: 30000,
      description: 'Refresh interval in milliseconds',
      minimum: 5000,
      maximum: 300000,
    },
    showOfflineDevices: {
      type: 'boolean',
      default: true,
      description: 'Show offline devices in widget',
    },
    maxDevices: {
      type: 'number',
      default: 10,
      description: 'Maximum devices to display',
      minimum: 1,
      maximum: 50,
    },
  },
});

// ==================== Widget Component ====================

function DeviceStatusWidget() {
  const { data: devices, loading, error, refetch } = useDevices();
  const [refreshInterval] = useConfig('refreshInterval', 30000);
  const [showOfflineDevices] = useConfig('showOfflineDevices', true);
  const [maxDevices] = useConfig('maxDevices', 10);

  // Auto-refresh
  useInterval(() => {
    refetch();
  }, refreshInterval);

  if (loading) {
    return <Loading text="Loading devices..." />;
  }

  if (error) {
    return (
      <Card title="Device Status">
        <div style={{ color: 'red' }}>Error loading devices: {error.message}</div>
      </Card>
    );
  }

  if (!devices || devices.length === 0) {
    return (
      <Card title="Device Status">
        <EmptyState
          title="No Devices"
          description="No devices have been registered yet"
          icon="📱"
        />
      </Card>
    );
  }

  // Filter and limit devices
  const filteredDevices = showOfflineDevices
    ? devices
    : devices.filter((d) => d.status !== 'offline');

  const displayDevices = filteredDevices.slice(0, maxDevices);

  // Calculate stats
  const stats = {
    total: devices.length,
    online: devices.filter((d) => d.status === 'online').length,
    offline: devices.filter((d) => d.status === 'offline').length,
    warning: devices.filter((d) => d.status === 'warning').length,
  };

  return (
    <Card
      title="Device Status"
      subtitle={`${stats.online} online / ${stats.total} total`}
      actions={
        <Button size="small" onClick={() => refetch()}>
          🔄 Refresh
        </Button>
      }
    >
      {/* Status Summary */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <StatusBadge label="Online" count={stats.online} variant="success" />
        <StatusBadge label="Offline" count={stats.offline} variant="error" />
        <StatusBadge label="Warning" count={stats.warning} variant="warning" />
      </div>

      {/* Device List */}
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {displayDevices.map((device) => (
          <DeviceRow key={device.id} device={device} />
        ))}
      </div>

      {filteredDevices.length > maxDevices && (
        <div style={{ marginTop: '12px', textAlign: 'center', color: '#666' }}>
          Showing {maxDevices} of {filteredDevices.length} devices
        </div>
      )}
    </Card>
  );
}

// ==================== Sub-components ====================

interface StatusBadgeProps {
  label: string;
  count: number;
  variant: 'success' | 'error' | 'warning';
}

function StatusBadge({ label, count, variant }: StatusBadgeProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{ fontSize: '12px', color: '#666' }}>{label}:</span>
      <Badge variant={variant}>{count}</Badge>
    </div>
  );
}

interface DeviceRowProps {
  device: any;
}

function DeviceRow({ device }: DeviceRowProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      <div>
        <div style={{ fontWeight: 'bold' }}>{device.name}</div>
        <div style={{ fontSize: '12px', color: '#666' }}>{device.type}</div>
      </div>
      <Badge variant={getStatusVariant(device.status)}>{device.status}</Badge>
    </div>
  );
}

// ==================== Settings Component ====================

function WidgetSettings() {
  const [refreshInterval, setRefreshInterval] = useConfig('refreshInterval', 30000);
  const [showOfflineDevices, setShowOfflineDevices] = useConfig('showOfflineDevices', true);
  const [maxDevices, setMaxDevices] = useConfig('maxDevices', 10);

  return (
    <Card title="Widget Settings">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Refresh Interval (ms)
          </label>
          <input
            type="number"
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            min="5000"
            max="300000"
            step="1000"
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </div>

        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showOfflineDevices}
              onChange={(e) => setShowOfflineDevices(e.target.checked)}
            />
            <span>Show Offline Devices</span>
          </label>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Max Devices to Display
          </label>
          <input
            type="number"
            value={maxDevices}
            onChange={(e) => setMaxDevices(Number(e.target.value))}
            min="1"
            max="50"
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </div>
      </div>
    </Card>
  );
}

// ==================== Plugin Registration ====================

// Register widget in dashboard slot
plugin.registerSlot('dashboard.widget', () => (
  <PluginProvider plugin={plugin}>
    <DeviceStatusWidget />
  </PluginProvider>
), 10);

// Register settings page
plugin.registerRoute('/settings', () => (
  <PluginProvider plugin={plugin}>
    <WidgetSettings />
  </PluginProvider>
), true);

// ==================== Lifecycle Handlers ====================

plugin.onEnable = async () => {
  plugin.log('info', 'Device Status Widget enabled');
  
  // Subscribe to device events
  plugin.hook('device.created', (device) => {
    plugin.log('info', 'New device detected:', device.id);
  });

  plugin.hook('device.status_changed', (device, oldStatus, newStatus) => {
    plugin.log('info', `Device ${device.id} status changed: ${oldStatus} -> ${newStatus}`);
  });
};

plugin.onDisable = async () => {
  plugin.log('info', 'Device Status Widget disabled');
};

// Export for Ops-Center to load
export default plugin;
