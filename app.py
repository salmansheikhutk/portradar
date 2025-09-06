from flask import Flask, jsonify, request, render_template
import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import psycopg
from datetime import datetime
import json

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
                    'time': time_from if time_from else "2025-06"
                }
            else:  # exports
                params = {
                    'get': 'PORT,PORT_NAME,E_COMMODITY,E_COMMODITY_LDESC,ALL_VAL_MO',
                    'E_COMMODITY': hs6_code,
                    'time': time_from if time_from else "2025-06"
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
    
    def fetch_all_port_commodities(self, port_code, time_period, trade_type="imports"):
        """
        Fetch ALL commodity data for a specific port and time period
        
        Args:
            port_code (str): Port code (e.g., '2010' for LA)
            time_period (str): Time period in format 'YYYY-MM' (e.g., '2025-06')
            trade_type (str): 'imports' or 'exports' (default: 'imports')
        
        Returns:
            dict: API response data with all commodities for the port
        """
        try:
            # Choose the correct endpoint based on trade type
            base_url = self.BASE_URL_IMPORTS if trade_type == "imports" else self.BASE_URL_EXPORTS
            
            # Build query parameters - no commodity filter to get ALL commodities
            if trade_type == "imports":
                params = {
                    'get': 'I_COMMODITY,I_COMMODITY_LDESC,GEN_VAL_MO',
                    'PORT': port_code,
                    'time': time_period
                }
            else:  # exports
                params = {
                    'get': 'E_COMMODITY,E_COMMODITY_LDESC,ALL_VAL_MO',
                    'PORT': port_code,
                    'time': time_period
                }
            
            if self.api_key:
                params['key'] = self.api_key
            
            logger.info(f"Fetching ALL {trade_type} commodities for port {port_code}, time {time_period}")
            
            response = requests.get(base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response - first row is headers
            if len(data) < 2:
                return {"error": "No data found", "raw_response": data}
            
            headers = data[0]
            rows = data[1:]
            
            # Convert to list of dictionaries, filtering out total rows
            parsed_data = []
            for row in rows:
                # Skip the "TOTAL" row (commodity code is typically "-")
                if row[0] != '-' and len(row) >= len(headers):
                    record = dict(zip(headers, row))
                    
                    # Add port code to each record
                    record['PORT'] = port_code
                    record['time'] = time_period
                    
                    parsed_data.append(record)
            
            logger.info(f"Successfully fetched {len(parsed_data)} commodity records for port {port_code}")
            return {"success": True, "data": parsed_data, "count": len(parsed_data)}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for port {port_code}: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error for port {port_code}: {str(e)}")
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


class WatchlistManager:
    """Handles watchlist management and operations"""
    
    def __init__(self, database_url):
        self.database_url = database_url
    
    def create_watchlist(self, user_id, name, hs6_codes=None, port_codes=None, rules=None):
        """Create a new watchlist"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Convert lists to PostgreSQL arrays
                    hs6_array = hs6_codes or []
                    ports_array = port_codes or []
                    rules_json = rules or {}
                    
                    cursor.execute("""
                        INSERT INTO watchlists (user_id, name, hs6, ports, rules_json, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                    """, (user_id, name, hs6_array, ports_array, json.dumps(rules_json), datetime.now()))
                    
                    result = cursor.fetchone()
                    watchlist_id = result[0]
                    created_at = result[1]
                    
                    conn.commit()
                    
                    logger.info(f"Created watchlist '{name}' with ID {watchlist_id} for user {user_id}")
                    return {
                        "success": True,
                        "watchlist_id": watchlist_id,
                        "name": name,
                        "user_id": user_id,
                        "hs6": hs6_array,
                        "ports": ports_array,
                        "rules": rules_json,
                        "created_at": created_at.isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to create watchlist: {e}")
            return {"error": f"Failed to create watchlist: {str(e)}"}
    
    def get_watchlists(self, user_id=None, watchlist_id=None):
        """Get watchlists for a user or specific watchlist"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    if watchlist_id:
                        # Get specific watchlist
                        cursor.execute("""
                            SELECT id, user_id, name, hs6, ports, rules_json, created_at
                            FROM watchlists WHERE id = %s
                        """, (watchlist_id,))
                        row = cursor.fetchone()
                        
                        if not row:
                            return {"error": "Watchlist not found"}
                        
                        return {
                            "success": True,
                            "watchlist": {
                                "id": row[0],
                                "user_id": row[1],
                                "name": row[2],
                                "hs6": row[3],
                                "ports": row[4],
                                "rules": row[5],
                                "created_at": row[6].isoformat()
                            }
                        }
                    
                    elif user_id:
                        # Get all watchlists for user
                        cursor.execute("""
                            SELECT id, user_id, name, hs6, ports, rules_json, created_at
                            FROM watchlists WHERE user_id = %s
                            ORDER BY created_at DESC
                        """, (user_id,))
                        rows = cursor.fetchall()
                        
                        watchlists = []
                        for row in rows:
                            watchlists.append({
                                "id": row[0],
                                "user_id": row[1],
                                "name": row[2],
                                "hs6": row[3],
                                "ports": row[4],
                                "rules": row[5],
                                "created_at": row[6].isoformat()
                            })
                        
                        return {
                            "success": True,
                            "watchlists": watchlists,
                            "count": len(watchlists)
                        }
                    
                    else:
                        # Get all watchlists (admin view)
                        cursor.execute("""
                            SELECT id, user_id, name, hs6, ports, rules_json, created_at
                            FROM watchlists
                            ORDER BY created_at DESC
                            LIMIT 100
                        """)
                        rows = cursor.fetchall()
                        
                        watchlists = []
                        for row in rows:
                            watchlists.append({
                                "id": row[0],
                                "user_id": row[1],
                                "name": row[2],
                                "hs6": row[3],
                                "ports": row[4],
                                "rules": row[5],
                                "created_at": row[6].isoformat()
                            })
                        
                        return {
                            "success": True,
                            "watchlists": watchlists,
                            "count": len(watchlists)
                        }
                        
        except Exception as e:
            logger.error(f"Failed to get watchlists: {e}")
            return {"error": f"Failed to get watchlists: {str(e)}"}
    
    def update_watchlist(self, watchlist_id, user_id=None, name=None, hs6_codes=None, port_codes=None, rules=None):
        """Update an existing watchlist"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # First check if watchlist exists and belongs to user
                    cursor.execute("SELECT user_id FROM watchlists WHERE id = %s", (watchlist_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        return {"error": "Watchlist not found"}
                    
                    if user_id and result[0] != user_id:
                        return {"error": "Access denied"}
                    
                    # Build update query dynamically
                    updates = []
                    params = []
                    
                    if name is not None:
                        updates.append("name = %s")
                        params.append(name)
                    
                    if hs6_codes is not None:
                        updates.append("hs6 = %s")
                        params.append(hs6_codes)
                    
                    if port_codes is not None:
                        updates.append("ports = %s")
                        params.append(port_codes)
                    
                    if rules is not None:
                        updates.append("rules_json = %s")
                        params.append(json.dumps(rules))
                    
                    if not updates:
                        return {"error": "No updates provided"}
                    
                    params.append(watchlist_id)
                    query = f"UPDATE watchlists SET {', '.join(updates)} WHERE id = %s"
                    
                    cursor.execute(query, params)
                    conn.commit()
                    
                    # Return updated watchlist
                    return self.get_watchlists(watchlist_id=watchlist_id)
                    
        except Exception as e:
            logger.error(f"Failed to update watchlist: {e}")
            return {"error": f"Failed to update watchlist: {str(e)}"}
    
    def delete_watchlist(self, watchlist_id, user_id=None):
        """Delete a watchlist"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Check ownership if user_id provided
                    if user_id:
                        cursor.execute("SELECT user_id FROM watchlists WHERE id = %s", (watchlist_id,))
                        result = cursor.fetchone()
                        
                        if not result:
                            return {"error": "Watchlist not found"}
                        
                        if result[0] != user_id:
                            return {"error": "Access denied"}
                    
                    cursor.execute("DELETE FROM watchlists WHERE id = %s", (watchlist_id,))
                    
                    if cursor.rowcount == 0:
                        return {"error": "Watchlist not found"}
                    
                    conn.commit()
                    
                    logger.info(f"Deleted watchlist {watchlist_id}")
                    return {"success": True, "message": f"Watchlist {watchlist_id} deleted"}
                    
        except Exception as e:
            logger.error(f"Failed to delete watchlist: {e}")
            return {"error": f"Failed to delete watchlist: {str(e)}"}


class AlertManager:
    """Handles alert generation and management based on watchlist rules"""
    
    def __init__(self, database_url):
        self.database_url = database_url
    
    def generate_alerts(self, watchlist_id=None, user_id=None):
        """Generate alerts by checking watchlist rules against current data"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Get watchlists to check
                    if watchlist_id:
                        cursor.execute("""
                            SELECT id, user_id, name, hs6, ports, rules_json
                            FROM watchlists WHERE id = %s
                        """, (watchlist_id,))
                    elif user_id:
                        cursor.execute("""
                            SELECT id, user_id, name, hs6, ports, rules_json
                            FROM watchlists WHERE user_id = %s
                        """, (user_id,))
                    else:
                        cursor.execute("""
                            SELECT id, user_id, name, hs6, ports, rules_json
                            FROM watchlists
                            ORDER BY id
                        """)
                    
                    watchlists = cursor.fetchall()
                    generated_alerts = []
                    
                    for watchlist_row in watchlists:
                        wl_id, wl_user_id, wl_name, hs6_codes, port_codes, rules_json = watchlist_row
                        
                        if not rules_json:
                            continue
                        
                        rules = rules_json
                        
                        # Check each HS6 code in the watchlist
                        for hs6 in (hs6_codes or []):
                            
                            # Check month-over-month change rule
                            if rules.get('mom_change_threshold'):
                                mom_alerts = self._check_mom_change(cursor, hs6, port_codes, rules['mom_change_threshold'], wl_id, wl_user_id)
                                generated_alerts.extend(mom_alerts)
                            
                            # Check volume threshold rule
                            if rules.get('volume_threshold'):
                                volume_alerts = self._check_volume_threshold(cursor, hs6, port_codes, rules['volume_threshold'], wl_id, wl_user_id)
                                generated_alerts.extend(volume_alerts)
                    
                    # Store generated alerts in database
                    for alert in generated_alerts:
                        cursor.execute("""
                            INSERT INTO alerts (watchlist_id, period, rule, score, details_json, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (watchlist_id, period, rule) 
                            DO NOTHING
                        """, (
                            alert['watchlist_id'], alert['period'], alert['alert_type'],
                            alert.get('score', 0), json.dumps(alert), datetime.now()
                        ))
                    
                    conn.commit()
                    
                    logger.info(f"Generated {len(generated_alerts)} alerts")
                    return {
                        "success": True,
                        "alerts_generated": len(generated_alerts),
                        "alerts": generated_alerts
                    }
                    
        except Exception as e:
            logger.error(f"Failed to generate alerts: {e}")
            return {"error": f"Failed to generate alerts: {str(e)}"}
    
    def _check_mom_change(self, cursor, hs6, port_codes, threshold, watchlist_id, user_id):
        """Check for month-over-month change alerts"""
        alerts = []
        
        # Get data from multiple periods for comparison (expand limit)
        if port_codes:
            cursor.execute("""
                SELECT port_code, period, value_usd
                FROM trade_monthly
                WHERE hs6 = %s AND port_code = ANY(%s)
                ORDER BY period DESC
                LIMIT 100
            """, (hs6, port_codes))
        else:
            cursor.execute("""
                SELECT port_code, period, value_usd
                FROM trade_monthly
                WHERE hs6 = %s
                ORDER BY period DESC
                LIMIT 100
            """, (hs6,))
        
        rows = cursor.fetchall()
        
        # Group by port and calculate changes
        port_data = {}
        for port_code, period, value_usd in rows:
            if port_code not in port_data:
                port_data[port_code] = []
            port_data[port_code].append((period, float(value_usd or 0)))
        
        for port_code, data_points in port_data.items():
            if len(data_points) < 2:
                continue
            
            # Sort by period (most recent first)
            data_points.sort(key=lambda x: x[0], reverse=True)
            current_value = data_points[0][1]
            previous_value = data_points[1][1]
            current_period = data_points[0][0]
            
            if previous_value == 0:
                continue
            
            # Calculate percentage change
            pct_change = ((current_value - previous_value) / previous_value) * 100
            
            if abs(pct_change) >= threshold:
                direction = "increased" if pct_change > 0 else "decreased"
                alerts.append({
                    'watchlist_id': watchlist_id,
                    'user_id': user_id,
                    'alert_type': 'mom_change',
                    'hs6': hs6,
                    'port_code': port_code,
                    'period': current_period.strftime('%Y-%m-%d'),
                    'value_usd': current_value,
                    'reference_value': previous_value,
                    'threshold_value': threshold,
                    'score': abs(pct_change),
                    'message': f"HS6 {hs6} at port {port_code} {direction} by {abs(pct_change):.1f}% MoM (${current_value:,.0f} vs ${previous_value:,.0f})"
                })
        
        return alerts
    
    def _check_volume_threshold(self, cursor, hs6, port_codes, threshold, watchlist_id, user_id):
        """Check for volume threshold alerts"""
        alerts = []
        
        # Get recent data to check against threshold (expand time range)
        if port_codes:
            cursor.execute("""
                SELECT port_code, period, value_usd
                FROM trade_monthly
                WHERE hs6 = %s AND port_code = ANY(%s)
                AND period >= (CURRENT_DATE - INTERVAL '12 months')
                ORDER BY period DESC, value_usd DESC
            """, (hs6, port_codes))
        else:
            cursor.execute("""
                SELECT port_code, period, value_usd
                FROM trade_monthly
                WHERE hs6 = %s
                AND period >= (CURRENT_DATE - INTERVAL '12 months')
                ORDER BY period DESC, value_usd DESC
            """, (hs6,))
        
        rows = cursor.fetchall()
        
        for port_code, period, value_usd in rows:
            value = float(value_usd or 0)
            if value >= threshold:
                alerts.append({
                    'watchlist_id': watchlist_id,
                    'user_id': user_id,
                    'alert_type': 'volume_threshold',
                    'hs6': hs6,
                    'port_code': port_code,
                    'period': period.strftime('%Y-%m-%d'),
                    'value_usd': value,
                    'reference_value': None,
                    'threshold_value': threshold,
                    'score': (value / threshold) * 100,
                    'message': f"HS6 {hs6} at port {port_code} exceeded volume threshold: ${value:,.0f} >= ${threshold:,.0f}"
                })
        
        return alerts
    
    def get_alerts(self, user_id=None, watchlist_id=None, alert_type=None, limit=100):
        """Get alerts for user, watchlist, or all alerts"""
        if not self.database_url:
            return {"error": "Database not configured"}
        
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    conditions = []
                    params = []
                    
                    if user_id:
                        conditions.append("w.user_id = %s")
                        params.append(user_id)
                    
                    if watchlist_id:
                        conditions.append("a.watchlist_id = %s")
                        params.append(watchlist_id)
                    
                    if alert_type:
                        conditions.append("a.rule = %s")
                        params.append(alert_type)
                    
                    where_clause = " AND ".join(conditions) if conditions else "1=1"
                    
                    query = f"""
                        SELECT a.id, a.watchlist_id, a.period, a.rule, a.score, 
                               a.details_json, a.created_at, w.name as watchlist_name,
                               w.user_id
                        FROM alerts a
                        LEFT JOIN watchlists w ON a.watchlist_id = w.id
                        WHERE {where_clause}
                        ORDER BY a.created_at DESC
                        LIMIT %s
                    """
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    alerts = []
                    for row in rows:
                        alert = {
                            'id': row[0],
                            'watchlist_id': row[1],
                            'period': row[2].strftime('%Y-%m-%d') if row[2] else None,
                            'alert_type': row[3],
                            'score': float(row[4]) if row[4] else 0,
                            'details': row[5],
                            'created_at': row[6].isoformat() if row[6] else None,
                            'watchlist_name': row[7],
                            'user_id': row[8]
                        }
                        # Extract message from details if available
                        if alert['details'] and isinstance(alert['details'], dict):
                            alert['message'] = alert['details'].get('message', '')
                        alerts.append(alert)
                    
                    return {
                        "success": True,
                        "alerts": alerts,
                        "count": len(alerts)
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return {"error": f"Failed to get alerts: {str(e)}"}


# Initialize API client, database manager, watchlist manager, and alert manager
census_api = CensusTradeAPI()
db_manager = TradeDataManager(DATABASE_URL) if DATABASE_URL else None
watchlist_manager = WatchlistManager(DATABASE_URL) if DATABASE_URL else None
alert_manager = AlertManager(DATABASE_URL) if DATABASE_URL else None

@app.route('/')
def index():
    """Basic home route"""
    return jsonify({
        "message": "PortRadar API - U.S. Census Trade Data Tracker",
        "version": "1.0.0",
        "endpoints": {
            "/trade-data": "GET - Fetch trade data from Census API",
            "/stored-data": "GET - Query stored trade data",
            "/watchlists": "GET, POST - Manage watchlists",
            "/watchlists/<id>": "PUT, DELETE - Update/delete specific watchlist",
            "/alerts": "GET, POST - View and generate alerts",
            "/health": "GET - Health check",
            "/test-db": "GET - Test database connectivity",
            "/test-api": "GET - Test Census API with sample data",
            "/dashboard": "GET - Web dashboard interface"
        }
    })

@app.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/watchlists-page')
def watchlists_page():
    """Watchlists management page"""
    return render_template('watchlists.html')

@app.route('/trade-data-page')
def trade_data_page():
    """Trade data search page"""
    return render_template('trade_data.html')

@app.route('/alerts-page')
def alerts_page():
    """Alerts monitoring page"""
    return render_template('alerts.html')

@app.route('/debug')
def debug_page():
    """Debug page for testing API calls"""
    return render_template('debug.html')

@app.route('/trade-simple')
def trade_simple_page():
    """Simple trade data page for testing"""
    return render_template('trade_simple.html')

@app.route('/commodity-lookup', methods=['GET'])
def commodity_lookup():
    """Search for commodity codes by description"""
    try:
        search_term = request.args.get('search', '').lower()
        limit = int(request.args.get('limit', 20))
        
        conn = psycopg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Search in both HS6 codes and commodity descriptions
        query = """
        SELECT DISTINCT hs6_code, commodity_description
        FROM trade_data 
        WHERE LOWER(commodity_description) LIKE %s 
           OR hs6_code::text LIKE %s
        ORDER BY hs6_code
        LIMIT %s
        """
        
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (search_pattern, search_pattern, limit))
        rows = cursor.fetchall()
        
        # Convert to dictionary format
        commodities = []
        for row in rows:
            commodities.append({
                'hs6_code': row[0],
                'commodity_description': row[1]
            })
        
        conn.close()
        
        return jsonify({
            "success": True,
            "commodities": commodities,
            "count": len(commodities)
        })
        
    except Exception as e:
        logger.error(f"Error in commodity lookup: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/port-lookup', methods=['GET'])
def port_lookup():
    """Search for port codes by name"""
    try:
        search_term = request.args.get('search', '').lower()
        limit = int(request.args.get('limit', 20))
        
        conn = psycopg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Search in both port codes and port names
        query = """
        SELECT DISTINCT port_code, port_name
        FROM ports 
        WHERE LOWER(port_name) LIKE %s 
           OR port_code::text LIKE %s
        ORDER BY port_code
        LIMIT %s
        """
        
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (search_pattern, search_pattern, limit))
        rows = cursor.fetchall()
        
        # Convert to dictionary format
        ports = []
        for row in rows:
            ports.append({
                'port_code': row[0],
                'port_name': row[1]
            })
        
        conn.close()
        
        return jsonify({
            "success": True,
            "ports": ports,
            "count": len(ports)
        })
        
    except Exception as e:
        logger.error(f"Error in port lookup: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

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
    time_from = request.args.get('time_from', '2025-06')
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
    # Test with HS6 850760 with more recent data
    result = census_api.fetch_trade_data('850760', '2025-06', trade_type='imports')
    return jsonify(result)

@app.route('/refresh-data')
def refresh_current_data():
    """Fetch and store current trade data for all available commodities at major ports"""
    if not db_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        # Major U.S. ports to fetch data from (start with just LA for testing)
        major_ports = ['2010']  # Just LA for now
        
        success_count = 0
        error_count = 0
        total_records = 0
        
        for port_code in major_ports:
            logger.info(f"Fetching ALL commodities for port {port_code}...")
            
            try:
                # Get all available commodities for this port
                result = census_api.fetch_all_port_commodities(port_code, '2025-06')
                
                if result.get('success') and result.get('data'):
                    # Process and filter the data
                    trade_records = []
                    for record in result['data']:
                        # Skip records with null or empty commodity codes
                        commodity_code = record.get('I_COMMODITY')
                        if not commodity_code or commodity_code == '-':
                            continue
                            
                        # Convert to the format expected by store_trade_data
                        processed_record = {
                            'PORT': port_code,
                            'PORT_NAME': record.get('PORT_NAME', ''),
                            'I_COMMODITY_LDESC': record.get('I_COMMODITY_LDESC', ''),
                            'GEN_VAL_MO': record.get('GEN_VAL_MO', '0'),
                            'time': '2025-06'
                        }
                        trade_records.append((processed_record, commodity_code))
                    
                    if trade_records:
                        # Store each commodity separately
                        records_stored = 0
                        for processed_record, commodity_code in trade_records:
                            store_result = db_manager.store_trade_data(
                                [processed_record], 'imports', commodity_code, '2025-06'
                            )
                            records_stored += store_result.get('stored_count', 0)
                        
                        total_records += records_stored
                        success_count += 1
                        logger.info(f"Port {port_code}: {records_stored} records stored")
                    else:
                        logger.warning(f"No valid records after filtering for port {port_code}")
                        error_count += 1
                else:
                    logger.warning(f"No data returned for port {port_code}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error fetching data for port {port_code}: {e}")
                error_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Data refresh complete. Processed {success_count} ports, {error_count} errors. {total_records} total records stored.',
            'ports_processed': success_count,
            'ports_failed': error_count,
            'total_records_stored': total_records
        })
        
    except Exception as e:
        logger.error(f"Failed to refresh data: {e}")
        return jsonify({"error": f"Failed to refresh data: {str(e)}"}), 500

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
    
    if limit > 10000:
        return jsonify({"error": "limit cannot exceed 10000"}), 400
    
    # Query database
    result = db_manager.get_trade_data(hs6_code, port_code, flow_type, start_period, limit)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/quick-reference')
def get_quick_reference():
    """Get real commodity and port data for quick reference"""
    if not db_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        with psycopg.connect(db_manager.database_url) as conn:
            with conn.cursor() as cursor:
                # Get top 5 HS6 codes by trade value
                cursor.execute("""
                    SELECT tm.hs6, pr.product_desc, SUM(tm.value_usd) as total_value
                    FROM trade_monthly tm
                    LEFT JOIN products pr ON tm.hs6 = pr.hs6
                    WHERE tm.value_usd > 0
                    GROUP BY tm.hs6, pr.product_desc
                    ORDER BY total_value DESC
                    LIMIT 5
                """)
                commodity_rows = cursor.fetchall()
                
                # Get top 5 ports by trade value
                cursor.execute("""
                    SELECT tm.port_code, p.name as port_name, SUM(tm.value_usd) as total_value
                    FROM trade_monthly tm
                    LEFT JOIN ports p ON tm.port_code = p.port_code
                    WHERE tm.value_usd > 0
                    GROUP BY tm.port_code, p.name
                    ORDER BY total_value DESC
                    LIMIT 5
                """)
                port_rows = cursor.fetchall()
                
                commodities = []
                for hs6, desc, value in commodity_rows:
                    commodities.append({
                        'code': hs6,
                        'description': desc or f"HS6 Code {hs6}",
                        'value': float(value or 0)
                    })
                
                ports = []
                for port_code, port_name, value in port_rows:
                    ports.append({
                        'code': port_code,
                        'name': port_name or f"Port {port_code}",
                        'value': float(value or 0)
                    })
                
                return jsonify({
                    'success': True,
                    'commodities': commodities,
                    'ports': ports
                })
                
    except Exception as e:
        logger.error(f"Failed to get quick reference: {e}")
        return jsonify({"error": f"Failed to get quick reference: {str(e)}"}), 500

@app.route('/ports')
def get_ports():
    """Get available ports for dropdown"""
    if not db_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        with psycopg.connect(db_manager.database_url) as conn:
            with conn.cursor() as cursor:
                # Get ports ordered by trade volume
                cursor.execute("""
                    SELECT DISTINCT tm.port_code, 
                           COALESCE(p.name, 'Port ' || tm.port_code) as port_name,
                           SUM(tm.value_usd) as total_value
                    FROM trade_monthly tm
                    LEFT JOIN ports p ON tm.port_code = p.port_code
                    WHERE tm.port_code != '-' AND tm.value_usd > 0
                    GROUP BY tm.port_code, p.name
                    ORDER BY total_value DESC
                    LIMIT 50
                """)
                port_rows = cursor.fetchall()
                
                ports = []
                for port_code, port_name, value in port_rows:
                    ports.append({
                        'code': port_code,
                        'name': port_name,
                        'display_name': f"{port_name} ({port_code})",
                        'value': float(value or 0)
                    })
                
                return jsonify({
                    'success': True,
                    'ports': ports,
                    'count': len(ports)
                })
                
    except Exception as e:
        logger.error(f"Failed to get ports: {e}")
        return jsonify({"error": f"Failed to get ports: {str(e)}"}), 500

@app.route('/commodities')
def get_commodities():
    """Get available commodities for dropdown"""
    if not db_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        with psycopg.connect(db_manager.database_url) as conn:
            with conn.cursor() as cursor:
                # Get commodities ordered by trade volume
                cursor.execute("""
                    SELECT DISTINCT tm.hs6,
                           COALESCE(pr.product_desc, 'HS6 ' || tm.hs6) as product_desc,
                           SUM(tm.value_usd) as total_value
                    FROM trade_monthly tm
                    LEFT JOIN products pr ON tm.hs6 = pr.hs6
                    WHERE tm.value_usd > 0
                    GROUP BY tm.hs6, pr.product_desc
                    ORDER BY total_value DESC
                    LIMIT 100
                """)
                commodity_rows = cursor.fetchall()
                
                commodities = []
                for hs6, product_desc, value in commodity_rows:
                    # Truncate long descriptions
                    short_desc = product_desc[:40] + "..." if len(product_desc) > 40 else product_desc
                    commodities.append({
                        'code': hs6,
                        'description': product_desc,
                        'display_name': f"{hs6} - {short_desc}",
                        'value': float(value or 0)
                    })
                
                return jsonify({
                    'success': True,
                    'commodities': commodities,
                    'count': len(commodities)
                })
                
    except Exception as e:
        logger.error(f"Failed to get commodities: {e}")
        return jsonify({"error": f"Failed to get commodities: {str(e)}"}), 500

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

@app.route('/watchlists', methods=['POST'])
def create_watchlist():
    """
    Create a new watchlist
    
    JSON Body:
    - user_id (required): User identifier
    - name (required): Watchlist name
    - hs6 (optional): Array of HS6 codes to monitor
    - ports (optional): Array of port codes to monitor
    - rules (optional): JSON object with alert rules
    """
    if not watchlist_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        user_id = data.get('user_id')
        name = data.get('name')
        hs6_codes = data.get('hs6', [])
        port_codes = data.get('ports', [])
        rules = data.get('rules', {})
        
        # Validate required fields
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        if not name:
            return jsonify({"error": "name is required"}), 400
        
        # Validate HS6 codes
        if hs6_codes:
            for hs6 in hs6_codes:
                if not isinstance(hs6, str) or len(hs6) != 6 or not hs6.isdigit():
                    return jsonify({"error": f"Invalid HS6 code: {hs6}"}), 400
        
        result = watchlist_manager.create_watchlist(user_id, name, hs6_codes, port_codes, rules)
        
        if "error" in result:
            return jsonify(result), 500
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Failed to create watchlist: {e}")
        return jsonify({"error": "Failed to create watchlist"}), 500

@app.route('/watchlists', methods=['GET'])
def get_watchlists():
    """
    Get watchlists
    
    Query parameters:
    - user_id (optional): Get watchlists for specific user
    - id (optional): Get specific watchlist by ID
    """
    if not watchlist_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    user_id = request.args.get('user_id')
    watchlist_id = request.args.get('id')
    
    if watchlist_id:
        try:
            watchlist_id = int(watchlist_id)
        except ValueError:
            return jsonify({"error": "Invalid watchlist ID"}), 400
    
    result = watchlist_manager.get_watchlists(user_id, watchlist_id)
    
    if "error" in result:
        return jsonify(result), 404 if "not found" in result["error"].lower() else 500
    
    return jsonify(result)

@app.route('/watchlists/<int:watchlist_id>', methods=['PUT'])
def update_watchlist(watchlist_id):
    """
    Update an existing watchlist
    
    JSON Body (all optional):
    - name: New watchlist name
    - hs6: New array of HS6 codes
    - ports: New array of port codes  
    - rules: New rules JSON object
    """
    if not watchlist_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        name = data.get('name')
        hs6_codes = data.get('hs6')
        port_codes = data.get('ports')
        rules = data.get('rules')
        user_id = data.get('user_id')  # Optional for access control
        
        # Validate HS6 codes if provided
        if hs6_codes:
            for hs6 in hs6_codes:
                if not isinstance(hs6, str) or len(hs6) != 6 or not hs6.isdigit():
                    return jsonify({"error": f"Invalid HS6 code: {hs6}"}), 400
        
        result = watchlist_manager.update_watchlist(watchlist_id, user_id, name, hs6_codes, port_codes, rules)
        
        if "error" in result:
            status_code = 404 if "not found" in result["error"].lower() else \
                         403 if "access denied" in result["error"].lower() else 500
            return jsonify(result), status_code
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to update watchlist: {e}")
        return jsonify({"error": "Failed to update watchlist"}), 500

@app.route('/watchlists/<int:watchlist_id>', methods=['DELETE'])
def delete_watchlist(watchlist_id):
    """
    Delete a watchlist
    
    Query parameters:
    - user_id (optional): User ID for access control
    """
    if not watchlist_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    user_id = request.args.get('user_id')
    
    result = watchlist_manager.delete_watchlist(watchlist_id, user_id)
    
    if "error" in result:
        status_code = 404 if "not found" in result["error"].lower() else \
                     403 if "access denied" in result["error"].lower() else 500
        return jsonify(result), status_code
    
    return jsonify(result)

@app.route('/alerts', methods=['POST'])
def generate_alerts():
    """
    Generate alerts for watchlists
    
    JSON Body (optional):
    - user_id: Generate alerts for specific user's watchlists
    - watchlist_id: Generate alerts for specific watchlist
    """
    if not alert_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        watchlist_id = data.get('watchlist_id')
        
        if watchlist_id:
            try:
                watchlist_id = int(watchlist_id)
            except ValueError:
                return jsonify({"error": "Invalid watchlist ID"}), 400
        
        result = alert_manager.generate_alerts(watchlist_id, user_id)
        
        if "error" in result:
            return jsonify(result), 500
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Failed to generate alerts: {e}")
        return jsonify({"error": "Failed to generate alerts"}), 500

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Get alerts
    
    Query parameters:
    - user_id (optional): Get alerts for specific user
    - watchlist_id (optional): Get alerts for specific watchlist
    - alert_type (optional): Filter by alert type ('mom_change', 'volume_threshold')
    - limit (optional): Max records to return (default: 100)
    """
    if not alert_manager:
        return jsonify({"error": "Database not configured"}), 500
    
    user_id = request.args.get('user_id')
    watchlist_id = request.args.get('watchlist_id')
    alert_type = request.args.get('alert_type')
    limit = int(request.args.get('limit', 100))
    
    if watchlist_id:
        try:
            watchlist_id = int(watchlist_id)
        except ValueError:
            return jsonify({"error": "Invalid watchlist ID"}), 400
    
    if alert_type and alert_type not in ['mom_change', 'volume_threshold']:
        return jsonify({"error": "Invalid alert_type. Must be 'mom_change' or 'volume_threshold'"}), 400
    
    if limit > 1000:
        return jsonify({"error": "limit cannot exceed 1000"}), 400
    
    result = alert_manager.get_alerts(user_id, watchlist_id, alert_type, limit)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)

if __name__ == '__main__':
    # Get host and port from environment variables
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(debug=debug, host=host, port=port)
