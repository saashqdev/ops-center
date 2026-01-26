"""API client for Ops-Center CLI"""

import requests
from typing import Optional, Dict, Any
from requests.exceptions import RequestException


class APIClient:
    """HTTP client for Ops-Center API"""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Initialize API client
        
        Args:
            base_url: Base URL of Ops-Center API (e.g., http://localhost:8084)
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'ops-center-cli/1.0.0'
        })
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (e.g., /api/v1/users)
            params: Query parameters
            json: JSON body
            data: Form data
            
        Returns:
            Response JSON
            
        Raises:
            Exception: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                timeout=self.timeout
            )
            
            # Raise for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            
            # Return JSON if response has content
            if response.content:
                return response.json()
            return {}
            
        except RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('detail', str(e))
                except:
                    error_msg = e.response.text or str(e)
                raise Exception(f"API Error ({e.response.status_code}): {error_msg}")
            else:
                raise Exception(f"Connection Error: {e}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request"""
        return self._make_request('POST', endpoint, json=json)
    
    def put(self, endpoint: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request"""
        return self._make_request('PUT', endpoint, json=json)
    
    def patch(self, endpoint: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PATCH request"""
        return self._make_request('PATCH', endpoint, json=json)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request"""
        return self._make_request('DELETE', endpoint)
