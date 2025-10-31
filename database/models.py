"""SQLAlchemy database models."""

from sqlalchemy import (
    Column, Integer, String, Numeric, BigInteger, Boolean,
    Date, DateTime, ForeignKey, UniqueConstraint, Index, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()


class Stock(Base):
    """Master list of US-listed stocks."""
    
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    market = Column(String(50))
    locale = Column(String(10), default='us')
    primary_exchange = Column(String(50))
    type = Column(String(50))
    active = Column(Boolean, default=True, index=True)
    currency = Column(String(10), default='USD')
    sector = Column(String(100))
    industry = Column(String(255))
    description = Column(Text)
    homepage_url = Column(String(500))
    total_employees = Column(Integer)
    list_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = relationship('StockPrice', back_populates='stock', cascade='all, delete-orphan')
    technical_indicators = relationship('TechnicalIndicator', back_populates='stock', cascade='all, delete-orphan')
    fundamental_data = relationship('FundamentalData', back_populates='stock', cascade='all, delete-orphan')
    predictions = relationship('Prediction', back_populates='stock', cascade='all, delete-orphan')
    analysis_reports = relationship('AnalysisReport', back_populates='stock', cascade='all, delete-orphan')


class StockPrice(Base):
    """Historical price data."""
    
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Numeric(15, 4), nullable=False)
    high = Column(Numeric(15, 4), nullable=False)
    low = Column(Numeric(15, 4), nullable=False)
    close = Column(Numeric(15, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    vwap = Column(Numeric(15, 4))
    transactions = Column(Integer)
    otc = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'timestamp', name='uq_stock_prices_stock_timestamp'),
        Index('idx_stock_prices_stock_timestamp', 'stock_id', 'timestamp'),
    )
    
    # Relationships
    stock = relationship('Stock', back_populates='prices')


class TechnicalIndicator(Base):
    """Pre-calculated technical indicators."""
    
    __tablename__ = 'technical_indicators'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Moving Averages
    sma_20 = Column(Numeric(15, 4))
    sma_50 = Column(Numeric(15, 4))
    sma_200 = Column(Numeric(15, 4))
    ema_12 = Column(Numeric(15, 4))
    ema_26 = Column(Numeric(15, 4))
    
    # MACD
    macd = Column(Numeric(15, 4))
    macd_signal = Column(Numeric(15, 4))
    macd_histogram = Column(Numeric(15, 4))
    
    # Momentum
    rsi = Column(Numeric(5, 2))
    stochastic_k = Column(Numeric(5, 2))
    stochastic_d = Column(Numeric(5, 2))
    williams_r = Column(Numeric(5, 2))
    
    # Volatility
    bollinger_upper = Column(Numeric(15, 4))
    bollinger_middle = Column(Numeric(15, 4))
    bollinger_lower = Column(Numeric(15, 4))
    atr = Column(Numeric(15, 4))
    
    # Volume
    obv = Column(BigInteger)
    volume_sma = Column(Numeric(15, 2))
    
    # Support/Resistance
    support_level = Column(Numeric(15, 4))
    resistance_level = Column(Numeric(15, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'timestamp', name='uq_technical_indicators_stock_timestamp'),
        Index('idx_technical_indicators_stock_timestamp', 'stock_id', 'timestamp'),
    )
    
    # Relationships
    stock = relationship('Stock', back_populates='technical_indicators')


class FundamentalData(Base):
    """Company fundamental data."""
    
    __tablename__ = 'fundamental_data'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    fiscal_year = Column(Integer, index=True)
    fiscal_quarter = Column(Integer)
    
    # Valuation
    market_cap = Column(BigInteger)
    pe_ratio = Column(Numeric(10, 2))
    pb_ratio = Column(Numeric(10, 2))
    ev_ebitda = Column(Numeric(10, 2))
    
    # Financial Health
    current_ratio = Column(Numeric(10, 2))
    debt_to_equity = Column(Numeric(10, 2))
    quick_ratio = Column(Numeric(10, 2))
    
    # Growth
    revenue_growth = Column(Numeric(10, 2))
    earnings_growth = Column(Numeric(10, 2))
    
    # Profitability
    roe = Column(Numeric(10, 2))
    roa = Column(Numeric(10, 2))
    profit_margin = Column(Numeric(10, 2))
    
    # Raw data
    revenue = Column(BigInteger)
    earnings = Column(BigInteger)
    assets = Column(BigInteger)
    liabilities = Column(BigInteger)
    equity = Column(BigInteger)
    cash = Column(BigInteger)
    debt = Column(BigInteger)
    
    report_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'fiscal_year', 'fiscal_quarter', name='uq_fundamental_data_stock_fiscal'),
        Index('idx_fundamental_data_fiscal', 'fiscal_year', 'fiscal_quarter'),
    )
    
    # Relationships
    stock = relationship('Stock', back_populates='fundamental_data')


class Prediction(Base):
    """ML model predictions."""
    
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    prediction_date = Column(DateTime, nullable=False, index=True)
    prediction_horizon = Column(Integer, nullable=False)  # days ahead
    predicted_price = Column(Numeric(15, 4))
    predicted_change = Column(Numeric(10, 2))  # percentage
    predicted_direction = Column(String(10))  # 'bullish', 'bearish', 'neutral'
    confidence_score = Column(Numeric(5, 2))  # 0-100
    model_version = Column(String(50))
    features = Column(JSONB)  # JSONB data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_predictions_stock_date', 'stock_id', 'prediction_date'),
    )
    
    # Relationships
    stock = relationship('Stock', back_populates='predictions')
    
    def set_features(self, features_dict: dict):
        """Set features as JSON object."""
        self.features = features_dict
    
    def get_features(self) -> dict:
        """Get features as dictionary."""
        return self.features or {}


class AnalysisReport(Base):
    """Comprehensive analysis reports."""
    
    __tablename__ = 'analysis_reports'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    report_date = Column(DateTime, nullable=False, index=True)
    
    # Overall scores
    technical_score = Column(Numeric(5, 2))  # 0-100
    fundamental_score = Column(Numeric(5, 2))  # 0-100
    overall_score = Column(Numeric(5, 2))  # 0-100
    
    # Recommendations
    recommendation = Column(String(10))  # 'BUY', 'HOLD', 'SELL'
    recommendation_confidence = Column(Numeric(5, 2))  # 0-100
    
    # Risk assessment
    risk_level = Column(String(20))  # 'LOW', 'MEDIUM', 'HIGH'
    volatility_score = Column(Numeric(5, 2))
    drawdown_potential = Column(Numeric(5, 2))
    
    # Summaries
    technical_summary = Column(Text)
    fundamental_summary = Column(Text)
    prediction_summary = Column(Text)
    overall_summary = Column(Text)
    
    # Raw data (JSON)
    technical_data = Column(JSONB)  # JSONB data
    fundamental_data = Column(JSONB)  # JSONB data
    prediction_data = Column(JSONB)  # JSONB data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'report_date', name='uq_analysis_reports_stock_date'),
        Index('idx_analysis_reports_stock_date', 'stock_id', 'report_date'),
    )
    
    # Relationships
    stock = relationship('Stock', back_populates='analysis_reports')
    
    def set_technical_data(self, data: dict):
        """Set technical data as JSON object."""
        self.technical_data = data
    
    def set_fundamental_data(self, data: dict):
        """Set fundamental data as JSON object."""
        self.fundamental_data = data
    
    def set_prediction_data(self, data: dict):
        """Set prediction data as JSON object."""
        self.prediction_data = data
    
    def get_technical_data(self) -> dict:
        """Get technical data as dictionary."""
        return self.technical_data or {}
    
    def get_fundamental_data(self) -> dict:
        """Get fundamental data as dictionary."""
        return self.fundamental_data or {}
    
    def get_prediction_data(self) -> dict:
        """Get prediction data as dictionary."""
        return self.prediction_data or {}


class IngestionState(Base):
    """Tracks per-symbol ingestion metrics for adaptive scheduling."""
    __tablename__ = 'ingestion_state'

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    last_price_update = Column(DateTime)
    last_fundamental_update = Column(DateTime)
    last_prediction = Column(DateTime)
    success_streak = Column(Integer, default=0)
    failure_streak = Column(Integer, default=0)
    priority_score = Column(Numeric(10, 4), default=0)
    avg_runtime_ms = Column(Integer)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stock = relationship('Stock')

