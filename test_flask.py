#!/usr/bin/env python3
"""
Test the Flask app endpoints by importing the app directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
import json

def test_flask_endpoints():
    """Test Flask app endpoints without running the server"""
    print("Testing PortRadar Flask API Endpoints...")
    print("=" * 50)
    
    with app.test_client() as client:
        # Test 1: Root endpoint
        print("\nTest 1: GET /")
        response = client.get('/')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"✅ Success! Message: {data.get('message', 'N/A')}")
        else:
            print(f"❌ Failed: {response.data}")
        
        # Test 2: Health endpoint
        print("\nTest 2: GET /health")
        response = client.get('/health')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"✅ Success! Status: {data.get('status', 'N/A')}")
        else:
            print(f"❌ Failed: {response.data}")
        
        # Test 3: Trade data endpoint - imports
        print("\nTest 3: GET /trade-data?hs6=850760&time_from=2024-01&trade_type=imports")
        response = client.get('/trade-data?hs6=850760&time_from=2024-01&trade_type=imports')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ Success! Found {count} records")
            if count > 0 and 'data' in data:
                sample = data['data'][0]
                port_name = sample.get('PORT_NAME', 'N/A')
                value = sample.get('GEN_VAL_MO', 'N/A')
                print(f"   Sample: {port_name}, Value: ${value}")
        else:
            print(f"❌ Failed: {response.data}")
        
        # Test 4: Trade data endpoint - exports
        print("\nTest 4: GET /trade-data?hs6=850760&time_from=2024-01&trade_type=exports")
        response = client.get('/trade-data?hs6=850760&time_from=2024-01&trade_type=exports')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ Success! Found {count} export records")
            if count > 0 and 'data' in data:
                sample = data['data'][0]
                port_name = sample.get('PORT_NAME', 'N/A')
                value = sample.get('ALL_VAL_MO', 'N/A')
                print(f"   Sample: {port_name}, Value: ${value}")
        else:
            print(f"❌ Failed: {response.data}")
        
        # Test 5: Error handling - invalid HS6
        print("\nTest 5: GET /trade-data?hs6=invalid")
        response = client.get('/trade-data?hs6=invalid')
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            data = response.get_json()
            print(f"✅ Success! Proper error handling: {data.get('error', 'N/A')}")
        else:
            print(f"❌ Unexpected response: {response.data}")
        
        # Test 6: Test API endpoint
        print("\nTest 6: GET /test-api")
        response = client.get('/test-api')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ Success! Test API returned {count} records")
        else:
            print(f"❌ Failed: {response.data}")
        
        # Test 7: Database connectivity
        print("\nTest 7: GET /test-db")
        response = client.get('/test-db')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"✅ Success! Database connection: {data.get('message')}")
            print(f"   Tables: {data.get('tables', [])}")
        else:
            print(f"❌ Failed: {response.data}")
        
        # Test 8: Query stored data
        print("\nTest 8: GET /stored-data")
        response = client.get('/stored-data?limit=3')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            count = data.get('count', 0)
            print(f"✅ Success! Found {count} stored records")
            if count > 0:
                sample = data['data'][0]
                print(f"   Sample: {sample.get('port_code')} - ${sample.get('value_usd')}")
        else:
            print(f"❌ Failed: {response.data}")
    
    print("\n" + "=" * 50)
    print("Flask endpoint testing completed!")

if __name__ == "__main__":
    test_flask_endpoints()
