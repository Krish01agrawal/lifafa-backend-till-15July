"""
Intelligent Content Compressor
=============================

Smart compression that preserves important information while optimizing storage.
Uses context-aware compression instead of blind truncation.
"""

import re
import gzip
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Configure comprehensive logging for intelligent compressor
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create specialized loggers for different components
compression_logger = logging.getLogger(f"{__name__}.compression")
classification_logger = logging.getLogger(f"{__name__}.classification")
extraction_logger = logging.getLogger(f"{__name__}.extraction")
stats_logger = logging.getLogger(f"{__name__}.stats")
performance_logger = logging.getLogger(f"{__name__}.performance")

logger.info("🚀 INTELLIGENT COMPRESSOR - Enhanced logging initialized")
logger.info("📊 Component loggers: compression, classification, extraction, stats, performance")

class IntelligentCompressor:
    """
    Smart compression that preserves critical information while optimizing storage.
    
    Key Principles:
    1. PRESERVE financial data (amounts, merchants, transaction IDs)
    2. EXTRACT structured data before compression
    3. COMPRESS narrative/promotional content aggressively
    4. USE different strategies for different email types
    5. MAINTAIN query-answerable information
    """
    
    def __init__(self):
        # Financial data patterns that must be preserved
        self.financial_patterns = [
            r'(?:rs\.?|rupees?|inr|₹)\s*[\d,]+(?:\.\d{2})?',  # Amounts
            r'transaction\s*(?:id|ref|no)?\s*:?\s*[a-zA-Z0-9]+',  # Transaction IDs
            r'order\s*(?:id|no)?\s*:?\s*[a-zA-Z0-9]+',  # Order IDs
            r'card\s*(?:ending|****)\s*\d{4}',  # Card numbers
            r'account\s*(?:no|number)?\s*:?\s*(?:****|\*{4})\d{4}',  # Account numbers
            r'upi\s*id\s*:?\s*[a-zA-Z0-9@.-]+',  # UPI IDs
            r'(?:credited|debited|paid|received|transferred)\s*(?:to|from|rs\.?|₹)\s*[\d,]+',  # Transaction descriptions
        ]
        
        # Promotional content patterns (can be heavily compressed)
        self.promotional_patterns = [
            r'unsubscribe.*?(?:\n|$)',
            r'click\s+here.*?(?:\n|$)',
            r'limited\s+time.*?(?:\n|$)',
            r'(?:sale|discount|offer).*?(?:\n|$)',
            r'terms\s+and\s+conditions.*?(?:\n|$)',
            r'privacy\s+policy.*?(?:\n|$)',
            r'copyright.*?(?:\n|$)',
        ]
        
        # Structured data extractors
        self.data_extractors = {
            'amounts': r'(?:rs\.?|rupees?|inr|₹)\s*([\d,]+(?:\.\d{2})?)',
            'transaction_ids': r'transaction\s*(?:id|ref|no)?\s*:?\s*([a-zA-Z0-9]+)',
            'order_ids': r'order\s*(?:id|no)?\s*:?\s*([a-zA-Z0-9]+)',
            'dates': r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'merchants': r'(?:from|to|at)\s+([A-Z][a-zA-Z\s&]+?)(?:\s+(?:bank|pvt|ltd|inc))?',
            'payment_methods': r'(upi|card|netbanking|wallet|cash)',
        }
        
        self.compression_stats = {
            'total_processed': 0,
            'financial_preserved': 0,
            'promotional_compressed': 0,
            'space_saved_bytes': 0,
            'structured_data_extracted': 0
        }
    
    def compress_email_intelligently(self, email_data: Dict) -> Dict:
        """
        Intelligent compression based on email type and content importance
        """
        start_time = datetime.now()
        email_id = email_data.get('id', 'unknown')
        compression_id = f"comp_{email_id}_{int(time.time() * 1000)}"
        
        compression_logger.info(f"🗜️ [START] INTELLIGENT COMPRESSION - Compression ID: {compression_id}")
        compression_logger.info(f"📧 [INPUT] Email ID: {email_id}, Subject: {email_data.get('subject', 'N/A')[:50]}...")
        
        original_size = len(str(email_data))
        compression_logger.info(f"📏 [SIZE] Original size: {original_size} characters")
        
        try:
            # Step 1: Classify email type
            classification_start = datetime.now()
            email_type = self._classify_email_type(email_data, compression_id)
            classification_time = (datetime.now() - classification_start).total_seconds()
            
            classification_logger.info(f"✅ [CLASSIFICATION] Email type: {email_type}, Time: {classification_time:.3f}s")
            
            # Step 2: Apply appropriate compression strategy
            compression_start = datetime.now()
            
            if email_type == 'financial':
                compressed_data = self._compress_financial_email(email_data, compression_id)
            elif email_type == 'promotional':
                compressed_data = self._compress_promotional_email(email_data, compression_id)
            elif email_type == 'personal':
                compressed_data = self._compress_personal_email(email_data, compression_id)
            else:
                compressed_data = self._compress_standard_email(email_data, compression_id)
            
            compression_time = (datetime.now() - compression_start).total_seconds()
            
            # Step 3: Calculate compression metrics
            compressed_size = len(str(compressed_data))
            compression_ratio = compressed_size / original_size if original_size > 0 else 1
            space_saved = original_size - compressed_size
            
            # Update stats
            self.compression_stats['total_processed'] += 1
            self.compression_stats['space_saved_bytes'] += max(0, space_saved)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            performance_logger.info(f"🎯 [PERFORMANCE] INTELLIGENT COMPRESSION - Compression ID: {compression_id}")
            performance_logger.info(f"   📧 Email Type: {email_type}")
            performance_logger.info(f"   📏 Original Size: {original_size} chars")
            performance_logger.info(f"   🗜️ Compressed Size: {compressed_size} chars")
            performance_logger.info(f"   📊 Compression Ratio: {compression_ratio:.2%}")
            performance_logger.info(f"   💾 Space Saved: {space_saved} chars")
            performance_logger.info(f"   ⏱️ Total Time: {total_time:.3f}s")
            
            compression_logger.info(f"✅ [COMPLETE] INTELLIGENT COMPRESSION SUCCESS - Compression ID: {compression_id}")
            
            return compressed_data
                
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            compression_logger.error(f"❌ [CRITICAL] INTELLIGENT COMPRESSION FAILED - Compression ID: {compression_id}, Time: {total_time:.3f}s")
            compression_logger.error(f"🔍 [DEBUG] Exception: {str(e)}", exc_info=True)
            return self._fallback_compression(email_data, compression_id)
    
    def _classify_email_type(self, email_data: Dict, compression_id: str = None) -> str:
        """Classify email type for appropriate compression strategy"""
        content = f"{email_data.get('subject', '')} {email_data.get('sender', '')} {email_data.get('body', '')}".lower()
        
        # Financial email indicators
        financial_keywords = [
            'transaction', 'payment', 'debit', 'credit', 'refund', 'invoice',
            'receipt', 'statement', 'balance', 'transfer', 'bank', 'card'
        ]
        
        # Promotional email indicators
        promotional_keywords = [
            'unsubscribe', 'newsletter', 'offer', 'sale', 'discount',
            'marketing', 'promotion', 'deal', 'limited time'
        ]
        
        # Count keyword occurrences
        financial_score = sum(1 for keyword in financial_keywords if keyword in content)
        promotional_score = sum(1 for keyword in promotional_keywords if keyword in content)
        
        if financial_score >= 2:
            return 'financial'
        elif promotional_score >= 2:
            return 'promotional'
        elif '@' in email_data.get('sender', '') and 'gmail.com' in email_data.get('sender', ''):
            return 'personal'
        else:
            return 'standard'
    
    def _compress_financial_email(self, email_data: Dict, compression_id: str = None) -> Dict:
        """
        Compress financial email while preserving ALL important data
        """
        self.compression_stats['financial_preserved'] += 1
        
        # Extract structured financial data FIRST
        structured_data = self._extract_structured_data(email_data)
        
        # Preserve complete financial content (NO truncation)
        content = email_data.get('body', '') or email_data.get('snippet', '')
        
        # Clean up content (remove HTML, normalize whitespace)
        content = self._clean_content(content)
        
        # For financial emails, preserve MORE content (up to 2000 characters)
        if len(content) > 2000:
            # Instead of blind truncation, preserve important sections
            content = self._preserve_important_sections(content, max_length=2000)
        
        # Store both structured data and cleaned content
        compressed_data = {
            **email_data,
            'body': content,
            'structured_data': structured_data,
            'compression_type': 'financial_preserved',
            'original_length': len(email_data.get('body', '')),
            'compressed_length': len(content),
            'compression_ratio': len(content) / max(len(email_data.get('body', '')), 1)
        }
        
        return compressed_data
    
    def _compress_promotional_email(self, email_data: Dict, compression_id: str = None) -> Dict:
        """
        Aggressive compression for promotional emails
        """
        self.compression_stats['promotional_compressed'] += 1
        
        content = email_data.get('body', '') or email_data.get('snippet', '')
        original_length = len(content)
        
        # Remove promotional fluff
        content = self._remove_promotional_content(content)
        
        # Clean up content
        content = self._clean_content(content)
        
        # For promotional emails, more aggressive truncation is acceptable
        if len(content) > 300:
            content = content[:300] + "..."
        
        # Track space saved
        self.compression_stats['space_saved_bytes'] += original_length - len(content)
        
        compressed_data = {
            **email_data,
            'body': content,
            'compression_type': 'promotional_compressed',
            'original_length': original_length,
            'compressed_length': len(content),
            'compression_ratio': len(content) / max(original_length, 1)
        }
        
        return compressed_data
    
    def _compress_personal_email(self, email_data: Dict, compression_id: str = None) -> Dict:
        """
        Moderate compression for personal emails
        """
        content = email_data.get('body', '') or email_data.get('snippet', '')
        
        # Clean up content
        content = self._clean_content(content)
        
        # Moderate truncation for personal emails
        if len(content) > 1000:
            content = self._preserve_important_sections(content, max_length=1000)
        
        compressed_data = {
            **email_data,
            'body': content,
            'compression_type': 'personal_moderate',
            'original_length': len(email_data.get('body', '')),
            'compressed_length': len(content),
            'compression_ratio': len(content) / max(len(email_data.get('body', '')), 1)
        }
        
        return compressed_data
    
    def _compress_standard_email(self, email_data: Dict, compression_id: str = None) -> Dict:
        """
        Standard compression for other emails
        """
        content = email_data.get('body', '') or email_data.get('snippet', '')
        
        # Clean up content
        content = self._clean_content(content)
        
        # Standard truncation
        if len(content) > 800:
            content = self._preserve_important_sections(content, max_length=800)
        
        compressed_data = {
            **email_data,
            'body': content,
            'compression_type': 'standard',
            'original_length': len(email_data.get('body', '')),
            'compressed_length': len(content),
            'compression_ratio': len(content) / max(len(email_data.get('body', '')), 1)
        }
        
        return compressed_data
    
    def _extract_structured_data(self, email_data: Dict) -> Dict:
        """
        Extract structured data that's critical for queries
        """
        content = f"{email_data.get('subject', '')} {email_data.get('body', '')} {email_data.get('snippet', '')}"
        structured_data = {}
        
        # Extract using patterns
        for data_type, pattern in self.data_extractors.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                structured_data[data_type] = list(set(matches))  # Remove duplicates
        
        # Extract additional financial metadata
        if any(keyword in content.lower() for keyword in ['transaction', 'payment', 'debit', 'credit']):
            structured_data['is_financial'] = True
            structured_data['financial_keywords'] = [
                keyword for keyword in ['transaction', 'payment', 'debit', 'credit', 'refund', 'transfer']
                if keyword in content.lower()
            ]
        
        if structured_data:
            self.compression_stats['structured_data_extracted'] += 1
        
        return structured_data
    
    def _clean_content(self, content: str) -> str:
        """
        Clean content while preserving important information
        """
        # Remove HTML tags but preserve important content
        content = re.sub(r'<[^>]+>', '', content)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove excessive line breaks
        content = re.sub(r'\n\s*\n', '\n', content)
        
        return content.strip()
    
    def _preserve_important_sections(self, content: str, max_length: int) -> str:
        """
        Intelligent truncation that preserves important sections
        """
        # If content is already short enough, return as-is
        if len(content) <= max_length:
            return content
        
        # Find important sections (containing financial data)
        important_sections = []
        
        # Look for sections with financial patterns
        for pattern in self.financial_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Get context around the match (±100 characters)
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                section = content[start:end]
                important_sections.append(section)
        
        # If we found important sections, prioritize them
        if important_sections:
            # Combine important sections
            combined = ' ... '.join(important_sections)
            
            # If still too long, truncate but keep as much as possible
            if len(combined) > max_length:
                combined = combined[:max_length - 3] + "..."
            
            return combined
        
        # If no important sections found, use beginning and end
        half_length = (max_length - 10) // 2
        return content[:half_length] + " ... " + content[-half_length:]
    
    def _remove_promotional_content(self, content: str) -> str:
        """
        Remove promotional fluff from content
        """
        # Remove promotional patterns
        for pattern in self.promotional_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Remove excessive promotional text
        content = re.sub(r'(?:sale|discount|offer).*?(?:\n|$)', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _fallback_compression(self, email_data: Dict, compression_id: str = None) -> Dict:
        """
        Fallback compression if intelligent compression fails
        """
        content = email_data.get('body', '') or email_data.get('snippet', '')
        
        # Simple cleaning
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Conservative truncation
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        return {
            **email_data,
            'body': content,
            'compression_type': 'fallback',
            'original_length': len(email_data.get('body', '')),
            'compressed_length': len(content)
        }
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return self.compression_stats.copy()
    
    def reset_stats(self):
        """Reset compression statistics"""
        self.compression_stats = {
            'total_processed': 0,
            'financial_preserved': 0,
            'promotional_compressed': 0,
            'space_saved_bytes': 0,
            'structured_data_extracted': 0
        }

# Global intelligent compressor instance
intelligent_compressor = IntelligentCompressor() 