"""
API Client for accessing Ops-Center APIs from plugins
"""

import httpx
from typing import Dict, List, Any, Optional
from uuid import UUID


class APIClient:
    """
    Client for accessing Ops-Center REST APIs
    
    Example:
        ```python
        api = APIClient(base_url="https://api.ops-center.com", api_key="key")
        
        # Get devices
        devices = await api.devices.list()
        
        # Get specific device
        device = await api.devices.get("device-id")
        
        # Create device
        new_device = await api.devices.create({
            "name": "New Device",
            "type": "sensor"
        })
        ```
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "OpsCenter-Plugin-SDK/0.1.0"
            },
            timeout=timeout
        )
        
        # Resource accessors
        self.devices = DevicesAPI(self)
        self.users = UsersAPI(self)
        self.orgs = OrganizationsAPI(self)
        self.webhooks = WebhooksAPI(self)
        self.alerts = AlertsAPI(self)
    
    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Ops-Center API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/api/v1/devices")
            **kwargs: Additional arguments for httpx
        
        Returns:
            Response JSON
        """
        response = await self._client.request(method, endpoint, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST request"""
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT request"""
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request"""
        return await self.request("DELETE", endpoint, **kwargs)
    
    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()


class DevicesAPI:
    """Device management API"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List devices"""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        
        response = await self.client.get("/api/v1/devices", params=params)
        return response.get("devices", [])
    
    async def get(self, device_id: str) -> Dict[str, Any]:
        """Get device by ID"""
        return await self.client.get(f"/api/v1/devices/{device_id}")
    
    async def create(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new device"""
        return await self.client.post("/api/v1/devices", json=device_data)
    
    async def update(self, device_id: str, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update device"""
        return await self.client.put(f"/api/v1/devices/{device_id}", json=device_data)
    
    async def delete(self, device_id: str) -> Dict[str, Any]:
        """Delete device"""
        return await self.client.delete(f"/api/v1/devices/{device_id}")
    
    async def get_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status"""
        return await self.client.get(f"/api/v1/devices/{device_id}/status")


class UsersAPI:
    """User management API"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    async def list(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """List users"""
        response = await self.client.get(
            "/api/v1/users",
            params={"page": page, "page_size": page_size}
        )
        return response.get("users", [])
    
    async def get(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID"""
        return await self.client.get(f"/api/v1/users/{user_id}")
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user"""
        return await self.client.post("/api/v1/users", json=user_data)
    
    async def update(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user"""
        return await self.client.put(f"/api/v1/users/{user_id}", json=user_data)


class OrganizationsAPI:
    """Organization management API"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    async def list(self) -> List[Dict[str, Any]]:
        """List organizations"""
        response = await self.client.get("/api/v1/orgs")
        return response.get("organizations", [])
    
    async def get(self, org_id: str) -> Dict[str, Any]:
        """Get organization"""
        return await self.client.get(f"/api/v1/orgs/{org_id}")
    
    async def create(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create organization"""
        return await self.client.post("/api/v1/orgs", json=org_data)


class WebhooksAPI:
    """Webhook management API"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    async def list(self) -> List[Dict[str, Any]]:
        """List webhooks"""
        response = await self.client.get("/api/v1/webhooks")
        return response.get("webhooks", [])
    
    async def create(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create webhook"""
        return await self.client.post("/api/v1/webhooks", json=webhook_data)
    
    async def delete(self, webhook_id: str) -> Dict[str, Any]:
        """Delete webhook"""
        return await self.client.delete(f"/api/v1/webhooks/{webhook_id}")


class AlertsAPI:
    """Alert management API"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    async def list(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List alerts"""
        params = {}
        if severity:
            params["severity"] = severity
        if status:
            params["status"] = status
        
        response = await self.client.get("/api/v1/alerts", params=params)
        return response.get("alerts", [])
    
    async def get(self, alert_id: str) -> Dict[str, Any]:
        """Get alert"""
        return await self.client.get(f"/api/v1/alerts/{alert_id}")
    
    async def create(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert"""
        return await self.client.post("/api/v1/alerts", json=alert_data)
    
    async def acknowledge(self, alert_id: str) -> Dict[str, Any]:
        """Acknowledge alert"""
        return await self.client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
