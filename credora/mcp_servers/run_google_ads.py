"""
Google Ads MCP Server Entry Point.

Run the Google Ads MCP server for Google advertising integration.

Usage:
    python -m credora.mcp_servers.run_google_ads [--log-level LEVEL]

Environment Variables:
    GOOGLE_CLIENT_ID: Google OAuth Client ID
    GOOGLE_CLIENT_SECRET: Google OAuth Client Secret
    GOOGLE_ADS_DEVELOPER_TOKEN: Google Ads API developer token
    GOOGLE_REDIRECT_URI: OAuth redirect URI
    TOKEN_ENCRYPTION_KEY: Key for encrypting stored tokens
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)

Requirements: 1.1, 4.6
"""

import os
import sys

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.google_ads import GoogleAdsMCPServer
from credora.mcp_servers.run_base import run_mcp_server
from credora.mcp_servers.token_store import TokenStore


def main() -> None:
    """Main entry point for Google Ads MCP server."""
    # Get configuration from environment
    developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    
    # Initialize token store and connection manager
    # TokenStore uses the default encryption from security module
    token_store = TokenStore()
    connection_manager = ConnectionManager(token_store=token_store)
    
    # Run the server
    run_mcp_server(
        GoogleAdsMCPServer,
        connection_manager=connection_manager,
        developer_token=developer_token,
    )


if __name__ == "__main__":
    main()
