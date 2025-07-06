#!/usr/bin/env python3

"""
Advanced Two-Stage Email Filter
===============================

Stage 1: Conservative filtering (preserve everything that might be important)
Stage 2: Deep content analysis for newsletters and promotional content

This ensures zero data loss while still filtering out clear promotional content.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from .config import ENABLE_SMART_EMAIL_FILTERING

# Configure logging
logger = logging.getLogger(__name__)

class AdvancedEmailFilter:
    """
    Advanced two-stage email filtering system
    
    Stage 1: Conservative filtering (current system)
    Stage 2: Deep content analysis for newsletters and promotional articles
    """
    
    def __init__(self):
        self.stats = {
            "stage1_processed": 0,
            "stage1_filtered": 0,
            "stage2_processed": 0,
            "stage2_filtered": 0,
            "newsletters_filtered": 0,
            "promotional_articles_filtered": 0,
            "preserved_for_safety": 0,
            "total_space_saved": 0
        }
    
    def reset_stats(self):
        """Reset filtering statistics"""
        self.stats = {key: 0 for key in self.stats.keys()}
    
    async def two_stage_filter_emails(self, emails: List[Dict], user_id: str, processing_type: str = "two-stage") -> List[Dict]:
        """
        Apply two-stage filtering to emails
        
        Stage 1: Conservative filtering (preserve everything that might be important)
        Stage 2: Deep content analysis for newsletters and promotional articles
        """
        
        logger.info(f"🔍 [{processing_type.upper()}] Starting two-stage filtering for {len(emails)} emails")
        
        # Stage 1: Conservative filtering (existing system)
        stage1_start = datetime.now()
        from .db import email_filter
        
        stage1_filtered = await email_filter.smart_filter_emails(emails, user_id, f"{processing_type}-stage1")
        self.stats["stage1_processed"] = len(emails)
        self.stats["stage1_filtered"] = len(emails) - len(stage1_filtered)
        
        stage1_time = (datetime.now() - stage1_start).total_seconds()
        logger.info(f"✅ [STAGE 1] Conservative filtering: {len(emails)} → {len(stage1_filtered)} emails (removed {self.stats['stage1_filtered']}) in {stage1_time:.2f}s")
        
        if not stage1_filtered:
            logger.info(f"📭 [COMPLETE] No emails left after stage 1 filtering")
            return []
        
        # Stage 2: Deep content analysis
        stage2_start = datetime.now()
        stage2_filtered = await self._stage2_deep_content_analysis(stage1_filtered, user_id, processing_type)
        self.stats["stage2_processed"] = len(stage1_filtered)
        self.stats["stage2_filtered"] = len(stage1_filtered) - len(stage2_filtered)
        
        stage2_time = (datetime.now() - stage2_start).total_seconds()
        logger.info(f"✅ [STAGE 2] Deep content analysis: {len(stage1_filtered)} → {len(stage2_filtered)} emails (removed {self.stats['stage2_filtered']}) in {stage2_time:.2f}s")
        
        # Total statistics
        total_removed = len(emails) - len(stage2_filtered)
        total_time = stage1_time + stage2_time
        
        logger.info(f"🎯 [COMPLETE] Two-stage filtering results:")
        logger.info(f"   📊 Original emails: {len(emails)}")
        logger.info(f"   📧 Final preserved: {len(stage2_filtered)}")
        logger.info(f"   🗑️ Total removed: {total_removed}")
        logger.info(f"   📈 Preservation rate: {(len(stage2_filtered)/len(emails)*100):.1f}%")
        logger.info(f"   ⏱️ Total time: {total_time:.2f}s")
        logger.info(f"   📰 Newsletters filtered: {self.stats['newsletters_filtered']}")
        logger.info(f"   📄 Promotional articles filtered: {self.stats['promotional_articles_filtered']}")
        logger.info(f"   🛡️ Preserved for safety: {self.stats['preserved_for_safety']}")
        
        return stage2_filtered
    
    async def _stage2_deep_content_analysis(self, emails: List[Dict], user_id: str, processing_type: str) -> List[Dict]:
        """
        Stage 2: Deep content analysis for newsletters and promotional articles
        
        This stage analyzes the complete email content and applies sophisticated filtering
        for newsletters and promotional articles while being very careful to preserve 
        anything that might have value.
        """
        
        logger.info(f"🔍 [STAGE 2] Starting deep content analysis for {len(emails)} emails")
        
        filtered_emails = []
        
        for i, email in enumerate(emails):
            try:
                # Analyze email content deeply
                keep_email, reason = self._analyze_email_content_deeply(email)
                
                if keep_email:
                    filtered_emails.append(email)
                    
                    # Add stage 2 metadata
                    email["stage2_reason"] = reason
                    email["stage2_analyzed_at"] = datetime.now().isoformat()
                else:
                    # Log filtered email for transparency
                    logger.info(f"🗑️ [STAGE 2] Filtered: {email.get('subject', 'No Subject')[:50]}... | Reason: {reason}")
                
                # Progress logging
                if (i + 1) % 50 == 0:
                    progress = ((i + 1) / len(emails)) * 100
                    logger.info(f"📊 [STAGE 2] Progress: {progress:.1f}% ({i + 1}/{len(emails)} emails analyzed)")
            
            except Exception as e:
                # If analysis fails, preserve email to be safe
                logger.error(f"❌ [STAGE 2] Error analyzing email {email.get('id', 'unknown')}: {e}")
                filtered_emails.append(email)
                email["stage2_reason"] = "analysis_failed_preserved"
                self.stats["preserved_for_safety"] += 1
        
        return filtered_emails
    
    def _analyze_email_content_deeply(self, email: Dict) -> Tuple[bool, str]:
        """
        Deep analysis of email content to determine if it should be kept
        
        Returns:
            (keep_email: bool, reason: str)
        """
        
        # Extract all content for analysis
        subject = email.get('subject', '').lower()
        sender = email.get('sender', '').lower()
        snippet = email.get('snippet', '').lower()
        body = email.get('body', '').lower()
        
        # Combine all content for analysis
        full_content = f"{subject} {sender} {snippet} {body}"
        
        # 🛡️ SAFETY CHECKS: Always preserve if any of these conditions are met
        
        # 1. Has any transactional content (highest priority)
        if self._has_transactional_content(full_content):
            return True, "transactional_content"
        
        # 2. Has any financial/payment content
        if self._has_financial_content(full_content):
            return True, "financial_content"
        
        # 3. Has any booking/reservation content
        if self._has_booking_content(full_content):
            return True, "booking_content"
        
        # 4. Has any subscription/service content
        if self._has_subscription_content(full_content):
            return True, "subscription_content"
        
        # 5. Has any important account/service notifications
        if self._has_important_notifications(full_content):
            return True, "important_notification"
        
        # 6. From important senders (even if content looks promotional)
        if self._is_important_sender(sender):
            return True, "important_sender"
        
        # 7. Has any purchase/order content
        if self._has_purchase_content(full_content):
            return True, "purchase_content"
        
        # 🔍 PROMOTIONAL ANALYSIS: Only filter if clearly promotional AND no value
        
        # Check if it's clearly a newsletter
        is_newsletter, newsletter_confidence = self._is_newsletter(email)
        if is_newsletter and newsletter_confidence > 0.8:
            # Even newsletters can have value, so check for exceptions
            if self._newsletter_has_value(full_content):
                return True, "newsletter_with_value"
            else:
                self.stats["newsletters_filtered"] += 1
                return False, f"newsletter_filtered_confidence_{newsletter_confidence:.2f}"
        
        # Check if it's clearly a promotional article
        is_promotional_article, promo_confidence = self._is_promotional_article(email)
        if is_promotional_article and promo_confidence > 0.8:
            # Check if promotional article has any value
            if self._promotional_article_has_value(full_content):
                return True, "promotional_article_with_value"
            else:
                self.stats["promotional_articles_filtered"] += 1
                return False, f"promotional_article_filtered_confidence_{promo_confidence:.2f}"
        
        # Check if it's clearly marketing spam
        is_marketing_spam, spam_confidence = self._is_marketing_spam(email)
        if is_marketing_spam and spam_confidence > 0.9:  # Very high confidence required
            self.stats["stage2_filtered"] += 1
            return False, f"marketing_spam_confidence_{spam_confidence:.2f}"
        
        # 🛡️ DEFAULT: When in doubt, PRESERVE
        return True, "preserved_by_default"
    
    def _has_transactional_content(self, content: str) -> bool:
        """Check if content has any transactional elements"""
        transaction_patterns = [
            r'[₹\$]\s*[\d,]+',  # Amount patterns
            r'(?:rs\.?|rupees?|inr)\s*[\d,]+',
            r'paid\s*[:\-]?\s*[₹\$]?[\d,]+',
            r'charged\s*[:\-]?\s*[₹\$]?[\d,]+',
            r'order\s*(?:id|no|number)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'transaction\s*(?:id|ref|no)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'reference\s*(?:no|number)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'booking\s*(?:id|ref|no)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'ticket\s*(?:no|number)?\s*[:\-]?\s*[a-zA-Z0-9]+',
            r'invoice\s*(?:no|number)?\s*[:\-]?\s*[a-zA-Z0-9]+',
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in transaction_patterns)
    
    def _has_financial_content(self, content: str) -> bool:
        """Check if content has financial/banking elements"""
        financial_keywords = [
            'payment', 'transaction', 'credited', 'debited', 'balance', 'statement',
            'account', 'bank', 'card', 'upi', 'wallet', 'investment', 'mutual fund',
            'trading', 'stock', 'portfolio', 'dividend', 'interest', 'loan', 'emi'
        ]
        
        return any(keyword in content for keyword in financial_keywords)
    
    def _has_booking_content(self, content: str) -> bool:
        """Check if content has booking/reservation elements"""
        booking_keywords = [
            'booking', 'reservation', 'confirmed', 'cancelled', 'rescheduled',
            'flight', 'hotel', 'train', 'bus', 'taxi', 'cab', 'ticket', 'itinerary',
            'check-in', 'check-out', 'pnr', 'boarding', 'seat', 'travel'
        ]
        
        return any(keyword in content for keyword in booking_keywords)
    
    def _has_subscription_content(self, content: str) -> bool:
        """Check if content has subscription/service elements"""
        subscription_keywords = [
            'subscription', 'plan', 'premium', 'pro', 'membership', 'renewal',
            'expired', 'activate', 'upgrade', 'downgrade', 'billing', 'auto-renewal'
        ]
        
        return any(keyword in content for keyword in subscription_keywords)
    
    def _has_important_notifications(self, content: str) -> bool:
        """Check if content has important account/service notifications"""
        notification_keywords = [
            'security', 'password', 'login', 'account', 'verification', 'otp',
            'two-factor', '2fa', 'authentication', 'suspicious', 'unauthorized',
            'locked', 'suspended', 'reactivate', 'verify', 'confirm'
        ]
        
        return any(keyword in content for keyword in notification_keywords)
    
    def _is_important_sender(self, sender: str) -> bool:
        """Check if sender is from an important service/platform"""
        important_domains = [
            # Banking
            'bank', 'hdfc', 'icici', 'sbi', 'axis', 'kotak', 'pnb',
            # Payment platforms
            'paytm', 'phonepe', 'googlepay', 'amazonpay', 'razorpay',
            # E-commerce
            'amazon', 'flipkart', 'myntra', 'nykaa', 'bigbasket',
            # Food delivery
            'swiggy', 'zomato', 'ubereats', 'dominos',
            # Travel
            'makemytrip', 'goibibo', 'irctc', 'uber', 'ola',
            # Investment
            'zerodha', 'groww', 'angelbroking', 'icicidirect',
            # Government
            'gov.in', 'uidai', 'epfo', 'irctc', 'incometax'
        ]
        
        return any(domain in sender for domain in important_domains)
    
    def _has_purchase_content(self, content: str) -> bool:
        """Check if content has purchase/order elements"""
        purchase_keywords = [
            'order', 'purchase', 'bought', 'delivered', 'shipped', 'dispatched',
            'tracking', 'delivery', 'item', 'product', 'cart', 'checkout',
            'receipt', 'invoice', 'return', 'refund', 'exchange'
        ]
        
        return any(keyword in content for keyword in purchase_keywords)
    
    def _is_newsletter(self, email: Dict) -> Tuple[bool, float]:
        """
        Determine if email is a newsletter
        
        Returns:
            (is_newsletter: bool, confidence: float)
        """
        
        subject = email.get('subject', '').lower()
        sender = email.get('sender', '').lower()
        body = email.get('body', '').lower()
        
        confidence = 0.0
        
        # Newsletter indicators in subject
        newsletter_subject_patterns = [
            r'newsletter',
            r'weekly\s+(?:digest|update|roundup)',
            r'daily\s+(?:digest|update|roundup)',
            r'monthly\s+(?:digest|update|roundup)',
            r'this\s+week\s+in',
            r'edition\s+#?\d+',
            r'issue\s+#?\d+',
            r'vol\.*\s*\d+',
            r'digest\s+for'
        ]
        
        for pattern in newsletter_subject_patterns:
            if re.search(pattern, subject):
                confidence += 0.3
        
        # Newsletter indicators in sender
        newsletter_sender_patterns = [
            r'newsletter@',
            r'noreply@.*newsletter',
            r'digest@',
            r'updates@',
            r'weekly@',
            r'daily@'
        ]
        
        for pattern in newsletter_sender_patterns:
            if re.search(pattern, sender):
                confidence += 0.4
        
        # Newsletter indicators in body
        newsletter_body_patterns = [
            r'unsubscribe\s+from\s+this\s+newsletter',
            r'weekly\s+newsletter',
            r'daily\s+newsletter',
            r'you\s+are\s+receiving\s+this\s+because',
            r'manage\s+your\s+subscription',
            r'view\s+this\s+email\s+in\s+your\s+browser'
        ]
        
        for pattern in newsletter_body_patterns:
            if re.search(pattern, body):
                confidence += 0.2
        
        return confidence > 0.6, min(confidence, 1.0)
    
    def _is_promotional_article(self, email: Dict) -> Tuple[bool, float]:
        """
        Determine if email is a promotional article
        
        Returns:
            (is_promotional_article: bool, confidence: float)
        """
        
        subject = email.get('subject', '').lower()
        sender = email.get('sender', '').lower()
        body = email.get('body', '').lower()
        
        confidence = 0.0
        
        # Promotional article indicators
        promo_patterns = [
            r'(?:limited\s+time|special)\s+offer',
            r'(?:save|discount|off)\s+(?:up\s+to\s+)?\d+%',
            r'exclusive\s+(?:deal|offer|access)',
            r'(?:flash|mega|super)\s+sale',
            r'today\s+only',
            r'hurry\s+(?:up|now)',
            r'don\'t\s+miss\s+out',
            r'act\s+now',
            r'while\s+supplies\s+last',
            r'limited\s+stock'
        ]
        
        content = f"{subject} {body}"
        
        for pattern in promo_patterns:
            if re.search(pattern, content):
                confidence += 0.25
        
        # Marketing sender indicators
        marketing_sender_patterns = [
            r'marketing@',
            r'promo@',
            r'offers@',
            r'deals@',
            r'noreply@.*(?:marketing|promo|offers)'
        ]
        
        for pattern in marketing_sender_patterns:
            if re.search(pattern, sender):
                confidence += 0.3
        
        return confidence > 0.6, min(confidence, 1.0)
    
    def _is_marketing_spam(self, email: Dict) -> Tuple[bool, float]:
        """
        Determine if email is marketing spam (very high confidence required)
        
        Returns:
            (is_marketing_spam: bool, confidence: float)
        """
        
        subject = email.get('subject', '').lower()
        sender = email.get('sender', '').lower()
        body = email.get('body', '').lower()
        
        confidence = 0.0
        
        # Very clear spam indicators
        spam_patterns = [
            r'congratulations.*winner',
            r'you\'ve\s+won\s+(?:a\s+)?(?:free|prize)',
            r'claim\s+your\s+(?:free|prize)',
            r'click\s+here\s+to\s+claim',
            r'urgent\s+action\s+required',
            r'verify\s+your\s+account\s+immediately',
            r'suspended.*click\s+here',
            r'nigerian\s+prince',
            r'lottery\s+winner',
            r'inherit.*million'
        ]
        
        content = f"{subject} {body}"
        
        for pattern in spam_patterns:
            if re.search(pattern, content):
                confidence += 0.4
        
        # Suspicious sender patterns
        suspicious_sender_patterns = [
            r'[a-zA-Z0-9]{20,}@',  # Very long random sender
            r'noreply@[a-zA-Z0-9]{10,}\.com',  # Random domain
            r'.*\.tk$',  # Suspicious TLD
            r'.*\.ml$',  # Suspicious TLD
        ]
        
        for pattern in suspicious_sender_patterns:
            if re.search(pattern, sender):
                confidence += 0.3
        
        return confidence > 0.8, min(confidence, 1.0)
    
    def _newsletter_has_value(self, content: str) -> bool:
        """Check if newsletter has any valuable content"""
        valuable_patterns = [
            r'investment\s+(?:advice|update|news)',
            r'market\s+(?:update|news|analysis)',
            r'financial\s+(?:news|update|advice)',
            r'economic\s+(?:news|update|analysis)',
            r'industry\s+(?:news|update|analysis)',
            r'policy\s+(?:change|update|news)',
            r'regulation\s+(?:change|update|news)',
            r'tax\s+(?:news|update|change)',
            r'breaking\s+news',
            r'important\s+(?:update|news|announcement)'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in valuable_patterns)
    
    def _promotional_article_has_value(self, content: str) -> bool:
        """Check if promotional article has any valuable content"""
        valuable_patterns = [
            r'new\s+(?:product|service|feature)',
            r'product\s+(?:update|launch|announcement)',
            r'service\s+(?:update|enhancement|improvement)',
            r'security\s+(?:update|patch|fix)',
            r'important\s+(?:update|announcement|notice)',
            r'policy\s+(?:change|update)',
            r'terms\s+of\s+service\s+(?:change|update)',
            r'privacy\s+policy\s+(?:change|update)'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in valuable_patterns)
    
    def get_filtering_stats(self) -> Dict[str, any]:
        """Get comprehensive filtering statistics"""
        total_processed = self.stats["stage1_processed"]
        total_filtered = self.stats["stage1_filtered"] + self.stats["stage2_filtered"]
        
        if total_processed == 0:
            return self.stats
        
        return {
            **self.stats,
            "total_processed": total_processed,
            "total_filtered": total_filtered,
            "total_preserved": total_processed - total_filtered,
            "stage1_filter_rate": round((self.stats["stage1_filtered"] / total_processed) * 100, 1),
            "stage2_filter_rate": round((self.stats["stage2_filtered"] / max(total_processed - self.stats["stage1_filtered"], 1)) * 100, 1),
            "overall_filter_rate": round((total_filtered / total_processed) * 100, 1),
            "preservation_rate": round(((total_processed - total_filtered) / total_processed) * 100, 1)
        }

# Global instance
advanced_filter = AdvancedEmailFilter() 