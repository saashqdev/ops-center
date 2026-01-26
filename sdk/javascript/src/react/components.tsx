/**
 * React components for Ops-Center plugins
 */

import React, { ReactNode } from 'react';
import { Plugin } from '../core/Plugin';
import { PluginContext } from './hooks';

// ==================== PluginProvider ====================

export interface PluginProviderProps {
  plugin: Plugin;
  children: ReactNode;
}

export function PluginProvider({ plugin, children }: PluginProviderProps) {
  return (
    <PluginContext.Provider value={plugin}>
      {children}
    </PluginContext.Provider>
  );
}

// ==================== Slot Component ====================

export interface SlotProps {
  name: string;
  fallback?: ReactNode;
  className?: string;
}

/**
 * Renders all components registered for a slot
 */
export function Slot({ name, fallback, className }: SlotProps) {
  const plugin = React.useContext(PluginContext);
  
  if (!plugin) {
    return <>{fallback}</>;
  }

  const components = plugin.getSlotComponents(name);

  if (components.length === 0) {
    return <>{fallback}</>;
  }

  return (
    <div className={className} data-slot={name}>
      {components.map((Component, index) => (
        <Component key={index} />
      ))}
    </div>
  );
}

// ==================== Error Boundary ====================

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error) => ReactNode);
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.props.onError?.(error, errorInfo);
    console.error('[Plugin Error]', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error!);
      }
      
      return this.props.fallback || (
        <div style={{ padding: '20px', border: '1px solid #f00', borderRadius: '4px' }}>
          <h3>Plugin Error</h3>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}

// ==================== Loading Component ====================

export interface LoadingProps {
  text?: string;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

export function Loading({ text = 'Loading...', size = 'medium', className = '' }: LoadingProps) {
  const sizeStyles = {
    small: { width: '20px', height: '20px', borderWidth: '2px' },
    medium: { width: '40px', height: '40px', borderWidth: '3px' },
    large: { width: '60px', height: '60px', borderWidth: '4px' },
  };

  return (
    <div className={`loading ${className}`} style={{ textAlign: 'center', padding: '20px' }}>
      <div
        style={{
          ...sizeStyles[size],
          border: `${sizeStyles[size].borderWidth} solid #f3f3f3`,
          borderTop: `${sizeStyles[size].borderWidth} solid #3498db`,
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          margin: '0 auto',
        }}
      />
      {text && <p style={{ marginTop: '10px' }}>{text}</p>}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// ==================== Empty State Component ====================

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title = 'No data',
  description,
  icon,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`empty-state ${className}`} style={{ textAlign: 'center', padding: '40px' }}>
      {icon && <div style={{ fontSize: '48px', marginBottom: '16px' }}>{icon}</div>}
      <h3 style={{ margin: '0 0 8px' }}>{title}</h3>
      {description && <p style={{ color: '#666', margin: '0 0 16px' }}>{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}

// ==================== Card Component ====================

export interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function Card({ title, subtitle, children, actions, className = '', style = {} }: CardProps) {
  return (
    <div
      className={`card ${className}`}
      style={{
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        padding: '20px',
        backgroundColor: '#fff',
        ...style,
      }}
    >
      {(title || subtitle || actions) && (
        <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            {title && <h3 style={{ margin: '0 0 4px' }}>{title}</h3>}
            {subtitle && <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>{subtitle}</p>}
          </div>
          {actions && <div>{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

// ==================== Badge Component ====================

export interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const colors = {
    default: { bg: '#f5f5f5', color: '#333' },
    primary: { bg: '#3498db', color: '#fff' },
    success: { bg: '#2ecc71', color: '#fff' },
    warning: { bg: '#f39c12', color: '#fff' },
    error: { bg: '#e74c3c', color: '#fff' },
    info: { bg: '#9b59b6', color: '#fff' },
  };

  return (
    <span
      className={`badge badge-${variant} ${className}`}
      style={{
        display: 'inline-block',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 'bold',
        backgroundColor: colors[variant].bg,
        color: colors[variant].color,
      }}
    >
      {children}
    </span>
  );
}

// ==================== Button Component ====================

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  size?: 'small' | 'medium' | 'large';
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({
  children,
  variant = 'primary',
  size = 'medium',
  loading = false,
  icon,
  disabled,
  className = '',
  style = {},
  ...props
}: ButtonProps) {
  const colors = {
    primary: { bg: '#3498db', hover: '#2980b9' },
    secondary: { bg: '#95a5a6', hover: '#7f8c8d' },
    success: { bg: '#2ecc71', hover: '#27ae60' },
    warning: { bg: '#f39c12', hover: '#e67e22' },
    error: { bg: '#e74c3c', hover: '#c0392b' },
  };

  const sizes = {
    small: { padding: '6px 12px', fontSize: '12px' },
    medium: { padding: '10px 20px', fontSize: '14px' },
    large: { padding: '14px 28px', fontSize: '16px' },
  };

  return (
    <button
      className={`button button-${variant} button-${size} ${className}`}
      disabled={disabled || loading}
      style={{
        ...sizes[size],
        backgroundColor: colors[variant].bg,
        color: '#fff',
        border: 'none',
        borderRadius: '4px',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled || loading ? 0.6 : 1,
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        ...style,
      }}
      onMouseEnter={(e) => {
        if (!disabled && !loading) {
          e.currentTarget.style.backgroundColor = colors[variant].hover;
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = colors[variant].bg;
      }}
      {...props}
    >
      {loading && <span>⏳</span>}
      {!loading && icon && <span>{icon}</span>}
      {children}
    </button>
  );
}

// ==================== Alert Component ====================

export interface AlertProps {
  type?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: ReactNode;
  onClose?: () => void;
  className?: string;
}

export function Alert({
  type = 'info',
  title,
  children,
  onClose,
  className = '',
}: AlertProps) {
  const colors = {
    info: { bg: '#d1ecf1', border: '#bee5eb', color: '#0c5460' },
    success: { bg: '#d4edda', border: '#c3e6cb', color: '#155724' },
    warning: { bg: '#fff3cd', border: '#ffeaa7', color: '#856404' },
    error: { bg: '#f8d7da', border: '#f5c6cb', color: '#721c24' },
  };

  return (
    <div
      className={`alert alert-${type} ${className}`}
      style={{
        padding: '12px 16px',
        borderRadius: '4px',
        backgroundColor: colors[type].bg,
        border: `1px solid ${colors[type].border}`,
        color: colors[type].color,
        position: 'relative',
      }}
    >
      {onClose && (
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '20px',
            color: colors[type].color,
          }}
        >
          ×
        </button>
      )}
      {title && <strong style={{ display: 'block', marginBottom: '4px' }}>{title}</strong>}
      <div>{children}</div>
    </div>
  );
}
