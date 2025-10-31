"""CLI output formatter with tables and readable reports."""

from typing import Dict, Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from config import get_settings


class CLIFormatter:
    """Formats analysis reports for CLI display."""
    
    def __init__(self):
        """Initialize CLI formatter."""
        self.console = Console()
        self.settings = get_settings()
    
    def display_report(self, report: Dict):
        """Display complete analysis report in CLI.
        
        Args:
            report: Dictionary with analysis report
        """
        if not report:
            self.console.print("[red]No report data available.[/red]")
            return
        
        symbol = report.get('symbol', 'UNKNOWN')
        stock_name = report.get('stock_name', '')
        current_price = report.get('current_price', 0)
        
        # Header
        header_text = Text(f"Stock Analysis Report: {symbol}", style="bold cyan")
        if stock_name:
            header_text.append(f" - {stock_name}", style="dim")
        
        self.console.print(Panel(header_text, border_style="cyan", expand=False))
        self.console.print()
        
        # Current Price
        price_text = Text(f"Current Price: ${current_price:.2f}", style="bold yellow")
        self.console.print(price_text)
        self.console.print()
        
        # Scores Table
        scores = report.get('scores', {})
        scores_table = Table(title="Analysis Scores", box=box.ROUNDED, show_header=True)
        scores_table.add_column("Metric", style="cyan", width=20)
        scores_table.add_column("Score", justify="right", style="yellow")
        scores_table.add_column("Rating", justify="center")
        
        technical_score = scores.get('technical')
        if technical_score is not None:
            scores_table.add_row("Technical", f"{technical_score:.1f}/100", self._get_rating(technical_score))
        
        fundamental_score = scores.get('fundamental')
        if fundamental_score is not None:
            scores_table.add_row("Fundamental", f"{fundamental_score:.1f}/100", self._get_rating(fundamental_score))
        
        overall_score = scores.get('overall')
        if overall_score is not None:
            scores_table.add_row("Overall", f"{overall_score:.1f}/100", self._get_rating(overall_score), style="bold")
        
        self.console.print(scores_table)
        self.console.print()
        
        # Recommendation
        recommendation = report.get('recommendation', 'HOLD')
        confidence = report.get('recommendation_confidence', 0)
        
        rec_color = {
            'BUY': 'green',
            'SELL': 'red',
            'HOLD': 'yellow'
        }.get(recommendation, 'white')
        
        rec_text = Text("Recommendation: ", style="bold")
        rec_text.append(recommendation, style=f"bold {rec_color}")
        rec_text.append(f" (Confidence: {confidence:.1f}%)", style="dim")
        
        self.console.print(Panel(rec_text, border_style=rec_color, expand=False))
        self.console.print()
        
        # Risk Assessment
        risk = report.get('risk_assessment', {})
        if risk:
            risk_table = Table(title="Risk Assessment", box=box.ROUNDED, show_header=True)
            risk_table.add_column("Metric", style="cyan")
            risk_table.add_column("Value", justify="right", style="yellow")
            
            risk_level = risk.get('risk_level', 'MEDIUM')
            risk_color = {
                'LOW': 'green',
                'MEDIUM': 'yellow',
                'HIGH': 'red'
            }.get(risk_level, 'white')
            
            risk_table.add_row("Risk Level", f"[{risk_color}]{risk_level}[/{risk_color}]")
            risk_table.add_row("Volatility Score", f"{risk.get('volatility_score', 0):.1f}/100")
            risk_table.add_row("Drawdown Potential", f"{risk.get('drawdown_potential', 0):.1f}%")
            
            self.console.print(risk_table)
            self.console.print()
            
            # Risk factors
            risk_factors = risk.get('risk_factors', [])
            if risk_factors:
                factors_text = Text("Risk Factors:\n", style="bold")
                for factor in risk_factors:
                    factors_text.append(f"  • {factor}\n", style="red")
                self.console.print(Panel(factors_text, border_style="red", expand=False))
                self.console.print()
        
        # Technical Analysis
        technical = report.get('technical_analysis', {})
        if technical:
            tech_table = Table(title="Technical Indicators", box=box.ROUNDED, show_header=True)
            tech_table.add_column("Indicator", style="cyan", width=25)
            tech_table.add_column("Value", justify="right", style="yellow")
            
            if technical.get('rsi') is not None:
                rsi = technical['rsi']
                tech_table.add_row("RSI", f"{rsi:.2f}")
            
            if technical.get('macd') is not None:
                tech_table.add_row("MACD", f"{technical['macd']:.4f}")
            
            if technical.get('sma_20') is not None:
                tech_table.add_row("SMA (20)", f"${technical['sma_20']:.2f}")
            
            if technical.get('sma_50') is not None:
                tech_table.add_row("SMA (50)", f"${technical['sma_50']:.2f}")
            
            if technical.get('price_vs_sma20') is not None:
                pct = technical['price_vs_sma20']
                color = 'green' if pct > 0 else 'red'
                tech_table.add_row("Price vs SMA20", f"[{color}]{pct:+.2f}%[/{color}]")
            
            self.console.print(tech_table)
            self.console.print()
        
        # Fundamental Analysis
        fundamental = report.get('fundamental_analysis', {})
        if fundamental:
            fund_table = Table(title="Fundamental Metrics", box=box.ROUNDED, show_header=True)
            fund_table.add_column("Metric", style="cyan", width=25)
            fund_table.add_column("Value", justify="right", style="yellow")
            
            if fundamental.get('pe_ratio') is not None:
                fund_table.add_row("P/E Ratio", f"{fundamental['pe_ratio']:.2f}")
            
            if fundamental.get('pb_ratio') is not None:
                fund_table.add_row("P/B Ratio", f"{fundamental['pb_ratio']:.2f}")
            
            if fundamental.get('market_cap') is not None:
                market_cap = fundamental['market_cap']
                fund_table.add_row("Market Cap", self._format_currency(market_cap))
            
            if fundamental.get('roe') is not None:
                fund_table.add_row("ROE", f"{fundamental['roe']:.2f}%")
            
            if fundamental.get('debt_to_equity') is not None:
                fund_table.add_row("Debt/Equity", f"{fundamental['debt_to_equity']:.2f}")
            
            self.console.print(fund_table)
            self.console.print()
        
        # Predictions
        predictions = report.get('predictions', {})
        if predictions:
            pred_table = Table(title="ML Predictions", box=box.ROUNDED, show_header=True)
            pred_table.add_column("Metric", style="cyan", width=25)
            pred_table.add_column("Value", justify="right", style="yellow")
            
            pred_change = predictions.get('overall_predicted_change', 0)
            direction = predictions.get('overall_direction', 'neutral')
            confidence = predictions.get('overall_confidence', 0)
            
            direction_color = {
                'bullish': 'green',
                'bearish': 'red',
                'neutral': 'yellow'
            }.get(direction, 'white')
            
            pred_table.add_row("Predicted Change", f"[{direction_color}]{pred_change:+.2f}%[/{direction_color}]")
            pred_table.add_row("Direction", f"[{direction_color}]{direction.upper()}[/{direction_color}]")
            pred_table.add_row("Confidence", f"{confidence:.1f}%")
            
            self.console.print(pred_table)
            self.console.print()
        
        # Summaries
        summaries = report.get('summaries', {})
        if summaries:
            # Technical Summary
            if summaries.get('technical'):
                self.console.print(Panel(summaries['technical'], title="Technical Summary", border_style="cyan", expand=False))
                self.console.print()
            
            # Fundamental Summary
            if summaries.get('fundamental'):
                self.console.print(Panel(summaries['fundamental'], title="Fundamental Summary", border_style="cyan", expand=False))
                self.console.print()
            
            # Prediction Summary
            if summaries.get('prediction'):
                self.console.print(Panel(summaries['prediction'], title="Prediction Summary", border_style="cyan", expand=False))
                self.console.print()
            
            # Overall Summary
            if summaries.get('overall'):
                self.console.print(Panel(summaries['overall'], title="Overall Summary", border_style="bold cyan", expand=False))
                self.console.print()
        
        # Report Date
        report_date = report.get('report_date', '')
        if report_date:
            self.console.print(f"[dim]Report generated: {report_date}[/dim]")
    
    def _get_rating(self, score: float) -> str:
        """Get rating text for score."""
        if score >= 80:
            return "[green]Excellent[/green]"
        elif score >= 60:
            return "[yellow]Good[/yellow]"
        elif score >= 40:
            return "[white]Fair[/white]"
        elif score >= 20:
            return "[yellow]Poor[/yellow]"
        else:
            return "[red]Very Poor[/red]"
    
    def _format_currency(self, value: int) -> str:
        """Format large currency values."""
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        elif value >= 1_000:
            return f"${value / 1_000:.2f}K"
        else:
            return f"${value:.2f}"
    
    def display_summary_table(self, reports: List[Dict]):
        """Display summary table for multiple stocks.
        
        Args:
            reports: List of analysis reports
        """
        if not reports:
            self.console.print("[red]No reports available.[/red]")
            return
        
        table = Table(title="Stock Analysis Summary", box=box.ROUNDED, show_header=True)
        table.add_column("Symbol", style="cyan", width=10)
        table.add_column("Price", justify="right", style="yellow", width=12)
        table.add_column("Score", justify="right", style="yellow", width=10)
        table.add_column("Recommendation", justify="center", width=15)
        table.add_column("Risk", justify="center", width=10)
        
        for report in reports:
            symbol = report.get('symbol', 'N/A')
            price = report.get('current_price', 0)
            overall_score = report.get('scores', {}).get('overall', 0)
            recommendation = report.get('recommendation', 'HOLD')
            risk_level = report.get('risk_assessment', {}).get('risk_level', 'MEDIUM')
            
            rec_color = {
                'BUY': 'green',
                'SELL': 'red',
                'HOLD': 'yellow'
            }.get(recommendation, 'white')
            
            risk_color = {
                'LOW': 'green',
                'MEDIUM': 'yellow',
                'HIGH': 'red'
            }.get(risk_level, 'white')
            
            table.add_row(
                symbol,
                f"${price:.2f}",
                f"{overall_score:.1f}" if overall_score else "N/A",
                f"[{rec_color}]{recommendation}[/{rec_color}]",
                f"[{risk_color}]{risk_level}[/{risk_color}]"
            )
        
        self.console.print(table)

