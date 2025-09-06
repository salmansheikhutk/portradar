#!/usr/bin/env python3
"""
Manual alert generation test with specific data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, alert_manager
import json

def test_manual_alert_generation():
    """Manually test alert generation with the actual data we have"""
    print("🔍 Manual Alert Generation Test")
    print("=" * 50)
    
    with app.test_client() as client:
        # Create watchlist with very low thresholds
        print("\n📝 Step 1: Create watchlist with very low thresholds")
        watchlist_data = {
            "user_id": "manual_test_user",
            "name": "Manual Test Watchlist",
            "hs6": ["850760"],
            "ports": [],  # All ports
            "rules": {
                "mom_change_threshold": 1.0,    # 1% threshold (very low)
                "volume_threshold": 1000000     # $1M threshold
            }
        }
        
        response = client.post('/watchlists', 
                               json=watchlist_data, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 201:
            data = response.get_json()
            watchlist_id = data.get('watchlist_id')
            print(f"✅ Created watchlist ID: {watchlist_id}")
        else:
            print(f"❌ Failed: {response.data}")
            return
        
        # Manually test the alert generation logic
        print(f"\n🧪 Step 2: Test alert generation logic manually")
        try:
            result = alert_manager.generate_alerts(watchlist_id=watchlist_id)
            print(f"Alert generation result: {result}")
            
            if result.get('success'):
                alerts_count = result.get('alerts_generated', 0)
                print(f"✅ Generated {alerts_count} alerts")
                
                if alerts_count > 0:
                    for i, alert in enumerate(result.get('alerts', [])[:3], 1):
                        print(f"\n   Alert {i}:")
                        print(f"     Type: {alert.get('alert_type')}")
                        print(f"     HS6: {alert.get('hs6')}")
                        print(f"     Port: {alert.get('port_code')}")
                        print(f"     Period: {alert.get('period')}")
                        print(f"     Value: ${alert.get('value_usd', 0):,.0f}")
                        print(f"     Score: {alert.get('score', 0):.1f}")
                        print(f"     Message: {alert.get('message', 'N/A')}")
                else:
                    print("   No alerts generated - checking why...")
                    
            else:
                print(f"❌ Alert generation failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Exception in alert generation: {e}")
            
        # Query alerts from database
        print(f"\n📊 Step 3: Query alerts from database")
        response = client.get(f'/alerts?watchlist_id={watchlist_id}&limit=20')
        if response.status_code == 200:
            data = response.get_json()
            alerts = data.get('alerts', [])
            print(f"Found {len(alerts)} alerts in database")
            
            for alert in alerts[:5]:
                print(f"   - {alert.get('alert_type', 'N/A')}: {alert.get('message', 'No message')}")
        else:
            print(f"❌ Failed to query alerts: {response.data}")
        
        # Cleanup
        print(f"\n🧹 Step 4: Cleanup")
        client.delete(f'/watchlists/{watchlist_id}?user_id=manual_test_user')
        print("✅ Cleaned up test watchlist")

if __name__ == "__main__":
    test_manual_alert_generation()
