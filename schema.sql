-- PortRadar Database Schema
-- PostgreSQL schema for U.S. Census trade data tracking
-- Created: 2025-09-05

-- Core reference tables
CREATE TABLE IF NOT EXISTS ports (
  port_code TEXT PRIMARY KEY,
  name TEXT
);

CREATE TABLE IF NOT EXISTS products (
  hs6 TEXT PRIMARY KEY,
  product_desc TEXT
);

-- Main trade data table
CREATE TABLE IF NOT EXISTS trade_monthly (
  id BIGSERIAL PRIMARY KEY,
  flow TEXT CHECK (flow IN ('imports','exports')),
  port_code TEXT REFERENCES ports(port_code),
  hs6 TEXT REFERENCES products(hs6),
  period DATE,                 -- month start e.g. 2024-01-01
  value_usd NUMERIC,
  qty NUMERIC,
  unit TEXT,
  UNIQUE(flow, port_code, hs6, period)
);

-- ETL and operational tables
CREATE TABLE IF NOT EXISTS etl_runs (
  source TEXT,
  period DATE,
  completed_at TIMESTAMPTZ,
  PRIMARY KEY(source, period)
);

-- Watchlist and alert system tables
CREATE TABLE IF NOT EXISTS watchlists (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT,
  name TEXT,
  hs6 TEXT[],              -- Array of HS6 codes to monitor
  ports TEXT[],            -- Array of port codes to monitor
  rules_json JSONB,        -- Alert rules configuration
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts (
  id BIGSERIAL PRIMARY KEY,
  watchlist_id BIGINT REFERENCES watchlists(id),
  period DATE,
  rule TEXT,
  score NUMERIC,
  details_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (watchlist_id, period, rule)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_tm_port_period ON trade_monthly(port_code, period);
CREATE INDEX IF NOT EXISTS idx_tm_hs6_period  ON trade_monthly(hs6, period);

-- Additional useful indexes for queries
CREATE INDEX IF NOT EXISTS idx_tm_flow_period ON trade_monthly(flow, period);
CREATE INDEX IF NOT EXISTS idx_alerts_period ON alerts(period);
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);

-- Comments for documentation
COMMENT ON TABLE ports IS 'U.S. port reference data with codes and names';
COMMENT ON TABLE products IS 'HS6 commodity code reference data with descriptions';
COMMENT ON TABLE trade_monthly IS 'Monthly trade data by port, commodity, and flow direction';
COMMENT ON TABLE etl_runs IS 'Track ETL job completion for data consistency';
COMMENT ON TABLE watchlists IS 'User-defined monitoring lists for specific commodities/ports';
COMMENT ON TABLE alerts IS 'Generated alerts based on watchlist rules and thresholds';

COMMENT ON COLUMN trade_monthly.flow IS 'Trade direction: imports or exports';
COMMENT ON COLUMN trade_monthly.period IS 'Month start date (YYYY-MM-01)';
COMMENT ON COLUMN trade_monthly.value_usd IS 'Trade value in USD';
COMMENT ON COLUMN trade_monthly.qty IS 'Quantity traded';
COMMENT ON COLUMN trade_monthly.unit IS 'Unit of measurement for quantity';

COMMENT ON COLUMN watchlists.hs6 IS 'Array of HS6 commodity codes to monitor';
COMMENT ON COLUMN watchlists.ports IS 'Array of port codes to monitor';
COMMENT ON COLUMN watchlists.rules_json IS 'JSON configuration for alert rules and thresholds';

COMMENT ON COLUMN alerts.rule IS 'Name/type of rule that triggered the alert';
COMMENT ON COLUMN alerts.score IS 'Alert severity score or percentage change';
COMMENT ON COLUMN alerts.details_json IS 'Detailed alert information and context';
