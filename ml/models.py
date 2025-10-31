"""ML model definitions."""

import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')  # Reduce TF logging
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')  # Disable GPU to avoid CUDA warnings

import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
from abc import ABC, abstractmethod
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pickle
import os

from config import get_settings


class MLModel(ABC):
    """Abstract base class for ML models."""
    
    def __init__(self, model_type: str):
        """Initialize ML model."""
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.settings = get_settings()
    
    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the model."""
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        pass
    
    def save(self, filepath: str):
        """Save the model to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'scaler': self.scaler
        }
        
        if self.model_type == 'neural_network':
            # Use modern Keras format
            self.model.save(filepath + '.keras')
        else:
            model_data['model'] = self.model
            # Persist fitted model for ARIMA
            if self.model_type == 'arima':
                model_data['fitted_model'] = getattr(self, 'fitted_model', None)
        
        with open(filepath + '.pkl', 'wb') as f:
            pickle.dump(model_data, f)
    
    def load(self, filepath: str):
        """Load the model from disk."""
        with open(filepath + '.pkl', 'rb') as f:
            model_data = pickle.load(f)
        
        self.model_type = model_data['model_type']
        self.is_trained = model_data['is_trained']
        self.scaler = model_data['scaler']
        
        if self.model_type == 'neural_network':
            # Load modern Keras format if available, fallback to legacy
            try:
                self.model = keras.models.load_model(filepath + '.keras')
            except Exception:
                self.model = keras.models.load_model(filepath + '.h5')
        else:
            self.model = model_data.get('model')
            if self.model_type == 'arima':
                self.fitted_model = model_data.get('fitted_model')
                # If fitted_model restored, ensure trained flag is consistent
                self.is_trained = self.is_trained and (self.fitted_model is not None)


class LinearRegressionModel(MLModel):
    """Linear regression model for price prediction."""
    
    def __init__(self):
        """Initialize linear regression model."""
        super().__init__('linear_regression')
        self.model = LinearRegression()
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the linear regression model."""
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Calculate metrics
        y_pred = self.model.predict(X_scaled)
        mse = np.mean((y - y_pred) ** 2)
        mae = np.mean(np.abs(y - y_pred))
        r2 = self.model.score(X_scaled, y)
        
        return {
            'mse': float(mse),
            'mae': float(mae),
            'r2': float(r2)
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predictions = self.model.predict(X_scaled)
        
        return predictions


class ARIMAModel(MLModel):
    """ARIMA model for time series prediction."""
    
    def __init__(self, order: Tuple[int, int, int] = (5, 1, 0)):
        """Initialize ARIMA model.
        
        Args:
            order: (p, d, q) parameters for ARIMA
        """
        super().__init__('arima')
        self.order = order
        self.model = None
        self.fitted_model = None
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the ARIMA model."""
        # ARIMA works with univariate time series
        # Use the target variable y as the time series
        if len(y.shape) > 1:
            y = y.flatten()
        
        try:
            self.model = ARIMA(y, order=self.order)
            self.fitted_model = self.model.fit()
            self.is_trained = True
            
            # Get fitted values
            fitted_values = self.fitted_model.fittedvalues
            
            # Calculate metrics
            mse = np.mean((y - fitted_values) ** 2)
            mae = np.mean(np.abs(y - fitted_values))
            aic = self.fitted_model.aic
            
            return {
                'mse': float(mse),
                'mae': float(mae),
                'aic': float(aic)
            }
        except Exception as e:
            print(f"ARIMA training error: {str(e)}")
            return {'error': str(e)}
    
    def predict(self, X: np.ndarray, steps: int = 1) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained or self.fitted_model is None:
            raise ValueError("Model must be trained before prediction")
        
        try:
            # Forecast from the trained/fitted model without refitting
            forecast = self.fitted_model.forecast(steps=steps)
            
            return forecast
        except Exception as e:
            print(f"ARIMA prediction error: {str(e)}")
            return np.array([0.0] * steps)


class NeuralNetworkModel(MLModel):
    """Neural network model for price prediction."""
    
    def __init__(self, input_dim: int = 50, hidden_layers: list = [128, 64, 32], dropout: float = 0.2):
        """Initialize neural network model.
        
        Args:
            input_dim: Number of input features
            hidden_layers: List of hidden layer sizes
            dropout: Dropout rate
        """
        super().__init__('neural_network')
        self.input_dim = input_dim
        self.hidden_layers = hidden_layers
        self.dropout = dropout
        self.history = None
    
    def _build_model(self, input_dim: int):
        """Build the neural network architecture."""
        model = keras.Sequential()
        
        # Input layer
        model.add(layers.Input(shape=(input_dim,)))
        
        # Hidden layers
        for layer_size in self.hidden_layers:
            model.add(layers.Dense(layer_size, activation='relu'))
            if self.dropout > 0:
                model.add(layers.Dropout(self.dropout))
        
        # Output layer
        model.add(layers.Dense(1, activation='linear'))
        
        # Compile model
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 50, batch_size: int = 32, validation_split: float = 0.2) -> Dict:
        """Train the neural network."""
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Build model if not exists
        if self.model is None:
            self.model = self._build_model(X_scaled.shape[1])
        
        # Train model
        self.history = self.model.fit(
            X_scaled, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=0
        )
        
        self.is_trained = True
        
        # Calculate metrics
        y_pred = self.model.predict(X_scaled, verbose=0)
        mse = np.mean((y - y_pred.flatten()) ** 2)
        mae = np.mean(np.abs(y - y_pred.flatten()))
        
        # Validation metrics
        val_loss = self.history.history['val_loss'][-1] if 'val_loss' in self.history.history else None
        val_mae = self.history.history['val_mae'][-1] if 'val_mae' in self.history.history else None
        
        return {
            'mse': float(mse),
            'mae': float(mae),
            'val_loss': float(val_loss) if val_loss else None,
            'val_mae': float(val_mae) if val_mae else None,
            'epochs': len(self.history.history['loss'])
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predictions = self.model.predict(X_scaled, verbose=0)
        
        return predictions.flatten()

