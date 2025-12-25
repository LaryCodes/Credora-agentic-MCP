"""Data models for the Credora CFO system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class SessionState:
    """Persistent session state for a user.
    
    Tracks authorization status, connected platforms, and completed analyses.
    Requirements: 4.1, 4.2
    """
    user_id: str
    connected_platforms: List[str] = field(default_factory=list)
    platform_tokens: Dict[str, str] = field(default_factory=dict)  # Encrypted tokens
    business_goals: List[str] = field(default_factory=list)
    completed_analyses: List[str] = field(default_factory=list)
    onboarding_complete: bool = False
    last_interaction: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.user_id or not self.user_id.strip():
            raise ValueError("user_id is required and cannot be empty")


@dataclass
class UserContext:
    """User business context collected during onboarding.
    
    Requirements: 2.3, 2.4
    """
    user_id: str
    platform_type: str  # "shopify" | "woocommerce" | "other"
    business_goals: List[str] = field(default_factory=list)
    store_name: str = ""
    connected_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.user_id or not self.user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        if not self.platform_type or not self.platform_type.strip():
            raise ValueError("platform_type is required and cannot be empty")


@dataclass
class Recommendation:
    """A single actionable recommendation.
    
    Requirements: 7.2, 7.4
    """
    action: str
    reason: str
    expected_impact: str
    priority: int  # 1-5, 1 being highest
    
    def __post_init__(self):
        if not self.action or not self.action.strip():
            raise ValueError("action is required and cannot be empty")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason is required and cannot be empty")
        if not isinstance(self.priority, int) or not (1 <= self.priority <= 5):
            raise ValueError("priority must be an integer between 1 and 5")


@dataclass
class AnalysisResult:
    """Result of an analysis operation.
    
    Requirements: 5.3, 7.1
    """
    analysis_type: str
    data: Dict = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.analysis_type or not self.analysis_type.strip():
            raise ValueError("analysis_type is required and cannot be empty")


@dataclass
class ToolLog:
    """Log entry for tool invocations.
    
    Requirements: 3.6
    """
    tool_name: str
    input_params: Dict = field(default_factory=dict)
    output: str = ""
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    agent_name: str = ""
    
    def __post_init__(self):
        if not self.tool_name or not self.tool_name.strip():
            raise ValueError("tool_name is required and cannot be empty")


__all__ = [
    "SessionState",
    "UserContext",
    "AnalysisResult",
    "Recommendation",
    "ToolLog",
]
