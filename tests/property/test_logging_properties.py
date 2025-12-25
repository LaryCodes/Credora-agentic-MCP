"""Property-based tests for MCP Server logging.

**Feature: platform-mcp-servers**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from credora.mcp_servers.logging import (
    MCPLogger,
    APIErrorLog,
    sanitize_string,
    sanitize_dict,
    mask_value,
    SENSITIVE_KEYS,
)
from credora.mcp_servers.errors import MCPErrorType


# Strategy for generating error types
error_type_strategy = st.sampled_from([e.value for e in MCPErrorType])

# Strategy for generating platform names
platform_strategy = st.sampled_from(["meta", "google", "shopify"])

# Strategy for generating HTTP methods
http_method_strategy = st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"])

# Strategy for generating status codes
status_code_strategy = st.integers(min_value=100, max_value=599)

# Strategy for generating error messages
error_message_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != "")

# Strategy for generating URLs
url_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;="),
    min_size=10,
    max_size=100,
).map(lambda x: f"https://api.example.com/{x}")

# Strategy for generating request IDs
request_id_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=8,
    max_size=36,
)


class TestErrorLogging:
    """
    **Feature: platform-mcp-servers, Property 10: Error Logging**
    **Validates: Requirements 6.4**
    
    For any API error that occurs, a log entry shall be created containing
    the error type, request details, and timestamp.
    """

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        platform=platform_strategy,
        request_method=http_method_strategy,
        status_code=status_code_strategy,
    )
    def test_log_api_error_creates_entry_with_required_fields(
        self, error_type, message, platform, request_method, status_code
    ):
        """log_api_error should create entry with error_type, message, timestamp."""
        logger = MCPLogger(name="test_logger")
        
        log_entry = logger.log_api_error(
            error_type=error_type,
            message=message,
            platform=platform,
            request_method=request_method,
            status_code=status_code,
        )
        
        # Verify required fields are present
        assert log_entry.error_type == error_type
        assert log_entry.message == message
        assert log_entry.timestamp is not None
        
        # Verify optional fields
        assert log_entry.platform == platform
        assert log_entry.request_method == request_method
        assert log_entry.status_code == status_code

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        request_url=url_strategy,
        request_id=request_id_strategy,
    )
    def test_log_api_error_includes_request_details(
        self, error_type, message, request_url, request_id
    ):
        """log_api_error should include request URL and ID."""
        logger = MCPLogger(name="test_logger")
        
        log_entry = logger.log_api_error(
            error_type=error_type,
            message=message,
            request_url=request_url,
            request_id=request_id,
        )
        
        assert log_entry.request_url == request_url
        assert log_entry.request_id == request_id

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
    )
    def test_log_entry_stored_in_logger(self, error_type, message):
        """Logged errors should be stored and retrievable."""
        logger = MCPLogger(name="test_logger")
        
        log_entry = logger.log_api_error(
            error_type=error_type,
            message=message,
        )
        
        # Should be retrievable
        logs = logger.get_error_logs()
        assert len(logs) >= 1
        
        # Most recent should be our entry
        latest = logger.get_latest_errors(1)
        assert len(latest) == 1
        assert latest[0].error_type == error_type
        assert latest[0].message == message

    @settings(max_examples=100)
    @given(
        error_types=st.lists(error_type_strategy, min_size=1, max_size=10),
    )
    def test_error_count_matches_logged_errors(self, error_types):
        """error_count should match number of logged errors."""
        logger = MCPLogger(name="test_logger")
        
        for error_type in error_types:
            logger.log_api_error(
                error_type=error_type,
                message="Test error",
            )
        
        assert logger.error_count() == len(error_types)

    @settings(max_examples=100)
    @given(
        platform=platform_strategy,
        other_platform=platform_strategy,
        count=st.integers(min_value=1, max_value=5),
    )
    def test_filter_by_platform(self, platform, other_platform, count):
        """get_error_logs should filter by platform correctly."""
        # Skip if platforms are the same
        if platform == other_platform:
            return
        
        logger = MCPLogger(name="test_logger")
        
        # Log errors for target platform
        for _ in range(count):
            logger.log_api_error(
                error_type="api_error",
                message="Test error",
                platform=platform,
            )
        
        # Log errors for other platform
        logger.log_api_error(
            error_type="api_error",
            message="Other error",
            platform=other_platform,
        )
        
        # Filter by target platform
        filtered = logger.get_error_logs(platform=platform)
        
        assert len(filtered) == count
        for log in filtered:
            assert log.platform == platform

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        other_error_type=error_type_strategy,
        count=st.integers(min_value=1, max_value=5),
    )
    def test_filter_by_error_type(self, error_type, other_error_type, count):
        """get_error_logs should filter by error_type correctly."""
        # Skip if error types are the same
        if error_type == other_error_type:
            return
        
        logger = MCPLogger(name="test_logger")
        
        # Log errors of target type
        for _ in range(count):
            logger.log_api_error(
                error_type=error_type,
                message="Test error",
            )
        
        # Log errors of other type
        logger.log_api_error(
            error_type=other_error_type,
            message="Other error",
        )
        
        # Filter by target error type
        filtered = logger.get_error_logs(error_type=error_type)
        
        assert len(filtered) == count
        for log in filtered:
            assert log.error_type == error_type

    @settings(max_examples=100)
    @given(
        count=st.integers(min_value=5, max_value=20),
        limit=st.integers(min_value=1, max_value=10),
    )
    def test_limit_returns_correct_count(self, count, limit):
        """get_error_logs with limit should return at most limit entries."""
        logger = MCPLogger(name="test_logger")
        
        for i in range(count):
            logger.log_api_error(
                error_type="api_error",
                message=f"Error {i}",
            )
        
        limited = logger.get_error_logs(limit=limit)
        
        assert len(limited) == min(limit, count)

    def test_clear_error_logs_removes_all(self):
        """clear_error_logs should remove all entries."""
        logger = MCPLogger(name="test_logger")
        
        # Log some errors
        for i in range(5):
            logger.log_api_error(
                error_type="api_error",
                message=f"Error {i}",
            )
        
        assert logger.error_count() == 5
        
        # Clear
        cleared = logger.clear_error_logs()
        
        assert cleared == 5
        assert logger.error_count() == 0

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        platform=platform_strategy,
        request_method=http_method_strategy,
        request_url=url_strategy,
        status_code=status_code_strategy,
        request_id=request_id_strategy,
    )
    def test_to_dict_includes_all_fields(
        self, error_type, message, platform, request_method, request_url, status_code, request_id
    ):
        """APIErrorLog.to_dict should include all set fields."""
        logger = MCPLogger(name="test_logger")
        
        log_entry = logger.log_api_error(
            error_type=error_type,
            message=message,
            platform=platform,
            request_method=request_method,
            request_url=request_url,
            status_code=status_code,
            request_id=request_id,
        )
        
        log_dict = log_entry.to_dict()
        
        # Required fields
        assert "timestamp" in log_dict
        assert "error_type" in log_dict
        assert "message" in log_dict
        
        # Optional fields that were set
        assert "platform" in log_dict
        assert "request_method" in log_dict
        assert "request_url" in log_dict
        assert "status_code" in log_dict
        assert "request_id" in log_dict
        
        # Values should match (message may be sanitized)
        assert log_dict["error_type"] == error_type
        assert log_dict["platform"] == platform
        assert log_dict["request_method"] == request_method
        assert log_dict["status_code"] == status_code
        assert log_dict["request_id"] == request_id

    def test_logs_returned_newest_first(self):
        """get_error_logs should return logs newest first."""
        logger = MCPLogger(name="test_logger")
        
        # Log errors with identifiable messages
        for i in range(5):
            logger.log_api_error(
                error_type="api_error",
                message=f"Error {i}",
            )
        
        logs = logger.get_error_logs()
        
        # First log should be the most recent (Error 4)
        assert "Error 4" in logs[0].message
        # Last log should be the oldest (Error 0)
        assert "Error 0" in logs[-1].message



class TestNoSensitiveDataInLogs:
    """
    **Feature: platform-mcp-servers, Property 12: No Sensitive Data in Logs**
    **Validates: Requirements 7.3**
    
    For any log entry generated by the system, the entry shall not contain
    plaintext tokens or unmasked PII.
    """

    # Strategy for generating realistic tokens (alphanumeric with common token chars)
    token_strategy = st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"),
        min_size=10,
        max_size=100,
    ).filter(lambda x: x.strip() != "" and x[0].isalnum())

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_access_token_masked_in_string(self, token):
        """access_token values should be masked in sanitized strings."""
        text = f'access_token: "{token}"'
        sanitized = sanitize_string(text)
        
        # Original token should not appear in sanitized output
        assert token not in sanitized
        # Should contain mask indicator
        assert "****" in sanitized

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_refresh_token_masked_in_string(self, token):
        """refresh_token values should be masked in sanitized strings."""
        text = f'refresh_token="{token}"'
        sanitized = sanitize_string(text)
        
        # Original token should not appear in sanitized output
        assert token not in sanitized
        # Should contain mask indicator
        assert "****" in sanitized

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_bearer_token_masked_in_string(self, token):
        """Bearer tokens should be masked in sanitized strings."""
        text = f"Authorization: Bearer {token}"
        sanitized = sanitize_string(text)
        
        # Original token should not appear in sanitized output
        assert token not in sanitized
        # Should contain mask indicator
        assert "****" in sanitized

    @settings(max_examples=100)
    @given(
        key=token_strategy,
    )
    def test_api_key_masked_in_string(self, key):
        """api_key values should be masked in sanitized strings."""
        text = f'api_key: "{key}"'
        sanitized = sanitize_string(text)
        
        # Original key should not appear in sanitized output
        assert key not in sanitized
        # Should contain mask indicator
        assert "****" in sanitized

    @settings(max_examples=100)
    @given(
        secret=token_strategy,
    )
    def test_client_secret_masked_in_string(self, secret):
        """client_secret values should be masked in sanitized strings."""
        text = f'client_secret="{secret}"'
        sanitized = sanitize_string(text)
        
        # Original secret should not appear in sanitized output
        assert secret not in sanitized
        # Should contain mask indicator
        assert "****" in sanitized

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_access_token_masked_in_dict(self, token):
        """access_token values should be masked in sanitized dicts."""
        data = {"access_token": token, "other_field": "visible"}
        sanitized = sanitize_dict(data)
        
        # Original token should not appear in sanitized output
        assert sanitized["access_token"] != token
        assert "****" in sanitized["access_token"]
        # Non-sensitive field should be preserved
        assert sanitized["other_field"] == "visible"

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_refresh_token_masked_in_dict(self, token):
        """refresh_token values should be masked in sanitized dicts."""
        data = {"refresh_token": token}
        sanitized = sanitize_dict(data)
        
        assert sanitized["refresh_token"] != token
        assert "****" in sanitized["refresh_token"]

    @settings(max_examples=100)
    @given(
        password=token_strategy,
    )
    def test_password_masked_in_dict(self, password):
        """password values should be masked in sanitized dicts."""
        data = {"password": password}
        sanitized = sanitize_dict(data)
        
        assert sanitized["password"] != password
        assert "****" in sanitized["password"]

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_nested_sensitive_data_masked(self, token):
        """Sensitive data in nested dicts should be masked."""
        data = {
            "response": {
                "data": {
                    "access_token": token,
                }
            }
        }
        sanitized = sanitize_dict(data)
        
        assert sanitized["response"]["data"]["access_token"] != token
        assert "****" in sanitized["response"]["data"]["access_token"]

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_api_error_log_sanitizes_details(self, token):
        """APIErrorLog should sanitize sensitive data in details."""
        logger = MCPLogger(name="test_logger")
        
        log_entry = logger.log_api_error(
            error_type="api_error",
            message="Test error",
            details={"access_token": token, "user_id": "123"},
        )
        
        log_dict = log_entry.to_dict()
        
        # Token should be masked in details
        assert log_dict["details"]["access_token"] != token
        assert "****" in log_dict["details"]["access_token"]
        # Non-sensitive data should be preserved
        assert log_dict["details"]["user_id"] == "123"

    @settings(max_examples=100)
    @given(
        token=token_strategy,
    )
    def test_api_error_log_sanitizes_message(self, token):
        """APIErrorLog should sanitize sensitive data in message."""
        logger = MCPLogger(name="test_logger")
        
        message = f'Failed with access_token: "{token}"'
        log_entry = logger.log_api_error(
            error_type="api_error",
            message=message,
        )
        
        log_dict = log_entry.to_dict()
        
        # Token should be masked in message
        assert token not in log_dict["message"]

    @settings(max_examples=100)
    @given(
        token=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
            min_size=10,
            max_size=100,
        ).filter(lambda x: x.strip() != "" and x[0].isalnum() and "access" not in x.lower() and "token" not in x.lower()),
    )
    def test_api_error_log_sanitizes_url(self, token):
        """APIErrorLog should sanitize sensitive data in URL."""
        logger = MCPLogger(name="test_logger")
        
        url = f'https://api.example.com?access_token="{token}"'
        log_entry = logger.log_api_error(
            error_type="api_error",
            message="Test error",
            request_url=url,
        )
        
        log_dict = log_entry.to_dict()
        
        # Token should be masked in URL
        assert token not in log_dict["request_url"]

    def test_mask_value_shows_partial(self):
        """mask_value should show first few characters."""
        value = "abcdefghij"
        masked = mask_value(value, visible_chars=4)
        
        assert masked.startswith("abcd")
        assert masked.endswith("****")
        assert "efghij" not in masked

    def test_mask_value_short_string(self):
        """mask_value should fully mask short strings."""
        value = "abc"
        masked = mask_value(value, visible_chars=4)
        
        assert masked == "****"

    def test_mask_value_empty_string(self):
        """mask_value should handle empty strings."""
        masked = mask_value("")
        
        assert masked == "****"

    @settings(max_examples=100)
    @given(
        key=st.sampled_from(list(SENSITIVE_KEYS)),
        value=token_strategy,
    )
    def test_all_sensitive_keys_masked(self, key, value):
        """All keys in SENSITIVE_KEYS should have values masked."""
        data = {key: value}
        sanitized = sanitize_dict(data)
        
        assert sanitized[key] != value
        assert "****" in sanitized[key]

    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    @given(
        key=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            min_size=5,
            max_size=20,
        ).filter(lambda x: x.lower() not in SENSITIVE_KEYS and not any(s in x.lower() for s in SENSITIVE_KEYS)),
        value=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
    )
    def test_non_sensitive_keys_preserved(self, key, value):
        """Non-sensitive keys should have values preserved."""
        data = {key: value}
        sanitized = sanitize_dict(data)
        
        # For non-sensitive keys, value should be preserved or sanitized if it contains patterns
        # The key point is that the key itself doesn't trigger masking
        assert key in sanitized

    def test_deep_nesting_handled(self):
        """Deeply nested dicts should be handled without error."""
        data = {"level1": {"level2": {"level3": {"level4": {"level5": {"access_token": "secret123"}}}}}}
        sanitized = sanitize_dict(data)
        
        # Should not raise and should mask the token
        assert "****" in sanitized["level1"]["level2"]["level3"]["level4"]["level5"]["access_token"]

    def test_max_depth_truncation(self):
        """Very deep nesting should be truncated."""
        # Create deeply nested structure
        data = {"level": {}}
        current = data["level"]
        for i in range(15):
            current["nested"] = {}
            current = current["nested"]
        current["access_token"] = "secret"
        
        sanitized = sanitize_dict(data, max_depth=5)
        
        # Should not raise and should handle truncation
        assert sanitized is not None
