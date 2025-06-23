#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mem0_agent import query_email_database

async def test_agents():
    try:
        print("🧪 Testing Gmail Agent System...")
        
        # Test a simple query
        result = await query_email_database('test_user', 'food orders')
        
        print("✅ Query test successful!")
        print(f"Result type: {type(result)}")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            print("🎉 Agents are working correctly!")
        else:
            print(f"⚠️ Warning: {result.get('error', 'Unknown issue')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agents()) 