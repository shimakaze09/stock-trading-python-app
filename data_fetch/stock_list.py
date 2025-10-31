"""Stock list manager to fetch and maintain all US-listed stocks."""

from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_

from database.models import Stock
from .polygon_client import PolygonClient
from config import get_settings


class StockListManager:
    """Manages the list of US-listed stocks."""
    
    def __init__(self, db_session: Session, client: Optional[PolygonClient] = None):
        """Initialize stock list manager."""
        self.db = db_session
        self.client = client or PolygonClient()
        self.settings = get_settings()
    
    def fetch_all_stocks(self) -> int:
        """Fetch all US-listed stocks from Polygon.io and update database.
        
        Returns:
            Number of stocks processed
        """
        all_stocks = []
        cursor = None
        
        print("Fetching all US-listed stocks from Polygon.io...")
        
        while True:
            try:
                response = self.client.get_tickers(
                    market="stocks",
                    active=True,
                    limit=1000,
                    cursor=cursor
                )
                
                if 'results' in response:
                    all_stocks.extend(response['results'])
                    print(f"Fetched {len(response['results'])} stocks (total: {len(all_stocks)})")
                
                # Check for next page
                if 'next_url' in response and response['next_url']:
                    # Extract cursor from next_url if needed
                    cursor = response.get('next_cursor')
                    if not cursor:
                        break
                else:
                    break
                    
            except Exception as e:
                print(f"Error fetching stocks: {str(e)}")
                break
        
        print(f"Total stocks fetched: {len(all_stocks)}")
        
        # Process and save stocks
        processed = 0
        for stock_data in all_stocks:
            try:
                self._upsert_stock(stock_data)
                processed += 1
                if processed % 100 == 0:
                    print(f"Processed {processed} stocks...")
            except Exception as e:
                print(f"Error processing stock {stock_data.get('ticker')}: {str(e)}")
        
        self.db.commit()
        print(f"Successfully processed {processed} stocks.")
        
        return processed
    
    def _upsert_stock(self, stock_data: Dict):
        """Insert or update stock in database."""
        symbol = stock_data.get('ticker', '').upper()
        
        if not symbol:
            return
        
        # Prepare upsert payload
        payload = {
            'symbol': symbol,
            'name': stock_data.get('name', symbol),
            'market': stock_data.get('market'),
            'locale': stock_data.get('locale', 'us'),
            'primary_exchange': stock_data.get('primary_exchange'),
            'type': stock_data.get('type'),
            'active': stock_data.get('active', True),
            'currency': stock_data.get('currency_name', 'USD'),
            'description': stock_data.get('description') or None,
        }

        if stock_data.get('list_date'):
            try:
                payload['list_date'] = datetime.strptime(stock_data['list_date'], '%Y-%m-%d').date()
            except Exception:
                pass

        stmt = (
            insert(Stock)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=[Stock.symbol],
                set_={
                    'name': payload['name'],
                    'market': payload['market'],
                    'locale': payload['locale'],
                    'primary_exchange': payload['primary_exchange'],
                    'type': payload['type'],
                    'active': payload['active'],
                    'currency': payload['currency'],
                    'description': payload['description'],
                    'list_date': payload.get('list_date')
                }
            )
        )

        self.db.execute(stmt)
    
    def get_active_stocks(self, limit: Optional[int] = None) -> List[Stock]:
        """Get all active stocks from database.
        
        Args:
            limit: Maximum number of stocks to return
            
        Returns:
            List of Stock objects
        """
        query = self.db.query(Stock).filter(Stock.active == True)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[Stock]:
        """Get stock by symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Stock object or None
        """
        return self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    
    def update_stock_details(self, symbol: str) -> bool:
        """Update stock details from Polygon.io.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.get_ticker_details(symbol)
            
            if 'results' in response:
                ticker_data = response['results']
                self._upsert_stock(ticker_data)
                self.db.commit()
                return True
        except Exception as e:
            print(f"Error updating stock details for {symbol}: {str(e)}")
        
        return False
    
    def refresh_stock_list(self) -> int:
        """Refresh the entire stock list from Polygon.io.
        
        Returns:
            Number of stocks processed
        """
        return self.fetch_all_stocks()

