from flask import Flask, jsonify, request
import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import psycopg

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

# Initialize API client
census_api = CensusTradeAPI()

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
    
    return jsonify(result)

@app.route('/test-api')
def test_api():
    """Test endpoint with sample data"""
    # Test with HS6 850760 (example from requirements)
    result = census_api.fetch_trade_data('850760', '2024-01', trade_type='imports')
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
