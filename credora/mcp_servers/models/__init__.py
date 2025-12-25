"""
Data models for MCP servers.

This package contains dataclasses and type definitions for:
- OAuth configuration and tokens
- Meta Ads data structures
- Google Ads data structures
- Shopify data structures
"""

from credora.mcp_servers.models.oauth import (
    TokenData,
    OAuthConfig,
    Connection,
    ConnectionHealth,
)
from credora.mcp_servers.models.meta_ads import (
    AdAccount,
    Campaign as MetaCampaign,
    AdSet,
    AudienceInsights,
)
from credora.mcp_servers.models.google_ads import (
    Customer,
    Campaign as GoogleCampaign,
    Keyword,
    AdGroup,
)
from credora.mcp_servers.models.shopify import (
    StoreInfo,
    Order,
    Product,
    Customer as ShopifyCustomer,
    SalesAnalytics,
    LineItem,
    ProductSales,
)

__all__ = [
    # OAuth
    "TokenData",
    "OAuthConfig",
    "Connection",
    "ConnectionHealth",
    # Meta Ads
    "AdAccount",
    "MetaCampaign",
    "AdSet",
    "AudienceInsights",
    # Google Ads
    "Customer",
    "GoogleCampaign",
    "Keyword",
    "AdGroup",
    # Shopify
    "StoreInfo",
    "Order",
    "Product",
    "ShopifyCustomer",
    "SalesAnalytics",
    "LineItem",
    "ProductSales",
]
