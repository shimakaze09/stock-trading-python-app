"""Configuration settings management."""

import os
from typing import Optional
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Polygon.io API
    POLYGON_API_KEY: str = os.getenv('POLYGON_API_KEY', '')
    
    # Database Configuration
    DB_USER: str = os.getenv('DB_USER', 'stockuser')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'stockpass')
    DB_NAME: str = os.getenv('DB_NAME', 'stockdb')
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    
    @property
    def DATABASE_URL(self) -> str:
        """Get SQLAlchemy database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Pipeline Configuration
    UPDATE_INTERVAL_MINUTES: int = int(os.getenv('UPDATE_INTERVAL_MINUTES', '30'))
    MAX_API_CALLS_PER_MINUTE: int = int(os.getenv('MAX_API_CALLS_PER_MINUTE', '5'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '100'))
    MAX_SYMBOLS_PER_RUN: int = int(os.getenv('MAX_SYMBOLS_PER_RUN', '300'))
    COVERAGE_WINDOW_DAYS: int = int(os.getenv('COVERAGE_WINDOW_DAYS', '7'))
    MIN_REVISIT_DAYS: int = int(os.getenv('MIN_REVISIT_DAYS', '1'))
    MAX_REVISIT_DAYS: int = int(os.getenv('MAX_REVISIT_DAYS', '14'))
    EXPLORATION_RATE: float = float(os.getenv('EXPLORATION_RATE', '0.05'))
    
    # Rate limiting - compute dynamically to avoid NameError during class definition
    @property
    def API_CALL_INTERVAL_SECONDS(self) -> float:
        value = 60.0 / self.MAX_API_CALLS_PER_MINUTE if self.MAX_API_CALLS_PER_MINUTE > 0 else 12.0
        return float(value)
    
    # Analysis Configuration
    TECHNICAL_INDICATORS: bool = os.getenv('TECHNICAL_INDICATORS', 'true').lower() == 'true'
    FUNDAMENTAL_ANALYSIS: bool = os.getenv('FUNDAMENTAL_ANALYSIS', 'true').lower() == 'true'
    ML_PREDICTIONS: bool = os.getenv('ML_PREDICTIONS', 'true').lower() == 'true'
    
    # Output Configuration
    JSON_EXPORT_PATH: str = os.getenv('JSON_EXPORT_PATH', './exports')
    CLI_OUTPUT: bool = os.getenv('CLI_OUTPUT', 'true').lower() == 'true'
    
    # ML Configuration
    ML_MODEL_TYPES: list = ['linear_regression', 'arima', 'neural_network']
    PREDICTION_HORIZONS: list = [1, 3, 7]  # days ahead
    
    # Technical Indicator Configuration
    SMA_PERIODS: list = [20, 50, 200]
    EMA_PERIODS: list = [12, 26]
    RSI_PERIOD: int = 14
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    BOLLINGER_PERIOD: int = 20
    BOLLINGER_STD: float = 2.0
    
    def validate(self) -> None:
        """Validate that required settings are present."""
        if not self.POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY is required in .env file")
        
        if self.MAX_API_CALLS_PER_MINUTE <= 0:
            raise ValueError("MAX_API_CALLS_PER_MINUTE must be greater than 0")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    # Only validate when API key is actually used, not during import
    # settings.validate()
    return settings

