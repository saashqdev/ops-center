/**
 * Configuration management for plugins
 */

import { Storage } from './Storage';

export interface ConfigSchema {
  type: 'object';
  properties: Record<string, ConfigProperty>;
}

export interface ConfigProperty {
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  default?: any;
  description?: string;
  enum?: any[];
  minimum?: number;
  maximum?: number;
}

export class Config {
  private storage: Storage;
  private schema?: ConfigSchema;
  private cache: Map<string, any> = new Map();

  constructor(pluginId: string, schema?: ConfigSchema) {
    this.storage = new Storage(pluginId);
    this.schema = schema;
    
    // Load cached config
    this.loadCache();
  }

  private loadCache(): void {
    const stored = this.storage.get<Record<string, any>>('__config__', {});
    
    for (const [key, value] of Object.entries(stored)) {
      this.cache.set(key, value);
    }
  }

  private saveCache(): void {
    const config: Record<string, any> = {};
    
    for (const [key, value] of this.cache.entries()) {
      config[key] = value;
    }
    
    this.storage.set('__config__', config);
  }

  /**
   * Get configuration value
   */
  get<T = any>(key: string, defaultValue?: T): T {
    if (this.cache.has(key)) {
      return this.cache.get(key) as T;
    }

    // Check schema for default
    if (this.schema?.properties[key]?.default !== undefined) {
      return this.schema.properties[key].default as T;
    }

    return defaultValue as T;
  }

  /**
   * Set configuration value
   */
  set(key: string, value: any): void {
    // Validate against schema if present
    if (this.schema?.properties[key]) {
      this.validateValue(key, value, this.schema.properties[key]);
    }

    this.cache.set(key, value);
    this.saveCache();
  }

  /**
   * Get all configuration
   */
  all(): Record<string, any> {
    const config: Record<string, any> = {};

    // Add schema defaults
    if (this.schema) {
      for (const [key, prop] of Object.entries(this.schema.properties)) {
        if (prop.default !== undefined) {
          config[key] = prop.default;
        }
      }
    }

    // Override with cached values
    for (const [key, value] of this.cache.entries()) {
      config[key] = value;
    }

    return config;
  }

  /**
   * Reset to defaults
   */
  reset(): void {
    this.cache.clear();
    this.saveCache();
  }

  /**
   * Validate value against schema property
   */
  private validateValue(key: string, value: any, property: ConfigProperty): void {
    const actualType = typeof value;
    
    // Type check
    if (property.type === 'array') {
      if (!Array.isArray(value)) {
        throw new TypeError(`Config ${key}: expected array, got ${actualType}`);
      }
    } else if (property.type !== actualType) {
      throw new TypeError(`Config ${key}: expected ${property.type}, got ${actualType}`);
    }

    // Enum check
    if (property.enum && !property.enum.includes(value)) {
      throw new Error(`Config ${key}: value must be one of ${property.enum.join(', ')}`);
    }

    // Range check for numbers
    if (property.type === 'number') {
      if (property.minimum !== undefined && value < property.minimum) {
        throw new RangeError(`Config ${key}: value ${value} is below minimum ${property.minimum}`);
      }
      if (property.maximum !== undefined && value > property.maximum) {
        throw new RangeError(`Config ${key}: value ${value} exceeds maximum ${property.maximum}`);
      }
    }
  }

  /**
   * Get configuration schema
   */
  getSchema(): ConfigSchema | undefined {
    return this.schema;
  }

  /**
   * Update schema
   */
  setSchema(schema: ConfigSchema): void {
    this.schema = schema;
  }
}

export default Config;
