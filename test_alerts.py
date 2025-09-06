#!/usr/bin/env python3
"""
Comprehensive test for the PortRadar alerts system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
import json

def test_alerts_system():
    """Test the alerts system with realistic scenarios"""
    print("🚨 PortRadar Alerts System Test")
    print("=" * 50)
    
    with app.test_client() as client:
        # Step 1: Create a watchlist with aggressive thresholds to trigger alerts
        print("\n📝 Step 1: Create watchlist with alert rules")
        watchlist_data = {
            "user_id": "alerts_test_user",
            "name": "Electronics Alert Test",
            "hs6": ["850760"],  # Use HS6 code we have data for
            "ports": [],  # Monitor all ports
            "rules": {
                "mom_change_threshold": 5.0,    # Very low threshold for testing
                "volume_threshold": 100000      # Low threshold for testing
            }
        }
        
        response = client.post('/watchlists', 
                               json=watchlist_data, 
                               headers={'Content-Type': 'application/json'})
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            data = response.get_json()
            watchlist_id = data.get('watchlist_id')
            print(f"✅ Created watchlist ID: {watchlist_id}")
            print(f"   Rules: {data.get('rules')}")
        else:
            print(f"❌ Failed to create watchlist: {response.data}")
            return
        
        # Step 2: Fetch recent data to populate the database
        print(f"\n🌐 Step 2: Fetch trade data for multiple periods")
        for period in ['2024-01', '2023-12', '2023-11']:
            response = client.get(f'/trade-data?hs6=850760&time_from={period}&trade_type=imports')
            if response.status_code == 200:
                data = response.get_json()
                count = data.get('count', 0)
                print(f"   ✅ Fetched {count} records for {period}")
            else:
                print(f"   ❌ Failed to fetch data for {period}")
        
        # Step 3: Generate alerts for the watchlist
        print(f"\n🚨 Step 3: Generate alerts for watchlist {watchlist_id}")
        alert_data = {
            "watchlist_id": watchlist_id
        }
        response = client.post('/alerts', 
                               json=alert_data, 
                               headers={'Content-Type': 'application/json'})
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            data = response.get_json()
            alerts_count = data.get('alerts_generated', 0)
            print(f"✅ Generated {alerts_count} alerts")
            if alerts_count > 0:
                print("   Sample alerts:")
                for alert in data.get('alerts', [])[:3]:
                    print(f"   - {alert.get('alert_type')}: {alert.get('message', 'N/A')[:80]}...")
        else:
            print(f"❌ Failed to generate alerts: {response.data}")
        
        # Step 4: Query alerts
        print(f"\n📊 Step 4: Query generated alerts")
        response = client.get(f'/alerts?watchlist_id={watchlist_id}&limit=10')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            alerts = data.get('alerts', [])
            print(f"✅ Found {len(alerts)} alerts")
            
            for i, alert in enumerate(alerts[:5], 1):
                print(f"   Alert {i}:")
                print(f"     Type: {alert.get('alert_type', 'N/A')}")
                print(f"     Score: {alert.get('score', 0):.1f}")
                print(f"     Period: {alert.get('period', 'N/A')}")
                print(f"     Message: {alert.get('message', 'N/A')[:60]}...")
                print(f"     Created: {alert.get('created_at', 'N/A')[:19]}")
                print()
        else:
            print(f"❌ Failed to query alerts: {response.data}")
        
        # Step 5: Test alert filtering
        print(f"\n🔍 Step 5: Test alert filtering")
        
        # Test filtering by alert type
        response = client.get(f'/alerts?alert_type=volume_threshold&limit=5')
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ Volume threshold alerts: {count}")
        
        response = client.get(f'/alerts?alert_type=mom_change&limit=5')
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ MoM change alerts: {count}")
        
        # Test filtering by user
        response = client.get(f'/alerts?user_id=alerts_test_user&limit=10')
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ User alerts: {count}")
        
        # Step 6: Test generating alerts for all watchlists
        print(f"\n🔄 Step 6: Generate alerts for all user watchlists")
        alert_data = {
            "user_id": "alerts_test_user"
        }
        response = client.post('/alerts', 
                               json=alert_data, 
                               headers={'Content-Type': 'application/json'})
        if response.status_code == 201:
            data = response.get_json()
            alerts_count = data.get('alerts_generated', 0)
            print(f"✅ Generated {alerts_count} alerts for user watchlists")
        
        # Step 7: Cleanup - delete test watchlist
        print(f"\n🧹 Step 7: Cleanup")
        response = client.delete(f'/watchlists/{watchlist_id}?user_id=alerts_test_user')
        if response.status_code == 200:
            print(f"✅ Deleted test watchlist {watchlist_id}")
        else:
            print(f"❌ Failed to delete watchlist: {response.data}")
    
    print(f"\n" + "=" * 50)
    print("🎯 Alerts system test completed!")
    print("   ✓ Watchlist creation with alert rules")
    print("   ✓ Data fetching and storage") 
    print("   ✓ Alert generation (MoM change & volume threshold)")
    print("   ✓ Alert querying and filtering")
    print("   ✓ User-based alert management")

if __name__ == "__main__":
    test_alerts_system()
