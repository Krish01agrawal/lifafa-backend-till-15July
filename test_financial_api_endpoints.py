"""
Test script for the new Financial API Endpoints
==============================================

This script tests:
1. POST /financial/process-from-emails (Fast processing)
2. GET /financial/transactions/all (Retrieve transactions)
"""

import requests
import json
from datetime import datetime

class FinancialAPIEndpointTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
    
    def test_fast_processing_endpoint(self, jwt_token):
        """
        Test the fast financial processing endpoint
        POST /financial/process-from-emails
        """
        print("🚀 Testing FAST Financial Processing Endpoint...")
        print(f"📡 Endpoint: POST {self.base_url}/financial/process-from-emails")
        
        if not jwt_token:
            print("❌ Error: JWT token is required")
            return False
        
        # Prepare payload
        payload = {"jwt_token": jwt_token}
        
        try:
            print(f"📤 Making POST request...")
            response = requests.post(
                f"{self.base_url}/financial/process-from-emails",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📥 Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS! Fast financial processing completed")
                print(f"📊 Processing Results:")
                print(f"   - Message: {data.get('message', 'No message')}")
                print(f"   - Processing Method: {data.get('processing_method', 'unknown')}")
                print(f"   - Speed: {data.get('speed', 'unknown')}")
                
                # Show processing data
                processing_data = data.get('data', {})
                if processing_data:
                    print(f"   - User ID: {processing_data.get('user_id', 'unknown')}")
                    print(f"   - Transactions Found: {processing_data.get('transactions_found', 0)}")
                    print(f"   - Total Amount: ₹{processing_data.get('total_amount', 0):.2f}")
                    print(f"   - Processing Method: {processing_data.get('processing_method', 'unknown')}")
                
                return True
                
            else:
                print(f"❌ ERROR! Status Code: {response.status_code}")
                print(f"❌ Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection Error: Could not connect to {self.base_url}")
            return False
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
            return False
    
    def test_get_transactions_endpoint(self, jwt_token):
        """
        Test the get financial transactions endpoint
        GET /financial/transactions/all
        """
        print("\n💳 Testing Get Financial Transactions Endpoint...")
        print(f"📡 Endpoint: GET {self.base_url}/financial/transactions/all")
        
        if not jwt_token:
            print("❌ Error: JWT token is required")
            return False
        
        # Make GET request with JWT token as query parameter
        params = {"jwt_token": jwt_token}
        
        try:
            print(f"📤 Making GET request...")
            response = requests.get(
                f"{self.base_url}/financial/transactions/all",
                params=params
            )
            
            print(f"📥 Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS! Financial transactions retrieved")
                print(f"📊 Transaction Summary:")
                print(f"   - Status: {data.get('status', 'unknown')}")
                
                # User info
                user_info = data.get('user_info', {})
                print(f"   - User ID: {user_info.get('user_id', 'unknown')}")
                print(f"   - User Email: {user_info.get('email', 'unknown')}")
                
                # Transaction info
                transactions = data.get('transactions', {})
                print(f"   - Total Transactions: {transactions.get('count', 0)}")
                print(f"   - Total Amount: ₹{transactions.get('total_amount', 0):.2f}")
                
                # Analytics
                analytics = data.get('analytics', {})
                if analytics:
                    print(f"📈 Analytics:")
                    print(f"   - Transaction Types: {analytics.get('transaction_types', {})}")
                    print(f"   - Payment Methods: {analytics.get('payment_methods', {})}")
                    
                    top_merchants = analytics.get('top_merchants', {})
                    if top_merchants:
                        print(f"   - Top Merchants: {list(top_merchants.keys())[:5]}")
                
                # Show sample transaction
                transaction_data = transactions.get('data', [])
                if transaction_data:
                    sample = transaction_data[0]
                    print(f"💳 Sample Transaction:")
                    print(f"   - Amount: ₹{sample.get('amount', 0)}")
                    print(f"   - Merchant: {sample.get('merchant', 'N/A')}")
                    print(f"   - Type: {sample.get('transaction_type', 'N/A')}")
                    print(f"   - Payment Method: {sample.get('payment_method', 'N/A')}")
                
                return True
                
            else:
                print(f"❌ ERROR! Status Code: {response.status_code}")
                print(f"❌ Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection Error: Could not connect to {self.base_url}")
            return False
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
            return False
    
    def run_full_workflow_test(self, jwt_token):
        """
        Run the complete workflow test:
        1. Process financial transactions (fast)
        2. Retrieve financial transactions
        """
        print("=" * 70)
        print("🧪 FINANCIAL API WORKFLOW TEST")
        print("=" * 70)
        print("Testing complete workflow: Process → Retrieve")
        print()
        
        # Step 1: Process financial transactions
        print("📋 STEP 1: Process Financial Transactions")
        print("-" * 50)
        process_success = self.test_fast_processing_endpoint(jwt_token)
        
        if not process_success:
            print("\n❌ Processing failed. Cannot continue to retrieval test.")
            return False
        
        print("\n✅ Processing completed successfully!")
        print("\n" + "⏳" * 3 + " Waiting 2 seconds for database sync..." + "⏳" * 3)
        import time
        time.sleep(2)
        
        # Step 2: Retrieve financial transactions
        print("\n📋 STEP 2: Retrieve Financial Transactions")
        print("-" * 50)
        retrieve_success = self.test_get_transactions_endpoint(jwt_token)
        
        if retrieve_success:
            print("\n" + "🎉" * 20)
            print("🏆 WORKFLOW TEST COMPLETED SUCCESSFULLY!")
            print("🎉" * 20)
            print("\n✅ Both endpoints working perfectly:")
            print("   1. ✅ POST /financial/process-from-emails")
            print("   2. ✅ GET /financial/transactions/all")
            print("\n🚀 Your financial API is ready for production!")
            return True
        else:
            print("\n❌ Retrieval failed. Check the logs.")
            return False

def main():
    """Main function"""
    print("=" * 70)
    print("🔥 FINANCIAL API ENDPOINTS TESTER")
    print("=" * 70)
    print("This will test both financial API endpoints in sequence")
    print()
    
    # Get JWT token from user
    jwt_token = input("🔑 Enter your JWT token: ").strip()
    
    if not jwt_token:
        print("⏭️  No JWT token provided. Exiting...")
        return
    
    # Initialize tester
    tester = FinancialAPIEndpointTester()
    
    # Ask user what to test
    print("\nChoose test option:")
    print("1. Test complete workflow (Process + Retrieve)")
    print("2. Test processing only")
    print("3. Test retrieval only")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        tester.run_full_workflow_test(jwt_token)
    elif choice == "2":
        tester.test_fast_processing_endpoint(jwt_token)
    elif choice == "3":
        tester.test_get_transactions_endpoint(jwt_token)
    else:
        print("Invalid choice. Running complete workflow...")
        tester.run_full_workflow_test(jwt_token)

if __name__ == "__main__":
    main() 