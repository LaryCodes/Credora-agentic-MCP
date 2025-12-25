"""
MCP Servers for Credora CFO Agent.

This package contains custom MCP (Model Context Protocol) servers for integrating
with external advertising and e-commerce platforms:
- Meta Ads (Facebook/Instagram)
- Google Ads
- Shopify

Each server implements the standard MCP protocol, handles OAuth authentication,
and exposes platform-specific tools for data retrieval.
"""

from credora.mcp_servers.base import (
    BaseMCPServer,
    MCPRequest,
    MCPResponse,
    Tool,
    ToolResult,
)
from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.token_store import TokenStore
from credora.mcp_servers.meta_ads import MetaAdsMCPServer
from credora.mcp_servers.meta_ads_client import MetaAdsClient
from credora.mcp_servers.google_ads import GoogleAdsMCPServer
from credora.mcp_servers.google_ads_client import GoogleAdsClient
from credora.mcp_servers.shopify import ShopifyMCPServer
from credora.mcp_servers.shopify_client import ShopifyClient

__all__ = [
    "BaseMCPServer",
    "ConnectionManager",
    "GoogleAdsMCPServer",
    "GoogleAdsClient",
    "MCPRequest",
    "MCPResponse",
    "MetaAdsMCPServer",
    "MetaAdsClient",
    "ShopifyMCPServer",
    "ShopifyClient",
    "TokenStore",
    "Tool",
    "ToolResult",
]
