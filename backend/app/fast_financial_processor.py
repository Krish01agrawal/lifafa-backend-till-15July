"""
Fast Financial Transaction Processor for API
============================================

This module provides fast financial transaction processing from MongoDB emails
for use in FastAPI endpoints. Much faster than Gmail API processing.
"""

import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.db import emails_collection, users_collection, db
import logging

logger = logging.getLogger(__name__)

class FastTransactionExtractor:
    """Fast transaction extractor for MongoDB emails"""
    
    def __init__(self):
        self.currency_patterns = [
            r'₹\s*([\d,]+\.?\d*)',
            r'Rs\.?\s*([\d,]+\.?\d*)',
            r'INR\s*([\d,]+\.?\d*)',
        ]
        
        self.financial_keywords = [
            'debited', 'credited', 'charged', 'payment', 'transaction',
            'UPI', 'transfer', 'paid', 'received', 'refund', 'order', 'bill'
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
        
        # Check for financial senders
        sender = email_data.get('sender', '').lower()
        financial_domains = ['hdfcbank', 'icici', 'sbi', 'paytm', 'phonepe', 'amazon', 'uber', 'swiggy', 'zomato']
        for domain in financial_domains:
            if domain in sender:
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
            
            # Extract account info (masked)
            account_info = self._extract_account_info(content)
            
            # Convert ObjectId to string if present
            email_id = email_data.get('_id')
            email_id_str = str(email_id) if email_id else 'unknown'
            
            return {
                "id": f"{user_id}_{email_id_str}_{int(datetime.now().timestamp())}",
                "email_id": email_id_str,
                "user_id": user_id,
                "date": email_data.get('date'),
                "amount": amount,
                "currency": currency,
                "transaction_type": transaction_type,
                "merchant": merchant,
                "description": email_data.get('subject', ''),
                "payment_method": payment_method,
                "account_info": account_info,
                "transaction_id": self._extract_transaction_id(content),
                "sender": sender,
                "subject": email_data.get('subject', ''),
                "snippet": email_data.get('snippet', ''),
                "extracted_at": datetime.now().isoformat(),
                "confidence_score": 0.8
            }
            
        except Exception as e:
            logger.error(f"Error extracting transaction: {e}")
            return None
    
    def _extract_merchant(self, sender: str, content: str) -> str:
        """Extract merchant name"""
        sender_lower = sender.lower()
        
        # Common financial institutions and services
        merchant_map = {
            'hdfcbank': 'HDFC Bank',
            'hdfc': 'HDFC Bank',
            'icici': 'ICICI Bank',
            'sbi': 'SBI Bank',
            'paytm': 'Paytm',
            'phonepe': 'PhonePe',
            'googlepay': 'Google Pay',
            'google': 'Google Pay',
            'amazon': 'Amazon',
            'flipkart': 'Flipkart',
            'swiggy': 'Swiggy',
            'zomato': 'Zomato',
            'uber': 'Uber',
            'ola': 'Ola',
            'myntra': 'Myntra',
            'bigbasket': 'BigBasket',
            'grofers': 'Grofers',
            'zerodha': 'Zerodha',
            'groww': 'Groww'
        }
        
        for key, merchant in merchant_map.items():
            if key in sender_lower:
                return merchant
        
        # Extract from domain
        if '@' in sender:
            domain_parts = sender.split('@')[1].split('.')
            if domain_parts:
                domain = domain_parts[0]
                return domain.title()
        
        return 'Unknown'
    
    def _determine_type(self, content: str) -> str:
        """Determine transaction type"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['debited', 'charged', 'paid', 'purchase', 'spent']):
            return 'debit'
        elif any(word in content_lower for word in ['credited', 'received', 'deposit', 'cashback']):
            return 'credit'
        elif any(word in content_lower for word in ['refund', 'reversal', 'returned']):
            return 'refund'
        else:
            return 'debit'  # Default assumption
    
    def _extract_payment_method(self, content: str) -> str:
        """Extract payment method"""
        content_lower = content.lower()
        
        if 'upi' in content_lower:
            return 'upi'
        elif any(word in content_lower for word in ['credit card', 'visa', 'mastercard']):
            return 'credit_card'
        elif any(word in content_lower for word in ['debit card', 'atm']):
            return 'debit_card'
        elif any(word in content_lower for word in ['neft', 'rtgs', 'imps', 'bank transfer']):
            return 'bank_transfer'
        elif 'wallet' in content_lower:
            return 'wallet'
        else:
            return 'unknown'
    
    def _extract_account_info(self, content: str) -> Optional[str]:
        """Extract masked account info"""
        # Look for account numbers (masked)
        account_patterns = [
            r'\*+(\d{4})',  # ****1234
            r'ending (\d{4})',  # ending 1234
            r'xx+(\d{4})',  # xxxx1234
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"****{match.group(1)}"
        
        return None
    
    def _extract_transaction_id(self, content: str) -> Optional[str]:
        """Extract transaction ID"""
        # Look for transaction IDs
        id_patterns = [
            r'(?:txn|transaction|ref|reference)[\s:]+([a-zA-Z0-9]+)',
            r'([A-Z0-9]{10,})',  # Long alphanumeric strings
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

async def process_financial_transactions_from_mongodb(user_id: str) -> Dict[str, Any]:
    """Process financial transactions from MongoDB emails"""
    try:
        logger.info(f"Processing financial transactions from MongoDB for user: {user_id}")
        
        # Get all emails for the user
        cursor = emails_collection.find({"user_id": user_id})
        all_emails = await cursor.to_list(length=None)
        
        logger.info(f"Found {len(all_emails)} total emails in MongoDB")
        
        # Extract financial transactions
        extractor = FastTransactionExtractor()
        financial_emails = []
        transactions = []
        
        for email in all_emails:
            if extractor.is_financial_email(email):
                financial_emails.append(email)
                transaction = extractor.extract_transaction(email, user_id)
                if transaction:
                    transactions.append(transaction)
        
        logger.info(f"Found {len(financial_emails)} financial emails")
        logger.info(f"Extracted {len(transactions)} transactions")
        
        if not transactions:
            return {
                "status": "success",
                "message": "No financial transactions found in stored emails",
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
            logger.info(f"Stored {len(transactions)} transactions in database")
        
        # Create and store summary
        summary = {
            "user_id": user_id,
            "period": "all_stored_emails",
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
        transaction_type_breakdown = {}
        
        for txn in transactions:
            # Merchant breakdown
            merchant = txn.get('merchant', 'Unknown')
            merchant_breakdown[merchant] = merchant_breakdown.get(merchant, 0) + txn['amount']
            
            # Payment method breakdown
            payment_method = txn.get('payment_method', 'unknown')
            payment_method_breakdown[payment_method] = payment_method_breakdown.get(payment_method, 0) + txn['amount']
            
            # Transaction type breakdown
            txn_type = txn.get('transaction_type', 'unknown')
            transaction_type_breakdown[txn_type] = transaction_type_breakdown.get(txn_type, 0) + 1
        
        summary['merchant_breakdown'] = merchant_breakdown
        summary['category_breakdown'] = payment_method_breakdown
        summary['transaction_type_breakdown'] = transaction_type_breakdown
        
        # Store summary
        summary_collection = db["financial_summaries"]
        await summary_collection.delete_many({"user_id": user_id})
        await summary_collection.insert_one(summary.copy())
        logger.info("Stored financial summary in database")
        
        # Update user status
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "financial_analysis_completed": True,
                "financial_transactions_count": len(transactions),
                "financial_analysis_date": datetime.now().isoformat(),
                "financial_processing_method": "fast_mongodb"
            }}
        )
        
        # Create clean response without MongoDB ObjectIds
        clean_summary = {
            "user_id": user_id,
            "period": "all_stored_emails",
            "total_transactions": len(transactions),
            "total_amount": total_amount,
            "average_transaction": total_amount / len(transactions) if transactions else 0,
            "merchant_breakdown": summary['merchant_breakdown'],
            "category_breakdown": summary['category_breakdown'],
            "transaction_type_breakdown": summary['transaction_type_breakdown'],
            "generated_at": summary['generated_at']
        }
        
        return {
            "status": "success",
            "user_id": user_id,
            "transactions_found": len(transactions),
            "total_amount": total_amount,
            "period": "all_stored_emails",
            "processing_method": "fast_mongodb",
            "summary": clean_summary
        }
        
    except Exception as e:
        logger.error(f"Error processing transactions from MongoDB: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        } 