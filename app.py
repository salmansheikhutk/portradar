from flask import Flask, jsonify, request
import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import psycopg
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure Flask app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.warning("DATABASE_URL not set - database features will be disabled")

class CensusTradeAPI:
    """Handler for U.S. Census International Trade Data API"""
    
    BASE_URL_IMPORTS = "https://api.census.gov/data/timeseries/intltrade/imports/porths"
    BASE_URL_EXPORTS = "https://api.census.gov/data/timeseries/intltrade/exports/porths"
    
    def __init__(self):
        # Get API configuration from environment
        self.api_key = os.environ.get('CENSUS_API_KEY')
        self.timeout = int(os.environ.get('API_TIMEOUT', '30'))
        self.max_retries = int(os.environ.get('MAX_RETRIES', '3'))
    
    def fetch_trade_data(self, hs6_code, time_from=None, port_code=None, trade_type="imports"):
        """
        Fetch trade data from Census API
        
        Args:
            hs6_code (str): 6-digit HS code (e.g., '850760')
            time_from (str): Time period in format 'YYYY-MM' (e.g., '2024-01')
            port_code (str): Optional port code filter
            trade_type (str): 'imports' or 'exports' (default: 'imports')
        
        Returns:
            dict: API response data
        """
        try:
            # Choose the correct endpoint based on trade type
            base_url = self.BASE_URL_IMPORTS if trade_type == "imports" else self.BASE_URL_EXPORTS
            
            # Build query parameters for imports
            if trade_type == "imports":
                params = {
                    'get': 'PORT,PORT_NAME,I_COMMODITY,I_COMMODITY_LDESC,GEN_VAL_MO',
                    'I_COMMODITY': hs6_code,
                    'time': time_from if time_from else "2024-01"
                }
            else:  # exports
                params = {
                    'get': 'PORT,PORT_NAME,E_COMMODITY,E_COMMODITY_LDESC,ALL_VAL_MO',
                    'E_COMMODITY': hs6_code,
                    'time': time_from if time_from else "2024-01"
                }
            
            if port_code:
                params['PORT'] = port_code
            
            if self.api_key:
                params['key'] = self.api_key
            
            logger.info(f"Fetching {trade_type} data for HS6: {hs6_code}, Time: {time_from}")
            logger.info(f"URL: {base_url}")
            logger.info(f"Params: {params}")
            
            response = requests.get(base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response - first row is headers
            if len(data) < 2:
                return {"error": "No data found", "raw_response": data}
            
            headers = data[0]
            rows = data[1:]
            
            # Convert to list of dictionaries
            parsed_data = []
            for row in rows:
                record = dict(zip(headers, row))
                parsed_data.append(record)
            
            logger.info(f"Successfully fetched {len(parsed_data)} records")
            return {"success": True, "data": parsed_data, "count": len(parsed_data)}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}


class TradeDataManager:
    """Handles storing and retrieving trade data from PostgreSQL"""
    
    def __init__(self, database_url):
        self.database_url = database_url
    
    def store_trade_data(self, trade_data, flow_type, hs6_code, time_period):
        """Store trade data records in the database"""
        if not self.database_url:
            logger.warning("Database URL not configured - skipping data storage")
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    stored_count = 0
                    updated_count = 0
                    
                    # Convert time_period to proper date format (YYYY-MM-01)
                    period_date = f"{time_period}-01"
                    
                    for record in trade_data:
                        # Extract relevant data from Census API response
                        port_code = record.get('PORT')
                        port_name = record.get('PORT_NAME', '')
                        
                        # Handle different field names for imports vs exports
                        if flow_type == 'imports':
                            value_field = record.get('GEN_VAL_MO') or record.get('IMPGEN_VAL_MO')
                            commodity_desc = record.get('I_COMMODITY_LDESC', '')
                        else:
                            value_field = record.get('ALL_VAL_MO') or record.get('EXPALL_VAL_MO')  
                            commodity_desc = record.get('E_COMMODITY_LDESC', '')
                        
                        if not port_code or not value_field:
                            logger.debug(f"Skipping record with missing data: {record}")
                            continue
                        
                        try:
                            value_usd = float(value_field)
                        except (ValueError, TypeError):
                            logger.debug(f"Invalid value_usd: {value_field}")
                            continue
                        
                        # Store/update port reference data
                        cursor.execute("""
                            INSERT INTO ports (port_code, name) 
                            VALUES (%s, %s) 
                            ON CONFLICT (port_code) DO UPDATE SET name = EXCLUDED.name
                        """, (port_code, port_name))
                        
                        # Store/update product reference data
                        cursor.execute("""
                            INSERT INTO products (hs6, product_desc) 
                            VALUES (%s, %s) 
                            ON CONFLICT (hs6) DO UPDATE SET product_desc = EXCLUDED.product_desc
                        """, (hs6_code, commodity_desc))
                        
                        # Store/update trade data
                        cursor.execute("""
                            INSERT INTO trade_monthly (flow, port_code, hs6, period, value_usd, qty, unit)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (flow, port_code, hs6, period) 
                            DO UPDATE SET 
                                value_usd = EXCLUDED.value_usd,
                                qty = EXCLUDED.qty,
                                unit = EXCLUDED.unit
                        """, (flow_type, port_code, hs6_code, period_date, value_usd, None, None))
                        
                        # Check if this was an insert or update
                        if cursor.rowcount > 0:
                            stored_count += 1
                    
                    # Record the ETL run
                    cursor.execute("""
                        INSERT INTO etl_runs (source, period, completed_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (source, period) 
                        DO UPDATE SET completed_at = EXCLUDED.completed_at
                    """, (f"census_api_{flow_type}", period_date, datetime.now()))
                    
                    conn.commit()
                    
                    logger.info(f"Stored {stored_count} trade records for {hs6_code} {flow_type} in {time_period}")
                    return {
                        "success": True,
                        "stored_count": stored_count,
                        "period": time_period,
                        "flow": flow_type,
                        "hs6": hs6_code
                    }
                    
        except Exception as e:
            logger.error(f"Database storage failed: {e}")
            return {"error": f"Database storage failed: {str(e)}"}
    
    def get_trade_data(self, hs6_code=None, port_code=None, flow_type=None, start_period=None, limit=100):
        """Retrieve trade data from database"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Build dynamic query
                    conditions = []
                    params = []
                    
                    if hs6_code:
                        conditions.append("tm.hs6 = %s")
                        params.append(hs6_code)
                    
                    if port_code:
                        conditions.append("tm.port_code = %s")
                        params.append(port_code)
                    
                    if flow_type:
                        conditions.append("tm.flow = %s")
                        params.append(flow_type)
                    
                    if start_period:
                        conditions.append("tm.period >= %s")
                        params.append(f"{start_period}-01")
                    
                    where_clause = " AND ".join(conditions) if conditions else "1=1"
                    
                    query = f"""
                        SELECT tm.*, p.name as port_name, pr.product_desc
                        FROM trade_monthly tm
                        LEFT JOIN ports p ON tm.port_code = p.port_code
                        LEFT JOIN products pr ON tm.hs6 = pr.hs6
                        WHERE {where_clause}
                        ORDER BY tm.period DESC, tm.value_usd DESC
                        LIMIT %s
                    """
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    for row in rows:
                        record = dict(zip(columns, row))
                        # Format the period date as string
                        if record.get('period'):
                            record['period'] = record['period'].strftime('%Y-%m')
                        results.append(record)
                    
                    return {
                        "success": True,
                        "data": results,
                        "count": len(results)
                    }
                    
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return {"error": f"Database query failed: {str(e)}"}


# Initialize API client and database manager
census_api = CensusTradeAPI()
db_manager = TradeDataManager(DATABASE_URL) if DATABASE_URL else None

@app.route('/')
def index():
    """Basic home route"""
    return jsonify({
        "message": "PortRadar API - U.S. Census Trade Data Tracker",
        "version": "1.0.0",
        "endpoints": {
            "/trade-data": "GET - Fetch trade data",
            "/health": "GET - Health check"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

@app.route('/trade-data')
def get_trade_data():
    """
    Fetch trade data from Census API
    
    Query parameters:
    - hs6 (required): 6-digit HS code
    - time_from (optional): Start time in YYYY-MM format (default: 2024-01)
    - port_code (optional): Specific port code to filter by
    - trade_type (optional): 'imports' or 'exports' (default: 'imports')
    """
    # Get query parameters
    hs6_code = request.args.get('hs6')
    time_from = request.args.get('time_from', '2024-01')
    port_code = request.args.get('port_code')
    trade_type = request.args.get('trade_type', 'imports')
    
    # Validate required parameters
    if not hs6_code:
        return jsonify({"error": "hs6 parameter is required"}), 400
    
    if len(hs6_code) != 6 or not hs6_code.isdigit():
        return jsonify({"error": "hs6 must be a 6-digit code"}), 400
    
    # Validate trade_type
    if trade_type not in ['imports', 'exports']:
        return jsonify({"error": "trade_type must be 'imports' or 'exports'"}), 400
    
    # Validate time format
    if time_from:
        try:
            datetime.strptime(time_from, '%Y-%m')
        except ValueError:
            return jsonify({"error": "time_from must be in YYYY-MM format"}), 400
    
    # Fetch data from API
    result = census_api.fetch_trade_data(hs6_code, time_from, port_code, trade_type)
    
    if "error" in result:
        return jsonify(result), 500
    
    # Store data in database if available
    storage_result = None
    if db_manager and result.get("success") and result.get("data"):
        storage_result = db_manager.store_trade_data(
            result["data"], trade_type, hs6_code, time_from
        )
        if storage_result.get("success"):
            logger.info(f"Stored {storage_result.get('stored_count')} records in database")
        else:
            logger.warning(f"Database storage failed: {storage_result.get('error')}")
    
    # Add storage info to response
    if storage_result:
        result["database_storage"] = storage_result
    
    return jsonify(result)

@app.route('/test-api')
def test_api():
    """Test endpoint with sample data"""
    # Test with HS6 850760 (example from requirements)
    result = census_api.fetch_trade_data('850760', '2024-01', trade_type='imports')
    return jsonify(result)

@app.route('/stored-data')
def get_stored_data():
    """
    Query stored trade data from database
    
    Query parameters:
    - hs6 (optional): 6-digit HS code filter
    - port_code (optional): Port code filter  
    - flow (optional): 'imports' or 'exports' filter
    - start_period (optional): Start period in YYYY-MM format
    - limit (optional): Max records to return (default: 100)
    """
    if not db_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    # Get query parameters
    hs6_code = request.args.get('hs6')
    port_code = request.args.get('port_code')
    flow_type = request.args.get('flow')
    start_period = request.args.get('start_period')
    limit = int(request.args.get('limit', 100))
    
    # Validate parameters
    if hs6_code and (len(hs6_code) != 6 or not hs6_code.isdigit()):
        return jsonify({"error": "hs6 must be a 6-digit code"}), 400
    
    if flow_type and flow_type not in ['imports', 'exports']:
        return jsonify({"error": "flow must be 'imports' or 'exports'"}), 400
    
    if start_period:
        try:
            datetime.strptime(start_period, '%Y-%m')
        except ValueError:
            return jsonify({"error": "start_period must be in YYYY-MM format"}), 400
    
    if limit > 1000:
        return jsonify({"error": "limit cannot exceed 1000"}), 400
    
    # Query database
    result = db_manager.get_trade_data(hs6_code, port_code, flow_type, start_period, limit)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/test-db')
def test_db():
    """Test database connectivity"""
    if not DATABASE_URL:
        return jsonify({
            'status': 'error',
            'message': 'Database not configured (DATABASE_URL not set)'
        }), 500
    
    try:
        # Test basic connectivity
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # Test basic connectivity
                cursor.execute("SELECT 1 as test_value")
                test_row = cursor.fetchone()
                
                # Test our tables exist
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                return jsonify({
                    'status': 'success',
                    'database': 'Connected successfully',
                    'test_query': test_row[0] if test_row else None,
                    'tables': tables,
                    'message': f'Found {len(tables)} tables in the database'
                })
            
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Database connection failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Get host and port from environment variables
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(debug=debug, host=host, port=port)
