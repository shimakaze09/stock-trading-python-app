"""Prediction generation module with confidence scores."""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.models import Stock, Prediction
from .models import MLModel, LinearRegressionModel, ARIMAModel, NeuralNetworkModel
from .features import FeatureEngineer
from config import get_settings


class PredictionGenerator:
    """Generates predictions using trained ML models."""
    
    def __init__(self, db_session: Session):
        """Initialize prediction generator."""
        self.db = db_session
        self.settings = get_settings()
        self.feature_engineer = FeatureEngineer(db_session)
    
    def generate_predictions(
        self,
        symbol: str,
        horizons: Optional[List[int]] = None,
        save_to_db: bool = True
    ) -> Dict[str, Dict]:
        """Generate predictions for a stock using all trained models.
        
        Args:
            symbol: Stock ticker symbol
            horizons: List of prediction horizons in days (default: [1, 3, 7])
            save_to_db: Save predictions to database (default: True)
            
        Returns:
            Dictionary mapping model_type to predictions
        """
        horizons = horizons or self.settings.PREDICTION_HORIZONS
        
        # Get stock
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            print(f"Stock {symbol} not found in database.")
            return {}
        
        # Get latest price
        from data_fetch.price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher(self.db)
        latest_price = price_fetcher.get_latest_price(symbol)
        
        if not latest_price:
            print(f"No price data available for {symbol}")
            return {}
        
        current_price = float(latest_price.close)
        
        # Extract features
        latest_features = self.feature_engineer.get_latest_features(symbol, lookback_window=30)
        
        if latest_features is None:
            print(f"Insufficient data to generate predictions for {symbol}")
            return {}
        
        all_predictions = {}
        
        # Generate predictions for each model type
        for model_type in self.settings.ML_MODEL_TYPES:
            try:
                model_predictions = self._generate_model_predictions(
                    symbol, stock.id, model_type, horizons, current_price, latest_features, save_to_db
                )
                all_predictions[model_type] = model_predictions
            except Exception as e:
                print(f"Error generating {model_type} predictions for {symbol}: {str(e)}")
                all_predictions[model_type] = {'error': str(e)}
        
        return all_predictions
    
    def _generate_model_predictions(
        self,
        symbol: str,
        stock_id: int,
        model_type: str,
        horizons: List[int],
        current_price: float,
        features: np.ndarray,
        save_to_db: bool
    ) -> Dict:
        """Generate predictions for a specific model type."""
        predictions = {}
        
        import os
        for horizon in horizons:
            try:
                # Load model
                model_path = f'models/{symbol}/{model_type}_{horizon}d'
                
                if model_type == 'linear_regression':
                    model = LinearRegressionModel()
                elif model_type == 'arima':
                    model = ARIMAModel()
                elif model_type == 'neural_network':
                    model = NeuralNetworkModel()
                else:
                    continue
                
                # Skip if model file(s) do not exist
                if model_type == 'neural_network':
                    has_file = os.path.exists(model_path + '.keras') or os.path.exists(model_path + '.h5')
                else:
                    has_file = os.path.exists(model_path + '.pkl')
                if not has_file:
                    # Try restore from DB registry
                    from database.connection import get_db_context
                    from ml.registry import restore_model_binary
                    restored = False
                    try:
                        # Use current session from orchestrator context if possible
                        restored = restore_model_binary(self.db, symbol, model_type, horizon, model_path)
                    except Exception:
                        pass
                    if not restored:
                        print(f"Model file not found for {symbol} {model_type} {horizon}d, skipping prediction")
                        continue

                # Load model
                model.load(model_path)
                
                # Make prediction
                if model_type == 'arima':
                    # ARIMA needs historical data
                    pred_return = model.predict(features.reshape(1, -1), steps=1)[0]
                else:
                    pred_return = model.predict(features.reshape(1, -1))[0]
                
                # Calculate predicted price
                predicted_price = current_price * (1 + pred_return)
                predicted_change = pred_return * 100  # percentage
                
                # Determine direction
                if pred_return > 0.02:  # > 2%
                    direction = 'bullish'
                elif pred_return < -0.02:  # < -2%
                    direction = 'bearish'
                else:
                    direction = 'neutral'
                
                # Calculate confidence (based on magnitude of prediction)
                confidence = min(100, abs(pred_return) * 1000)  # Scale to 0-100
                
                # Store prediction
                pred_data = {
                    'predicted_price': float(predicted_price),
                    'predicted_change': float(predicted_change),
                    'predicted_direction': direction,
                    'confidence_score': float(confidence),
                    'horizon': horizon,
                    'current_price': current_price
                }
                
                predictions[f'{horizon}d'] = pred_data
                
                # Save to database
                if save_to_db:
                    self._save_prediction(
                        stock_id=stock_id,
                        model_type=model_type,
                        prediction_horizon=horizon,
                        predicted_price=predicted_price,
                        predicted_change=predicted_change,
                        predicted_direction=direction,
                        confidence_score=confidence,
                        features={'latest_features': features.tolist()}
                    )
                
            except Exception as e:
                print(f"Error generating {model_type} prediction for horizon {horizon}d: {str(e)}")
                predictions[f'{horizon}d'] = {'error': str(e)}
        
        return predictions
    
    def _save_prediction(
        self,
        stock_id: int,
        model_type: str,
        prediction_horizon: int,
        predicted_price: float,
        predicted_change: float,
        predicted_direction: str,
        confidence_score: float,
        features: Dict
    ):
        """Save prediction to database."""
        import json
        from sqlalchemy import Date
        from sqlalchemy import func
        
        # Avoid duplicates: delete any existing record for the same key before insert
        today = datetime.utcnow().date()
        existing = (
            self.db.query(Prediction)
            .filter(
                Prediction.stock_id == stock_id,
                Prediction.model_type == model_type,
                Prediction.prediction_horizon == prediction_horizon,
                func.date(Prediction.prediction_date) == today
            )
            .all()
        )
        for row in existing:
            self.db.delete(row)
        self.db.flush()

        prediction = Prediction(
            stock_id=stock_id,
            model_type=model_type,
            prediction_date=datetime.utcnow(),
            prediction_horizon=prediction_horizon,
            predicted_price=predicted_price,
            predicted_change=predicted_change,
            predicted_direction=predicted_direction,
            confidence_score=confidence_score,
            model_version='1.0'
        )
        prediction.set_features(features)
        self.db.add(prediction)
        self.db.commit()
    
    def get_latest_predictions(self, symbol: str, model_type: Optional[str] = None) -> List[Prediction]:
        """Get latest predictions for a stock.
        
        Args:
            symbol: Stock ticker symbol
            model_type: Filter by model type (optional)
            
        Returns:
            List of Prediction objects
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return []
        
        query = (
            self.db.query(Prediction)
            .filter(Prediction.stock_id == stock.id)
            .order_by(Prediction.prediction_date.desc())
        )
        
        if model_type:
            query = query.filter(Prediction.model_type == model_type)
        
        return query.limit(10).all()
    
    def generate_ensemble_prediction(
        self,
        symbol: str,
        horizon: int,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Generate ensemble prediction combining multiple models.
        
        Args:
            symbol: Stock ticker symbol
            horizon: Prediction horizon in days
            weights: Dictionary mapping model_type to weight (default: equal weights)
            
        Returns:
            Dictionary with ensemble prediction
        """
        # Generate predictions from all models
        all_predictions = self.generate_predictions(symbol, horizons=[horizon], save_to_db=False)
        
        # Collect predictions
        predictions = []
        weights_dict = weights or {}
        
        for model_type, model_preds in all_predictions.items():
            if f'{horizon}d' in model_preds and 'error' not in model_preds[f'{horizon}d']:
                pred_data = model_preds[f'{horizon}d']
                weight = weights_dict.get(model_type, 1.0 / len(all_predictions))
                predictions.append({
                    'predicted_change': pred_data['predicted_change'],
                    'confidence': pred_data['confidence_score'],
                    'weight': weight,
                    'model_type': model_type
                })
        
        if not predictions:
            return {'error': 'No predictions available'}
        
        # Weighted average
        total_weight = sum(p['weight'] for p in predictions)
        weighted_change = sum(p['predicted_change'] * p['weight'] for p in predictions) / total_weight
        weighted_confidence = sum(p['confidence'] * p['weight'] for p in predictions) / total_weight
        
        # Get current price
        from data_fetch.price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher(self.db)
        latest_price = price_fetcher.get_latest_price(symbol)
        current_price = float(latest_price.close) if latest_price else 0
        
        # Calculate predicted price
        predicted_price = current_price * (1 + weighted_change / 100)
        
        # Determine direction
        if weighted_change > 2:
            direction = 'bullish'
        elif weighted_change < -2:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        return {
            'predicted_price': float(predicted_price),
            'predicted_change': float(weighted_change),
            'predicted_direction': direction,
            'confidence_score': float(weighted_confidence),
            'horizon': horizon,
            'current_price': current_price,
            'models_used': [p['model_type'] for p in predictions],
            'num_models': len(predictions)
        }

