import psycopg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cursor:
        # Check actual values with proper handling of nulls
        cursor.execute("""
            SELECT hs6, port_code, period, 
                   COALESCE(value_usd, 0) as value_usd
            FROM trade_monthly 
            WHERE hs6 = '850760' AND COALESCE(value_usd, 0) > 0
            ORDER BY value_usd DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        print('Top 10 non-zero value trade records:')
        for hs6, port_code, period, value_usd in rows:
            print(f'  {period} | {port_code} | HS6:{hs6} | ${value_usd:,.0f}')
        
        # Count records by value
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN value_usd IS NULL THEN 1 END) as null_values,
                COUNT(CASE WHEN value_usd = 0 THEN 1 END) as zero_values,
                COUNT(CASE WHEN value_usd > 0 THEN 1 END) as positive_values,
                MIN(CASE WHEN value_usd > 0 THEN value_usd END) as min_positive,
                MAX(value_usd) as max_value
            FROM trade_monthly 
            WHERE hs6 = '850760'
        """)
        result = cursor.fetchone()
        null_count, zero_count, positive_count, min_pos, max_val = result
        print(f'\nValue distribution for HS6 850760:')
        print(f'  NULL values: {null_count}')
        print(f'  Zero values: {zero_count}')  
        print(f'  Positive values: {positive_count}')
        print(f'  Min positive: ${min_pos or 0:,.0f}')
        print(f'  Max value: ${max_val or 0:,.0f}')
