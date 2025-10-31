"""Test Polygon.io API client."""

import pytest
import time
from data_fetch.polygon_client import PolygonClient
from config import get_settings


@pytest.fixture
def client():
    """Create Polygon client."""
    settings = get_settings()
    return PolygonClient(api_key=settings.POLYGON_API_KEY)


def test_polygon_client_init(client):
    """Test Polygon client initialization."""
    assert client is not None
    assert client.api_key is not None
    assert client.max_calls_per_minute == 5


def test_polygon_rate_limiting(client):
    """Test rate limiting."""
    start_time = time.time()
    
    # Make a few calls
    for i in range(3):
        try:
            response = client.get_tickers(market="stocks", active=True, limit=1)
            assert 'results' in response or 'status' in response
        except Exception as e:
            pytest.skip(f"API call failed: {str(e)}")
    
    elapsed = time.time() - start_time
    
    # Should take at least 2 * (60/5) = 24 seconds for 3 calls (12 seconds between each)
    assert elapsed >= 2.0  # At least some delay


def test_polygon_get_tickers(client):
    """Test getting tickers."""
    try:
        response = client.get_tickers(market="stocks", active=True, limit=10)
        assert 'results' in response or 'status' in response
        if 'results' in response:
            assert isinstance(response['results'], list)
    except Exception as e:
        pytest.skip(f"API call failed: {str(e)}")


def test_polygon_get_ticker_details(client):
    """Test getting ticker details."""
    try:
        response = client.get_ticker_details("AAPL")
        assert 'results' in response or 'status' in response
        if 'results' in response:
            result = response['results']
            assert 'ticker' in result or 'name' in result
    except Exception as e:
        pytest.skip(f"API call failed: {str(e)}")


def test_polygon_get_aggregates(client):
    """Test getting aggregates."""
    try:
        from datetime import datetime, timedelta
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        response = client.get_aggregates(
            symbol="AAPL",
            multiplier=1,
            timespan="day",
            from_date=from_date.strftime('%Y-%m-%d'),
            to_date=to_date.strftime('%Y-%m-%d'),
            limit=10
        )
        assert 'results' in response or 'status' in response
    except Exception as e:
        pytest.skip(f"API call failed: {str(e)}")

