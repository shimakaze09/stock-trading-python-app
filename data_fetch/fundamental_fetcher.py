"""Fundamental data fetcher using Polygon.io free tier capabilities."""

from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from database.models import Stock, FundamentalData
from .polygon_client import PolygonClient
from config import get_settings


class FundamentalFetcher:
    """Fetches and stores fundamental data."""
    
    def __init__(self, db_session: Session, client: Optional[PolygonClient] = None):
        """Initialize fundamental fetcher."""
        self.db = db_session
        self.client = client or PolygonClient()
        self.settings = get_settings()
    
    def fetch_fundamental_data(self, symbol: str, period: str = "annual") -> bool:
        """Fetch fundamental data for a stock.
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarterly'
            
        Returns:
            True if successful, False otherwise
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            print(f"Stock {symbol} not found in database.")
            return False
        
        try:
            # Fetch financials from Polygon.io
            response = self.client.get_ticker_financials(
                symbol=symbol,
                period=period,
                limit=10
            )
            
            if 'results' not in response or not response['results']:
                print(f"No fundamental data returned for {symbol}")
                return False
            
            # Process and store financials
            for financial in response['results']:
                try:
                    self._process_financial_data(stock.id, financial, period)
                except Exception as e:
                    print(f"Error processing financial data for {symbol}: {str(e)}")
                    continue
            
            self.db.commit()
            print(f"Fetched fundamental data for {symbol}")
            return True
            
        except Exception as e:
            print(f"Error fetching fundamental data for {symbol}: {str(e)}")
            self.db.rollback()
            return False
    
    def _process_financial_data(self, stock_id: int, financial: Dict, period: str):
        """Process and store financial data."""
        fiscal_year = financial.get('fiscal_year')
        fiscal_quarter = financial.get('fiscal_period') if period == "quarterly" else None
        
        if not fiscal_year:
            return
        
        # Extract financial metrics and build payload
        financials = financial.get('financials', {})
        payload = {
            'stock_id': stock_id,
            'fiscal_year': fiscal_year,
            'fiscal_quarter': fiscal_quarter,
            'market_cap': None,
            'pe_ratio': None,
            'pb_ratio': None,
            'ev_ebitda': None,
            'current_ratio': None,
            'debt_to_equity': None,
            'quick_ratio': None,
            'revenue_growth': None,
            'earnings_growth': None,
            'roe': None,
            'roa': None,
            'profit_margin': None,
            'revenue': None,
            'earnings': None,
            'assets': None,
            'liabilities': None,
            'equity': None,
            'cash': None,
            'debt': None,
            'report_date': None,
            'updated_at': datetime.utcnow()
        }
        
        if financials:
            income_statement = financials.get('income_statement', {})
            balance_sheet = financials.get('balance_sheet', {})
            
            # Valuation metrics (may be limited in free tier)
            valuations = financial.get('valuations', {})
            if valuations:
                payload['market_cap'] = valuations.get('market_capitalization')
                payload['pe_ratio'] = valuations.get('price_to_earnings_ratio')
                payload['pb_ratio'] = valuations.get('price_to_book_ratio')
                payload['ev_ebitda'] = valuations.get('enterprise_value_to_ebitda')
            
            # Revenue and earnings
            if income_statement:
                payload['revenue'] = income_statement.get('revenues')
                payload['earnings'] = income_statement.get('net_income_loss')
                if payload['revenue'] and payload['earnings']:
                    payload['profit_margin'] = (
                        float(payload['earnings']) / 
                        float(payload['revenue']) * 100
                    )
            
            # Balance sheet items
            if balance_sheet:
                payload['assets'] = balance_sheet.get('assets')
                payload['liabilities'] = balance_sheet.get('liabilities')
                payload['equity'] = balance_sheet.get('equity')
                payload['cash'] = balance_sheet.get('cash_and_cash_equivalents_at_carrying_value')
                payload['debt'] = balance_sheet.get('liabilities')
                
                # Calculate ratios
                if payload['liabilities'] and payload['equity']:
                    payload['debt_to_equity'] = (
                        float(payload['liabilities']) / 
                        float(payload['equity'])
                    )
                
                current_assets = balance_sheet.get('assets_current')
                current_liabilities = balance_sheet.get('liabilities_current')
                
                if current_assets and current_liabilities:
                    payload['current_ratio'] = (
                        float(current_assets) / 
                        float(current_liabilities)
                    )
            
            # Calculate ROE and ROA
            if payload['earnings'] and payload['equity']:
                payload['roe'] = (
                    float(payload['earnings']) / 
                    float(payload['equity']) * 100
                )
            
            if payload['earnings'] and payload['assets']:
                payload['roa'] = (
                    float(payload['earnings']) / 
                    float(payload['assets']) * 100
                )
            
            # Report date
            if financial.get('end_date'):
                try:
                    payload['report_date'] = datetime.strptime(
                        financial['end_date'], 
                        '%Y-%m-%d'
                    ).date()
                except:
                    pass

        stmt = (
            insert(FundamentalData)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=[
                    FundamentalData.stock_id,
                    FundamentalData.fiscal_year,
                    FundamentalData.fiscal_quarter,
                ],
                set_={k: payload[k] for k in payload if k not in ('stock_id', 'fiscal_year', 'fiscal_quarter')}
            )
        )
        self.db.execute(stmt)
    
    def get_latest_fundamental_data(self, symbol: str) -> Optional[FundamentalData]:
        """Get latest fundamental data for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest FundamentalData object or None
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return None
        
        return (
            self.db.query(FundamentalData)
            .filter(FundamentalData.stock_id == stock.id)
            .order_by(FundamentalData.fiscal_year.desc())
            .first()
        )
    
    def fetch_batch(self, symbols: List[str], period: str = "annual") -> Dict[str, bool]:
        """Fetch fundamental data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            period: 'annual' or 'quarterly'
            
        Returns:
            Dictionary mapping symbol to success status
        """
        results = {}
        
        for symbol in symbols:
            try:
                success = self.fetch_fundamental_data(symbol, period)
                results[symbol] = success
            except Exception as e:
                print(f"Error fetching fundamental data for {symbol}: {str(e)}")
                results[symbol] = False
        
        return results

