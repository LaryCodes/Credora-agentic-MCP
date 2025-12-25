"""
Google Ads data models.

Data structures for Google Ads advertising data.

Requirements: 4.1, 4.2, 4.3, 4.4
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Customer:
    """Google Ads customer account information.
    
    Requirements: 4.1
    
    Attributes:
        id: Unique customer identifier
        name: Customer display name
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
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        """Create Customer from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            currency=data.get("currency", ""),
            timezone=data.get("timezone", ""),
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Customer":
        """Create Customer from Google Ads API response."""
        # Google Ads API returns customer data in a nested structure
        customer = data.get("customer", data)
        return cls(
            id=customer.get("id", customer.get("resourceName", "").split("/")[-1]),
            name=customer.get("descriptiveName", customer.get("name", "")),
            currency=customer.get("currencyCode", "USD"),
            timezone=customer.get("timeZone", ""),
        )


@dataclass
class Campaign:
    """Google Ads campaign with performance metrics.
    
    Requirements: 4.2
    
    Attributes:
        id: Unique campaign identifier
        name: Campaign display name
        status: Campaign status (ENABLED, PAUSED, REMOVED)
        campaign_type: Campaign type (SEARCH, DISPLAY, VIDEO, etc.)
        cost: Total cost in micros (divide by 1,000,000 for actual value)
        impressions: Total impressions
        clicks: Total clicks
        conversions: Total conversions
        cpc: Cost per click
        ctr: Click-through rate (percentage)
    """
    
    id: str
    name: str
    status: str
    campaign_type: str
    cost: float
    impressions: int
    clicks: int
    conversions: float
    cpc: float
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
            "campaign_type": self.campaign_type,
            "cost": self.cost,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "cpc": self.cpc,
            "ctr": self.ctr,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        """Create Campaign from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            status=data.get("status", ""),
            campaign_type=data.get("campaign_type", ""),
            cost=float(data.get("cost", 0)),
            impressions=int(data.get("impressions", 0)),
            clicks=int(data.get("clicks", 0)),
            conversions=float(data.get("conversions", 0)),
            cpc=float(data.get("cpc", 0)),
            ctr=float(data.get("ctr", 0)),
        )
    
    @classmethod
    def from_api_response(
        cls, data: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None
    ) -> "Campaign":
        """Create Campaign from Google Ads API response with optional metrics."""
        metrics = metrics or {}
        campaign = data.get("campaign", data)
        
        # Extract campaign ID from resource name if needed
        campaign_id = campaign.get("id", "")
        if not campaign_id and campaign.get("resourceName"):
            campaign_id = campaign["resourceName"].split("/")[-1]
        
        # Parse metrics (Google Ads returns cost in micros)
        cost_micros = float(metrics.get("costMicros", metrics.get("cost_micros", 0)))
        cost = cost_micros / 1_000_000  # Convert micros to actual currency
        
        impressions = int(metrics.get("impressions", 0))
        clicks = int(metrics.get("clicks", 0))
        conversions = float(metrics.get("conversions", 0))
        
        # Calculate derived metrics
        cpc = cost / clicks if clicks > 0 else 0.0
        ctr = (clicks / impressions) * 100 if impressions > 0 else 0.0
        
        return cls(
            id=campaign_id,
            name=campaign.get("name", ""),
            status=campaign.get("status", ""),
            campaign_type=campaign.get("advertisingChannelType", campaign.get("type", "")),
            cost=cost,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            cpc=cpc,
            ctr=ctr,
        )



@dataclass
class Keyword:
    """Google Ads keyword with performance metrics.
    
    Requirements: 4.3
    
    Attributes:
        id: Unique keyword identifier
        text: Keyword text
        match_type: Match type (EXACT, PHRASE, BROAD)
        impressions: Total impressions
        clicks: Total clicks
        cost: Total cost
        conversions: Total conversions
        quality_score: Quality score (1-10, optional)
    """
    
    id: str
    text: str
    match_type: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    quality_score: Optional[int]
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.id:
            raise ValueError("id is required and cannot be empty")
        if not self.text:
            raise ValueError("text is required and cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "match_type": self.match_type,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "cost": self.cost,
            "conversions": self.conversions,
            "quality_score": self.quality_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Keyword":
        """Create Keyword from dictionary."""
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            match_type=data.get("match_type", ""),
            impressions=int(data.get("impressions", 0)),
            clicks=int(data.get("clicks", 0)),
            cost=float(data.get("cost", 0)),
            conversions=float(data.get("conversions", 0)),
            quality_score=data.get("quality_score"),
        )
    
    @classmethod
    def from_api_response(
        cls, data: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None
    ) -> "Keyword":
        """Create Keyword from Google Ads API response with optional metrics."""
        metrics = metrics or {}
        keyword = data.get("adGroupCriterion", data.get("keyword", data))
        keyword_info = keyword.get("keyword", keyword)
        
        # Extract keyword ID from resource name if needed
        keyword_id = keyword.get("criterionId", "")
        if not keyword_id and keyword.get("resourceName"):
            keyword_id = keyword["resourceName"].split("~")[-1]
        
        # Parse metrics (Google Ads returns cost in micros)
        cost_micros = float(metrics.get("costMicros", metrics.get("cost_micros", 0)))
        cost = cost_micros / 1_000_000
        
        impressions = int(metrics.get("impressions", 0))
        clicks = int(metrics.get("clicks", 0))
        conversions = float(metrics.get("conversions", 0))
        
        # Quality score may not always be available
        quality_score = None
        qs_info = keyword.get("qualityInfo", {})
        if qs_info.get("qualityScore"):
            quality_score = int(qs_info["qualityScore"])
        
        return cls(
            id=str(keyword_id),
            text=keyword_info.get("text", ""),
            match_type=keyword_info.get("matchType", ""),
            impressions=impressions,
            clicks=clicks,
            cost=cost,
            conversions=conversions,
            quality_score=quality_score,
        )


@dataclass
class AdGroup:
    """Google Ads ad group with performance metrics.
    
    Requirements: 4.4
    
    Attributes:
        id: Unique ad group identifier
        name: Ad group display name
        campaign_id: Parent campaign identifier
        status: Ad group status (ENABLED, PAUSED, REMOVED)
        cost: Total cost
        impressions: Total impressions
        clicks: Total clicks
        conversions: Total conversions
    """
    
    id: str
    name: str
    campaign_id: str
    status: str
    cost: float
    impressions: int
    clicks: int
    conversions: float
    
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
            "cost": self.cost,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdGroup":
        """Create AdGroup from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            campaign_id=data.get("campaign_id", ""),
            status=data.get("status", ""),
            cost=float(data.get("cost", 0)),
            impressions=int(data.get("impressions", 0)),
            clicks=int(data.get("clicks", 0)),
            conversions=float(data.get("conversions", 0)),
        )
    
    @classmethod
    def from_api_response(
        cls, data: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None
    ) -> "AdGroup":
        """Create AdGroup from Google Ads API response with optional metrics."""
        metrics = metrics or {}
        ad_group = data.get("adGroup", data)
        
        # Extract ad group ID from resource name if needed
        ad_group_id = ad_group.get("id", "")
        if not ad_group_id and ad_group.get("resourceName"):
            ad_group_id = ad_group["resourceName"].split("/")[-1]
        
        # Extract campaign ID from resource name
        campaign_id = ""
        campaign_resource = ad_group.get("campaign", "")
        if campaign_resource:
            campaign_id = campaign_resource.split("/")[-1]
        
        # Parse metrics (Google Ads returns cost in micros)
        cost_micros = float(metrics.get("costMicros", metrics.get("cost_micros", 0)))
        cost = cost_micros / 1_000_000
        
        impressions = int(metrics.get("impressions", 0))
        clicks = int(metrics.get("clicks", 0))
        conversions = float(metrics.get("conversions", 0))
        
        return cls(
            id=str(ad_group_id),
            name=ad_group.get("name", ""),
            campaign_id=campaign_id,
            status=ad_group.get("status", ""),
            cost=cost,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
        )
