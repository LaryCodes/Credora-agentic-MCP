"""
Shopify MCP Server.

MCP Server for Shopify e-commerce integration.

Requirements: 1.1, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

from typing import Any, Dict, List, Optional

from credora.mcp_servers.base import BaseMCPServer
from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.errors import MCPError, MCPErrorType
from credora.mcp_servers.shopify_client import ShopifyClient
from credora.mcp_servers.models.shopify import (
    Customer,
    Order,
    Product,
    SalesAnalytics,
    StoreInfo,
)


# Tool input schemas
GET_STORE_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
    },
    "required": ["user_id"],
}

GET_ORDERS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "date_from": {
            "type": "string",
            "description": "Start date in YYYY-MM-DD format",
        },
        "date_to": {
            "type": "string",
            "description": "End date in YYYY-MM-DD format",
        },
        "status": {
            "type": "string",
            "description": "Order status filter (any, open, closed, cancelled)",
            "default": "any",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of orders to return",
            "default": 50,
        },
    },
    "required": ["user_id"],
}

GET_PRODUCTS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of products to return",
            "default": 50,
        },
    },
    "required": ["user_id"],
}

GET_CUSTOMERS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "segment": {
            "type": "string",
            "description": "Customer segment filter (all, repeat, new, vip)",
            "default": "all",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of customers to return",
            "default": 50,
        },
    },
    "required": ["user_id"],
}

GET_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "date_from": {
            "type": "string",
            "description": "Start date in YYYY-MM-DD format",
        },
        "date_to": {
            "type": "string",
            "description": "End date in YYYY-MM-DD format",
        },
    },
    "required": ["user_id"],
}


class ShopifyMCPServer(BaseMCPServer):
    """
    MCP Server for Shopify e-commerce integration.
    
    Exposes tools for fetching store info, orders, products,
    customers, and sales analytics from the Shopify Admin API.
    
    Requirements: 1.1, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
    """
    
    name = "shopify"
    version = "1.0.0"
    api_version = "2024-10"
    
    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
    ):
        """Initialize the Shopify MCP Server.
        
        Args:
            connection_manager: Optional ConnectionManager for OAuth tokens
        """
        self._connection_manager = connection_manager or ConnectionManager()
        super().__init__()
    
    def _register_tools(self) -> None:
        """Register Shopify tools.
        
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        self.register_tool(
            name="shopify_get_store_info",
            description="Get Shopify store information including name, domain, and settings",
            input_schema=GET_STORE_INFO_SCHEMA,
            handler=self._get_store_info,
        )
        
        self.register_tool(
            name="shopify_get_orders",
            description="Get Shopify orders with date and status filtering",
            input_schema=GET_ORDERS_SCHEMA,
            handler=self._get_orders,
        )
        
        self.register_tool(
            name="shopify_get_products",
            description="Get Shopify products with inventory levels",
            input_schema=GET_PRODUCTS_SCHEMA,
            handler=self._get_products,
        )
        
        self.register_tool(
            name="shopify_get_customers",
            description="Get Shopify customers with segment filtering",
            input_schema=GET_CUSTOMERS_SCHEMA,
            handler=self._get_customers,
        )
        
        self.register_tool(
            name="shopify_get_analytics",
            description="Get Shopify sales analytics including revenue, AOV, and top products",
            input_schema=GET_ANALYTICS_SCHEMA,
            handler=self._get_analytics,
        )

    async def _get_client(self, user_id: str) -> ShopifyClient:
        """Get an authenticated Shopify client for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Authenticated ShopifyClient
            
        Raises:
            MCPError: If authentication fails
        """
        try:
            access_token = await self._connection_manager.get_access_token(
                platform="shopify",
                user_id=user_id,
            )
            
            # Get shop domain from connection metadata
            shop_domain = await self._connection_manager.get_platform_metadata(
                platform="shopify",
                user_id=user_id,
                key="shop_domain",
            )
            
            if not shop_domain:
                raise MCPError(
                    error_type=MCPErrorType.AUTH_REQUIRED,
                    message="Shopify shop domain not found. Please reconnect your Shopify store.",
                    recoverable=False,
                )
            
            return ShopifyClient(
                access_token=access_token,
                shop_domain=shop_domain,
            )
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"Failed to get Shopify access token: {str(e)}",
                recoverable=False,
            )
    
    async def _get_store_info(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get store information.
        
        Args:
            user_id: User identifier for authentication
            
        Returns:
            Store info dictionary
            
        Requirements: 5.1
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        client = await self._get_client(user_id)
        store_info = await client.get_store_info()
        
        return store_info.to_dict()
    
    async def _get_orders(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: str = "any",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get orders with filtering.
        
        Args:
            user_id: User identifier for authentication
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            status: Order status filter
            limit: Maximum number of orders
            
        Returns:
            List of order dictionaries
            
        Requirements: 5.2
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        # Validate status
        valid_statuses = ["any", "open", "closed", "cancelled"]
        if status not in valid_statuses:
            raise MCPError.invalid_params(
                f"status must be one of: {', '.join(valid_statuses)}"
            )
        
        client = await self._get_client(user_id)
        orders = await client.get_orders(
            date_from=date_from,
            date_to=date_to,
            status=status,
            limit=limit,
        )
        
        return [order.to_dict() for order in orders]

    async def _get_products(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get products with inventory.
        
        Args:
            user_id: User identifier for authentication
            limit: Maximum number of products
            
        Returns:
            List of product dictionaries
            
        Requirements: 5.3
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        client = await self._get_client(user_id)
        products = await client.get_products(limit=limit)
        
        return [product.to_dict() for product in products]
    
    async def _get_customers(
        self,
        user_id: str,
        segment: str = "all",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get customers with segment filtering.
        
        Args:
            user_id: User identifier for authentication
            segment: Customer segment filter
            limit: Maximum number of customers
            
        Returns:
            List of customer dictionaries
            
        Requirements: 5.4
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        # Validate segment
        valid_segments = ["all", "repeat", "new", "vip"]
        if segment not in valid_segments:
            raise MCPError.invalid_params(
                f"segment must be one of: {', '.join(valid_segments)}"
            )
        
        client = await self._get_client(user_id)
        customers = await client.get_customers(segment=segment, limit=limit)
        
        return [customer.to_dict() for customer in customers]
    
    async def _get_analytics(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get sales analytics.
        
        Args:
            user_id: User identifier for authentication
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            Analytics dictionary
            
        Requirements: 5.5
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        client = await self._get_client(user_id)
        analytics = await client.get_analytics(
            date_from=date_from,
            date_to=date_to,
        )
        
        return analytics.to_dict()
    
    def _validate_date_format(self, date_str: str, field_name: str) -> None:
        """Validate date string format.
        
        Args:
            date_str: Date string to validate
            field_name: Field name for error message
            
        Raises:
            MCPError: If date format is invalid
        """
        import re
        
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise MCPError.invalid_params(
                f"{field_name} must be in YYYY-MM-DD format"
            )
        
        # Validate it's a real date
        try:
            from datetime import datetime
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise MCPError.invalid_params(
                f"{field_name} is not a valid date"
            )
    
    def get_api_base_url(self) -> str:
        """Get the base URL for Shopify API requests.
        
        Returns:
            Base URL string (always HTTPS)
            
        Requirements: 7.2
        """
        return f"https://{{shop_domain}}/admin/api/{self.api_version}"
