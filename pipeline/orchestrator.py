"""Main pipeline orchestrator."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.models import Stock
from data_fetch.price_fetcher import PriceFetcher
from data_fetch.fundamental_fetcher import FundamentalFetcher
from analysis.technical import TechnicalAnalyzer
from analysis.fundamental import FundamentalAnalyzer
from ml.training import ModelTrainer
from ml.prediction import PredictionGenerator
from reporting.report_generator import ReportGenerator
from reporting.json_exporter import JSONExporter
from reporting.cli_formatter import CLIFormatter
from config import get_settings


class PipelineOrchestrator:
    """Orchestrates the complete data pipeline."""
    
    def __init__(self, db_session: Session):
        """Initialize pipeline orchestrator."""
        self.db = db_session
        self.settings = get_settings()
        
        # Initialize components
        self.price_fetcher = PriceFetcher(db_session)
        self.fundamental_fetcher = FundamentalFetcher(db_session)
        self.technical_analyzer = TechnicalAnalyzer(db_session)
        self.fundamental_analyzer = FundamentalAnalyzer(db_session)
        self.model_trainer = ModelTrainer(db_session)
        self.prediction_generator = PredictionGenerator(db_session)
        self.report_generator = ReportGenerator(db_session)
        self.json_exporter = JSONExporter()
        self.cli_formatter = CLIFormatter()
    
    def run_full_pipeline(
        self,
        symbols: Optional[List[str]] = None,
        limit: Optional[int] = None,
        fetch_data: bool = True,
        calculate_indicators: bool = True,
        analyze_fundamentals: bool = True,
        train_models: bool = True,
        generate_predictions: bool = True,
        generate_reports: bool = True,
        export_json: bool = True,
        display_cli: bool = True
    ) -> Dict[str, Dict]:
        """Run the complete pipeline for one or more stocks.
        
        Args:
            symbols: List of stock symbols to process (None = all active stocks)
            limit: Maximum number of stocks to process (default: None)
            fetch_data: Fetch price and fundamental data (default: True)
            calculate_indicators: Calculate technical indicators (default: True)
            analyze_fundamentals: Perform fundamental analysis (default: True)
            train_models: Train ML models (default: True)
            generate_predictions: Generate predictions (default: True)
            generate_reports: Generate analysis reports (default: True)
            export_json: Export to JSON (default: True)
            display_cli: Display CLI output (default: True)
            
        Returns:
            Dictionary mapping symbol to results
        """
        # Get stocks to process
        if symbols:
            stocks = [self.db.query(Stock).filter(Stock.symbol == s.upper()).first() for s in symbols]
            stocks = [s for s in stocks if s]
        else:
            query = self.db.query(Stock).filter(Stock.active == True)
            if limit:
                query = query.limit(limit)
            stocks = query.all()
        
        if not stocks:
            print("No stocks found to process.")
            return {}
        
        print(f"Processing {len(stocks)} stocks...")
        
        results = {}
        reports = []
        
        for i, stock in enumerate(stocks, 1):
            symbol = stock.symbol
            print(f"\n[{i}/{len(stocks)}] Processing {symbol}...")
            
            try:
                result = self._process_stock(
                    symbol,
                    fetch_data=fetch_data,
                    calculate_indicators=calculate_indicators,
                    analyze_fundamentals=analyze_fundamentals,
                    train_models=train_models,
                    generate_predictions=generate_predictions,
                    generate_reports=generate_reports,
                    export_json=export_json,
                    display_cli=display_cli
                )
                
                results[symbol] = result
                
                # Collect reports for batch export
                if generate_reports and result.get('report'):
                    reports.append(result['report'])
            
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                results[symbol] = {'error': str(e)}
                continue
        
        # Batch export if requested
        if export_json and reports:
            try:
                export_path = self.json_exporter.export_batch(reports)
                print(f"\nBatch export completed: {export_path}")
            except Exception as e:
                print(f"Error exporting batch: {str(e)}")
        
        print(f"\nPipeline completed. Processed {len(results)} stocks.")
        return results
    
    def _process_stock(
        self,
        symbol: str,
        fetch_data: bool,
        calculate_indicators: bool,
        analyze_fundamentals: bool,
        train_models: bool,
        generate_predictions: bool,
        generate_reports: bool,
        export_json: bool,
        display_cli: bool
    ) -> Dict:
        """Process a single stock through the pipeline."""
        result = {}
        
        # 1. Fetch Data
        if fetch_data:
            print(f"  Fetching price data for {symbol}...")
            price_count = self.price_fetcher.fetch_stock_prices(symbol, incremental=True)
            result['price_records_fetched'] = price_count
            
            if self.settings.FUNDAMENTAL_ANALYSIS:
                print(f"  Fetching fundamental data for {symbol}...")
                fundamental_success = self.fundamental_fetcher.fetch_fundamental_data(symbol)
                result['fundamental_data_fetched'] = fundamental_success
        
        # 2. Calculate Technical Indicators
        if calculate_indicators and self.settings.TECHNICAL_INDICATORS:
            print(f"  Calculating technical indicators for {symbol}...")
            indicator_count = self.technical_analyzer.calculate_indicators(symbol)
            result['indicators_calculated'] = indicator_count
        
        # 3. Analyze Fundamentals
        if analyze_fundamentals and self.settings.FUNDAMENTAL_ANALYSIS:
            print(f"  Analyzing fundamentals for {symbol}...")
            fundamental_analysis = self.fundamental_analyzer.analyze_fundamentals(symbol)
            result['fundamental_analysis'] = fundamental_analysis is not None
        
        # 4. Train ML Models
        models_trained_count = 0
        if train_models and self.settings.ML_PREDICTIONS:
            print(f"  Training ML models for {symbol}...")
            training_results = self.model_trainer.train_models(symbol, retrain=False)
            # Count per model_type and horizon that trained successfully
            for mt, details in training_results.items():
                if isinstance(details, dict):
                    for h, res in details.items():
                        if isinstance(res, dict) and 'error' not in res:
                            models_trained_count += 1
            result['models_trained'] = models_trained_count
        
        # 5. Generate Predictions
        if generate_predictions and self.settings.ML_PREDICTIONS and models_trained_count > 0:
            print(f"  Generating predictions for {symbol}...")
            predictions = self.prediction_generator.generate_predictions(symbol, save_to_db=True)
            result['predictions_generated'] = len(predictions)
        elif generate_predictions and self.settings.ML_PREDICTIONS:
            print(f"  Skipping predictions for {symbol}: no trained models available")
            result['predictions_generated'] = 0
        
        # 6. Generate Report
        report = None
        if generate_reports:
            print(f"  Generating report for {symbol}...")
            report = self.report_generator.generate_report(
                symbol,
                calculate_indicators=False,  # Already calculated
                calculate_fundamentals=False,  # Already calculated
                generate_predictions=False,  # Already generated
                save_to_db=True
            )
            result['report_generated'] = report is not None
        
        # 7. Export JSON
        if export_json and report:
            try:
                export_path = self.json_exporter.export_report(report)
                result['json_export_path'] = export_path
            except Exception as e:
                print(f"  Error exporting JSON: {str(e)}")
        
        # 8. Display CLI
        if display_cli and report:
            print(f"\n  Report for {symbol}:")
            self.cli_formatter.display_report(report)
        
        result['report'] = report
        result['success'] = True
        
        return result
    
    def run_incremental_update(self, days_back: int = 1) -> Dict[str, Dict]:
        """Run incremental update for recently updated stocks.
        
        Args:
            days_back: Number of days to look back for updates (default: 1)
            
        Returns:
            Dictionary mapping symbol to results
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get stocks with recent price updates
        from database.models import StockPrice
        recent_stocks = (
            self.db.query(Stock)
            .join(StockPrice)
            .filter(StockPrice.timestamp >= cutoff_date)
            .distinct()
            .all()
        )
        
        symbols = [stock.symbol for stock in recent_stocks]
        
        print(f"Running incremental update for {len(symbols)} stocks...")
        
        return self.run_full_pipeline(
            symbols=symbols,
            fetch_data=False,  # Assume data is already fetched
            calculate_indicators=True,
            analyze_fundamentals=True,
            train_models=False,  # Don't retrain on every update
            generate_predictions=True,
            generate_reports=True,
            export_json=True,
            display_cli=False  # Don't display for batch updates
        )

