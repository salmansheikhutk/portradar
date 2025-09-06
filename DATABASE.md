# PortRadar Database Schema Documentation

## Overview
PostgreSQL database schema for tracking U.S. Census international trade data by port and commodity codes.

## Database Name
`portradar`

## Connection Details
- **Host**: localhost
- **Port**: 5432
- **Database**: portradar
- **User**: salmansheikh
- **URL**: `postgresql://salmansheikh@localhost:5432/portradar`

## Schema Design

### Core Reference Tables

#### `ports`
Stores U.S. port reference data.
```sql
port_code TEXT PRIMARY KEY  -- Port identifier (e.g., "0101", "2703")
name TEXT                   -- Full port name (e.g., "NEW YORK, NY")
```

#### `products` 
Stores HS6 commodity code reference data.
```sql
hs6 TEXT PRIMARY KEY        -- 6-digit HS commodity code (e.g., "850760")
product_desc TEXT          -- Product description (e.g., "Lithium ion batteries")
```

### Main Data Table

#### `trade_monthly`
Core table storing monthly trade data by port and commodity.
```sql
id BIGSERIAL PRIMARY KEY           -- Auto-incrementing ID
flow TEXT CHECK (flow IN ('imports','exports'))  -- Trade direction
port_code TEXT REFERENCES ports(port_code)       -- Foreign key to ports
hs6 TEXT REFERENCES products(hs6)               -- Foreign key to products  
period DATE                                      -- Month start date (YYYY-MM-01)
value_usd NUMERIC                               -- Trade value in USD
qty NUMERIC                                     -- Quantity traded
unit TEXT                                       -- Unit of measurement
UNIQUE(flow, port_code, hs6, period)           -- Prevent duplicates
```

**Key Constraints:**
- Unique constraint prevents duplicate records for same flow/port/commodity/period
- Foreign keys ensure referential integrity
- CHECK constraint validates flow values

### Operational Tables

#### `etl_runs`
Tracks ETL job completion for data consistency.
```sql
source TEXT      -- Data source identifier (e.g., "census_api")
period DATE      -- Period processed (YYYY-MM-01)
completed_at TIMESTAMPTZ  -- Job completion timestamp
PRIMARY KEY(source, period)  -- Composite primary key
```

### Monitoring System Tables

#### `watchlists`
User-defined monitoring lists for specific commodities/ports.
```sql
id BIGSERIAL PRIMARY KEY              -- Auto-incrementing ID
user_id TEXT                         -- User identifier
name TEXT                           -- Watchlist name
hs6 TEXT[]                          -- Array of HS6 codes to monitor
ports TEXT[]                        -- Array of port codes to monitor
rules_json JSONB                    -- Alert rules configuration
created_at TIMESTAMPTZ DEFAULT now()  -- Creation timestamp
```

**Rules JSON Structure Example:**
```json
{
  "alerts": [
    {
      "type": "monthly_change",
      "threshold": 25.0,
      "direction": "increase"
    },
    {
      "type": "volume_threshold", 
      "value": 1000000,
      "unit": "usd"
    }
  ]
}
```

#### `alerts`
Generated alerts based on watchlist rules and thresholds.
```sql
id BIGSERIAL PRIMARY KEY                    -- Auto-incrementing ID
watchlist_id BIGINT REFERENCES watchlists(id)  -- Foreign key to watchlists
period DATE                                 -- Period that triggered alert
rule TEXT                                  -- Rule name/type that triggered alert
score NUMERIC                              -- Alert severity or percentage change
details_json JSONB                         -- Detailed alert context
created_at TIMESTAMPTZ DEFAULT now()       -- Alert generation timestamp
UNIQUE (watchlist_id, period, rule)        -- Prevent duplicate alerts
```

## Performance Indexes

### Core Indexes
- `idx_tm_port_period`: Optimizes queries by port and time period
- `idx_tm_hs6_period`: Optimizes queries by commodity and time period  
- `idx_tm_flow_period`: Optimizes queries by trade direction and time period

### Monitoring Indexes
- `idx_alerts_period`: Optimizes alert queries by time period
- `idx_watchlists_user`: Optimizes watchlist queries by user

## Data Sources

### U.S. Census API Integration
- **Imports**: `https://api.census.gov/data/timeseries/intltrade/imports/porths`
- **Exports**: `https://api.census.gov/data/timeseries/intltrade/exports/porths`

### Data Flow
1. Census API → `trade_monthly` table
2. Reference data populated in `ports` and `products`  
3. ETL completion tracked in `etl_runs`
4. User-defined monitoring via `watchlists`
5. Automated alerts generated in `alerts`

## Future Enhancements

### Additional Tables (Potential)
- `users`: User authentication and profiles
- `audit_log`: Track data changes and access
- `port_coordinates`: Geographic data for mapping
- `hs_hierarchy`: HS code classification structure

### Additional Indexes (As Needed)
- Composite indexes for complex queries
- Partial indexes for filtered queries
- GIN indexes for JSONB columns

## Maintenance Notes

### Regular Tasks
- Monitor table sizes and growth
- Analyze query performance
- Update statistics periodically
- Archive old data as needed

### Backup Strategy
- Daily automated backups recommended
- Test restore procedures regularly
- Consider point-in-time recovery setup

## Schema Creation

To recreate the schema, run:
```bash
psql -d portradar -f schema.sql
```

## Current Status
✅ All tables created and connected  
✅ Database connectivity verified  
✅ Flask app integration complete  
🚧 Data persistence layer (next step)
