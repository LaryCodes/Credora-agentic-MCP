"""Property-based tests for CFO agent routing.

**Feature: credora-cfo-agent**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from credora.agents.cfo import classify_query_intent, QUERY_INTENTS


# Collect all keywords from all intents for filtering
ALL_KEYWORDS = set()
for keywords in QUERY_INTENTS.values():
    ALL_KEYWORDS.update(keywords)


def contains_other_intent_keywords(text: str, target_intent: str) -> bool:
    """Check if text contains keywords from other intents."""
    text_lower = text.lower()
    for intent, keywords in QUERY_INTENTS.items():
        if intent != target_intent:
            for keyword in keywords:
                if keyword in text_lower:
                    return True
    return False


class TestCorrectAgentRouting:
    """
    **Feature: credora-cfo-agent, Property 10: Correct Agent Routing**
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
    
    For any user query, the CFO Agent shall handoff to the appropriate 
    specialized agent based on query intent:
    - data requests → Data Fetcher
    - analysis requests → Analytics
    - competitor requests → Competitor
    - recommendation requests → Insight
    """

    @settings(max_examples=100)
    @given(
        keyword=st.sampled_from(QUERY_INTENTS["data_fetch"]),
        prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
        suffix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
    )
    def test_data_fetch_queries_route_to_data_fetcher(
        self, keyword: str, prefix: str, suffix: str
    ):
        """Queries with data fetch keywords (and no conflicting keywords) should route to data_fetch intent."""
        # Exclude queries that contain keywords from other intents
        assume(not contains_other_intent_keywords(prefix, "data_fetch"))
        assume(not contains_other_intent_keywords(suffix, "data_fetch"))
        
        query = f"{prefix} {keyword} {suffix}"
        intent = classify_query_intent(query)
        assert intent == "data_fetch", f"Query '{query}' should route to data_fetch, got {intent}"

    @settings(max_examples=100)
    @given(
        keyword=st.sampled_from(QUERY_INTENTS["analytics"]),
        prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
        suffix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
    )
    def test_analytics_queries_route_to_analytics(
        self, keyword: str, prefix: str, suffix: str
    ):
        """Queries with analytics keywords (and no conflicting keywords) should route to analytics intent."""
        # Exclude queries that contain keywords from other intents
        assume(not contains_other_intent_keywords(prefix, "analytics"))
        assume(not contains_other_intent_keywords(suffix, "analytics"))
        
        query = f"{prefix} {keyword} {suffix}"
        intent = classify_query_intent(query)
        assert intent == "analytics", f"Query '{query}' should route to analytics, got {intent}"

    @settings(max_examples=100)
    @given(
        keyword=st.sampled_from(QUERY_INTENTS["competitor"]),
        prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
        suffix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
    )
    def test_competitor_queries_route_to_competitor(
        self, keyword: str, prefix: str, suffix: str
    ):
        """Queries with competitor keywords (and no conflicting keywords) should route to competitor intent."""
        # Exclude queries that contain keywords from other intents
        assume(not contains_other_intent_keywords(prefix, "competitor"))
        assume(not contains_other_intent_keywords(suffix, "competitor"))
        
        query = f"{prefix} {keyword} {suffix}"
        intent = classify_query_intent(query)
        assert intent == "competitor", f"Query '{query}' should route to competitor, got {intent}"

    @settings(max_examples=100)
    @given(
        keyword=st.sampled_from(QUERY_INTENTS["insight"]),
        prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
        suffix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
    )
    def test_insight_queries_route_to_insight(
        self, keyword: str, prefix: str, suffix: str
    ):
        """Queries with insight keywords (and no conflicting keywords) should route to insight intent."""
        # Exclude queries that contain keywords from other intents
        assume(not contains_other_intent_keywords(prefix, "insight"))
        assume(not contains_other_intent_keywords(suffix, "insight"))
        
        query = f"{prefix} {keyword} {suffix}"
        intent = classify_query_intent(query)
        assert intent == "insight", f"Query '{query}' should route to insight, got {intent}"

    @settings(max_examples=100)
    @given(
        keyword=st.sampled_from(QUERY_INTENTS["onboarding"]),
        prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
        suffix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))),
    )
    def test_onboarding_queries_route_to_onboarding(
        self, keyword: str, prefix: str, suffix: str
    ):
        """Queries with onboarding keywords (and no conflicting keywords) should route to onboarding intent."""
        # Exclude queries that contain keywords from other intents
        assume(not contains_other_intent_keywords(prefix, "onboarding"))
        assume(not contains_other_intent_keywords(suffix, "onboarding"))
        
        query = f"{prefix} {keyword} {suffix}"
        intent = classify_query_intent(query)
        assert intent == "onboarding", f"Query '{query}' should route to onboarding, got {intent}"

    @settings(max_examples=100)
    @given(
        query=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')))
    )
    def test_all_queries_return_valid_intent(self, query: str):
        """All queries should return a valid intent category."""
        valid_intents = {"onboarding", "data_fetch", "analytics", "competitor", "insight", "general"}
        intent = classify_query_intent(query)
        assert intent in valid_intents, f"Intent '{intent}' is not a valid category"

    @settings(max_examples=100)
    @given(
        query=st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')))
    )
    def test_routing_is_deterministic(self, query: str):
        """Same query should always route to the same intent."""
        intent1 = classify_query_intent(query)
        intent2 = classify_query_intent(query)
        assert intent1 == intent2, f"Query '{query}' routed to {intent1} then {intent2}"

    @settings(max_examples=100)
    @given(
        query=st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')))
    )
    def test_routing_is_case_insensitive(self, query: str):
        """Routing should be case-insensitive."""
        intent_lower = classify_query_intent(query.lower())
        intent_upper = classify_query_intent(query.upper())
        intent_mixed = classify_query_intent(query)
        
        assert intent_lower == intent_upper == intent_mixed, \
            f"Case sensitivity issue: lower={intent_lower}, upper={intent_upper}, mixed={intent_mixed}"



class TestHandoffCompletion:
    """
    **Feature: credora-cfo-agent, Property 11: Handoff Completion**
    **Validates: Requirements 6.5**
    
    For any agent handoff, the specialized agent shall return results to 
    the CFO Agent, and the CFO Agent shall incorporate those results into 
    the final user response.
    
    This property tests that the CFO agent is properly configured with
    handoffs to all specialized agents, ensuring the handoff mechanism
    is in place for result incorporation.
    """

    @pytest.fixture(autouse=True)
    def skip_without_api_key(self):
        """Skip tests if OPENROUTER_API_KEY is not set."""
        import os
        if not os.environ.get("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY not set - skipping agent creation tests")

    def test_cfo_agent_has_all_required_handoffs(self):
        """CFO Agent should have handoffs to all specialized agents."""
        from credora.agents.cfo import create_cfo_agent
        
        cfo_agent = create_cfo_agent()
        
        # Get handoff agent names
        handoff_names = {agent.name for agent in cfo_agent.handoffs}
        
        # Verify all required specialized agents are present
        required_agents = {
            "Onboarding Agent",
            "Data Fetcher Agent",
            "Analytics Agent",
            "Competitor Agent",
            "Insight Agent",
        }
        
        assert required_agents.issubset(handoff_names), \
            f"Missing handoffs: {required_agents - handoff_names}"

    def test_cfo_agent_has_state_tools(self):
        """CFO Agent should have state management tools."""
        from credora.agents.cfo import create_cfo_agent
        
        cfo_agent = create_cfo_agent()
        
        # Get tool names - tools are function_tool decorated functions
        tool_names = set()
        for tool in cfo_agent.tools:
            # function_tool creates a FunctionTool with a name attribute
            if hasattr(tool, 'name'):
                tool_names.add(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.add(tool.__name__)
        
        # Verify state tools are present
        required_tools = {"get_session_state", "update_session_state"}
        
        assert required_tools.issubset(tool_names), \
            f"Missing tools: {required_tools - tool_names}"

    @settings(max_examples=100, deadline=None)
    @given(
        agent_name=st.sampled_from([
            "Onboarding Agent",
            "Data Fetcher Agent", 
            "Analytics Agent",
            "Competitor Agent",
            "Insight Agent",
        ])
    )
    def test_each_handoff_agent_has_tools(self, agent_name: str):
        """Each specialized agent in handoffs should have tools configured."""
        from credora.agents.cfo import create_cfo_agent
        
        cfo_agent = create_cfo_agent()
        
        # Find the agent by name
        target_agent = None
        for agent in cfo_agent.handoffs:
            if agent.name == agent_name:
                target_agent = agent
                break
        
        assert target_agent is not None, f"Agent '{agent_name}' not found in handoffs"
        assert len(target_agent.tools) > 0, f"Agent '{agent_name}' has no tools"

    @settings(max_examples=100, deadline=None)
    @given(
        agent_name=st.sampled_from([
            "Onboarding Agent",
            "Data Fetcher Agent",
            "Analytics Agent", 
            "Competitor Agent",
            "Insight Agent",
        ])
    )
    def test_each_handoff_agent_has_instructions(self, agent_name: str):
        """Each specialized agent should have instructions for handling requests."""
        from credora.agents.cfo import create_cfo_agent
        
        cfo_agent = create_cfo_agent()
        
        # Find the agent by name
        target_agent = None
        for agent in cfo_agent.handoffs:
            if agent.name == agent_name:
                target_agent = agent
                break
        
        assert target_agent is not None, f"Agent '{agent_name}' not found in handoffs"
        assert target_agent.instructions, f"Agent '{agent_name}' has no instructions"
        assert len(target_agent.instructions) > 100, \
            f"Agent '{agent_name}' instructions too short to be meaningful"

    def test_cfo_agent_instructions_mention_handoffs(self):
        """CFO Agent instructions should describe handoff behavior."""
        from credora.agents.cfo import CFO_AGENT_INSTRUCTIONS
        
        # Check that instructions mention key handoff concepts
        instructions_lower = CFO_AGENT_INSTRUCTIONS.lower()
        
        assert "handoff" in instructions_lower, "Instructions should mention handoffs"
        assert "onboarding" in instructions_lower, "Instructions should mention Onboarding Agent"
        assert "data" in instructions_lower, "Instructions should mention Data Fetcher"
        assert "analytics" in instructions_lower, "Instructions should mention Analytics Agent"
        assert "competitor" in instructions_lower, "Instructions should mention Competitor Agent"
        assert "insight" in instructions_lower, "Instructions should mention Insight Agent"
