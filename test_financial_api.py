"""
Test script for the new GET /api/financial/transactions/all endpoint
This script tests the API with JWT token as query parameter
"""

import requests
import json
from datetime import datetime

class FinancialAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.test_jwt_token = None  # You'll need to get this from Google login
    
    def test_financial_transactions_endpoint(self, jwt_token):
        """
        Test the new GET /financial/transactions/all endpoint
        """
        print("🧪 Testing GET /financial/transactions/all endpoint...")
        print(f"📡 Base URL: {self.base_url}")
        print(f"🔑 JWT Token: {jwt_token[:50]}..." if jwt_token else "❌ No JWT token provided")
        
        if not jwt_token:
            print("❌ Error: JWT token is required for testing")
            return
        
        # Make GET request with JWT token as query parameter
        endpoint_url = f"{self.base_url}/financial/transactions/all"
        params = {"jwt_token": jwt_token}
        
        try:
            print(f"📤 Making GET request to: {endpoint_url}")
            response = requests.get(endpoint_url, params=params)
            
            print(f"📥 Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS! Financial transactions retrieved successfully")
                print(f"📊 Response Overview:")
                print(f"   - Status: {data.get('status', 'unknown')}")
                print(f"   - User ID: {data.get('user_info', {}).get('user_id', 'unknown')}")
                print(f"   - User Email: {data.get('user_info', {}).get('email', 'unknown')}")
                print(f"   - Total Transactions: {data.get('transactions', {}).get('count', 0)}")
                print(f"   - Total Amount: ₹{data.get('transactions', {}).get('total_amount', 0)}")
                
                # Show analytics
                analytics = data.get('analytics', {})
                if analytics:
                    print(f"📈 Analytics:")
                    print(f"   - Transaction Types: {analytics.get('transaction_types', {})}")
                    print(f"   - Payment Methods: {analytics.get('payment_methods', {})}")
                    print(f"   - Top Merchants: {list(analytics.get('top_merchants', {}).keys())[:5]}")
                
                # Show metadata
                metadata = data.get('metadata', {})
                if metadata:
                    print(f"📝 Metadata:")
                    print(f"   - Extracted At: {metadata.get('extracted_at', 'unknown')}")
                    print(f"   - Data Includes: {len(metadata.get('data_includes', []))} types")
                
                # Show sample transaction (first one)
                transactions = data.get('transactions', {}).get('data', [])
                if transactions:
                    print(f"💳 Sample Transaction:")
                    sample_txn = transactions[0]
                    print(f"   - Amount: ₹{sample_txn.get('amount', 'N/A')}")
                    print(f"   - Merchant: {sample_txn.get('merchant', 'N/A')}")
                    print(f"   - Type: {sample_txn.get('transaction_type', 'N/A')}")
                    print(f"   - Payment Method: {sample_txn.get('payment_method', 'N/A')}")
                    print(f"   - Date: {sample_txn.get('date', 'N/A')}")
                
                # Save response to file for detailed analysis
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"financial_transactions_response_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"💾 Full response saved to: {filename}")
                
            else:
                print(f"❌ ERROR! Status Code: {response.status_code}")
                print(f"❌ Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection Error: Could not connect to {self.base_url}")
            print("   Make sure the FastAPI server is running on the correct port")
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
    
    def print_usage_instructions(self):
        """Print instructions for using the API"""
        print("\n" + "="*60)
        print("📋 HOW TO USE THE NEW FINANCIAL TRANSACTIONS API")
        print("="*60)
        print("\n🔗 Endpoint: GET /financial/transactions/all")
        print("📄 Method: GET")
        print("🔑 Authentication: JWT token as query parameter")
        print("\n📤 Usage in Postman:")
        print("   1. Set method to GET")
        print("   2. Enter URL: http://your-server.com/financial/transactions/all")
        print("   3. Add query parameter:")
        print("      - Key: jwt_token")
        print("      - Value: your_jwt_token_here")
        print("   4. Send request")
        print("\n📤 Usage with curl:")
        print('   curl "http://localhost:8001/financial/transactions/all?jwt_token=YOUR_JWT_TOKEN"')
        print("\n📤 Usage with Python requests:")
        print("   import requests")
        print("   response = requests.get(")
        print("       'http://localhost:8001/financial/transactions/all',")
        print("       params={'jwt_token': 'YOUR_JWT_TOKEN'}")
        print("   )")
        print("\n💡 Response includes:")
        print("   ✅ All financial transactions (credit/debit cards, UPI, bank transfers)")
        print("   ✅ Transaction analytics and summaries")
        print("   ✅ User information")
        print("   ✅ Metadata about data types included")
        print("="*60)

def main():
    """Main function to run the test"""
    tester = FinancialAPITester()
    
    # Print usage instructions
    tester.print_usage_instructions()
    
    # For manual testing, you can add your JWT token here
    jwt_token = input("\n🔑 Enter your JWT token to test the endpoint (or press Enter to skip): ").strip()
    
    if jwt_token:
        tester.test_financial_transactions_endpoint(jwt_token)
    else:
        print("⏭️  Skipping live test. You can test manually using the instructions above.")
        print("\n🚀 To get a JWT token:")
        print("   1. Use the /auth/google-login endpoint first")
        print("   2. Copy the jwt_token from the response")
        print("   3. Use that token with this new endpoint")

if __name__ == "__main__":
    main() 