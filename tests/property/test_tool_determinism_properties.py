"""Property-based tests for tool determinism.

**Feature: credora-cfo-agent**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List

from credora.tools.analytics import (
    _analyze_revenue_trends_impl,
    _detect_bottlenecks_impl,
    _compare_periods_impl,
    _calculate_metrics_impl,
    VALID_PERIODS,
    VALID_METRICS,
)


# Strategies for generating test data
period_strategy = st.sampled_from(VALID_PERIODS)
metrics_strategy = st.lists(
    st.sampled_from(VALID_METRICS),
    min_size=1,
    max_size=len(VALID_METRICS),
    unique=True,
)

# Strategy for generating revenue data dictionaries
revenue_data_strategy = st.fixed_dictionaries({
    "total_revenue": st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    "previous_revenue": st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    "average_order_value": st.floats(min_value=0, max_value=10_000, allow_nan=False, allow_infinity=False),
})

# Strategy for generating bottleneck data dictionaries
bottleneck_data_strategy = st.fixed_dictionaries({
    "conversion_rate": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "cart_abandonment_rate": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "fulfillment_rate": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "average_fulfillment_days": st.floats(min_value=0, max_value=30, allow_nan=False, allow_infinity=False),
    "customer_acquisition_cost": st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
    "customer_lifetime_value": st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
})

# Strategy for generating period comparison data
period_data_strategy = st.fixed_dictionaries({
    "total_revenue": st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    "total_orders": st.integers(min_value=0, max_value=100_000),
    "average_order_value": st.floats(min_value=0, max_value=10_000, allow_nan=False, allow_infinity=False),
    "conversion_rate": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "customer_count": st.integers(min_value=0, max_value=100_000),
    "fulfillment_rate": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
})

# Strategy for generating metrics calculation data
metrics_data_strategy = st.fixed_dictionaries({
    "total_revenue": st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    "total_orders": st.integers(min_value=0, max_value=100_000),
    "visitors": st.integers(min_value=0, max_value=1_000_000),
    "marketing_spend": st.floats(min_value=0, max_value=100_000, allow_nan=False, allow_infinity=False),
    "new_customers": st.integers(min_value=0, max_value=10_000),
    "average_order_value": st.floats(min_value=0, max_value=10_000, allow_nan=False, allow_infinity=False),
    "purchase_frequency": st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    "customer_lifespan_years": st.floats(min_value=0.1, max_value=20, allow_nan=False, allow_infinity=False),
    "repeat_customers": st.integers(min_value=0, max_value=10_000),
    "total_customers": st.integers(min_value=1, max_value=100_000),
    "cost_of_goods_sold": st.floats(min_value=0, max_value=500_000, allow_nan=False, allow_infinity=False),
})


class TestToolDeterminism:
    """
    **Feature: credora-cfo-agent, Property 5: Tool Determinism**
    **Validates: Requirements 3.3**
    
    For any tool and any set of input parameters, invoking the tool multiple
    times with identical inputs shall produce identical outputs.
    """

    @settings(max_examples=100)
    @given(
        data=revenue_data_strategy,
        period=period_strategy,
    )
    def test_analyze_revenue_trends_is_deterministic(
        self, data: Dict[str, Any], period: str
    ):
        """analyze_revenue_trends should return identical results for identical inputs."""
        # Call the tool twice with the same inputs
        result1 = _analyze_revenue_trends_impl(data, period)
        result2 = _analyze_revenue_trends_impl(data, period)
        
        # Results should be identical
        assert result1 == result2, (
            f"analyze_revenue_trends produced different results for identical inputs:\n"
            f"First call: {result1}\n"
            f"Second call: {result2}"
        )

    @settings(max_examples=100)
    @given(data=bottleneck_data_strategy)
    def test_detect_bottlenecks_is_deterministic(self, data: Dict[str, Any]):
        """detect_bottlenecks should return identical results for identical inputs."""
        # Call the tool twice with the same inputs
        result1 = _detect_bottlenecks_impl(data)
        result2 = _detect_bottlenecks_impl(data)
        
        # Results should be identical
        assert result1 == result2, (
            f"detect_bottlenecks produced different results for identical inputs:\n"
            f"First call: {result1}\n"
            f"Second call: {result2}"
        )

    @settings(max_examples=100)
    @given(
        current=period_data_strategy,
        previous=period_data_strategy,
    )
    def test_compare_periods_is_deterministic(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ):
        """compare_periods should return identical results for identical inputs."""
        # Call the tool twice with the same inputs
        result1 = _compare_periods_impl(current, previous)
        result2 = _compare_periods_impl(current, previous)
        
        # Results should be identical
        assert result1 == result2, (
            f"compare_periods produced different results for identical inputs:\n"
            f"First call: {result1}\n"
            f"Second call: {result2}"
        )

    @settings(max_examples=100)
    @given(
        data=metrics_data_strategy,
        metrics=metrics_strategy,
    )
    def test_calculate_metrics_is_deterministic(
        self, data: Dict[str, Any], metrics: List[str]
    ):
        """calculate_metrics should return identical results for identical inputs."""
        # Call the tool twice with the same inputs
        result1 = _calculate_metrics_impl(data, metrics)
        result2 = _calculate_metrics_impl(data, metrics)
        
        # Results should be identical
        assert result1 == result2, (
            f"calculate_metrics produced different results for identical inputs:\n"
            f"First call: {result1}\n"
            f"Second call: {result2}"
        )

    @settings(max_examples=100)
    @given(
        data=revenue_data_strategy,
        period=period_strategy,
    )
    def test_analyze_revenue_trends_multiple_calls_deterministic(
        self, data: Dict[str, Any], period: str
    ):
        """analyze_revenue_trends should be deterministic across multiple calls."""
        # Call the tool multiple times
        results = [_analyze_revenue_trends_impl(data, period) for _ in range(5)]
        
        # All results should be identical
        assert all(r == results[0] for r in results), (
            "analyze_revenue_trends produced inconsistent results across multiple calls"
        )

    @settings(max_examples=100)
    @given(data=bottleneck_data_strategy)
    def test_detect_bottlenecks_multiple_calls_deterministic(self, data: Dict[str, Any]):
        """detect_bottlenecks should be deterministic across multiple calls."""
        # Call the tool multiple times
        results = [_detect_bottlenecks_impl(data) for _ in range(5)]
        
        # All results should be identical
        assert all(r == results[0] for r in results), (
            "detect_bottlenecks produced inconsistent results across multiple calls"
        )
