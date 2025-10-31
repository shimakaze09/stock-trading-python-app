-- Stock Analysis Pipeline Database Schema

-- Master list of all US-listed stocks
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    market VARCHAR(50),
    locale VARCHAR(10) DEFAULT 'us',
    primary_exchange VARCHAR(50),
    type VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    currency VARCHAR(10) DEFAULT 'USD',
    sector VARCHAR(100),
    industry VARCHAR(255),
    description TEXT,
    homepage_url VARCHAR(500),
    total_employees INTEGER,
    list_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historical price data
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(15, 4) NOT NULL,
    high DECIMAL(15, 4) NOT NULL,
    low DECIMAL(15, 4) NOT NULL,
    close DECIMAL(15, 4) NOT NULL,
    volume BIGINT NOT NULL,
    vwap DECIMAL(15, 4),
    transactions INTEGER,
    otc BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, timestamp)
);

-- Technical indicators (pre-calculated)
CREATE TABLE IF NOT EXISTS technical_indicators (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    -- Moving Averages
    sma_20 DECIMAL(15, 4),
    sma_50 DECIMAL(15, 4),
    sma_200 DECIMAL(15, 4),
    ema_12 DECIMAL(15, 4),
    ema_26 DECIMAL(15, 4),
    -- MACD
    macd DECIMAL(15, 4),
    macd_signal DECIMAL(15, 4),
    macd_histogram DECIMAL(15, 4),
    -- Momentum
    rsi DECIMAL(5, 2),
    stochastic_k DECIMAL(5, 2),
    stochastic_d DECIMAL(5, 2),
    williams_r DECIMAL(5, 2),
    -- Volatility
    bollinger_upper DECIMAL(15, 4),
    bollinger_middle DECIMAL(15, 4),
    bollinger_lower DECIMAL(15, 4),
    atr DECIMAL(15, 4),
    -- Volume
    obv BIGINT,
    volume_sma DECIMAL(15, 2),
    -- Support/Resistance
    support_level DECIMAL(15, 4),
    resistance_level DECIMAL(15, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, timestamp)
);

-- Fundamental data
CREATE TABLE IF NOT EXISTS fundamental_data (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    -- Valuation
    market_cap BIGINT,
    pe_ratio DECIMAL(10, 2),
    pb_ratio DECIMAL(10, 2),
    ev_ebitda DECIMAL(10, 2),
    -- Financial Health
    current_ratio DECIMAL(10, 2),
    debt_to_equity DECIMAL(10, 2),
    quick_ratio DECIMAL(10, 2),
    -- Growth
    revenue_growth DECIMAL(10, 2),
    earnings_growth DECIMAL(10, 2),
    -- Profitability
    roe DECIMAL(10, 2),
    roa DECIMAL(10, 2),
    profit_margin DECIMAL(10, 2),
    -- Raw data
    revenue BIGINT,
    earnings BIGINT,
    assets BIGINT,
    liabilities BIGINT,
    equity BIGINT,
    cash BIGINT,
    debt BIGINT,
    report_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, fiscal_year, fiscal_quarter)
);

-- ML model predictions
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    model_type VARCHAR(50) NOT NULL,
    prediction_date TIMESTAMP NOT NULL,
    prediction_horizon INTEGER NOT NULL, -- days ahead
    predicted_price DECIMAL(15, 4),
    predicted_change DECIMAL(10, 2), -- percentage
    predicted_direction VARCHAR(10), -- 'bullish', 'bearish', 'neutral'
    confidence_score DECIMAL(5, 2), -- 0-100
    model_version VARCHAR(50),
    features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comprehensive analysis reports
CREATE TABLE IF NOT EXISTS analysis_reports (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    report_date TIMESTAMP NOT NULL,
    -- Overall scores
    technical_score DECIMAL(5, 2), -- 0-100
    fundamental_score DECIMAL(5, 2), -- 0-100
    overall_score DECIMAL(5, 2), -- 0-100
    -- Recommendations
    recommendation VARCHAR(10), -- 'BUY', 'HOLD', 'SELL'
    recommendation_confidence DECIMAL(5, 2), -- 0-100
    -- Risk assessment
    risk_level VARCHAR(20), -- 'LOW', 'MEDIUM', 'HIGH'
    volatility_score DECIMAL(5, 2),
    drawdown_potential DECIMAL(5, 2),
    -- Summaries
    technical_summary TEXT,
    fundamental_summary TEXT,
    prediction_summary TEXT,
    overall_summary TEXT,
    -- Raw data (JSON)
    technical_data JSONB,
    fundamental_data JSONB,
    prediction_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, report_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_active ON stocks(active);

CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_id ON stock_prices(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_timestamp ON stock_prices(timestamp);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_timestamp ON stock_prices(stock_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_technical_indicators_stock_id ON technical_indicators(stock_id);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_timestamp ON technical_indicators(timestamp);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_stock_timestamp ON technical_indicators(stock_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_fundamental_data_stock_id ON fundamental_data(stock_id);
CREATE INDEX IF NOT EXISTS idx_fundamental_data_fiscal ON fundamental_data(fiscal_year DESC, fiscal_quarter DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_stock_id ON predictions(stock_id);
CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_predictions_stock_date ON predictions(stock_id, prediction_date DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_reports_stock_id ON analysis_reports(stock_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_date ON analysis_reports(report_date);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_stock_date ON analysis_reports(stock_id, report_date DESC);

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fundamental_data_updated_at BEFORE UPDATE ON fundamental_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

