"""Fundamental analysis engine."""

from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Stock, FundamentalData
from config import get_settings


class FundamentalAnalyzer:
    """Performs fundamental analysis on stock data."""
    
    def __init__(self, db_session: Session):
        """Initialize fundamental analyzer."""
        self.db = db_session
        self.settings = get_settings()
    
    def analyze_fundamentals(self, symbol: str) -> Optional[Dict]:
        """Analyze fundamental data for a stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with fundamental analysis scores and metrics
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return None
        
        # Get latest fundamental data
        fundamental = (
            self.db.query(FundamentalData)
            .filter(FundamentalData.stock_id == stock.id)
            .order_by(FundamentalData.fiscal_year.desc())
            .first()
        )
        
        if not fundamental:
            return None
        
        # Calculate scores
        analysis = {
            'symbol': symbol,
            'valuation_score': self._calculate_valuation_score(fundamental),
            'financial_health_score': self._calculate_financial_health_score(fundamental),
            'growth_score': self._calculate_growth_score(fundamental),
            'profitability_score': self._calculate_profitability_score(fundamental),
            'overall_score': 0,
            'metrics': self._extract_metrics(fundamental)
        }
        
        # Calculate overall score (weighted average)
        scores = [
            analysis['valuation_score'],
            analysis['financial_health_score'],
            analysis['growth_score'],
            analysis['profitability_score']
        ]
        valid_scores = [s for s in scores if s is not None]
        
        if valid_scores:
            analysis['overall_score'] = sum(valid_scores) / len(valid_scores)
        else:
            analysis['overall_score'] = None
        
        return analysis
    
    def _calculate_valuation_score(self, fundamental: FundamentalData) -> Optional[float]:
        """Calculate valuation score (0-100)."""
        score = 50.0  # Neutral baseline
        factors = []
        
        # P/E ratio analysis
        if fundamental.pe_ratio:
            pe = float(fundamental.pe_ratio)
            # Lower P/E is generally better (value)
            if pe < 15:
                score += 15
                factors.append("Low P/E ratio")
            elif pe < 25:
                score += 5
                factors.append("Moderate P/E ratio")
            elif pe > 30:
                score -= 15
                factors.append("High P/E ratio")
        
        # P/B ratio analysis
        if fundamental.pb_ratio:
            pb = float(fundamental.pb_ratio)
            # Lower P/B is generally better
            if pb < 1:
                score += 10
                factors.append("Undervalued by book value")
            elif pb > 3:
                score -= 10
                factors.append("Overvalued by book value")
        
        # EV/EBITDA analysis
        if fundamental.ev_ebitda:
            ev_ebitda = float(fundamental.ev_ebitda)
            if ev_ebitda < 10:
                score += 10
                factors.append("Low EV/EBITDA")
            elif ev_ebitda > 20:
                score -= 10
                factors.append("High EV/EBITDA")
        
        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        return score
    
    def _calculate_financial_health_score(self, fundamental: FundamentalData) -> Optional[float]:
        """Calculate financial health score (0-100)."""
        score = 50.0  # Neutral baseline
        factors = []
        
        # Current ratio (liquidity)
        if fundamental.current_ratio:
            cr = float(fundamental.current_ratio)
            if cr > 2:
                score += 15
                factors.append("Strong liquidity")
            elif cr < 1:
                score -= 20
                factors.append("Weak liquidity")
        
        # Debt to equity ratio
        if fundamental.debt_to_equity:
            dte = float(fundamental.debt_to_equity)
            if dte < 0.5:
                score += 15
                factors.append("Low debt")
            elif dte > 2:
                score -= 20
                factors.append("High debt")
        
        # Quick ratio
        if fundamental.quick_ratio:
            qr = float(fundamental.quick_ratio)
            if qr > 1:
                score += 10
                factors.append("Good quick ratio")
            elif qr < 0.5:
                score -= 15
                factors.append("Poor quick ratio")
        
        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        return score
    
    def _calculate_growth_score(self, fundamental: FundamentalData) -> Optional[float]:
        """Calculate growth score (0-100)."""
        score = 50.0  # Neutral baseline
        
        # Revenue growth
        if fundamental.revenue_growth:
            rg = float(fundamental.revenue_growth)
            if rg > 20:
                score += 20
            elif rg > 10:
                score += 10
            elif rg < 0:
                score -= 15
        
        # Earnings growth
        if fundamental.earnings_growth:
            eg = float(fundamental.earnings_growth)
            if eg > 25:
                score += 20
            elif eg > 10:
                score += 10
            elif eg < 0:
                score -= 15
        
        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        return score
    
    def _calculate_profitability_score(self, fundamental: FundamentalData) -> Optional[float]:
        """Calculate profitability score (0-100)."""
        score = 50.0  # Neutral baseline
        
        # ROE (Return on Equity)
        if fundamental.roe:
            roe = float(fundamental.roe)
            if roe > 20:
                score += 20
            elif roe > 10:
                score += 10
            elif roe < 5:
                score -= 15
        
        # ROA (Return on Assets)
        if fundamental.roa:
            roa = float(fundamental.roa)
            if roa > 10:
                score += 15
            elif roa > 5:
                score += 5
            elif roa < 0:
                score -= 20
        
        # Profit margin
        if fundamental.profit_margin:
            pm = float(fundamental.profit_margin)
            if pm > 20:
                score += 15
            elif pm > 10:
                score += 5
            elif pm < 0:
                score -= 20
        
        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        return score
    
    def _extract_metrics(self, fundamental: FundamentalData) -> Dict:
        """Extract fundamental metrics."""
        return {
            'market_cap': int(fundamental.market_cap) if fundamental.market_cap else None,
            'pe_ratio': float(fundamental.pe_ratio) if fundamental.pe_ratio else None,
            'pb_ratio': float(fundamental.pb_ratio) if fundamental.pb_ratio else None,
            'ev_ebitda': float(fundamental.ev_ebitda) if fundamental.ev_ebitda else None,
            'current_ratio': float(fundamental.current_ratio) if fundamental.current_ratio else None,
            'debt_to_equity': float(fundamental.debt_to_equity) if fundamental.debt_to_equity else None,
            'quick_ratio': float(fundamental.quick_ratio) if fundamental.quick_ratio else None,
            'revenue_growth': float(fundamental.revenue_growth) if fundamental.revenue_growth else None,
            'earnings_growth': float(fundamental.earnings_growth) if fundamental.earnings_growth else None,
            'roe': float(fundamental.roe) if fundamental.roe else None,
            'roa': float(fundamental.roa) if fundamental.roa else None,
            'profit_margin': float(fundamental.profit_margin) if fundamental.profit_margin else None,
            'revenue': int(fundamental.revenue) if fundamental.revenue else None,
            'earnings': int(fundamental.earnings) if fundamental.earnings else None,
            'assets': int(fundamental.assets) if fundamental.assets else None,
            'liabilities': int(fundamental.liabilities) if fundamental.liabilities else None,
            'equity': int(fundamental.equity) if fundamental.equity else None,
            'cash': int(fundamental.cash) if fundamental.cash else None,
            'debt': int(fundamental.debt) if fundamental.debt else None,
            'fiscal_year': fundamental.fiscal_year,
            'fiscal_quarter': fundamental.fiscal_quarter,
            'report_date': fundamental.report_date.isoformat() if fundamental.report_date else None
        }

