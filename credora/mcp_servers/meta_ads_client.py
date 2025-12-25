"""
Meta Ads API Client.

HTTP client for Meta Marketing API v21.0.

Requirements: 3.6
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

import httpx

from credora.mcp_servers.errors import MCPError, MCPErrorType, classify_http_error
from credora.mcp_servers.logging import get_mcp_logger
from credora.mcp_servers.models.meta_ads import (
    AdAccount,
    AdSet,
    AudienceInsights,
    Campaign,
)


# Meta Marketing API configuration
META_API_VERSION = "v21.0"
META_API_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"


class MetaAdsClient:
    """
    HTTP client for Meta Marketing API.
    
    Handles authentication, request building, and response parsing
    for Meta Ads API calls.
    
    Requirements: 3.6
    """
    
    def __init__(
        self,
        access_token: str,
        timeout: float = 30.0,
    ):
        """Initialize the Meta Ads client.
        
        Args:
            access_token: OAuth access token for Meta API
            timeout: Request timeout in seconds
        """
        if not access_token:
            raise ValueError("access_token is required")
        
        self._access_token = access_token
        self._timeout = timeout
        self._logger = get_mcp_logger()
        self._base_url = META_API_BASE_URL
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication.
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
    
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
        """Make an HTTP request to the Meta API.
        
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
        
        # Add access token to params if not using header auth
        params = params or {}
        params["access_token"] = self._access_token
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
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
                        message=f"Meta API error: {response.status_code}",
                        platform="meta",
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
                    platform="meta",
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
                    platform="meta",
                    request_method=method,
                    request_url=url,
                )
                raise MCPError.network_error(
                    message=f"Network error: {str(e)}",
                    endpoint=endpoint,
                )

    async def list_ad_accounts(self) -> List[AdAccount]:
        """List all ad accounts accessible to the user.
        
        Returns:
            List of AdAccount objects
            
        Requirements: 3.1
        """
        endpoint = "/me/adaccounts"
        params = {
            "fields": "id,name,currency,timezone_name",
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        
        accounts = []
        for item in response.get("data", []):
            accounts.append(AdAccount.from_api_response(item))
        
        return accounts
    
    async def get_campaigns(
        self,
        account_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Campaign]:
        """Get campaigns for an ad account with metrics.
        
        Args:
            account_id: Ad account ID (with or without 'act_' prefix)
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of Campaign objects with metrics
            
        Requirements: 3.2, 3.5
        """
        # Ensure account_id has act_ prefix
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        endpoint = f"/{account_id}/campaigns"
        params = {
            "fields": "id,name,status,objective",
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        
        campaigns = []
        for item in response.get("data", []):
            # Fetch insights for each campaign
            insights = await self._get_campaign_insights(
                item["id"], date_from, date_to
            )
            campaigns.append(Campaign.from_api_response(item, insights))
        
        return campaigns
    
    async def _get_campaign_insights(
        self,
        campaign_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get insights for a campaign.
        
        Args:
            campaign_id: Campaign ID
            date_from: Start date
            date_to: End date
            
        Returns:
            Insights data dictionary
        """
        endpoint = f"/{campaign_id}/insights"
        params = {
            "fields": "spend,impressions,clicks,actions",
        }
        
        # Add date range if provided
        if date_from and date_to:
            params["time_range"] = f'{{"since":"{date_from}","until":"{date_to}"}}'
        
        try:
            response = await self._make_request("GET", endpoint, params=params)
            data = response.get("data", [])
            return data[0] if data else {}
        except MCPError:
            # Return empty insights if fetch fails
            return {}
    
    async def get_adsets(
        self,
        account_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[AdSet]:
        """Get ad sets for an ad account with metrics.
        
        Args:
            account_id: Ad account ID (with or without 'act_' prefix)
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            
        Returns:
            List of AdSet objects with metrics
            
        Requirements: 3.3, 3.5
        """
        # Ensure account_id has act_ prefix
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        endpoint = f"/{account_id}/adsets"
        params = {
            "fields": "id,name,campaign_id,status,daily_budget,lifetime_budget",
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        
        adsets = []
        for item in response.get("data", []):
            # Fetch insights for each ad set
            insights = await self._get_adset_insights(
                item["id"], date_from, date_to
            )
            adsets.append(AdSet.from_api_response(item, insights))
        
        return adsets
    
    async def _get_adset_insights(
        self,
        adset_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get insights for an ad set.
        
        Args:
            adset_id: Ad set ID
            date_from: Start date
            date_to: End date
            
        Returns:
            Insights data dictionary
        """
        endpoint = f"/{adset_id}/insights"
        params = {
            "fields": "spend,impressions,clicks,actions",
        }
        
        # Add date range if provided
        if date_from and date_to:
            params["time_range"] = f'{{"since":"{date_from}","until":"{date_to}"}}'
        
        try:
            response = await self._make_request("GET", endpoint, params=params)
            data = response.get("data", [])
            return data[0] if data else {}
        except MCPError:
            # Return empty insights if fetch fails
            return {}
    
    async def get_audience_insights(
        self,
        account_id: str,
    ) -> AudienceInsights:
        """Get audience demographic insights for an ad account.
        
        Args:
            account_id: Ad account ID (with or without 'act_' prefix)
            
        Returns:
            AudienceInsights object
            
        Requirements: 3.4
        """
        # Ensure account_id has act_ prefix
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        # Fetch delivery insights with demographic breakdowns
        endpoint = f"/{account_id}/insights"
        params = {
            "fields": "impressions",
            "breakdowns": "age,gender,country",
            "date_preset": "last_30d",
        }
        
        try:
            response = await self._make_request("GET", endpoint, params=params)
            data = response.get("data", [])
            
            # Process breakdown data
            age_data = []
            gender_data = []
            country_data = []
            
            total_impressions = sum(int(item.get("impressions", 0)) for item in data)
            
            for item in data:
                impressions = int(item.get("impressions", 0))
                percentage = (impressions / total_impressions * 100) if total_impressions > 0 else 0
                
                if "age" in item:
                    age_data.append({
                        "age": item["age"],
                        "percentage": percentage,
                    })
                if "gender" in item:
                    gender_data.append({
                        "gender": item["gender"],
                        "percentage": percentage,
                    })
                if "country" in item:
                    country_data.append({
                        "country": item["country"],
                        "percentage": percentage,
                    })
            
            insights_data = {
                "age": age_data,
                "gender": gender_data,
                "country": country_data,
                "interests": [],  # Would require separate targeting API call
            }
            
            return AudienceInsights.from_api_response(account_id, insights_data)
            
        except MCPError:
            # Return empty insights if fetch fails
            return AudienceInsights(account_id=account_id)
    
    def get_api_base_url(self) -> str:
        """Get the base URL for API requests.
        
        Returns:
            Base URL string (always HTTPS)
            
        Requirements: 7.2
        """
        return self._base_url
