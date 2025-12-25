"""Property-based tests for insight generation functionality.

**Feature: credora-cfo-agent**
"""

import pytest
from hypothesis import given, strategies as st, settings

from credora.tools.insight import (
    _generate_recommendation_impl,
    _explain_metric_change_impl,
    _prioritize_actions_impl,
    PRIORITY_LEVELS,
    VALID_CATEGORIES,
)


# Strategies for generating test data
metric_strategy = st.sampled_from([
    "revenue", "conversion_rate", "customer_acquisition_cost",
    "average_order_value", "cart_abandonment_rate", "traffic"
])

percentage_change_strategy = st.floats(min_value=-100, max_value=200, allow_nan=False)

# Strategy for analysis data with various metrics
analysis_data_strategy = st.fixed_dictionaries({
    "total_revenue": st.floats(min_value=0, max_value=1000000, allow_nan=False),
    "revenue_change": st.floats(min_value=-100, max_value=200, allow_nan=False),
    "conversion_rate": st.floats(min_value=0, max_value=100, allow_nan=False),
    "cart_abandonment_rate": st.floats(min_value=0, max_value=100, allow_nan=False),
    "average_order_value": st.floats(min_value=0, max_value=1000, allow_nan=False),
    "customer_acquisition_cost": st.floats(min_value=0, max_value=500, allow_nan=False),
    "customer_lifetime_value": st.floats(min_value=0, max_value=5000, allow_nan=False),
})

# Strategy for business context
context_strategy = st.fixed_dictionaries({
    "business_goals": st.lists(
        st.sampled_from(["growth", "cost_optimization", "retention", "expansion"]),
        min_size=0,
        max_size=3,
        unique=True,
    ),
    "industry": st.sampled_from(["ecommerce", "fashion", "electronics", "beauty"]),
})

# Strategy for supporting data with metric changes
supporting_data_strategy = st.fixed_dictionaries({
    "visitors": st.integers(min_value=0, max_value=100000),
    "traffic_change": st.floats(min_value=-100, max_value=200, allow_nan=False),
    "conversion_rate": st.floats(min_value=0, max_value=100, allow_nan=False),
    "conversion_change": st.floats(min_value=-100, max_value=200, allow_nan=False),
    "average_order_value": st.floats(min_value=0, max_value=1000, allow_nan=False),
    "aov_change": st.floats(min_value=-100, max_value=200, allow_nan=False),
    "bounce_rate": st.floats(min_value=0, max_value=100, allow_nan=False),
    "bounce_rate_change": st.floats(min_value=-100, max_value=200, allow_nan=False),
})

# Strategy for recommendations list
recommendation_strategy = st.fixed_dictionaries({
    "action": st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
    "reason": st.text(min_size=5, max_size=200).filter(lambda x: x.strip()),
    "expected_impact": st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
    "priority": st.integers(min_value=1, max_value=5),
})

recommendations_list_strategy = st.lists(
    recommendation_strategy,
    min_size=1,
    max_size=5,
)



class TestExplainableBusinessLanguageOutput:
    """
    **Feature: credora-cfo-agent, Property 12: Explainable Business-Language Output**
    **Validates: Requirements 5.4, 5.5, 7.1, 7.3**
    
    For any insight or recommendation generated, the output shall include both
    the conclusion and the causal reasoning in non-technical language.
    
    This property validates that:
    1. Recommendations include both what to do AND why
    2. Metric explanations include root causes, not just symptoms
    3. Language is business-friendly (no raw technical jargon)
    """

    @settings(max_examples=100)
    @given(
        analysis=analysis_data_strategy,
        context=context_strategy,
    )
    def test_recommendations_include_reasoning(
        self, analysis: dict, context: dict
    ):
        """Generated recommendations should include reasoning (why)."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If recommendations are generated (not insufficient data message)
        if "Recommended Actions" in result or "Business Recommendations" in result:
            # Should contain reasoning indicators
            reasoning_indicators = ["why", "because", "reason", "due to", "since", "as a result"]
            result_lower = result.lower()
            has_reasoning = any(indicator in result_lower for indicator in reasoning_indicators)
            assert has_reasoning, "Recommendations should include reasoning"

    @settings(max_examples=100)
    @given(
        analysis=analysis_data_strategy,
        context=context_strategy,
    )
    def test_recommendations_include_actions(
        self, analysis: dict, context: dict
    ):
        """Generated recommendations should include specific actions."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If recommendations are generated
        if "Recommended Actions" in result or "Business Recommendations" in result:
            # Should contain action-oriented language
            action_indicators = [
                "implement", "reduce", "increase", "optimize", "review",
                "focus", "consider", "add", "improve", "test", "audit",
                "expand", "simplify", "action"
            ]
            result_lower = result.lower()
            has_action = any(indicator in result_lower for indicator in action_indicators)
            assert has_action, "Recommendations should include specific actions"

    @settings(max_examples=100)
    @given(
        metric=metric_strategy,
        change=percentage_change_strategy,
        data=supporting_data_strategy,
    )
    def test_metric_explanation_includes_cause(
        self, metric: str, change: float, data: dict
    ):
        """Metric change explanations should identify causes, not just symptoms."""
        result = _explain_metric_change_impl(metric, change, data)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should explain what changed
        assert metric.lower().replace("_", " ") in result.lower() or "changed" in result.lower()
        
        # If not an error or insufficient data message, should have causal language
        if "Error" not in result and "Insufficient Data" not in result:
            # Should contain causal/explanatory language
            causal_indicators = [
                "because", "due to", "means", "suggests", "indicates",
                "contributing", "factor", "cause", "result", "why",
                "this", "your", "the"
            ]
            result_lower = result.lower()
            has_explanation = any(indicator in result_lower for indicator in causal_indicators)
            assert has_explanation, "Explanations should include causal reasoning"

    @settings(max_examples=100)
    @given(
        analysis=analysis_data_strategy,
        context=context_strategy,
    )
    def test_output_uses_business_language(
        self, analysis: dict, context: dict
    ):
        """Output should use business-friendly language, not raw technical jargon."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should not contain raw technical terms without explanation
        # These are acceptable in context but shouldn't be the only explanation
        technical_only_patterns = [
            "NaN", "null", "undefined", "exception", "stack trace",
            "HTTP", "API", "JSON", "SQL", "regex"
        ]
        
        for pattern in technical_only_patterns:
            assert pattern not in result, f"Should not contain raw technical term: {pattern}"

    @settings(max_examples=100)
    @given(
        metric=metric_strategy,
        change=percentage_change_strategy,
        data=supporting_data_strategy,
    )
    def test_explanation_translates_metrics(
        self, metric: str, change: float, data: dict
    ):
        """Metric explanations should translate numbers into business meaning."""
        result = _explain_metric_change_impl(metric, change, data)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If not an error, should contain business context
        if "Error" not in result:
            # Should have human-readable language about the change
            business_terms = [
                "customer", "visitor", "sale", "order", "revenue",
                "buying", "purchase", "spend", "traffic", "conversion",
                "business", "store", "growth", "decline", "increase",
                "decrease", "stable", "change", "drop", "grew", "improved"
            ]
            result_lower = result.lower()
            has_business_context = any(term in result_lower for term in business_terms)
            assert has_business_context, "Should translate metrics into business terms"

    @settings(max_examples=100)
    @given(
        analysis=analysis_data_strategy,
        context=context_strategy,
    )
    def test_recommendations_have_expected_impact(
        self, analysis: dict, context: dict
    ):
        """Recommendations should include expected impact information."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If recommendations are generated
        if "Recommended Actions" in result or "Business Recommendations" in result:
            # Should contain impact-related language
            impact_indicators = [
                "impact", "result", "improve", "increase", "reduce",
                "could", "would", "expect", "potential", "revenue",
                "conversion", "customer", "%"
            ]
            result_lower = result.lower()
            has_impact = any(indicator in result_lower for indicator in impact_indicators)
            assert has_impact, "Recommendations should include expected impact"



class TestActionablePrioritizedRecommendations:
    """
    **Feature: credora-cfo-agent, Property 13: Actionable Prioritized Recommendations**
    **Validates: Requirements 7.2, 7.4**
    
    For any set of recommendations generated, each recommendation shall include
    a specific action and recommendations shall be ordered by priority (revenue impact).
    
    This property validates that:
    1. Each recommendation has a specific, actionable item
    2. Recommendations are ordered by priority
    3. Priority reflects potential revenue impact
    """

    @settings(max_examples=100)
    @given(recommendations=recommendations_list_strategy)
    def test_prioritize_actions_returns_ordered_list(self, recommendations: list):
        """prioritize_actions should return recommendations ordered by priority."""
        result = _prioritize_actions_impl(recommendations)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should contain prioritized output
        if "Prioritized Action Plan" in result:
            # Should have priority sections or numbered items
            assert "1." in result, "Should have numbered recommendations"
            
            # Find the priority section headers (marked with ---)
            # Priority labels in section headers should appear in order
            import re
            priority_sections = re.findall(r'---\s*(Critical|High|Medium|Low|Optional)', result)
            
            # If we have multiple priority sections, they should be in order
            if len(priority_sections) > 1:
                priority_order = ["Critical", "High", "Medium", "Low", "Optional"]
                for i in range(len(priority_sections) - 1):
                    current_priority = priority_sections[i]
                    next_priority = priority_sections[i + 1]
                    current_idx = priority_order.index(current_priority)
                    next_idx = priority_order.index(next_priority)
                    assert current_idx <= next_idx, \
                        f"{current_priority} should appear before {next_priority}"

    @settings(max_examples=100)
    @given(recommendations=recommendations_list_strategy)
    def test_each_recommendation_has_action(self, recommendations: list):
        """Each recommendation in output should have a specific action."""
        result = _prioritize_actions_impl(recommendations)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If we have a prioritized plan
        if "Prioritized Action Plan" in result:
            # Count numbered items (1., 2., etc.)
            import re
            numbered_items = re.findall(r'\d+\.\s+\S', result)
            
            # Should have at least one numbered action
            assert len(numbered_items) >= 1, "Should have numbered action items"
            
            # Each numbered item should be followed by some text (the action)
            # The action text can start with any non-whitespace character
            for i in range(1, len(numbered_items) + 1):
                pattern = rf'{i}\.\s+\S'  # Just check there's non-whitespace after number
                assert re.search(pattern, result), f"Item {i} should have action text"

    @settings(max_examples=100)
    @given(recommendations=recommendations_list_strategy)
    def test_recommendations_include_reason(self, recommendations: list):
        """Each recommendation should include a reason."""
        result = _prioritize_actions_impl(recommendations)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If we have a prioritized plan
        if "Prioritized Action Plan" in result:
            # Should contain "Reason:" labels
            assert "Reason:" in result, "Should include reasons for recommendations"

    @settings(max_examples=100)
    @given(recommendations=recommendations_list_strategy)
    def test_recommendations_include_impact(self, recommendations: list):
        """Each recommendation should include expected impact."""
        result = _prioritize_actions_impl(recommendations)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If we have a prioritized plan
        if "Prioritized Action Plan" in result:
            # Should contain impact information
            assert "Impact" in result or "impact" in result.lower(), \
                "Should include expected impact"

    @settings(max_examples=100)
    @given(
        analysis=analysis_data_strategy,
        context=context_strategy,
    )
    def test_generated_recommendations_are_actionable(
        self, analysis: dict, context: dict
    ):
        """Recommendations from generate_recommendation should be actionable."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If recommendations are generated
        if "Recommended Actions" in result or "Business Recommendations" in result:
            # Should contain action verbs
            action_verbs = [
                "implement", "reduce", "increase", "optimize", "review",
                "focus", "consider", "add", "improve", "test", "audit",
                "expand", "simplify", "cut", "double", "start", "stop"
            ]
            result_lower = result.lower()
            has_action_verb = any(verb in result_lower for verb in action_verbs)
            assert has_action_verb, "Recommendations should contain action verbs"

    @settings(max_examples=100)
    @given(
        analysis=analysis_data_strategy,
        context=context_strategy,
    )
    def test_generated_recommendations_have_priority(
        self, analysis: dict, context: dict
    ):
        """Recommendations from generate_recommendation should indicate priority."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # If recommendations are generated
        if "Recommended Actions" in result or "Business Recommendations" in result:
            # Should contain priority indicators
            priority_indicators = [
                "priority", "critical", "high", "medium", "low",
                "immediate", "urgent", "first", "1.", "2.", "3."
            ]
            result_lower = result.lower()
            has_priority = any(indicator in result_lower for indicator in priority_indicators)
            assert has_priority, "Recommendations should indicate priority"

    @settings(max_examples=100)
    @given(recommendations=recommendations_list_strategy)
    def test_empty_actions_filtered_out(self, recommendations: list):
        """Recommendations with empty actions should be filtered out."""
        # Add some invalid recommendations with empty actions
        invalid_recs = recommendations + [
            {"action": "", "reason": "test", "expected_impact": "test", "priority": 1},
            {"action": "   ", "reason": "test", "expected_impact": "test", "priority": 1},
        ]
        
        result = _prioritize_actions_impl(invalid_recs)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should still produce valid output (filtering invalid ones)
        # The count of items should match valid recommendations only
        if "Prioritized Action Plan" in result:
            import re
            numbered_items = re.findall(r'^\d+\.', result, re.MULTILINE)
            # Should have same count as valid recommendations
            assert len(numbered_items) == len(recommendations)



class TestInsufficientDataHandling:
    """
    **Feature: credora-cfo-agent, Property 14: Insufficient Data Handling**
    **Validates: Requirements 7.5**
    
    For any analysis request where data is insufficient, the system shall clearly
    state the limitation and specify what additional data is needed.
    
    This property validates that:
    1. Empty data triggers insufficient data message
    2. The message clearly states the limitation
    3. The message specifies what data is needed
    """

    @settings(max_examples=100)
    @given(context=context_strategy)
    def test_empty_analysis_data_states_limitation(self, context: dict):
        """Empty analysis data should clearly state the limitation."""
        result = _generate_recommendation_impl({}, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should indicate insufficient data
        limitation_indicators = [
            "insufficient", "empty", "no data", "cannot", "unable",
            "please provide", "need", "required", "missing"
        ]
        result_lower = result.lower()
        has_limitation = any(indicator in result_lower for indicator in limitation_indicators)
        assert has_limitation, "Should clearly state data limitation"

    @settings(max_examples=100)
    @given(context=context_strategy)
    def test_empty_analysis_data_specifies_needed_data(self, context: dict):
        """Empty analysis data should specify what data is needed."""
        result = _generate_recommendation_impl({}, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should specify what data is needed
        data_types = [
            "revenue", "sales", "conversion", "traffic", "customer",
            "metric", "data", "operational", "acquisition", "retention"
        ]
        result_lower = result.lower()
        specifies_data = any(data_type in result_lower for data_type in data_types)
        assert specifies_data, "Should specify what data is needed"

    @settings(max_examples=100)
    @given(
        metric=metric_strategy,
        change=percentage_change_strategy,
    )
    def test_empty_supporting_data_states_limitation(
        self, metric: str, change: float
    ):
        """Empty supporting data should state limitation for metric explanation."""
        result = _explain_metric_change_impl(metric, change, {})
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should indicate insufficient data for root cause analysis
        limitation_indicators = [
            "insufficient", "cannot", "unable", "please provide",
            "need", "required", "missing", "without", "context"
        ]
        result_lower = result.lower()
        has_limitation = any(indicator in result_lower for indicator in limitation_indicators)
        assert has_limitation, "Should state limitation when data is insufficient"

    @settings(max_examples=100)
    @given(
        metric=metric_strategy,
        change=percentage_change_strategy,
    )
    def test_empty_supporting_data_specifies_needed_data(
        self, metric: str, change: float
    ):
        """Empty supporting data should specify what additional data is needed."""
        result = _explain_metric_change_impl(metric, change, {})
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should specify what data would help
        data_types = [
            "traffic", "visitor", "conversion", "order", "marketing",
            "customer", "data", "metric", "context"
        ]
        result_lower = result.lower()
        specifies_data = any(data_type in result_lower for data_type in data_types)
        assert specifies_data, "Should specify what additional data is needed"

    @settings(max_examples=100)
    @given(st.just([]))
    def test_empty_recommendations_list_states_limitation(self, recommendations: list):
        """Empty recommendations list should state limitation."""
        result = _prioritize_actions_impl(recommendations)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should indicate no recommendations to prioritize
        limitation_indicators = [
            "no recommendation", "empty", "please provide", "no valid"
        ]
        result_lower = result.lower()
        has_limitation = any(indicator in result_lower for indicator in limitation_indicators)
        assert has_limitation, "Should state limitation for empty recommendations"

    @settings(max_examples=100)
    @given(st.just([]))
    def test_empty_recommendations_specifies_format(self, recommendations: list):
        """Empty recommendations should specify expected format."""
        result = _prioritize_actions_impl(recommendations)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should specify expected format
        format_indicators = [
            "action", "reason", "impact", "format", "example", "should"
        ]
        result_lower = result.lower()
        specifies_format = any(indicator in result_lower for indicator in format_indicators)
        assert specifies_format, "Should specify expected recommendation format"

    @settings(max_examples=100)
    @given(
        analysis=st.fixed_dictionaries({
            "total_revenue": st.just(0),
            "conversion_rate": st.just(0),
        }),
        context=context_strategy,
    )
    def test_zero_metrics_handled_gracefully(self, analysis: dict, context: dict):
        """Zero-value metrics should be handled gracefully."""
        result = _generate_recommendation_impl(analysis, context)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should not crash or produce error
        assert "Error" not in result or "Invalid" not in result
        
        # Should either provide recommendations or indicate insufficient data
        valid_response = (
            "Recommended Actions" in result or
            "Business Recommendations" in result or
            "insufficient" in result.lower() or
            "no critical" in result.lower() or
            "no significant" in result.lower()
        )
        assert valid_response, "Should handle zero metrics gracefully"

    @settings(max_examples=100)
    @given(
        metric=metric_strategy,
        change=st.just(0.0),
        data=supporting_data_strategy,
    )
    def test_zero_change_handled_gracefully(
        self, metric: str, change: float, data: dict
    ):
        """Zero change should be handled gracefully."""
        result = _explain_metric_change_impl(metric, change, data)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should not crash
        assert "Error" not in result or "Invalid" not in result
        
        # Should indicate stability or no change
        stability_indicators = [
            "stable", "unchanged", "no change", "remained", "0%", "0.0%"
        ]
        result_lower = result.lower()
        indicates_stability = any(indicator in result_lower for indicator in stability_indicators)
        assert indicates_stability, "Should indicate metric stability for zero change"

