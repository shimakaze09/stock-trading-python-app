"""Price data fetcher with batching, rate limiting, and incremental updates."""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_, func

from database.models import Stock, StockPrice
from .polygon_client import PolygonClient
from config import get_settings


class PriceFetcher:
    """Fetches and stores stock price data."""
    
    def __init__(self, db_session: Session, client: Optional[PolygonClient] = None):
        """Initialize price fetcher."""
        self.db = db_session
        self.client = client or PolygonClient()
        self.settings = get_settings()
    
    def fetch_stock_prices(
        self,
        symbol: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        incremental: bool = True
    ) -> int:
        """Fetch price data for a stock.
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date (default: 2 years ago or last update)
            to_date: End date (default: today)
            incremental: Only fetch missing data (default: True)
            
        Returns:
            Number of price records added/updated
        """
        # Get stock from database
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            print(f"Stock {symbol} not found in database. Please add it first.")
            return 0
        
        # Determine date range
        if incremental:
            # Get latest price in database
            latest_price = (
                self.db.query(StockPrice)
                .filter(StockPrice.stock_id == stock.id)
                .order_by(StockPrice.timestamp.desc())
                .first()
            )
            
            if latest_price:
                from_date = latest_price.timestamp + timedelta(days=1)
            else:
                from_date = datetime.now() - timedelta(days=730)  # 2 years
        else:
            if not from_date:
                from_date = datetime.now() - timedelta(days=730)  # 2 years
        
        if not to_date:
            to_date = datetime.now()
        
        # Skip if from_date is after to_date
        if from_date >= to_date:
            print(f"Stock {symbol} is up to date.")
            return 0
        
        try:
            # Fetch from Polygon.io
            response = self.client.get_aggregates(
                symbol=symbol,
                multiplier=1,
                timespan="day",
                from_date=from_date.strftime('%Y-%m-%d'),
                to_date=to_date.strftime('%Y-%m-%d'),
                limit=5000
            )
            
            if 'results' not in response or not response['results']:
                print(f"No price data returned for {symbol}")
                return 0
            
            # Process and upsert prices
            count = 0
            for bar in response['results']:
                try:
                    timestamp = datetime.fromtimestamp(bar['t'] / 1000)
                    payload = {
                        'stock_id': stock.id,
                        'timestamp': timestamp,
                        'open': float(bar['o']),
                        'high': float(bar['h']),
                        'low': float(bar['l']),
                        'close': float(bar['c']),
                        'volume': int(bar['v']),
                        'vwap': float(bar.get('vw', 0) or 0),
                        'transactions': int(bar.get('n', 0) or 0),
                    }

                    stmt = (
                        insert(StockPrice)
                        .values(**payload)
                        .on_conflict_do_update(
                            index_elements=[StockPrice.stock_id, StockPrice.timestamp],
                            set_={
                                'open': payload['open'],
                                'high': payload['high'],
                                'low': payload['low'],
                                'close': payload['close'],
                                'volume': payload['volume'],
                                'vwap': payload['vwap'],
                                'transactions': payload['transactions'],
                            }
                        )
                    )
                    self.db.execute(stmt)
                    count += 1
                except Exception as e:
                    print(f"Error processing price bar for {symbol}: {str(e)}")
                    continue
            
            self.db.commit()
            print(f"Fetched {count} new price records for {symbol}")
            return count
            
        except Exception as e:
            print(f"Error fetching prices for {symbol}: {str(e)}")
            self.db.rollback()
            return 0
    
    def fetch_batch(
        self,
        symbols: List[str],
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        incremental: bool = True
    ) -> Dict[str, int]:
        """Fetch prices for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            from_date: Start date
            to_date: End date
            incremental: Only fetch missing data
            
        Returns:
            Dictionary mapping symbol to number of records fetched
        """
        results = {}
        
        for symbol in symbols:
            try:
                count = self.fetch_stock_prices(
                    symbol=symbol,
                    from_date=from_date,
                    to_date=to_date,
                    incremental=incremental
                )
                results[symbol] = count
            except Exception as e:
                print(f"Error fetching prices for {symbol}: {str(e)}")
                results[symbol] = 0
        
        return results
    
    def get_latest_price(self, symbol: str) -> Optional[StockPrice]:
        """Get latest price for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest StockPrice object or None
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return None
        
        return (
            self.db.query(StockPrice)
            .filter(StockPrice.stock_id == stock.id)
            .order_by(StockPrice.timestamp.desc())
            .first()
        )
    
    def get_price_history(
        self,
        symbol: str,
        days: int = 365
    ) -> List[StockPrice]:
        """Get price history for a stock.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days to retrieve
            
        Returns:
            List of StockPrice objects
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return (
            self.db.query(StockPrice)
            .filter(
                and_(
                    StockPrice.stock_id == stock.id,
                    StockPrice.timestamp >= cutoff_date
                )
            )
            .order_by(StockPrice.timestamp.asc())
            .all()
        )

