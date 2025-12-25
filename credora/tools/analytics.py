"""Analytics tools for trend analysis and bottleneck detection.

Requirements: 1.1, 5.2
"""

import json
from typing import Dict, List, Any
from agents import function_tool


def _parse_json_data(data_json: str) -> Dict[str, Any] | str:
    """Parse JSON string to dictionary.
    
    Args:
        data_json: JSON string to parse
        
    Returns:
        Parsed dictionary or error message string
    """
    try:
        data = json.loads(data_json)
        if not isinstance(data, dict):
            return "Error: JSON must represent an object/dictionary"
        return data
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {str(e)}"


# Valid analysis periods
VALID_PERIODS = ["daily", "weekly", "monthly", "quarterly", "yearly"]

# Valid metrics for calculation
VALID_METRICS = [
    "revenue",
    "orders",
    "average_order_value",
    "conversion_rate",
    "customer_acquisition_cost",
    "customer_lifetime_value",
    "repeat_purchase_rate",
    "gross_margin",
]


def _analyze_revenue_trends_impl(data: Dict[str, Any], period: str = "monthly") -> str:
    """Internal implementation of analyze_revenue_trends.
    
    Identifies revenue patterns and trends from sales data.
    This is a deterministic, read-only analysis operation.
    
    Args:
        data: Sales data dictionary containing revenue information
        period: Analysis period (daily, weekly, monthly, quarterly, yearly)
        
    Returns:
        Revenue trend analysis or error message
        
    Requirements: 1.1, 5.2
    """
    # Validate period
    if period not in VALID_PERIODS:
        return f"Error: Invalid period '{period}'. Valid options: {', '.join(VALID_PERIODS)}"
    
    # Validate data structure
    if not isinstance(data, dict):
        return "Error: data must be a dictionary"
    
    if not data:
        return "Error: data cannot be empty. Please provide sales data for analysis."
    
    # Extract revenue data - handle various input formats
    total_revenue = data.get("total_revenue", data.get("revenue", 0))
    previous_revenue = data.get("previous_revenue", data.get("previous_total_revenue", 0))
    
    # Calculate growth rate if we have comparison data
    if previous_revenue and previous_revenue > 0:
        growth_rate = ((total_revenue - previous_revenue) / previous_revenue) * 100
        trend = "increasing" if growth_rate > 0 else "decreasing" if growth_rate < 0 else "stable"
    else:
        growth_rate = 0
        trend = "stable"
    
    # Determine trend strength
    if abs(growth_rate) > 20:
        trend_strength = "strong"
    elif abs(growth_rate) > 10:
        trend_strength = "moderate"
    elif abs(growth_rate) > 5:
        trend_strength = "slight"
    else:
        trend_strength = "minimal"
    
    # Generate insights based on data
    insights = []
    
    if growth_rate > 0:
        insights.append(f"Revenue is {trend_strength}ly increasing at {growth_rate:.1f}% {period}")
    elif growth_rate < 0:
        insights.append(f"Revenue is {trend_strength}ly decreasing at {abs(growth_rate):.1f}% {period}")
    else:
        insights.append(f"Revenue is stable with {trend_strength} change")
    
    # Check for seasonal patterns if daily/weekly data available
    if "revenue_by_day" in data or "daily_revenue" in data:
        insights.append("Daily revenue data available for detailed pattern analysis")
    
    # Check average order value trends
    aov = data.get("average_order_value", data.get("aov", 0))
    if aov > 0:
        insights.append(f"Average order value: ${aov:.2f}")
    
    return f"""Revenue Trend Analysis ({period}):

Trend: {trend.capitalize()} ({trend_strength})
Growth Rate: {growth_rate:+.1f}%
Current Revenue: ${total_revenue:,.2f}
Previous Revenue: ${previous_revenue:,.2f}

Key Insights:
{chr(10).join(f'- {insight}' for insight in insights)}

Analysis Period: {period}
Data Points Analyzed: {len(data)} fields"""


def _detect_bottlenecks_impl(data: Dict[str, Any]) -> str:
    """Internal implementation of detect_bottlenecks.
    
    Identifies conversion and operational bottlenecks from data.
    This is a deterministic, read-only analysis operation.
    
    Args:
        data: Operational data dictionary containing metrics
        
    Returns:
        Bottleneck analysis or error message
        
    Requirements: 1.1, 5.2
    """
    # Validate data structure
    if not isinstance(data, dict):
        return "Error: data must be a dictionary"
    
    if not data:
        return "Error: data cannot be empty. Please provide operational data for analysis."
    
    bottlenecks = []
    recommendations = []
    
    # Check conversion rate
    conversion_rate = data.get("conversion_rate", data.get("conversion", 0))
    if conversion_rate > 0:
        if conversion_rate < 1:
            bottlenecks.append(f"Critical: Very low conversion rate ({conversion_rate}%)")
            recommendations.append("Review checkout flow and reduce friction points")
        elif conversion_rate < 2:
            bottlenecks.append(f"Warning: Below average conversion rate ({conversion_rate}%)")
            recommendations.append("Consider A/B testing landing pages")
        elif conversion_rate < 3:
            bottlenecks.append(f"Note: Conversion rate ({conversion_rate}%) has room for improvement")
    
    # Check cart abandonment
    cart_abandonment = data.get("cart_abandonment_rate", data.get("abandonment_rate", 0))
    if cart_abandonment > 0:
        if cart_abandonment > 80:
            bottlenecks.append(f"Critical: Very high cart abandonment ({cart_abandonment}%)")
            recommendations.append("Implement cart recovery emails and simplify checkout")
        elif cart_abandonment > 70:
            bottlenecks.append(f"Warning: High cart abandonment ({cart_abandonment}%)")
            recommendations.append("Review shipping costs and payment options")
    
    # Check fulfillment rate
    fulfillment_rate = data.get("fulfillment_rate", 0)
    if fulfillment_rate > 0:
        if fulfillment_rate < 90:
            bottlenecks.append(f"Warning: Low fulfillment rate ({fulfillment_rate}%)")
            recommendations.append("Review inventory management and supplier reliability")
        elif fulfillment_rate < 95:
            bottlenecks.append(f"Note: Fulfillment rate ({fulfillment_rate}%) could be improved")
    
    # Check average fulfillment time
    avg_fulfillment_days = data.get("average_fulfillment_days", data.get("fulfillment_days", 0))
    if avg_fulfillment_days > 0:
        if avg_fulfillment_days > 5:
            bottlenecks.append(f"Warning: Slow fulfillment time ({avg_fulfillment_days} days)")
            recommendations.append("Consider faster shipping options or local fulfillment")
        elif avg_fulfillment_days > 3:
            bottlenecks.append(f"Note: Fulfillment time ({avg_fulfillment_days} days) is average")
    
    # Check customer acquisition cost vs lifetime value
    cac = data.get("customer_acquisition_cost", data.get("cac", 0))
    ltv = data.get("customer_lifetime_value", data.get("ltv", 0))
    if cac > 0 and ltv > 0:
        ltv_cac_ratio = ltv / cac
        if ltv_cac_ratio < 1:
            bottlenecks.append(f"Critical: LTV/CAC ratio ({ltv_cac_ratio:.1f}) is below 1")
            recommendations.append("Reduce acquisition costs or increase customer value")
        elif ltv_cac_ratio < 3:
            bottlenecks.append(f"Warning: LTV/CAC ratio ({ltv_cac_ratio:.1f}) is below target")
            recommendations.append("Focus on retention to improve lifetime value")
    
    if not bottlenecks:
        return """Bottleneck Analysis:

No significant bottlenecks detected in the provided data.

All analyzed metrics are within acceptable ranges. Continue monitoring for changes.

Data Points Analyzed: """ + str(len(data)) + " fields"
    
    return f"""Bottleneck Analysis:

Identified Issues ({len(bottlenecks)}):
{chr(10).join(f'{i+1}. {b}' for i, b in enumerate(bottlenecks))}

Recommendations:
{chr(10).join(f'- {r}' for r in recommendations)}

Data Points Analyzed: {len(data)} fields"""



def _compare_periods_impl(current: Dict[str, Any], previous: Dict[str, Any]) -> str:
    """Internal implementation of compare_periods.
    
    Performs period-over-period comparison of metrics.
    This is a deterministic, read-only analysis operation.
    
    Args:
        current: Current period data dictionary
        previous: Previous period data dictionary
        
    Returns:
        Period comparison analysis or error message
        
    Requirements: 1.1, 5.2
    """
    # Validate data structures
    if not isinstance(current, dict):
        return "Error: current must be a dictionary"
    if not isinstance(previous, dict):
        return "Error: previous must be a dictionary"
    
    if not current:
        return "Error: current period data cannot be empty"
    if not previous:
        return "Error: previous period data cannot be empty"
    
    comparisons = []
    improvements = []
    declines = []
    
    # Compare common metrics
    metrics_to_compare = [
        ("total_revenue", "revenue", "Revenue", "$", True),
        ("total_orders", "orders", "Orders", "", True),
        ("average_order_value", "aov", "Avg Order Value", "$", True),
        ("conversion_rate", "conversion", "Conversion Rate", "%", True),
        ("customer_count", "customers", "Customers", "", True),
        ("fulfillment_rate", "fulfillment", "Fulfillment Rate", "%", True),
    ]
    
    for primary_key, alt_key, label, prefix, higher_is_better in metrics_to_compare:
        current_val = current.get(primary_key, current.get(alt_key, None))
        previous_val = previous.get(primary_key, previous.get(alt_key, None))
        
        if current_val is not None and previous_val is not None:
            if previous_val != 0:
                change_pct = ((current_val - previous_val) / previous_val) * 100
            else:
                change_pct = 100 if current_val > 0 else 0
            
            change_direction = "↑" if change_pct > 0 else "↓" if change_pct < 0 else "→"
            
            if prefix == "$":
                comparison = f"{label}: {prefix}{current_val:,.2f} vs {prefix}{previous_val:,.2f} ({change_direction} {abs(change_pct):.1f}%)"
            elif prefix == "%":
                comparison = f"{label}: {current_val:.1f}{prefix} vs {previous_val:.1f}{prefix} ({change_direction} {abs(change_pct):.1f}%)"
            else:
                comparison = f"{label}: {current_val:,} vs {previous_val:,} ({change_direction} {abs(change_pct):.1f}%)"
            
            comparisons.append(comparison)
            
            # Track improvements and declines
            is_improvement = (change_pct > 0 and higher_is_better) or (change_pct < 0 and not higher_is_better)
            if abs(change_pct) > 5:  # Only significant changes
                if is_improvement:
                    improvements.append(f"{label}: +{abs(change_pct):.1f}%")
                else:
                    declines.append(f"{label}: -{abs(change_pct):.1f}%")
    
    if not comparisons:
        return "Error: No comparable metrics found between the two periods"
    
    result = f"""Period-over-Period Comparison:

Metrics Comparison:
{chr(10).join(f'- {c}' for c in comparisons)}
"""
    
    if improvements:
        result += f"""
Improvements:
{chr(10).join(f'✓ {i}' for i in improvements)}
"""
    
    if declines:
        result += f"""
Areas of Concern:
{chr(10).join(f'✗ {d}' for d in declines)}
"""
    
    result += f"""
Summary: {len(improvements)} improvements, {len(declines)} declines out of {len(comparisons)} metrics compared"""
    
    return result


def _calculate_metrics_impl(data: Dict[str, Any], metrics: List[str]) -> str:
    """Internal implementation of calculate_metrics.
    
    Computes specified KPIs from provided data.
    This is a deterministic, read-only analysis operation.
    
    Args:
        data: Data dictionary containing raw values
        metrics: List of metrics to calculate
        
    Returns:
        Calculated metrics or error message
        
    Requirements: 1.1, 5.2
    """
    # Validate data structure
    if not isinstance(data, dict):
        return "Error: data must be a dictionary"
    
    if not data:
        return "Error: data cannot be empty"
    
    # Validate metrics
    if not isinstance(metrics, list):
        return "Error: metrics must be a list"
    
    if not metrics:
        return "Error: at least one metric must be specified"
    
    # Normalize metrics
    normalized_metrics = [m.lower().strip() for m in metrics]
    
    invalid_metrics = [m for m in normalized_metrics if m not in VALID_METRICS]
    if invalid_metrics:
        return f"Error: Invalid metrics: {', '.join(invalid_metrics)}. Valid options: {', '.join(VALID_METRICS)}"
    
    calculated = []
    
    for metric in normalized_metrics:
        if metric == "revenue":
            value = data.get("total_revenue", data.get("revenue", 0))
            calculated.append(f"Revenue: ${value:,.2f}")
        
        elif metric == "orders":
            value = data.get("total_orders", data.get("orders", 0))
            calculated.append(f"Orders: {value:,}")
        
        elif metric == "average_order_value":
            revenue = data.get("total_revenue", data.get("revenue", 0))
            orders = data.get("total_orders", data.get("orders", 0))
            if orders > 0:
                aov = revenue / orders
                calculated.append(f"Average Order Value: ${aov:,.2f}")
            else:
                aov = data.get("average_order_value", data.get("aov", 0))
                if aov > 0:
                    calculated.append(f"Average Order Value: ${aov:,.2f}")
                else:
                    calculated.append("Average Order Value: Unable to calculate (no orders)")
        
        elif metric == "conversion_rate":
            visitors = data.get("visitors", data.get("sessions", 0))
            orders = data.get("total_orders", data.get("orders", 0))
            if visitors > 0:
                rate = (orders / visitors) * 100
                calculated.append(f"Conversion Rate: {rate:.2f}%")
            else:
                rate = data.get("conversion_rate", data.get("conversion", 0))
                if rate > 0:
                    calculated.append(f"Conversion Rate: {rate:.2f}%")
                else:
                    calculated.append("Conversion Rate: Unable to calculate (no visitor data)")
        
        elif metric == "customer_acquisition_cost":
            marketing_spend = data.get("marketing_spend", data.get("ad_spend", 0))
            new_customers = data.get("new_customers", data.get("acquired_customers", 0))
            if new_customers > 0:
                cac = marketing_spend / new_customers
                calculated.append(f"Customer Acquisition Cost: ${cac:,.2f}")
            else:
                cac = data.get("customer_acquisition_cost", data.get("cac", 0))
                if cac > 0:
                    calculated.append(f"Customer Acquisition Cost: ${cac:,.2f}")
                else:
                    calculated.append("Customer Acquisition Cost: Unable to calculate (no customer data)")
        
        elif metric == "customer_lifetime_value":
            aov = data.get("average_order_value", data.get("aov", 0))
            purchase_frequency = data.get("purchase_frequency", data.get("avg_purchases_per_customer", 0))
            customer_lifespan = data.get("customer_lifespan_years", data.get("avg_customer_years", 1))
            if aov > 0 and purchase_frequency > 0:
                ltv = aov * purchase_frequency * customer_lifespan
                calculated.append(f"Customer Lifetime Value: ${ltv:,.2f}")
            else:
                ltv = data.get("customer_lifetime_value", data.get("ltv", 0))
                if ltv > 0:
                    calculated.append(f"Customer Lifetime Value: ${ltv:,.2f}")
                else:
                    calculated.append("Customer Lifetime Value: Unable to calculate (insufficient data)")
        
        elif metric == "repeat_purchase_rate":
            repeat_customers = data.get("repeat_customers", data.get("returning_customers", 0))
            total_customers = data.get("total_customers", data.get("customers", 0))
            if total_customers > 0:
                rate = (repeat_customers / total_customers) * 100
                calculated.append(f"Repeat Purchase Rate: {rate:.1f}%")
            else:
                rate = data.get("repeat_purchase_rate", data.get("retention_rate", 0))
                if rate > 0:
                    calculated.append(f"Repeat Purchase Rate: {rate:.1f}%")
                else:
                    calculated.append("Repeat Purchase Rate: Unable to calculate (no customer data)")
        
        elif metric == "gross_margin":
            revenue = data.get("total_revenue", data.get("revenue", 0))
            cogs = data.get("cost_of_goods_sold", data.get("cogs", 0))
            if revenue > 0:
                margin = ((revenue - cogs) / revenue) * 100
                calculated.append(f"Gross Margin: {margin:.1f}%")
            else:
                margin = data.get("gross_margin", data.get("margin", 0))
                if margin > 0:
                    calculated.append(f"Gross Margin: {margin:.1f}%")
                else:
                    calculated.append("Gross Margin: Unable to calculate (no revenue data)")
    
    return f"""Calculated Metrics:

{chr(10).join(calculated)}

Metrics Requested: {len(metrics)}
Metrics Calculated: {len(calculated)}"""


# Decorated tools for agent use
@function_tool
def analyze_revenue_trends(data_json: str, period: str = "monthly") -> str:
    """Analyze revenue patterns and trends from sales data.
    
    This is a read-only analysis operation that identifies revenue patterns
    without modifying any data.
    
    Args:
        data_json: JSON string containing sales data with revenue information
        period: Analysis period (daily, weekly, monthly, quarterly, yearly)
        
    Returns:
        Revenue trend analysis or error message
    """
    data = _parse_json_data(data_json)
    if isinstance(data, str):  # Error message
        return data
    return _analyze_revenue_trends_impl(data, period)


@function_tool
def detect_bottlenecks(data_json: str) -> str:
    """Identify conversion and operational bottlenecks from data.
    
    This is a read-only analysis operation that identifies issues
    without modifying any data.
    
    Args:
        data_json: JSON string containing operational data with metrics
        
    Returns:
        Bottleneck analysis or error message
    """
    data = _parse_json_data(data_json)
    if isinstance(data, str):  # Error message
        return data
    return _detect_bottlenecks_impl(data)


@function_tool
def compare_periods(current_json: str, previous_json: str) -> str:
    """Perform period-over-period comparison of metrics.
    
    This is a read-only analysis operation that compares data
    without modifying any data.
    
    Args:
        current_json: JSON string containing current period data
        previous_json: JSON string containing previous period data
        
    Returns:
        Period comparison analysis or error message
    """
    current = _parse_json_data(current_json)
    if isinstance(current, str):  # Error message
        return f"Error in current period data: {current}"
    
    previous = _parse_json_data(previous_json)
    if isinstance(previous, str):  # Error message
        return f"Error in previous period data: {previous}"
    
    return _compare_periods_impl(current, previous)


@function_tool
def calculate_metrics(data_json: str, metrics: List[str]) -> str:
    """Calculate specified KPIs from provided data.
    
    This is a read-only analysis operation that computes metrics
    without modifying any data.
    
    Args:
        data_json: JSON string containing raw data values
        metrics: List of metrics to calculate (revenue, orders, average_order_value,
                 conversion_rate, customer_acquisition_cost, customer_lifetime_value,
                 repeat_purchase_rate, gross_margin)
        
    Returns:
        Calculated metrics or error message
    """
    data = _parse_json_data(data_json)
    if isinstance(data, str):  # Error message
        return data
    return _calculate_metrics_impl(data, metrics)


__all__ = [
    # Decorated tools for agent use
    "analyze_revenue_trends",
    "detect_bottlenecks",
    "compare_periods",
    "calculate_metrics",
    # Internal implementations for testing
    "_analyze_revenue_trends_impl",
    "_detect_bottlenecks_impl",
    "_compare_periods_impl",
    "_calculate_metrics_impl",
    # Constants
    "VALID_PERIODS",
    "VALID_METRICS",
]
