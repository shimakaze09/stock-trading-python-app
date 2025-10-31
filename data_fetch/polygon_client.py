"""Polygon.io API client wrapper with rate limiting."""

import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
from config import get_settings


class PolygonClient:
    """Polygon.io API client with rate limiting."""
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Polygon.io client."""
        self.settings = get_settings()
        self.api_key = api_key or self.settings.POLYGON_API_KEY
        
        if not self.api_key:
            raise ValueError("Polygon.io API key is required")
        
        self.call_times = deque()
        self.max_calls_per_minute = self.settings.MAX_API_CALLS_PER_MINUTE
        self.call_interval = self.settings.API_CALL_INTERVAL_SECONDS
        
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Remove calls older than 1 minute
        while self.call_times and now - self.call_times[0] > 60:
            self.call_times.popleft()
        
        # If we're at the limit, wait
        if len(self.call_times) >= self.max_calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)
                self._wait_for_rate_limit()
                return
        
        # Record this call
        self.call_times.append(now)
        
        # Always wait the minimum interval between calls
        if len(self.call_times) > 1:
            time_since_last = now - self.call_times[-2]
            if time_since_last < self.call_interval:
                time.sleep(self.call_interval - time_since_last)
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with rate limiting and error handling."""
        self._wait_for_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def get_tickers(
        self,
        market: str = "stocks",
        active: bool = True,
        limit: int = 1000,
        cursor: Optional[str] = None
    ) -> Dict:
        """Get list of tickers from Polygon.io.
        
        Args:
            market: Market type (default: 'stocks')
            active: Only active tickers (default: True)
            limit: Results per page (default: 1000, max: 1000)
            cursor: Pagination cursor
            
        Returns:
            Dictionary with tickers and pagination info
        """
        params = {
            'market': market,
            'active': str(active).lower(),
            'limit': min(limit, 1000)
        }
        
        if cursor:
            params['cursor'] = cursor
        
        return self._make_request('/v3/reference/tickers', params)
    
    def get_ticker_details(self, symbol: str) -> Dict:
        """Get detailed information about a ticker.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with ticker details
        """
        return self._make_request(f'/v3/reference/tickers/{symbol.upper()}')
    
    def get_aggregates(
        self,
        symbol: str,
        multiplier: int = 1,
        timespan: str = "day",
        from_date: str = None,
        to_date: str = None,
        limit: int = 5000
    ) -> Dict:
        """Get aggregated bars (OHLCV) for a ticker.
        
        Args:
            symbol: Stock ticker symbol
            multiplier: Size of the timespan multiplier
            timespan: Size of the time window (minute, hour, day, week, month, quarter, year)
            from_date: Start date (YYYY-MM-DD or Unix timestamp in milliseconds)
            to_date: End date (YYYY-MM-DD or Unix timestamp in milliseconds)
            limit: Number of results (max: 5000)
            
        Returns:
            Dictionary with aggregated bars
        """
        if not from_date:
            # Default to 2 years ago
            from_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'ticker': symbol.upper(),
            'multiplier': multiplier,
            'timespan': timespan,
            'from': from_date,
            'to': to_date,
            'limit': min(limit, 5000),
            'adjusted': 'true',
            'sort': 'asc'
        }
        
        return self._make_request(f'/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}', params)
    
    def get_ticker_financials(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> Dict:
        """Get financials data for a ticker (free tier limited).
        
        Args:
            symbol: Stock ticker symbol
            period: Period type (annual or quarterly)
            limit: Number of results (default: 10)
            
        Returns:
            Dictionary with financials data
        """
        params = {
            'ticker': symbol.upper(),
            'period': period,
            'limit': limit
        }
        
        return self._make_request('/vX/reference/financials', params)
    
    def get_ticker_news(
        self,
        symbol: str,
        limit: int = 10
    ) -> Dict:
        """Get news articles for a ticker.
        
        Args:
            symbol: Stock ticker symbol
            limit: Number of results (default: 10)
            
        Returns:
            Dictionary with news articles
        """
        params = {
            'ticker': symbol.upper(),
            'limit': limit
        }
        
        return self._make_request('/v2/reference/news', params)

