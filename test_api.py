#!/usr/bin/env python3
"""
Test script for PortRadar Census API functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import CensusTradeAPI

def test_census_api():
    """Test the Census API integration"""
    print("Testing PortRadar Census API Integration...")
    print("=" * 50)
    
    api = CensusTradeAPI()
    
    # Test 1: Fetch data for HS6 850760 (from requirements example)
    print("\nTest 1: Fetching imports data for HS6 850760 from 2024-01")
    result = api.fetch_trade_data('850760', '2024-01', trade_type='imports')
    
    if result.get('success'):
        print(f"✅ Success! Found {result['count']} records")
        if result['data']:
            sample = result['data'][0]
            print(f"Sample record: Port {sample.get('PORT')} - {sample.get('PORT_NAME')}")
            print(f"Value: ${sample.get('GEN_VAL_MO', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Test 2: Test with different HS6 and exports
    print("\nTest 2: Testing exports data for HS6 850760")
    result = api.fetch_trade_data('850760', '2024-01', trade_type='exports')
    
    if result.get('success'):
        print(f"✅ Success! Found {result['count']} export records")
        if result['data']:
            sample = result['data'][0]
            print(f"Sample record: Port {sample.get('PORT')} - {sample.get('PORT_NAME')}")
            print(f"Value: ${sample.get('ALL_VAL_MO', 'N/A')}")
    else:
        print(f"⚠️ Expected behavior - Error or no data: {result.get('error', 'No data found')}")
    
    # Test 3: Test with invalid HS6
    print("\nTest 3: Testing error handling with invalid HS6")
    result = api.fetch_trade_data('123456', '2024-01', trade_type='imports')
    
    if result.get('success'):
        print(f"✅ API returned data for test HS6: {result['count']} records")
    else:
        print(f"⚠️ Expected behavior - Error or no data: {result.get('error', 'No data found')}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_census_api()
