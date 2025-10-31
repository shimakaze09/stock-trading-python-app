# Setup Instructions

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Polygon.io API key (free tier)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
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
   ```

6. **Seed stocks from Polygon.io**
   ```bash
   python scripts/seed_stocks.py
   ```
   Note: This may take a while due to rate limiting (5 calls/min).

## Usage

### Run the complete pipeline
```bash
python scripts/run_pipeline.py [limit]
```

### Use the CLI interface
```bash
# Generate analysis report for a stock
python -m cli.main analyze AAPL

# Run complete pipeline
python -m cli.main pipeline

# List all stocks
python -m cli.main list-stocks

# Fetch price data
python -m cli.main fetch AAPL

# Train ML models
python -m cli.main train AAPL

# View report
python -m cli.main report AAPL

# Run incremental update
python -m cli.main update
```

## Scheduling

### GitHub Actions
The workflow is configured in `.github/workflows/pipeline.yml`. It runs:
- Every 30 minutes
- At market open (9:30 AM EST)
- At market close (4:00 PM EST)

To use GitHub Actions:
1. Add your `POLYGON_API_KEY` to GitHub Secrets
2. The workflow will run automatically on schedule

### Local Cron
You can set up a cron job to run the pipeline locally:
```bash
# Edit crontab
crontab -e

# Add line (runs every 30 minutes)
*/30 * * * * cd /path/to/project && python scripts/run_pipeline.py 100
```

## Configuration

Edit `.env` to configure:
- `UPDATE_INTERVAL_MINUTES`: Update interval (default: 30)
- `MAX_API_CALLS_PER_MINUTE`: API rate limit (default: 5)
- `BATCH_SIZE`: Batch processing size (default: 100)
- Analysis settings (technical, fundamental, ML)
- Output settings (JSON export path, CLI output)

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL container is running: `docker-compose ps`
- Check database credentials in `.env`
- Verify database is accessible: `docker-compose logs postgres`

### API Rate Limiting
- The pipeline automatically handles rate limiting (5 calls/min)
- Processing all US stocks will take hours
- Use `limit` parameter to process fewer stocks

### ML Model Training
- Models require sufficient historical data (at least 100 days)
- Training may take several minutes per stock
- Models are saved in `models/{symbol}/` directory

## Output

- **CLI Output**: Formatted reports in terminal
- **JSON Exports**: Saved to `./exports` directory
- **Database**: All data stored in PostgreSQL

