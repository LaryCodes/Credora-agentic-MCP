"""
Google Ads MCP Server.

MCP Server for Google Ads integration.

Requirements: 1.1, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import os
from typing import Any, Dict, List, Optional

from credora.mcp_servers.base import BaseMCPServer
from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.errors import MCPError, MCPErrorType
from credora.mcp_servers.google_ads_client import GoogleAdsClient
from credora.mcp_servers.models.google_ads import (
    AdGroup,
    Campaign,
    Customer,
    Keyword,
)


# Tool input schemas
LIST_CUSTOMERS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
    },
    "required": ["user_id"],
}

GET_CAMPAIGNS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "customer_id": {
            "type": "string",
            "description": "Google Ads customer ID",
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
    "required": ["user_id", "customer_id"],
}

GET_KEYWORDS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "customer_id": {
            "type": "string",
            "description": "Google Ads customer ID",
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
    "required": ["user_id", "customer_id"],
}

GET_AD_GROUPS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "customer_id": {
            "type": "string",
            "description": "Google Ads customer ID",
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
    "required": ["user_id", "customer_id"],
}



class GoogleAdsMCPServer(BaseMCPServer):
    """
    MCP Server for Google Ads integration.
    
    Exposes tools for fetching customer accounts, campaigns, keywords,
    and ad groups from the Google Ads API.
    
    Requirements: 1.1, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    
    name = "google-ads"
    version = "1.0.0"
    api_version = "v18"
    
    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
        developer_token: Optional[str] = None,
    ):
        """Initialize the Google Ads MCP Server.
        
        Args:
            connection_manager: Optional ConnectionManager for OAuth tokens
            developer_token: Google Ads API developer token (or from env)
        """
        self._connection_manager = connection_manager or ConnectionManager()
        self._developer_token = developer_token or os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        super().__init__()
    
    def _register_tools(self) -> None:
        """Register Google Ads tools.
        
        Requirements: 4.1, 4.2, 4.3, 4.4
        """
        self.register_tool(
            name="google_list_customers",
            description="List all Google Ads customer accounts accessible to the user",
            input_schema=LIST_CUSTOMERS_SCHEMA,
            handler=self._list_customers,
        )
        
        self.register_tool(
            name="google_get_campaigns",
            description="Get campaigns for a Google Ads customer with performance metrics",
            input_schema=GET_CAMPAIGNS_SCHEMA,
            handler=self._get_campaigns,
        )
        
        self.register_tool(
            name="google_get_keywords",
            description="Get keywords for a Google Ads customer with performance metrics",
            input_schema=GET_KEYWORDS_SCHEMA,
            handler=self._get_keywords,
        )
        
        self.register_tool(
            name="google_get_ad_groups",
            description="Get ad groups for a Google Ads customer with performance metrics",
            input_schema=GET_AD_GROUPS_SCHEMA,
            handler=self._get_ad_groups,
        )

    async def _get_client(self, user_id: str) -> GoogleAdsClient:
        """Get an authenticated Google Ads client for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Authenticated GoogleAdsClient
            
        Raises:
            MCPError: If authentication fails
        """
        if not self._developer_token:
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message="Google Ads developer token not configured",
                recoverable=False,
            )
        
        try:
            access_token = await self._connection_manager.get_access_token(
                platform="google",
                user_id=user_id,
            )
            return GoogleAdsClient(
                access_token=access_token,
                developer_token=self._developer_token,
            )
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"Failed to get Google Ads access token: {str(e)}",
                recoverable=False,
            )
    
    async def _list_customers(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """List all customer accounts accessible to the user.
        
        Args:
            user_id: User identifier for authentication
            
        Returns:
            List of customer account dictionaries
            
        Requirements: 4.1
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        client = await self._get_client(user_id)
        customers = await client.list_customers()
        
        return [customer.to_dict() for customer in customers]
    
    async def _get_campaigns(
        self,
        user_id: str,
        customer_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get campaigns for a customer with metrics.
        
        Args:
            user_id: User identifier for authentication
            customer_id: Google Ads customer ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of campaign dictionaries with metrics
            
        Requirements: 4.2, 4.5
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        if not customer_id:
            raise MCPError.invalid_params("customer_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        client = await self._get_client(user_id)
        campaigns = await client.get_campaigns(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        
        return [campaign.to_dict() for campaign in campaigns]

    
    async def _get_keywords(
        self,
        user_id: str,
        customer_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get keywords for a customer with metrics.
        
        Args:
            user_id: User identifier for authentication
            customer_id: Google Ads customer ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of keyword dictionaries with metrics
            
        Requirements: 4.3, 4.5
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        if not customer_id:
            raise MCPError.invalid_params("customer_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        client = await self._get_client(user_id)
        keywords = await client.get_keywords(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        
        return [keyword.to_dict() for keyword in keywords]
    
    async def _get_ad_groups(
        self,
        user_id: str,
        customer_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get ad groups for a customer with metrics.
        
        Args:
            user_id: User identifier for authentication
            customer_id: Google Ads customer ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of ad group dictionaries with metrics
            
        Requirements: 4.4, 4.5
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        if not customer_id:
            raise MCPError.invalid_params("customer_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        client = await self._get_client(user_id)
        ad_groups = await client.get_ad_groups(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        
        return [ad_group.to_dict() for ad_group in ad_groups]
    
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
        """Get the base URL for Google Ads API requests.
        
        Returns:
            Base URL string (always HTTPS)
            
        Requirements: 7.2
        """
        return f"https://googleads.googleapis.com/{self.api_version}"
