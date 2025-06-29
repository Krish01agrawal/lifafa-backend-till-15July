#!/usr/bin/env python3
"""
🚀 Gmail Data Download API Test Script

This script tests the new /gmail/download-data endpoint that downloads
Gmail data for the last 6 months in JSON format.

Features tested:
- JWT token validation
- Gmail data fetching
- JSON response format
- Error handling
- Data completeness
"""

import requests
import json
import os
import sys
from datetime import datetime
import time

# Configuration
BASE_URL = "http://localhost:8001"
TEST_JWT_TOKEN = None  # Will be set from environment or user input

def get_test_jwt_token():
    """Get JWT token for testing"""
    global TEST_JWT_TOKEN
    
    # Try to get from environment
    TEST_JWT_TOKEN = os.getenv("TEST_JWT_TOKEN")
    
    if not TEST_JWT_TOKEN:
        print("🔐 No JWT token found in environment variable TEST_JWT_TOKEN")
        TEST_JWT_TOKEN = input("Please enter your JWT token: ").strip()
    
    if not TEST_JWT_TOKEN:
        print("❌ No JWT token provided. Cannot proceed with tests.")
        sys.exit(1)
    
    print(f"✅ JWT token loaded (length: {len(TEST_JWT_TOKEN)} chars)")

def test_health_check():
    """Test if the backend is running"""
    print("\n🏥 Testing backend health...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            print("✅ Backend is healthy")
            health_data = response.json()
            print(f"   - Version: {health_data.get('_version', 'unknown')}")
            print(f"   - Status: {health_data.get('status', 'unknown')}")
            return True
        else:
            print(f"⚠️ Backend health check returned: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def test_gmail_download_api():
    """Test the Gmail data download API"""
    print("\n📧 Testing Gmail data download API...")
    
    # Prepare request payload
    payload = {
        "jwt_token": TEST_JWT_TOKEN
    }
    
    try:
        print("🔄 Sending download request...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/gmail/download-data",
            json=payload,
            timeout=300  # 5 minutes timeout for large data downloads
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️ Request completed in {duration:.2f} seconds")
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("✅ Gmail data download successful!")
            
            # Parse JSON response
            try:
                data = response.json()
                
                # Analyze response structure
                print("\n📋 Response Analysis:")
                print(f"   - Status: {data.get('status', 'unknown')}")
                print(f"   - Total emails: {data.get('data_info', {}).get('total_emails', 0)}")
                print(f"   - Date range: {data.get('data_info', {}).get('date_range', 'unknown')}")
                print(f"   - Data completeness: {data.get('data_info', {}).get('data_completeness', 'unknown')}")
                
                # User info
                user_info = data.get('user_info', {})
                print(f"   - User email: {user_info.get('email', 'unknown')}")
                print(f"   - User name: {user_info.get('name', 'unknown')}")
                
                # Extraction stats
                extraction_stats = data.get('extraction_stats', {})
                if extraction_stats:
                    print(f"   - Emails processed: {extraction_stats.get('total_processed', 0)}")
                    print(f"   - Complete data extracted: {extraction_stats.get('complete_data_extracted', 0)}")
                    print(f"   - Financial emails found: {extraction_stats.get('financial_emails', 0)}")
                
                # Sample first email
                emails = data.get('emails', [])
                if emails:
                    sample_email = emails[0]
                    print(f"\n📧 Sample Email:")
                    print(f"   - Subject: {sample_email.get('subject', 'No Subject')[:50]}...")
                    print(f"   - Sender: {sample_email.get('sender', 'Unknown')}")
                    print(f"   - Date: {sample_email.get('date', 'Unknown')}")
                    print(f"   - Has body: {'body' in sample_email}")
                    print(f"   - Has headers: {'headers' in sample_email}")
                    print(f"   - Financial: {sample_email.get('financial', False)}")
                    print(f"   - Importance score: {sample_email.get('importance_score', 0)}")
                
                # Metadata
                metadata = data.get('metadata', {})
                print(f"\n🔧 Metadata:")
                print(f"   - API version: {metadata.get('api_version', 'unknown')}")
                print(f"   - Format: {metadata.get('format', 'unknown')}")
                print(f"   - Includes: {', '.join(metadata.get('includes', []))}")
                
                # Save sample to file
                save_sample_data(data)
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing JSON response: {e}")
                print(f"📄 Raw response (first 500 chars): {response.text[:500]}")
                return False
        
        elif response.status_code == 401:
            print("❌ Authentication failed - Invalid JWT token")
            print(f"📄 Error: {response.text}")
            return False
            
        elif response.status_code == 404:
            print("❌ User not found")
            print(f"📄 Error: {response.text}")
            return False
            
        elif response.status_code == 500:
            print("❌ Internal server error")
            print(f"📄 Error: {response.text}")
            return False
            
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout - Gmail data download took too long")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def save_sample_data(data):
    """Save a sample of the downloaded data to file"""
    try:
        # Create a sample with first 3 emails
        sample_data = {
            "status": data.get("status"),
            "user_info": data.get("user_info"),
            "data_info": data.get("data_info"),
            "emails": data.get("emails", [])[:3],  # First 3 emails only
            "extraction_stats": data.get("extraction_stats"),
            "metadata": data.get("metadata"),
            "sample_note": "This is a sample containing only the first 3 emails"
        }
        
        filename = f"gmail_download_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Sample data saved to: {filename}")
        
    except Exception as e:
        print(f"⚠️ Could not save sample data: {e}")

def test_error_scenarios():
    """Test various error scenarios"""
    print("\n🧪 Testing error scenarios...")
    
    # Test with invalid JWT token
    print("\n1️⃣ Testing invalid JWT token...")
    invalid_payload = {"jwt_token": "invalid_token_123"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/gmail/download-data",
            json=invalid_payload,
            timeout=30
        )
        
        if response.status_code == 401:
            print("✅ Invalid JWT token correctly rejected")
        else:
            print(f"⚠️ Unexpected response for invalid token: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing invalid token: {e}")
    
    # Test with missing JWT token
    print("\n2️⃣ Testing missing JWT token...")
    empty_payload = {}
    
    try:
        response = requests.post(
            f"{BASE_URL}/gmail/download-data",
            json=empty_payload,
            timeout=30
        )
        
        if response.status_code in [400, 422]:  # FastAPI validation error
            print("✅ Missing JWT token correctly rejected")
        else:
            print(f"⚠️ Unexpected response for missing token: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing missing token: {e}")

def main():
    """Main test function"""
    print("🚀 Gmail Data Download API Test Suite")
    print("=" * 50)
    
    # Get JWT token
    get_test_jwt_token()
    
    # Test backend health
    if not test_health_check():
        print("❌ Backend is not healthy. Please start the backend server.")
        sys.exit(1)
    
    # Test the main API
    success = test_gmail_download_api()
    
    # Test error scenarios
    test_error_scenarios()
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("✅ Gmail Data Download API tests completed successfully!")
        print("\n📋 API Summary:")
        print("   - Endpoint: POST /gmail/download-data")
        print("   - Authentication: JWT token required")
        print("   - Data range: Last 6 months")
        print("   - Format: Complete JSON with headers, body, attachments")
        print("   - Features: Financial classification, importance scoring")
    else:
        print("❌ Some tests failed. Please check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 