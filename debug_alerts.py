#!/usr/bin/env python3
"""
Debug the alert generation process
"""

import psycopg
import os
from dotenv import load_dotenv
import json

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

def debug_alert_generation():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            # Create a test watchlist
            cursor.execute("""
                INSERT INTO watchlists (user_id, name, hs6, ports, rules_json, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, ("debug_user", "Debug Watchlist", ["850760"], [], json.dumps({
                "mom_change_threshold": 5.0,
                "volume_threshold": 1000000
            })))
            
            watchlist_id = cursor.fetchone()[0]
            print(f"Created debug watchlist {watchlist_id}")
            
            # Check what data we have for MoM comparison
            print("\n=== Debug MoM Change Logic ===")
            cursor.execute("""
                SELECT port_code, period, value_usd
                FROM trade_monthly
                WHERE hs6 = %s
                ORDER BY period DESC
                LIMIT 100
            """, ("850760",))
            
            rows = cursor.fetchall()
            print(f"Found {len(rows)} records for HS6 850760")
            
            # Group by port and show data
            port_data = {}
            for port_code, period, value_usd in rows:
                if port_code not in port_data:
                    port_data[port_code] = []
                port_data[port_code].append((period, float(value_usd or 0)))
            
            print("\nPort data for MoM analysis:")
            alerts_found = 0
            threshold = 5.0
            
            for port_code, data_points in port_data.items():
                if len(data_points) < 2:
                    print(f"  {port_code}: Only {len(data_points)} data points - skipping")
                    continue
                
                # Sort by period (most recent first)
                data_points.sort(key=lambda x: x[0], reverse=True)
                current_value = data_points[0][1]
                previous_value = data_points[1][1]
                current_period = data_points[0][0]
                
                if previous_value == 0:
                    print(f"  {port_code}: Previous value is 0 - skipping")
                    continue
                
                # Calculate percentage change
                pct_change = ((current_value - previous_value) / previous_value) * 100
                
                print(f"  {port_code}: {current_period} = ${current_value:,.0f} vs previous ${previous_value:,.0f}")
                print(f"    Change: {pct_change:.2f}%")
                
                if abs(pct_change) >= threshold:
                    print(f"    🚨 ALERT! Change {abs(pct_change):.1f}% exceeds threshold {threshold}%")
                    alerts_found += 1
                else:
                    print(f"    ✅ No alert - change {abs(pct_change):.1f}% below threshold {threshold}%")
            
            print(f"\nExpected alerts from MoM analysis: {alerts_found}")
            
            # Check volume threshold logic
            print(f"\n=== Debug Volume Threshold Logic ===")
            volume_threshold = 1000000
            cursor.execute("""
                SELECT port_code, period, value_usd
                FROM trade_monthly
                WHERE hs6 = %s
                AND period >= (CURRENT_DATE - INTERVAL '12 months')
                AND value_usd > %s
                ORDER BY value_usd DESC
                LIMIT 10
            """, ("850760", volume_threshold))
            
            volume_rows = cursor.fetchall()
            print(f"Records exceeding ${volume_threshold:,} threshold: {len(volume_rows)}")
            
            for port_code, period, value_usd in volume_rows:
                print(f"  {port_code} | {period} | ${value_usd:,.0f}")
            
            # Clean up
            cursor.execute("DELETE FROM watchlists WHERE id = %s", (watchlist_id,))
            conn.commit()
            print(f"\nCleaned up debug watchlist {watchlist_id}")

if __name__ == "__main__":
    debug_alert_generation()
