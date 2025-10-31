"""Generate comprehensive analysis reports."""

from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_

from database.models import Stock, StockPrice, TechnicalIndicator, FundamentalData, Prediction, AnalysisReport
from analysis.technical import TechnicalAnalyzer
from analysis.fundamental import FundamentalAnalyzer
from ml.prediction import PredictionGenerator
from config import get_settings


class ReportGenerator:
    """Generates comprehensive analysis reports."""
    
    def __init__(self, db_session: Session):
        """Initialize report generator."""
        self.db = db_session
        self.settings = get_settings()
        self.technical_analyzer = TechnicalAnalyzer(db_session)
        self.fundamental_analyzer = FundamentalAnalyzer(db_session)
        self.prediction_generator = PredictionGenerator(db_session)
    
    def generate_report(
        self,
        symbol: str,
        calculate_indicators: bool = True,
        calculate_fundamentals: bool = True,
        generate_predictions: bool = True,
        save_to_db: bool = True
    ) -> Optional[Dict]:
        """Generate comprehensive analysis report for a stock.
        
        Args:
            symbol: Stock ticker symbol
            calculate_indicators: Calculate technical indicators if missing (default: True)
            calculate_fundamentals: Calculate fundamental analysis if missing (default: True)
            generate_predictions: Generate ML predictions (default: True)
            save_to_db: Save report to database (default: True)
            
        Returns:
            Dictionary with complete analysis report, or None if stock not found
        """
        # Get stock
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            print(f"Stock {symbol} not found in database.")
            return None
        
        print(f"Generating analysis report for {symbol}...")
        
        # Get latest price
        from data_fetch.price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher(self.db)
        latest_price = price_fetcher.get_latest_price(symbol)
        
        if not latest_price:
            print(f"No price data available for {symbol}")
            return None
        
        current_price = float(latest_price.close)
        
        # Technical Analysis
        technical_data = None
        if self.settings.TECHNICAL_INDICATORS:
            if calculate_indicators:
                self.technical_analyzer.calculate_indicators(symbol)
            
            latest_indicators = self.technical_analyzer.get_latest_indicators(symbol)
            technical_data = self._extract_technical_data(latest_indicators, current_price)
            technical_score = self._calculate_technical_score(technical_data)
        else:
            technical_score = None
        
        # Fundamental Analysis
        fundamental_data = None
        fundamental_score = None
        if self.settings.FUNDAMENTAL_ANALYSIS:
            fundamental_analysis = self.fundamental_analyzer.analyze_fundamentals(symbol)
            if fundamental_analysis:
                fundamental_data = fundamental_analysis.get('metrics', {})
                fundamental_score = fundamental_analysis.get('overall_score')
        
        # ML Predictions
        prediction_data = None
        if self.settings.ML_PREDICTIONS and generate_predictions:
            predictions = self.prediction_generator.generate_predictions(
                symbol, 
                horizons=self.settings.PREDICTION_HORIZONS,
                save_to_db=True
            )
            prediction_data = self._process_predictions(predictions, current_price)
        
        # Calculate overall score
        scores = []
        if technical_score is not None:
            scores.append(technical_score * 0.5)  # 50% weight
        if fundamental_score is not None:
            scores.append(fundamental_score * 0.3)  # 30% weight
        if prediction_data and prediction_data.get('overall_confidence'):
            # Use prediction confidence as score component (20% weight)
            pred_score = (prediction_data['overall_confidence'] / 100) * 100
            scores.append(pred_score * 0.2)
        
        overall_score = sum(scores) / len(scores) if scores else None
        
        # Generate recommendations
        recommendation, recommendation_confidence = self._generate_recommendation(
            technical_score, fundamental_score, prediction_data, overall_score
        )
        
        # Risk assessment
        risk_assessment = self._assess_risk(technical_data, fundamental_data, prediction_data)
        
        # Generate summaries
        summaries = self._generate_summaries(
            symbol, technical_data, fundamental_data, prediction_data, recommendation, risk_assessment
        )
        
        # Build report
        report = {
            'symbol': symbol,
            'stock_name': stock.name,
            'current_price': current_price,
            'report_date': datetime.utcnow().isoformat(),
            'scores': {
                'technical': technical_score,
                'fundamental': fundamental_score,
                'overall': overall_score
            },
            'recommendation': recommendation,
            'recommendation_confidence': recommendation_confidence,
            'risk_assessment': risk_assessment,
            'technical_analysis': technical_data,
            'fundamental_analysis': fundamental_data,
            'predictions': prediction_data,
            'summaries': summaries
        }
        
        # Save to database
        if save_to_db:
            self._save_report(stock.id, report)
        
        return report
    
    def _extract_technical_data(self, indicators: Optional[TechnicalIndicator], current_price: float) -> Dict:
        """Extract technical data from indicators."""
        if not indicators:
            return {}
        
        return {
            'rsi': float(indicators.rsi) if indicators.rsi else None,
            'macd': float(indicators.macd) if indicators.macd else None,
            'macd_signal': float(indicators.macd_signal) if indicators.macd_signal else None,
            'macd_histogram': float(indicators.macd_histogram) if indicators.macd_histogram else None,
            'sma_20': float(indicators.sma_20) if indicators.sma_20 else None,
            'sma_50': float(indicators.sma_50) if indicators.sma_50 else None,
            'sma_200': float(indicators.sma_200) if indicators.sma_200 else None,
            'bollinger_upper': float(indicators.bollinger_upper) if indicators.bollinger_upper else None,
            'bollinger_middle': float(indicators.bollinger_middle) if indicators.bollinger_middle else None,
            'bollinger_lower': float(indicators.bollinger_lower) if indicators.bollinger_lower else None,
            'atr': float(indicators.atr) if indicators.atr else None,
            'support_level': float(indicators.support_level) if indicators.support_level else None,
            'resistance_level': float(indicators.resistance_level) if indicators.resistance_level else None,
            'price_vs_sma20': (current_price / float(indicators.sma_20) - 1) * 100 if indicators.sma_20 else None,
            'price_vs_sma50': (current_price / float(indicators.sma_50) - 1) * 100 if indicators.sma_50 else None,
            'price_vs_sma200': (current_price / float(indicators.sma_200) - 1) * 100 if indicators.sma_200 else None,
            'timestamp': indicators.timestamp.isoformat() if indicators.timestamp else None
        }
    
    def _calculate_technical_score(self, technical_data: Dict) -> float:
        """Calculate technical score (0-100)."""
        if not technical_data:
            return 50.0  # Neutral
        
        score = 50.0  # Neutral baseline
        factors = []
        
        # RSI analysis
        rsi = technical_data.get('rsi')
        if rsi:
            if rsi < 30:
                score += 15  # Oversold, potential buy
                factors.append("Oversold (RSI < 30)")
            elif rsi > 70:
                score -= 15  # Overbought, potential sell
                factors.append("Overbought (RSI > 70)")
            elif 40 < rsi < 60:
                score += 5  # Neutral, healthy
                factors.append("Neutral RSI")
        
        # MACD analysis
        macd_histogram = technical_data.get('macd_histogram')
        if macd_histogram:
            if macd_histogram > 0:
                score += 10  # Bullish momentum
                factors.append("MACD bullish")
            else:
                score -= 5  # Bearish momentum
                factors.append("MACD bearish")
        
        # Price vs Moving Averages
        price_vs_sma20 = technical_data.get('price_vs_sma20')
        if price_vs_sma20:
            if price_vs_sma20 > 5:
                score += 10  # Above short-term MA
                factors.append("Above SMA 20")
            elif price_vs_sma20 < -5:
                score -= 10  # Below short-term MA
                factors.append("Below SMA 20")
        
        price_vs_sma50 = technical_data.get('price_vs_sma50')
        if price_vs_sma50:
            if price_vs_sma50 > 0:
                score += 5  # Above medium-term MA
            elif price_vs_sma50 < -10:
                score -= 10  # Well below medium-term MA
        
        price_vs_sma200 = technical_data.get('price_vs_sma200')
        if price_vs_sma200:
            if price_vs_sma200 > 0:
                score += 5  # Above long-term MA (bullish trend)
            elif price_vs_sma200 < -20:
                score -= 15  # Well below long-term MA (bearish trend)
        
        # Bollinger Bands
        bollinger_lower = technical_data.get('bollinger_lower')
        bollinger_upper = technical_data.get('bollinger_upper')
        current_price = technical_data.get('current_price', 0)
        if bollinger_lower and bollinger_upper and current_price:
            bb_position = (current_price - bollinger_lower) / (bollinger_upper - bollinger_lower)
            if bb_position < 0.2:
                score += 10  # Near lower band (potential bounce)
                factors.append("Near Bollinger lower band")
            elif bb_position > 0.8:
                score -= 10  # Near upper band (potential reversal)
                factors.append("Near Bollinger upper band")
        
        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        
        return score
    
    def _process_predictions(self, predictions: Dict, current_price: float) -> Dict:
        """Process ML predictions."""
        if not predictions:
            return {}
        
        all_pred_changes = []
        all_confidences = []
        directions = []
        
        for model_type, model_preds in predictions.items():
            if 'error' in model_preds:
                continue
            
            for horizon, pred_data in model_preds.items():
                if 'error' in pred_data:
                    continue
                
                all_pred_changes.append(pred_data.get('predicted_change', 0))
                all_confidences.append(pred_data.get('confidence_score', 0))
                directions.append(pred_data.get('predicted_direction', 'neutral'))
        
        if not all_pred_changes:
            return {}
        
        # Average predictions
        avg_change = sum(all_pred_changes) / len(all_pred_changes)
        avg_confidence = sum(all_confidences) / len(all_confidences)
        
        # Determine overall direction
        bullish_count = directions.count('bullish')
        bearish_count = directions.count('bearish')
        neutral_count = directions.count('neutral')
        
        if bullish_count > bearish_count and bullish_count > neutral_count:
            overall_direction = 'bullish'
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            overall_direction = 'bearish'
        else:
            overall_direction = 'neutral'
        
        return {
            'overall_predicted_change': avg_change,
            'overall_confidence': avg_confidence,
            'overall_direction': overall_direction,
            'num_predictions': len(all_pred_changes),
            'detailed_predictions': predictions
        }
    
    def _generate_recommendation(
        self,
        technical_score: Optional[float],
        fundamental_score: Optional[float],
        prediction_data: Optional[Dict],
        overall_score: Optional[float]
    ) -> tuple:
        """Generate trading recommendation."""
        if overall_score is None:
            return 'HOLD', 50.0
        
        # Determine recommendation based on overall score
        if overall_score >= 70:
            recommendation = 'BUY'
            confidence = overall_score
        elif overall_score <= 30:
            recommendation = 'SELL'
            confidence = 100 - overall_score
        else:
            recommendation = 'HOLD'
            confidence = 50.0
        
        return recommendation, float(confidence)
    
    def _assess_risk(
        self,
        technical_data: Optional[Dict],
        fundamental_data: Optional[Dict],
        prediction_data: Optional[Dict]
    ) -> Dict:
        """Assess risk level."""
        risk_factors = []
        volatility_score = 50.0  # Neutral
        
        # Technical risk factors
        if technical_data:
            atr = technical_data.get('atr')
            if atr:
                volatility_score += (atr / 10) * 10  # Scale ATR to volatility score
        
        # Fundamental risk factors
        if fundamental_data:
            debt_to_equity = fundamental_data.get('debt_to_equity')
            if debt_to_equity and debt_to_equity > 2:
                risk_factors.append("High debt-to-equity ratio")
                volatility_score += 15
        
        # Prediction confidence
        if prediction_data:
            confidence = prediction_data.get('overall_confidence', 0)
            if confidence < 50:
                risk_factors.append("Low prediction confidence")
                volatility_score += 10
        
        # Determine risk level
        if volatility_score > 70:
            risk_level = 'HIGH'
        elif volatility_score < 30:
            risk_level = 'LOW'
        else:
            risk_level = 'MEDIUM'
        
        return {
            'risk_level': risk_level,
            'volatility_score': float(volatility_score),
            'drawdown_potential': float(min(50, volatility_score)),  # Estimate
            'risk_factors': risk_factors
        }
    
    def _generate_summaries(
        self,
        symbol: str,
        technical_data: Optional[Dict],
        fundamental_data: Optional[Dict],
        prediction_data: Optional[Dict],
        recommendation: str,
        risk_assessment: Dict
    ) -> Dict:
        """Generate text summaries."""
        summaries = {}
        
        # Technical summary
        if technical_data:
            tech_summary = f"Technical indicators for {symbol}: "
            rsi = technical_data.get('rsi')
            if rsi:
                if rsi < 30:
                    tech_summary += "RSI indicates oversold conditions. "
                elif rsi > 70:
                    tech_summary += "RSI indicates overbought conditions. "
            
            macd_hist = technical_data.get('macd_histogram')
            if macd_hist and macd_hist > 0:
                tech_summary += "MACD shows bullish momentum. "
            
            price_vs_sma200 = technical_data.get('price_vs_sma200')
            if price_vs_sma200:
                if price_vs_sma200 > 0:
                    tech_summary += "Price is above long-term moving average (bullish trend). "
                else:
                    tech_summary += "Price is below long-term moving average (bearish trend). "
            
            summaries['technical'] = tech_summary.strip()
        else:
            summaries['technical'] = "Technical analysis data not available."
        
        # Fundamental summary
        if fundamental_data:
            fund_summary = f"Fundamental analysis for {symbol}: "
            pe_ratio = fundamental_data.get('pe_ratio')
            if pe_ratio:
                if pe_ratio < 15:
                    fund_summary += "Valuation appears attractive (low P/E). "
                elif pe_ratio > 30:
                    fund_summary += "Valuation appears expensive (high P/E). "
            
            roe = fundamental_data.get('roe')
            if roe and roe > 20:
                fund_summary += "Strong return on equity. "
            
            summaries['fundamental'] = fund_summary.strip()
        else:
            summaries['fundamental'] = "Fundamental analysis data not available."
        
        # Prediction summary
        if prediction_data:
            pred_change = prediction_data.get('overall_predicted_change', 0)
            direction = prediction_data.get('overall_direction', 'neutral')
            confidence = prediction_data.get('overall_confidence', 0)
            
            pred_summary = f"ML predictions for {symbol}: "
            pred_summary += f"Model suggests {direction} movement with {pred_change:.2f}% expected change. "
            pred_summary += f"Confidence: {confidence:.1f}%. "
            
            summaries['prediction'] = pred_summary.strip()
        else:
            summaries['prediction'] = "ML predictions not available."
        
        # Overall summary
        overall_summary = f"Overall analysis for {symbol}: "
        overall_summary += f"Recommendation: {recommendation}. "
        overall_summary += f"Risk level: {risk_assessment.get('risk_level', 'MEDIUM')}. "
        overall_summary += f"{summaries.get('technical', '')} {summaries.get('fundamental', '')} {summaries.get('prediction', '')}"
        
        summaries['overall'] = overall_summary.strip()
        
        return summaries
    
    def _save_report(self, stock_id: int, report: Dict):
        """Save report to database."""
        import json
        
        report_date = datetime.fromisoformat(report['report_date'])
        
        # Check if report already exists
        existing = (
            self.db.query(AnalysisReport)
            .filter(
                and_(
                    AnalysisReport.stock_id == stock_id,
                    AnalysisReport.report_date >= report_date - timedelta(hours=1)
                )
            )
            .first()
        )
        
        # Prepare payload
        scores = report.get('scores', {})
        risk = report.get('risk_assessment', {})
        summaries = report.get('summaries', {})

        payload = {
            'stock_id': stock_id,
            'report_date': report_date,
            'technical_score': scores.get('technical'),
            'fundamental_score': scores.get('fundamental'),
            'overall_score': scores.get('overall'),
            'recommendation': report.get('recommendation'),
            'recommendation_confidence': report.get('recommendation_confidence'),
            'risk_level': risk.get('risk_level'),
            'volatility_score': risk.get('volatility_score'),
            'drawdown_potential': risk.get('drawdown_potential'),
            'technical_summary': summaries.get('technical'),
            'fundamental_summary': summaries.get('fundamental'),
            'prediction_summary': summaries.get('prediction'),
            'overall_summary': summaries.get('overall'),
            'technical_data': json.dumps(report.get('technical_analysis', {})),
            'fundamental_data': json.dumps(report.get('fundamental_analysis', {})),
            'prediction_data': json.dumps(report.get('predictions', {})),
        }

        stmt = (
            insert(AnalysisReport)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=[AnalysisReport.stock_id, AnalysisReport.report_date],
                set_={k: payload[k] for k in payload if k not in ('stock_id', 'report_date')}
            )
        )
        self.db.execute(stmt)
        self.db.commit()

