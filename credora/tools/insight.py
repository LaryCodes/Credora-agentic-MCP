"""Insight tools for generating actionable recommendations in business language.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5

These tools translate complex metrics into simple business language,
provide specific actions, identify root causes, and prioritize by revenue impact.
"""

import json
from typing import Dict, List, Any
from agents import function_tool


# Priority levels for recommendations
PRIORITY_LEVELS = {
    1: "Critical - Immediate action required",
    2: "High - Address within this week",
    3: "Medium - Address within this month",
    4: "Low - Address when convenient",
    5: "Optional - Nice to have",
}

# Valid recommendation categories
VALID_CATEGORIES = [
    "revenue_growth",
    "cost_reduction",
    "conversion_optimization",
    "customer_retention",
    "operational_efficiency",
    "inventory_management",
    "marketing_optimization",
]


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


def _check_data_sufficiency(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, List[str]]:
    """Check if data has sufficient fields for analysis.
    
    Args:
        data: Data dictionary to check
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_sufficient, missing_fields)
    """
    missing = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing.append(field)
    return len(missing) == 0, missing



def _generate_recommendation_impl(analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Internal implementation of generate_recommendation.
    
    Creates actionable advice based on analysis results and business context.
    Translates complex metrics into simple business language.
    
    Args:
        analysis: Analysis results dictionary containing metrics and findings
        context: Business context dictionary (goals, industry, etc.)
        
    Returns:
        Actionable recommendation in business language or error message
        
    Requirements: 7.1, 7.2, 7.3, 7.5
    """
    # Validate inputs
    if not isinstance(analysis, dict):
        return "Error: analysis must be a dictionary"
    if not isinstance(context, dict):
        return "Error: context must be a dictionary"
    
    # Check for minimum required data
    if not analysis:
        return """Insufficient Data for Recommendation:

The analysis data provided is empty. To generate actionable recommendations, please provide:
- Revenue or sales metrics
- Conversion rates or traffic data
- Customer acquisition or retention metrics
- Operational metrics (fulfillment, inventory)

Without this data, specific recommendations cannot be generated."""
    
    recommendations = []
    explanations = []
    
    # Extract key metrics from analysis
    revenue = analysis.get("total_revenue", analysis.get("revenue", 0))
    revenue_change = analysis.get("revenue_change", analysis.get("growth_rate", 0))
    conversion_rate = analysis.get("conversion_rate", analysis.get("conversion", 0))
    cart_abandonment = analysis.get("cart_abandonment_rate", analysis.get("abandonment_rate", 0))
    aov = analysis.get("average_order_value", analysis.get("aov", 0))
    cac = analysis.get("customer_acquisition_cost", analysis.get("cac", 0))
    ltv = analysis.get("customer_lifetime_value", analysis.get("ltv", 0))
    
    # Extract context
    business_goals = context.get("business_goals", context.get("goals", []))
    industry = context.get("industry", "ecommerce")
    
    # Generate recommendations based on data patterns
    
    # Revenue decline analysis
    if revenue_change < -10:
        explanations.append(
            f"Your revenue has dropped by {abs(revenue_change):.1f}%. "
            "This isn't just a number - it means fewer customers are buying or they're spending less per order."
        )
        if conversion_rate > 0 and conversion_rate < 2:
            recommendations.append({
                "action": "Optimize your checkout process to reduce friction",
                "reason": f"Your conversion rate ({conversion_rate}%) is below the industry average of 2-3%. "
                         "This suggests visitors are interested but something is stopping them from buying.",
                "impact": "Could increase revenue by 20-40% if conversion improves to industry average",
                "priority": 1,
            })
        elif cart_abandonment > 70:
            recommendations.append({
                "action": "Implement cart abandonment email recovery",
                "reason": f"With {cart_abandonment}% cart abandonment, you're losing potential sales at the final step. "
                         "These are customers who wanted to buy but didn't complete the purchase.",
                "impact": "Recovering even 10% of abandoned carts could significantly boost revenue",
                "priority": 1,
            })
        else:
            recommendations.append({
                "action": "Review your marketing channels and customer acquisition strategy",
                "reason": "Revenue decline without clear conversion issues suggests you may be attracting "
                         "fewer visitors or the wrong audience.",
                "impact": "Identifying and fixing traffic issues can stabilize and grow revenue",
                "priority": 2,
            })
    
    # Low conversion rate
    if conversion_rate > 0 and conversion_rate < 1.5:
        explanations.append(
            f"Your conversion rate of {conversion_rate}% means only {conversion_rate} out of every 100 visitors "
            "are buying. The typical e-commerce store converts 2-3%."
        )
        recommendations.append({
            "action": "A/B test your product pages and checkout flow",
            "reason": "Low conversion often comes from unclear value propositions, complicated checkout, "
                     "or trust issues. Testing helps identify what's blocking purchases.",
            "impact": "Doubling conversion rate doubles revenue without spending more on marketing",
            "priority": 1 if not any(r["priority"] == 1 for r in recommendations) else 2,
        })
    
    # High cart abandonment
    if cart_abandonment > 75:
        explanations.append(
            f"You're losing {cart_abandonment}% of customers at checkout. "
            "These people wanted to buy but something stopped them at the last moment."
        )
        if not any("cart" in r["action"].lower() for r in recommendations):
            recommendations.append({
                "action": "Simplify checkout and add trust signals",
                "reason": "High abandonment usually means unexpected costs (shipping), complicated forms, "
                         "or lack of trust. Address these friction points.",
                "impact": "Reducing abandonment by 10% could increase completed orders significantly",
                "priority": 2,
            })
    
    # Customer acquisition cost vs lifetime value
    if cac > 0 and ltv > 0:
        ltv_cac_ratio = ltv / cac
        if ltv_cac_ratio < 3:
            explanations.append(
                f"You're spending ${cac:.2f} to acquire each customer, but they're only worth ${ltv:.2f} over time. "
                f"A healthy ratio is 3:1 or higher - yours is {ltv_cac_ratio:.1f}:1."
            )
            if ltv_cac_ratio < 1:
                recommendations.append({
                    "action": "Immediately reduce customer acquisition spending",
                    "reason": "You're losing money on every new customer. Either reduce acquisition costs "
                             "or increase customer value through retention and upselling.",
                    "impact": "Critical for business sustainability - you're currently unprofitable per customer",
                    "priority": 1,
                })
            else:
                recommendations.append({
                    "action": "Focus on customer retention and repeat purchases",
                    "reason": "Increasing customer lifetime value is often cheaper than reducing acquisition costs. "
                             "Email marketing, loyalty programs, and great service help.",
                    "impact": "Improving LTV by 50% would bring your ratio to healthy levels",
                    "priority": 2,
                })
    
    # Low average order value
    if aov > 0 and aov < 50:
        explanations.append(
            f"Your average order is ${aov:.2f}. Small orders mean you need more customers to hit revenue goals."
        )
        recommendations.append({
            "action": "Implement upselling and cross-selling strategies",
            "reason": "Bundling products, showing 'frequently bought together', and offering free shipping "
                     "thresholds can increase order size without acquiring new customers.",
            "impact": "Increasing AOV by $10-20 can significantly improve profitability",
            "priority": 3,
        })
    
    # Check for goal alignment
    if "growth" in business_goals or "revenue_growth" in business_goals:
        if not any("revenue" in r.get("impact", "").lower() for r in recommendations):
            recommendations.append({
                "action": "Expand to new marketing channels or customer segments",
                "reason": "Your goal is growth, and current metrics suggest room for expansion. "
                         "Consider new channels like social commerce or new customer segments.",
                "impact": "New channels can provide 20-50% revenue growth when executed well",
                "priority": 3,
            })
    
    if "cost_optimization" in business_goals or "cost_reduction" in business_goals:
        recommendations.append({
            "action": "Audit your marketing spend by channel ROI",
            "reason": "Cost optimization starts with knowing which channels deliver results. "
                     "Cut underperforming channels and double down on winners.",
            "impact": "Typically 20-30% of marketing spend can be reallocated for better returns",
            "priority": 2 if not any(r["priority"] <= 2 for r in recommendations) else 3,
        })
    
    # If no specific recommendations, provide general guidance
    if not recommendations:
        return """Analysis Complete - No Critical Issues Found:

Based on the data provided, your metrics appear to be within acceptable ranges.

To provide more specific recommendations, consider sharing:
- Conversion rate and traffic data
- Customer acquisition costs
- Cart abandonment rates
- Customer lifetime value

General best practices:
1. Continuously test and optimize your checkout flow
2. Monitor customer acquisition cost vs lifetime value ratio
3. Implement customer retention strategies
4. Track and reduce cart abandonment"""
    
    # Sort recommendations by priority
    recommendations.sort(key=lambda x: x["priority"])
    
    # Build response
    response_parts = ["Business Recommendations:\n"]
    
    if explanations:
        response_parts.append("What the Data Shows:")
        for exp in explanations:
            response_parts.append(f"• {exp}")
        response_parts.append("")
    
    response_parts.append("Recommended Actions (in priority order):\n")
    
    for i, rec in enumerate(recommendations, 1):
        priority_label = PRIORITY_LEVELS.get(rec["priority"], "Medium")
        response_parts.append(f"{i}. {rec['action']}")
        response_parts.append(f"   Why: {rec['reason']}")
        response_parts.append(f"   Expected Impact: {rec['impact']}")
        response_parts.append(f"   Priority: {priority_label}")
        response_parts.append("")
    
    return "\n".join(response_parts)


def _explain_metric_change_impl(metric: str, change: float, data: Dict[str, Any]) -> str:
    """Internal implementation of explain_metric_change.
    
    Explains why a metric changed, identifying root causes not just symptoms.
    Translates technical metrics into business language.
    
    Args:
        metric: Name of the metric that changed
        change: Percentage change in the metric
        data: Supporting data dictionary with related metrics
        
    Returns:
        Explanation of metric change in business language or error message
        
    Requirements: 7.1, 7.3, 7.5
    """
    # Validate inputs
    if not metric or not metric.strip():
        return "Error: metric name is required"
    
    if not isinstance(change, (int, float)):
        return "Error: change must be a number (percentage)"
    
    if not isinstance(data, dict):
        return "Error: data must be a dictionary"
    
    metric_lower = metric.lower().strip()
    direction = "increased" if change > 0 else "decreased" if change < 0 else "remained stable"
    abs_change = abs(change)
    
    # Check for minimum data to explain
    if not data:
        return f"""Metric Change Explanation:

{metric.title()} has {direction} by {abs_change:.1f}%.

Insufficient Data for Root Cause Analysis:

To explain why this change occurred, please provide supporting data such as:
- Traffic or visitor counts
- Conversion rates
- Average order value
- Marketing spend
- Customer counts
- Operational metrics

Without this context, the specific cause cannot be determined."""
    
    explanations = []
    contributing_factors = []
    
    # Revenue change analysis
    if "revenue" in metric_lower:
        traffic = data.get("visitors", data.get("sessions", data.get("traffic", 0)))
        traffic_change = data.get("traffic_change", data.get("visitor_change", 0))
        conversion = data.get("conversion_rate", data.get("conversion", 0))
        conversion_change = data.get("conversion_change", 0)
        aov = data.get("average_order_value", data.get("aov", 0))
        aov_change = data.get("aov_change", 0)
        
        if change < 0:  # Revenue decreased
            explanations.append(
                f"Your revenue dropped {abs_change:.1f}%. Let's understand why this happened."
            )
            
            if traffic_change < -5:
                contributing_factors.append(
                    f"Fewer visitors: Traffic is down {abs(traffic_change):.1f}%. "
                    "This means fewer people are seeing your store, which directly impacts sales."
                )
            
            if conversion_change < -5:
                contributing_factors.append(
                    f"Lower conversion: Your conversion rate dropped {abs(conversion_change):.1f}%. "
                    "Visitors are coming but not buying as much as before."
                )
            
            if aov_change < -5:
                contributing_factors.append(
                    f"Smaller orders: Average order value is down {abs(aov_change):.1f}%. "
                    "Customers are buying less per transaction."
                )
            
            if not contributing_factors:
                explanations.append(
                    "The data doesn't show a clear single cause. The decline may be due to "
                    "a combination of small changes across traffic, conversion, and order value."
                )
        else:  # Revenue increased
            explanations.append(
                f"Great news! Your revenue grew {abs_change:.1f}%. Here's what's driving this growth."
            )
            
            if traffic_change > 5:
                contributing_factors.append(
                    f"More visitors: Traffic is up {traffic_change:.1f}%. "
                    "More people are discovering your store."
                )
            
            if conversion_change > 5:
                contributing_factors.append(
                    f"Better conversion: Your conversion rate improved {conversion_change:.1f}%. "
                    "Visitors are more likely to buy."
                )
            
            if aov_change > 5:
                contributing_factors.append(
                    f"Larger orders: Average order value increased {aov_change:.1f}%. "
                    "Customers are spending more per transaction."
                )
    
    # Conversion rate change analysis
    elif "conversion" in metric_lower:
        bounce_rate = data.get("bounce_rate", 0)
        bounce_change = data.get("bounce_rate_change", 0)
        cart_abandonment = data.get("cart_abandonment_rate", data.get("abandonment_rate", 0))
        abandonment_change = data.get("abandonment_change", 0)
        page_load_time = data.get("page_load_time", data.get("load_time", 0))
        
        if change < 0:
            explanations.append(
                f"Your conversion rate dropped {abs_change:.1f}%. "
                "This means fewer visitors are completing purchases."
            )
            
            if bounce_change > 5:
                contributing_factors.append(
                    f"Higher bounce rate: Up {bounce_change:.1f}%. "
                    "More visitors are leaving immediately without exploring your site."
                )
            
            if abandonment_change > 5:
                contributing_factors.append(
                    f"More cart abandonment: Up {abandonment_change:.1f}%. "
                    "Customers are adding items but not completing checkout."
                )
            
            if page_load_time > 3:
                contributing_factors.append(
                    f"Slow page load: {page_load_time:.1f} seconds. "
                    "Slow sites frustrate visitors and hurt conversion."
                )
        else:
            explanations.append(
                f"Your conversion rate improved {abs_change:.1f}%. "
                "More visitors are becoming customers."
            )
            
            if bounce_change < -5:
                contributing_factors.append(
                    f"Lower bounce rate: Down {abs(bounce_change):.1f}%. "
                    "Visitors are more engaged with your site."
                )
            
            if abandonment_change < -5:
                contributing_factors.append(
                    f"Less cart abandonment: Down {abs(abandonment_change):.1f}%. "
                    "More customers are completing their purchases."
                )
    
    # Customer acquisition cost change
    elif "acquisition" in metric_lower or "cac" in metric_lower:
        marketing_spend = data.get("marketing_spend", data.get("ad_spend", 0))
        spend_change = data.get("spend_change", data.get("marketing_change", 0))
        new_customers = data.get("new_customers", 0)
        customer_change = data.get("new_customer_change", 0)
        
        if change > 0:  # CAC increased (bad)
            explanations.append(
                f"It's costing {abs_change:.1f}% more to acquire each new customer. "
                "This squeezes your profit margins."
            )
            
            if spend_change > 5 and customer_change <= 0:
                contributing_factors.append(
                    f"Marketing spend up {spend_change:.1f}% but customer acquisition flat or down. "
                    "Your marketing efficiency has decreased."
                )
            
            if customer_change < -5:
                contributing_factors.append(
                    f"Fewer new customers: Down {abs(customer_change):.1f}%. "
                    "Even with similar spend, you're acquiring fewer customers."
                )
        else:  # CAC decreased (good)
            explanations.append(
                f"Great efficiency! Customer acquisition cost dropped {abs_change:.1f}%. "
                "You're getting more customers for your marketing dollar."
            )
            
            if customer_change > 5:
                contributing_factors.append(
                    f"More new customers: Up {customer_change:.1f}%. "
                    "Your marketing is reaching more potential buyers."
                )
    
    # Generic metric change
    else:
        explanations.append(
            f"{metric.title()} has {direction} by {abs_change:.1f}%."
        )
        
        # Look for any related changes in the data
        for key, value in data.items():
            if "change" in key.lower() and isinstance(value, (int, float)) and abs(value) > 5:
                related_metric = key.replace("_change", "").replace("change", "").strip()
                if value > 0:
                    contributing_factors.append(
                        f"{related_metric.title()} increased by {value:.1f}%, which may have contributed."
                    )
                else:
                    contributing_factors.append(
                        f"{related_metric.title()} decreased by {abs(value):.1f}%, which may have contributed."
                    )
    
    # Build response
    response_parts = [f"Why {metric.title()} Changed:\n"]
    
    for exp in explanations:
        response_parts.append(exp)
    
    response_parts.append("")
    
    if contributing_factors:
        response_parts.append("Contributing Factors:")
        for factor in contributing_factors:
            response_parts.append(f"• {factor}")
    else:
        response_parts.append(
            "Root Cause: The available data doesn't clearly indicate a single cause. "
            "Consider reviewing recent changes to your site, marketing, or external factors "
            "like seasonality or market conditions."
        )
    
    return "\n".join(response_parts)


def _prioritize_actions_impl(recommendations: List[Dict[str, Any]]) -> str:
    """Internal implementation of prioritize_actions.
    
    Ranks recommendations by potential revenue impact.
    Each recommendation must include a specific action.
    
    Args:
        recommendations: List of recommendation dictionaries
        
    Returns:
        Prioritized list of actions or error message
        
    Requirements: 7.2, 7.4
    """
    # Validate input
    if not isinstance(recommendations, list):
        return "Error: recommendations must be a list"
    
    if not recommendations:
        return """No Recommendations to Prioritize:

Please provide a list of recommendations to prioritize. Each recommendation should include:
- action: What specific action to take
- reason: Why this action is recommended
- expected_impact: What results to expect (optional but helpful)
- priority: Initial priority level 1-5 (optional)

Example:
[
  {"action": "Reduce checkout steps", "reason": "High cart abandonment", "expected_impact": "10-20% more conversions"},
  {"action": "Add trust badges", "reason": "Low conversion rate", "expected_impact": "5-10% conversion lift"}
]"""
    
    # Validate and normalize recommendations
    valid_recommendations = []
    for i, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            continue
        
        action = rec.get("action", "").strip()
        if not action:
            continue
        
        # Extract or estimate priority based on impact keywords
        priority = rec.get("priority", 3)
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            priority = 3
        
        reason = rec.get("reason", "No reason provided")
        impact = rec.get("expected_impact", rec.get("impact", "Impact not specified"))
        
        # Adjust priority based on impact keywords
        impact_lower = str(impact).lower()
        if any(word in impact_lower for word in ["critical", "immediate", "urgent", "significant"]):
            priority = min(priority, 1)
        elif any(word in impact_lower for word in ["high", "major", "substantial"]):
            priority = min(priority, 2)
        elif any(word in impact_lower for word in ["moderate", "medium"]):
            priority = min(priority, 3)
        elif any(word in impact_lower for word in ["low", "minor", "small"]):
            priority = max(priority, 4)
        
        # Estimate revenue impact score for sorting
        revenue_score = 0
        if "revenue" in impact_lower or "sales" in impact_lower:
            revenue_score += 10
        if "%" in impact:
            # Try to extract percentage
            import re
            percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', impact)
            if percentages:
                revenue_score += max(float(p) for p in percentages)
        if "conversion" in impact_lower:
            revenue_score += 8
        if "customer" in impact_lower:
            revenue_score += 5
        
        valid_recommendations.append({
            "action": action,
            "reason": reason,
            "impact": impact,
            "priority": priority,
            "revenue_score": revenue_score,
        })
    
    if not valid_recommendations:
        return """No Valid Recommendations Found:

The provided recommendations don't contain valid action items. 
Each recommendation must have an 'action' field with a non-empty value.

Please provide recommendations in this format:
{"action": "Specific action to take", "reason": "Why", "expected_impact": "Expected results"}"""
    
    # Sort by priority first, then by revenue score (descending)
    valid_recommendations.sort(key=lambda x: (x["priority"], -x["revenue_score"]))
    
    # Build response
    response_parts = ["Prioritized Action Plan:\n"]
    response_parts.append(f"Total Actions: {len(valid_recommendations)}\n")
    
    current_priority = None
    for i, rec in enumerate(valid_recommendations, 1):
        priority = rec["priority"]
        priority_label = PRIORITY_LEVELS.get(priority, "Medium")
        
        # Add priority header when it changes
        if priority != current_priority:
            current_priority = priority
            response_parts.append(f"\n--- {priority_label} ---\n")
        
        response_parts.append(f"{i}. {rec['action']}")
        response_parts.append(f"   Reason: {rec['reason']}")
        response_parts.append(f"   Expected Impact: {rec['impact']}")
        response_parts.append("")
    
    response_parts.append("\nExecution Guidance:")
    response_parts.append("• Start with Priority 1 (Critical) items immediately")
    response_parts.append("• Schedule Priority 2 (High) items for this week")
    response_parts.append("• Plan Priority 3 (Medium) items for this month")
    response_parts.append("• Address lower priorities as resources allow")
    
    return "\n".join(response_parts)


# Decorated tools for agent use
@function_tool
def generate_recommendation(analysis_json: str, context_json: str) -> str:
    """Generate actionable business recommendations from analysis results.
    
    Translates complex metrics into simple business language with specific
    actions and expected impacts. Identifies root causes, not just symptoms.
    
    Args:
        analysis_json: JSON string containing analysis results (metrics, findings)
        context_json: JSON string containing business context (goals, industry)
        
    Returns:
        Actionable recommendations in business language or error message
    """
    analysis = _parse_json_data(analysis_json)
    if isinstance(analysis, str):  # Error message
        return f"Error in analysis data: {analysis}"
    
    context = _parse_json_data(context_json)
    if isinstance(context, str):  # Error message
        return f"Error in context data: {context}"
    
    return _generate_recommendation_impl(analysis, context)


@function_tool
def explain_metric_change(metric: str, change: float, data_json: str) -> str:
    """Explain why a metric changed, identifying root causes.
    
    Translates technical metrics into business language and identifies
    contributing factors, not just symptoms.
    
    Args:
        metric: Name of the metric that changed (e.g., "revenue", "conversion_rate")
        change: Percentage change in the metric (positive or negative)
        data_json: JSON string containing supporting data with related metrics
        
    Returns:
        Explanation of metric change in business language or error message
    """
    data = _parse_json_data(data_json)
    if isinstance(data, str):  # Error message
        return f"Error in data: {data}"
    
    return _explain_metric_change_impl(metric, change, data)


@function_tool
def prioritize_actions(recommendations_json: str) -> str:
    """Prioritize recommendations by potential revenue impact.
    
    Takes a list of recommendations and orders them by priority,
    with guidance on execution timing.
    
    Args:
        recommendations_json: JSON string containing list of recommendations.
            Each recommendation should have: action, reason, expected_impact, priority (optional)
        
    Returns:
        Prioritized action plan or error message
    """
    try:
        recommendations = json.loads(recommendations_json)
        if not isinstance(recommendations, list):
            return "Error: recommendations_json must be a JSON array"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {str(e)}"
    
    return _prioritize_actions_impl(recommendations)


__all__ = [
    # Decorated tools for agent use
    "generate_recommendation",
    "explain_metric_change",
    "prioritize_actions",
    # Internal implementations for testing
    "_generate_recommendation_impl",
    "_explain_metric_change_impl",
    "_prioritize_actions_impl",
    # Helper functions
    "_parse_json_data",
    "_check_data_sufficiency",
    # Constants
    "PRIORITY_LEVELS",
    "VALID_CATEGORIES",
]
