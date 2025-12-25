"""
OAuth-related data models for MCP servers.

Requirements: 2.2
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# Valid connection statuses
VALID_CONNECTION_STATUSES = {"active", "expired", "error"}

# Supported platforms
SUPPORTED_PLATFORMS = {"meta", "google", "shopify"}


@dataclass
class TokenData:
    """OAuth token data stored for a platform connection.
    
    Requirements: 2.2, 2.3, 7.1
    """
    
    access_token: str  # Encrypted when stored
    refresh_token: str  # Encrypted when stored
    expires_at: datetime
    scopes: List[str]
    platform_user_id: str
    
    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.access_token:
            raise ValueError("access_token is required and cannot be empty")
        if not self.refresh_token:
            raise ValueError("refresh_token is required and cannot be empty")
        if not isinstance(self.expires_at, datetime):
            raise ValueError("expires_at must be a datetime object")
        if not isinstance(self.scopes, list):
            raise ValueError("scopes must be a list")
        if not self.platform_user_id:
            raise ValueError("platform_user_id is required and cannot be empty")
    
    def is_expired(self) -> bool:
        """Check if the access token has expired."""
        return datetime.now() >= self.expires_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "scopes": self.scopes,
            "platform_user_id": self.platform_user_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TokenData":
        """Create TokenData from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            scopes=data["scopes"],
            platform_user_id=data["platform_user_id"],
        )


@dataclass
class OAuthConfig:
    """OAuth configuration for a platform.
    
    Requirements: 2.1, 2.6
    """
    
    client_id: str
    client_secret: str  # Encrypted
    redirect_uri: str
    scopes: List[str]
    auth_url: str
    token_url: str
    
    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.client_id:
            raise ValueError("client_id is required and cannot be empty")
        if not self.client_secret:
            raise ValueError("client_secret is required and cannot be empty")
        if not self.redirect_uri:
            raise ValueError("redirect_uri is required and cannot be empty")
        if not isinstance(self.scopes, list):
            raise ValueError("scopes must be a list")
        if not self.auth_url:
            raise ValueError("auth_url is required and cannot be empty")
        if not self.token_url:
            raise ValueError("token_url is required and cannot be empty")
        
        # Validate URLs start with https
        if not self.auth_url.startswith("https://"):
            raise ValueError("auth_url must use HTTPS")
        if not self.token_url.startswith("https://"):
            raise ValueError("token_url must use HTTPS")


@dataclass
class Connection:
    """Represents a user's connection to a platform.
    
    Requirements: 8.1, 8.5
    """
    
    platform: str
    user_id: str
    platform_user_id: str
    connected_at: datetime
    last_sync: datetime
    status: str  # "active", "expired", "error"
    
    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.platform:
            raise ValueError("platform is required and cannot be empty")
        if not self.user_id:
            raise ValueError("user_id is required and cannot be empty")
        if not self.platform_user_id:
            raise ValueError("platform_user_id is required and cannot be empty")
        if not isinstance(self.connected_at, datetime):
            raise ValueError("connected_at must be a datetime object")
        if not isinstance(self.last_sync, datetime):
            raise ValueError("last_sync must be a datetime object")
        if self.status not in VALID_CONNECTION_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(VALID_CONNECTION_STATUSES)}"
            )
    
    def is_active(self) -> bool:
        """Check if the connection is active."""
        return self.status == "active"


@dataclass
class ConnectionHealth:
    """Health status of a platform connection.
    
    Requirements: 8.4
    """
    
    platform: str
    is_healthy: bool
    token_valid: bool
    last_checked: datetime
    error_message: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.platform:
            raise ValueError("platform is required and cannot be empty")
        if not isinstance(self.is_healthy, bool):
            raise ValueError("is_healthy must be a boolean")
        if not isinstance(self.token_valid, bool):
            raise ValueError("token_valid must be a boolean")
        if not isinstance(self.last_checked, datetime):
            raise ValueError("last_checked must be a datetime object")
