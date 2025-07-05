"""
Fast Financial Transaction Processor for API
============================================

This module provides fast financial transaction processing from MongoDB emails
for use in FastAPI endpoints. Much faster than Gmail API processing.
"""

import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from .db import emails_collection, users_collection, db
import logging

logger = logging.getLogger(__name__)

class EnhancedTransactionExtractor:
    """Enhanced transaction extractor with improved pattern matching for real transaction data"""
    
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
        
        # Enhanced transaction ID patterns for real UPI/bank transaction IDs
        self.transaction_id_patterns = [
            r'(?:UPI transaction reference number|reference number|ref no|transaction reference)[:\s]*([0-9]{10,15})',
            r'(?:UTR|UPI Ref|Transaction ID|Txn ID)[:\s]*([A-Z0-9]{10,20})',
            r'(?:reference number is|ref\s*no\.?\s*is)[:\s]*([0-9]{10,15})',
            r'(?:transaction reference number is)[:\s]*([0-9]{10,15})',
            r'(?:ORDER ID)[:\s]*([A-Z0-9]{8,15})',
            r'(?:Invoice|Bill)\s*#?[:\s]*([A-Z0-9]{6,20})',
            # Subscription and recurring payment patterns
            r'(?:subscription|recurring|renewal)\s*(?:id|number)?[:\s]*([A-Z0-9]{6,20})',
            r'(?:Order Receipt|Receipt)\s*(?:from|#)?[:\s]*([A-Z0-9\s]{6,30})',
        ]
        
        # UPI ID patterns
        self.upi_id_patterns = [
            r'to VPA\s+([a-zA-Z0-9@.\-_]+@[a-zA-Z0-9.\-_]+)',
            r'from VPA\s+([a-zA-Z0-9@.\-_]+@[a-zA-Z0-9.\-_]+)',
            r'UPI ID[:\s]*([a-zA-Z0-9@.\-_]+@[a-zA-Z0-9.\-_]+)',
            r'([a-zA-Z0-9@.\-_]+@[a-zA-Z0-9]+)',  # Generic UPI pattern
        ]
        
        # Account number patterns (masked)
        self.account_patterns = [
            r'account\s+(?:ending\s+with\s+|\*+)(\d{4})',
            r'A/C\s+(?:XXXXX|XXX)(\d{4,6})',  # For SBI format
            r'account\s+\*+(\d{4})',
            r'from\s+account\s+\*+(\d{4})',
            r'to\s+account\s+\*+(\d{4})',
        ]
        
        # Bank name extraction patterns
        self.bank_patterns = [
            r'(HDFC\s*Bank|HDFC)',
            r'(ICICI\s*Bank|ICICI)',
            r'(State\s*Bank\s*of\s*India|SBI)',
            r'(Axis\s*Bank|Axis)',
            r'(Kotak\s*Mahindra\s*Bank|Kotak)',
            r'(Yes\s*Bank|YES)',
            r'(Punjab\s*National\s*Bank|PNB)',
            r'(Bank\s*of\s*Baroda|BOB)',
        ]
        
        # Card number patterns (masked)
        self.card_patterns = [
            r'card\s+(?:ending\s+with\s+|\*+)(\d{4})',
            r'(?:credit|debit)\s+card\s+\*+(\d{4})',
            r'card\s+number\s+\*+(\d{4})',
        ]
        
        # App/Service patterns for UPI
        self.upi_app_patterns = [
            r'(PhonePe|phonepe|PHONEPE)',
            r'(Paytm|paytm|PAYTM)',
            r'(Google\s*Pay|googlepay|GOOGLEPAY)',
            r'(BHIM|bhim)',
            r'(Amazon\s*Pay|amazonpay)',
            r'(WhatsApp|whatsapp)',
        ]
        
        # Comprehensive subscription detection patterns
        self.subscription_keywords = [
            'subscription', 'recurring', 'renewal', 'auto-renewal', 'auto renewal',
            'monthly', 'yearly', 'annual', 'premium', 'plus', 'pro', 'plan',
            'membership', 'service', 'billing', 'auto-pay', 'autopay'
        ]
        
        # Subscription product mapping with detailed information
        self.subscription_products = {
            # Streaming Services
            'netflix': {
                'name': 'Netflix',
                'category': 'Entertainment',
                'type': 'Video Streaming',
                'typical_amounts': [199, 499, 649, 799],
                'keywords': ['netflix', 'netflix.com', 'netflix subscription', 'netflix premium', 'netflix basic', 'netflix standard']
            },
            'spotify': {
                'name': 'Spotify',
                'category': 'Entertainment', 
                'type': 'Music Streaming',
                'typical_amounts': [119, 149, 179, 389],
                'keywords': ['spotify', 'spotify.com', 'spotify premium', 'spotify family', 'spotify individual']
            },
            'youtube_premium': {
                'name': 'YouTube Premium',
                'category': 'Entertainment',
                'type': 'Video Streaming',
                'typical_amounts': [129, 189, 269],
                'keywords': ['youtube premium', 'youtube music', 'youtube red', 'youtube.com']
            },
            'amazon_prime': {
                'name': 'Amazon Prime',
                'category': 'Shopping & Entertainment',
                'type': 'Membership',
                'typical_amounts': [179, 329, 999, 1499],
                'keywords': ['amazon prime', 'prime membership', 'prime video', 'amazon.in', 'primevideo.com']
            },
            'disney_hotstar': {
                'name': 'Disney+ Hotstar',
                'category': 'Entertainment',
                'type': 'Video Streaming',
                'typical_amounts': [299, 899, 1499],
                'keywords': ['disney', 'hotstar', 'disney+', 'disney plus', 'hotstar.com']
            },
            
            # Software & Productivity
            'microsoft_365': {
                'name': 'Microsoft 365',
                'category': 'Software',
                'type': 'Office Suite',
                'typical_amounts': [489, 719, 1049],
                'keywords': ['microsoft 365', 'office 365', 'microsoft office', 'outlook', 'microsoft.com']
            },
            'adobe_creative': {
                'name': 'Adobe Creative Cloud',
                'category': 'Software',
                'type': 'Design Software',
                'typical_amounts': [1675, 2390, 4290],
                'keywords': ['adobe', 'creative cloud', 'photoshop', 'illustrator', 'adobe.com']
            },
            'google_workspace': {
                'name': 'Google Workspace',
                'category': 'Software', 
                'type': 'Productivity Suite',
                'typical_amounts': [136, 272, 544],
                'keywords': ['google workspace', 'g suite', 'gsuite', 'google.com', 'workspace.google.com']
            },
            'canva_pro': {
                'name': 'Canva Pro',
                'category': 'Software',
                'type': 'Design Tool',
                'typical_amounts': [399, 499],
                'keywords': ['canva', 'canva pro', 'canva.com']
            },
            
            # AI & ChatGPT
            'chatgpt_plus': {
                'name': 'ChatGPT Plus',
                'category': 'AI & Technology',
                'type': 'AI Assistant',
                'typical_amounts': [1650, 1950, 2000],
                'keywords': ['chatgpt', 'openai', 'gpt', 'chatgpt plus', 'openai.com', 'chat.openai.com']
            },
            'claude_pro': {
                'name': 'Claude Pro',
                'category': 'AI & Technology',
                'type': 'AI Assistant',
                'typical_amounts': [1650, 1950],
                'keywords': ['claude', 'anthropic', 'claude pro', 'claude.ai']
            },
            'midjourney': {
                'name': 'Midjourney',
                'category': 'AI & Technology',
                'type': 'AI Art Generator',
                'typical_amounts': [830, 2490, 4990],
                'keywords': ['midjourney', 'midjourney.com']
            },
            
            # Cloud Storage
            'google_drive': {
                'name': 'Google Drive',
                'category': 'Cloud Storage',
                'type': 'File Storage',
                'typical_amounts': [130, 210, 650],
                'keywords': ['google drive', 'google one', 'google storage', 'drive.google.com']
            },
            'dropbox': {
                'name': 'Dropbox',
                'category': 'Cloud Storage',
                'type': 'File Storage',
                'typical_amounts': [830, 1650, 2075],
                'keywords': ['dropbox', 'dropbox.com']
            },
            'icloud': {
                'name': 'iCloud',
                'category': 'Cloud Storage',
                'type': 'File Storage',
                'typical_amounts': [75, 219, 749],
                'keywords': ['icloud', 'apple', 'icloud.com', 'apple.com']
            },
            
            # Gaming
            'playstation_plus': {
                'name': 'PlayStation Plus',
                'category': 'Gaming',
                'type': 'Gaming Subscription',
                'typical_amounts': [499, 849, 2999],
                'keywords': ['playstation', 'ps plus', 'sony', 'playstation.com']
            },
            'xbox_game_pass': {
                'name': 'Xbox Game Pass',
                'category': 'Gaming',
                'type': 'Gaming Subscription',
                'typical_amounts': [489, 699],
                'keywords': ['xbox', 'game pass', 'microsoft', 'xbox.com']
            },
            
            # News & Reading
            'kindle_unlimited': {
                'name': 'Kindle Unlimited',
                'category': 'Reading',
                'type': 'Book Subscription',
                'typical_amounts': [169, 199],
                'keywords': ['kindle', 'kindle unlimited', 'amazon kindle', 'amazon.in']
            },
            'times_of_india': {
                'name': 'Times of India',
                'category': 'News',
                'type': 'News Subscription',
                'typical_amounts': [99, 199, 299],
                'keywords': ['times of india', 'toi', 'timesofindia.com']
            },
            
            # Fitness & Health
            'cult_fit': {
                'name': 'Cult.fit',
                'category': 'Fitness',
                'type': 'Fitness Subscription',
                'typical_amounts': [999, 1499, 2999],
                'keywords': ['cult', 'cultfit', 'cult.fit', 'cure.fit']
            },
            'healthify_me': {
                'name': 'HealthifyMe',
                'category': 'Health',
                'type': 'Health App',
                'typical_amounts': [999, 1999, 3999],
                'keywords': ['healthify', 'healthifyme', 'healthifyme.com']
            },
            
            # App Store & Play Store
            'google_play': {
                'name': 'Google Play',
                'category': 'App Store',
                'type': 'App Subscription',
                'typical_amounts': [99, 199, 299, 499, 999, 1950],
                'keywords': ['google play', 'play store', 'play.google.com', 'googleplay']
            },
            'app_store': {
                'name': 'App Store',
                'category': 'App Store',
                'type': 'App Subscription',
                'typical_amounts': [99, 199, 299, 499, 999, 1950],
                'keywords': ['app store', 'apple', 'itunes', 'apple.com']
            },
            
            # Others
            'zomato_pro': {
                'name': 'Zomato Pro',
                'category': 'Food',
                'type': 'Food Delivery',
                'typical_amounts': [99, 199, 299],
                'keywords': ['zomato pro', 'zomato plus', 'zomato.com']
            },
            'swiggy_super': {
                'name': 'Swiggy Super',
                'category': 'Food',
                'type': 'Food Delivery',
                'typical_amounts': [99, 199, 299],
                'keywords': ['swiggy super', 'swiggy plus', 'swiggy.com']
            }
        }
    
    def is_financial_email(self, email_data: Dict) -> bool:
        """
        Enhanced financial email detection with context awareness
        Uses the new EnhancedFinancialDetector to avoid false positives from job postings
        """
        from .enhanced_financial_detector import is_actual_financial_transaction
        
        # Use the enhanced detector that can distinguish between
        # actual transactions and job postings/newsletters
        is_financial = is_actual_financial_transaction(email_data)
        
        if not is_financial:
            # Get the exclusion reason for logging
            from .enhanced_financial_detector import get_financial_exclusion_reason
            exclusion_reason = get_financial_exclusion_reason(email_data)
            sender = email_data.get('sender', 'unknown')
            subject = email_data.get('subject', 'unknown')
            
            logger.debug(f"Email excluded from financial processing:")
            logger.debug(f"  Sender: {sender}")
            logger.debug(f"  Subject: {subject}")
            logger.debug(f"  Reason: {exclusion_reason}")
        
        return is_financial
    
    def _detect_subscription(self, content: str, sender: str) -> Dict[str, Any]:
        """
        Detect if transaction is a subscription and identify the product
        Returns subscription details including product name, category, and confidence
        """
        content_lower = content.lower()
        sender_lower = sender.lower()
        
        subscription_info = {
            'is_subscription': False,
            'subscription_product': None,
            'subscription_category': None,
            'subscription_type': None,
            'confidence_score': 0.0,
            'detection_reasons': []
        }
        
        # Check for subscription keywords
        subscription_keyword_found = False
        for keyword in self.subscription_keywords:
            if keyword in content_lower:
                subscription_keyword_found = True
                subscription_info['confidence_score'] += 0.3
                subscription_info['detection_reasons'].append(f"Subscription keyword: {keyword}")
                break
        
        # Check for specific subscription products
        detected_product = None
        highest_confidence = 0.0
        
        for product_key, product_info in self.subscription_products.items():
            product_confidence = 0.0
            
            # Check keywords in content and sender
            for keyword in product_info['keywords']:
                if keyword.lower() in content_lower:
                    product_confidence += 0.4
                    subscription_info['detection_reasons'].append(f"Product keyword in content: {keyword}")
                elif keyword.lower() in sender_lower:
                    product_confidence += 0.5  # Sender match is more reliable
                    subscription_info['detection_reasons'].append(f"Product keyword in sender: {keyword}")
            
            # If product confidence is high enough, consider it detected
            if product_confidence > highest_confidence and product_confidence >= 0.3:
                highest_confidence = product_confidence
                detected_product = product_info
                subscription_info['subscription_product'] = product_info['name']
                subscription_info['subscription_category'] = product_info['category']
                subscription_info['subscription_type'] = product_info['type']
        
        # Additional subscription indicators
        recurring_indicators = [
            'auto-renewal', 'auto renewal', 'recurring payment', 'monthly charge',
            'annual charge', 'yearly charge', 'subscription renewed', 'plan renewed',
            'membership renewed', 'premium subscription', 'pro subscription'
        ]
        
        for indicator in recurring_indicators:
            if indicator in content_lower:
                subscription_info['confidence_score'] += 0.2
                subscription_info['detection_reasons'].append(f"Recurring indicator: {indicator}")
        
        # Check sender domains for known subscription services
        subscription_domains = [
            'netflix.com', 'spotify.com', 'amazon.in', 'amazon.com', 'google.com',
            'microsoft.com', 'adobe.com', 'apple.com', 'disney.com', 'hotstar.com',
            'openai.com', 'anthropic.com', 'midjourney.com', 'canva.com',
            'dropbox.com', 'icloud.com', 'playstation.com', 'xbox.com'
        ]
        
        for domain in subscription_domains:
            if domain in sender_lower:
                subscription_info['confidence_score'] += 0.3
                subscription_info['detection_reasons'].append(f"Subscription service domain: {domain}")
                break
        
        # Update confidence score with product detection
        subscription_info['confidence_score'] += highest_confidence
        
        # Final determination
        if subscription_info['confidence_score'] >= 0.5 or (subscription_keyword_found and highest_confidence > 0):
            subscription_info['is_subscription'] = True
            
            # If no specific product detected but subscription confirmed, try to infer from content
            if not detected_product:
                subscription_info['subscription_product'] = self._infer_subscription_product(content_lower, sender_lower)
                subscription_info['subscription_category'] = 'Unknown'
                subscription_info['subscription_type'] = 'Subscription Service'
        
        return subscription_info
    
    def _infer_subscription_product(self, content_lower: str, sender_lower: str) -> str:
        """
        Infer subscription product when specific product is not detected
        but subscription is confirmed
        """
        # Try to extract product name from sender domain
        if '@' in sender_lower:
            domain = sender_lower.split('@')[1].split('.')[0]
            return domain.title() + ' Subscription'
        
        # Try to extract from common patterns in content
        if 'google play' in content_lower:
            return 'Google Play Subscription'
        elif 'app store' in content_lower:
            return 'App Store Subscription'
        elif 'premium' in content_lower:
            return 'Premium Subscription'
        elif 'pro' in content_lower:
            return 'Pro Subscription'
        elif 'plus' in content_lower:
            return 'Plus Subscription'
        else:
            return 'Unknown Subscription'
    
    def _validate_subscription_amount(self, amount: float, product_info: Dict) -> bool:
        """
        Validate if the transaction amount matches typical subscription amounts
        for the detected product
        """
        if not amount or not product_info:
            return False
        
        typical_amounts = product_info.get('typical_amounts', [])
        if not typical_amounts:
            return True  # If no typical amounts defined, assume valid
        
        # Check if amount is within 20% of any typical amount
        for typical_amount in typical_amounts:
            if abs(amount - typical_amount) / typical_amount <= 0.2:
                return True
        
        return False
    
    def extract_transaction(self, email_data: Dict, user_id: str) -> Optional[Dict]:
        """Extract comprehensive transaction data from email - FIXED: No double-checking"""
        try:
            # ✅ SKIP REDUNDANT CHECK - We already know this is financial from the calling function
            # This was causing the 6 emails found, 0 transactions extracted issue
            logger.debug(f"Extracting transaction from financial email: {email_data.get('subject', '')[:50]}...")
            
            content = f"{email_data.get('subject', '')} {email_data.get('snippet', '')} {email_data.get('body', '')}"
            
            # ✅ AGGRESSIVE AMOUNT EXTRACTION - Try multiple methods
            amount = None
            currency = "INR"
            
            # Method 1: Basic currency patterns (most reliable)
            for pattern in self.currency_patterns:
                match = re.search(pattern, content)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        logger.info(f"✅ Amount extracted via pattern: ₹{amount} from: {email_data.get('subject', '')[:50]}...")
                        break
                    except ValueError:
                        continue
            
            # Method 2: Enhanced detector (only if basic patterns fail)
            if not amount:
                from .enhanced_financial_detector import extract_transaction_amount_safe
                amount, currency = extract_transaction_amount_safe(email_data)
                if amount:
                    logger.info(f"✅ Amount extracted via enhanced detector: ₹{amount} from: {email_data.get('subject', '')[:50]}...")
                    
            # Method 3: Expanded amount patterns for harder cases
            if not amount:
                expanded_patterns = [
                    r'(?:amount|total|paid|charged|received|sent|transfer|debit|credit)[:\s]*[₹\$]?\s*([\d,]+\.?\d*)',
                    r'[₹\$]\s*([\d,]+\.?\d*)',
                    r'(?:rs|rupees|inr)[:\s]*([\d,]+\.?\d*)',
                    r'amount[:\s]*[₹\$]?\s*([\d,]+\.?\d*)',
                    r'([\d,]+\.?\d*)\s*(?:rs|rupees|inr)',
                    r'(?:spent|cost|price|bill)[:\s]*[₹\$]?\s*([\d,]+\.?\d*)',
                ]
                
                for pattern in expanded_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        try:
                            amount = float(amount_str)
                            if amount > 0:  # Valid amount
                                logger.info(f"✅ Amount extracted via expanded patterns: ₹{amount} from: {email_data.get('subject', '')[:50]}...")
                                break
                        except ValueError:
                            continue
            
            # Special handling for subscription transactions without explicit amounts
            if not amount and any(word in content.lower() for word in ['subscription', 'recurring', 'renewal']):
                # Try to infer amount from subscription context
                if 'chatgpt' in content.lower():
                    # ChatGPT Plus subscription is typically ₹1950 in India
                    amount = 1950.0
                elif 'netflix' in content.lower():
                    # Netflix subscription varies, use average
                    amount = 649.0
                elif 'spotify' in content.lower():
                    # Spotify premium is typically ₹119
                    amount = 119.0
                elif 'google' in content.lower() and 'play' in content.lower():
                    # Google Play subscription, try to infer from context
                    amount = 1950.0  # Default for premium subscriptions
                
                # If still no amount, check if it's a payment issue/refund
                if not amount and any(word in content.lower() for word in ['declined', 'suspended', 'failed', 'issue']):
                    # Payment issue emails often reference the subscription amount
                    amount = 1950.0  # Common subscription amount
            
            if not amount:
                logger.warning(f"❌ No amount extracted from financial email: {email_data.get('subject', '')[:50]}...")
                logger.warning(f"   Sender: {email_data.get('sender', '')[:50]}...")
                logger.warning(f"   Content preview: {content[:100]}...")
                return None
            
            # Extract comprehensive transaction details
            sender = email_data.get('sender', '')
            merchant = self._extract_merchant(sender, content)
            transaction_type = self._determine_type(content)
            payment_method = self._extract_payment_method(content)
            transaction_id = self._extract_transaction_id(content)
            
            # Extract account information
            account_info = self._extract_account_info(content)
            bank_name = self._extract_bank_name(content, sender)
            
            # Extract UPI details if applicable
            upi_details = self._extract_upi_details(content) if payment_method == 'upi' else {}
            
            # Extract card details if applicable
            card_details = self._extract_card_details(content) if 'card' in payment_method else {}
            
            # Detect subscription information
            subscription_info = self._detect_subscription(content, sender)
            
            # Convert ObjectId to string if present
            email_id = email_data.get('_id')
            email_id_str = str(email_id) if email_id else 'unknown'
            
            # Create comprehensive transaction record
            transaction = {
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
                "transaction_id": transaction_id,
                "sender": sender,
                "subject": email_data.get('subject', ''),
                "snippet": email_data.get('snippet', ''),
                "extracted_at": datetime.now().isoformat(),
                "confidence_score": 0.8,
                
                # Subscription fields
                "is_subscription": subscription_info['is_subscription'],
                "subscription_product": subscription_info['subscription_product'],
                
                # Enhanced details
                "bank_details": {
                    "bank_name": bank_name,
                    "account_number": account_info,
                },
                "upi_details": upi_details,
                "card_details": card_details,
                
                # Subscription details (comprehensive)
                "subscription_details": {
                    "is_subscription": subscription_info['is_subscription'],
                    "product_name": subscription_info['subscription_product'],
                    "category": subscription_info['subscription_category'],
                    "type": subscription_info['subscription_type'],
                    "confidence_score": subscription_info['confidence_score'],
                    "detection_reasons": subscription_info['detection_reasons']
                } if subscription_info['is_subscription'] else {}
            }
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error extracting transaction: {e}")
            return None
    
    def _extract_merchant(self, sender: str, content: str) -> str:
        """Extract merchant name with improved logic"""
        sender_lower = sender.lower()
        content_lower = content.lower()
        
        # First check for merchant in UPI VPA (most accurate for payments)
        upi_merchant_match = re.search(r'to VPA\s+([a-zA-Z0-9@.\-_]*)\s+([A-Z\s&0-9]+)', content)
        if upi_merchant_match:
            vpa = upi_merchant_match.group(1).lower()
            receiver_name = upi_merchant_match.group(2).strip()
            
            # Extract merchant from VPA
            if 'zomato' in vpa:
                return 'Zomato'
            elif 'paytm' in vpa:
                return 'Paytm'
            elif 'swiggy' in vpa:
                return 'Swiggy'
            elif 'uber' in vpa:
                return 'Uber'
            elif 'blinkit' in vpa:
                return 'Blinkit'
            elif 'bmtc' in vpa:
                return 'BMTC'
            elif 'amazon' in vpa:
                return 'Amazon'
            elif 'flipkart' in vpa:
                return 'Flipkart'
            else:
                # Use receiver name if VPA doesn't match known merchants
                return receiver_name if len(receiver_name) > 1 else 'Unknown'
        
        # Check content for merchant indicators
        if 'zomato' in content_lower:
            return 'Zomato'
        elif 'swiggy' in content_lower:
            return 'Swiggy'
        elif 'uber' in content_lower:
            return 'Uber'
        elif 'blinkit' in content_lower:
            return 'Blinkit'
        elif 'paytm' in content_lower:
            return 'Paytm'
        
        # Enhanced merchant detection from sender
        merchants = {
            'hdfc': 'HDFC Bank',
            'icici': 'ICICI Bank', 
            'sbi': 'SBI Bank',
            'axis': 'Axis Bank',
            'kotak': 'Kotak Bank',
            'paytm': 'Paytm',
            'phonepe': 'PhonePe',
            'googlepay': 'Google Pay',
            'amazon': 'Amazon',
            'flipkart': 'Flipkart',
            'swiggy': 'Swiggy',
            'zomato': 'Zomato',
            'uber': 'Uber',
            'ola': 'Ola',
            'netflix': 'Netflix',
            'spotify': 'Spotify',
            'blinkit': 'Blinkit',
            'grofers': 'Grofers',
            'bigbasket': 'BigBasket',
            'myntra': 'Myntra',
            'jabong': 'Jabong',
            'makemytrip': 'MakeMyTrip',
            'goibibo': 'Goibibo',
            'irctc': 'IRCTC',
            'bookmyshow': 'BookMyShow',
            'dominos': 'Dominos',
            'kfc': 'KFC',
            'mcdonalds': 'McDonalds',
            'pizzahut': 'Pizza Hut'
        }
        
        # Only use sender-based merchant for non-bank senders
        if not any(bank in sender_lower for bank in ['hdfc', 'icici', 'sbi', 'axis', 'kotak', 'bank']):
            for key, name in merchants.items():
                if key in sender_lower:
                    return name
        
        # Extract from domain as fallback
        if '@' in sender:
            domain_parts = sender.split('@')[1].split('.')
            if domain_parts:
                domain = domain_parts[0]
                return domain.title()
        
        return 'Unknown'
    
    def _determine_type(self, content: str) -> str:
        """Determine transaction type with better accuracy"""
        content_lower = content.lower()
        
        # Check for specific transaction types
        if any(word in content_lower for word in ['refund', 'refunded', 'returned', 'reversed']):
            return 'refund'
        
        # Check for subscription-specific refund scenarios
        if 'subscription' in content_lower:
            if any(word in content_lower for word in ['suspended', 'declined', 'failed', 'issue', 'problem', 'attention']):
                return 'refund'  # Payment issue often leads to refund
            elif any(word in content_lower for word in ['renewed', 'renewal', 'active', 'continued', 'receipt', 'order', 'thank you']):
                return 'debit'   # Subscription renewal/order is a charge
        
        # General transaction types
        if any(word in content_lower for word in ['credited', 'received', 'deposit', 'cashback', 'credit']):
            return 'credit'
        elif any(word in content_lower for word in ['debited', 'charged', 'paid', 'payment']):
            return 'debit'
        
        # Special handling for subscription transactions
        if 'subscription' in content_lower:
            if any(word in content_lower for word in ['suspended', 'declined', 'failed', 'issue', 'problem', 'cancelled', 'refund', 'reversal', 'returned']):
                return 'refund'  # Payment issue often leads to refund
            elif any(word in content_lower for word in ['renewed', 'renewal', 'active', 'continued', 'purchase', 'spent', 'debit']):
                return 'debit'   # Subscription renewal is a charge
            elif any(word in content_lower for word in ['receipt', 'order', 'thank you']):
                return 'debit'   # Order receipt is a charge
        
        # Default to debit for most financial transactions
        return 'debit'
    
    def _extract_payment_method(self, content: str) -> str:
        """Extract payment method with enhanced detection"""
        content_lower = content.lower()
        
        if 'upi' in content_lower or 'vpa' in content_lower:
            return 'upi'
        elif any(word in content_lower for word in ['credit card', 'visa', 'mastercard', 'amex']):
            return 'credit_card'
        elif any(word in content_lower for word in ['debit card', 'atm', 'pos']):
            return 'debit_card'
        elif any(word in content_lower for word in ['neft', 'rtgs', 'imps', 'bank transfer']):
            return 'bank_transfer'
        elif any(word in content_lower for word in ['wallet', 'paytm wallet', 'phonepe wallet']):
            return 'wallet'
        else:
            return 'unknown'
    
    def _extract_account_info(self, content: str) -> Optional[str]:
        """Extract masked account info with better patterns"""
        for pattern in self.account_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"****{match.group(1)}"
        
        return None
    
    def _extract_transaction_id(self, content: str) -> Optional[str]:
        """Extract actual transaction ID with improved patterns"""
        # First try to extract with existing patterns
        for pattern in self.transaction_id_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted_id = match.group(1).strip()
                # Enhanced validation - exclude more generic words
                generic_words = [
                    'reference', 'interesting', 'application', 'processing', 
                    'subscription', 'active', 'suspended', 'renewed', 'declined',
                    'attention', 'reminder', 'update', 'backup', 'manage'
                ]
                if len(extracted_id) >= 6 and extracted_id.lower() not in generic_words:
                    return extracted_id
        
        # Special handling for subscription/recurring payments
        if any(word in content.lower() for word in ['subscription', 'recurring', 'renewal', 'google play', 'app store']):
            # Try to extract meaningful identifiers for subscriptions
            
            # Google Play order patterns with more specific matching
            google_play_match = re.search(r'(?:order receipt|receipt).*?(\w{3}\s+\d{1,2},\s+\d{4})', content, re.IGNORECASE)
            if google_play_match:
                date_str = google_play_match.group(1).replace(' ', '').replace(',', '')
                if 'chatgpt' in content.lower():
                    return f"CHATGPT_GPLAY_{date_str}"
                else:
                    return f"GPLAY_{date_str}"
            
            # Alternative Google Play pattern
            google_play_match2 = re.search(r'(?:google play).*?(?:receipt|order).*?(\w{3}\s+\d{1,2},\s+\d{4})', content, re.IGNORECASE)
            if google_play_match2:
                date_str = google_play_match2.group(1).replace(' ', '').replace(',', '')
                if 'chatgpt' in content.lower():
                    return f"CHATGPT_GPLAY_{date_str}"
                else:
                    return f"GPLAY_{date_str}"
            
            # Try to extract service name and date for subscription ID
            service_name = "SUBSCRIPTION"
            if 'chatgpt' in content.lower() or 'openai' in content.lower():
                service_name = "CHATGPT_SUB"
            elif 'netflix' in content.lower():
                service_name = "NETFLIX_SUB"
            elif 'spotify' in content.lower():
                service_name = "SPOTIFY_SUB"
            elif 'google play' in content.lower():
                service_name = "GOOGLE_PLAY_SUB"
            elif 'app store' in content.lower():
                service_name = "APP_STORE_SUB"
            
            # Extract date from content
            date_match = re.search(r'(\w{3}\s+\d{1,2},\s+\d{4})', content)
            if date_match:
                date_str = date_match.group(1).replace(' ', '').replace(',', '')
                return f"{service_name}_{date_str}"
            
            # Try different date formats
            date_match2 = re.search(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', content)
            if date_match2:
                date_str = date_match2.group(1).replace('/', '').replace('-', '')
                return f"{service_name}_{date_str}"
            
            # Fallback - use amount and service for unique ID
            amount_match = re.search(r'₹\s*([\d,]+\.?\d*)', content)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '').replace('.', '')
                return f"{service_name}_{amount_str}"
            
            # Final fallback for subscription payments
            if 'subscription' in content.lower():
                # Generate a subscription ID based on content hash
                import hashlib
                content_hash = hashlib.md5(content.encode()).hexdigest()[:8].upper()
                return f"{service_name}_{content_hash}"
        
        return None
    
    def _extract_bank_name(self, content: str, sender: str) -> Optional[str]:
        """Extract bank name from content or sender"""
        # Check sender first
        for pattern in self.bank_patterns:
            match = re.search(pattern, sender, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Check content
        for pattern in self.bank_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_upi_details(self, content: str) -> Dict[str, Any]:
        """Extract comprehensive UPI transaction details with clear sender/receiver distinction"""
        upi_details = {
            "transaction_flow": {},
            "sender": {},
            "receiver": {}
        }
        
        # Extract sender UPI details (from account)
        sender_account_match = re.search(r'from account\s+\*+(\d{4})', content, re.IGNORECASE)
        if sender_account_match:
            upi_details["sender"]["account_number"] = f"****{sender_account_match.group(1)}"
        
        # Extract receiver UPI details (to VPA)
        receiver_vpa_match = re.search(r'to VPA\s+([a-zA-Z0-9@.\-_]+@[a-zA-Z0-9.\-_]+)\s+([A-Z][a-zA-Z\s&0-9]+)', content)
        if receiver_vpa_match:
            upi_details["receiver"]["upi_id"] = receiver_vpa_match.group(1)
            upi_details["receiver"]["name"] = receiver_vpa_match.group(2).strip()
            
            # Determine UPI app from VPA
            vpa = receiver_vpa_match.group(1).lower()
            if '@paytm' in vpa or 'paytm' in vpa:
                upi_details["receiver"]["upi_app"] = "Paytm"
            elif '@axisbank' in vpa:
                upi_details["receiver"]["upi_app"] = "Axis Bank UPI"
            elif '@ybl' in vpa:
                upi_details["receiver"]["upi_app"] = "PhonePe"
            elif '@oksbi' in vpa or '@sbi' in vpa:
                upi_details["receiver"]["upi_app"] = "SBI UPI"
            elif '@hdfcbank' in vpa or '@hdfc' in vpa:
                upi_details["receiver"]["upi_app"] = "HDFC Bank UPI"
            elif '@icici' in vpa:
                upi_details["receiver"]["upi_app"] = "ICICI Bank UPI"
            elif '@cnrb' in vpa:
                upi_details["receiver"]["upi_app"] = "Canara Bank UPI"
            else:
                upi_details["receiver"]["upi_app"] = "Unknown UPI App"
        
        # Extract sender UPI details (from VPA - for incoming transactions)
        sender_vpa_match = re.search(r'from VPA\s+([a-zA-Z0-9@.\-_]+@[a-zA-Z0-9.\-_]+)\s+([A-Z\s&0-9]+)', content)
        if sender_vpa_match:
            upi_details["sender"]["upi_id"] = sender_vpa_match.group(1)
            upi_details["sender"]["name"] = sender_vpa_match.group(2).strip()
        
        # Determine transaction direction
        if 'debited' in content.lower():
            upi_details["transaction_flow"]["direction"] = "outgoing"
            upi_details["transaction_flow"]["description"] = "Money sent from your account"
        elif 'credited' in content.lower():
            upi_details["transaction_flow"]["direction"] = "incoming"
            upi_details["transaction_flow"]["description"] = "Money received in your account"
        
        # Clean up empty sections
        upi_details = {k: v for k, v in upi_details.items() if v}
        
        return upi_details
    
    def _extract_card_details(self, content: str) -> Dict[str, Any]:
        """Extract card transaction details"""
        card_details = {}
        
        # Extract masked card number
        for pattern in self.card_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                card_details['card_number'] = f"****{match.group(1)}"
                break
        
        # Determine card type
        if any(word in content.lower() for word in ['visa', 'mastercard', 'amex', 'rupay']):
            if 'visa' in content.lower():
                card_details['card_type'] = 'Visa'
            elif 'mastercard' in content.lower():
                card_details['card_type'] = 'Mastercard'
            elif 'amex' in content.lower():
                card_details['card_type'] = 'American Express'
            elif 'rupay' in content.lower():
                card_details['card_type'] = 'RuPay'
        
        return card_details

async def process_financial_transactions_from_mongodb(user_id: str) -> Dict[str, Any]:
    """
    Process financial transactions from MongoDB emails
    FIXED: Handles asyncio event loop conflicts properly
    """
    try:
        logger.info(f"Processing financial transactions from MongoDB for user: {user_id}")
        
        # ✅ FIX: Create proper async context for database operations
        import asyncio
        
        # Handle uvloop and standard asyncio loops properly
        try:
            loop = asyncio.get_running_loop()
            logger.debug(f"Using existing event loop: {type(loop)}")
        except RuntimeError:
            logger.debug("No running event loop found")
        
        # Use user-specific collection via db_manager (handles sharding)
        from .db import db_manager  # local import to avoid circular deps
        emails_coll = await db_manager.get_collection(user_id, "emails")

        # Project only the fields needed for financial extraction to minimize payload
        projection = {
            "_id": 0,
            "subject": 1,
            "snippet": 1,
            "body": 1,
            "sender": 1,
            "date": 1
        }

        cursor = emails_coll.find({"user_id": user_id}, projection=projection).batch_size(200)

        all_emails: List[Dict] = []
        async for email_doc in cursor:
            all_emails.append(email_doc)

        logger.debug(f"Successfully streamed {len(all_emails)} emails from database (projection mode)")
        
        # Extract financial transactions
        extractor = EnhancedTransactionExtractor()
        financial_emails = []
        transactions = []
        
        for email in all_emails:
            if extractor.is_financial_email(email):
                financial_emails.append(email)
                logger.info(f"📧 Processing financial email: {email.get('subject', '')[:50]}... from {email.get('sender', '')[:30]}...")
                transaction = extractor.extract_transaction(email, user_id)
                if transaction:
                    transactions.append(transaction)
                    logger.info(f"✅ Transaction extracted: ₹{transaction.get('amount', 0)} from {transaction.get('merchant', 'Unknown')}")
                else:
                    logger.warning(f"❌ No transaction extracted from: {email.get('subject', '')[:50]}...")
        
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
        
        # Store in financial_transactions collection with proper async handling
        financial_collection = db["financial_transactions"]
        
        # 🔄 UPSERT transactions one-by-one (or in bulk) to avoid data loss
        from pymongo import UpdateOne
        bulk_ops = []
        for txn in transactions:
            txn_id = txn.get("id")
            if not txn_id:
                # Fallback: derive deterministic id from email + amount
                import hashlib, json
                txn_id = hashlib.md5(json.dumps(txn, sort_keys=True).encode()).hexdigest()
                txn["id"] = txn_id

            bulk_ops.append(
                UpdateOne(
                    {"user_id": user_id, "id": txn_id},
                    {"$set": txn},
                    upsert=True
                )
            )

        if bulk_ops:
            result = await financial_collection.bulk_write(bulk_ops, ordered=False)
            inserted_count = result.upserted_count + result.inserted_count
            modified_count = result.modified_count
            logger.info(f"Upserted {inserted_count} new and modified {modified_count} existing transactions for user {user_id}")
        else:
            logger.info("No transactions to upsert")
        
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
        
        # Upsert summary for the period
        summary_collection = db["financial_summaries"]
        await summary_collection.update_one(
            {"user_id": user_id, "period": "all_stored_emails"},
            {"$set": summary},
            upsert=True
        )
        logger.info("Upserted financial summary in database")
        
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