"""Technical analysis engine."""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import Stock, StockPrice, TechnicalIndicator
from .indicators import IndicatorCalculator
from config import get_settings


class TechnicalAnalyzer:
    """Performs technical analysis on stock price data."""
    
    def __init__(self, db_session: Session):
        """Initialize technical analyzer."""
        self.db = db_session
        self.settings = get_settings()
        self.calculator = IndicatorCalculator()
    
    def calculate_indicators(
        self,
        symbol: str,
        days: int = 365,
        recalculate: bool = False
    ) -> int:
        """Calculate technical indicators for a stock.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days of price data to analyze
            recalculate: Recalculate existing indicators (default: False)
            
        Returns:
            Number of indicator records created/updated
        """
        # Get stock
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            print(f"Stock {symbol} not found in database.")
            return 0
        
        # Get price data
        cutoff_date = datetime.now() - timedelta(days=days)
        
        prices = (
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
        
        if not prices or len(prices) < 50:
            print(f"Insufficient price data for {symbol}")
            return 0
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': p.timestamp,
            'open': float(p.open),
            'high': float(p.high),
            'low': float(p.low),
            'close': float(p.close),
            'volume': int(p.volume)
        } for p in prices])
        
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Calculate indicators
        indicators_df = self._calculate_all_indicators(df)
        
        # Store indicators in database
        count = 0
        for timestamp, row in indicators_df.iterrows():
            # Check if indicator already exists
            existing = (
                self.db.query(TechnicalIndicator)
                .filter(
                    and_(
                        TechnicalIndicator.stock_id == stock.id,
                        TechnicalIndicator.timestamp == timestamp
                    )
                )
                .first()
            )
            
            if existing and not recalculate:
                continue
            
            if existing:
                indicator = existing
            else:
                indicator = TechnicalIndicator(
                    stock_id=stock.id,
                    timestamp=timestamp
                )
                self.db.add(indicator)
            
            # Update indicator values
            indicator.sma_20 = float(row.get('sma_20', 0)) if pd.notna(row.get('sma_20')) else None
            indicator.sma_50 = float(row.get('sma_50', 0)) if pd.notna(row.get('sma_50')) else None
            indicator.sma_200 = float(row.get('sma_200', 0)) if pd.notna(row.get('sma_200')) else None
            indicator.ema_12 = float(row.get('ema_12', 0)) if pd.notna(row.get('ema_12')) else None
            indicator.ema_26 = float(row.get('ema_26', 0)) if pd.notna(row.get('ema_26')) else None
            
            indicator.macd = float(row.get('macd', 0)) if pd.notna(row.get('macd')) else None
            indicator.macd_signal = float(row.get('macd_signal', 0)) if pd.notna(row.get('macd_signal')) else None
            indicator.macd_histogram = float(row.get('macd_histogram', 0)) if pd.notna(row.get('macd_histogram')) else None
            
            indicator.rsi = float(row.get('rsi', 0)) if pd.notna(row.get('rsi')) else None
            indicator.stochastic_k = float(row.get('stochastic_k', 0)) if pd.notna(row.get('stochastic_k')) else None
            indicator.stochastic_d = float(row.get('stochastic_d', 0)) if pd.notna(row.get('stochastic_d')) else None
            indicator.williams_r = float(row.get('williams_r', 0)) if pd.notna(row.get('williams_r')) else None
            
            indicator.bollinger_upper = float(row.get('bb_upper', 0)) if pd.notna(row.get('bb_upper')) else None
            indicator.bollinger_middle = float(row.get('bb_middle', 0)) if pd.notna(row.get('bb_middle')) else None
            indicator.bollinger_lower = float(row.get('bb_lower', 0)) if pd.notna(row.get('bb_lower')) else None
            indicator.atr = float(row.get('atr', 0)) if pd.notna(row.get('atr')) else None
            
            indicator.obv = int(row.get('obv', 0)) if pd.notna(row.get('obv')) else None
            indicator.volume_sma = float(row.get('volume_sma', 0)) if pd.notna(row.get('volume_sma')) else None
            
            indicator.support_level = float(row.get('support', 0)) if pd.notna(row.get('support')) else None
            indicator.resistance_level = float(row.get('resistance', 0)) if pd.notna(row.get('resistance')) else None
            
            count += 1
        
        self.db.commit()
        print(f"Calculated {count} technical indicators for {symbol}")
        return count
    
    def _calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        indicators = pd.DataFrame(index=df.index)
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Moving Averages
        indicators['sma_20'] = self.calculator.sma(close, 20)
        indicators['sma_50'] = self.calculator.sma(close, 50)
        indicators['sma_200'] = self.calculator.sma(close, 200)
        indicators['ema_12'] = self.calculator.ema(close, 12)
        indicators['ema_26'] = self.calculator.ema(close, 26)
        
        # MACD
        macd_result = self.calculator.macd(close, 12, 26, 9)
        indicators['macd'] = macd_result['macd']
        indicators['macd_signal'] = macd_result['signal']
        indicators['macd_histogram'] = macd_result['histogram']
        
        # Momentum
        indicators['rsi'] = self.calculator.rsi(close, 14)
        
        stochastic_result = self.calculator.stochastic(high, low, close, 14, 3)
        indicators['stochastic_k'] = stochastic_result['k']
        indicators['stochastic_d'] = stochastic_result['d']
        
        indicators['williams_r'] = self.calculator.williams_r(high, low, close, 14)
        
        # Volatility
        bb_result = self.calculator.bollinger_bands(close, 20, 2.0)
        indicators['bb_upper'] = bb_result['upper']
        indicators['bb_middle'] = bb_result['middle']
        indicators['bb_lower'] = bb_result['lower']
        
        indicators['atr'] = self.calculator.atr(high, low, close, 14)
        
        # Volume
        indicators['obv'] = self.calculator.obv(close, volume)
        indicators['volume_sma'] = self.calculator.volume_sma(volume, 20)
        
        # Support/Resistance
        sr_result = self.calculator.support_resistance(high, low, close, 20)
        indicators['support'] = sr_result['support']
        indicators['resistance'] = sr_result['resistance']
        
        return indicators
    
    def get_latest_indicators(self, symbol: str) -> Optional[TechnicalIndicator]:
        """Get latest technical indicators for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest TechnicalIndicator object or None
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return None
        
        return (
            self.db.query(TechnicalIndicator)
            .filter(TechnicalIndicator.stock_id == stock.id)
            .order_by(TechnicalIndicator.timestamp.desc())
            .first()
        )
    
    def calculate_batch(self, symbols: List[str], days: int = 365, recalculate: bool = False) -> Dict[str, int]:
        """Calculate indicators for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            days: Number of days of price data
            recalculate: Recalculate existing indicators
            
        Returns:
            Dictionary mapping symbol to number of indicators calculated
        """
        results = {}
        
        for symbol in symbols:
            try:
                count = self.calculate_indicators(symbol, days, recalculate)
                results[symbol] = count
            except Exception as e:
                print(f"Error calculating indicators for {symbol}: {str(e)}")
                results[symbol] = 0
        
        return results

