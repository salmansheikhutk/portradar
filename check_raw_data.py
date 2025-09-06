import psycopg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cursor:
        # Check data for port 2704 with explicit casting
        cursor.execute("""
            SELECT port_code, period, COALESCE(value_usd, 0) as value_usd
            FROM trade_monthly
            WHERE hs6 = '850760' AND port_code = '2704'
            ORDER BY period DESC
        """)
        rows = cursor.fetchall()
        print('Port 2704 data (with coalesce):')
        for port_code, period, value_usd in rows:
            print(f'  {port_code} | {period} | ${float(value_usd or 0):,.0f}')
        
        # Show the raw data types
        cursor.execute("""
            SELECT port_code, period, value_usd, pg_typeof(value_usd)
            FROM trade_monthly
            WHERE hs6 = '850760' AND port_code = '2704'
            ORDER BY period DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        print('\nRaw data with types:')
        for port_code, period, value_usd, data_type in rows:
            print(f'  {port_code} | {period} | {value_usd} ({data_type})')
