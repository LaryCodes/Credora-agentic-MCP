"""MCP Server Router for Data Fetcher.

Routes data requests to the appropriate MCP server based on platform.

Requirements: 1.4
"""

from typing import Any, Dict, List, Optional

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.meta_ads import MetaAdsMCPServer
from credora.mcp_servers.google_ads import GoogleAdsMCPServer
from credora.mcp_servers.shopify import ShopifyMCPServer
from credora.mcp_servers.errors import MCPError, MCPErrorType


# Platform to MCP server mapping
PLATFORM_MCP_MAPPING = {
    "meta": "meta-ads",
    "google": "google-ads",
    "shopify": "shopify",
}

# Supported MCP platforms
MCP_PLATFORMS = {"meta", "google", "shopify"}


class MCPRouter:
    """Routes requests to appropriate MCP servers based on platform.
    
    Requirements: 1.4
    """
    
    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        """Initialize the MCP router.
        
        Args:
            connection_manager: Optional shared ConnectionManager instance
        """
        self._connection_manager = connection_manager or ConnectionManager()
        self._servers: Dict[str, Any] = {}
        self._initialize_servers()
    
    def _initialize_servers(self) -> None:
        """Initialize MCP server instances."""
        self._servers["meta"] = MetaAdsMCPServer(
            connection_manager=self._connection_manager
        )
        self._servers["google"] = GoogleAdsMCPServer(
            connection_manager=self._connection_manager
        )
        self._servers["shopify"] = ShopifyMCPServer(
            connection_manager=self._connection_manager
        )
    
    def get_server(self, platform: str) -> Any:
        """Get the MCP server for a platform.
        
        Args:
            platform: Platform name (meta, google, shopify)
            
        Returns:
            MCP server instance
            
        Raises:
            MCPError: If platform is not supported
        """
        platform_lower = platform.lower().strip()
        if platform_lower not in MCP_PLATFORMS:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Unsupported MCP platform: {platform}. Supported: {', '.join(MCP_PLATFORMS)}",
                recoverable=False,
            )
        return self._servers[platform_lower]
    
    def is_mcp_platform(self, platform: str) -> bool:
        """Check if a platform is supported by MCP servers.
        
        Args:
            platform: Platform name to check
            
        Returns:
            True if platform has MCP server support
        """
        return platform.lower().strip() in MCP_PLATFORMS
    
    async def fetch_campaigns(
        self,
        user_id: str,
        platform: str,
        account_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch campaigns from the appropriate MCP server.
        
        Args:
            user_id: User identifier
            platform: Platform name (meta, google)
            account_id: Account/customer ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            
        Returns:
            List of campaign data dictionaries
            
        Requirements: 1.4
        """
        platform_lower = platform.lower().strip()
        
        if platform_lower == "meta":
            server = self._servers["meta"]
            return await server._get_campaigns(
                user_id=user_id,
                account_id=account_id,
                date_from=date_from,
                date_to=date_to,
            )
        elif platform_lower == "google":
            server = self._servers["google"]
            return await server._get_campaigns(
                user_id=user_id,
                customer_id=account_id,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Campaign data not available for platform: {platform}",
                recoverable=False,
            )
    

    async def fetch_orders(
        self,
        user_id: str,
        platform: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: str = "any",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch orders from Shopify MCP server.
        
        Args:
            user_id: User identifier
            platform: Platform name (shopify)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            status: Order status filter
            limit: Maximum orders to return
            
        Returns:
            List of order data dictionaries
            
        Requirements: 1.4
        """
        platform_lower = platform.lower().strip()
        
        if platform_lower == "shopify":
            server = self._servers["shopify"]
            return await server._get_orders(
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                status=status,
                limit=limit,
            )
        else:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Order data not available for platform: {platform}",
                recoverable=False,
            )
    
    async def fetch_products(
        self,
        user_id: str,
        platform: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch products from Shopify MCP server.
        
        Args:
            user_id: User identifier
            platform: Platform name (shopify)
            limit: Maximum products to return
            
        Returns:
            List of product data dictionaries
            
        Requirements: 1.4
        """
        platform_lower = platform.lower().strip()
        
        if platform_lower == "shopify":
            server = self._servers["shopify"]
            return await server._get_products(
                user_id=user_id,
                limit=limit,
            )
        else:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Product data not available for platform: {platform}",
                recoverable=False,
            )
    
    async def fetch_customers(
        self,
        user_id: str,
        platform: str,
        segment: str = "all",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch customers from Shopify MCP server.
        
        Args:
            user_id: User identifier
            platform: Platform name (shopify)
            segment: Customer segment filter
            limit: Maximum customers to return
            
        Returns:
            List of customer data dictionaries
            
        Requirements: 1.4
        """
        platform_lower = platform.lower().strip()
        
        if platform_lower == "shopify":
            server = self._servers["shopify"]
            return await server._get_customers(
                user_id=user_id,
                segment=segment,
                limit=limit,
            )
        else:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Customer data not available for platform: {platform}",
                recoverable=False,
            )
    
    async def fetch_analytics(
        self,
        user_id: str,
        platform: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch analytics from Shopify MCP server.
        
        Args:
            user_id: User identifier
            platform: Platform name (shopify)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            
        Returns:
            Analytics data dictionary
            
        Requirements: 1.4
        """
        platform_lower = platform.lower().strip()
        
        if platform_lower == "shopify":
            server = self._servers["shopify"]
            return await server._get_analytics(
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Analytics data not available for platform: {platform}",
                recoverable=False,
            )
    
    async def fetch_ad_accounts(
        self,
        user_id: str,
        platform: str,
    ) -> List[Dict[str, Any]]:
        """Fetch ad accounts from Meta or Google MCP server.
        
        Args:
            user_id: User identifier
            platform: Platform name (meta, google)
            
        Returns:
            List of ad account/customer data dictionaries
            
        Requirements: 1.4
        """
        platform_lower = platform.lower().strip()
        
        if platform_lower == "meta":
            server = self._servers["meta"]
            return await server._list_ad_accounts(user_id=user_id)
        elif platform_lower == "google":
            server = self._servers["google"]
            return await server._list_customers(user_id=user_id)
        else:
            raise MCPError(
                error_type=MCPErrorType.INVALID_PARAMS,
                message=f"Ad account data not available for platform: {platform}",
                recoverable=False,
            )


# Module-level router instance
_mcp_router: Optional[MCPRouter] = None


def get_mcp_router() -> MCPRouter:
    """Get the global MCP router instance.
    
    Returns:
        MCPRouter instance
    """
    global _mcp_router
    if _mcp_router is None:
        _mcp_router = MCPRouter()
    return _mcp_router


def set_mcp_router(router: MCPRouter) -> None:
    """Set the global MCP router instance (for testing).
    
    Args:
        router: MCPRouter instance to use
    """
    global _mcp_router
    _mcp_router = router


__all__ = [
    "MCPRouter",
    "MCP_PLATFORMS",
    "PLATFORM_MCP_MAPPING",
    "get_mcp_router",
    "set_mcp_router",
]
