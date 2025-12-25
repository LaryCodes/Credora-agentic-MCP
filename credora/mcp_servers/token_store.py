"""
Token Store for secure OAuth token storage.

This module provides encrypted storage for OAuth tokens.

Requirements: 2.3, 7.1
"""

from datetime import datetime
from typing import Dict, List, Optional

from credora.mcp_servers.models.oauth import TokenData
from credora.security import TokenEncryption, get_encryption


class TokenStore:
    """
    Encrypted storage for OAuth tokens.
    
    Uses the existing encryption utilities from credora/security.py
    to securely store and retrieve OAuth tokens.
    
    Requirements: 2.3, 7.1
    """
    
    def __init__(self, encryption: Optional[TokenEncryption] = None):
        """Initialize the token store.
        
        Args:
            encryption: Optional TokenEncryption instance. If None, uses the
                       default encryption instance from security module.
        """
        self._encryption = encryption or get_encryption()
        # Storage structure: {user_id: {platform: encrypted_token_dict}}
        self._tokens: Dict[str, Dict[str, dict]] = {}
    
    def _get_storage_key(self, user_id: str, platform: str) -> str:
        """Generate a storage key for user/platform combination."""
        return f"{user_id}:{platform.lower()}"
    
    def _validate_inputs(self, user_id: str, platform: str) -> None:
        """Validate user_id and platform inputs.
        
        Args:
            user_id: The user identifier
            platform: The platform name
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        if not platform or not platform.strip():
            raise ValueError("platform is required and cannot be empty")
    
    def store_token(
        self, user_id: str, platform: str, token_data: TokenData
    ) -> None:
        """Store an OAuth token with encryption.
        
        The access_token and refresh_token are encrypted before storage.
        Other fields are stored as-is.
        
        Args:
            user_id: The user identifier
            platform: The platform name (e.g., "meta", "google", "shopify")
            token_data: The token data to store
            
        Raises:
            ValueError: If inputs are invalid
            
        Requirements: 2.3, 7.1
        """
        self._validate_inputs(user_id, platform)
        
        if token_data is None:
            raise ValueError("token_data is required")
        
        platform_lower = platform.lower().strip()
        user_id_clean = user_id.strip()
        
        # Encrypt sensitive token fields
        encrypted_data = {
            "access_token": self._encryption.encrypt(token_data.access_token),
            "refresh_token": self._encryption.encrypt(token_data.refresh_token),
            "expires_at": token_data.expires_at.isoformat(),
            "scopes": token_data.scopes.copy(),
            "platform_user_id": token_data.platform_user_id,
        }
        
        # Initialize user storage if needed
        if user_id_clean not in self._tokens:
            self._tokens[user_id_clean] = {}
        
        # Store the encrypted token data
        self._tokens[user_id_clean][platform_lower] = encrypted_data
    
    def get_token(self, user_id: str, platform: str) -> Optional[TokenData]:
        """Retrieve and decrypt an OAuth token.
        
        Args:
            user_id: The user identifier
            platform: The platform name
            
        Returns:
            TokenData with decrypted tokens, or None if not found
            
        Raises:
            ValueError: If inputs are invalid
            
        Requirements: 2.3, 7.1
        """
        self._validate_inputs(user_id, platform)
        
        platform_lower = platform.lower().strip()
        user_id_clean = user_id.strip()
        
        # Check if user has any tokens
        if user_id_clean not in self._tokens:
            return None
        
        # Check if platform token exists
        if platform_lower not in self._tokens[user_id_clean]:
            return None
        
        encrypted_data = self._tokens[user_id_clean][platform_lower]
        
        # Decrypt and reconstruct TokenData
        return TokenData(
            access_token=self._encryption.decrypt(encrypted_data["access_token"]),
            refresh_token=self._encryption.decrypt(encrypted_data["refresh_token"]),
            expires_at=datetime.fromisoformat(encrypted_data["expires_at"]),
            scopes=encrypted_data["scopes"].copy(),
            platform_user_id=encrypted_data["platform_user_id"],
        )
    
    def delete_token(self, user_id: str, platform: str) -> bool:
        """Delete a stored OAuth token.
        
        Args:
            user_id: The user identifier
            platform: The platform name
            
        Returns:
            True if token was deleted, False if it didn't exist
            
        Raises:
            ValueError: If inputs are invalid
            
        Requirements: 7.4
        """
        self._validate_inputs(user_id, platform)
        
        platform_lower = platform.lower().strip()
        user_id_clean = user_id.strip()
        
        # Check if user has any tokens
        if user_id_clean not in self._tokens:
            return False
        
        # Check if platform token exists
        if platform_lower not in self._tokens[user_id_clean]:
            return False
        
        # Delete the token
        del self._tokens[user_id_clean][platform_lower]
        
        # Clean up empty user entry
        if not self._tokens[user_id_clean]:
            del self._tokens[user_id_clean]
        
        return True
    
    def list_platforms(self, user_id: str) -> List[str]:
        """List all platforms with stored tokens for a user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            List of platform names with stored tokens
            
        Raises:
            ValueError: If user_id is invalid
            
        Requirements: 8.1
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        
        user_id_clean = user_id.strip()
        
        if user_id_clean not in self._tokens:
            return []
        
        return list(self._tokens[user_id_clean].keys())
    
    def has_token(self, user_id: str, platform: str) -> bool:
        """Check if a token exists for user/platform.
        
        Args:
            user_id: The user identifier
            platform: The platform name
            
        Returns:
            True if token exists, False otherwise
        """
        self._validate_inputs(user_id, platform)
        
        platform_lower = platform.lower().strip()
        user_id_clean = user_id.strip()
        
        return (
            user_id_clean in self._tokens
            and platform_lower in self._tokens[user_id_clean]
        )
    
    def clear_user_tokens(self, user_id: str) -> int:
        """Delete all tokens for a user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Number of tokens deleted
            
        Requirements: 7.4
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        
        user_id_clean = user_id.strip()
        
        if user_id_clean not in self._tokens:
            return 0
        
        count = len(self._tokens[user_id_clean])
        del self._tokens[user_id_clean]
        return count
