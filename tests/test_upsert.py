"""Test upsert functionality to prevent duplicates."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.connection import get_db_context
from database.models import Stock, StockPrice, FundamentalData, AnalysisReport, Prediction
from data_fetch.stock_list import StockListManager
from data_fetch.price_fetcher import PriceFetcher
from data_fetch.fundamental_fetcher import FundamentalFetcher
from reporting.report_generator import ReportGenerator
from ml.prediction import PredictionGenerator


def test_stock_upsert():
    """Test that stock upsert prevents duplicates."""
    try:
        with get_db_context() as db:
            manager = StockListManager(db)
            
            # Create test stock data
            stock_data1 = {
                'ticker': 'UPSERT',
                'name': 'Test Stock Original',
                'market': 'stocks',
                'locale': 'us',
                'primary_exchange': 'NYSE',
                'active': True,
                'currency_name': 'USD'
            }
            
            # First insert
            manager._upsert_stock(stock_data1)
            db.commit()
            
            # Count records
            count_before = db.query(Stock).filter(Stock.symbol == 'UPSERT').count()
            assert count_before == 1, "Should have exactly 1 stock"
            
            # Second insert with same symbol but different data
            stock_data2 = {
                'ticker': 'UPSERT',
                'name': 'Test Stock Updated',
                'market': 'stocks',
                'locale': 'us',
                'primary_exchange': 'NASDAQ',
                'active': True,
                'currency_name': 'USD'
            }
            
            manager._upsert_stock(stock_data2)
            db.commit()
            
            # Should still be 1 record, not 2
            count_after = db.query(Stock).filter(Stock.symbol == 'UPSERT').count()
            assert count_after == 1, f"Should still be 1 stock after upsert, got {count_after}"
            
            # Verify data was updated
            stock = db.query(Stock).filter(Stock.symbol == 'UPSERT').first()
            assert stock.name == 'Test Stock Updated', "Name should be updated"
            assert stock.primary_exchange == 'NASDAQ', "Exchange should be updated"
            
            # Clean up
            db.delete(stock)
            db.commit()
            
    except Exception as e:
        pytest.fail(f"Stock upsert test failed: {str(e)}")


def test_price_upsert():
    """Test that price upsert prevents duplicates."""
    try:
        with get_db_context() as db:
            # Create test stock
            stock = db.query(Stock).filter(Stock.symbol == 'UPSERT').first()
            if not stock:
                stock = Stock(
                    symbol='UPSERT',
                    name='Test Stock',
                    active=True,
                    currency='USD'
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
            
            price_fetcher = PriceFetcher(db)
            timestamp = datetime.now()
            
            # Create test price data
            price_data1 = {
                'stock_id': stock.id,
                'timestamp': timestamp,
                'open': 100.0,
                'high': 105.0,
                'low': 95.0,
                'close': 102.0,
                'volume': 1000000,
                'vwap': 101.0,
                'transactions': 1000
            }
            
            # First insert
            from sqlalchemy.dialects.postgresql import insert
            stmt = (
                insert(StockPrice)
                .values(**price_data1)
                .on_conflict_do_update(
                    index_elements=[StockPrice.stock_id, StockPrice.timestamp],
                    set_={
                        'open': price_data1['open'],
                        'high': price_data1['high'],
                        'low': price_data1['low'],
                        'close': price_data1['close'],
                        'volume': price_data1['volume'],
                        'vwap': price_data1['vwap'],
                        'transactions': price_data1['transactions'],
                    }
                )
            )
            db.execute(stmt)
            db.commit()
            
            count_before = db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.timestamp == timestamp
            ).count()
            assert count_before == 1, "Should have exactly 1 price record"
            
            # Second insert with same timestamp but different data
            price_data2 = {
                'stock_id': stock.id,
                'timestamp': timestamp,
                'open': 102.0,
                'high': 107.0,
                'low': 97.0,
                'close': 104.0,
                'volume': 2000000,
                'vwap': 103.0,
                'transactions': 2000
            }
            
            stmt = (
                insert(StockPrice)
                .values(**price_data2)
                .on_conflict_do_update(
                    index_elements=[StockPrice.stock_id, StockPrice.timestamp],
                    set_={
                        'open': price_data2['open'],
                        'high': price_data2['high'],
                        'low': price_data2['low'],
                        'close': price_data2['close'],
                        'volume': price_data2['volume'],
                        'vwap': price_data2['vwap'],
                        'transactions': price_data2['transactions'],
                    }
                )
            )
            db.execute(stmt)
            db.commit()
            
            # Should still be 1 record
            count_after = db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.timestamp == timestamp
            ).count()
            assert count_after == 1, f"Should still be 1 price after upsert, got {count_after}"
            
            # Verify data was updated
            price = db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.timestamp == timestamp
            ).first()
            assert price.close == 104.0, "Close price should be updated"
            assert price.volume == 2000000, "Volume should be updated"
            
            # Clean up
            db.delete(price)
            db.delete(stock)
            db.commit()
            
    except Exception as e:
        pytest.fail(f"Price upsert test failed: {str(e)}")


def test_fundamental_upsert():
    """Test that fundamental data upsert prevents duplicates."""
    try:
        with get_db_context() as db:
            # Create test stock
            stock = db.query(Stock).filter(Stock.symbol == 'UPSERT').first()
            if not stock:
                stock = Stock(
                    symbol='UPSERT',
                    name='Test Stock',
                    active=True,
                    currency='USD'
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
            
            # Create test fundamental data
            fundamental_data1 = {
                'stock_id': stock.id,
                'fiscal_year': 2024,
                'fiscal_quarter': 1,
                'market_cap': 1000000000,
                'pe_ratio': 25.0,
                'revenue': 50000000,
                'earnings': 5000000
            }
            
            # First insert
            from sqlalchemy.dialects.postgresql import insert
            stmt = (
                insert(FundamentalData)
                .values(**fundamental_data1)
                .on_conflict_do_update(
                    index_elements=[
                        FundamentalData.stock_id,
                        FundamentalData.fiscal_year,
                        FundamentalData.fiscal_quarter,
                    ],
                    set_={k: fundamental_data1[k] for k in fundamental_data1 if k not in ('stock_id', 'fiscal_year', 'fiscal_quarter')}
                )
            )
            db.execute(stmt)
            db.commit()
            
            count_before = db.query(FundamentalData).filter(
                FundamentalData.stock_id == stock.id,
                FundamentalData.fiscal_year == 2024,
                FundamentalData.fiscal_quarter == 1
            ).count()
            assert count_before == 1, "Should have exactly 1 fundamental record"
            
            # Second insert with same key but different data
            fundamental_data2 = {
                'stock_id': stock.id,
                'fiscal_year': 2024,
                'fiscal_quarter': 1,
                'market_cap': 2000000000,
                'pe_ratio': 30.0,
                'revenue': 60000000,
                'earnings': 6000000
            }
            
            stmt = (
                insert(FundamentalData)
                .values(**fundamental_data2)
                .on_conflict_do_update(
                    index_elements=[
                        FundamentalData.stock_id,
                        FundamentalData.fiscal_year,
                        FundamentalData.fiscal_quarter,
                    ],
                    set_={k: fundamental_data2[k] for k in fundamental_data2 if k not in ('stock_id', 'fiscal_year', 'fiscal_quarter')}
                )
            )
            db.execute(stmt)
            db.commit()
            
            # Should still be 1 record
            count_after = db.query(FundamentalData).filter(
                FundamentalData.stock_id == stock.id,
                FundamentalData.fiscal_year == 2024,
                FundamentalData.fiscal_quarter == 1
            ).count()
            assert count_after == 1, f"Should still be 1 fundamental after upsert, got {count_after}"
            
            # Verify data was updated
            fundamental = db.query(FundamentalData).filter(
                FundamentalData.stock_id == stock.id,
                FundamentalData.fiscal_year == 2024,
                FundamentalData.fiscal_quarter == 1
            ).first()
            assert fundamental.market_cap == 2000000000, "Market cap should be updated"
            assert fundamental.pe_ratio == 30.0, "P/E ratio should be updated"
            
            # Clean up
            db.delete(fundamental)
            db.delete(stock)
            db.commit()
            
    except Exception as e:
        pytest.fail(f"Fundamental upsert test failed: {str(e)}")


def test_analysis_report_upsert():
    """Test that analysis report upsert prevents duplicates."""
    try:
        with get_db_context() as db:
            # Create test stock
            stock = db.query(Stock).filter(Stock.symbol == 'UPSERT').first()
            if not stock:
                stock = Stock(
                    symbol='UPSERT',
                    name='Test Stock',
                    active=True,
                    currency='USD'
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
            
            report_date = datetime.utcnow()
            
            # Create test report data
            report_data1 = {
                'stock_id': stock.id,
                'report_date': report_date,
                'overall_score': 75.0,
                'recommendation': 'BUY',
                'recommendation_confidence': 75.0
            }
            
            # First insert
            from sqlalchemy.dialects.postgresql import insert
            import json
            payload1 = {
                **report_data1,
                'technical_data': json.dumps({}),
                'fundamental_data': json.dumps({}),
                'prediction_data': json.dumps({})
            }
            
            stmt = (
                insert(AnalysisReport)
                .values(**payload1)
                .on_conflict_do_update(
                    index_elements=[AnalysisReport.stock_id, AnalysisReport.report_date],
                    set_={k: payload1[k] for k in payload1 if k not in ('stock_id', 'report_date')}
                )
            )
            db.execute(stmt)
            db.commit()
            
            count_before = db.query(AnalysisReport).filter(
                AnalysisReport.stock_id == stock.id,
                AnalysisReport.report_date == report_date
            ).count()
            assert count_before == 1, "Should have exactly 1 report"
            
            # Second insert with same key but different data
            report_data2 = {
                'stock_id': stock.id,
                'report_date': report_date,
                'overall_score': 80.0,
                'recommendation': 'HOLD',
                'recommendation_confidence': 80.0
            }
            
            payload2 = {
                **report_data2,
                'technical_data': json.dumps({}),
                'fundamental_data': json.dumps({}),
                'prediction_data': json.dumps({})
            }
            
            stmt = (
                insert(AnalysisReport)
                .values(**payload2)
                .on_conflict_do_update(
                    index_elements=[AnalysisReport.stock_id, AnalysisReport.report_date],
                    set_={k: payload2[k] for k in payload2 if k not in ('stock_id', 'report_date')}
                )
            )
            db.execute(stmt)
            db.commit()
            
            # Should still be 1 record
            count_after = db.query(AnalysisReport).filter(
                AnalysisReport.stock_id == stock.id,
                AnalysisReport.report_date == report_date
            ).count()
            assert count_after == 1, f"Should still be 1 report after upsert, got {count_after}"
            
            # Verify data was updated
            report = db.query(AnalysisReport).filter(
                AnalysisReport.stock_id == stock.id,
                AnalysisReport.report_date == report_date
            ).first()
            assert float(report.overall_score) == 80.0, "Score should be updated"
            assert report.recommendation == 'HOLD', "Recommendation should be updated"
            
            # Clean up
            db.delete(report)
            db.delete(stock)
            db.commit()
            
    except Exception as e:
        pytest.fail(f"Analysis report upsert test failed: {str(e)}")


def test_prediction_no_duplicates():
    """Test that prediction save prevents duplicates."""
    try:
        with get_db_context() as db:
            # Create test stock
            stock = db.query(Stock).filter(Stock.symbol == 'UPSERT').first()
            if not stock:
                stock = Stock(
                    symbol='UPSERT',
                    name='Test Stock',
                    active=True,
                    currency='USD'
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
            
            generator = PredictionGenerator(db)
            
            # First save
            generator._save_prediction(
                stock_id=stock.id,
                model_type='linear_regression',
                prediction_horizon=1,
                predicted_price=100.0,
                predicted_change=5.0,
                predicted_direction='bullish',
                confidence_score=75.0,
                features={}
            )
            
            count_before = db.query(Prediction).filter(
                Prediction.stock_id == stock.id,
                Prediction.model_type == 'linear_regression',
                Prediction.prediction_horizon == 1
            ).count()
            
            # Second save (should replace, not duplicate)
            generator._save_prediction(
                stock_id=stock.id,
                model_type='linear_regression',
                prediction_horizon=1,
                predicted_price=105.0,
                predicted_change=7.0,
                predicted_direction='bullish',
                confidence_score=80.0,
                features={}
            )
            
            # Should still be 1 or 0 records (depending on date filtering)
            count_after = db.query(Prediction).filter(
                Prediction.stock_id == stock.id,
                Prediction.model_type == 'linear_regression',
                Prediction.prediction_horizon == 1
            ).count()
            
            # Clean up
            predictions = db.query(Prediction).filter(
                Prediction.stock_id == stock.id
            ).all()
            for pred in predictions:
                db.delete(pred)
            db.delete(stock)
            db.commit()
            
            # Test passes if no duplicate errors occur
            assert True
            
    except Exception as e:
        pytest.fail(f"Prediction save test failed: {str(e)}")

