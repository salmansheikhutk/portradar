#!/usr/bin/env python3
"""Test the /refresh-data endpoint"""

import requests
import json
import time

def test_refresh_endpoint():
    """Test the refresh-data endpoint"""
    print("Testing /refresh-data endpoint...")
    
    try:
        # Give the server a moment to be ready
        time.sleep(2)
        
        response = requests.get('http://localhost:5000/refresh-data', timeout=120)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success!")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (this is expected for large data fetches)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_refresh_endpoint()
