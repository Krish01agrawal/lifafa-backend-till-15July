"""
Script to process financial transactions for a user
This will analyze raw emails and extract financial transaction data
"""

import requests
import json

def process_financial_transactions(jwt_token, base_url="http://localhost:8001"):
    """
    Process financial transactions for the authenticated user
    """
    print("🔄 Processing financial transactions from your emails...")
    print(f"📡 Server: {base_url}")
    print(f"🔑 JWT Token: {jwt_token[:50]}..." if jwt_token else "❌ No JWT token")
    
    if not jwt_token:
        print("❌ Error: JWT token is required")
        return False
    
    # Call the financial processing endpoint
    endpoint_url = f"{base_url}/financial/process"
    payload = {"jwt_token": jwt_token}
    
    try:
        print(f"📤 Making POST request to: {endpoint_url}")
        response = requests.post(
            endpoint_url, 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📥 Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS! Financial transactions processed successfully")
            print(f"📊 Processing Results:")
            
            # Show results from the processing
            processing_data = data.get('data', {})
            print(f"   - Status: {processing_data.get('status', 'unknown')}")
            print(f"   - User ID: {processing_data.get('user_id', 'unknown')}")
            print(f"   - Transactions Found: {processing_data.get('transactions_found', 0)}")
            print(f"   - Total Amount: ₹{processing_data.get('total_amount', 0)}")
            print(f"   - Period: {processing_data.get('period', 'unknown')}")
            
            # Save processing result
            with open('financial_processing_result.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"💾 Processing result saved to: financial_processing_result.json")
            
            print("\n🎉 Now you can call the /financial/transactions/all endpoint!")
            return True
            
        else:
            print(f"❌ ERROR! Status Code: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Could not connect to {base_url}")
        print("   Make sure the FastAPI server is running on the correct port")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("🔥 FINANCIAL TRANSACTION PROCESSOR")
    print("=" * 60)
    print("This script will process your raw emails and extract financial transactions")
    print("You need to run this BEFORE calling /financial/transactions/all")
    print()
    
    # Get JWT token from user
    jwt_token = input("🔑 Enter your JWT token: ").strip()
    
    if jwt_token:
        success = process_financial_transactions(jwt_token)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ FINANCIAL PROCESSING COMPLETED!")
            print("=" * 60)
            print("Now you can test the financial transactions API:")
            print("python3 test_financial_api.py")
            print()
            print("Or call directly in Postman:")
            print("GET http://localhost:8001/financial/transactions/all?jwt_token=YOUR_JWT_TOKEN")
        else:
            print("\n" + "=" * 60)
            print("❌ FINANCIAL PROCESSING FAILED!")
            print("=" * 60)
            print("Please check the error messages above and try again.")
    else:
        print("⏭️  No JWT token provided. Exiting...")

if __name__ == "__main__":
    main() 