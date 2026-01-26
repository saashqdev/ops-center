/**
 * React hooks for Ops-Center plugins
 */

import { useEffect, useState, useCallback, useMemo, useContext, createContext } from 'react';
import { Plugin } from '../core/Plugin';
import { APIClient } from '../core/APIClient';
import { Storage } from '../core/Storage';
import { Config } from '../core/Config';

// ==================== Plugin Context ====================

export const PluginContext = createContext<Plugin | null>(null);

export function usePlugin(): Plugin {
  const plugin = useContext(PluginContext);
  
  if (!plugin) {
    throw new Error('usePlugin must be used within PluginProvider');
  }
  
  return plugin;
}

// ==================== API Hooks ====================

export interface UseAPIOptions {
  initialData?: any;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

export function useAPI<T = any>(
  fetcher: (api: APIClient) => Promise<T>,
  dependencies: any[] = [],
  options: UseAPIOptions = {}
) {
  const plugin = usePlugin();
  const [data, setData] = useState<T | undefined>(options.initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const { onSuccess, onError, enabled = true } = options;

  const fetchData = useCallback(async () => {
    if (!enabled) return;
    
    setLoading(true);
    setError(null);

    try {
      const result = await fetcher(plugin.api);
      setData(result);
      onSuccess?.(result);
    } catch (err) {
      const error = err as Error;
      setError(error);
      onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [plugin.api, enabled, ...dependencies]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const refetch = useCallback(() => {
    return fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch };
}

// ==================== Device Hooks ====================

export function useDevices(params?: { status?: string }) {
  return useAPI(
    api => api.getDevices(params),
    [params?.status]
  );
}

export function useDevice(id?: string) {
  return useAPI(
    api => id ? api.getDevice(id) : Promise.resolve(null),
    [id],
    { enabled: !!id }
  );
}

export function useDeviceMetrics(id?: string, params?: { start?: string; end?: string }) {
  return useAPI(
    api => id ? api.getDeviceMetrics(id, params) : Promise.resolve(null),
    [id, params?.start, params?.end],
    { enabled: !!id }
  );
}

// ==================== User Hooks ====================

export function useUsers() {
  return useAPI(api => api.getUsers());
}

export function useUser(id?: string) {
  return useAPI(
    api => id ? api.getUser(id) : Promise.resolve(null),
    [id],
    { enabled: !!id }
  );
}

export function useCurrentUser() {
  return useAPI(api => api.getCurrentUser());
}

// ==================== Alert Hooks ====================

export function useAlerts(params?: { severity?: string; status?: string; device_id?: string }) {
  return useAPI(
    api => api.getAlerts(params),
    [params?.severity, params?.status, params?.device_id]
  );
}

export function useAlert(id?: string) {
  return useAPI(
    api => id ? api.getAlert(id) : Promise.resolve(null),
    [id],
    { enabled: !!id }
  );
}

// ==================== Storage Hooks ====================

export function useStorage<T = any>(key: string, defaultValue?: T) {
  const plugin = usePlugin();
  const [value, setValue] = useState<T | undefined>(() => 
    plugin.storage.get(key, defaultValue)
  );

  const setStoredValue = useCallback((newValue: T | ((prev: T | undefined) => T)) => {
    const valueToStore = newValue instanceof Function ? newValue(value) : newValue;
    setValue(valueToStore);
    plugin.storage.set(key, valueToStore);
  }, [plugin.storage, key, value]);

  const removeValue = useCallback(() => {
    setValue(defaultValue);
    plugin.storage.remove(key);
  }, [plugin.storage, key, defaultValue]);

  return [value, setStoredValue, removeValue] as const;
}

// ==================== Config Hooks ====================

export function useConfig<T = any>(key: string, defaultValue?: T) {
  const plugin = usePlugin();
  const [value, setValue] = useState<T>(() => 
    plugin.config.get(key, defaultValue)
  );

  const setConfigValue = useCallback((newValue: T) => {
    setValue(newValue);
    plugin.config.set(key, newValue);
  }, [plugin.config, key]);

  // Listen for config changes
  useEffect(() => {
    const handler = (configKey: string, configValue: any) => {
      if (configKey === key) {
        setValue(configValue);
      }
    };

    plugin.events.on('config:change', handler);

    return () => {
      plugin.events.off('config:change', handler);
    };
  }, [plugin.events, key]);

  return [value, setConfigValue] as const;
}

export function useAllConfig() {
  const plugin = usePlugin();
  const [config, setConfig] = useState(() => plugin.config.all());

  // Listen for config changes
  useEffect(() => {
    const handler = () => {
      setConfig(plugin.config.all());
    };

    plugin.events.on('config:change', handler);

    return () => {
      plugin.events.off('config:change', handler);
    };
  }, [plugin.events, plugin.config]);

  return config;
}

// ==================== Event Hooks ====================

export function useEvent(event: string, handler: (...args: any[]) => void, deps: any[] = []) {
  const plugin = usePlugin();

  useEffect(() => {
    plugin.events.on(event, handler);

    return () => {
      plugin.events.off(event, handler);
    };
  }, [plugin.events, event, ...deps]);
}

export function useEmit() {
  const plugin = usePlugin();

  return useCallback((event: string, ...args: any[]) => {
    plugin.events.emit(event, ...args);
  }, [plugin.events]);
}

// ==================== Plugin State Hooks ====================

export function usePluginMetadata() {
  const plugin = usePlugin();
  return plugin.metadata;
}

export function usePluginAPI() {
  const plugin = usePlugin();
  return plugin.api;
}

export function usePluginStorage() {
  const plugin = usePlugin();
  return plugin.storage;
}

export function usePluginConfig() {
  const plugin = usePlugin();
  return plugin.config;
}

// ==================== Mutation Hooks ====================

export interface UseMutationOptions<T = any, V = any> {
  onSuccess?: (data: T, variables: V) => void;
  onError?: (error: Error, variables: V) => void;
  onSettled?: (data: T | undefined, error: Error | null, variables: V) => void;
}

export function useMutation<T = any, V = any>(
  mutationFn: (api: APIClient, variables: V) => Promise<T>,
  options: UseMutationOptions<T, V> = {}
) {
  const plugin = usePlugin();
  const [data, setData] = useState<T | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { onSuccess, onError, onSettled } = options;

  const mutate = useCallback(async (variables: V) => {
    setLoading(true);
    setError(null);

    try {
      const result = await mutationFn(plugin.api, variables);
      setData(result);
      onSuccess?.(result, variables);
      onSettled?.(result, null, variables);
      return result;
    } catch (err) {
      const error = err as Error;
      setError(error);
      onError?.(error, variables);
      onSettled?.(undefined, error, variables);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [plugin.api, mutationFn, onSuccess, onError, onSettled]);

  const reset = useCallback(() => {
    setData(undefined);
    setError(null);
  }, []);

  return { mutate, data, loading, error, reset };
}

// ==================== Interval Hook ====================

export function useInterval(callback: () => void, delay: number | null) {
  useEffect(() => {
    if (delay === null) return;

    const id = setInterval(callback, delay);

    return () => clearInterval(id);
  }, [callback, delay]);
}

// ==================== Debounce Hook ====================

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// ==================== Previous Value Hook ====================

export function usePrevious<T>(value: T): T | undefined {
  const [current, setCurrent] = useState(value);
  const [previous, setPrevious] = useState<T>();

  if (value !== current) {
    setPrevious(current);
    setCurrent(value);
  }

  return previous;
}
