"""
Shopify API Client.

HTTP client for Shopify Admin API 2024-10.

Requirements: 5.6
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from credora.mcp_servers.errors import MCPError, MCPErrorType, classify_http_error
from credora.mcp_servers.logging import get_mcp_logger
from credora.mcp_servers.models.shopify import (
    Customer,
    Order,
    Product,
    SalesAnalytics,
    StoreInfo,
)


# Shopify Admin API configuration
SHOPIFY_API_VERSION = "2024-10"


class ShopifyClient:
    """
    HTTP client for Shopify Admin API.
    
    Handles authentication, request building, and response parsing
    for Shopify API calls.
    
    Requirements: 5.6
    """
    
    def __init__(
        self,
        access_token: str,
        shop_domain: str,
        timeout: float = 30.0,
    ):
        """Initialize the Shopify client.
        
        Args:
            access_token: OAuth access token for Shopify API
            shop_domain: Shop domain (e.g., mystore.myshopify.com)
            timeout: Request timeout in seconds
        """
        if not access_token:
            raise ValueError("access_token is required")
        if not shop_domain:
            raise ValueError("shop_domain is required")
        
        self._access_token = access_token
        self._shop_domain = self._normalize_domain(shop_domain)
        self._timeout = timeout
        self._logger = get_mcp_logger()
        self._base_url = f"https://{self._shop_domain}/admin/api/{SHOPIFY_API_VERSION}"
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize shop domain to standard format.
        
        Args:
            domain: Shop domain (may include https://, trailing slash, etc.)
            
        Returns:
            Normalized domain (e.g., mystore.myshopify.com)
        """
        # Remove protocol if present
        domain = domain.replace("https://", "").replace("http://", "")
        # Remove trailing slash
        domain = domain.rstrip("/")
        # Remove /admin path if present
        if "/admin" in domain:
            domain = domain.split("/admin")[0]
        return domain
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication.
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "X-Shopify-Access-Token": self._access_token,
            "Content-Type": "application/json",
        }
    
    def _build_url(self, endpoint: str) -> str:
        """Build full API URL for an endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL string (always HTTPS)
            
        Requirements: 7.2 (HTTPS enforcement)
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        
        url = f"{self._base_url}{endpoint}"
        
        # Verify HTTPS (should always be true given our base URL)
        if not url.startswith("https://"):
            raise ValueError("API URLs must use HTTPS")
        
        return url

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Shopify API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            Parsed JSON response
            
        Raises:
            MCPError: If request fails
        """
        url = self._build_url(endpoint)
        headers = self._get_headers()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data if data else None,
                )
                
                # Check for errors
                if response.status_code >= 400:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass
                    
                    # Log the error
                    self._logger.log_api_error(
                        error_type=MCPErrorType.API_ERROR.value,
                        message=f"Shopify API error: {response.status_code}",
                        platform="shopify",
                        request_method=method,
                        request_url=url,
                        status_code=response.status_code,
                        details=error_data,
                    )
                    
                    # Classify and raise appropriate error
                    raise classify_http_error(response.status_code, response.text)
                
                return response.json()
                
            except httpx.TimeoutException as e:
                self._logger.log_api_error(
                    error_type=MCPErrorType.NETWORK_ERROR.value,
                    message=f"Request timeout: {str(e)}",
                    platform="shopify",
                    request_method=method,
                    request_url=url,
                )
                raise MCPError.network_error(
                    message=f"Request timeout: {str(e)}",
                    endpoint=endpoint,
                )
            except httpx.RequestError as e:
                self._logger.log_api_error(
                    error_type=MCPErrorType.NETWORK_ERROR.value,
                    message=f"Network error: {str(e)}",
                    platform="shopify",
                    request_method=method,
                    request_url=url,
                )
                raise MCPError.network_error(
                    message=f"Network error: {str(e)}",
                    endpoint=endpoint,
                )

    async def get_store_info(self) -> StoreInfo:
        """Get store information.
        
        Returns:
            StoreInfo object
            
        Requirements: 5.1
        """
        endpoint = "/shop.json"
        response = await self._make_request("GET", endpoint)
        return StoreInfo.from_api_response(response)
    
    async def get_orders(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: str = "any",
        limit: int = 50,
    ) -> List[Order]:
        """Get orders with filtering.
        
        Args:
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            status: Order status filter (any, open, closed, cancelled)
            limit: Maximum number of orders to return
            
        Returns:
            List of Order objects
            
        Requirements: 5.2
        """
        endpoint = "/orders.json"
        params: Dict[str, Any] = {
            "limit": min(limit, 250),  # Shopify max is 250
            "status": status,
        }
        
        # Add date filters
        if date_from:
            params["created_at_min"] = f"{date_from}T00:00:00Z"
        if date_to:
            params["created_at_max"] = f"{date_to}T23:59:59Z"
        
        response = await self._make_request("GET", endpoint, params=params)
        
        orders = []
        for item in response.get("orders", []):
            order = Order.from_api_response(item)
            # Apply date filtering (double-check since API might not filter exactly)
            if date_from or date_to:
                order_date = order.created_at.date() if isinstance(order.created_at, datetime) else None
                if order_date:
                    if date_from:
                        from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                        if order_date < from_date:
                            continue
                    if date_to:
                        to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                        if order_date > to_date:
                            continue
            orders.append(order)
        
        return orders

    async def get_products(
        self,
        limit: int = 50,
    ) -> List[Product]:
        """Get products with inventory levels.
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            List of Product objects
            
        Requirements: 5.3
        """
        endpoint = "/products.json"
        params: Dict[str, Any] = {
            "limit": min(limit, 250),  # Shopify max is 250
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        
        products = []
        for item in response.get("products", []):
            products.append(Product.from_api_response(item))
        
        return products
    
    async def get_customers(
        self,
        segment: str = "all",
        limit: int = 50,
    ) -> List[Customer]:
        """Get customers with optional segment filtering.
        
        Args:
            segment: Customer segment filter (all, repeat, new, vip)
            limit: Maximum number of customers to return
            
        Returns:
            List of Customer objects
            
        Requirements: 5.4
        """
        endpoint = "/customers.json"
        params: Dict[str, Any] = {
            "limit": min(limit, 250),  # Shopify max is 250
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        
        customers = []
        for item in response.get("customers", []):
            customer = Customer.from_api_response(item)
            
            # Apply segment filtering
            if segment != "all":
                if segment == "repeat" and customer.orders_count < 2:
                    continue
                elif segment == "new" and customer.orders_count > 1:
                    continue
                elif segment == "vip" and customer.total_spent < 1000:
                    continue
            
            customers.append(customer)
        
        return customers
    
    async def get_analytics(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> SalesAnalytics:
        """Get sales analytics for a date range.
        
        Args:
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            SalesAnalytics object
            
        Requirements: 5.5
        """
        # Fetch orders for the date range
        orders = await self.get_orders(
            date_from=date_from,
            date_to=date_to,
            status="any",
            limit=250,
        )
        
        # Calculate analytics from orders
        return SalesAnalytics.from_orders(orders)
    
    def get_api_base_url(self) -> str:
        """Get the base URL for API requests.
        
        Returns:
            Base URL string (always HTTPS)
            
        Requirements: 7.2
        """
        return self._base_url
