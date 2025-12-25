"""Tool implementations for agent operations."""

from credora.tools.onboarding import (
    collect_platform_type,
    collect_business_goals,
    initiate_oauth,
    complete_onboarding,
    get_state_manager,
    set_state_manager,
    VALID_PLATFORMS,
    VALID_GOALS,
)

from credora.tools.data_fetcher import (
    fetch_sales_data,
    fetch_orders,
    fetch_products,
    fetch_customers,
    VALID_DATE_RANGES,
    VALID_ORDER_STATUSES,
    VALID_CUSTOMER_SEGMENTS,
)

from credora.tools.analytics import (
    analyze_revenue_trends,
    detect_bottlenecks,
    compare_periods,
    calculate_metrics,
    VALID_PERIODS,
    VALID_METRICS,
)

from credora.tools.competitor import (
    search_competitor,
    analyze_competitor_pricing,
    get_market_trends,
    VALID_INDUSTRIES,
)

from credora.tools.insight import (
    generate_recommendation,
    explain_metric_change,
    prioritize_actions,
    PRIORITY_LEVELS,
    VALID_CATEGORIES,
)

from credora.tools.cfo import (
    get_session_state,
    update_session_state,
    get_state_manager as get_cfo_state_manager,
    set_state_manager as set_cfo_state_manager,
)

from credora.tools.connection import (
    list_connected_platforms,
    initiate_platform_connection,
    disconnect_platform,
    check_platform_health,
    get_connection_manager,
    set_connection_manager,
    SUPPORTED_PLATFORMS,
)

__all__ = [
    # Onboarding tools
    "collect_platform_type",
    "collect_business_goals",
    "initiate_oauth",
    "complete_onboarding",
    "get_state_manager",
    "set_state_manager",
    "VALID_PLATFORMS",
    "VALID_GOALS",
    # Data fetcher tools
    "fetch_sales_data",
    "fetch_orders",
    "fetch_products",
    "fetch_customers",
    "VALID_DATE_RANGES",
    "VALID_ORDER_STATUSES",
    "VALID_CUSTOMER_SEGMENTS",
    # Analytics tools
    "analyze_revenue_trends",
    "detect_bottlenecks",
    "compare_periods",
    "calculate_metrics",
    "VALID_PERIODS",
    "VALID_METRICS",
    # Competitor tools
    "search_competitor",
    "analyze_competitor_pricing",
    "get_market_trends",
    "VALID_INDUSTRIES",
    # Insight tools
    "generate_recommendation",
    "explain_metric_change",
    "prioritize_actions",
    "PRIORITY_LEVELS",
    "VALID_CATEGORIES",
    # CFO state tools
    "get_session_state",
    "update_session_state",
    "get_cfo_state_manager",
    "set_cfo_state_manager",
    # Connection management tools
    "list_connected_platforms",
    "initiate_platform_connection",
    "disconnect_platform",
    "check_platform_health",
    "get_connection_manager",
    "set_connection_manager",
    "SUPPORTED_PLATFORMS",
]
