"""Example conversation runner for demonstrating CFO Agent capabilities.

This module provides example queries and a runner for testing conversations
with the Credora CFO Agent system.

Requirements: 5.4
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ExampleQuery:
    """Represents an example query with metadata."""
    
    category: str
    description: str
    query: str
    expected_agent: str


# Example queries demonstrating each agent capability
EXAMPLE_QUERIES: List[ExampleQuery] = [
    # Onboarding Agent examples
    ExampleQuery(
        category="Onboarding",
        description="New user getting started",
        query="I'm new here, help me get started",
        expected_agent="Onboarding Agent",
    ),
    ExampleQuery(
        category="Onboarding",
        description="Connect Shopify store",
        query="I want to connect my Shopify store",
        expected_agent="Onboarding Agent",
    ),
    ExampleQuery(
        category="Onboarding",
        description="Set up account",
        query="Help me set up my account for my WooCommerce store",
        expected_agent="Onboarding Agent",
    ),
    
    # Data Fetcher Agent examples
    ExampleQuery(
        category="Data Retrieval",
        description="Get sales data",
        query="Show me my sales from the last 30 days",
        expected_agent="Data Fetcher Agent",
    ),
    ExampleQuery(
        category="Data Retrieval",
        description="Get pending orders",
        query="What are my pending orders?",
        expected_agent="Data Fetcher Agent",
    ),
    ExampleQuery(
        category="Data Retrieval",
        description="List products",
        query="List my top 10 products",
        expected_agent="Data Fetcher Agent",
    ),
    ExampleQuery(
        category="Data Retrieval",
        description="Get customer segments",
        query="Show me my VIP customers",
        expected_agent="Data Fetcher Agent",
    ),
    
    # Analytics Agent examples
    ExampleQuery(
        category="Analytics",
        description="Revenue trend analysis",
        query="Why did my revenue drop last month?",
        expected_agent="Analytics Agent",
    ),
    ExampleQuery(
        category="Analytics",
        description="Identify bottlenecks",
        query="Find bottlenecks in my sales funnel",
        expected_agent="Analytics Agent",
    ),
    ExampleQuery(
        category="Analytics",
        description="Period comparison",
        query="Compare my performance this month vs last month",
        expected_agent="Analytics Agent",
    ),
    ExampleQuery(
        category="Analytics",
        description="Trend analysis",
        query="Analyze my sales trends over the past quarter",
        expected_agent="Analytics Agent",
    ),
    
    # Competitor Agent examples
    ExampleQuery(
        category="Competitor Analysis",
        description="Market trends",
        query="What are the current market trends in e-commerce?",
        expected_agent="Competitor Agent",
    ),
    ExampleQuery(
        category="Competitor Analysis",
        description="Competitor pricing",
        query="How do my prices compare to competitors?",
        expected_agent="Competitor Agent",
    ),
    ExampleQuery(
        category="Competitor Analysis",
        description="Industry benchmarks",
        query="What are the industry benchmarks for conversion rates?",
        expected_agent="Competitor Agent",
    ),
    
    # Insight Agent examples
    ExampleQuery(
        category="Recommendations",
        description="Growth recommendations",
        query="What should I focus on to grow my business?",
        expected_agent="Insight Agent",
    ),
    ExampleQuery(
        category="Recommendations",
        description="Cost optimization",
        query="How can I optimize my costs?",
        expected_agent="Insight Agent",
    ),
    ExampleQuery(
        category="Recommendations",
        description="Action prioritization",
        query="What actions should I prioritize this quarter?",
        expected_agent="Insight Agent",
    ),
    ExampleQuery(
        category="Recommendations",
        description="Improvement suggestions",
        query="Give me specific recommendations to improve my conversion rate",
        expected_agent="Insight Agent",
    ),
    
    # Complex multi-agent queries
    ExampleQuery(
        category="Complex Query",
        description="Full business analysis",
        query="Analyze my business performance and give me actionable recommendations",
        expected_agent="Multiple Agents",
    ),
    ExampleQuery(
        category="Complex Query",
        description="Comprehensive review",
        query="Review my sales data, identify issues, and suggest improvements",
        expected_agent="Multiple Agents",
    ),
]


def get_examples_by_category(category: str) -> List[ExampleQuery]:
    """Get example queries filtered by category.
    
    Args:
        category: The category to filter by
        
    Returns:
        List of ExampleQuery objects matching the category
    """
    return [q for q in EXAMPLE_QUERIES if q.category == category]


def get_all_categories() -> List[str]:
    """Get all unique categories.
    
    Returns:
        List of unique category names
    """
    return list(set(q.category for q in EXAMPLE_QUERIES))


def print_examples() -> None:
    """Print all example queries organized by category."""
    print("\n" + "=" * 70)
    print("  Credora CFO Agent - Example Queries")
    print("=" * 70)
    
    categories = get_all_categories()
    
    for category in sorted(categories):
        print(f"\n{category}:")
        print("-" * 50)
        
        examples = get_examples_by_category(category)
        for i, example in enumerate(examples, 1):
            print(f"  {i}. {example.description}")
            print(f"     Query: \"{example.query}\"")
            print(f"     Expected Agent: {example.expected_agent}")
            print()


__all__ = [
    "ExampleQuery",
    "EXAMPLE_QUERIES",
    "get_examples_by_category",
    "get_all_categories",
    "print_examples",
]
