"""
Shopify MCP Server Entry Point.

Run the Shopify MCP server for e-commerce integration.

Usage:
    python -m credora.mcp_servers.run_shopify [--log-level LEVEL]

Environment Variables:
    SHOPIFY_API_KEY: Shopify App API Key
    SHOPIFY_API_SECRET: Shopify App API Secret
    SHOPIFY_REDIRECT_URI: OAuth redirect URI
    TOKEN_ENCRYPTION_KEY: Key for encrypting stored tokens
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)

Requirements: 1.1, 5.6
"""

import os
import sys

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.run_base import run_mcp_server
from credora.mcp_servers.shopify import ShopifyMCPServer
from credora.mcp_servers.token_store import TokenStore


def main() -> None:
    """Main entry point for Shopify MCP server."""
    # Initialize token store and connection manager
    # TokenStore uses the default encryption from security module
    token_store = TokenStore()
    connection_manager = ConnectionManager(token_store=token_store)
    
    # Run the server
    run_mcp_server(
        ShopifyMCPServer,
        connection_manager=connection_manager,
    )


if __name__ == "__main__":
    main()
