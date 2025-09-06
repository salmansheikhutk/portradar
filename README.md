# PortRadar - U.S. Census Trade Data Tracker

A Flask application for monitoring U.S. international trade data by port and commodity codes.

## ✅ Step 1 Complete: API Data Fetching
## ✅ Step 2 Complete: Database Integration  
## ✅ Step 3 Complete: Watchlist Management

**Status: WATCHLIST SYSTEM OPERATIONAL** - Users can now create and manage watchlists!

**Step 1 includes:**
- ✅ Flask web application with REST API endpoints
- ✅ Integration with U.S. Census International Trade Data API (porths endpoints)
- ✅ Support for both import and export data
- ✅ Error handling and logging
- ✅ Data validation and parameter sanitization
- ✅ Comprehensive test coverage

**Step 2 includes:**
- ✅ PostgreSQL database created (`portradar`)
- ✅ Database schema created (6 tables: ports, products, trade_monthly, etl_runs, watchlists, alerts)
- ✅ Database connectivity established (psycopg3)
- ✅ Database test endpoint (`/test-db`)
- ✅ Schema documented (`schema.sql`, `DATABASE.md`)
- ✅ **Data persistence layer** - API data automatically stored in database
- ✅ **Database query endpoint** (`/stored-data`) - Query historical data

**Step 3 includes:**
- ✅ **Watchlist Management System** - Complete CRUD operations for watchlists
- ✅ **User-specific watchlists** - Filter by user ID for access control
- ✅ **Multi-commodity monitoring** - Track multiple HS6 codes per watchlist
- ✅ **Multi-port monitoring** - Track multiple ports per watchlist
- ✅ **Configurable alert rules** - JSON-based rule configuration
- ✅ **Full REST API** - Create, read, update, delete watchlists

### 🎯 Test Results
- **90 import records** successfully fetched for HS6 850760 (Lithium Ion Batteries)
- **83 export records** successfully fetched for HS6 850760  
- **173 total records stored** in PostgreSQL database automatically
- **All endpoints working** (/, /health, /trade-data, /test-api, /test-db, /stored-data, /watchlists)
- **Watchlist system operational** - Create, read, update, delete operations tested
- **Database connectivity verified** - 6 tables found in PostgreSQL
- **Data persistence verified** - API data automatically stored and queryable
- **User access control** - Watchlists filtered by user ID
- **Error handling verified** for invalid parameters

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# The .env file is already created with default values
# Update the variables as needed, especially:
# - CENSUS_API_KEY (optional but recommended)
# - SECRET_KEY (required for production)
# - Database settings (for future use)
```

3. (Optional) Get a Census API key for higher rate limits:
   - Visit: https://api.census.gov/data/key_signup.html
   - Add your key to the `.env` file: `CENSUS_API_KEY=your_key_here`

## Usage

### Start the Flask application:
```bash
python app.py
```

The app will run on `http://localhost:5000`

### API Endpoints

#### GET `/`
Returns API information and available endpoints.
**Status: ✅ Working**

#### GET `/health`  
Health check endpoint.
**Status: ✅ Working**

#### GET `/trade-data`
Fetch trade data from Census API.
**Status: ✅ Working**

**Query Parameters:**
- `hs6` (required): 6-digit HS commodity code (e.g., "850760")
- `time_from` (optional): Start time in YYYY-MM format (default: "2024-01")  
- `port_code` (optional): Specific port code to filter results
- `trade_type` (optional): "imports" or "exports" (default: "imports")

**Example:**
```bash
curl "http://localhost:5000/trade-data?hs6=850760&time_from=2024-01&trade_type=imports"
```

#### GET `/test-api`
Test endpoint that fetches sample data for HS6 code 850760.
**Status: ✅ Working**

#### GET `/test-db`
Test database connectivity and show available tables.
**Status: ✅ Working**

#### GET `/stored-data`
Query stored trade data from database.
**Status: ✅ Working**

**Query Parameters:**
- `hs6` (optional): 6-digit HS commodity code filter
- `port_code` (optional): Port code filter  
- `flow` (optional): "imports" or "exports" filter
- `start_period` (optional): Start period in YYYY-MM format
- `limit` (optional): Max records to return (default: 100, max: 1000)

**Example:**
```bash
curl "http://localhost:5000/stored-data?hs6=850760&flow=imports&limit=10"
```

### Watchlist Management

#### POST `/watchlists`
Create a new watchlist for monitoring specific commodities and ports.
**Status: ✅ Working**

**JSON Body:**
- `user_id` (required): User identifier
- `name` (required): Watchlist name
- `hs6` (optional): Array of HS6 codes to monitor
- `ports` (optional): Array of port codes to monitor
- `rules` (optional): JSON object with alert rules

**Example:**
```bash
curl -X POST "http://localhost:5000/watchlists" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "name": "Battery Watch", "hs6": ["850760", "850790"], "ports": ["1001"], "rules": {"threshold": 25}}'
```

#### GET `/watchlists`
Get watchlists for a user or specific watchlist.
**Status: ✅ Working**

**Query Parameters:**
- `user_id` (optional): Get watchlists for specific user
- `id` (optional): Get specific watchlist by ID

#### PUT `/watchlists/<id>`
Update an existing watchlist.
**Status: ✅ Working**

#### DELETE `/watchlists/<id>`
Delete a watchlist.
**Status: ✅ Working**

## Testing

Run the Census API integration test:
```bash
python test_api.py
```

Run the Flask endpoint tests:
```bash
python test_flask.py
```

Both test suites should show all tests passing ✅

## Database Schema

The PostgreSQL database includes 6 tables for comprehensive trade data tracking:

**Core Tables:**
- `ports`: U.S. port reference data
- `products`: HS6 commodity code reference data  
- `trade_monthly`: Monthly trade data by port and commodity

**Operational Tables:**
- `etl_runs`: ETL job completion tracking
- `watchlists`: User-defined monitoring lists
- `alerts`: Generated alerts based on rules

**Documentation:**
- See `schema.sql` for complete table definitions
- See `DATABASE.md` for detailed schema documentation

## Next Steps

## Next Steps

- [x] ✅ Step 1: API integration with U.S. Census trade data
- [x] ✅ Step 2: Database schema creation and connectivity  
- [x] ✅ Step 2: Data persistence layer (store API data in database)
- [x] ✅ Step 3: Watchlist management endpoints
- [ ] Step 4: Alert system with MoM change detection
- [ ] Step 5: Dashboard UI with Bootstrap

## API Data Structure

The Census API returns data with the following fields:
- `PORT_CODE`: Port identifier code
- `PORT_NAME`: Port name
- `COMMODITY_LDESC`: Commodity description
- `I_COMMODITY`: Import commodity code (HS6)
- `GEN_VAL_MO`: General value in USD
- `time`: Time period (YYYY-MM)

## Environment Variables

## Configuration

The app uses environment variables defined in `.env`:

- `CENSUS_API_KEY`: Optional Census API key for higher rate limits
- `SECRET_KEY`: Flask secret key (required for production)  
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)
- `FLASK_ENV`: Flask environment (development, production)
- Additional database and feature settings for future use

Update these variables as needed for your environment.