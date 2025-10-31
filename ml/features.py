"""Feature engineering for ML models."""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import Stock, StockPrice, TechnicalIndicator
from analysis.indicators import IndicatorCalculator
from config import get_settings


class FeatureEngineer:
    """Engineers features from technical indicators and price data."""
    
    def __init__(self, db_session: Session):
        """Initialize feature engineer."""
        self.db = db_session
        self.settings = get_settings()
        self.calculator = IndicatorCalculator()
    
    def extract_features(
        self,
        symbol: str,
        days: int = 365,
        lookback_window: int = 30
    ) -> Optional[pd.DataFrame]:
        """Extract features for ML models.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days of historical data
            lookback_window: Number of days to use as features
            
        Returns:
            DataFrame with features, or None if insufficient data
        """
        # Get stock
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return None
        
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
        
        if not prices or len(prices) < lookback_window + 10:
            return None
        
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
        
        # Get technical indicators
        indicators = (
            self.db.query(TechnicalIndicator)
            .filter(
                and_(
                    TechnicalIndicator.stock_id == stock.id,
                    TechnicalIndicator.timestamp >= cutoff_date
                )
            )
            .order_by(TechnicalIndicator.timestamp.asc())
            .all()
        )
        
        # Create features
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features['close'] = df['close']
        features['open'] = df['open']
        features['high'] = df['high']
        features['low'] = df['low']
        features['volume'] = df['volume']
        
        # Price changes
        features['price_change'] = df['close'].pct_change()
        features['price_change_abs'] = abs(features['price_change'])
        features['high_low_ratio'] = df['high'] / df['low']
        features['close_open_ratio'] = df['close'] / df['open']
        
        # Moving averages
        features['sma_20'] = self.calculator.sma(df['close'], 20)
        features['sma_50'] = self.calculator.sma(df['close'], 50)
        features['ema_12'] = self.calculator.ema(df['close'], 12)
        
        # Price relative to moving averages
        features['price_sma20_ratio'] = df['close'] / features['sma_20']
        features['price_sma50_ratio'] = df['close'] / features['sma_50']
        features['sma20_sma50_ratio'] = features['sma_20'] / features['sma_50']
        
        # MACD
        macd_result = self.calculator.macd(df['close'])
        features['macd'] = macd_result['macd']
        features['macd_signal'] = macd_result['signal']
        features['macd_histogram'] = macd_result['histogram']
        
        # RSI
        features['rsi'] = self.calculator.rsi(df['close'])
        
        # Bollinger Bands
        bb_result = self.calculator.bollinger_bands(df['close'])
        features['bb_upper'] = bb_result['upper']
        features['bb_lower'] = bb_result['lower']
        features['bb_width'] = (bb_result['upper'] - bb_result['lower']) / bb_result['middle']
        features['bb_position'] = (df['close'] - bb_result['lower']) / (bb_result['upper'] - bb_result['lower'])
        
        # ATR
        features['atr'] = self.calculator.atr(df['high'], df['low'], df['close'])
        features['atr_ratio'] = features['atr'] / df['close']
        
        # Volume features
        features['volume_sma'] = self.calculator.volume_sma(df['volume'], 20)
        features['volume_ratio'] = df['volume'] / features['volume_sma']
        
        # OBV
        features['obv'] = self.calculator.obv(df['close'], df['volume'])
        features['obv_change'] = features['obv'].pct_change()
        
        # Lag features
        for lag in [1, 2, 3, 5, 10]:
            features[f'close_lag_{lag}'] = df['close'].shift(lag)
            features[f'price_change_lag_{lag}'] = features['price_change'].shift(lag)
            features[f'volume_lag_{lag}'] = df['volume'].shift(lag)
        
        # Rolling statistics
        for window in [5, 10, 20]:
            features[f'close_rolling_mean_{window}'] = df['close'].rolling(window=window).mean()
            features[f'close_rolling_std_{window}'] = df['close'].rolling(window=window).std()
            features[f'volume_rolling_mean_{window}'] = df['volume'].rolling(window=window).mean()
        
        # Time features
        features['day_of_week'] = features.index.dayofweek
        features['day_of_month'] = features.index.day
        features['month'] = features.index.month
        
        # Target variables (for training)
        features['target_1d'] = df['close'].shift(-1) / df['close'] - 1  # 1-day return
        features['target_3d'] = df['close'].shift(-3) / df['close'] - 1  # 3-day return
        features['target_7d'] = df['close'].shift(-7) / df['close'] - 1  # 7-day return
        
        # Direction targets
        features['target_1d_direction'] = (features['target_1d'] > 0).astype(int)
        features['target_3d_direction'] = (features['target_3d'] > 0).astype(int)
        features['target_7d_direction'] = (features['target_7d'] > 0).astype(int)
        
        # Drop rows with NaN (due to lags and calculations)
        features = features.dropna()
        
        return features
    
    def get_latest_features(self, symbol: str, lookback_window: int = 30) -> Optional[np.ndarray]:
        """Get latest features for prediction.
        
        Args:
            symbol: Stock ticker symbol
            lookback_window: Number of days to use as features
            
        Returns:
            NumPy array of features, or None
        """
        features_df = self.extract_features(symbol, days=lookback_window + 100, lookback_window=lookback_window)
        
        if features_df is None or len(features_df) == 0:
            return None
        
        # Get latest row
        latest_features = features_df.iloc[-1:].copy()
        
        # Drop target columns
        target_cols = [col for col in latest_features.columns if col.startswith('target_')]
        latest_features = latest_features.drop(columns=target_cols)
        
        # Fill NaN with 0
        latest_features = latest_features.fillna(0)
        
        return latest_features.values[0]

