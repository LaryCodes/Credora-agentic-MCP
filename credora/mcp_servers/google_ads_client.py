"""
Google Ads API Client.

HTTP client for Google Ads API v18.

Requirements: 4.6
"""

from typing import Any, Dict, List, Optional

import httpx

from credora.mcp_servers.errors import MCPError, MCPErrorType, classify_http_error
from credora.mcp_servers.logging import get_mcp_logger
from credora.mcp_servers.models.google_ads import (
    AdGroup,
    Campaign,
    Customer,
    Keyword,
)


# Google Ads API configuration
GOOGLE_ADS_API_VERSION = "v18"
GOOGLE_ADS_API_BASE_URL = f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}"


class GoogleAdsClient:
    """
    HTTP client for Google Ads API.
    
    Handles authentication, request building, and response parsing
    for Google Ads API calls.
    
    Requirements: 4.6
    """
    
    def __init__(
        self,
        access_token: str,
        developer_token: str,
        login_customer_id: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize the Google Ads client.
        
        Args:
            access_token: OAuth access token for Google API
            developer_token: Google Ads API developer token
            login_customer_id: Optional manager account ID for MCC access
            timeout: Request timeout in seconds
        """
        if not access_token:
            raise ValueError("access_token is required")
        if not developer_token:
            raise ValueError("developer_token is required")
        
        self._access_token = access_token
        self._developer_token = developer_token
        self._login_customer_id = login_customer_id
        self._timeout = timeout
        self._logger = get_mcp_logger()
        self._base_url = GOOGLE_ADS_API_BASE_URL
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication.
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "developer-token": self._developer_token,
            "Content-Type": "application/json",
        }
        
        if self._login_customer_id:
            headers["login-customer-id"] = self._login_customer_id
        
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """Build full API URL for an endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL string (always HTTPS)
            
        Requirements: 7.2 (HTTPS enforcement)
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        
        url = f"{self._base_url}{endpoint}"
        
        # Verify HTTPS (should always be true given our base URL)
        if not url.startswith("https://"):
            raise ValueError("API URLs must use HTTPS")
        
        return url

    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Google Ads API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            Parsed JSON response
            
        Raises:
            MCPError: If request fails
        """
        url = self._build_url(endpoint)
        headers = self._get_headers()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data if data else None,
                )
                
                # Check for errors
                if response.status_code >= 400:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass
                    
                    # Log the error
                    self._logger.log_api_error(
                        error_type=MCPErrorType.API_ERROR.value,
                        message=f"Google Ads API error: {response.status_code}",
                        platform="google",
                        request_method=method,
                        request_url=url,
                        status_code=response.status_code,
                        details=error_data,
                    )
                    
                    # Classify and raise appropriate error
                    raise classify_http_error(response.status_code, response.text)
                
                return response.json()
                
            except httpx.TimeoutException as e:
                self._logger.log_api_error(
                    error_type=MCPErrorType.NETWORK_ERROR.value,
                    message=f"Request timeout: {str(e)}",
                    platform="google",
                    request_method=method,
                    request_url=url,
                )
                raise MCPError.network_error(
                    message=f"Request timeout: {str(e)}",
                    endpoint=endpoint,
                )
            except httpx.RequestError as e:
                self._logger.log_api_error(
                    error_type=MCPErrorType.NETWORK_ERROR.value,
                    message=f"Network error: {str(e)}",
                    platform="google",
                    request_method=method,
                    request_url=url,
                )
                raise MCPError.network_error(
                    message=f"Network error: {str(e)}",
                    endpoint=endpoint,
                )

    async def _search(
        self,
        customer_id: str,
        query: str,
    ) -> List[Dict[str, Any]]:
        """Execute a Google Ads Query Language (GAQL) search.
        
        Args:
            customer_id: Customer ID to query
            query: GAQL query string
            
        Returns:
            List of result rows
        """
        # Remove dashes from customer ID if present
        customer_id = customer_id.replace("-", "")
        
        endpoint = f"/customers/{customer_id}/googleAds:search"
        data = {"query": query}
        
        response = await self._make_request("POST", endpoint, data=data)
        return response.get("results", [])

    async def list_customers(self) -> List[Customer]:
        """List all accessible customer accounts.
        
        Returns:
            List of Customer objects
            
        Requirements: 4.1
        """
        # Use the listAccessibleCustomers endpoint
        endpoint = "/customers:listAccessibleCustomers"
        
        response = await self._make_request("GET", endpoint)
        
        customers = []
        resource_names = response.get("resourceNames", [])
        
        for resource_name in resource_names:
            # Extract customer ID from resource name (format: customers/1234567890)
            customer_id = resource_name.split("/")[-1]
            
            # Fetch customer details
            try:
                customer_data = await self._get_customer_details(customer_id)
                customers.append(Customer.from_api_response(customer_data))
            except MCPError:
                # Skip customers we can't access
                continue
        
        return customers
    
    async def _get_customer_details(self, customer_id: str) -> Dict[str, Any]:
        """Get details for a specific customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer data dictionary
        """
        query = """
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone
            FROM customer
            LIMIT 1
        """
        
        results = await self._search(customer_id, query)
        if results:
            return results[0]
        
        return {"customer": {"id": customer_id, "descriptiveName": "", "currencyCode": "USD", "timeZone": ""}}


    async def get_campaigns(
        self,
        customer_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Campaign]:
        """Get campaigns for a customer with metrics.
        
        Args:
            customer_id: Customer ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of Campaign objects with metrics
            
        Requirements: 4.2, 4.5
        """
        # Build date filter
        date_filter = ""
        if date_from and date_to:
            date_filter = f"AND segments.date BETWEEN '{date_from}' AND '{date_to}'"
        elif date_from:
            date_filter = f"AND segments.date >= '{date_from}'"
        elif date_to:
            date_filter = f"AND segments.date <= '{date_to}'"
        
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            {date_filter}
        """
        
        results = await self._search(customer_id, query)
        
        campaigns = []
        for row in results:
            campaign_data = row.get("campaign", {})
            metrics_data = row.get("metrics", {})
            campaigns.append(Campaign.from_api_response(
                {"campaign": campaign_data},
                metrics_data
            ))
        
        return campaigns

    async def get_keywords(
        self,
        customer_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Keyword]:
        """Get keywords for a customer with metrics.
        
        Args:
            customer_id: Customer ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of Keyword objects with metrics
            
        Requirements: 4.3, 4.5
        """
        # Build date filter
        date_filter = ""
        if date_from and date_to:
            date_filter = f"AND segments.date BETWEEN '{date_from}' AND '{date_to}'"
        elif date_from:
            date_filter = f"AND segments.date >= '{date_from}'"
        elif date_to:
            date_filter = f"AND segments.date <= '{date_to}'"
        
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.quality_info.quality_score,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions
            FROM keyword_view
            WHERE ad_group_criterion.status != 'REMOVED'
            {date_filter}
        """
        
        results = await self._search(customer_id, query)
        
        keywords = []
        for row in results:
            criterion_data = row.get("adGroupCriterion", {})
            metrics_data = row.get("metrics", {})
            keywords.append(Keyword.from_api_response(
                {"adGroupCriterion": criterion_data},
                metrics_data
            ))
        
        return keywords

    async def get_ad_groups(
        self,
        customer_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[AdGroup]:
        """Get ad groups for a customer with metrics.
        
        Args:
            customer_id: Customer ID
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of AdGroup objects with metrics
            
        Requirements: 4.4, 4.5
        """
        # Build date filter
        date_filter = ""
        if date_from and date_to:
            date_filter = f"AND segments.date BETWEEN '{date_from}' AND '{date_to}'"
        elif date_from:
            date_filter = f"AND segments.date >= '{date_from}'"
        elif date_to:
            date_filter = f"AND segments.date <= '{date_to}'"
        
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.campaign,
                ad_group.status,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions
            FROM ad_group
            WHERE ad_group.status != 'REMOVED'
            {date_filter}
        """
        
        results = await self._search(customer_id, query)
        
        ad_groups = []
        for row in results:
            ad_group_data = row.get("adGroup", {})
            metrics_data = row.get("metrics", {})
            ad_groups.append(AdGroup.from_api_response(
                {"adGroup": ad_group_data},
                metrics_data
            ))
        
        return ad_groups
    
    def get_api_base_url(self) -> str:
        """Get the base URL for API requests.
        
        Returns:
            Base URL string (always HTTPS)
            
        Requirements: 7.2
        """
        return self._base_url
