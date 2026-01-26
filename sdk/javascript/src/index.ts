/**
 * @ops-center/plugin-sdk
 * 
 * JavaScript/React SDK for building Ops-Center plugins
 */

// Core
export { Plugin } from './core/Plugin';
export type { PluginMetadata, PluginManifest, SlotRegistration, RouteRegistration, HookRegistration } from './core/Plugin';

export { APIClient } from './core/APIClient';
export type { APIClientConfig, Device, User, Organization, Alert, Webhook } from './core/APIClient';

export { Storage } from './core/Storage';
export { Config } from './core/Config';
export type { ConfigSchema, ConfigProperty } from './core/Config';

// Default export
export { Plugin as default } from './core/Plugin';
