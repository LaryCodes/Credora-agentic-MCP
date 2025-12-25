"""Security utilities for token encryption and user data isolation.

Requirements: 8.1, 8.2, 8.3
"""

import os
import base64
from typing import Optional, Dict, Set, Any

from cryptography.fernet import Fernet


class TokenEncryption:
    """Handles encryption and decryption of platform tokens.
    
    Uses Fernet symmetric encryption from the cryptography library.
    
    Requirements: 8.1
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """Initialize with an encryption key.
        
        Args:
            key: Fernet key bytes. If None, generates a new key.
        """
        if key is None:
            key = self._get_or_generate_key()
        self._fernet = Fernet(key)
        self._key = key
    
    @staticmethod
    def _get_or_generate_key() -> bytes:
        """Get key from environment or generate a new one."""
        env_key = os.environ.get("CREDORA_ENCRYPTION_KEY")
        if env_key:
            return base64.urlsafe_b64decode(env_key)
        return Fernet.generate_key()
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new Fernet encryption key.
        
        Returns:
            A new Fernet key as bytes
        """
        return Fernet.generate_key()
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext token.
        
        Args:
            plaintext: The token to encrypt
            
        Returns:
            Base64-encoded encrypted token
            
        Raises:
            ValueError: If plaintext is empty
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty token")
        
        encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted token.
        
        Args:
            ciphertext: Base64-encoded encrypted token
            
        Returns:
            Decrypted plaintext token
            
        Raises:
            ValueError: If ciphertext is empty or invalid
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty ciphertext")
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {e}")
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value appears to be encrypted.
        
        This is a heuristic check - encrypted values are base64 and
        cannot be decrypted with a wrong key without error.
        
        Args:
            value: The value to check
            
        Returns:
            True if value appears to be encrypted
        """
        if not value:
            return False
        
        # Encrypted tokens are base64 encoded and have specific structure
        try:
            decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
            # Fernet tokens start with version byte and have minimum length
            return len(decoded) >= 57  # Minimum Fernet token size
        except Exception:
            return False


# Global instance for convenience
_default_encryption: Optional[TokenEncryption] = None


def get_encryption() -> TokenEncryption:
    """Get the default TokenEncryption instance."""
    global _default_encryption
    if _default_encryption is None:
        _default_encryption = TokenEncryption()
    return _default_encryption


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token using the default encryption instance."""
    return get_encryption().encrypt(plaintext)


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a token using the default encryption instance."""
    return get_encryption().decrypt(ciphertext)


class UserDataIsolation:
    """Enforces user data isolation boundaries.
    
    Ensures that data access operations are scoped to the requesting user
    and that no cross-user data leakage can occur.
    
    Requirements: 8.2
    """
    
    def __init__(self):
        """Initialize user data isolation tracker."""
        # Track which users own which data keys
        self._user_data_ownership: Dict[str, Set[str]] = {}
    
    def validate_user_id(self, user_id: str) -> bool:
        """Validate that a user_id is properly formatted.
        
        Args:
            user_id: The user identifier to validate
            
        Returns:
            True if valid, raises ValueError if invalid
            
        Raises:
            ValueError: If user_id is empty or invalid
        """
        if not user_id:
            raise ValueError("user_id is required and cannot be None")
        if not isinstance(user_id, str):
            raise ValueError("user_id must be a string")
        if not user_id.strip():
            raise ValueError("user_id cannot be empty or whitespace only")
        return True
    
    def register_data_ownership(self, user_id: str, data_key: str) -> None:
        """Register that a user owns a specific data key.
        
        Args:
            user_id: The user who owns the data
            data_key: The key identifying the data
            
        Requirements: 8.2
        """
        self.validate_user_id(user_id)
        if not data_key or not data_key.strip():
            raise ValueError("data_key is required and cannot be empty")
        
        if user_id not in self._user_data_ownership:
            self._user_data_ownership[user_id] = set()
        self._user_data_ownership[user_id].add(data_key)
    
    def check_data_access(self, user_id: str, data_key: str) -> bool:
        """Check if a user has access to a specific data key.
        
        Args:
            user_id: The user requesting access
            data_key: The key identifying the data
            
        Returns:
            True if user has access, False otherwise
            
        Requirements: 8.2
        """
        self.validate_user_id(user_id)
        if not data_key or not data_key.strip():
            return False
        
        # User has access if they own the data
        if user_id in self._user_data_ownership:
            return data_key in self._user_data_ownership[user_id]
        return False
    
    def get_user_data_keys(self, user_id: str) -> Set[str]:
        """Get all data keys owned by a user.
        
        Args:
            user_id: The user to get data keys for
            
        Returns:
            Set of data keys owned by the user
            
        Requirements: 8.2
        """
        self.validate_user_id(user_id)
        return self._user_data_ownership.get(user_id, set()).copy()
    
    def remove_data_ownership(self, user_id: str, data_key: str) -> bool:
        """Remove a user's ownership of a data key.
        
        Args:
            user_id: The user who owns the data
            data_key: The key identifying the data
            
        Returns:
            True if ownership was removed, False if it didn't exist
            
        Requirements: 8.3
        """
        self.validate_user_id(user_id)
        if user_id in self._user_data_ownership:
            if data_key in self._user_data_ownership[user_id]:
                self._user_data_ownership[user_id].discard(data_key)
                return True
        return False
    
    def clear_user_data(self, user_id: str) -> Set[str]:
        """Clear all data ownership for a user.
        
        Args:
            user_id: The user to clear data for
            
        Returns:
            Set of data keys that were cleared
            
        Requirements: 8.3
        """
        self.validate_user_id(user_id)
        if user_id in self._user_data_ownership:
            cleared_keys = self._user_data_ownership[user_id].copy()
            del self._user_data_ownership[user_id]
            return cleared_keys
        return set()
    
    def verify_isolation(self, user_id_a: str, user_id_b: str) -> bool:
        """Verify that two users have completely isolated data.
        
        Args:
            user_id_a: First user
            user_id_b: Second user
            
        Returns:
            True if users have no shared data keys
            
        Requirements: 8.2
        """
        self.validate_user_id(user_id_a)
        self.validate_user_id(user_id_b)
        
        if user_id_a == user_id_b:
            return True  # Same user, isolation is trivially satisfied
        
        keys_a = self._user_data_ownership.get(user_id_a, set())
        keys_b = self._user_data_ownership.get(user_id_b, set())
        
        # No intersection means complete isolation
        return len(keys_a & keys_b) == 0


# Global instance for user data isolation
_user_isolation: Optional[UserDataIsolation] = None


def get_user_isolation() -> UserDataIsolation:
    """Get the default UserDataIsolation instance."""
    global _user_isolation
    if _user_isolation is None:
        _user_isolation = UserDataIsolation()
    return _user_isolation


def set_user_isolation(isolation: UserDataIsolation) -> None:
    """Set the user isolation instance (for testing)."""
    global _user_isolation
    _user_isolation = isolation


def validate_user_access(user_id: str, data_key: str) -> bool:
    """Validate that a user has access to specific data.
    
    Args:
        user_id: The user requesting access
        data_key: The key identifying the data
        
    Returns:
        True if user has access
        
    Raises:
        ValueError: If user_id is invalid
        PermissionError: If user does not have access
    """
    isolation = get_user_isolation()
    isolation.validate_user_id(user_id)
    
    if not isolation.check_data_access(user_id, data_key):
        raise PermissionError(f"User '{user_id}' does not have access to data '{data_key}'")
    return True


class AccessRevocation:
    """Handles access revocation and cleanup of user data.
    
    When a user revokes access, this class ensures all stored tokens
    and cached data for that platform are deleted.
    
    Requirements: 8.3
    """
    
    def __init__(self):
        """Initialize access revocation handler."""
        # Track revoked access for audit purposes
        self._revocation_log: Dict[str, list] = {}
    
    def revoke_platform_access(
        self, 
        user_id: str, 
        platform: str, 
        state_manager: Any
    ) -> Dict[str, Any]:
        """Revoke access to a specific platform and clean up all associated data.
        
        This function:
        1. Removes the platform token from session state
        2. Removes the platform from connected platforms list
        3. Clears any cached data for that platform
        4. Removes data ownership records
        
        Args:
            user_id: The user revoking access
            platform: The platform to revoke access for
            state_manager: The StateManager instance to update
            
        Returns:
            Dictionary with cleanup results
            
        Requirements: 8.3
        """
        isolation = get_user_isolation()
        isolation.validate_user_id(user_id)
        
        if not platform or not platform.strip():
            raise ValueError("platform is required and cannot be empty")
        
        platform_lower = platform.lower().strip()
        result = {
            "user_id": user_id,
            "platform": platform_lower,
            "token_deleted": False,
            "platform_disconnected": False,
            "data_ownership_cleared": False,
            "cached_data_cleared": False,
        }
        
        # Get current session state
        session = state_manager.get_session_state(user_id)
        updates = {}
        
        # Remove platform token
        if platform_lower in session.platform_tokens:
            new_tokens = {k: v for k, v in session.platform_tokens.items() if k != platform_lower}
            updates["platform_tokens"] = new_tokens
            result["token_deleted"] = True
        
        # Remove from connected platforms
        if platform_lower in session.connected_platforms:
            new_platforms = [p for p in session.connected_platforms if p != platform_lower]
            updates["connected_platforms"] = new_platforms
            result["platform_disconnected"] = True
        
        # Apply updates if any
        if updates:
            state_manager.update_session_state(user_id, updates)
        
        # Clear data ownership for platform-related keys
        platform_data_key = f"platform:{user_id}:{platform_lower}"
        if isolation.remove_data_ownership(user_id, platform_data_key):
            result["data_ownership_cleared"] = True
        
        # Clear any cached data keys for this platform
        user_keys = isolation.get_user_data_keys(user_id)
        for key in user_keys:
            if platform_lower in key:
                isolation.remove_data_ownership(user_id, key)
                result["cached_data_cleared"] = True
        
        # Log the revocation
        if user_id not in self._revocation_log:
            self._revocation_log[user_id] = []
        self._revocation_log[user_id].append({
            "platform": platform_lower,
            "result": result,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        
        return result
    
    def revoke_all_access(self, user_id: str, state_manager: Any) -> Dict[str, Any]:
        """Revoke access to all platforms and clear all user data.
        
        This function:
        1. Removes all platform tokens
        2. Clears all connected platforms
        3. Clears all data ownership records
        4. Clears the entire session
        
        Args:
            user_id: The user revoking all access
            state_manager: The StateManager instance to update
            
        Returns:
            Dictionary with cleanup results
            
        Requirements: 8.3
        """
        isolation = get_user_isolation()
        isolation.validate_user_id(user_id)
        
        result = {
            "user_id": user_id,
            "platforms_revoked": [],
            "tokens_deleted": 0,
            "session_cleared": False,
            "data_ownership_cleared": False,
        }
        
        # Get current session state
        session = state_manager.get_session_state(user_id)
        
        # Track what we're cleaning up
        result["platforms_revoked"] = list(session.connected_platforms)
        result["tokens_deleted"] = len(session.platform_tokens)
        
        # Clear the entire session
        if state_manager.clear_session(user_id):
            result["session_cleared"] = True
        
        # Clear all data ownership for this user
        cleared_keys = isolation.clear_user_data(user_id)
        if cleared_keys:
            result["data_ownership_cleared"] = True
            result["cleared_keys_count"] = len(cleared_keys)
        
        # Log the revocation
        if user_id not in self._revocation_log:
            self._revocation_log[user_id] = []
        self._revocation_log[user_id].append({
            "type": "full_revocation",
            "result": result,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        
        return result
    
    def get_revocation_log(self, user_id: str) -> list:
        """Get the revocation log for a user.
        
        Args:
            user_id: The user to get the log for
            
        Returns:
            List of revocation events
        """
        return self._revocation_log.get(user_id, []).copy()
    
    def verify_cleanup(self, user_id: str, platform: str, state_manager: Any) -> bool:
        """Verify that all data for a platform has been cleaned up.
        
        Args:
            user_id: The user to verify cleanup for
            platform: The platform to verify cleanup for
            state_manager: The StateManager instance to check
            
        Returns:
            True if all data has been cleaned up
            
        Requirements: 8.3
        """
        isolation = get_user_isolation()
        isolation.validate_user_id(user_id)
        
        platform_lower = platform.lower().strip()
        
        # Check session state
        session = state_manager.get_session_state(user_id)
        
        # Token should not exist
        if platform_lower in session.platform_tokens:
            return False
        
        # Platform should not be connected
        if platform_lower in session.connected_platforms:
            return False
        
        # No data ownership keys should contain the platform
        user_keys = isolation.get_user_data_keys(user_id)
        for key in user_keys:
            if platform_lower in key:
                return False
        
        return True


# Global instance for access revocation
_access_revocation: Optional[AccessRevocation] = None


def get_access_revocation() -> AccessRevocation:
    """Get the default AccessRevocation instance."""
    global _access_revocation
    if _access_revocation is None:
        _access_revocation = AccessRevocation()
    return _access_revocation


def set_access_revocation(revocation: AccessRevocation) -> None:
    """Set the access revocation instance (for testing)."""
    global _access_revocation
    _access_revocation = revocation


def revoke_access(user_id: str, platform: str, state_manager: Any) -> Dict[str, Any]:
    """Revoke access to a platform and clean up all associated data.
    
    Convenience function that uses the default AccessRevocation instance.
    
    Args:
        user_id: The user revoking access
        platform: The platform to revoke access for
        state_manager: The StateManager instance to update
        
    Returns:
        Dictionary with cleanup results
        
    Requirements: 8.3
    """
    return get_access_revocation().revoke_platform_access(user_id, platform, state_manager)


def revoke_all_user_access(user_id: str, state_manager: Any) -> Dict[str, Any]:
    """Revoke all access and clear all user data.
    
    Convenience function that uses the default AccessRevocation instance.
    
    Args:
        user_id: The user revoking all access
        state_manager: The StateManager instance to update
        
    Returns:
        Dictionary with cleanup results
        
    Requirements: 8.3
    """
    return get_access_revocation().revoke_all_access(user_id, state_manager)


__all__ = [
    "TokenEncryption",
    "get_encryption",
    "encrypt_token",
    "decrypt_token",
    "UserDataIsolation",
    "get_user_isolation",
    "set_user_isolation",
    "validate_user_access",
    "AccessRevocation",
    "get_access_revocation",
    "set_access_revocation",
    "revoke_access",
    "revoke_all_user_access",
]
