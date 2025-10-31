"""Model training pipeline with backtesting and evaluation."""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Stock, Prediction
from .models import MLModel, LinearRegressionModel, ARIMAModel, NeuralNetworkModel
from .features import FeatureEngineer
from config import get_settings


class ModelTrainer:
    """Trains ML models with backtesting and evaluation."""
    
    def __init__(self, db_session: Session):
        """Initialize model trainer."""
        self.db = db_session
        self.settings = get_settings()
        self.feature_engineer = FeatureEngineer(db_session)
    
    def train_models(
        self,
        symbol: str,
        horizons: Optional[List[int]] = None,
        test_split: float = 0.2,
        retrain: bool = False
    ) -> Dict[str, Dict]:
        """Train all ML models for a stock.
        
        Args:
            symbol: Stock ticker symbol
            horizons: List of prediction horizons in days (default: [1, 3, 7])
            test_split: Fraction of data to use for testing
            retrain: Retrain even if model exists (default: False)
            
        Returns:
            Dictionary mapping model_type to training results
        """
        horizons = horizons or self.settings.PREDICTION_HORIZONS
        
        # Extract features
        features_df = self.feature_engineer.extract_features(symbol, days=730, lookback_window=30)
        
        if features_df is None or len(features_df) < 100:
            print(f"Insufficient data for training models for {symbol}")
            return {}
        
        results = {}
        
        # Train each model type
        for model_type in self.settings.ML_MODEL_TYPES:
            try:
                model_results = self._train_model_type(
                    symbol, model_type, features_df, horizons, test_split, retrain
                )
                results[model_type] = model_results
            except Exception as e:
                print(f"Error training {model_type} for {symbol}: {str(e)}")
                results[model_type] = {'error': str(e)}
        
        return results
    
    def _train_model_type(
        self,
        symbol: str,
        model_type: str,
        features_df: pd.DataFrame,
        horizons: List[int],
        test_split: float,
        retrain: bool
    ) -> Dict:
        """Train a specific model type."""
        results = {}
        
        # Prepare data
        # Drop target columns to get features
        target_cols = [col for col in features_df.columns if col.startswith('target_')]
        feature_cols = [col for col in features_df.columns if col not in target_cols]
        
        X = features_df[feature_cols].values
        
        # Train for each horizon
        for horizon in horizons:
            try:
                target_col = f'target_{horizon}d'
                if target_col not in features_df.columns:
                    continue
                
                y = features_df[target_col].values
                
                # Remove NaN values
                valid_mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
                X_clean = X[valid_mask]
                y_clean = y[valid_mask]
                
                if len(X_clean) < 50:
                    print(f"Insufficient clean data for horizon {horizon}d")
                    continue
                
                # Split train/test
                split_idx = int(len(X_clean) * (1 - test_split))
                X_train, X_test = X_clean[:split_idx], X_clean[split_idx:]
                y_train, y_test = y_clean[:split_idx], y_clean[split_idx:]
                
                # Create and train model
                if model_type == 'linear_regression':
                    model = LinearRegressionModel()
                elif model_type == 'arima':
                    model = ARIMAModel(order=(5, 1, 0))
                elif model_type == 'neural_network':
                    model = NeuralNetworkModel(input_dim=X_train.shape[1], hidden_layers=[128, 64, 32])
                else:
                    continue
                
                # Train model
                train_metrics = model.train(X_train, y_train)
                
                # Evaluate on test set
                if model_type == 'arima':
                    test_pred = model.predict(X_test, steps=len(y_test))
                else:
                    test_pred = model.predict(X_test)
                
                test_mse = np.mean((y_test - test_pred) ** 2)
                test_mae = np.mean(np.abs(y_test - test_pred))
                
                # Save model
                model_dir = f'models/{symbol}'
                model_path = f'{model_dir}/{model_type}_{horizon}d'
                model.save(model_path)
                
                results[f'{horizon}d'] = {
                    'train_metrics': train_metrics,
                    'test_mse': float(test_mse),
                    'test_mae': float(test_mae),
                    'model_path': model_path
                }
                
                print(f"Trained {model_type} for {symbol} (horizon: {horizon}d)")
                
            except Exception as e:
                print(f"Error training {model_type} for horizon {horizon}d: {str(e)}")
                results[f'{horizon}d'] = {'error': str(e)}
        
        return results
    
    def backtest_model(
        self,
        symbol: str,
        model_type: str,
        horizon: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Backtest a trained model.
        
        Args:
            symbol: Stock ticker symbol
            model_type: Type of model to backtest
            horizon: Prediction horizon in days
            start_date: Start date for backtesting
            end_date: End date for backtesting
            
        Returns:
            Dictionary with backtesting results
        """
        # Load model
        model_path = f'models/{symbol}/{model_type}_{horizon}d'
        
        if model_type == 'linear_regression':
            model = LinearRegressionModel()
        elif model_type == 'arima':
            model = ARIMAModel()
        elif model_type == 'neural_network':
            model = NeuralNetworkModel()
        else:
            return {'error': f'Unknown model type: {model_type}'}
        
        try:
            model.load(model_path)
        except Exception as e:
            return {'error': f'Failed to load model: {str(e)}'}
        
        # Extract features for backtest period
        features_df = self.feature_engineer.extract_features(symbol, days=730, lookback_window=30)
        
        if features_df is None or len(features_df) == 0:
            return {'error': 'Insufficient data for backtesting'}
        
        # Filter by date range if provided
        if start_date:
            features_df = features_df[features_df.index >= start_date]
        if end_date:
            features_df = features_df[features_df.index <= end_date]
        
        if len(features_df) < 10:
            return {'error': 'Insufficient data in date range'}
        
        # Prepare features
        target_col = f'target_{horizon}d'
        if target_col not in features_df.columns:
            return {'error': f'Target column {target_col} not found'}
        
        target_cols = [col for col in features_df.columns if col.startswith('target_')]
        feature_cols = [col for col in features_df.columns if col not in target_cols]
        
        X = features_df[feature_cols].values
        y_true = features_df[target_col].values
        
        # Remove NaN
        valid_mask = ~(np.isnan(X).any(axis=1) | np.isnan(y_true))
        X_clean = X[valid_mask]
        y_true_clean = y_true[valid_mask]
        
        if len(X_clean) < 10:
            return {'error': 'Insufficient clean data'}
        
        # Make predictions
        if model_type == 'arima':
            y_pred = model.predict(X_clean, steps=len(y_true_clean))
        else:
            y_pred = model.predict(X_clean)
        
        # Calculate metrics
        mse = np.mean((y_true_clean - y_pred) ** 2)
        mae = np.mean(np.abs(y_true_clean - y_pred))
        rmse = np.sqrt(mse)
        
        # Direction accuracy
        direction_correct = np.sum((y_true_clean > 0) == (y_pred > 0)) / len(y_true_clean)
        
        return {
            'mse': float(mse),
            'mae': float(mae),
            'rmse': float(rmse),
            'direction_accuracy': float(direction_correct),
            'num_predictions': len(y_pred)
        }

