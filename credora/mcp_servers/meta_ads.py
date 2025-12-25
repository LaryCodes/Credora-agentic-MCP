"""
Meta Ads MCP Server.

MCP Server for Meta (Facebook/Instagram) Ads integration.

Requirements: 1.1, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from typing import Any, Dict, List, Optional

from credora.mcp_servers.base import BaseMCPServer
from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.errors import MCPError, MCPErrorType
from credora.mcp_servers.meta_ads_client import MetaAdsClient
from credora.mcp_servers.models.meta_ads import (
    AdAccount,
    AdSet,
    AudienceInsights,
    Campaign,
)


# Tool input schemas
LIST_AD_ACCOUNTS_SCHEMA = {
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
        "account_id": {
            "type": "string",
            "description": "Ad account ID",
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
    "required": ["user_id", "account_id"],
}

GET_ADSETS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "account_id": {
            "type": "string",
            "description": "Ad account ID",
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
    "required": ["user_id", "account_id"],
}

GET_AUDIENCE_INSIGHTS_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "User identifier for authentication",
        },
        "account_id": {
            "type": "string",
            "description": "Ad account ID",
        },
    },
    "required": ["user_id", "account_id"],
}


class MetaAdsMCPServer(BaseMCPServer):
    """
    MCP Server for Meta Ads (Facebook/Instagram) integration.
    
    Exposes tools for fetching ad accounts, campaigns, ad sets,
    and audience insights from the Meta Marketing API.
    
    Requirements: 1.1, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    
    name = "meta-ads"
    version = "1.0.0"
    api_version = "v21.0"
    
    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
    ):
        """Initialize the Meta Ads MCP Server.
        
        Args:
            connection_manager: Optional ConnectionManager for OAuth tokens
        """
        self._connection_manager = connection_manager or ConnectionManager()
        super().__init__()
    
    def _register_tools(self) -> None:
        """Register Meta Ads tools.
        
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        self.register_tool(
            name="meta_list_ad_accounts",
            description="List all Meta Ads accounts accessible to the user",
            input_schema=LIST_AD_ACCOUNTS_SCHEMA,
            handler=self._list_ad_accounts,
        )
        
        self.register_tool(
            name="meta_get_campaigns",
            description="Get campaigns for a Meta Ads account with performance metrics",
            input_schema=GET_CAMPAIGNS_SCHEMA,
            handler=self._get_campaigns,
        )
        
        self.register_tool(
            name="meta_get_adsets",
            description="Get ad sets for a Meta Ads account with performance metrics",
            input_schema=GET_ADSETS_SCHEMA,
            handler=self._get_adsets,
        )
        
        self.register_tool(
            name="meta_get_audience_insights",
            description="Get audience demographic insights for a Meta Ads account",
            input_schema=GET_AUDIENCE_INSIGHTS_SCHEMA,
            handler=self._get_audience_insights,
        )

    async def _get_client(self, user_id: str) -> MetaAdsClient:
        """Get an authenticated Meta Ads client for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Authenticated MetaAdsClient
            
        Raises:
            MCPError: If authentication fails
        """
        try:
            access_token = await self._connection_manager.get_access_token(
                platform="meta",
                user_id=user_id,
            )
            return MetaAdsClient(access_token=access_token)
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"Failed to get Meta Ads access token: {str(e)}",
                recoverable=False,
            )
    
    async def _list_ad_accounts(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """List all ad accounts accessible to the user.
        
        Args:
            user_id: User identifier for authentication
            
        Returns:
            List of ad account dictionaries
            
        Requirements: 3.1
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        
        client = await self._get_client(user_id)
        accounts = await client.list_ad_accounts()
        
        return [account.to_dict() for account in accounts]
    
    async def _get_campaigns(
        self,
        user_id: str,
        account_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get campaigns for an ad account with metrics.
        
        Args:
            user_id: User identifier for authentication
            account_id: Ad account ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of campaign dictionaries with metrics
            
        Requirements: 3.2, 3.5
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        if not account_id:
            raise MCPError.invalid_params("account_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        client = await self._get_client(user_id)
        campaigns = await client.get_campaigns(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
        )
        
        return [campaign.to_dict() for campaign in campaigns]
    
    async def _get_adsets(
        self,
        user_id: str,
        account_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get ad sets for an ad account with metrics.
        
        Args:
            user_id: User identifier for authentication
            account_id: Ad account ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of ad set dictionaries with metrics
            
        Requirements: 3.3, 3.5
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        if not account_id:
            raise MCPError.invalid_params("account_id is required")
        
        # Validate date format if provided
        if date_from:
            self._validate_date_format(date_from, "date_from")
        if date_to:
            self._validate_date_format(date_to, "date_to")
        
        client = await self._get_client(user_id)
        adsets = await client.get_adsets(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
        )
        
        return [adset.to_dict() for adset in adsets]
    
    async def _get_audience_insights(
        self,
        user_id: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """Get audience demographic insights for an ad account.
        
        Args:
            user_id: User identifier for authentication
            account_id: Ad account ID
            
        Returns:
            Audience insights dictionary
            
        Requirements: 3.4
        """
        if not user_id:
            raise MCPError.invalid_params("user_id is required")
        if not account_id:
            raise MCPError.invalid_params("account_id is required")
        
        client = await self._get_client(user_id)
        insights = await client.get_audience_insights(account_id=account_id)
        
        return insights.to_dict()
    
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
        """Get the base URL for Meta API requests.
        
        Returns:
            Base URL string (always HTTPS)
            
        Requirements: 7.2
        """
        return f"https://graph.facebook.com/{self.api_version}"
