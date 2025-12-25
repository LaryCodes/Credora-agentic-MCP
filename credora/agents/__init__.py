"""Agent definitions for the Credora CFO system."""

from credora.agents.base import (
    create_openai_client,
    create_model,
    get_default_model,
)
from credora.agents.onboarding import (
    create_onboarding_agent,
    get_onboarding_agent,
    ONBOARDING_INSTRUCTIONS,
)
from credora.agents.data_fetcher import (
    create_data_fetcher_agent,
    get_data_fetcher_agent,
    DATA_FETCHER_INSTRUCTIONS,
)
from credora.agents.analytics import (
    create_analytics_agent,
    get_analytics_agent,
    ANALYTICS_AGENT_INSTRUCTIONS,
)
from credora.agents.competitor import (
    create_competitor_agent,
    get_competitor_agent,
    COMPETITOR_AGENT_INSTRUCTIONS,
)
from credora.agents.insight import (
    create_insight_agent,
    get_insight_agent,
    INSIGHT_AGENT_INSTRUCTIONS,
)
from credora.agents.cfo import (
    create_cfo_agent,
    get_cfo_agent,
    CFO_AGENT_INSTRUCTIONS,
    QUERY_INTENTS,
    classify_query_intent,
)

__all__ = [
    # Base agent utilities
    "create_openai_client",
    "create_model",
    "get_default_model",
    # Onboarding agent
    "create_onboarding_agent",
    "get_onboarding_agent",
    "ONBOARDING_INSTRUCTIONS",
    # Data Fetcher agent
    "create_data_fetcher_agent",
    "get_data_fetcher_agent",
    "DATA_FETCHER_INSTRUCTIONS",
    # Analytics agent
    "create_analytics_agent",
    "get_analytics_agent",
    "ANALYTICS_AGENT_INSTRUCTIONS",
    # Competitor agent
    "create_competitor_agent",
    "get_competitor_agent",
    "COMPETITOR_AGENT_INSTRUCTIONS",
    # Insight agent
    "create_insight_agent",
    "get_insight_agent",
    "INSIGHT_AGENT_INSTRUCTIONS",
    # CFO orchestrator agent
    "create_cfo_agent",
    "get_cfo_agent",
    "CFO_AGENT_INSTRUCTIONS",
    "QUERY_INTENTS",
    "classify_query_intent",
]
