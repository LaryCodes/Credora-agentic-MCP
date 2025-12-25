"""Data fetcher tools for retrieving e-commerce platform data.

Requirements: 1.1, 1.4, 1.6
"""

import json
from typing import Optional
from datetime import datetime, timedelta
from agents import function_tool

from credora.state import StateManager
from credora.tools.mcp_router import get_mcp_router, MCP_PLATFORMS
from credora.mcp_servers.errors import MCPError


# Global state manager instance (can be injected for testing)
_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Get or create the global state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the state manager (for testing)."""
    global _state_manager
    _state_manager = manager


VALID_PLATFORMS = ["shopify", "woocommerce", "meta", "google"]
VALID_DATE_RANGES = ["7d", "30d", "90d", "1y", "all"]
VALID_ORDER_STATUSES = ["pending", "processing", "completed", "cancelled", "all"]
VALID_CUSTOMER_SEGMENTS = ["new", "returning", "vip", "at_risk", "all"]


def _convert_date_range_to_dates(date_range: str) -> tuple:
    """Convert date range string to date_from and date_to.
    
    Args:
        date_range: Date range string (7d, 30d, 90d, 1y, all)
        
    Returns:
        Tuple of (date_from, date_to) as YYYY-MM-DD strings
    """
    today = datetime.now()
    date_to = today.strftime("%Y-%m-%d")
    
    if date_range == "7d":
        date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif date_range == "30d":
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif date_range == "90d":
        date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    elif date_range == "1y":
        date_from = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    else:  # "all"
        date_from = None
        date_to = None
    
    return date_from, date_to


def _check_authorization(user_id: str, platform: str) -> Optional[str]:
    """Check if user is authorized to access the specified platform.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to check authorization for
        
    Returns:
        Error message if not authorized, None if authorized
        
    Requirements: 1.4, 1.6
    """
    if not user_id or not user_id.strip():
        return "Error: user_id is required"
    
    platform_lower = platform.lower().strip()
    if platform_lower not in VALID_PLATFORMS:
        return f"Error: Invalid platform '{platform}'. Supported platforms: {', '.join(VALID_PLATFORMS)}"
    
    manager = get_state_manager()
    session = manager.get_session_state(user_id)
    
    # Check if platform is connected
    if platform_lower not in session.connected_platforms:
        return f"Error: Platform '{platform_lower}' is not connected. Please connect your {platform_lower} store first."
    
    # Check if we have a token for this platform
    if platform_lower not in session.platform_tokens:
        return f"Error: No authorization token found for '{platform_lower}'. Please re-authenticate."
    
    return None  # Authorized


def _fetch_sales_data_impl(user_id: str, platform: str, date_range: str = "30d") -> str:
    """Internal implementation of fetch_sales_data.
    
    Retrieves sales metrics from the specified platform.
    This is a read-only operation that does not modify any store data.
    Routes to MCP servers for supported platforms (meta, google, shopify).
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce, meta, google)
        date_range: Time period for data (7d, 30d, 90d, 1y, all)
        
    Returns:
        Sales data summary or error message
        
    Requirements: 1.1, 1.4, 1.6
    """
    # Check authorization first
    auth_error = _check_authorization(user_id, platform)
    if auth_error:
        return auth_error
    
    # Validate date range
    if date_range not in VALID_DATE_RANGES:
        return f"Error: Invalid date_range '{date_range}'. Valid options: {', '.join(VALID_DATE_RANGES)}"
    
    platform_lower = platform.lower().strip()
    
    # Route to MCP server for supported platforms
    if platform_lower in MCP_PLATFORMS:
        try:
            import asyncio
            router = get_mcp_router()
            date_from, date_to = _convert_date_range_to_dates(date_range)
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if platform_lower == "shopify":
                # Use Shopify analytics for sales data
                analytics = loop.run_until_complete(
                    router.fetch_analytics(user_id, platform_lower, date_from, date_to)
                )
                return f"""Sales Data for {platform_lower} ({date_range}):
- Total Revenue: ${analytics.get('total_revenue', 0):,.2f}
- Total Orders: {analytics.get('total_orders', 0)}
- Average Order Value: ${analytics.get('average_order_value', 0):,.2f}
- Conversion Rate: {analytics.get('conversion_rate', 0)}%

Top Products:
{_format_top_products(analytics.get('top_products', []))}"""
            else:
                # For Meta/Google, fetch campaign data as sales metrics
                accounts = loop.run_until_complete(
                    router.fetch_ad_accounts(user_id, platform_lower)
                )
                if not accounts:
                    return f"No ad accounts found for {platform_lower}. Please connect an account."
                
                # Get campaigns from first account
                account_id = accounts[0].get('id', '')
                campaigns = loop.run_until_complete(
                    router.fetch_campaigns(user_id, platform_lower, account_id, date_from, date_to)
                )
                
                total_spend = sum(c.get('spend', 0) for c in campaigns)
                total_impressions = sum(c.get('impressions', 0) for c in campaigns)
                total_clicks = sum(c.get('clicks', 0) for c in campaigns)
                total_conversions = sum(c.get('conversions', 0) for c in campaigns)
                
                return f"""Ad Performance Data for {platform_lower} ({date_range}):
- Total Spend: ${total_spend:,.2f}
- Total Impressions: {total_impressions:,}
- Total Clicks: {total_clicks:,}
- Total Conversions: {total_conversions:,}
- CTR: {(total_clicks / total_impressions * 100) if total_impressions > 0 else 0:.2f}%

Campaigns: {len(campaigns)}"""
        except MCPError as e:
            return f"Error fetching data from {platform_lower}: {e.message}"
        except Exception as e:
            return f"Error fetching data from {platform_lower}: {str(e)}"
    
    # Mock data for non-MCP platforms (woocommerce)
    mock_sales_data = {
        "platform": platform_lower,
        "date_range": date_range,
        "total_revenue": 45230.50,
        "total_orders": 342,
        "average_order_value": 132.25,
        "conversion_rate": 3.2,
        "top_products": [
            {"name": "Product A", "revenue": 12500.00, "units": 125},
            {"name": "Product B", "revenue": 8750.00, "units": 87},
            {"name": "Product C", "revenue": 6200.00, "units": 62},
        ],
        "revenue_by_day": {
            "trend": "increasing",
            "growth_rate": 5.2,
        },
    }
    
    return f"""Sales Data for {platform_lower} ({date_range}):
- Total Revenue: ${mock_sales_data['total_revenue']:,.2f}
- Total Orders: {mock_sales_data['total_orders']}
- Average Order Value: ${mock_sales_data['average_order_value']:,.2f}
- Conversion Rate: {mock_sales_data['conversion_rate']}%
- Revenue Trend: {mock_sales_data['revenue_by_day']['trend']} ({mock_sales_data['revenue_by_day']['growth_rate']}% growth)

Top Products:
1. {mock_sales_data['top_products'][0]['name']}: ${mock_sales_data['top_products'][0]['revenue']:,.2f} ({mock_sales_data['top_products'][0]['units']} units)
2. {mock_sales_data['top_products'][1]['name']}: ${mock_sales_data['top_products'][1]['revenue']:,.2f} ({mock_sales_data['top_products'][1]['units']} units)
3. {mock_sales_data['top_products'][2]['name']}: ${mock_sales_data['top_products'][2]['revenue']:,.2f} ({mock_sales_data['top_products'][2]['units']} units)"""


def _format_top_products(products: list) -> str:
    """Format top products list for display."""
    if not products:
        return "No product data available"
    
    lines = []
    for i, p in enumerate(products[:5], 1):
        name = p.get('name', p.get('product_name', 'Unknown'))
        revenue = p.get('revenue', p.get('total_revenue', 0))
        units = p.get('units', p.get('quantity_sold', 0))
        lines.append(f"{i}. {name}: ${revenue:,.2f} ({units} units)")
    
    return "\n".join(lines)


def _fetch_orders_impl(
    user_id: str, platform: str, date_range: str = "30d", status: str = "all"
) -> str:
    """Internal implementation of fetch_orders.
    
    Retrieves order data from the specified platform.
    This is a read-only operation that does not modify any store data.
    Routes to MCP servers for supported platforms (shopify).
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        date_range: Time period for data (7d, 30d, 90d, 1y, all)
        status: Order status filter (pending, processing, completed, cancelled, all)
        
    Returns:
        Order data summary or error message
        
    Requirements: 1.1, 1.4, 1.6
    """
    # Check authorization first
    auth_error = _check_authorization(user_id, platform)
    if auth_error:
        return auth_error
    
    # Validate date range
    if date_range not in VALID_DATE_RANGES:
        return f"Error: Invalid date_range '{date_range}'. Valid options: {', '.join(VALID_DATE_RANGES)}"
    
    # Validate status
    if status not in VALID_ORDER_STATUSES:
        return f"Error: Invalid status '{status}'. Valid options: {', '.join(VALID_ORDER_STATUSES)}"
    
    platform_lower = platform.lower().strip()
    
    # Route to MCP server for Shopify
    if platform_lower == "shopify":
        try:
            import asyncio
            router = get_mcp_router()
            date_from, date_to = _convert_date_range_to_dates(date_range)
            
            # Map status to Shopify format
            shopify_status = "any" if status == "all" else status
            if status == "completed":
                shopify_status = "closed"
            elif status == "pending" or status == "processing":
                shopify_status = "open"
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            orders = loop.run_until_complete(
                router.fetch_orders(user_id, platform_lower, date_from, date_to, shopify_status, 50)
            )
            
            # Calculate order statistics
            total_orders = len(orders)
            orders_by_status = {}
            for order in orders:
                order_status = order.get('status', 'unknown')
                orders_by_status[order_status] = orders_by_status.get(order_status, 0) + 1
            
            status_breakdown = "\n".join([
                f"  - {s.capitalize()}: {count}"
                for s, count in orders_by_status.items()
            ])
            
            return f"""Order Data for {platform_lower} ({date_range}, status: {status}):
- Total Orders: {total_orders}

Orders by Status:
{status_breakdown if status_breakdown else "  No orders found"}"""
        except MCPError as e:
            return f"Error fetching orders from {platform_lower}: {e.message}"
        except Exception as e:
            return f"Error fetching orders from {platform_lower}: {str(e)}"
    
    # Mock data for non-MCP platforms (woocommerce)
    mock_orders_data = {
        "platform": platform_lower,
        "date_range": date_range,
        "status_filter": status,
        "total_orders": 342,
        "orders_by_status": {
            "pending": 23,
            "processing": 45,
            "completed": 267,
            "cancelled": 7,
        },
        "fulfillment_rate": 94.5,
        "average_fulfillment_time": "2.3 days",
    }
    
    status_breakdown = "\n".join([
        f"  - {s.capitalize()}: {count}"
        for s, count in mock_orders_data['orders_by_status'].items()
    ])
    
    return f"""Order Data for {platform_lower} ({date_range}, status: {status}):
- Total Orders: {mock_orders_data['total_orders']}
- Fulfillment Rate: {mock_orders_data['fulfillment_rate']}%
- Average Fulfillment Time: {mock_orders_data['average_fulfillment_time']}

Orders by Status:
{status_breakdown}"""


def _fetch_products_impl(user_id: str, platform: str, limit: int = 10) -> str:
    """Internal implementation of fetch_products.
    
    Retrieves product catalog data from the specified platform.
    This is a read-only operation that does not modify any store data.
    Routes to MCP servers for supported platforms (shopify).
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        limit: Maximum number of products to return (1-100)
        
    Returns:
        Product catalog summary or error message
        
    Requirements: 1.1, 1.4, 1.6
    """
    # Check authorization first
    auth_error = _check_authorization(user_id, platform)
    if auth_error:
        return auth_error
    
    # Validate limit
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        return "Error: limit must be an integer between 1 and 100"
    
    platform_lower = platform.lower().strip()
    
    # Route to MCP server for Shopify
    if platform_lower == "shopify":
        try:
            import asyncio
            router = get_mcp_router()
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            products = loop.run_until_complete(
                router.fetch_products(user_id, platform_lower, limit)
            )
            
            products_to_show = products[:limit]
            
            product_list = "\n".join([
                f"{i+1}. {p.get('title', 'Unknown')}: ${float(p.get('price', 0)):.2f} (Inventory: {p.get('inventory_quantity', 0)}, Status: {p.get('status', 'unknown')})"
                for i, p in enumerate(products_to_show)
            ])
            
            active_count = sum(1 for p in products if p.get('status') == 'active')
            
            return f"""Product Catalog for {platform_lower} (showing {len(products_to_show)} of {len(products)} products):

{product_list if product_list else "No products found"}

Total Products: {len(products)}
Active Products: {active_count}"""
        except MCPError as e:
            return f"Error fetching products from {platform_lower}: {e.message}"
        except Exception as e:
            return f"Error fetching products from {platform_lower}: {str(e)}"
    
    # Mock data for non-MCP platforms (woocommerce)
    mock_products = [
        {"name": "Premium Widget", "price": 49.99, "inventory": 150, "status": "active"},
        {"name": "Basic Widget", "price": 24.99, "inventory": 320, "status": "active"},
        {"name": "Widget Pro", "price": 79.99, "inventory": 45, "status": "active"},
        {"name": "Widget Lite", "price": 14.99, "inventory": 500, "status": "active"},
        {"name": "Widget Bundle", "price": 99.99, "inventory": 25, "status": "active"},
    ]
    
    # Limit the results
    products_to_show = mock_products[:min(limit, len(mock_products))]
    
    product_list = "\n".join([
        f"{i+1}. {p['name']}: ${p['price']:.2f} (Inventory: {p['inventory']}, Status: {p['status']})"
        for i, p in enumerate(products_to_show)
    ])
    
    return f"""Product Catalog for {platform_lower} (showing {len(products_to_show)} of {len(mock_products)} products):

{product_list}

Total Products: {len(mock_products)}
Active Products: {sum(1 for p in mock_products if p['status'] == 'active')}"""


def _fetch_customers_impl(
    user_id: str, platform: str, segment: str = "all"
) -> str:
    """Internal implementation of fetch_customers.
    
    Retrieves customer data from the specified platform.
    This is a read-only operation that does not modify any store data.
    Routes to MCP servers for supported platforms (shopify).
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        segment: Customer segment filter (new, returning, vip, at_risk, all)
        
    Returns:
        Customer data summary or error message
        
    Requirements: 1.1, 1.4, 1.6
    """
    # Check authorization first
    auth_error = _check_authorization(user_id, platform)
    if auth_error:
        return auth_error
    
    # Validate segment
    if segment not in VALID_CUSTOMER_SEGMENTS:
        return f"Error: Invalid segment '{segment}'. Valid options: {', '.join(VALID_CUSTOMER_SEGMENTS)}"
    
    platform_lower = platform.lower().strip()
    
    # Route to MCP server for Shopify
    if platform_lower == "shopify":
        try:
            import asyncio
            router = get_mcp_router()
            
            # Map segment to Shopify format
            shopify_segment = segment if segment != "returning" else "repeat"
            if segment == "at_risk":
                shopify_segment = "all"  # Shopify doesn't have at_risk segment
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            customers = loop.run_until_complete(
                router.fetch_customers(user_id, platform_lower, shopify_segment, 50)
            )
            
            total_customers = len(customers)
            
            # Calculate average lifetime value if available
            total_spent = sum(float(c.get('total_spent', 0)) for c in customers)
            avg_ltv = total_spent / total_customers if total_customers > 0 else 0
            
            return f"""Customer Data for {platform_lower} (segment: {segment}):
- Total Customers: {total_customers}
- Average Lifetime Value: ${avg_ltv:,.2f}

Customer segment: {segment}"""
        except MCPError as e:
            return f"Error fetching customers from {platform_lower}: {e.message}"
        except Exception as e:
            return f"Error fetching customers from {platform_lower}: {str(e)}"
    
    # Mock data for non-MCP platforms (woocommerce)
    mock_customer_data = {
        "platform": platform_lower,
        "segment_filter": segment,
        "total_customers": 1250,
        "customers_by_segment": {
            "new": 320,
            "returning": 680,
            "vip": 150,
            "at_risk": 100,
        },
        "average_lifetime_value": 285.50,
        "repeat_purchase_rate": 42.5,
        "customer_acquisition_cost": 25.00,
    }
    
    segment_breakdown = "\n".join([
        f"  - {s.replace('_', ' ').title()}: {count}"
        for s, count in mock_customer_data['customers_by_segment'].items()
    ])
    
    return f"""Customer Data for {platform_lower} (segment: {segment}):
- Total Customers: {mock_customer_data['total_customers']}
- Average Lifetime Value: ${mock_customer_data['average_lifetime_value']:,.2f}
- Repeat Purchase Rate: {mock_customer_data['repeat_purchase_rate']}%
- Customer Acquisition Cost: ${mock_customer_data['customer_acquisition_cost']:,.2f}

Customers by Segment:
{segment_breakdown}"""


# Decorated tools for agent use
@function_tool
def fetch_sales_data(user_id: str, platform: str, date_range: str = "30d") -> str:
    """Fetch sales metrics from a connected e-commerce platform.
    
    This is a read-only operation that retrieves sales data without modifying
    any store data.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        date_range: Time period for data (7d, 30d, 90d, 1y, all)
        
    Returns:
        Sales data summary or error message
    """
    return _fetch_sales_data_impl(user_id, platform, date_range)


@function_tool
def fetch_orders(
    user_id: str, platform: str, date_range: str = "30d", status: str = "all"
) -> str:
    """Fetch order data from a connected e-commerce platform.
    
    This is a read-only operation that retrieves order data without modifying
    any store data.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        date_range: Time period for data (7d, 30d, 90d, 1y, all)
        status: Order status filter (pending, processing, completed, cancelled, all)
        
    Returns:
        Order data summary or error message
    """
    return _fetch_orders_impl(user_id, platform, date_range, status)


@function_tool
def fetch_products(user_id: str, platform: str, limit: int = 10) -> str:
    """Fetch product catalog from a connected e-commerce platform.
    
    This is a read-only operation that retrieves product data without modifying
    any store data.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        limit: Maximum number of products to return (1-100)
        
    Returns:
        Product catalog summary or error message
    """
    return _fetch_products_impl(user_id, platform, limit)


@function_tool
def fetch_customers(user_id: str, platform: str, segment: str = "all") -> str:
    """Fetch customer data from a connected e-commerce platform.
    
    This is a read-only operation that retrieves customer data without modifying
    any store data.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform (shopify, woocommerce)
        segment: Customer segment filter (new, returning, vip, at_risk, all)
        
    Returns:
        Customer data summary or error message
    """
    return _fetch_customers_impl(user_id, platform, segment)


__all__ = [
    # Decorated tools for agent use
    "fetch_sales_data",
    "fetch_orders",
    "fetch_products",
    "fetch_customers",
    # Internal implementations for testing
    "_fetch_sales_data_impl",
    "_fetch_orders_impl",
    "_fetch_products_impl",
    "_fetch_customers_impl",
    # Utilities
    "get_state_manager",
    "set_state_manager",
    "_check_authorization",
    "VALID_PLATFORMS",
    "VALID_DATE_RANGES",
    "VALID_ORDER_STATUSES",
    "VALID_CUSTOMER_SEGMENTS",
]
