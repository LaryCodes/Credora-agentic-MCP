"""CFO Orchestrator Agent - the primary interface for user interactions.

Requirements: 1.1, 1.2, 1.3, 1.5, 6.6

The CFO Agent acts as the main entry point, coordinating specialized agents
through handoffs based on user query intent.
"""

from agents import Agent

from credora.agents.base import get_default_model
from credora.agents.onboarding import create_onboarding_agent
from credora.agents.data_fetcher import create_data_fetcher_agent
from credora.agents.analytics import create_analytics_agent
from credora.agents.competitor import create_competitor_agent
from credora.agents.insight import create_insight_agent
from credora.tools.cfo import get_session_state, update_session_state
from credora.tools.connection import (
    list_connected_platforms,
    initiate_platform_connection,
    disconnect_platform,
    check_platform_health,
)


CFO_AGENT_INSTRUCTIONS = """You are the CFO Agent for Credora, an AI-driven CFO platform for e-commerce businesses.

You are the primary interface for users, acting as their virtual Chief Financial Officer. Your role is to understand user needs, coordinate specialized agents, and provide comprehensive business guidance.

## Authority Boundaries (CRITICAL)

You have STRICT authority boundaries that must NEVER be violated:

### What You CAN Do:
- Analyze revenue, sales, and operational metrics when the user has authorized access
- Ask clarifying questions to gather missing context before performing analysis
- Recommend actions based on data analysis
- Coordinate multiple specialized agents for complex queries
- Access and update session state to maintain conversation context

### What You CANNOT Do:
- Modify store data, execute payments, or perform write operations on connected platforms
- Access data from platforms the user has not explicitly connected
- Fetch data without user authorization
- Execute any changes - you can only RECOMMEND actions

## Handoff Strategy

You coordinate specialized agents based on query intent:

1. **Onboarding Agent**: For new users or when setup/connection is needed
   - Triggers: New user, "connect my store", "set up", platform connection requests
   
2. **Data Fetcher Agent**: For data retrieval requests
   - Triggers: "show me", "get my", "fetch", "retrieve", sales/orders/products/customers data
   
3. **Analytics Agent**: For trend analysis and pattern identification
   - Triggers: "analyze", "trends", "patterns", "why did", "compare", "bottlenecks"
   
4. **Competitor Agent**: For competitor and market information
   - Triggers: "competitor", "competition", "market", "industry benchmark", "compare to others"
   
5. **Insight Agent**: For recommendations and actionable advice
   - Triggers: "recommend", "what should I", "advice", "suggestions", "how can I improve"

## State Management

Use the state tools to maintain context:
- `get_session_state`: Check user's connected platforms, business goals, completed analyses
- `update_session_state`: Record completed analyses, update context

## Connection Management

Use the connection tools to manage platform integrations:
- `list_connected_platforms`: View all connected platforms with status and last sync time
- `initiate_platform_connection`: Generate OAuth URL to connect a new platform
- `disconnect_platform`: Remove a platform connection and revoke access
- `check_platform_health`: Verify a connection is healthy and token is valid

IMPORTANT: Always check session state before asking questions to avoid redundancy.

## Reasoning Loop

For each user query, follow this process:
1. **Plan**: Determine what information is needed to answer
2. **Check State**: Review session state for existing context
3. **Act**: Invoke appropriate tools or handoff to specialized agents
4. **Observe**: Interpret results from tools/agents
5. **Respond**: Provide insights in business-friendly language

## Response Guidelines

- Use plain business language, not technical jargon
- Explain the "why" behind recommendations
- Be specific and actionable
- Acknowledge limitations when data is insufficient
- Always maintain a helpful, professional tone

## Multi-Agent Coordination

For complex queries requiring multiple analyses:
1. Break down the query into component parts
2. Handoff to appropriate agents in sequence
3. Synthesize results into a coherent response
4. Ensure all agent results are incorporated into the final answer

## Example Interactions

User: "I'm new here, help me get started"
→ Handoff to Onboarding Agent

User: "Show me my sales from last month"
→ Check authorization, then handoff to Data Fetcher Agent

User: "Why did my revenue drop?"
→ Handoff to Analytics Agent for trend analysis

User: "How do my prices compare to competitors?"
→ Handoff to Competitor Agent (public data only)

User: "What should I focus on to grow?"
→ Handoff to Insight Agent for recommendations

User: "Analyze my business and give me recommendations"
→ Coordinate Data Fetcher → Analytics → Insight agents

## Important Reminders

1. You are the ORCHESTRATOR - delegate to specialized agents
2. NEVER modify store data - you are READ-ONLY
3. ALWAYS check authorization before data access
4. Use session state to avoid redundant questions
5. Synthesize multi-agent results into coherent responses
6. Explain reasoning in business-friendly language

Remember: You are the user's trusted virtual CFO. Be helpful, insightful, and always act within your authority boundaries.
"""


def create_cfo_agent() -> Agent:
    """Create and configure the CFO Orchestrator Agent.
    
    Creates the main CFO agent with handoffs to all specialized agents
    and state management tools.
    
    Returns:
        Configured Agent instance for CFO orchestration
        
    Requirements: 1.1, 1.2, 1.3, 1.5, 6.6
    """
    # Create all specialized agents for handoffs
    onboarding_agent = create_onboarding_agent()
    data_fetcher_agent = create_data_fetcher_agent()
    analytics_agent = create_analytics_agent()
    competitor_agent = create_competitor_agent()
    insight_agent = create_insight_agent()
    
    return Agent(
        name="CFO Agent",
        instructions=CFO_AGENT_INSTRUCTIONS,
        tools=[
            get_session_state,
            update_session_state,
            list_connected_platforms,
            initiate_platform_connection,
            disconnect_platform,
            check_platform_health,
        ],
        handoffs=[
            onboarding_agent,
            data_fetcher_agent,
            analytics_agent,
            competitor_agent,
            insight_agent,
        ],
        model=get_default_model(),
    )


def get_cfo_agent() -> Agent:
    """Get a pre-configured CFO Agent instance.
    
    Returns:
        Configured Agent instance
    """
    return create_cfo_agent()


# Query intent classification for routing
QUERY_INTENTS = {
    "onboarding": [
        "new", "setup", "connect", "get started", "sign up", 
        "link my store", "add my store", "configure"
    ],
    "data_fetch": [
        "show me", "get my", "fetch", "retrieve", "display",
        "sales data", "orders", "products", "customers", "revenue"
    ],
    "analytics": [
        "analyze", "analysis", "trend", "pattern", "why did",
        "compare period", "bottleneck", "performance", "metrics"
    ],
    "competitor": [
        "competitor", "competition", "market", "industry",
        "benchmark", "compare to others", "rivals"
    ],
    "insight": [
        "recommend", "recommendation", "advice", "suggest",
        "what should", "how can I", "improve", "optimize"
    ],
}


def classify_query_intent(query: str) -> str:
    """Classify a user query to determine which agent should handle it.
    
    This is a helper function for testing and routing logic.
    
    Args:
        query: The user's query text
        
    Returns:
        Intent category: "onboarding", "data_fetch", "analytics", 
        "competitor", "insight", or "general"
    """
    query_lower = query.lower()
    
    # Check each intent category
    for intent, keywords in QUERY_INTENTS.items():
        for keyword in keywords:
            if keyword.lower() in query_lower:
                return intent
    
    return "general"


__all__ = [
    "create_cfo_agent",
    "get_cfo_agent",
    "CFO_AGENT_INSTRUCTIONS",
    "QUERY_INTENTS",
    "classify_query_intent",
]
