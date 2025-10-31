# Stock Analysis and Trading Advice Pipeline

A comprehensive real-time stock analysis system that fetches data from Polygon.io, performs technical and fundamental analysis, generates ML-powered predictions, and provides trading advice.

## Features

- **Data Pipeline**: Automated fetching of all US-listed stocks from Polygon.io free tier
- **Technical Analysis**: RSI, MACD, Moving Averages, Bollinger Bands, and more
- **Fundamental Analysis**: P/E ratios, market cap, and other metrics (free tier limited)
- **ML Predictions**: Linear regression, ARIMA, and neural network models
- **Dual Output**: CLI interface and JSON export for AI training
- **Cost Optimized**: Uses free tier APIs and local processing
- **Automated Scheduling**: GitHub Actions or local cron jobs

## Requirements

- Python 3.9+
- Docker and Docker Compose
- Polygon.io API key (free tier)

## Setup

1. **Clone and navigate to the project**
   ```bash
   cd stock-trading-python-app
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Polygon.io API key
   ```

3. **Start PostgreSQL with Docker**
   ```bash
   docker-compose up -d
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize the database**
   ```bash
   python scripts/init_db.py
   python scripts/seed_stocks.py
   ```

## Usage

### Run the complete pipeline
```bash
python scripts/run_pipeline.py
```

### Use the CLI interface
```bash
python -m cli.main analyze AAPL
python -m cli.main list-stocks
python -m cli.main report AAPL
```

### View exports
JSON exports are saved to `./exports` directory

## Configuration

Update `.env` file to configure:
- API rate limits
- Update intervals
- Database credentials
- Analysis settings

## Scheduling

### GitHub Actions
The workflow runs automatically on schedule (defined in `.github/workflows/pipeline.yml`)

### Local Cron
Set up a cron job to run `scripts/run_pipeline.py` at your desired interval

## Architecture

- **Data Fetch**: Polygon.io API integration with rate limiting
- **Database**: PostgreSQL with optimized schema
- **Analysis**: Technical indicators + fundamental metrics
- **ML Models**: Multiple prediction models with ensemble approach
- **Reporting**: CLI and JSON outputs

## Cost Optimization

- Uses Polygon.io free tier (5 calls/min)
- Local processing (no cloud compute costs)
- Efficient batching and incremental updates
- Lightweight ML models

## Testing

Run all tests:
```bash
python -m pytest tests/ -v
```

Run specific test module:
```bash
python -m pytest tests/test_config.py -v
```

See `TEST_RESULTS.md` for detailed test results.

**Note**: Database is configured to use port **5435** by default to avoid conflicts with existing PostgreSQL instances on ports 5432 and 5433.

## License

MIT

