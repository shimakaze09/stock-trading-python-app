"""JSON exporter for AI training data."""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from config import get_settings


class JSONExporter:
    """Exports analysis data to JSON for AI training."""
    
    def __init__(self):
        """Initialize JSON exporter."""
        self.settings = get_settings()
        self.export_path = Path(self.settings.JSON_EXPORT_PATH)
        self.export_path.mkdir(parents=True, exist_ok=True)
    
    def export_report(self, report: Dict, filename: Optional[str] = None) -> str:
        """Export single analysis report to JSON.
        
        Args:
            report: Dictionary with analysis report
            filename: Optional custom filename (default: {symbol}_{timestamp}.json)
            
        Returns:
            Path to exported JSON file
        """
        if not report:
            raise ValueError("Report data is required")
        
        symbol = report.get('symbol', 'UNKNOWN')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if not filename:
            filename = f"{symbol}_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.export_path / filename
        
        # Export report
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Exported report to {filepath}")
        return str(filepath)
    
    def export_batch(self, reports: List[Dict], filename: Optional[str] = None) -> str:
        """Export multiple reports to a single JSON file.
        
        Args:
            reports: List of analysis reports
            filename: Optional custom filename (default: batch_{timestamp}.json)
            
        Returns:
            Path to exported JSON file
        """
        if not reports:
            raise ValueError("Reports list is required")
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if not filename:
            filename = f"batch_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.export_path / filename
        
        # Export reports
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'num_reports': len(reports),
            'reports': reports
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"Exported {len(reports)} reports to {filepath}")
        return str(filepath)
    
    def export_training_data(
        self,
        reports: List[Dict],
        include_features: bool = True,
        include_targets: bool = True,
        filename: Optional[str] = None
    ) -> str:
        """Export data in format suitable for ML training.
        
        Args:
            reports: List of analysis reports
            include_features: Include feature data (default: True)
            include_targets: Include target variables (default: True)
            filename: Optional custom filename (default: training_data_{timestamp}.json)
            
        Returns:
            Path to exported JSON file
        """
        if not reports:
            raise ValueError("Reports list is required")
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if not filename:
            filename = f"training_data_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.export_path / filename
        
        # Prepare training data
        training_data = {
            'export_date': datetime.utcnow().isoformat(),
            'num_samples': len(reports),
            'samples': []
        }
        
        for report in reports:
            sample = {
                'symbol': report.get('symbol'),
                'timestamp': report.get('report_date'),
                'current_price': report.get('current_price')
            }
            
            # Features
            if include_features:
                features = {}
                
                # Technical features
                technical = report.get('technical_analysis', {})
                if technical:
                    features['technical'] = {
                        'rsi': technical.get('rsi'),
                        'macd': technical.get('macd'),
                        'sma_20': technical.get('sma_20'),
                        'sma_50': technical.get('sma_50'),
                        'bollinger_upper': technical.get('bollinger_upper'),
                        'bollinger_lower': technical.get('bollinger_lower'),
                        'atr': technical.get('atr')
                    }
                
                # Fundamental features
                fundamental = report.get('fundamental_analysis', {})
                if fundamental:
                    features['fundamental'] = {
                        'pe_ratio': fundamental.get('pe_ratio'),
                        'pb_ratio': fundamental.get('pb_ratio'),
                        'market_cap': fundamental.get('market_cap'),
                        'roe': fundamental.get('roe'),
                        'debt_to_equity': fundamental.get('debt_to_equity'),
                        'current_ratio': fundamental.get('current_ratio')
                    }
                
                sample['features'] = features
            
            # Targets
            if include_targets:
                targets = {
                    'technical_score': report.get('scores', {}).get('technical'),
                    'fundamental_score': report.get('scores', {}).get('fundamental'),
                    'overall_score': report.get('scores', {}).get('overall'),
                    'recommendation': report.get('recommendation'),
                    'recommendation_confidence': report.get('recommendation_confidence')
                }
                
                # Prediction targets
                predictions = report.get('predictions', {})
                if predictions:
                    targets['predicted_change'] = predictions.get('overall_predicted_change')
                    targets['predicted_direction'] = predictions.get('overall_direction')
                    targets['prediction_confidence'] = predictions.get('overall_confidence')
                
                sample['targets'] = targets
            
            training_data['samples'].append(sample)
        
        # Export training data
        with open(filepath, 'w') as f:
            json.dump(training_data, f, indent=2, default=str)
        
        print(f"Exported {len(reports)} training samples to {filepath}")
        return str(filepath)
    
    def export_historical_predictions(
        self,
        symbol: str,
        predictions: List[Dict],
        filename: Optional[str] = None
    ) -> str:
        """Export historical predictions for a stock.
        
        Args:
            symbol: Stock ticker symbol
            predictions: List of prediction dictionaries
            filename: Optional custom filename
            
        Returns:
            Path to exported JSON file
        """
        if not predictions:
            raise ValueError("Predictions list is required")
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if not filename:
            filename = f"{symbol}_predictions_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.export_path / filename
        
        # Prepare export data
        export_data = {
            'symbol': symbol,
            'export_date': datetime.utcnow().isoformat(),
            'num_predictions': len(predictions),
            'predictions': predictions
        }
        
        # Export
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"Exported {len(predictions)} predictions for {symbol} to {filepath}")
        return str(filepath)

