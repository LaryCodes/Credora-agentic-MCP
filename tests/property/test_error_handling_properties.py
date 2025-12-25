"""Property-based tests for MCP Server error handling.

**Feature: platform-mcp-servers**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from credora.mcp_servers.errors import (
    MCPError,
    MCPErrorType,
    RetryConfig,
    classify_http_error,
)


# Strategy for generating error types
error_type_strategy = st.sampled_from(list(MCPErrorType))

# Strategy for generating error messages
error_message_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != "")

# Strategy for generating retry_after values
retry_after_strategy = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=3600),
)

# Strategy for generating error details
error_details_strategy = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
        values=st.one_of(
            st.text(max_size=50),
            st.integers(),
            st.booleans(),
        ),
        max_size=5,
    ),
)


class TestErrorResponseStructure:
    """
    **Feature: platform-mcp-servers, Property 8: Error Response Structure**
    **Validates: Requirements 6.1, 6.3**
    
    For any API error (rate limit, auth failure, network error), the MCP server
    shall return a structured error with error_type, message, and recoverable fields.
    """

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        recoverable=st.booleans(),
        retry_after=retry_after_strategy,
        details=error_details_strategy,
    )
    def test_mcp_error_to_dict_has_required_fields(
        self, error_type, message, recoverable, retry_after, details
    ):
        """MCPError.to_dict() should always include error_type, message, recoverable."""
        error = MCPError(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            retry_after=retry_after,
            details=details,
        )
        
        error_dict = error.to_dict()
        
        # Required fields must always be present
        assert "error_type" in error_dict
        assert "message" in error_dict
        assert "recoverable" in error_dict
        
        # Values should match
        assert error_dict["error_type"] == error_type.value
        assert error_dict["message"] == message
        assert error_dict["recoverable"] == recoverable

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        recoverable=st.booleans(),
        retry_after=st.integers(min_value=1, max_value=3600),
    )
    def test_retry_after_included_when_set(
        self, error_type, message, recoverable, retry_after
    ):
        """retry_after should be included in dict when set."""
        error = MCPError(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            retry_after=retry_after,
        )
        
        error_dict = error.to_dict()
        
        assert "retry_after" in error_dict
        assert error_dict["retry_after"] == retry_after

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        recoverable=st.booleans(),
    )
    def test_retry_after_excluded_when_none(
        self, error_type, message, recoverable
    ):
        """retry_after should not be in dict when None."""
        error = MCPError(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            retry_after=None,
        )
        
        error_dict = error.to_dict()
        
        assert "retry_after" not in error_dict

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        recoverable=st.booleans(),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.text(max_size=50),
            min_size=1,
            max_size=5,
        ),
    )
    def test_details_included_when_set(
        self, error_type, message, recoverable, details
    ):
        """details should be included in dict when set."""
        error = MCPError(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            details=details,
        )
        
        error_dict = error.to_dict()
        
        assert "details" in error_dict
        assert error_dict["details"] == details

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        recoverable=st.booleans(),
    )
    def test_details_excluded_when_none(
        self, error_type, message, recoverable
    ):
        """details should not be in dict when None."""
        error = MCPError(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            details=None,
        )
        
        error_dict = error.to_dict()
        
        assert "details" not in error_dict

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=error_message_strategy,
        recoverable=st.booleans(),
        retry_after=retry_after_strategy,
        details=error_details_strategy,
    )
    def test_error_round_trip(
        self, error_type, message, recoverable, retry_after, details
    ):
        """MCPError should round-trip through to_dict/from_dict."""
        original = MCPError(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            retry_after=retry_after,
            details=details,
        )
        
        error_dict = original.to_dict()
        restored = MCPError.from_dict(error_dict)
        
        assert restored.error_type == original.error_type
        assert restored.message == original.message
        assert restored.recoverable == original.recoverable
        assert restored.retry_after == original.retry_after
        assert restored.details == original.details

    @settings(max_examples=100)
    @given(message=error_message_strategy)
    def test_auth_required_factory(self, message):
        """auth_required factory should create correct error type."""
        error = MCPError.auth_required(message)
        
        assert error.error_type == MCPErrorType.AUTH_REQUIRED
        assert error.message == message
        assert error.recoverable is False

    @settings(max_examples=100)
    @given(message=error_message_strategy)
    def test_auth_expired_factory(self, message):
        """auth_expired factory should create correct error type."""
        error = MCPError.auth_expired(message)
        
        assert error.error_type == MCPErrorType.AUTH_EXPIRED
        assert error.message == message
        assert error.recoverable is False

    @settings(max_examples=100)
    @given(
        message=error_message_strategy,
        retry_after=st.integers(min_value=1, max_value=3600),
    )
    def test_rate_limited_factory(self, message, retry_after):
        """rate_limited factory should create correct error type."""
        error = MCPError.rate_limited(message, retry_after=retry_after)
        
        assert error.error_type == MCPErrorType.RATE_LIMITED
        assert error.message == message
        assert error.recoverable is True
        assert error.retry_after == retry_after

    @settings(max_examples=100)
    @given(
        message=error_message_strategy,
        recoverable=st.booleans(),
    )
    def test_api_error_factory(self, message, recoverable):
        """api_error factory should create correct error type."""
        error = MCPError.api_error(message, recoverable=recoverable)
        
        assert error.error_type == MCPErrorType.API_ERROR
        assert error.message == message
        assert error.recoverable == recoverable

    @settings(max_examples=100)
    @given(message=error_message_strategy)
    def test_network_error_factory(self, message):
        """network_error factory should create correct error type."""
        error = MCPError.network_error(message)
        
        assert error.error_type == MCPErrorType.NETWORK_ERROR
        assert error.message == message
        assert error.recoverable is True

    @settings(max_examples=100)
    @given(message=error_message_strategy)
    def test_invalid_params_factory(self, message):
        """invalid_params factory should create correct error type."""
        error = MCPError.invalid_params(message)
        
        assert error.error_type == MCPErrorType.INVALID_PARAMS
        assert error.message == message
        assert error.recoverable is False

    @settings(max_examples=100)
    @given(message=error_message_strategy)
    def test_not_found_factory(self, message):
        """not_found factory should create correct error type."""
        error = MCPError.not_found(message)
        
        assert error.error_type == MCPErrorType.NOT_FOUND
        assert error.message == message
        assert error.recoverable is False

    def test_classify_http_401_returns_auth_required(self):
        """HTTP 401 should be classified as auth_required."""
        error = classify_http_error(401)
        
        assert error.error_type == MCPErrorType.AUTH_REQUIRED
        assert error.recoverable is False

    def test_classify_http_403_returns_auth_expired(self):
        """HTTP 403 should be classified as auth_expired."""
        error = classify_http_error(403)
        
        assert error.error_type == MCPErrorType.AUTH_EXPIRED
        assert error.recoverable is False

    def test_classify_http_404_returns_not_found(self):
        """HTTP 404 should be classified as not_found."""
        error = classify_http_error(404)
        
        assert error.error_type == MCPErrorType.NOT_FOUND
        assert error.recoverable is False

    def test_classify_http_429_returns_rate_limited(self):
        """HTTP 429 should be classified as rate_limited."""
        error = classify_http_error(429)
        
        assert error.error_type == MCPErrorType.RATE_LIMITED
        assert error.recoverable is True
        assert error.retry_after is not None

    @settings(max_examples=100)
    @given(status_code=st.integers(min_value=500, max_value=599))
    def test_classify_http_5xx_returns_recoverable_api_error(self, status_code):
        """HTTP 5xx should be classified as recoverable api_error."""
        error = classify_http_error(status_code)
        
        assert error.error_type == MCPErrorType.API_ERROR
        assert error.recoverable is True

    @settings(max_examples=100)
    @given(status_code=st.integers(min_value=400, max_value=499).filter(
        lambda x: x not in (401, 403, 404, 429)
    ))
    def test_classify_http_4xx_returns_non_recoverable_api_error(self, status_code):
        """HTTP 4xx (except special cases) should be non-recoverable api_error."""
        error = classify_http_error(status_code)
        
        assert error.error_type == MCPErrorType.API_ERROR
        assert error.recoverable is False



class TestExponentialBackoff:
    """
    **Feature: platform-mcp-servers, Property 9: Exponential Backoff**
    **Validates: Requirements 6.2**
    
    For any sequence of rate-limited requests, the retry delays shall increase
    exponentially (delay_n+1 >= 2 * delay_n).
    """

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        exponential_base=st.floats(min_value=1.5, max_value=4.0),
        max_retries=st.integers(min_value=1, max_value=10),
    )
    def test_delays_increase_exponentially(
        self, initial_delay, max_delay, exponential_base, max_retries
    ):
        """Each delay should be at least exponential_base times the previous."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            max_retries=max_retries,
            jitter=False,  # Disable jitter for deterministic testing
        )
        
        delays = [config.get_delay(i) for i in range(max_retries)]
        
        # Each delay should be >= exponential_base * previous (until max_delay)
        for i in range(1, len(delays)):
            expected_min = min(delays[i - 1] * exponential_base, max_delay)
            # Allow small floating point tolerance
            assert delays[i] >= expected_min - 0.001 or delays[i] >= max_delay - 0.001

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        max_retries=st.integers(min_value=1, max_value=10),
    )
    def test_delays_never_exceed_max_delay(
        self, initial_delay, max_delay, max_retries
    ):
        """No delay should exceed max_delay (plus jitter allowance)."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            max_retries=max_retries,
            jitter=True,
        )
        
        for i in range(max_retries):
            delay = config.get_delay(i)
            # With jitter, delay can be up to 25% more than max_delay
            assert delay <= max_delay * 1.26

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        max_retries=st.integers(min_value=1, max_value=10),
    )
    def test_first_delay_equals_initial_delay_without_jitter(
        self, initial_delay, max_delay, max_retries
    ):
        """First delay (attempt 0) should equal initial_delay without jitter."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            max_retries=max_retries,
            jitter=False,
        )
        
        first_delay = config.get_delay(0)
        
        assert first_delay == initial_delay

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        exponential_base=st.floats(min_value=1.5, max_value=4.0),
        max_retries=st.integers(min_value=1, max_value=10),
    )
    def test_delays_are_positive(
        self, initial_delay, max_delay, exponential_base, max_retries
    ):
        """All delays should be positive."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            max_retries=max_retries,
        )
        
        for i in range(max_retries):
            delay = config.get_delay(i)
            assert delay > 0

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        exponential_base=st.floats(min_value=1.5, max_value=4.0),
        max_retries=st.integers(min_value=1, max_value=10),
    )
    def test_get_delays_returns_correct_count(
        self, initial_delay, max_delay, exponential_base, max_retries
    ):
        """get_delays should return max_retries delays."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            max_retries=max_retries,
        )
        
        delays = config.get_delays()
        
        assert len(delays) == max_retries

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        exponential_base=st.floats(min_value=2.0, max_value=4.0),
        attempt=st.integers(min_value=0, max_value=20),
    )
    def test_delay_formula_without_jitter(
        self, initial_delay, max_delay, exponential_base, attempt
    ):
        """Delay should follow formula: min(initial * base^attempt, max_delay)."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=False,
        )
        
        delay = config.get_delay(attempt)
        expected = min(initial_delay * (exponential_base ** attempt), max_delay)
        
        # Allow small floating point tolerance
        assert abs(delay - expected) < 0.001

    @settings(max_examples=100)
    @given(
        initial_delay=st.floats(min_value=0.1, max_value=10.0),
        max_delay=st.floats(min_value=30.0, max_value=300.0),
        max_retries=st.integers(min_value=3, max_value=10),
    )
    def test_delays_with_jitter_vary(
        self, initial_delay, max_delay, max_retries
    ):
        """Delays with jitter should vary between calls for same attempt."""
        config = RetryConfig(
            initial_delay=initial_delay,
            max_delay=max_delay,
            max_retries=max_retries,
            jitter=True,
        )
        
        # Get multiple delays for the same attempt
        delays = [config.get_delay(1) for _ in range(20)]
        
        # With jitter, we should see some variation (not all identical)
        # Note: There's a tiny chance all 20 could be identical, but very unlikely
        unique_delays = set(delays)
        # At least some variation expected
        assert len(unique_delays) > 1 or max_delay <= initial_delay * 2

    def test_default_config_values(self):
        """Default RetryConfig should have sensible defaults."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_exponential_growth_example(self):
        """Verify exponential growth with specific values."""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            max_retries=5,
            jitter=False,
        )
        
        # Expected: 1, 2, 4, 8, 16
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0
        assert config.get_delay(4) == 16.0

    def test_max_delay_caps_growth(self):
        """Verify max_delay caps exponential growth."""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            max_retries=10,
            jitter=False,
        )
        
        # After a few attempts, should hit max_delay
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0
        assert config.get_delay(4) == 10.0  # Capped at max_delay
        assert config.get_delay(5) == 10.0  # Still capped
