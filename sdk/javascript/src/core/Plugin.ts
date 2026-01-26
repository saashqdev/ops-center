/**
 * Core Plugin class for frontend plugins
 */

import EventEmitter from 'eventemitter3';
import { APIClient } from './APIClient';
import { Storage } from './Storage';
import { Config } from './Config';

export interface PluginMetadata {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  type: 'frontend' | 'hybrid';
  category: 'monitoring' | 'ai' | 'security' | 'integration' | 'analytics';
  homepage?: string;
  repository?: string;
  license?: string;
}

export interface PluginManifest extends PluginMetadata {
  permissions: string[];
  slots: SlotRegistration[];
  routes: RouteRegistration[];
  hooks: HookRegistration[];
  configSchema?: Record<string, any>;
}

export interface SlotRegistration {
  name: string;
  component: string;
  priority?: number;
}

export interface RouteRegistration {
  path: string;
  component: string;
  exact?: boolean;
}

export interface HookRegistration {
  event: string;
  handler: string;
  priority?: number;
}

export type HookHandler = (...args: any[]) => void | Promise<void>;
export type FilterHandler<T = any> = (data: T, ...args: any[]) => T | Promise<T>;

/**
 * Main Plugin class for frontend development
 */
export class Plugin {
  private _metadata: PluginMetadata;
  private _api: APIClient;
  private _storage: Storage;
  private _config: Config;
  private _events: EventEmitter;
  
  private _hooks: Map<string, Array<{ handler: HookHandler; priority: number }>> = new Map();
  private _filters: Map<string, Array<{ handler: FilterHandler; priority: number }>> = new Map();
  private _slots: Map<string, any> = new Map();
  private _routes: Array<{ path: string; component: any; exact?: boolean }> = [];

  constructor(metadata: PluginMetadata) {
    this._metadata = metadata;
    this._events = new EventEmitter();
    
    // Initialize services
    this._api = new APIClient();
    this._storage = new Storage(metadata.id);
    this._config = new Config(metadata.id);
  }

  // ==================== Properties ====================

  get metadata(): PluginMetadata {
    return { ...this._metadata };
  }

  get api(): APIClient {
    return this._api;
  }

  get storage(): Storage {
    return this._storage;
  }

  get config(): Config {
    return this._config;
  }

  get events(): EventEmitter {
    return this._events;
  }

  // ==================== Hook Registration ====================

  /**
   * Register an event hook
   */
  hook(event: string, handler: HookHandler, priority: number = 10): void {
    if (!this._hooks.has(event)) {
      this._hooks.set(event, []);
    }

    this._hooks.get(event)!.push({ handler, priority });
    
    // Sort by priority (higher first)
    this._hooks.get(event)!.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Register a filter hook
   */
  filter<T = any>(name: string, handler: FilterHandler<T>, priority: number = 10): void {
    if (!this._filters.has(name)) {
      this._filters.set(name, []);
    }

    this._filters.get(name)!.push({ handler, priority });
    
    // Sort by priority (higher first)
    this._filters.get(name)!.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Emit an event to registered hooks
   */
  async emit(event: string, ...args: any[]): Promise<void> {
    const handlers = this._hooks.get(event) || [];
    
    for (const { handler } of handlers) {
      await Promise.resolve(handler(...args));
    }
  }

  /**
   * Apply filters to data
   */
  async applyFilter<T = any>(name: string, data: T, ...args: any[]): Promise<T> {
    const handlers = this._filters.get(name) || [];
    
    let result = data;
    for (const { handler } of handlers) {
      result = await Promise.resolve(handler(result, ...args));
    }
    
    return result;
  }

  // ==================== Slot Registration ====================

  /**
   * Register a component for a UI slot
   */
  registerSlot(name: string, component: any, priority: number = 10): void {
    if (!this._slots.has(name)) {
      this._slots.set(name, []);
    }

    this._slots.get(name)!.push({ component, priority });
    
    // Sort by priority (higher first)
    this._slots.get(name)!.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Get components registered for a slot
   */
  getSlotComponents(name: string): any[] {
    const slot = this._slots.get(name) || [];
    return slot.map(s => s.component);
  }

  // ==================== Route Registration ====================

  /**
   * Register a route component
   */
  registerRoute(path: string, component: any, exact: boolean = true): void {
    this._routes.push({ path, component, exact });
  }

  /**
   * Get all registered routes
   */
  getRoutes(): Array<{ path: string; component: any; exact?: boolean }> {
    return [...this._routes];
  }

  // ==================== Lifecycle Methods ====================

  /**
   * Called when plugin is installed
   */
  async onInstall(): Promise<void> {
    // Override in subclass
  }

  /**
   * Called when plugin is enabled
   */
  async onEnable(): Promise<void> {
    // Override in subclass
  }

  /**
   * Called when plugin is disabled
   */
  async onDisable(): Promise<void> {
    // Override in subclass
  }

  /**
   * Called when plugin is uninstalled
   */
  async onUninstall(): Promise<void> {
    // Override in subclass
  }

  /**
   * Called when plugin configuration changes
   */
  async onConfigChange(key: string, value: any): Promise<void> {
    // Override in subclass
  }

  // ==================== Manifest Generation ====================

  /**
   * Generate plugin manifest
   */
  getManifest(): PluginManifest {
    return {
      ...this._metadata,
      permissions: [],
      slots: Array.from(this._slots.entries()).flatMap(([name, components]) =>
        components.map((c: any) => ({
          name,
          component: c.component.name || 'Component',
          priority: c.priority
        }))
      ),
      routes: this._routes.map(r => ({
        path: r.path,
        component: r.component.name || 'Component',
        exact: r.exact
      })),
      hooks: Array.from(this._hooks.entries()).flatMap(([event, handlers]) =>
        handlers.map(h => ({
          event,
          handler: h.handler.name || 'handler',
          priority: h.priority
        }))
      ),
      configSchema: this._config.getSchema()
    };
  }

  // ==================== Utility Methods ====================

  /**
   * Log message (will appear in browser console)
   */
  log(level: 'debug' | 'info' | 'warn' | 'error', message: string, ...args: any[]): void {
    const prefix = `[${this._metadata.id}]`;
    
    switch (level) {
      case 'debug':
        console.debug(prefix, message, ...args);
        break;
      case 'info':
        console.info(prefix, message, ...args);
        break;
      case 'warn':
        console.warn(prefix, message, ...args);
        break;
      case 'error':
        console.error(prefix, message, ...args);
        break;
    }
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this._events.removeAllListeners();
    this._hooks.clear();
    this._filters.clear();
    this._slots.clear();
    this._routes = [];
  }
}

export default Plugin;
