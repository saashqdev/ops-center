/**
 * API Client for accessing Ops-Center APIs from browser
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

export interface APIClientConfig {
  baseURL?: string;
  apiKey?: string;
  token?: string;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

export interface Device {
  id: string;
  name: string;
  type: string;
  status: string;
  [key: string]: any;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  [key: string]: any;
}

export interface Organization {
  id: string;
  name: string;
  [key: string]: any;
}

export interface Alert {
  id: string;
  device_id?: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  status: 'active' | 'acknowledged' | 'resolved';
  [key: string]: any;
}

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  [key: string]: any;
}

/**
 * Main API Client
 */
export class APIClient {
  private client: AxiosInstance;

  constructor(config: APIClientConfig = {}) {
    const baseURL = config.baseURL || this.getDefaultBaseURL();
    
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth interceptor
    this.client.interceptors.request.use((config) => {
      const token = this.getAuthToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  private getDefaultBaseURL(): string {
    // In browser, use relative URL
    if (typeof window !== 'undefined') {
      return window.location.origin + '/api';
    }
    return 'http://localhost:8000/api';
  }

  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      // Try to get from localStorage or cookies
      return localStorage.getItem('ops_center_token') || 
             sessionStorage.getItem('ops_center_token');
    }
    return null;
  }

  // ==================== HTTP Methods ====================

  async get<T = any>(endpoint: string, params?: any): Promise<T> {
    const response = await this.client.get(endpoint, { params });
    return response.data;
  }

  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    const response = await this.client.post(endpoint, data);
    return response.data;
  }

  async put<T = any>(endpoint: string, data?: any): Promise<T> {
    const response = await this.client.put(endpoint, data);
    return response.data;
  }

  async patch<T = any>(endpoint: string, data?: any): Promise<T> {
    const response = await this.client.patch(endpoint, data);
    return response.data;
  }

  async delete<T = any>(endpoint: string): Promise<T> {
    const response = await this.client.delete(endpoint);
    return response.data;
  }

  // ==================== Devices API ====================

  async getDevices(params?: PaginationParams & { status?: string }): Promise<Device[]> {
    return this.get('/devices', params);
  }

  async getDevice(id: string): Promise<Device> {
    return this.get(`/devices/${id}`);
  }

  async createDevice(data: Partial<Device>): Promise<Device> {
    return this.post('/devices', data);
  }

  async updateDevice(id: string, data: Partial<Device>): Promise<Device> {
    return this.put(`/devices/${id}`, data);
  }

  async deleteDevice(id: string): Promise<void> {
    return this.delete(`/devices/${id}`);
  }

  async getDeviceStatus(id: string): Promise<{ status: string }> {
    return this.get(`/devices/${id}/status`);
  }

  async getDeviceMetrics(id: string, params?: { start?: string; end?: string }): Promise<any> {
    return this.get(`/devices/${id}/metrics`, params);
  }

  // ==================== Users API ====================

  async getUsers(params?: PaginationParams): Promise<User[]> {
    return this.get('/users', params);
  }

  async getUser(id: string): Promise<User> {
    return this.get(`/users/${id}`);
  }

  async getCurrentUser(): Promise<User> {
    return this.get('/users/me');
  }

  async createUser(data: Partial<User>): Promise<User> {
    return this.post('/users', data);
  }

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    return this.put(`/users/${id}`, data);
  }

  // ==================== Organizations API ====================

  async getOrganizations(params?: PaginationParams): Promise<Organization[]> {
    return this.get('/organizations', params);
  }

  async getOrganization(id: string): Promise<Organization> {
    return this.get(`/organizations/${id}`);
  }

  async createOrganization(data: Partial<Organization>): Promise<Organization> {
    return this.post('/organizations', data);
  }

  // ==================== Alerts API ====================

  async getAlerts(params?: PaginationParams & { 
    severity?: string; 
    status?: string;
    device_id?: string;
  }): Promise<Alert[]> {
    return this.get('/alerts', params);
  }

  async getAlert(id: string): Promise<Alert> {
    return this.get(`/alerts/${id}`);
  }

  async createAlert(data: Partial<Alert>): Promise<Alert> {
    return this.post('/alerts', data);
  }

  async acknowledgeAlert(id: string): Promise<Alert> {
    return this.post(`/alerts/${id}/acknowledge`);
  }

  async resolveAlert(id: string): Promise<Alert> {
    return this.post(`/alerts/${id}/resolve`);
  }

  // ==================== Webhooks API ====================

  async getWebhooks(params?: PaginationParams): Promise<Webhook[]> {
    return this.get('/webhooks', params);
  }

  async createWebhook(data: Partial<Webhook>): Promise<Webhook> {
    return this.post('/webhooks', data);
  }

  async deleteWebhook(id: string): Promise<void> {
    return this.delete(`/webhooks/${id}`);
  }

  // ==================== Plugin-specific APIs ====================

  /**
   * Call plugin's custom API endpoint
   */
  async callPluginAPI<T = any>(
    pluginId: string, 
    endpoint: string, 
    options?: AxiosRequestConfig
  ): Promise<T> {
    const url = `/plugins/${pluginId}${endpoint}`;
    const response = await this.client.request({ url, ...options });
    return response.data;
  }

  /**
   * Get plugin configuration
   */
  async getPluginConfig(pluginId: string): Promise<Record<string, any>> {
    return this.get(`/plugins/${pluginId}/config`);
  }

  /**
   * Update plugin configuration
   */
  async updatePluginConfig(
    pluginId: string, 
    config: Record<string, any>
  ): Promise<Record<string, any>> {
    return this.put(`/plugins/${pluginId}/config`, config);
  }
}

export default APIClient;
