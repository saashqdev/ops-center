/**
 * @ops-center/plugin-sdk/testing
 * 
 * Testing utilities for plugin development
 */

import { Plugin, PluginMetadata } from './core/Plugin';
import { APIClient } from './core/APIClient';
import { Storage } from './core/Storage';
import { Config, ConfigSchema } from './core/Config';

// ==================== Mock API Client ====================

export class MockAPIClient extends APIClient {
  private _requestLog: Array<{ method: string; endpoint: string; data?: any }> = [];
  private _mockDevices: Map<string, any> = new Map();
  private _mockUsers: Map<string, any> = new Map();
  private _mockOrgs: Map<string, any> = new Map();
  private _mockAlerts: Map<string, any> = new Map();

  constructor() {
    super({ baseURL: 'http://mock' });
  }

  private logRequest(method: string, endpoint: string, data?: any) {
    this._requestLog.push({ method, endpoint, data });
  }

  getRequestLog() {
    return [...this._requestLog];
  }

  clearRequestLog() {
    this._requestLog = [];
  }

  // Override API methods with mocks
  async getDevices(params?: any) {
    this.logRequest('GET', '/devices', params);
    return Array.from(this._mockDevices.values());
  }

  async getDevice(id: string) {
    this.logRequest('GET', `/devices/${id}`);
    return this._mockDevices.get(id) || null;
  }

  async createDevice(data: any) {
    this.logRequest('POST', '/devices', data);
    const device = { id: `device-${this._mockDevices.size}`, ...data };
    this._mockDevices.set(device.id, device);
    return device;
  }

  async updateDevice(id: string, data: any) {
    this.logRequest('PUT', `/devices/${id}`, data);
    const device = this._mockDevices.get(id);
    if (device) {
      Object.assign(device, data);
      return device;
    }
    return null;
  }

  async deleteDevice(id: string) {
    this.logRequest('DELETE', `/devices/${id}`);
    this._mockDevices.delete(id);
  }

  async getUsers() {
    this.logRequest('GET', '/users');
    return Array.from(this._mockUsers.values());
  }

  async getUser(id: string) {
    this.logRequest('GET', `/users/${id}`);
    return this._mockUsers.get(id) || null;
  }

  async getCurrentUser() {
    this.logRequest('GET', '/users/me');
    return { id: 'user-me', email: 'test@example.com', name: 'Test User', role: 'admin' };
  }

  async getAlerts(params?: any) {
    this.logRequest('GET', '/alerts', params);
    return Array.from(this._mockAlerts.values());
  }

  async createAlert(data: any) {
    this.logRequest('POST', '/alerts', data);
    const alert = { id: `alert-${this._mockAlerts.size}`, status: 'active', ...data };
    this._mockAlerts.set(alert.id, alert);
    return alert;
  }

  // Test helpers
  setMockDevice(device: any) {
    this._mockDevices.set(device.id, device);
  }

  setMockUser(user: any) {
    this._mockUsers.set(user.id, user);
  }

  setMockAlert(alert: any) {
    this._mockAlerts.set(alert.id, alert);
  }
}

// ==================== Mock Storage ====================

export class MockStorage extends Storage {
  private _data: Map<string, any> = new Map();

  constructor(pluginId: string = 'test-plugin') {
    super(pluginId);
  }

  set<T = any>(key: string, value: T): void {
    this._data.set(key, value);
  }

  get<T = any>(key: string, defaultValue?: T): T | undefined {
    return this._data.has(key) ? this._data.get(key) : defaultValue;
  }

  remove(key: string): void {
    this._data.delete(key);
  }

  has(key: string): boolean {
    return this._data.has(key);
  }

  keys(): string[] {
    return Array.from(this._data.keys());
  }

  clear(): void {
    this._data.clear();
  }

  getSize(): number {
    return JSON.stringify(Array.from(this._data.entries())).length;
  }
}

// ==================== Mock Config ====================

export class MockConfig extends Config {
  private _data: Map<string, any> = new Map();

  constructor(pluginId: string = 'test-plugin', schema?: ConfigSchema) {
    super(pluginId, schema);
  }

  get<T = any>(key: string, defaultValue?: T): T {
    return this._data.has(key) ? this._data.get(key) : defaultValue;
  }

  set(key: string, value: any): void {
    this._data.set(key, value);
  }

  all(): Record<string, any> {
    const result: Record<string, any> = {};
    this._data.forEach((value, key) => {
      result[key] = value;
    });
    return result;
  }

  reset(): void {
    this._data.clear();
  }
}

// ==================== Create Test Plugin ====================

export function createTestPlugin(
  metadata?: Partial<PluginMetadata>,
  config?: Record<string, any>
): Plugin {
  const defaultMetadata: PluginMetadata = {
    id: 'test-plugin',
    name: 'Test Plugin',
    version: '1.0.0',
    description: 'Test plugin for unit tests',
    author: 'Test Author',
    type: 'frontend',
    category: 'monitoring',
    ...metadata,
  };

  const plugin = new Plugin(defaultMetadata);

  // Replace with mock implementations
  (plugin as any)._api = new MockAPIClient();
  (plugin as any)._storage = new MockStorage(defaultMetadata.id);
  (plugin as any)._config = new MockConfig(defaultMetadata.id);

  // Set initial config
  if (config) {
    Object.entries(config).forEach(([key, value]) => {
      plugin.config.set(key, value);
    });
  }

  return plugin;
}

// ==================== Test Helpers ====================

export function mockDevice(overrides?: Partial<any>) {
  return {
    id: 'device-test-1',
    name: 'Test Device',
    type: 'server',
    status: 'online',
    ...overrides,
  };
}

export function mockUser(overrides?: Partial<any>) {
  return {
    id: 'user-test-1',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    ...overrides,
  };
}

export function mockAlert(overrides?: Partial<any>) {
  return {
    id: 'alert-test-1',
    device_id: 'device-test-1',
    severity: 'warning',
    title: 'Test Alert',
    message: 'This is a test alert',
    status: 'active',
    ...overrides,
  };
}

// ==================== React Testing Utilities ====================

export { renderHook, act } from '@testing-library/react-hooks';
export { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Re-export for convenience
export { MockAPIClient, MockStorage, MockConfig };
