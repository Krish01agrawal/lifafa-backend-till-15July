"""
Fast Financial Transaction Processor - Uses MongoDB Emails
==========================================================

This script processes financial transactions from emails already stored in MongoDB
instead of fetching from Gmail API. Much faster for testing!
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# MongoDB connection (same as your app)
MONGO_URI = "mongodb+srv://itskashyap26:%40gitartham1@cluster0.swuj2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
ca = certifi.where()
client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=ca)
db = client.genai_gmail_chat
emails_collection = db["emails"]
users_collection = db["users"]

class SimpleTransactionExtractor:
    """Simple transaction extractor for MongoDB emails"""
    
    def __init__(self):
        self.currency_patterns = [
            r'₹\s*([\d,]+\.?\d*)',
            r'Rs\.?\s*([\d,]+\.?\d*)',
            r'INR\s*([\d,]+\.?\d*)',
        ]
        
        self.financial_keywords = [
            'debited', 'credited', 'charged', 'payment', 'transaction',
            'UPI', 'transfer', 'paid', 'received', 'refund'
        ]
    
    def is_financial_email(self, email_data: Dict) -> bool:
        """Check if email is financial"""
        content = f"{email_data.get('subject', '')} {email_data.get('snippet', '')} {email_data.get('body', '')}"
        content_lower = content.lower()
        
        # Check for currency patterns
        for pattern in self.currency_patterns:
            if re.search(pattern, content):
                return True
        
        # Check for financial keywords
        for keyword in self.financial_keywords:
            if keyword.lower() in content_lower:
                return True
        
        return False
    
    def extract_transaction(self, email_data: Dict, user_id: str) -> Optional[Dict]:
        """Extract transaction data from email"""
        try:
            content = f"{email_data.get('subject', '')} {email_data.get('snippet', '')} {email_data.get('body', '')}"
            
            # Extract amount
            amount = None
            currency = "INR"
            for pattern in self.currency_patterns:
                match = re.search(pattern, content)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
            
            if not amount:
                return None
            
            # Extract merchant/bank from sender
            sender = email_data.get('sender', '')
            merchant = self._extract_merchant(sender, content)
            
            # Determine transaction type
            transaction_type = self._determine_type(content)
            
            # Extract payment method
            payment_method = self._extract_payment_method(content)
            
            return {
                "id": f"{user_id}_{email_data.get('_id', 'unknown')}_{int(datetime.now().timestamp())}",
                "email_id": str(email_data.get('_id', '')),
                "user_id": user_id,
                "date": email_data.get('date'),
                "amount": amount,
                "currency": currency,
                "transaction_type": transaction_type,
                "merchant": merchant,
                "description": email_data.get('subject', ''),
                "payment_method": payment_method,
                "sender": sender,
                "subject": email_data.get('subject', ''),
                "snippet": email_data.get('snippet', ''),
                "extracted_at": datetime.now().isoformat(),
                "confidence_score": 0.8
            }
            
        except Exception as e:
            print(f"Error extracting transaction: {e}")
            return None
    
    def _extract_merchant(self, sender: str, content: str) -> str:
        """Extract merchant name"""
        # Common financial institutions
        if 'hdfc' in sender.lower():
            return 'HDFC Bank'
        elif 'icici' in sender.lower():
            return 'ICICI Bank'
        elif 'sbi' in sender.lower():
            return 'SBI Bank'
        elif 'paytm' in sender.lower():
            return 'Paytm'
        elif 'phonepe' in sender.lower():
            return 'PhonePe'
        elif 'google' in sender.lower():
            return 'Google Pay'
        elif 'amazon' in sender.lower():
            return 'Amazon'
        elif 'flipkart' in sender.lower():
            return 'Flipkart'
        elif 'swiggy' in sender.lower():
            return 'Swiggy'
        elif 'zomato' in sender.lower():
            return 'Zomato'
        else:
            # Extract domain
            if '@' in sender:
                domain = sender.split('@')[1].split('.')[0]
                return domain.title()
            return 'Unknown'
    
    def _determine_type(self, content: str) -> str:
        """Determine transaction type"""
        content_lower = content.lower()
        if 'debited' in content_lower or 'charged' in content_lower:
            return 'debit'
        elif 'credited' in content_lower or 'received' in content_lower:
            return 'credit'
        elif 'refund' in content_lower:
            return 'refund'
        else:
            return 'debit'  # Default
    
    def _extract_payment_method(self, content: str) -> str:
        """Extract payment method"""
        content_lower = content.lower()
        if 'upi' in content_lower:
            return 'upi'
        elif 'card' in content_lower:
            if 'credit' in content_lower:
                return 'credit_card'
            else:
                return 'debit_card'
        elif 'bank' in content_lower or 'account' in content_lower:
            return 'bank_transfer'
        else:
            return 'unknown'

async def process_financial_transactions_from_mongodb(user_id: str) -> Dict[str, Any]:
    """Process financial transactions from MongoDB emails"""
    try:
        print(f"🔍 Processing financial transactions for user: {user_id}")
        
        # Get all emails for the user
        cursor = emails_collection.find({"user_id": user_id})
        all_emails = await cursor.to_list(length=None)
        
        print(f"📧 Found {len(all_emails)} total emails in MongoDB")
        
        # Extract financial transactions
        extractor = SimpleTransactionExtractor()
        financial_emails = []
        transactions = []
        
        for email in all_emails:
            if extractor.is_financial_email(email):
                financial_emails.append(email)
                transaction = extractor.extract_transaction(email, user_id)
                if transaction:
                    transactions.append(transaction)
        
        print(f"💰 Found {len(financial_emails)} financial emails")
        print(f"📊 Extracted {len(transactions)} transactions")
        
        if not transactions:
            return {
                "status": "success",
                "message": "No financial transactions found in emails",
                "transactions_found": 0,
                "user_id": user_id
            }
        
        # Calculate summary
        total_amount = sum(t['amount'] for t in transactions if t['amount'])
        
        # Store in financial_transactions collection
        financial_collection = db["financial_transactions"]
        
        # Remove existing data for user
        await financial_collection.delete_many({"user_id": user_id})
        
        # Insert new transactions
        if transactions:
            await financial_collection.insert_many(transactions)
        
        # Create and store summary
        summary = {
            "user_id": user_id,
            "period": "all_available",
            "total_transactions": len(transactions),
            "total_amount": total_amount,
            "average_transaction": total_amount / len(transactions) if transactions else 0,
            "category_breakdown": {},
            "merchant_breakdown": {},
            "monthly_trends": {},
            "generated_at": datetime.now().isoformat()
        }
        
        # Calculate breakdowns
        merchant_breakdown = {}
        payment_method_breakdown = {}
        
        for txn in transactions:
            merchant = txn.get('merchant', 'Unknown')
            merchant_breakdown[merchant] = merchant_breakdown.get(merchant, 0) + txn['amount']
            
            payment_method = txn.get('payment_method', 'unknown')
            payment_method_breakdown[payment_method] = payment_method_breakdown.get(payment_method, 0) + txn['amount']
        
        summary['merchant_breakdown'] = merchant_breakdown
        summary['category_breakdown'] = payment_method_breakdown
        
        # Store summary
        summary_collection = db["financial_summaries"]
        await summary_collection.delete_many({"user_id": user_id})
        await summary_collection.insert_one(summary)
        
        # Update user status
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "financial_analysis_completed": True,
                "financial_transactions_count": len(transactions),
                "financial_analysis_date": datetime.now().isoformat()
            }}
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "transactions_found": len(transactions),
            "total_amount": total_amount,
            "period": "all_available",
            "summary": summary
        }
        
    except Exception as e:
        print(f"❌ Error processing transactions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }

async def main():
    """Main function"""
    print("=" * 60)
    print("🚀 FAST FINANCIAL PROCESSOR (MongoDB)")
    print("=" * 60)
    print("This script processes emails already in MongoDB - Much faster!")
    print()
    
    # Get user ID
    user_id = input("👤 Enter your user ID (117694049755408407575): ").strip()
    if not user_id:
        user_id = "117694049755408407575"  # Default from your screenshot
    
    print(f"Processing for user: {user_id}")
    
    # Process transactions
    result = await process_financial_transactions_from_mongodb(user_id)
    
    # Show results
    if result["status"] == "success":
        print("\n" + "✅" * 20)
        print("🎉 FINANCIAL PROCESSING COMPLETED!")
        print("✅" * 20)
        print(f"📊 Results:")
        print(f"   - User ID: {result['user_id']}")
        print(f"   - Transactions Found: {result['transactions_found']}")
        print(f"   - Total Amount: ₹{result['total_amount']:.2f}")
        print(f"   - Period: {result['period']}")
        
        # Show breakdown
        summary = result.get('summary', {})
        if summary.get('merchant_breakdown'):
            print(f"🏪 Top Merchants:")
            for merchant, amount in list(summary['merchant_breakdown'].items())[:5]:
                print(f"   - {merchant}: ₹{amount:.2f}")
        
        # Save result
        with open('mongodb_financial_result.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"💾 Result saved to: mongodb_financial_result.json")
        
        print("\n🧪 Now test your API:")
        print("python3 test_financial_api.py")
        
    else:
        print("\n❌ PROCESSING FAILED!")
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main()) 