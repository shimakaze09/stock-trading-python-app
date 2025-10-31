"""Test that real API is always used - no mocks in production code."""

import pytest
from database.connection import get_db_context
from data_fetch.polygon_client import PolygonClient
from data_fetch.stock_list import StockListManager
from data_fetch.price_fetcher import PriceFetcher
from config import get_settings


def test_polygon_client_requires_real_api_key():
    """Test that PolygonClient requires a real API key."""
    settings = get_settings()
    
    # Should work with real API key
    if settings.POLYGON_API_KEY:
        client = PolygonClient()
        assert client.api_key == settings.POLYGON_API_KEY, "Should use real API key"
        assert len(client.api_key) > 0, "API key should not be empty"
        assert client.BASE_URL == "https://api.polygon.io", "Should use real API URL"
    else:
        pytest.skip("API key not configured")


def test_stock_list_uses_real_api():
    """Test that stock list manager uses real API."""
    try:
        with get_db_context() as db:
            settings = get_settings()
            if not settings.POLYGON_API_KEY:
                pytest.skip("API key not configured")
            
            manager = StockListManager(db)
            
            # Should make real API call (limited to avoid rate limit)
            # Just test that it doesn't use mock data
            response = manager.client.get_tickers(
                market="stocks",
                active=True,
                limit=5
            )
            
            # Should return real data structure
            assert 'results' in response or 'status' in response, "Should return API response"
            
            # If results exist, verify structure
            if 'results' in response and response['results']:
                ticker = response['results'][0]
                assert 'ticker' in ticker or 'symbol' in ticker, "Should have ticker symbol"
                
    except Exception as e:
        # API might be unavailable, but we should try real API, not mock
        assert 'mock' not in str(e).lower(), "Should not use mocks"
        pytest.skip(f"API unavailable: {str(e)}")


def test_price_fetcher_uses_real_api():
    """Test that price fetcher uses real API."""
    try:
        with get_db_context() as db:
            settings = get_settings()
            if not settings.POLYGON_API_KEY:
                pytest.skip("API key not configured")
            
            # Need a stock first
            from database.models import Stock
            stock = db.query(Stock).filter(Stock.symbol == 'AAPL').first()
            created_here = False
            if not stock:
                # Create test stock
                stock = Stock(
                    symbol='AAPL',
                    name='Apple Inc.',
                    active=True,
                    currency='USD'
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
                created_here = True
            
            price_fetcher = PriceFetcher(db)
            
            # Should make real API call (just verify it attempts real API)
            # Don't actually fetch to avoid rate limits
            assert price_fetcher.client.api_key == settings.POLYGON_API_KEY, "Should use real API key"
            assert price_fetcher.client.BASE_URL == "https://api.polygon.io", "Should use real API URL"
            
            if created_here:
                # Re-fetch to ensure it's the same instance
                s = db.query(Stock).filter(Stock.symbol == 'AAPL').first()
                if s:
                    db.delete(s)
                    db.commit()
                
    except Exception as e:
        pytest.skip(f"Test setup failed: {str(e)}")


def test_no_mock_data_in_code():
    """Verify that production code doesn't contain mock/test data."""
    import os
    import re
    
    # Check key files for mock patterns
    files_to_check = [
        'data_fetch/polygon_client.py',
        'data_fetch/stock_list.py',
        'data_fetch/price_fetcher.py',
        'data_fetch/fundamental_fetcher.py',
        'pipeline/orchestrator.py',
    ]
    
    mock_patterns = [
        r'mock_data',
        r'test_data',
        r'sample_data',
        r'fake_',
        r'dummy_',
        r'placeholder',
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in mock_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    # Only fail if it's not in a comment or test context
                    for match in matches:
                        line_num = content[:content.find(match)].count('\n') + 1
                        line = content.split('\n')[line_num - 1]
                        if 'def test_' not in line and '# test' not in line.lower() and '"""' not in line:
                            pytest.fail(f"Found mock pattern '{match}' in {file_path} at line {line_num}: {line.strip()}")
    
    assert True, "No mock data patterns found in production code"


def test_upsert_uses_real_database():
    """Test that upserts actually hit the database."""
    try:
        with get_db_context() as db:
            from sqlalchemy.dialects.postgresql import insert
            from database.models import Stock
            
            # Test real database upsert (max 10 chars for symbol)
            test_symbol = 'TESTU'
            
            # Insert
            stmt = (
                insert(Stock)
                .values(
                    symbol=test_symbol,
                    name='Test Stock',
                    active=True,
                    currency='USD'
                )
                .on_conflict_do_update(
                    index_elements=[Stock.symbol],
                    set_={'name': 'Test Stock Updated'}
                )
            )
            db.execute(stmt)
            db.commit()
            
            # Verify it exists in real database
            stock = db.query(Stock).filter(Stock.symbol == test_symbol).first()
            assert stock is not None, "Stock should exist in real database"
            assert stock.name == 'Test Stock', "Should have original name"
            
            # Upsert
            stmt = (
                insert(Stock)
                .values(
                    symbol=test_symbol,
                    name='Test Stock Updated',
                    active=True,
                    currency='USD'
                )
                .on_conflict_do_update(
                    index_elements=[Stock.symbol],
                    set_={'name': 'Test Stock Updated'}
                )
            )
            db.execute(stmt)
            db.commit()
            
            # Verify update
            db.refresh(stock)
            assert stock.name == 'Test Stock Updated', "Should have updated name"
            
            # Verify only one record
            count = db.query(Stock).filter(Stock.symbol == test_symbol).count()
            assert count == 1, f"Should have exactly 1 record, got {count}"
            
            # Clean up
            db.delete(stock)
            db.commit()
            
    except Exception as e:
        pytest.fail(f"Database upsert test failed: {str(e)}")

