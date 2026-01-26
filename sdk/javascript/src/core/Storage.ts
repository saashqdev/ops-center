/**
 * Browser-based storage for plugin data
 * Uses localStorage with namespacing
 */

export class Storage {
  private prefix: string;

  constructor(pluginId: string) {
    this.prefix = `ops_center_plugin_${pluginId}_`;
  }

  private getKey(key: string): string {
    return this.prefix + key;
  }

  /**
   * Set a value in storage
   */
  set<T = any>(key: string, value: T): void {
    try {
      const serialized = JSON.stringify(value);
      localStorage.setItem(this.getKey(key), serialized);
    } catch (error) {
      console.error(`[Storage] Failed to set ${key}:`, error);
      throw error;
    }
  }

  /**
   * Get a value from storage
   */
  get<T = any>(key: string, defaultValue?: T): T | undefined {
    try {
      const item = localStorage.getItem(this.getKey(key));
      
      if (item === null) {
        return defaultValue;
      }

      return JSON.parse(item) as T;
    } catch (error) {
      console.error(`[Storage] Failed to get ${key}:`, error);
      return defaultValue;
    }
  }

  /**
   * Remove a value from storage
   */
  remove(key: string): void {
    localStorage.removeItem(this.getKey(key));
  }

  /**
   * Check if key exists
   */
  has(key: string): boolean {
    return localStorage.getItem(this.getKey(key)) !== null;
  }

  /**
   * Get all keys for this plugin
   */
  keys(): string[] {
    const keys: string[] = [];
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.prefix)) {
        keys.push(key.substring(this.prefix.length));
      }
    }
    
    return keys;
  }

  /**
   * Clear all plugin data
   */
  clear(): void {
    const keys = this.keys();
    keys.forEach(key => this.remove(key));
  }

  /**
   * Get storage size in bytes
   */
  getSize(): number {
    let size = 0;
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.prefix)) {
        const value = localStorage.getItem(key);
        size += key.length + (value?.length || 0);
      }
    }
    
    return size;
  }
}

export default Storage;
