/**
 * @ops-center/plugin-sdk/react
 * 
 * React hooks and components for plugin development
 */

// Context and Provider
export { PluginContext, PluginProvider } from './react/components';

// Hooks
export {
  usePlugin,
  useAPI,
  useDevices,
  useDevice,
  useDeviceMetrics,
  useUsers,
  useUser,
  useCurrentUser,
  useAlerts,
  useAlert,
  useStorage,
  useConfig,
  useAllConfig,
  useEvent,
  useEmit,
  usePluginMetadata,
  usePluginAPI,
  usePluginStorage,
  usePluginConfig,
  useMutation,
  useInterval,
  useDebounce,
  usePrevious,
} from './react/hooks';

export type { UseAPIOptions, UseMutationOptions } from './react/hooks';

// Components
export {
  Slot,
  ErrorBoundary,
  Loading,
  EmptyState,
  Card,
  Badge,
  Button,
  Alert,
} from './react/components';

export type {
  PluginProviderProps,
  SlotProps,
  ErrorBoundaryProps,
  LoadingProps,
  EmptyStateProps,
  CardProps,
  BadgeProps,
  ButtonProps,
  AlertProps,
} from './react/components';
