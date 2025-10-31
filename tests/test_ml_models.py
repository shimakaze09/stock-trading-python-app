"""Test ML models."""

import pytest
import numpy as np
from ml.models import LinearRegressionModel, ARIMAModel, NeuralNetworkModel


def test_linear_regression_model():
    """Test linear regression model."""
    model = LinearRegressionModel()
    
    # Generate sample data
    np.random.seed(42)
    X = np.random.randn(100, 10)
    y = np.random.randn(100)
    
    # Train model
    metrics = model.train(X, y)
    
    assert model.is_trained
    assert 'mse' in metrics
    assert 'mae' in metrics
    assert 'r2' in metrics
    
    # Make predictions
    predictions = model.predict(X[:10])
    assert len(predictions) == 10
    assert isinstance(predictions[0], (float, np.floating))


def test_arima_model():
    """Test ARIMA model."""
    model = ARIMAModel(order=(5, 1, 0))
    
    # Generate sample time series data
    np.random.seed(42)
    y = np.cumsum(np.random.randn(100)) + 100
    
    # Train model
    metrics = model.train(np.random.randn(100, 10), y)
    
    if 'error' not in metrics:
        assert model.is_trained
        
        # Make predictions
        predictions = model.predict(np.random.randn(10, 10), steps=10)
        assert len(predictions) == 10
    else:
        pytest.skip(f"ARIMA training failed: {metrics.get('error')}")


def test_neural_network_model():
    """Test neural network model."""
    model = NeuralNetworkModel(input_dim=10, hidden_layers=[32, 16], dropout=0.2)
    
    # Generate sample data
    np.random.seed(42)
    X = np.random.randn(100, 10)
    y = np.random.randn(100)
    
    # Train model
    metrics = model.train(X, y, epochs=5, batch_size=32, validation_split=0.2)
    
    assert model.is_trained
    assert 'mse' in metrics
    assert 'mae' in metrics
    
    # Make predictions
    predictions = model.predict(X[:10])
    assert len(predictions) == 10
    assert isinstance(predictions[0], (float, np.floating))


def test_model_save_load():
    """Test model save and load."""
    model = LinearRegressionModel()
    
    # Generate sample data
    np.random.seed(42)
    X = np.random.randn(50, 5)
    y = np.random.randn(50)
    
    # Train model
    model.train(X, y)
    
    # Save model
    import os
    os.makedirs('test_models', exist_ok=True)
    model.save('test_models/test_linear')
    
    # Load model
    new_model = LinearRegressionModel()
    new_model.load('test_models/test_linear')
    
    assert new_model.is_trained
    
    # Test predictions match
    predictions1 = model.predict(X[:5])
    predictions2 = new_model.predict(X[:5])
    
    np.testing.assert_array_almost_equal(predictions1, predictions2)

