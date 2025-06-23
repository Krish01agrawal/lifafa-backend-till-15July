#!/usr/bin/env python3
"""
Quick test script to verify the fixed API endpoints work properly
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8001"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTE3Njk0MDQ5NzU1NDA4NDA3NTc1IiwiZW1haWwiOiJpdHNrYXNoeWFwMjZAZ21haWwuY29tIiwiZXhwIjoxNzU3OTIyNTA1fQ.A42jdJcl5xuL9YPnjwi7VM2ox-iChiD4XEzRfOlCPfg"

def test_process_from_emails():
    """Test the POST /financial/process-from-emails endpoint"""
    print("🧪 Testing POST /financial/process-from-emails endpoint...")
    
    url = f"{BASE_URL}/financial/process-from-emails"
    payload = {"jwt_token": JWT_TOKEN}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS - Process from emails endpoint working!")
            print(f"Transactions found: {data.get('transactions_found', 0)}")
            print(f"Total amount: ₹{data.get('total_amount', 0):.2f}")
            return True
        else:
            print(f"❌ ERROR - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR - Request failed: {e}")
        return False

def test_get_all_transactions():
    """Test the GET /financial/transactions/all endpoint"""
    print("🧪 Testing GET /financial/transactions/all endpoint...")
    
    url = f"{BASE_URL}/financial/transactions/all"
    params = {"jwt_token": JWT_TOKEN}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS - Get all transactions endpoint working!")
            print(f"Total transactions: {len(data.get('transactions', []))}")
            print(f"Total amount: ₹{data.get('analytics', {}).get('total_amount', 0):.2f}")
            return True
        else:
            print(f"❌ ERROR - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR - Request failed: {e}")
        return False

def main():
    """Run the tests"""
    print("🚀 Testing Fixed Financial API Endpoints")
    print("=" * 50)
    
    # Test processing endpoint
    process_success = test_process_from_emails()
    print()
    
    # Test retrieval endpoint
    get_success = test_get_all_transactions()
    print()
    
    # Summary
    print("📊 Test Results Summary:")
    print("=" * 30)
    print(f"Process from emails: {'✅ PASS' if process_success else '❌ FAIL'}")
    print(f"Get all transactions: {'✅ PASS' if get_success else '❌ FAIL'}")
    
    if process_success and get_success:
        print("\n🎉 All tests passed! The ObjectId serialization issue is fixed!")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main() 