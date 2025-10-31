"""CLI entry point."""

import click
from rich.console import Console
from sqlalchemy.orm import Session

from database.connection import get_db_context
from data_fetch.stock_list import StockListManager
from data_fetch.price_fetcher import PriceFetcher
from pipeline.orchestrator import PipelineOrchestrator
from reporting.report_generator import ReportGenerator
from reporting.cli_formatter import CLIFormatter
from reporting.json_exporter import JSONExporter
from ml.training import ModelTrainer
from config import get_settings


console = Console()
settings = get_settings()


@click.group()
def cli():
    """Stock Analysis Pipeline CLI."""
    pass


@cli.command()
@click.argument('symbol')
def analyze(symbol: str):
    """Generate analysis report for a stock."""
    with get_db_context() as db:
        report_generator = ReportGenerator(db)
        formatter = CLIFormatter()
        
        console.print(f"[cyan]Generating analysis report for {symbol}...[/cyan]")
        
        report = report_generator.generate_report(
            symbol,
            calculate_indicators=True,
            calculate_fundamentals=True,
            generate_predictions=True,
            save_to_db=True
        )
        
        if report:
            formatter.display_report(report)
            
            # Export JSON
            exporter = JSONExporter()
            export_path = exporter.export_report(report)
            console.print(f"\n[green]Report exported to: {export_path}[/green]")
        else:
            console.print(f"[red]Failed to generate report for {symbol}[/red]")


@cli.command()
@click.option('--limit', '-l', type=int, help='Limit number of stocks')
@click.option('--symbols', '-s', multiple=True, help='Specific stock symbols')
def pipeline(limit: int, symbols: tuple):
    """Run the complete data pipeline."""
    with get_db_context() as db:
        orchestrator = PipelineOrchestrator(db)
        
        symbol_list = list(symbols) if symbols else None
        
        console.print("[cyan]Running complete pipeline...[/cyan]")
        
        results = orchestrator.run_full_pipeline(
            symbols=symbol_list,
            limit=limit,
            fetch_data=True,
            calculate_indicators=True,
            analyze_fundamentals=True,
            train_models=True,
            generate_predictions=True,
            generate_reports=True,
            export_json=True,
            display_cli=False  # Don't display for batch
        )
        
        console.print(f"\n[green]Pipeline completed. Processed {len(results)} stocks.[/green]")


@cli.command()
def list_stocks():
    """List all active stocks in database."""
    with get_db_context() as db:
        stock_manager = StockListManager(db)
        stocks = stock_manager.get_active_stocks(limit=1000)
        
        from rich.table import Table
        from rich import box
        
        table = Table(title="Active Stocks", box=box.ROUNDED, show_header=True)
        table.add_column("Symbol", style="cyan", width=10)
        table.add_column("Name", style="yellow", width=40)
        table.add_column("Exchange", style="dim", width=15)
        table.add_column("Sector", style="dim", width=20)
        
        for stock in stocks[:100]:  # Show first 100
            table.add_row(
                stock.symbol,
                stock.name or 'N/A',
                stock.primary_exchange or 'N/A',
                stock.sector or 'N/A'
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {min(len(stocks), 100)} of {len(stocks)} stocks.[/dim]")


@cli.command()
def seed_stocks():
    """Fetch and seed all US-listed stocks from Polygon.io."""
    with get_db_context() as db:
        stock_manager = StockListManager(db)
        
        console.print("[cyan]Fetching all US-listed stocks from Polygon.io...[/cyan]")
        console.print("[yellow]This may take a while due to rate limiting (5 calls/min)...[/yellow]")
        
        count = stock_manager.fetch_all_stocks()
        
        console.print(f"\n[green]Successfully seeded {count} stocks.[/green]")


@cli.command()
@click.argument('symbol')
def fetch(symbol: str):
    """Fetch price data for a stock."""
    with get_db_context() as db:
        price_fetcher = PriceFetcher(db)
        
        console.print(f"[cyan]Fetching price data for {symbol}...[/cyan]")
        
        count = price_fetcher.fetch_stock_prices(symbol, incremental=True)
        
        console.print(f"[green]Fetched {count} new price records for {symbol}.[/green]")


@cli.command()
@click.argument('symbol')
def train(symbol: str):
    """Train ML models for a stock."""
    with get_db_context() as db:
        trainer = ModelTrainer(db)
        
        console.print(f"[cyan]Training ML models for {symbol}...[/cyan]")
        
        results = trainer.train_models(symbol, retrain=False)
        
        for model_type, model_results in results.items():
            if 'error' not in model_results:
                console.print(f"[green]{model_type}: Trained successfully[/green]")
            else:
                console.print(f"[red]{model_type}: {model_results['error']}[/red]")


@cli.command()
@click.argument('symbol')
def report(symbol: str):
    """Display analysis report for a stock."""
    with get_db_context() as db:
        report_generator = ReportGenerator(db)
        formatter = CLIFormatter()
        
        report = report_generator.generate_report(
            symbol,
            calculate_indicators=True,
            calculate_fundamentals=True,
            generate_predictions=True,
            save_to_db=True
        )
        
        if report:
            formatter.display_report(report)
        else:
            console.print(f"[red]Failed to generate report for {symbol}[/red]")


@cli.command()
def update():
    """Run incremental update for recently updated stocks."""
    with get_db_context() as db:
        orchestrator = PipelineOrchestrator(db)
        
        console.print("[cyan]Running incremental update...[/cyan]")
        
        results = orchestrator.run_incremental_update(days_back=1)
        
        console.print(f"\n[green]Incremental update completed. Processed {len(results)} stocks.[/green]")


if __name__ == '__main__':
    cli()

