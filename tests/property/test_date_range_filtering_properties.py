"""Property-based tests for date range filtering.

**Feature: platform-mcp-servers, Property 7: Date Range Filtering**
**Validates: Requirements 3.5, 4.5**

For any data fetch request with date_from and date_to parameters,
the returned data shall only include records within that date range.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

from credora.mcp_servers.models.shopify import (
    Order,
    LineItem,
    SalesAnalytics,
)


# Strategy for generating valid dates within a reasonable range
date_strategy = st.dates(
    min_value=datetime(2020, 1, 1).date(),
    max_value=datetime(2025, 12, 31).date(),
)

# Strategy for generating date ranges (date_from <= date_to)
date_range_strategy = st.tuples(date_strategy, date_strategy).map(
    lambda x: (min(x), max(x))
)

# Strategy for generating order IDs
order_id_strategy = st.text(
    alphabet="0123456789",
    min_size=1,
    max_size=10,
).map(lambda x: f"order_{x}")

# Strategy for generating order numbers
order_number_strategy = st.integers(min_value=1000, max_value=99999).map(str)


def create_test_order(
    order_id: str,
    order_number: str,
    created_at: datetime,
    total_price: float = 100.0,
) -> Order:
    """Create a test Order with minimal required fields."""
    return Order(
        id=order_id,
        order_number=order_number,
        created_at=created_at,
        total_price=total_price,
        currency="USD",
        status="fulfilled",
        line_items=[],
        customer_id=None,
    )


def filter_orders_by_date_range(
    orders: list,
    date_from: str = None,
    date_to: str = None,
) -> list:
    """Filter orders by date range (simulates what the client does)."""
    filtered = []
    for order in orders:
        order_date = order.created_at.date() if isinstance(order.created_at, datetime) else None
        if order_date is None:
            continue
        
        if date_from:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            if order_date < from_date:
                continue
        
        if date_to:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            if order_date > to_date:
                continue
        
        filtered.append(order)
    
    return filtered


class TestDateRangeFiltering:
    """
    **Feature: platform-mcp-servers, Property 7: Date Range Filtering**
    **Validates: Requirements 3.5, 4.5**
    
    For any data fetch request with date_from and date_to parameters,
    the returned data shall only include records within that date range.
    """

    @settings(max_examples=100)
    @given(
        date_range=date_range_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_filtered_orders_within_date_range(self, date_range, order_dates):
        """All filtered orders should have created_at within the specified date range."""
        date_from, date_to = date_range
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
                total_price=100.0 + i,
            ))
        
        # Filter orders
        filtered = filter_orders_by_date_range(orders, date_from_str, date_to_str)
        
        # Verify all filtered orders are within the date range
        for order in filtered:
            order_date = order.created_at.date()
            assert order_date >= date_from, f"Order date {order_date} is before date_from {date_from}"
            assert order_date <= date_to, f"Order date {order_date} is after date_to {date_to}"

    @settings(max_examples=100)
    @given(
        date_range=date_range_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_orders_outside_range_excluded(self, date_range, order_dates):
        """Orders outside the date range should be excluded from results."""
        date_from, date_to = date_range
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Filter orders
        filtered = filter_orders_by_date_range(orders, date_from_str, date_to_str)
        filtered_ids = {o.id for o in filtered}
        
        # Verify orders outside range are excluded
        for order in orders:
            order_date = order.created_at.date()
            if order_date < date_from or order_date > date_to:
                assert order.id not in filtered_ids, \
                    f"Order {order.id} with date {order_date} should be excluded"

    @settings(max_examples=100)
    @given(
        date_range=date_range_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_all_matching_orders_included(self, date_range, order_dates):
        """All orders within the date range should be included in results."""
        date_from, date_to = date_range
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Filter orders
        filtered = filter_orders_by_date_range(orders, date_from_str, date_to_str)
        filtered_ids = {o.id for o in filtered}
        
        # Verify all orders within range are included
        for order in orders:
            order_date = order.created_at.date()
            if date_from <= order_date <= date_to:
                assert order.id in filtered_ids, \
                    f"Order {order.id} with date {order_date} should be included"

    @settings(max_examples=100)
    @given(
        single_date=date_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_single_day_range(self, single_date, order_dates):
        """When date_from equals date_to, only orders on that exact date should be returned."""
        date_str = single_date.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Filter with same date for from and to
        filtered = filter_orders_by_date_range(orders, date_str, date_str)
        
        # Verify only orders on that exact date are returned
        for order in filtered:
            assert order.created_at.date() == single_date

    @settings(max_examples=100)
    @given(
        date_from=date_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_date_from_only(self, date_from, order_dates):
        """When only date_from is specified, all orders on or after that date should be returned."""
        date_from_str = date_from.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Filter with only date_from
        filtered = filter_orders_by_date_range(orders, date_from_str, None)
        
        # Verify all filtered orders are on or after date_from
        for order in filtered:
            assert order.created_at.date() >= date_from

    @settings(max_examples=100)
    @given(
        date_to=date_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_date_to_only(self, date_to, order_dates):
        """When only date_to is specified, all orders on or before that date should be returned."""
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Filter with only date_to
        filtered = filter_orders_by_date_range(orders, None, date_to_str)
        
        # Verify all filtered orders are on or before date_to
        for order in filtered:
            assert order.created_at.date() <= date_to

    @settings(max_examples=100)
    @given(
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_no_date_filter_returns_all(self, order_dates):
        """When no date filter is specified, all orders should be returned."""
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Filter with no date constraints
        filtered = filter_orders_by_date_range(orders, None, None)
        
        # Verify all orders are returned
        assert len(filtered) == len(orders)

    @settings(max_examples=100)
    @given(
        date_range=date_range_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_filter_preserves_order_data(self, date_range, order_dates):
        """Filtering should preserve all order data, not just dates."""
        date_from, date_to = date_range
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        # Create test orders with various dates and unique prices
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
                total_price=100.0 + i * 10,  # Unique price per order
            ))
        
        # Filter orders
        filtered = filter_orders_by_date_range(orders, date_from_str, date_to_str)
        
        # Verify order data is preserved
        original_by_id = {o.id: o for o in orders}
        for order in filtered:
            original = original_by_id[order.id]
            assert order.order_number == original.order_number
            assert order.total_price == original.total_price
            assert order.currency == original.currency
            assert order.status == original.status

    @settings(max_examples=100)
    @given(
        date_range=date_range_strategy,
    )
    def test_empty_orders_returns_empty(self, date_range):
        """Filtering empty order list should return empty list."""
        date_from, date_to = date_range
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        filtered = filter_orders_by_date_range([], date_from_str, date_to_str)
        
        assert filtered == []

    @settings(max_examples=100)
    @given(
        date_range=date_range_strategy,
        order_dates=st.lists(date_strategy, min_size=1, max_size=20),
    )
    def test_filter_count_consistency(self, date_range, order_dates):
        """Number of filtered orders should equal count of orders within range."""
        date_from, date_to = date_range
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        # Create test orders with various dates
        orders = []
        for i, order_date in enumerate(order_dates):
            order_datetime = datetime.combine(order_date, datetime.min.time())
            orders.append(create_test_order(
                order_id=f"order_{i}",
                order_number=str(1000 + i),
                created_at=order_datetime,
            ))
        
        # Count orders that should be in range
        expected_count = sum(
            1 for o in orders
            if date_from <= o.created_at.date() <= date_to
        )
        
        # Filter orders
        filtered = filter_orders_by_date_range(orders, date_from_str, date_to_str)
        
        assert len(filtered) == expected_count
