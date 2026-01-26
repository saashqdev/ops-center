/**
 * Metrics Dashboard Plugin
 * 
 * Advanced metrics visualization dashboard with custom charts
 * Demonstrates: Multiple slots, data visualization, real-time updates, chart library integration
 */

import React, { useState, useEffect } from 'react';
import { Plugin } from '@ops-center/plugin-sdk';
import {
  PluginProvider,
  useDevices,
  useDeviceMetrics,
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
  id: 'metrics-dashboard',
  name: 'Metrics Dashboard',
  version: '1.0.0',
  description: 'Advanced metrics visualization with custom charts',
  author: 'Ops-Center Team',
  type: 'frontend',
  category: 'analytics',
});

// ==================== Configuration ====================

plugin.config.setSchema({
  type: 'object',
  properties: {
    refreshInterval: {
      type: 'number',
      default: 5000,
      description: 'Chart refresh interval (ms)',
      minimum: 1000,
      maximum: 60000,
    },
    showCpuChart: {
      type: 'boolean',
      default: true,
      description: 'Show CPU usage chart',
    },
    showMemoryChart: {
      type: 'boolean',
      default: true,
      description: 'Show memory usage chart',
    },
    showNetworkChart: {
      type: 'boolean',
      default: true,
      description: 'Show network traffic chart',
    },
    chartType: {
      type: 'string',
      default: 'line',
      enum: ['line', 'bar', 'area'],
      description: 'Chart visualization type',
    },
    maxDataPoints: {
      type: 'number',
      default: 20,
      description: 'Maximum data points to display',
      minimum: 10,
      maximum: 100,
    },
  },
});

// ==================== Metrics Chart Component ====================

interface MetricsChartProps {
  deviceId: string;
  metricType: 'cpu' | 'memory' | 'network';
  title: string;
}

function MetricsChart({ deviceId, metricType, title }: MetricsChartProps) {
  const [refreshInterval] = useConfig('refreshInterval', 5000);
  const [chartType] = useConfig('chartType', 'line');
  const [maxDataPoints] = useConfig('maxDataPoints', 20);
  
  const [dataPoints, setDataPoints] = useState<number[]>([]);
  const [labels, setLabels] = useState<string[]>([]);

  const { data: metrics, refetch } = useDeviceMetrics(deviceId);

  // Auto-refresh
  useInterval(() => {
    refetch();
  }, refreshInterval);

  // Update chart data when metrics change
  useEffect(() => {
    if (metrics) {
      const value = extractMetricValue(metrics, metricType);
      const timestamp = new Date().toLocaleTimeString();

      setDataPoints((prev) => {
        const newData = [...prev, value];
        return newData.slice(-maxDataPoints);
      });

      setLabels((prev) => {
        const newLabels = [...prev, timestamp];
        return newLabels.slice(-maxDataPoints);
      });
    }
  }, [metrics, metricType, maxDataPoints]);

  const extractMetricValue = (metrics: any, type: string): number => {
    switch (type) {
      case 'cpu':
        return metrics.cpu_usage || 0;
      case 'memory':
        return metrics.memory_usage || 0;
      case 'network':
        return metrics.network_bytes_in || 0;
      default:
        return 0;
    }
  };

  const getMaxValue = (): number => {
    if (metricType === 'cpu' || metricType === 'memory') return 100;
    return Math.max(...dataPoints, 100);
  };

  const renderChart = () => {
    const maxValue = getMaxValue();

    return (
      <div style={{ position: 'relative', height: '200px', marginTop: '16px' }}>
        <svg width="100%" height="200" style={{ border: '1px solid #e0e0e0' }}>
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((percent) => {
            const y = 200 - (percent / 100) * 180 + 10;
            return (
              <g key={percent}>
                <line
                  x1="0"
                  y1={y}
                  x2="100%"
                  y2={y}
                  stroke="#f0f0f0"
                  strokeDasharray="2,2"
                />
                <text x="5" y={y - 5} fontSize="10" fill="#666">
                  {Math.round((percent / 100) * maxValue)}
                </text>
              </g>
            );
          })}

          {/* Data line/bars */}
          {chartType === 'line' && renderLineChart(maxValue)}
          {chartType === 'bar' && renderBarChart(maxValue)}
          {chartType === 'area' && renderAreaChart(maxValue)}
        </svg>

        {/* Current value */}
        <div style={{ marginTop: '8px', textAlign: 'center', fontSize: '24px', fontWeight: 'bold' }}>
          {dataPoints[dataPoints.length - 1]?.toFixed(1) || 0}
          {metricType !== 'network' ? '%' : ' MB/s'}
        </div>
      </div>
    );
  };

  const renderLineChart = (maxValue: number) => {
    if (dataPoints.length < 2) return null;

    const width = 100; // percentage
    const points = dataPoints
      .map((value, index) => {
        const x = (index / (maxDataPoints - 1)) * width;
        const y = 200 - ((value / maxValue) * 180 + 10);
        return `${x}%,${y}`;
      })
      .join(' ');

    return <polyline points={points} fill="none" stroke="#3498db" strokeWidth="2" />;
  };

  const renderBarChart = (maxValue: number) => {
    const barWidth = 100 / maxDataPoints;

    return dataPoints.map((value, index) => {
      const x = (index / maxDataPoints) * 100;
      const height = (value / maxValue) * 180;
      const y = 200 - height - 10;

      return (
        <rect
          key={index}
          x={`${x}%`}
          y={y}
          width={`${barWidth * 0.8}%`}
          height={height}
          fill="#3498db"
        />
      );
    });
  };

  const renderAreaChart = (maxValue: number) => {
    if (dataPoints.length < 2) return null;

    const width = 100;
    const points = dataPoints
      .map((value, index) => {
        const x = (index / (maxDataPoints - 1)) * width;
        const y = 200 - ((value / maxValue) * 180 + 10);
        return `${x}%,${y}`;
      })
      .join(' ');

    const areaPoints = `0%,190 ${points} ${width}%,190`;

    return (
      <>
        <polygon points={areaPoints} fill="#3498db" fillOpacity="0.2" />
        <polyline points={points} fill="none" stroke="#3498db" strokeWidth="2" />
      </>
    );
  };

  if (dataPoints.length === 0) {
    return (
      <Card title={title}>
        <EmptyState title="Collecting metrics..." description="Data will appear shortly" />
      </Card>
    );
  }

  return (
    <Card
      title={title}
      actions={
        <Button size="small" onClick={() => setDataPoints([])}>
          Clear
        </Button>
      }
    >
      {renderChart()}
    </Card>
  );
}

// ==================== Dashboard Widget ====================

function MetricsDashboard() {
  const { data: devices, loading } = useDevices({ status: 'online' });
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');

  const [showCpuChart] = useConfig('showCpuChart', true);
  const [showMemoryChart] = useConfig('showMemoryChart', true);
  const [showNetworkChart] = useConfig('showNetworkChart', true);

  useEffect(() => {
    if (devices && devices.length > 0 && !selectedDeviceId) {
      setSelectedDeviceId(devices[0].id);
    }
  }, [devices, selectedDeviceId]);

  if (loading) {
    return <Loading text="Loading devices..." />;
  }

  if (!devices || devices.length === 0) {
    return (
      <Card title="Metrics Dashboard">
        <EmptyState title="No Devices" description="No online devices to monitor" icon="📊" />
      </Card>
    );
  }

  return (
    <div>
      {/* Device selector */}
      <Card title="Metrics Dashboard" subtitle="Real-time device metrics">
        <div style={{ marginBottom: '16px' }}>
          <label style={{ marginRight: '8px', fontWeight: 'bold' }}>Select Device:</label>
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            style={{
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              minWidth: '200px',
            }}
          >
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name} ({device.type})
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Charts */}
      {selectedDeviceId && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginTop: '16px' }}>
          {showCpuChart && <MetricsChart deviceId={selectedDeviceId} metricType="cpu" title="CPU Usage" />}
          {showMemoryChart && <MetricsChart deviceId={selectedDeviceId} metricType="memory" title="Memory Usage" />}
          {showNetworkChart && <MetricsChart deviceId={selectedDeviceId} metricType="network" title="Network Traffic" />}
        </div>
      )}
    </div>
  );
}

// ==================== Settings Component ====================

function DashboardSettings() {
  const [refreshInterval, setRefreshInterval] = useConfig('refreshInterval', 5000);
  const [showCpuChart, setShowCpuChart] = useConfig('showCpuChart', true);
  const [showMemoryChart, setShowMemoryChart] = useConfig('showMemoryChart', true);
  const [showNetworkChart, setShowNetworkChart] = useConfig('showNetworkChart', true);
  const [chartType, setChartType] = useConfig('chartType', 'line');
  const [maxDataPoints, setMaxDataPoints] = useConfig('maxDataPoints', 20);

  return (
    <Card title="Dashboard Settings">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Refresh Interval (ms)
          </label>
          <input
            type="number"
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            min="1000"
            max="60000"
            step="1000"
            style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Chart Type
          </label>
          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value)}
            style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
          >
            <option value="line">Line Chart</option>
            <option value="bar">Bar Chart</option>
            <option value="area">Area Chart</option>
          </select>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Max Data Points
          </label>
          <input
            type="number"
            value={maxDataPoints}
            onChange={(e) => setMaxDataPoints(Number(e.target.value))}
            min="10"
            max="100"
            style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Visible Charts
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showCpuChart}
                onChange={(e) => setShowCpuChart(e.target.checked)}
              />
              <span>CPU Usage</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showMemoryChart}
                onChange={(e) => setShowMemoryChart(e.target.checked)}
              />
              <span>Memory Usage</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showNetworkChart}
                onChange={(e) => setShowNetworkChart(e.target.checked)}
              />
              <span>Network Traffic</span>
            </label>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ==================== Plugin Registration ====================

// Register in multiple slots
plugin.registerSlot(
  'dashboard.widget',
  () => (
    <PluginProvider plugin={plugin}>
      <MetricsDashboard />
    </PluginProvider>
  ),
  15
);

plugin.registerSlot(
  'device.detail.tab',
  () => (
    <PluginProvider plugin={plugin}>
      <MetricsDashboard />
    </PluginProvider>
  ),
  10
);

// Register settings page
plugin.registerRoute(
  '/settings',
  () => (
    <PluginProvider plugin={plugin}>
      <DashboardSettings />
    </PluginProvider>
  ),
  true
);

// ==================== Lifecycle ====================

plugin.onEnable = async () => {
  plugin.log('info', 'Metrics Dashboard enabled');
};

plugin.onDisable = async () => {
  plugin.log('info', 'Metrics Dashboard disabled');
};

export default plugin;
