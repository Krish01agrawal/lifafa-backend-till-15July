#!/usr/bin/env python3

"""
Enhanced Financial Transaction Detector
======================================

This module provides intelligent financial email detection that can distinguish
between actual financial transactions and non-transaction emails like:
- Job postings mentioning salary (CTC)
- Investment newsletters mentioning amounts
- News articles about financial topics
- Promotional emails with prices

Key Features:
- Context-aware amount detection
- Job posting exclusion
- Recruitment site filtering
- Content analysis for transaction vs. mention
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedFinancialDetector:
    """
    Smart financial email detector with context awareness
    """
    
    def __init__(self):
        # Basic currency patterns
        self.currency_patterns = [
            r'₹\s*([\d,]+\.?\d*)',
            r'Rs\.?\s*([\d,]+\.?\d*)',
            r'INR\s*([\d,]+\.?\d*)',
        ]
        
        # =============================================
        # EXCLUSION PATTERNS (HIGH PRIORITY)
        # =============================================
        
        # Job posting domains and senders (EXPANDED)
        self.job_posting_domains = [
            'dare2compete.news', 'unstop.com', 'naukri.com', 'linkedin.com',
            'glassdoor.com', 'monster.com', 'indeed.com', 'timesjobs.com',
            'shine.com', 'freshersworld.com', 'internshala.com', 'recruitment',
            'careers', 'hiring', 'jobs', 'hr@', 'recruitment@',
            # Educational/Learning platforms (often send promotional emails)
            'techgig.com', 'hack2skill.com', 'hackerrank.com', 'hackerearth.com',
            'geeksforgeeks.org', 'coursera.org', 'udemy.com', 'edx.org'
        ]
        
        # Job posting keywords that indicate NOT a transaction
        self.job_posting_keywords = [
            'ctc', 'cost to company', 'salary', 'package', 'lpa', 'per annum',
            'hiring', 'job opening', 'position', 'vacancy', 'recruitment',
            'career opportunity', 'apply now', 'job alert', 'interview',
            'fresher', 'experienced', 'candidates', 'application', 'resume',
            'eligibility', 'required skills', 'job description', 'role',
            'openings', 'hiring alert', 'mega hiring', 'walk-in', 'campus',
            'placement', 'career', 'opportunity', 'join our team'
        ]
        
        # Educational/Learning keywords that indicate NOT a transaction
        self.educational_keywords = [
            'course', 'learn', 'learning', 'tutorial', 'training', 'education',
            'skill', 'challenge', 'competition', 'contest', 'programming',
            'coding', 'development', 'workshop', 'webinar', 'masterclass',
            'certification', 'certificate', 'diploma', 'degree', 'study',
            'academy', 'institute', 'university', 'college', 'school'
        ]
        
        # News/newsletter keywords that indicate NOT a transaction
        self.news_newsletter_keywords = [
            'newsletter', 'digest', 'news', 'article', 'report', 'analysis',
            'market update', 'daily brief', 'weekly roundup', 'insights',
            'commentary', 'opinion', 'editorial', 'breaking news', 'headlines',
            'market watch', 'business news', 'financial news', 'economic update'
        ]
        
        # Promotional keywords that indicate NOT a transaction
        self.promotional_keywords = [
            'offer', 'discount', 'sale', 'deal', 'promo', 'coupon', 'limited time',
            'exclusive offer', 'special price', 'buy now', 'shop now', 'save up to',
            'flat discount', '% off', 'cashback offer', 'free shipping', 'hurry up'
        ]
        
        # =============================================
        # TRANSACTION INDICATORS (POSITIVE SIGNALS)
        # =============================================
        
        # Strong transaction keywords (definite transactions)
        self.strong_transaction_keywords = [
            'debited', 'credited', 'charged', 'paid', 'received', 'refunded',
            'transaction successful', 'payment completed', 'order placed',
            'booking confirmed', 'purchase successful', 'bill paid',
            'amount transferred', 'money sent', 'money received'
        ]
        
        # General financial keywords (broader indicators)
        self.financial_keywords = [
            'transaction', 'payment', 'debit', 'credit', 'refund', 'invoice', 'receipt',
            'statement', 'balance', 'transfer', 'withdrawal', 'deposit', 'subscription',
            'billing', 'amount', 'rupees', 'inr', 'upi', 'netbanking',
            'credit card', 'debit card', 'loan', 'emi', 'interest', 'bank', 'account',
            'order', 'purchase', 'bought', 'cart', 'checkout', 'delivery', 'shipped',
            'booking', 'reservation', 'ticket', 'confirmation', 'bill', 'due'
        ]
        
        # Transaction context patterns
        self.transaction_patterns = [
            r'(?:debited|charged|paid)\s*[:\-]?\s*₹\s*[\d,]+',
            r'(?:credited|received|refunded)\s*[:\-]?\s*₹\s*[\d,]+',
            r'order\s*(?:id|no|number)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'transaction\s*(?:id|ref|no)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'upi\s*(?:ref|id|txn)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'payment\s*(?:successful|completed|failed)',
            r'booking\s*(?:confirmed|cancelled)',
            r'subscription\s*(?:activated|renewed|cancelled)'
        ]
        
        # Trusted financial sender domains (comprehensive list)
        self.trusted_financial_domains = [
            # Banks
            'hdfcbank', 'icici', 'sbi', 'axisbank', 'kotakbank', 'pnb', 'bankofbaroda',
            'yesbank', 'indusind', 'unionbank', 'canarabank', 'indianbank',
            # Payment platforms
            'paytm', 'phonepe', 'googlepay', 'amazonpay', 'mobikwik', 'freecharge',
            # E-commerce
            'amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'bigbasket', 'grofers',
            # Food delivery & transport
            'swiggy', 'zomato', 'uber', 'ola', 'rapido', 'dominos', 'pizzahut',
            # Travel
            'makemytrip', 'goibibo', 'oyorooms', 'cleartrip', 'irctc', 'redbus',
            'indigo', 'spicejet', 'airindia', 'vistara',
            # Subscriptions & services
            'netflix', 'spotify', 'adobe', 'microsoft', 'google', 'apple', 'disney',
            'hotstar', 'primevideo', 'youtube', 'openai', 'anthropic', 'midjourney',
            'canva', 'dropbox', 'icloud', 'playstation', 'xbox', 'steam',
            # Utilities & telecom
            'airtel', 'jio', 'vodafone', 'bsnl', 'tata', 'adani', 'bescom',
            # Investment & finance
            'zerodha', 'groww', 'angelbroking', 'icicidirect', 'hdfcsec', 'kotaksecurities',
            'mutualfund', 'sbi', 'axis', 'hdfc', 'icici',
            # Others
            'cult', 'healthify', 'kindle', 'times', 'rentomojo', 'urbancompany'
        ]
    
    def is_financial_email(self, email_data: Dict) -> bool:
        """
        Enhanced financial email detection with context awareness
        
        Returns True only if this is likely an actual financial transaction,
        not just an email mentioning money amounts.
        """
        
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        snippet = email_data.get('snippet', '').lower()
        body = email_data.get('body', '').lower()
        
        full_content = f"{subject} {snippet} {body}"
        
        # =============================================
        # STEP 1: EXCLUSION CHECKS (HIGH PRIORITY)
        # =============================================
        
        # Check if it's from a job posting domain
        if self._is_job_posting_email(sender, full_content):
            logger.debug(f"Email excluded: Job posting detected from {sender}")
            return False
        
        # Check if it's a news/newsletter
        if self._is_news_newsletter(sender, full_content):
            logger.debug(f"Email excluded: News/newsletter detected from {sender}")
            return False
        
        # Check if it's promotional content
        if self._is_promotional_email(full_content):
            logger.debug(f"Email excluded: Promotional content detected")
            return False
        
        # Check if it's educational/learning content
        if self._is_educational_content(sender, full_content):
            logger.debug(f"Email excluded: Educational content detected from {sender}")
            return False
        
        # =============================================
        # STEP 2: POSITIVE FINANCIAL INDICATORS
        # =============================================
        
        # Check for strong transaction indicators (definite transactions)
        has_strong_transaction = self._has_strong_transaction_indicators(full_content)
        
        # Check if sender is from trusted financial domain
        is_trusted_sender = self._is_trusted_financial_sender(sender)
        
        # Check for transaction patterns
        has_transaction_patterns = self._has_transaction_patterns(full_content)
        
        # Check for general financial keywords (broader indicators)
        has_financial_keywords = self._has_financial_keywords(full_content)
        
        # Check for currency patterns with amount
        has_currency_amount = self._has_currency_patterns(full_content)
        
        # =============================================
        # STEP 3: INTELLIGENT DECISION LOGIC
        # =============================================
        
        # Strong positive indicators (definite financial emails)
        if has_strong_transaction or is_trusted_sender:
            logger.debug(f"Email identified as financial: strong_transaction={has_strong_transaction}, trusted_sender={is_trusted_sender}")
            return True
        
        # Medium confidence indicators (need multiple signals)
        medium_confidence_signals = [
            has_transaction_patterns,
            has_financial_keywords,
            has_currency_amount
        ]
        
        # Require at least 2 medium confidence signals for financial classification
        medium_signals_count = sum(1 for signal in medium_confidence_signals if signal)
        
        if medium_signals_count >= 2:
            logger.debug(f"Email identified as financial: transaction_patterns={has_transaction_patterns}, financial_keywords={has_financial_keywords}, currency_amount={has_currency_amount}")
            return True
        
        logger.debug(f"Email excluded: Insufficient financial indicators (strong=0, medium={medium_signals_count}/3)")
        return False
    
    def _is_job_posting_email(self, sender: str, content: str) -> bool:
        """Check if email is a job posting"""
        
        # Check sender domain
        for domain in self.job_posting_domains:
            if domain in sender:
                return True
        
        # Check for job posting keywords (need multiple indicators)
        job_keywords_found = sum(1 for keyword in self.job_posting_keywords if keyword in content)
        
        # If multiple job keywords + currency mention = likely job posting
        if job_keywords_found >= 2:
            # Additional check: if content mentions "CTC" or "LPA" = definitely job posting
            if any(term in content for term in ['ctc', 'lpa', 'per annum', 'cost to company']):
                return True
            
            # If hiring-related terms + amount = job posting
            if any(term in content for term in ['hiring', 'openings', 'positions', 'vacancy']):
                return True
        
        return False
    
    def _is_news_newsletter(self, sender: str, content: str) -> bool:
        """Check if email is news/newsletter"""
        
        # Check for newsletter in sender
        if any(term in sender for term in ['newsletter', 'digest', 'news', 'insights']):
            return True
        
        # Check for news keywords in content
        news_keywords_found = sum(1 for keyword in self.news_newsletter_keywords if keyword in content)
        return news_keywords_found >= 2
    
    def _is_promotional_email(self, content: str) -> bool:
        """Check if email is promotional"""
        
        promo_keywords_found = sum(1 for keyword in self.promotional_keywords if keyword in content)
        return promo_keywords_found >= 2
    
    def _is_educational_content(self, sender: str, content: str) -> bool:
        """Check if email is educational/learning content"""
        
        # Check for educational domains in sender
        educational_domains = ['techgig.com', 'hack2skill.com', 'hackerrank.com', 'hackerearth.com',
                              'geeksforgeeks.org', 'coursera.org', 'udemy.com', 'edx.org']
        
        for domain in educational_domains:
            if domain in sender:
                return True
        
        # Check for educational keywords (need multiple indicators)
        educational_keywords_found = sum(1 for keyword in self.educational_keywords if keyword in content)
        
        # If multiple educational keywords = educational content
        if educational_keywords_found >= 2:
            return True
        
        # Check for specific learning patterns
        learning_patterns = [
            'deep learning', 'machine learning', 'data science', 'programming challenge',
            'coding contest', 'learn to build', 'tutorial', 'course completion',
            'skill development', 'training program'
        ]
        
        for pattern in learning_patterns:
            if pattern in content:
                return True
        
        return False
    
    def _has_strong_transaction_indicators(self, content: str) -> bool:
        """Check for strong transaction language"""
        
        return any(keyword in content for keyword in self.strong_transaction_keywords)
    
    def _is_trusted_financial_sender(self, sender: str) -> bool:
        """Check if sender is from trusted financial domain"""
        
        return any(domain in sender for domain in self.trusted_financial_domains)
    
    def _has_transaction_patterns(self, content: str) -> bool:
        """Check for transaction-specific patterns"""
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in self.transaction_patterns)
    
    def _has_financial_keywords(self, content: str) -> bool:
        """Check for general financial keywords"""
        
        return any(keyword in content for keyword in self.financial_keywords)
    
    def _has_currency_patterns(self, content: str) -> bool:
        """Check for currency patterns with amounts"""
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in self.currency_patterns)
    
    def extract_transaction_amount(self, email_data: Dict) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract transaction amount only if this is confirmed to be a financial email
        """
        
        if not self.is_financial_email(email_data):
            return None, None
        
        content = f"{email_data.get('subject', '')} {email_data.get('snippet', '')} {email_data.get('body', '')}"
        
        # Extract amount using currency patterns
        for pattern in self.currency_patterns:
            match = re.search(pattern, content)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    return amount, "INR"
                except ValueError:
                    continue
        
        return None, None
    
    def get_exclusion_reason(self, email_data: Dict) -> Optional[str]:
        """
        Get the reason why an email was excluded (for debugging)
        """
        
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        snippet = email_data.get('snippet', '').lower()
        body = email_data.get('body', '').lower()
        
        full_content = f"{subject} {snippet} {body}"
        
        if self._is_job_posting_email(sender, full_content):
            return f"job_posting_from_{sender}"
        
        if self._is_news_newsletter(sender, full_content):
            return f"news_newsletter_from_{sender}"
        
        if self._is_promotional_email(full_content):
            return "promotional_content"
        
        if self._is_educational_content(sender, full_content):
            return f"educational_content_from_{sender}"
        
        return "no_strong_financial_indicators"

# Global instance
enhanced_financial_detector = EnhancedFinancialDetector()

# Convenience functions
def is_actual_financial_transaction(email_data: Dict) -> bool:
    """
    Check if email represents an actual financial transaction
    (not just mentioning money amounts)
    """
    return enhanced_financial_detector.is_financial_email(email_data)

def extract_transaction_amount_safe(email_data: Dict) -> Tuple[Optional[float], Optional[str]]:
    """
    Safely extract transaction amount only from confirmed financial emails
    """
    return enhanced_financial_detector.extract_transaction_amount(email_data)

def get_financial_exclusion_reason(email_data: Dict) -> Optional[str]:
    """
    Get reason why email was excluded from financial processing
    """
    return enhanced_financial_detector.get_exclusion_reason(email_data) 