"""
Meta Ads data models.

Data structures for Meta (Facebook/Instagram) advertising data.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AdAccount:
    """Meta Ads account information.
    
    Requirements: 3.1
    
    Attributes:
        id: Unique account identifier
        name: Account display name
        currency: Account currency code (e.g., USD)
        timezone: Account timezone (e.g., America/New_York)
    """
    
    id: str
    name: str
    currency: str
    timezone: str
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.name:
            raise ValueError("name is required and cannot be empty")
        if not self.currency:
            raise ValueError("currency is required and cannot be empty")
        if not self.timezone:
            raise ValueError("timezone is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "currency": self.currency,
            "timezone": self.timezone,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdAccount":
        """Create AdAccount from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            currency=data.get("currency", ""),
            timezone=data.get("timezone", ""),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "AdAccount":
        """Create AdAccount from Meta API response."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            currency=data.get("currency", "USD"),
            timezone=data.get("timezone_name", data.get("timezone", "")),
        )


@dataclass
class Campaign:
    """Meta Ads campaign with performance metrics.
    
    Requirements: 3.2
    
    Attributes:
        id: Unique campaign identifier
        name: Campaign display name
        status: Campaign status (ACTIVE, PAUSED, DELETED, etc.)
        objective: Campaign objective (CONVERSIONS, TRAFFIC, etc.)
        spend: Total amount spent
        impressions: Total impressions
        clicks: Total clicks
        conversions: Total conversions
        cpc: Cost per click
        cpm: Cost per thousand impressions
        ctr: Click-through rate (percentage)
    """
    
    id: str
    name: str
    status: str
    objective: str
    spend: float
    impressions: int
    clicks: int
    conversions: int
    cpc: float
    cpm: float
    ctr: float
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.name:
            raise ValueError("name is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "objective": self.objective,
            "spend": self.spend,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "cpc": self.cpc,
            "cpm": self.cpm,
            "ctr": self.ctr,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        """Create Campaign from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            status=data.get("status", ""),
            objective=data.get("objective", ""),
            spend=float(data.get("spend", 0)),
            impressions=int(data.get("impressions", 0)),
            clicks=int(data.get("clicks", 0)),
            conversions=int(data.get("conversions", 0)),
            cpc=float(data.get("cpc", 0)),
            cpm=float(data.get("cpm", 0)),
            ctr=float(data.get("ctr", 0)),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], insights: Optional[Dict[str, Any]] = None) -> "Campaign":
        """Create Campaign from Meta API response with optional insights."""
        insights = insights or {}
        
        spend = float(insights.get("spend", 0))
        impressions = int(insights.get("impressions", 0))
        clicks = int(insights.get("clicks", 0))
        conversions = int(insights.get("actions", [{}])[0].get("value", 0) if insights.get("actions") else 0)
        
        # Calculate derived metrics
        cpc = spend / clicks if clicks > 0 else 0.0
        cpm = (spend / impressions) * 1000 if impressions > 0 else 0.0
        ctr = (clicks / impressions) * 100 if impressions > 0 else 0.0
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            status=data.get("status", ""),
            objective=data.get("objective", ""),
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            cpc=cpc,
            cpm=cpm,
            ctr=ctr,
        )


@dataclass
class AdSet:
    """Meta Ads ad set with performance metrics.
    
    Requirements: 3.3
    
    Attributes:
        id: Unique ad set identifier
        name: Ad set display name
        campaign_id: Parent campaign identifier
        status: Ad set status (ACTIVE, PAUSED, etc.)
        daily_budget: Daily budget in account currency (optional)
        lifetime_budget: Lifetime budget in account currency (optional)
        spend: Total amount spent
        impressions: Total impressions
        clicks: Total clicks
        conversions: Total conversions
    """
    
    id: str
    name: str
    campaign_id: str
    status: str
    daily_budget: Optional[float]
    lifetime_budget: Optional[float]
    spend: float
    impressions: int
    clicks: int
    conversions: int
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.name:
            raise ValueError("name is required and cannot be empty")
        if not self.campaign_id:
            raise ValueError("campaign_id is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "campaign_id": self.campaign_id,
            "status": self.status,
            "daily_budget": self.daily_budget,
            "lifetime_budget": self.lifetime_budget,
            "spend": self.spend,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdSet":
        """Create AdSet from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            campaign_id=data.get("campaign_id", ""),
            status=data.get("status", ""),
            daily_budget=data.get("daily_budget"),
            lifetime_budget=data.get("lifetime_budget"),
            spend=float(data.get("spend", 0)),
            impressions=int(data.get("impressions", 0)),
            clicks=int(data.get("clicks", 0)),
            conversions=int(data.get("conversions", 0)),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], insights: Optional[Dict[str, Any]] = None) -> "AdSet":
        """Create AdSet from Meta API response with optional insights."""
        insights = insights or {}
        
        # Parse budgets (Meta returns in cents)
        daily_budget = None
        lifetime_budget = None
        if data.get("daily_budget"):
            daily_budget = float(data["daily_budget"]) / 100
        if data.get("lifetime_budget"):
            lifetime_budget = float(data["lifetime_budget"]) / 100
        
        spend = float(insights.get("spend", 0))
        impressions = int(insights.get("impressions", 0))
        clicks = int(insights.get("clicks", 0))
        conversions = int(insights.get("actions", [{}])[0].get("value", 0) if insights.get("actions") else 0)
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            campaign_id=data.get("campaign_id", ""),
            status=data.get("status", ""),
            daily_budget=daily_budget,
            lifetime_budget=lifetime_budget,
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
        )


@dataclass
class AudienceInsights:
    """Audience demographic insights.
    
    Requirements: 3.4
    
    Attributes:
        account_id: Ad account identifier
        age_breakdown: Age distribution (e.g., {"18-24": 0.15, "25-34": 0.30})
        gender_breakdown: Gender distribution (e.g., {"male": 0.45, "female": 0.55})
        location_breakdown: Location distribution by country/region
        interests: List of top audience interests
    """
    
    account_id: str
    age_breakdown: Dict[str, float] = field(default_factory=dict)
    gender_breakdown: Dict[str, float] = field(default_factory=dict)
    location_breakdown: Dict[str, float] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.account_id:
            raise ValueError("account_id is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "account_id": self.account_id,
            "age_breakdown": self.age_breakdown,
            "gender_breakdown": self.gender_breakdown,
            "location_breakdown": self.location_breakdown,
            "interests": self.interests,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudienceInsights":
        """Create AudienceInsights from dictionary."""
        return cls(
            account_id=data.get("account_id", ""),
            age_breakdown=data.get("age_breakdown", {}),
            gender_breakdown=data.get("gender_breakdown", {}),
            location_breakdown=data.get("location_breakdown", {}),
            interests=data.get("interests", []),
        )
    
    @classmethod
    def from_api_response(cls, account_id: str, data: Dict[str, Any]) -> "AudienceInsights":
        """Create AudienceInsights from Meta API response."""
        age_breakdown = {}
        gender_breakdown = {}
        location_breakdown = {}
        interests = []
        
        # Parse age breakdown from insights
        for item in data.get("age", []):
            age_range = item.get("age", "")
            percentage = float(item.get("percentage", 0))
            if age_range:
                age_breakdown[age_range] = percentage
        
        # Parse gender breakdown
        for item in data.get("gender", []):
            gender = item.get("gender", "")
            percentage = float(item.get("percentage", 0))
            if gender:
                gender_breakdown[gender.lower()] = percentage
        
        # Parse location breakdown
        for item in data.get("country", []):
            country = item.get("country", "")
            percentage = float(item.get("percentage", 0))
            if country:
                location_breakdown[country] = percentage
        
        # Parse interests
        for item in data.get("interests", []):
            interest_name = item.get("name", "")
            if interest_name:
                interests.append(interest_name)
        
        return cls(
            account_id=account_id,
            age_breakdown=age_breakdown,
            gender_breakdown=gender_breakdown,
            location_breakdown=location_breakdown,
            interests=interests,
        )
