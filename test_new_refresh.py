#!/usr/bin/env python3
"""Test script to verify the new fetch_all_port_commodities method works"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import the CensusAPI class from app.py
try:
    # We need to mock the logger and db_manager for testing
    import logging
    logger = logging.getLogger(__name__)
    
    class MockDBManager:
        def store_trade_data(self, data, trade_type, hs6, time_period):
            print(f"MockDB: Would store {len(data)} records for {trade_type}")
            return {"stored_count": len(data)}
    
    db_manager = MockDBManager()
    
    # Import the CensusAPI class
    from app import CensusTradeAPI
    
    # Create API instance
    census_api = CensusTradeAPI()
    
    # Test fetching all commodities for LA port
    print("Testing fetch_all_port_commodities for LA port (2010)...")
    result = census_api.fetch_all_port_commodities('2010', '2025-06')
    
    if result.get('success'):
        data = result['data']
        print(f"✅ Successfully fetched {len(data)} commodities!")
        
        # Show first 10 commodities
        print("\nFirst 10 commodities:")
        for i, record in enumerate(data[:10]):
            commodity_code = record.get('I_COMMODITY', 'N/A')
            commodity_desc = record.get('I_COMMODITY_LDESC', 'N/A')[:50]
            value = record.get('GEN_VAL_MO', 'N/A')
            print(f"  {i+1}. {commodity_code}: {commodity_desc}... (${value})")
        
        # Show unique commodity codes count
        unique_codes = set(record.get('I_COMMODITY', '') for record in data)
        print(f"\n📊 Total unique commodity codes: {len(unique_codes)}")
        
        # Show sample codes
        sample_codes = list(unique_codes)[:20]
        print(f"Sample codes: {sample_codes}")
        
    else:
        print(f"❌ Error: {result.get('error')}")
        
except Exception as e:
    print(f"❌ Error running test: {e}")
    import traceback
    traceback.print_exc()
