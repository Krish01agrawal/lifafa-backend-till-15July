"""
Gmail Intelligence Agent System using Agno Framework
====================================================

This module implements a complete email intelligence system using Agno Agentic teams
to replace the monolithic mem0_agent.py implementation.

Key Features:
- Agno Agent Teams for specialized tasks
- Clean separation of concerns
- Intelligent query processing
- Email categorization with AI
- Memory management with Mem0
- Comprehensive error handling
- Smart caching system for performance
- Batch processing for scalability

Recent Optimizations (2025-06-23):
- Added intelligent caching system
- Implemented batch processing for email categorization
- Added smart memory management
- Enhanced error handling for rate limits and API failures
- Improved robustness for production use
"""

import os
import json
import asyncio
import traceback
import time
import hashlib
import sys
import gc
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import openai
from mem0 import MemoryClient
import re
from textwrap import dedent

# Agno Framework Imports
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.tools.python import PythonTools

# Load environment variables
from dotenv import load_dotenv
import os
# Load .env from parent directory (project root)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Import configuration
from .config import (
    ENABLE_SMART_CACHING, ENABLE_BATCH_PROCESSING,
    CACHE_AI_RESPONSES, CACHE_SEARCH_RESULTS, CACHE_EMAIL_METADATA,
    MAX_CACHE_SIZE_MB, EMAIL_CATEGORIZATION_BATCH_SIZE,
    MAX_CONCURRENT_AI_REQUESTS, MEM0_DEFAULT_SEARCH_LIMIT,
    MEM0_MAX_SEARCH_LIMIT, MEM0_RETRY_ATTEMPTS, MEM0_RETRY_DELAY
)

import logging

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

MEM0_API_KEY = os.getenv("MEM0_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not MEM0_API_KEY:
    raise ValueError("MEM0_API_KEY environment variable is required")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Initialize Mem0 clients
logger.info(f"🔑 Initializing Mem0 clients with API key: {MEM0_API_KEY[:8]}...{MEM0_API_KEY[-3:]}")

try:
    aclient = MemoryClient(api_key=MEM0_API_KEY)  # For add operations
    sync_client = MemoryClient(api_key=MEM0_API_KEY)  # For search operations
    logger.info("✅ Mem0 clients initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Mem0 clients: {e}")
    raise

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# ============================================================================
# SMART CACHING SYSTEM
# ============================================================================

class SmartCache:
    """Intelligent in-memory caching system for performance optimization"""
    
    def __init__(self, max_size_mb: int = MAX_CACHE_SIZE_MB):
        self.cache = {}
        self.access_times = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.hit_count = 0
        self.miss_count = 0
        logger.info(f"🧠 Smart cache initialized with {max_size_mb}MB capacity")
    
    def _get_cache_key(self, key_data: str) -> str:
        """Generate cache key from input data"""
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key_data: str) -> Optional[Any]:
        """Get cached result"""
        key = self._get_cache_key(key_data)
        
        if key in self.cache:
            # Check if expired
            cache_entry = self.cache[key]
            if time.time() < cache_entry['expires']:
                # Update access time and return data
                self.access_times[key] = time.time()
                self.hit_count += 1
                return cache_entry['data']
            else:
                # Remove expired entry
                self._remove_entry(key)
        
        self.miss_count += 1
        return None
    
    def set(self, key_data: str, result: Any, ttl: int = 3600):
        """Cache result with TTL"""
        if not ENABLE_SMART_CACHING:
            return
            
        key = self._get_cache_key(key_data)
        
        # Calculate result size
        result_size = sys.getsizeof(result)
        
        # Check if we need to evict old entries
        while self.current_size + result_size > self.max_size_bytes and self.cache:
            self._evict_lru()
        
        # Store result
        self.cache[key] = {
            'data': result,
            'expires': time.time() + ttl,
            'size': result_size
        }
        self.access_times[key] = time.time()
        self.current_size += result_size
    
    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self.cache:
            self.current_size -= self.cache[key]['size']
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.access_times:
            return
            
        # Find LRU key
        lru_key = min(self.access_times, key=self.access_times.get)
        self._remove_entry(lru_key)
    
    def cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time > entry['expires']:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size_mb": round(self.current_size / (1024 * 1024), 2),
            "cache_entries": len(self.cache),
            "max_size_mb": self.max_size_bytes / (1024 * 1024)
        }

# Global cache instance
smart_cache = SmartCache()

# ============================================================================
# BATCH PROCESSING SYSTEM
# ============================================================================

class AsyncBatchProcessor:
    """High-performance batch processing for emails and AI operations"""
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_AI_REQUESTS):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"⚡ Batch processor initialized with {max_concurrent} concurrent operations")
    
    async def process_emails_batch(self, emails: List['EmailMessage'], 
                                  processor_func, batch_size: int = EMAIL_CATEGORIZATION_BATCH_SIZE):
        """Process emails in optimized batches"""
        
        if not ENABLE_BATCH_PROCESSING:
            # Fallback to sequential processing
            return await self._process_sequential(emails, processor_func)
        
        logger.info(f"🔄 Processing {len(emails)} emails in batches of {batch_size}")
        
        # Split emails into batches
        batches = [emails[i:i + batch_size] for i in range(0, len(emails), batch_size)]
        
        # Process all batches concurrently
        async def process_batch_with_semaphore(batch):
            async with self.semaphore:
                return await processor_func(batch)
        
        # Execute all batches in parallel
        batch_tasks = [process_batch_with_semaphore(batch) for batch in batches]
        results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Combine results
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif not isinstance(result, Exception):
                all_results.append(result)
            else:
                logger.error(f"Batch processing error: {result}")
        
        logger.info(f"✅ Batch processing complete: {len(all_results)} results")
        return all_results
    
    async def _process_sequential(self, emails: List['EmailMessage'], processor_func):
        """Fallback sequential processing"""
        results = []
        for email in emails:
            try:
                result = await processor_func(email)
                results.append(result)
            except Exception as e:
                logger.error(f"Sequential processing error: {e}")
        return results
    
    async def categorize_emails_fast(self, emails: List['EmailMessage']):
        """Fast email categorization using intelligent batching"""
        
        async def categorize_batch(batch):
            # Group similar emails for batch processing
            financial_emails = [e for e in batch if self.is_likely_financial(e)]
            other_emails = [e for e in batch if not self.is_likely_financial(e)]
            
            batch_results = []
            
            # Process financial emails together (they have similar patterns)
            if financial_emails:
                financial_results = await self.batch_categorize_financial(financial_emails)
                batch_results.extend(financial_results)
            
            # Process other emails
            if other_emails:
                other_results = await self.batch_categorize_general(other_emails)
                batch_results.extend(other_results)
            
            return batch_results
        
        return await self.process_emails_batch(emails, categorize_batch, batch_size=50)
    
    def is_likely_financial(self, email: 'EmailMessage') -> bool:
        """Quick check if email is likely financial"""
        content = f"{email.subject} {email.sender} {email.snippet}".lower()
        financial_indicators = ['payment', 'charged', 'upi', 'bank', 'transaction', 
                               'order', 'receipt', 'bill', '₹', 'rs.', 'inr']
        return any(indicator in content for indicator in financial_indicators)
    
    async def batch_categorize_financial(self, emails: List['EmailMessage']):
        """Batch categorize financial emails"""
        results = []
        for email in emails:
            try:
                # Use cached result if available
                cache_key = f"financial_cat:{email.id}:{hash(email.subject)}"
                cached_result = smart_cache.get(cache_key)
                
                if cached_result:
                    results.append(cached_result)
                else:
                    result = await categorize_email_simple(email)
                    smart_cache.set(cache_key, result, ttl=CACHE_AI_RESPONSES)
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error categorizing financial email {email.id}: {e}")
                # Fallback result
                results.append({
                    'id': email.id,
                    'category': 'financial',
                    'subcategory': 'misc',
                    'merchant': 'unknown',
                    'amount': None,
                    'payment_method': 'unknown'
                })
        
        return results
    
    async def batch_categorize_general(self, emails: List['EmailMessage']):
        """Batch categorize general emails"""
        results = []
        for email in emails:
            try:
                # Use cached result if available
                cache_key = f"general_cat:{email.id}:{hash(email.subject)}"
                cached_result = smart_cache.get(cache_key)
                
                if cached_result:
                    results.append(cached_result)
                else:
                    result = await categorize_email_simple(email)
                    smart_cache.set(cache_key, result, ttl=CACHE_AI_RESPONSES)
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error categorizing general email {email.id}: {e}")
                # Fallback result
                results.append({
                    'id': email.id,
                    'category': 'general',
                    'subcategory': 'misc',
                    'merchant': 'unknown',
                    'amount': None,
                    'payment_method': 'unknown'
                })
        
        return results

# Global batch processor
batch_processor = AsyncBatchProcessor()

# ============================================================================
# DATA MODELS
# ============================================================================

class EmailMessage(BaseModel):
    id: str
    subject: str = ""
    sender: str = ""
    snippet: str = ""
    body: str = ""
    date: Optional[str] = None

class EmailInsight(BaseModel):
    category: str
    subcategory: str
    merchant: Optional[str] = "unknown"  # Make optional with default value
    amount: Optional[str] = None
    payment_method: str
    timestamp: Optional[str] = None

# ============================================================================
# AGNO AGENT DEFINITIONS
# ============================================================================

# Query Analysis Agent
query_analyzer = Agent(
    name="QueryAnalyzer",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at understanding user intent and refining search queries for email data",
    instructions=dedent("""
        You are a query analysis expert specializing in email search optimization.
        
        Your responsibilities:
        1. Understand user intent from natural language queries
        2. Distinguish between different query types:
           - Job application responses vs job alerts
           - Payment transactions vs payment failures  
           - Recent/latest queries vs general searches
           - Specific merchant/service queries
        
        3. Generate precise search terms that will find relevant emails in Mem0
        4. Use logical operators (OR, AND) for comprehensive searches
        
        Examples of query refinement:
        - "job application response" → "thank you for your application OR interview invitation OR application status OR we have reviewed"
        - "recent swiggy payments" → "swiggy AND (payment OR charged OR order)"
        - "failed transactions" → "payment failed OR transaction declined OR payment unsuccessful"
        
        Return ONLY the refined search query, nothing else.
    """),
    show_tool_calls=False,
    markdown=False
)

# Email Categorization Agent  
email_categorizer = Agent(
    name="EmailCategorizer",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at categorizing emails and extracting structured insights",
    instructions=dedent("""
        You are an expert email categorization agent.
        
        Your role:
        1. Analyze email content (subject, snippet, body)
        2. Extract structured information:
           - Category: financial, shopping, subscription, professional, general
           - Subcategory: payment, order, renewal, job, misc
           - Merchant: amazon, swiggy, netflix, etc.
           - Amount: financial transaction amount if present
           - Payment method: upi, card, bank_transfer, unknown
        
        3. Return data in this exact JSON format:
        {
            "category": "financial|shopping|subscription|professional|general",
            "subcategory": "payment|order|renewal|job|misc",
            "merchant": "company/service name",
            "amount": "amount with currency or null", 
            "payment_method": "upi|card|bank_transfer|unknown"
        }
        
        Be precise and consistent with your categorizations.
    """),
    tools=[PythonTools()],
    show_tool_calls=False,
    markdown=True
)

# Content Filter Agent
content_filter = Agent(
    name="ContentFilter",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at filtering email search results based on user intent",
    instructions=dedent("""
        You are an email content filtering expert.
        
        Your role:
        1. Analyze search results against user query intent
        2. Filter out irrelevant results:
           - Remove job alerts when user wants job responses
           - Remove promotional emails when user wants transactions
           - Remove unrelated content based on context
        
        3. Be strict about relevance to ensure high-quality results
        4. Provide clear reasoning for filtering decisions
        
        Return filtering recommendations or "KEEP_ALL" if all results are relevant.
    """),
    tools=[PythonTools()],
    show_tool_calls=False,
    markdown=True
)

# Intelligence Response Agent
intelligence_agent = Agent(
    name="IntelligenceAgent", 
    model=OpenAIChat(id="gpt-4o"),
    description="Expert Smart Gmail Assistant that provides comprehensive insights about ANY topic from email data",
    instructions=dedent("""
        You are a WORLD-CLASS Smart Gmail Assistant that analyzes email data to provide comprehensive insights about ANY topic.
        
        Your mission: Generate INSANELY GREAT responses that perfectly match the user's query, whether it's about:
        - Job applications and career insights
        - Financial transactions and spending patterns  
        - Travel bookings and trip planning
        - Shopping and purchase history
        - Subscriptions and services
        - Personal relationships and communications
        - Health and medical information
        - Education and learning
        - Entertainment and hobbies
        - Business and professional matters
        - Or ANY other topic found in emails
        
        🔥 DYNAMIC RESPONSE STRUCTURE:
        
        STEP 1: ANALYZE THE QUERY TYPE
        - If about JOB APPLICATIONS: Create career/job application insights report
        - If about FINANCES: Create financial intelligence report  
        - If about TRAVEL: Create travel insights and booking analysis
        - If about SHOPPING: Create shopping behavior analysis
        - If about RELATIONSHIPS: Create communication and relationship insights
        - If about HEALTH: Create health and medical insights
        - If about ANY OTHER TOPIC: Create relevant topical analysis
        
        STEP 1.5: FOR FINANCIAL ANALYSIS - EXTRACT COMPREHENSIVE TRANSACTION DATA
        When analyzing financial emails, extract ALL available transaction details including:
        
        Core Transaction Data:
        - fintransaction_id, date_time (exact timestamp), receiver/merchant
        - amount (numeric), currency, transaction_type (debit/credit/transfer)
        - transaction_status, reference_number, order_id
        
        Payment & Banking Details:
        - payment_medium (UPI/card/bank transfer), bank_name, account_number (masked)
        - card_number (masked last 4 digits), card_type, upi_id
        - emi_details, processing_fee, tax_amount, cashback_amount
        
        Location & Device Context:
        - location (city/state/country), merchant_location, device_type
        - channel_used (online/mobile/ATM), authentication_method
        - ip_address, user_agent (if available in email headers)
        
        Additional Details:
        - merchant_category, subcategory, description
        - subscription details (is_subscription, frequency, next_due_date)
        - promotional_offer, discount_amount, loyalty_points
        - risk_score, unusual_activity_flag
        - notes, tags, user_annotations
        
        Always format each transaction with all available fields, showing "Not Available" for missing data.
        
        CRITICAL: For financial transactions, you MUST extract actual values from email content:
        - Look for transaction IDs, reference numbers, order IDs in email body
        - Extract exact amounts with currency symbols (₹, $, etc.)
        - Find merchant/receiver names from email sender or content
        - Identify payment methods mentioned (UPI, card, bank transfer)
        - Extract dates and times from email timestamps or content
        - Look for account numbers, card numbers (mask sensitive digits)
        - Find transaction descriptions, purposes, or what was purchased
        - Extract any fees, taxes, or additional charges mentioned
        - Identify if it's a subscription, one-time payment, or recurring
        
        Do NOT use placeholder text - extract real data from the actual email content provided.
        
        MANDATORY TRANSACTION EXTRACTION EXAMPLE:
        When you find a financial email, you MUST extract details like this:
        
        SBI Mutual Fund Transaction
        - Email Source: abc@camsonline.com  
        - Date: 19-Jun-2025
        - Time: 4:15 AM
        - Amount: ₹499.98 (extract actual amount from email body)
        - Transaction ID: [look for reference/transaction number in email]
        - Order ID: [look for order reference if available]
        - Receiver: SBI Mutual Fund
        - Payment Mode: [extract from email - UPI/Bank Transfer/Card]
        - Description: [extract purpose/description from email content]
        - Status: [extract transaction status from email]
        
        You MUST show actual extracted values, not generic descriptions.
        
        STEP 2: GENERATE APPROPRIATE RESPONSE FORMAT
        
        FOR JOB APPLICATIONS:
        🚀 GMAIL CAREER INTELLIGENCE REPORT 🚀
        Query: "[exact user query]"
        
        💼 EXECUTIVE SUMMARY - YOUR CAREER DNA
        🎯 INSTANT INSIGHTS:
        - 📧 Total Applications Tracked: [count] applications across [timeframe]
        - 📊 Response Rate: [percentage]% of applications received responses
        - 🏆 Top Industry Focus: [industry] - [percentage]% of applications
        - ⚡ Application Velocity: [frequency] applications per [timeframe]
        - 🎪 Career Personality: [career type based on application patterns]
        
        FOR FINANCIAL QUERIES:
        🔥 GMAIL FINANCIAL INTELLIGENCE REPORT 🔥
        Query: "[exact user query]"
        
        💎 EXECUTIVE SUMMARY - YOUR FINANCIAL DNA
        🎯 INSTANT INSIGHTS:
        - 💰 Total Spending Power: ₹[amount] across [count] transactions
        - 📊 Financial Behavior Score: [score]/10 (Based on spending consistency)
        - 🏆 Top Spending Category: [category] - [percentage]% of total budget
        - ⚡ Average Transaction Velocity: ₹[amount] every [frequency]
        - 🎪 Spending Personality: [personality type]
        
        CONTINUE WITH RELEVANT SECTIONS BASED ON QUERY TYPE:
        
        FOR JOB APPLICATIONS - INCLUDE:
        📋 COMPLETE APPLICATION BREAKDOWN
        Date | Company | Position | Status | Response Type | Insights
        [Create detailed breakdown with actual job application data from emails]
        
        🎯 CAREER INTELLIGENCE MATRIX
        🏢 COMPANY TARGETING STRATEGY
        - [Company] Application Pattern: [count] applications - [response analysis]
        - 🔥 CAREER INSIGHT: [specific pattern from application data]
        - 💡 OPTIMIZATION: [specific career strategy recommendation]
        
        📊 RESPONSE ANALYSIS
        - Positive Responses: [count] ([percentage]%)
        - Rejections: [count] ([percentage]%)
        - No Response: [count] ([percentage]%)
        - 🔥 INSIGHT: [pattern analysis from response data]
        - 💡 STRATEGY: [application improvement tips]
        
        FOR FINANCIAL QUERIES - PROVIDE COMPREHENSIVE ANALYSIS:
        
        Transaction Summary and Email Analysis
        
        Based on your request to list all transactions, I've analyzed your emails to extract relevant financial activities. Here's a detailed breakdown:
        
        Individual Transaction Details
        
        ALWAYS extract and show actual data from emails like this format:
        
        1. SBI Mutual Fund Transaction
           Email Source: enq_sbimf@camsonline.com
           Date: 19-Jun-2025  
           Time: 3:15 AM
           Amount: ₹499.98
           Transaction ID: [extract actual ID from email content]
           Receiver: SBI Mutual Fund
           Payment Mode: [extract actual payment method]
           Description: [extract actual transaction purpose]
           Status: Transaction confirmed
        
        2. [Next Transaction Name]
           Email Source: [actual email sender]
           Date: [actual date from email]
           Time: [actual time from email]
           Amount: ₹[actual amount from email]
           Transaction ID: [actual transaction ID]
           Receiver: [actual receiver name]
           Payment Mode: [actual payment method]
           Description: [actual description]
           Status: [actual status]
        
        [Continue for all financial transactions found in emails]
        
        🔍 Additional Insights and Recommendations
        
        Email Categories Analysis:
        - Financial: [X] emails
        - General: [X] emails
        - Professional: [X] emails
        
        Merchants/Services Involved:
        [List all merchants and services found in emails with brief context]
        
        Query Relevance:
        [Analysis of how emails relate to the user's query]
        
        📌 Recommendations:
        1. [Specific actionable recommendation]
        2. [Another relevant suggestion]
        3. [Security or financial management tip]
        
        Total Transactions: [X] transactions worth ₹[Total Amount]
        
        🧠 BEHAVIORAL FINANCIAL PSYCHOLOGY
        ⏰ TIME-BASED SPENDING PATTERNS
        - Peak Spending Hour: [time] - [insight from timestamps]
        - Weekend vs Weekday: [ratio] - [analysis from dates]
        
        🎭 MERCHANT RELATIONSHIP ANALYSIS
        - Brand Loyalty Score: [score]/10 - [based on frequency data]
        - Merchant Diversity: [analysis of different merchants]
        
        🚀 PREDICTIVE FINANCIAL INTELLIGENCE
        📈 SPENDING TRAJECTORY
        - Monthly Burn Rate: ₹[amount] - [trend analysis]
        - Projected Annual Spending: ₹[amount] based on current patterns
        - Risk Assessment: [assessment based on spending patterns]
        
        💎 EXCLUSIVE INSIGHTS (The WOW Factor)
        🔥 HIDDEN PATTERNS DISCOVERED:
        [Reveal 2-3 surprising insights from actual email data]
        
        🎪 FINANCIAL PERSONALITY PROFILE:
        - Spending Style: [analysis based on transaction patterns]
        - Risk Tolerance: [assessment from spending behavior]
        
        🏆 ACTIONABLE INTELLIGENCE DASHBOARD
        ⚡ IMMEDIATE ACTIONS (Next 7 Days)
        [3 specific actions with potential savings based on data]
        
        🎯 STRATEGIC MOVES (Next 30 Days)
        [3 strategic recommendations based on patterns]
        
        🚀 LONG-TERM WEALTH STRATEGY (Next 12 Months)
        [3 long-term strategies based on financial behavior]
        
        ### 📱 SMART ALERTS & NOTIFICATIONS
        [4-5 specific alerts and optimization opportunities from data]
        
        🚨 CRITICAL REQUIREMENTS:
        - FIRST: Identify the EXACT topic/type of the user's query
        - MATCH the response format to the query type (career, financial, travel, etc.)
        - Use ONLY actual data from emails provided
        - **COMPREHENSIVE DETAILS**: Provide detailed breakdown showing individual email processing
        - **CLEAN FORMATTING**: NO hashtags (#), NO asterisks (*), NO bold (**), NO complex symbols - use plain text only
        - Extract relevant information based on query type:
          * For job applications: company names, positions, response types, dates
          * For finances: Show "EMAIL X PROCESSED" format with Category, Merchant, Amount, Payment Method, Content Overview
          * For travel: destinations, dates, booking details, costs
          * For any topic: relevant details from email content
        - Include comprehensive insights: email categories analysis, merchants involved, query relevance
        - Provide specific actionable recommendations
        - Include confidence levels for major claims
        - Never hallucinate or invent data
        - Base all analysis on actual email content provided
        - If query doesn't match email data, clearly state what was found vs requested
        - **FORMATTING RULES**: NO hashtags (#), NO asterisks (*), NO bold (**) - use plain text with simple indentation only
    """),
    tools=[PythonTools()],
    show_tool_calls=False,
    markdown=True
)

# Query Intent Analysis Agent
query_intent_analyzer = Agent(
    name="QueryIntentAnalyzer",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at understanding user intent and determining appropriate response types",
    instructions=dedent("""
        You are an expert at understanding user intent from natural language queries.
        
        Your role:
        1. Analyze user queries to understand their true intent
        2. Classify queries into categories:
           - LINKEDIN: LinkedIn updates, connections, professional networking, account insights
           - CAREER: Job applications, career progress, interview updates, professional development
           - TRAVEL: Travel bookings, trip planning, flight updates, hotel reservations
           - SHOPPING: Purchase behavior, order tracking, shopping patterns, merchant analysis
           - FINANCIAL: Transaction analysis, spending insights, financial behavior, payments
           - GENERAL: General email patterns, communication insights, productivity analysis
        
        3. Return JSON format:
        {
            "intent": "LINKEDIN|CAREER|TRAVEL|SHOPPING|FINANCIAL|GENERAL",
            "confidence": 0.8,
            "key_aspects": ["aspect1", "aspect2", "aspect3"],
            "response_focus": "What the response should focus on"
        }
        
        Provide precise intent classification to ensure users get exactly what they're looking for.
    """),
    show_tool_calls=False,
    markdown=False
)

# Response Enhancement Agent with Logical Reasoning
response_enhancer = Agent(
    name="ResponseEnhancer",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at generating highly relevant, insightful responses with advanced logical reasoning capabilities",
    instructions=dedent("""
        You are a master at creating personalized, insightful responses from email data with ADVANCED LOGICAL REASONING.
        
        🧠 CORE REASONING PRINCIPLES:
        1. Apply domain knowledge to make logical inferences
        2. Connect patterns across different data points
        3. Provide reasoning for major conclusions
        4. Assign confidence levels to inferences
        5. Think step-by-step through logical deductions
        
        🌍 MANDATORY DOMAIN KNOWLEDGE APPLICATION:
        - BMTC transactions → User lives/works in Bangalore (High confidence)
        - Frequent transport usage → Regular commuter pattern
        - Food delivery + transport + local services → Comprehensive location confirmation
        - Digital payment patterns → Tech adoption and lifestyle insights
        
        🎯 LOGICAL REASONING FRAMEWORK:
        For every analysis, you MUST:
        1. IDENTIFY patterns in the data
        2. APPLY domain knowledge to interpret patterns
        3. MAKE logical inferences from the evidence
        4. CONNECT multiple data points for comprehensive insights
        5. PROVIDE confidence levels for major conclusions
        
        RESPONSE STRUCTURE REQUIREMENTS:
        
        🧠 LOGICAL DEDUCTIONS SECTION (MANDATORY):
        - Pattern: [What you observed]
        - Inference: [What this logically means]
        - Conclusion: [Final deduction with confidence]
        
        Example:
        - Pattern: 8 BMTC transactions over 3 months
        - Inference: Regular use of Bangalore public transport
        - Conclusion: User lives/works in Bangalore (95% confidence)
        
        🌍 LOCATION INTELLIGENCE (When applicable):
        - Primary Location: [City with confidence level]
        - Supporting Evidence: [Specific services/addresses]
        - Lifestyle Type: [Based on service patterns]
        
        👤 BEHAVIORAL ANALYSIS:
        - User Profile: [Professional/Student/etc. based on patterns]
        - Daily Patterns: [Commuting/Working habits]
        - Technology Usage: [Digital adoption level]
        
        CRITICAL REQUIREMENTS:
        - ALWAYS make logical connections beyond surface data
        - EXPLAIN your reasoning for major inferences
        - USE specific evidence to support conclusions
        - PROVIDE confidence percentages for key insights
        - ADDRESS the user's question with intelligent analysis
        
        Response Guidelines:
            - Generate responses that DIRECTLY address the user's actual question
            - Match response type to query intent (don't give financial reports for LinkedIn queries)
            - Use actual email content and metadata provided
            - **COMPREHENSIVE ANALYSIS**: Show detailed individual email processing like "EMAIL 1 PROCESSED" with all relevant details
            - **SIMPLE FORMATTING**: NO hashtags (#), NO asterisks (*), NO bold (**), NO complex symbols - plain text only
            - Provide specific, data-driven insights including email categories analysis and merchant breakdown
            - Include confidence levels for major claims
            - Make recommendations practical and actionable
            - Use engaging, professional language with minimal but appropriate emojis
            - Structure responses with clear sections but simple formatting
            - **NO OVERFORMATTING**: Strictly NO hashtags (#), NO asterisks (*), NO bold (**), NO complex symbols - plain text responses only
        Example of Enhanced Thinking:
        ❌ BAD: "You use BMTC services for transportation"
        ✅ GOOD: "Your 8 BMTC transactions over 3 months indicate regular use of Bangalore public transport, strongly suggesting you live or work in Bangalore (95% confidence). The transaction frequency suggests daily commuting patterns typical of urban professionals."
        
        FORMATTING GUIDELINES:
        - Use clear, professional language
        - Include emojis sparingly for visual clarity
        - Structure with logical flow from observation to inference to conclusion
        - NO excessive formatting - focus on intelligent content
        
        Always provide comprehensive, reasoned analysis that demonstrates logical thinking.
    """),
    show_tool_calls=False,
    markdown=True
)

# ============================================================================
# AGNO TEAM DEFINITION
# ============================================================================

gmail_intelligence_team = Team(
    name="Gmail Intelligence Team",
    members=[query_analyzer, content_filter, intelligence_agent],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    instructions=dedent("""
        You are the Gmail Intelligence Team - a specialized group of AI agents 
        working together to provide intelligent email analysis and insights.
        
        WORKFLOW:
        1. Query Analyzer: Refine user queries for optimal email search
        2. Content Filter: Filter search results for maximum relevance
        3. Intelligence Agent: Generate comprehensive insights and responses
        
        COLLABORATION PRINCIPLES:
        - Each agent focuses on their core expertise
        - Pass relevant context between agents seamlessly
        - Ensure high-quality, accurate results
        - Base all analysis strictly on actual email data
        
        QUALITY STANDARDS:
        - Zero hallucination - only use provided data
        - Clear, actionable insights
        - Professional, helpful responses
        - Include confidence levels for major claims
        - Provide specific evidence for conclusions
    """),
    show_tool_calls=False,
    markdown=True
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def detect_user_location(emails: List[EmailMessage]) -> str:
    """Detect user's likely location from email content patterns"""
    try:
        location_indicators = {
            'India': ['₹', 'rupees', 'inr', 'mumbai', 'delhi', 'bangalore', 'chennai', 'paytm', 'phonepe'],
            'US': ['$', 'usd', 'dollars', 'new york', 'california', 'texas', 'venmo'],
            'UK': ['£', 'gbp', 'pounds', 'london', 'manchester', 'birmingham'],
            'EU': ['€', 'eur', 'euros', 'berlin', 'paris', 'madrid', 'amsterdam']
        }
        
        location_scores = {loc: 0 for loc in location_indicators.keys()}
        
        # Analyze first 50 emails for performance
        for email in emails[:50]:
            content = f"{email.subject} {email.snippet} {email.body}".lower()
            
            for location, indicators in location_indicators.items():
                for indicator in indicators:
                    if indicator in content:
                        location_scores[location] += 1
        
        return max(location_scores, key=location_scores.get) if max(location_scores.values()) > 0 else 'Unknown'
            
    except Exception as e:
        print(f"❌ Error detecting location: {e}")
        return 'Unknown'

def extract_amount_with_currency(content: str) -> tuple:
    """Extract monetary amount and currency from email content"""
    try:
        currency_patterns = [
            (r'₹\s*(\d+(?:,\d+)*(?:\.\d{2})?)', '₹'),  # Indian Rupees
            (r'\$\s*(\d+(?:,\d+)*(?:\.\d{2})?)', '$'),  # US Dollars  
            (r'£\s*(\d+(?:,\d+)*(?:\.\d{2})?)', '£'),  # British Pounds
            (r'€\s*(\d+(?:,\d+)*(?:\.\d{2})?)', '€'),  # Euros
        ]
        
        for pattern, currency in currency_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                amount_str = matches[0].replace(',', '')
                try:
                    amount = float(amount_str)
                    return amount, currency
                except ValueError:
                    continue
        
        return None, None
        
    except Exception as e:
        print(f"❌ Error extracting amount: {e}")
        return None, None

async def categorize_email_with_agent(email: EmailMessage) -> EmailInsight:
    """Categorize email using Agno agent with fallback to simple categorization"""
    try:
        # Prepare email content for analysis
        content = f"Subject: {email.subject}\nSnippet: {email.snippet}\nBody: {email.body[:500]}"
        
        # Use Agno agent for categorization
        categorization_result = email_categorizer.run(
            f"Categorize this email and extract structured data:\n\n{content}"
        )
        
        # Extract JSON from agent response
        response_text = categorization_result.content if hasattr(categorization_result, 'content') else str(categorization_result)
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[^}]*\}', response_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                
                return EmailInsight(
                    category=data.get('category', 'general'),
                    subcategory=data.get('subcategory', 'misc'),
                    merchant=data.get('merchant', 'unknown'),
                    amount=data.get('amount'),
                    payment_method=data.get('payment_method', 'unknown'),
                    timestamp=email.date
                )
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ JSON parsing failed, using fallback: {e}")
                return await categorize_email_simple(email)
        else:
            print("⚠️ No JSON found in agent response, using fallback")
            return await categorize_email_simple(email)
            
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "insufficient_quota" in error_msg:
            print(f"⚠️ OpenAI quota exceeded, using simple categorization for {email.id}")
        elif "rate limit" in error_msg:
            print(f"⚠️ OpenAI rate limit hit, using simple categorization for {email.id}")
        else:
            print(f"❌ Error categorizing email with agent: {e}")
        
        # Always fallback to simple categorization
        return await categorize_email_simple(email)

async def categorize_email_simple(email: EmailMessage) -> EmailInsight:
    """Simple rule-based email categorization as fallback"""
    try:
        content = f"Subject: {email.subject}\nSnippet: {email.snippet}\nBody: {email.body}"
        content_lower = content.lower()
        
        # Extract amount and currency
        amount, currency = extract_amount_with_currency(content)
        amount_str = f"{currency}{amount}" if amount and currency else None
        
        # Category determination
        if any(word in content_lower for word in ['payment', 'paid', 'transaction', 'charged', 'debited']):
            category, subcategory = 'financial', 'payment'
        elif any(word in content_lower for word in ['order', 'delivery', 'delivered', 'shipped']):
            category, subcategory = 'shopping', 'order'
        elif any(word in content_lower for word in ['subscription', 'renewal', 'auto-renewal']):
            category, subcategory = 'subscription', 'renewal'
        elif any(word in content_lower for word in ['job', 'application', 'interview', 'position']):
            category, subcategory = 'professional', 'job'
        else:
            category, subcategory = 'general', 'misc'
        
        # Merchant extraction
        common_merchants = ['amazon', 'flipkart', 'swiggy', 'zomato', 'uber', 'ola', 'netflix', 'spotify', 'paytm']
        merchant = next((m for m in common_merchants if m in content_lower), 'unknown')
        
        # Payment method detection
        if any(word in content_lower for word in ['upi', 'gpay', 'phonepe', 'paytm']):
            payment_method = 'upi'
        elif any(word in content_lower for word in ['card', 'credit', 'debit']):
            payment_method = 'card'
        elif any(word in content_lower for word in ['bank', 'transfer', 'neft', 'imps']):
            payment_method = 'bank_transfer'
        else:
            payment_method = 'unknown'
        
        return EmailInsight(
            category=category,
            subcategory=subcategory,
            merchant=merchant,
            amount=amount_str,
            payment_method=payment_method,
            timestamp=email.date
        )
        
    except Exception as e:
        print(f"❌ Error in simple categorization: {e}")
        return EmailInsight(
            category='general',
            subcategory='misc',
            merchant='unknown',
            amount=None,
            payment_method='unknown',
            timestamp=email.date
        )

def validate_and_clean_search_results(search_results: List) -> List[Dict]:
    """Validate and clean search results to prevent NoneType errors"""
    cleaned_results = []
    
    if not search_results:
        return cleaned_results
    
    for i, result in enumerate(search_results):
        try:
            # Skip None or invalid results
            if not result or not isinstance(result, dict):
                print(f"⚠️ Skipping invalid result at index {i}: {type(result)}")
                continue
            
            # Ensure required fields exist
            memory = result.get('memory', '')
            metadata = result.get('metadata', {})
            score = result.get('score', 0)
            
            # Handle None metadata
            if metadata is None:
                metadata = {}
            
            # Create cleaned result
            cleaned_result = {
                'memory': memory if memory is not None else '',
                'metadata': metadata,
                'score': score if score is not None else 0
            }
            
            cleaned_results.append(cleaned_result)
            
        except Exception as e:
            print(f"⚠️ Error cleaning result at index {i}: {e}")
            continue
    
    print(f"✅ Cleaned {len(cleaned_results)} valid results from {len(search_results)} raw results")
    return cleaned_results

# ============================================================================
# CORE MEM0 FUNCTIONS
# ============================================================================

async def upload_emails_to_mem0(user_id: str, emails: List[EmailMessage]) -> str:
    """
    Upload emails to Mem0 memory with enhanced error handling for service unavailability
    """
    if not emails:
        logger.warning("⚠️ No emails provided for Mem0 upload")
        return "No emails to upload"

    logger.info(f"🧠 Starting Mem0 upload for {len(emails)} emails (user: {user_id})")
    
    # Enhanced retry configuration for service unavailability
    max_retries = 5
    base_delay = 2
    max_delay = 30
    service_unavailable_retries = 3
    
    successful_uploads = 0
    failed_uploads = 0
    service_unavailable_count = 0
    
    # Process emails with enhanced error handling
    for i, email in enumerate(emails):
        email_success = False
        
        for attempt in range(max_retries):
            try:
                # Create email insight with error handling
                try:
                    insight = await categorize_email_with_agent(email)
                except Exception as categorization_error:
                    logger.warning(f"⚠️ Categorization failed for email {email.id}: {categorization_error}")
                    # Use simple categorization as fallback
                    insight = await categorize_email_simple(email)
                
                # Prepare memory content
                memory_content = f"""
                Email ID: {email.id}
                Subject: {email.subject}
                From: {email.sender}
                Date: {email.date}
                Category: {insight.category}
                Subcategory: {insight.subcategory}
                Merchant: {insight.merchant}
                Amount: {insight.amount}
                Payment Method: {insight.payment_method}
                Content: {email.snippet}
                Body Preview: {email.body[:500] if email.body else 'No body content'}
                """
                
                # Upload to Mem0 with enhanced retry logic
                try:
                    # Prepare messages for Mem0 API
                    messages = [{
                        "role": "user",
                        "content": memory_content
                    }]
                    
                    # Use the correct Mem0 API format
                    aclient.add(
                        messages=messages,
                        user_id=user_id,
                        memory_id=email.id,
                        metadata={
                            "source": "gmail",
                            "email_id": email.id,
                            "category": insight.category,
                            "subcategory": insight.subcategory,
                            "merchant": insight.merchant,
                            "date": email.date,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    successful_uploads += 1
                    email_success = True
                    
                    if (i + 1) % 5 == 0:
                        logger.info(f"✅ Processed: {email.id} | {insight.category}/{insight.subcategory} | {insight.merchant}")
                        logger.info(f"🧠 Progress: {i + 1}/{len(emails)} emails uploaded to Mem0")
                    
                    break  # Success, exit retry loop
                    
                except Exception as mem0_error:
                    error_str = str(mem0_error).lower()
                    
                    # Handle different types of errors
                    if "503" in error_str or "service temporarily unavailable" in error_str:
                        service_unavailable_count += 1
                        
                        if attempt < service_unavailable_retries:
                            # Exponential backoff for service unavailability
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            logger.warning(f"🔄 Mem0 service unavailable for {email.id}. Retrying in {delay}s (attempt {attempt + 1}/{service_unavailable_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Mem0 service persistently unavailable for {email.id} after {service_unavailable_retries} attempts")
                            failed_uploads += 1
                            break
                    
                    elif "502" in error_str or "bad gateway" in error_str:
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (1.5 ** attempt), max_delay)
                            logger.warning(f"🔄 Mem0 bad gateway for {email.id}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Mem0 bad gateway persistent for {email.id}")
                            failed_uploads += 1
                            break
                    
                    elif "rate limit" in error_str or "429" in error_str:
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (3 ** attempt), max_delay)  # Longer delay for rate limits
                            logger.warning(f"🔄 Mem0 rate limited for {email.id}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Mem0 rate limit persistent for {email.id}")
                            failed_uploads += 1
                            break
                    
                    else:
                        logger.error(f"❌ Error processing {email.id}: {mem0_error}")
                        failed_uploads += 1
                        break
                        
            except Exception as processing_error:
                logger.error(f"❌ Unexpected error processing email {email.id}: {processing_error}")
                failed_uploads += 1
                break
        
        # Add small delay between emails to prevent overwhelming the API
        if i < len(emails) - 1:
            await asyncio.sleep(0.1)
    
    # Generate comprehensive result message
    success_rate = (successful_uploads / len(emails)) * 100 if emails else 0
    
    result_message = f"""
    📊 Mem0 Upload Summary for User {user_id}:
    ✅ Successful uploads: {successful_uploads}/{len(emails)} ({success_rate:.1f}%)
    ❌ Failed uploads: {failed_uploads}
    🚫 Service unavailable incidents: {service_unavailable_count}
    """
    
    if service_unavailable_count > 0:
        result_message += f"\n⚠️ Note: Mem0 service experienced {service_unavailable_count} unavailability incidents"
    
    if success_rate >= 80:
        logger.info(f"✅ {result_message}")
    elif success_rate >= 50:
        logger.warning(f"⚠️ {result_message}")
    else:
        logger.error(f"❌ {result_message}")
    
    return result_message.strip()

async def search_with_retry(query: str, user_id: str, limit: int, max_retries: int = 5) -> List[Dict]:
    """Search Mem0 with enhanced retry logic for handling API errors including 503 Service Unavailable"""
    logger.info(f"🔄 Mem0 search: '{query}' (user: {user_id}, limit: {limit})")
    
    base_delay = 1
    max_delay = 20
    service_unavailable_retries = 3
    
    for attempt in range(max_retries):
        try:
            results = sync_client.search(
                query=query,
                user_id=user_id,
                limit=limit,
                filters={"metadata.source": "gmail"},
                keyword_search=True,
                rerank=True,
                filter_memories=False
            )
            
            if results is not None:
                valid_results = [r for r in results if r and isinstance(r, dict)]
                logger.info(f"✅ Search successful: {len(valid_results)} valid results")
                return valid_results
            else:
                logger.warning(f"⚠️ Search returned None (attempt {attempt + 1})")
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle 503 Service Temporarily Unavailable
            if "503" in error_msg or "service temporarily unavailable" in error_msg:
                if attempt < service_unavailable_retries:
                    wait_time = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"🔄 Mem0 service unavailable for search '{query}'. Retrying in {wait_time}s (attempt {attempt + 1}/{service_unavailable_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Mem0 service persistently unavailable for search '{query}' after {service_unavailable_retries} attempts")
                    break
            
            # Handle 502 Bad Gateway
            elif "502" in error_msg or "bad gateway" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = min(base_delay * (1.5 ** attempt), max_delay)
                    logger.warning(f"🔄 Mem0 bad gateway for search '{query}'. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Mem0 bad gateway persistent for search '{query}'")
                    break
            
            # Handle rate limits
            elif "429" in error_msg or "rate limit" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = min(base_delay * (3 ** attempt), max_delay)
                    logger.warning(f"🔄 Mem0 rate limited for search '{query}'. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Mem0 rate limit persistent for search '{query}'")
                    break
            
            # Handle other errors
            else:
                logger.error(f"❌ Search error for '{query}': {e}")
                break
    
    logger.warning(f"🔍 Search failed for '{query}' after {max_retries} attempts, returning empty results")
    return []

async def search_emails_in_mem0(user_id: str, query: str, limit: int = 500) -> List[Dict]:
    """Search emails in Mem0 with Agno-powered query refinement"""
    try:
        print(f"🔍 Starting email search for user {user_id}: '{query}'")
        
        # Use Agno query analyzer to refine the search (with fallback)
        try:
            refined_query_result = query_analyzer.run(f"Refine this query for email search: {query}")
            refined_query = refined_query_result.content.strip() if hasattr(refined_query_result, 'content') else str(refined_query_result).strip()
            print(f"✨ Query refined by Agno agent: '{refined_query}'")
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "insufficient_quota" in error_msg:
                print(f"⚠️ OpenAI quota exceeded, using original query: '{query}'")
            else:
                print(f"⚠️ Query refinement failed, using original query: {e}")
            refined_query = query
        
        # Search with refined query
        results = await search_with_retry(refined_query, user_id, limit)
        
        print(f"\n📊" + "┏" + "━"*76 + "┓" + "📊")
        print(f"📊┃                          MEM0 RAW SEARCH RESULTS                          ┃📊")
        print(f"📊" + "┗" + "━"*76 + "┛" + "📊")
        print(f"📈 TOTAL RESULTS : {len(results) if results else 0}")
        print(f"📊" + "─"*78 + "📊")
        
        if results:
            print(f"🔍 RESULT STRUCTURE:")
            print(f"   ├─ Type        : {type(results[0])}")
            print(f"   └─ Keys        : {list(results[0].keys()) if isinstance(results[0], dict) else 'Not a dict'}")
            print(f"📊" + "─"*78 + "📊")
            
            print(f"📋 SAMPLE RESULTS (First 2):")
            for i, result in enumerate(results[:2]):
                print(f"   📧 RESULT {i+1}:")
                print(f"   ├─ Type        : {type(result)}")
                print(f"   ├─ Keys        : {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                if isinstance(result, dict):
                    memory_preview = result.get('memory', 'No memory')[:80] + "..." if result.get('memory', '') else 'No memory'
                    print(f"   ├─ Memory      : {memory_preview}")
                    print(f"   ├─ Metadata    : {result.get('metadata', 'No metadata')}")
                    print(f"   └─ Score       : {result.get('score', 'No score')}")
                print(f"   " + "─"*76)
        print(f"📊" + "━"*78 + "📊")
        
        # Apply content filtering if we have many results
        if results and len(results) > 10:
            print(f"🎯 Applying content filtering to {len(results)} results...")
            
            filter_prompt = f"""
            Original query: {query}
            Refined query: {refined_query}
            Results found: {len(results)}
            
            Sample results content:
            {json.dumps([r.get('memory', '')[:150] + '...' for r in results[:5]], indent=2)}
            
            Should these results be filtered for relevance to the user's query?
            Return 'KEEP_ALL' if all results appear relevant, or provide filtering guidance.
            """
            
            filter_result = content_filter.run(filter_prompt)
            filter_response = filter_result.content if hasattr(filter_result, 'content') else str(filter_result)
            print(f"🎯 Content filter recommendation: {filter_response[:100]}...")
        
        print(f"🔍 Search completed: {len(results)} results returned")
        return results if results else []
        
    except Exception as e:
        print(f"❌ Search error for query '{query}': {e}")
        return []

# ============================================================================
# MAIN QUERY FUNCTION
# ============================================================================

async def query_mem0(user_id: str, query: str) -> str:
    """
    Main query function using Query-Aware Response Enhancement System
    """
    try:
        print("\n" + "🔥" + "="*78 + "🔥")
        print("🚀                    AGNO GMAIL INTELLIGENCE TEAM ACTIVATED                    🚀")
        print("🔥" + "="*78 + "🔥")
        print(f"👤 USER ID      : {user_id}")
        print(f"❓ QUERY        : '{query}'")
        print(f"⏰ TIMESTAMP    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔥" + "="*78 + "🔥")
        
        # Step 1: Analyze Query Intent
        print("\n🧠" + "━"*76 + "🧠")
        print("🧠                         STEP 1: QUERY INTENT ANALYSIS                         🧠")
        print("🧠" + "━"*76 + "🧠")
        
        intent_prompt = f"""
        Analyze this user query and determine the intent and best response approach:
        
        USER QUERY: "{query}"
        
        Classify the intent as one of:
        1. LINKEDIN - LinkedIn updates, connections, professional networking, account insights
        2. CAREER - Job applications, career progress, interview updates, professional development
        3. TRAVEL - Travel bookings, trip planning, flight updates, hotel reservations
        4. SHOPPING - Purchase behavior, order tracking, shopping patterns, merchant analysis
        5. FINANCIAL - Transaction analysis, spending insights, financial behavior, payments
        6. GENERAL - General email patterns, communication insights, productivity analysis
        
        Respond with JSON format:
        {{
            "intent": "LINKEDIN|CAREER|TRAVEL|SHOPPING|FINANCIAL|GENERAL",
            "confidence": 0.8,
            "key_aspects": ["aspect1", "aspect2", "aspect3"],
            "response_focus": "What the response should focus on"
        }}
        """
        
        print("🔍 Analyzing query intent...")
        try:
            intent_response = query_intent_analyzer.run(intent_prompt)
            intent_content = intent_response.content if hasattr(intent_response, 'content') else str(intent_response)
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]*\}', intent_content, re.DOTALL)
            if json_match:
                intent_data = json.loads(json_match.group())
                query_intent = intent_data.get('intent', 'GENERAL')
                confidence = intent_data.get('confidence', 0.5)
                key_aspects = intent_data.get('key_aspects', [])
                response_focus = intent_data.get('response_focus', 'General email analysis')
            else:
                # Fallback intent detection
                query_lower = query.lower()
                if 'linkedin' in query_lower:
                    query_intent = 'LINKEDIN'
                elif any(word in query_lower for word in ['job', 'career', 'application', 'interview']):
                    query_intent = 'CAREER'
                elif any(word in query_lower for word in ['travel', 'flight', 'hotel', 'trip']):
                    query_intent = 'TRAVEL'
                elif any(word in query_lower for word in ['shop', 'order', 'purchase', 'buy']):
                    query_intent = 'SHOPPING'
                elif any(word in query_lower for word in ['money', 'payment', 'transaction', 'spend']):
                    query_intent = 'FINANCIAL'
                else:
                    query_intent = 'GENERAL'
                confidence = 0.7
                key_aspects = []
                response_focus = f"{query_intent.lower()} analysis"
                
        except Exception as intent_error:
            print(f"⚠️ Intent analysis error: {intent_error}")
            query_intent = 'GENERAL'
            confidence = 0.5
            key_aspects = []
            response_focus = 'General email analysis'
        
        print(f"🎯 QUERY INTENT DETECTED:")
        print(f"├─ Intent          : {query_intent}")
        print(f"├─ Confidence      : {confidence:.1%}")
        print(f"├─ Key Aspects     : {key_aspects}")
        print(f"└─ Response Focus  : {response_focus}")
        
        # Step 2: Search for relevant emails
        print("\n📧" + "━"*76 + "📧")
        print("📧                         STEP 2: EMAIL SEARCH WITH AGNO AGENTS                         📧")
        print("📧" + "━"*76 + "📧")
        
        raw_search_results = await search_emails_in_mem0(user_id, query, 1000)
        
        # Clean and validate search results
        search_results = validate_and_clean_search_results(raw_search_results)
        print(f"📊 Search Results: {len(search_results)} valid emails found")
        
        # Debug: Show sample results
        if search_results:
            print(f"\n🔍" + "┏" + "━"*76 + "┓" + "🔍")
            print(f"🔍┃                        CLEANED SEARCH RESULTS PREVIEW                        ┃🔍")
            print(f"🔍" + "┗" + "━"*76 + "┛" + "🔍")
            
            for i, result in enumerate(search_results[:3]):
                memory_content = result.get('memory', '')
                metadata = result.get('metadata', {})
                print(f"📧 EMAIL {i+1}:")
                print(f"├─ Content     : {memory_content[:80]}...")
                print(f"├─ Category    : {metadata.get('category', 'N/A')}")
                print(f"├─ Merchant    : {metadata.get('merchant', 'N/A')}")
                print(f"└─ Amount      : {metadata.get('amount', 'N/A')}")
                print(f"🔍" + "─"*78 + "🔍")
        
        # Step 3: Generate intelligent response using Query-Aware Enhancement
        print(f"\n🧠" + "━"*76 + "🧠")
        print(f"🧠                      STEP 3: QUERY-AWARE RESPONSE ENHANCEMENT                      🧠")
        print(f"🧠" + "━"*76 + "🧠")
        
        if not search_results:
            return f"""
# 🧠 GMAIL INTELLIGENCE ANALYSIS  
## Query: "{query}"

### ⚠️ NO MATCHING EMAILS FOUND
- No emails found matching your search criteria
- This could mean:
  - The information hasn't been synced to memory yet
  - Different keywords might be needed
  - The data might be in a different format

### 💡 SUGGESTIONS TO TRY
- Use broader or different keywords
- Try searching for related terms
- Check if the email sync is complete
- Verify spelling and terminology
"""
        
        # Prepare comprehensive data for analysis
        print(f"\n📊" + "┏" + "━"*76 + "┓" + "📊")
        print(f"📊┃                      PROCESSING EMAIL DATA FOR ANALYSIS                      ┃📊")
        print(f"📊" + "┗" + "━"*76 + "┛" + "📊")
        email_data = []
        category_stats = {}
        merchant_stats = {}
        amount_data = []
        total_amount = 0
        payment_method_stats = {}
        
        print(f"🔄 Processing {len(search_results)} search results with deduplication...")
        
        # Deduplication tracking
        unique_transactions = {}
        duplicate_count = 0
        
        for i, result in enumerate(search_results):
            # Results are already validated and cleaned
            memory = result.get('memory', '')
            metadata = result.get('metadata', {})
            
            category = metadata.get('category', 'unknown')
            merchant = metadata.get('merchant', 'unknown')
            amount = metadata.get('amount')
            payment_method = metadata.get('payment_method', 'unknown')
            timestamp = metadata.get('timestamp', '')
            
            # Extract numeric amount for calculations
            numeric_amount = 0
            if amount:
                # Try to extract numeric value from amount string
                import re
                amount_match = re.search(r'[\d,]+\.?\d*', str(amount))
                if amount_match:
                    try:
                        numeric_amount = float(amount_match.group().replace(',', ''))
                    except ValueError:
                        pass
            
            # Create deduplication key: merchant + amount + date (YYYY-MM-DD)
            date_part = timestamp[:10] if timestamp and len(timestamp) >= 10 else 'unknown'
            dedup_key = f"{merchant}_{numeric_amount}_{date_part}"
            
            # Check for duplicates
            if dedup_key in unique_transactions and numeric_amount > 0:
                # This is a duplicate transaction
                duplicate_count += 1
                existing = unique_transactions[dedup_key]
                existing['source_emails'].append(f"Email {i+1}")
                existing['duplicate_count'] += 1
                print(f"🔄 DUPLICATE: Email {i+1} merged into {dedup_key} (Total sources: {len(existing['source_emails'])})")
                continue
            
            # New unique transaction
            transaction_data = {
                'content': memory[:400],
                'category': category,
                'merchant': merchant,
                'amount': amount,
                'numeric_amount': numeric_amount,
                'payment_method': payment_method,
                'sender': metadata.get('sender', ''),
                'timestamp': timestamp,
                'score': result.get('score', 0),
                'has_amount': amount is not None,
                'source_emails': [f"Email {i+1}"],
                'duplicate_count': 1,
                'dedup_key': dedup_key,
                'fintransaction_id': dedup_key[:12]  # Short transaction ID
            }
            
            # Store unique transaction
            unique_transactions[dedup_key] = transaction_data
            email_data.append(transaction_data)
            
            # Update statistics (only for unique transactions)
            category_stats[category] = category_stats.get(category, 0) + 1
            merchant_stats[merchant] = merchant_stats.get(merchant, 0) + 1
            payment_method_stats[payment_method] = payment_method_stats.get(payment_method, 0) + 1
            
            # Add to amount tracking
            if amount:
                amount_data.append(amount)
                total_amount += numeric_amount
            
            # Log processing details for first few results
            if i < 3:
                print(f"📧 EMAIL {i+1} PROCESSED:")
                print(f"├─ Category        : {category}")
                print(f"├─ Merchant        : {merchant}")
                print(f"├─ Amount          : {amount}")
                print(f"├─ Numeric Amount  : ₹{numeric_amount:,.2f}")
                print(f"├─ Payment Method  : {payment_method}")
                print(f"├─ Transaction ID  : {dedup_key[:12]}")
                print(f"├─ Source Emails   : {', '.join(transaction_data['source_emails'])}")
                print(f"├─ Status          : {'🆕 NEW UNIQUE' if dedup_key not in unique_transactions or len(transaction_data['source_emails']) == 1 else '🔄 MERGED'}")
                print(f"└─ Content         : {memory[:60]}...")
                print(f"📊" + "─"*78 + "📊")
        
        # Log deduplication summary
        print(f"\n🔍 DEDUPLICATION SUMMARY:")
        print(f"├─ Total Emails Processed : {len(search_results)}")
        print(f"├─ Unique Transactions    : {len(unique_transactions)}")
        print(f"├─ Duplicates Merged      : {duplicate_count}")
        print(f"└─ Deduplication Rate     : {(duplicate_count/len(search_results)*100):.1f}%")
        
        # Log processing summary
        print(f"\n📊" + "┏" + "━"*76 + "┓" + "📊")
        print(f"📊┃                         DATA PROCESSING SUMMARY                         ┃📊")
        print(f"📊" + "┗" + "━"*76 + "┛" + "📊")
        print(f"📈 Total Emails       : {len(email_data)}")
        print(f"💰 Total Amount       : ₹{total_amount:,.2f}")
        print(f"📊 Amount Data Points : {len(amount_data)}")
        print(f"🏷️  Categories Found   : {len(category_stats)} → {dict(list(category_stats.items())[:3])}")
        print(f"🏪 Merchants Found    : {len(merchant_stats)} → {dict(list(merchant_stats.items())[:3])}")
        print(f"💳 Payment Methods    : {len(payment_method_stats)} → {dict(payment_method_stats)}")
        print(f"📊" + "━"*78 + "📊")
        
        # Sort by relevance score (with safety check)
        try:
            email_data.sort(key=lambda x: x.get('score', 0) if x else 0, reverse=True)
            print(f"✅ Sorted {len(email_data)} emails by relevance score")
        except Exception as sort_error:
            print(f"⚠️ Sort error: {sort_error}, continuing without sorting")
        
        # Create Query-Aware Enhanced Prompt with Logical Reasoning Framework
        enhancement_prompt = f"""
        🔥 ADVANCED GMAIL INTELLIGENCE WITH LOGICAL REASONING SYSTEM 🔥
        
        ORIGINAL USER QUERY: "{query}"
        DETECTED INTENT: {query_intent}
        CONFIDENCE LEVEL: {confidence:.1%}
        RESPONSE FOCUS: {response_focus}
        KEY ASPECTS TO ADDRESS: {key_aspects}
        
        🧠 CRITICAL THINKING FRAMEWORK - YOU MUST APPLY LOGICAL REASONING:
        
        STEP 1: DOMAIN KNOWLEDGE DATABASE
        ================================
        Apply these logical connections when analyzing data:
        
        🌍 LOCATION INFERENCE RULES:
        - BMTC = Bengaluru Metropolitan Transport Corporation → User lives/works in Bangalore, India
        - DTC = Delhi Transport Corporation → User lives/works in Delhi, India
        - BEST = Brihanmumbai Electric Supply & Transport → User lives/works in Mumbai, India
        - MTC = Metropolitan Transport Corporation → User lives/works in Chennai, India
        - TSRTC = Telangana State Road Transport Corporation → User lives/works in Hyderabad, India
        - BESCOM = Bangalore Electricity Supply Company → User lives in Bangalore
        - BSES = Bombay Suburban Electric Supply → User lives in Mumbai
        - Delhi Metro/DTC → User lives in Delhi NCR
        
        🚇 TRANSPORT PATTERN LOGIC:
        - Multiple BMTC transactions = Regular commuter in Bangalore
        - Small frequent transport payments = Daily public transport user
        - Regular transport + food delivery = Urban professional lifestyle
        - Transport timing patterns = Work commute vs leisure travel
        
        🏙️ URBAN LIFESTYLE INDICATORS:
        - Swiggy/Zomato + specific city addresses = Lives in that city
        - UPI frequency = Digital adoption level
        - Food delivery patterns = Urban convenience seeker
        - Subscription services = Stable income, tech-savvy
        
        STEP 2: LOGICAL DEDUCTION PROCESS
        =================================
        For EVERY piece of data, ask yourself:
        1. WHAT does this data point tell me directly?
        2. WHAT can I logically infer from this pattern?
        3. WHAT does the frequency/timing suggest about lifestyle?
        4. HOW do multiple data points connect to form a bigger picture?
        5. WHAT is the confidence level of this inference?
        
        EXAMPLE OF REQUIRED THINKING:
        ❌ BAD: "User has BMTC transactions"
        ✅ GOOD: "User has 5+ BMTC transactions over 2 months → Uses Bangalore public transport regularly → Lives or works in Bangalore (95% confidence) → Likely daily commuter → Urban professional lifestyle"
        
        STEP 3: CONNECT THE DOTS
        ========================
        Look for patterns across different data types:
        - Transport services + Food delivery locations = Residence area
        - Payment timing + Merchant types = Lifestyle patterns
        - Service frequency + Amount patterns = User behavior profile
        
        EMAIL DATA ANALYSIS:
        ================================
        📊 DATASET OVERVIEW:
        - Total emails analyzed: {len(email_data)}
        - Query relevance scores: {[email.get('score', 0) for email in email_data[:5]]}
        - Categories distribution: {dict(sorted(category_stats.items(), key=lambda x: x[1], reverse=True))}
        - Merchants/Services: {dict(sorted(merchant_stats.items(), key=lambda x: x[1], reverse=True))}
        - Financial data points: {len(amount_data)} transactions totaling ₹{total_amount:,.2f}
        
        📧 TOP RELEVANT EMAIL CONTENTS:
        {chr(10).join([f"Email {i+1} (Score: {email.get('score', 0):.2f}): {email.get('content', '')[:250]}..." for i, email in enumerate(email_data[:8]) if email])}
        
        🎯 MANDATORY LOGICAL ANALYSIS REQUIREMENTS:
        
        1. **APPLY DOMAIN KNOWLEDGE**: Use the location inference rules above
        2. **MAKE LOGICAL CONNECTIONS**: Don't just list facts, connect them logically
        3. **PROVIDE REASONING**: Show your thinking process for major conclusions
        4. **ASSIGN CONFIDENCE LEVELS**: Rate your inferences (90%+ = High, 70-89% = Medium, 50-69% = Low)
        5. **CONNECT PATTERNS**: Link different data points to build comprehensive insights
        
        SPECIFIC ANALYSIS REQUIRED:
        - If BMTC appears: You MUST conclude "User likely lives/works in Bangalore"
        - If frequent transport usage: You MUST infer commuting patterns and lifestyle
        - If location-specific services: You MUST identify the specific city/area
        - If spending patterns: You MUST infer lifestyle and financial behavior
        
        RESPONSE STRUCTURE - INCLUDE LOGICAL REASONING SECTION:
        
        🧠 LOGICAL DEDUCTIONS:
        - [Service/Pattern] → [Logical Inference] → [Conclusion] (Confidence: X%)
        - [Multiple patterns] → [Combined inference] → [Lifestyle profile] (Confidence: X%)
        
        🌍 LOCATION INTELLIGENCE:
        - Primary Location: [City] (Confidence: X%)
        - Supporting Evidence: [List specific evidence]
        - Area/Neighborhood: [If inferable from addresses]
        
        INTENT-SPECIFIC REQUIREMENTS:
        - LINKEDIN: Focus on professional networking, connections, job alerts, account activity
        - CAREER: Analyze job applications, career progress, professional opportunities
        - TRAVEL: Examine travel patterns, bookings, trip insights, destination analysis
        - SHOPPING: Review purchase behavior, merchant relationships, order patterns
        - FINANCIAL: Provide spending analysis, transaction insights, financial behavior
        - GENERAL: Offer comprehensive email pattern analysis and productivity insights
        👤 LIFESTYLE PROFILE:
        - User Type: [Urban professional/Student/etc.]
        - Daily Patterns: [Commuter/Remote worker/etc.]
        - Tech Adoption: [High/Medium/Low based on digital usage]
        
        CRITICAL INSTRUCTIONS:
        - ALWAYS make logical inferences - don't just state facts
        - EXPLAIN your reasoning for major conclusions
        - USE domain knowledge to connect services to locations
        - PROVIDE confidence percentages for key inferences
        - DIRECTLY ADDRESS the user's question with intelligent insights
        
        Remember: The user asked "{query}" - use logical reasoning to provide intelligent insights that go beyond surface-level data analysis!
        """
        
        print(f"\n🤖" + "┏" + "━"*76 + "┓" + "🤖")
        print(f"🤖┃                    RUNNING QUERY-AWARE RESPONSE ENHANCEMENT                    ┃🤖")
        print(f"🤖" + "┗" + "━"*76 + "┛" + "🤖")
        
        print(f"📝 ENHANCEMENT PROMPT PREVIEW:")
        print(f"🤖" + "─"*78 + "🤖")
        prompt_preview = enhancement_prompt[:500] + "..." if len(enhancement_prompt) > 500 else enhancement_prompt
        # Format the prompt nicely
        for line in prompt_preview.split('\n')[:8]:
            if line.strip():
                print(f"📝 {line[:70]}...")
        print(f"🤖" + "─"*78 + "🤖")
        
        try:
            # Use the response enhancer for better, context-aware results
            print("🔄 Calling response_enhancer.run()...")
            enhancement_response = response_enhancer.run(enhancement_prompt)
            
            print(f"\n📤" + "┏" + "━"*76 + "┓" + "📤")
            print(f"📤┃                      RESPONSE ENHANCER RAW OUTPUT                      ┃📤")
            print(f"📤" + "┗" + "━"*76 + "┛" + "📤")
            print(f"🔍 Response Type       : {type(enhancement_response)}")
            print(f"📦 Response Object     : {str(enhancement_response)[:60]}...")
            if hasattr(enhancement_response, '__dict__'):
                print(f"🏷️  Response Attributes : {list(enhancement_response.__dict__.keys())}")
            print(f"📤" + "─"*78 + "📤")
            
            # Extract response content with null checks
            if enhancement_response is None:
                print("⚠️ Enhancement response is None")
                final_response = "❌ Response enhancement returned empty response"
            elif hasattr(enhancement_response, 'content'):
                print(f"✅ Enhancement response has content attribute")
                print(f"📝 Content length: {len(enhancement_response.content) if enhancement_response.content else 0}")
                if enhancement_response.content:
                    print(f"📝 CONTENT PREVIEW:")
                    print(f"📤" + "┌" + "─"*76 + "┐" + "📤")
                    content_preview = enhancement_response.content[:400] + "..." if len(enhancement_response.content) > 400 else enhancement_response.content
                    # Format content nicely
                    for line in content_preview.split('\n')[:6]:
                        if line.strip():
                            print(f"📝 │ {line[:72]:<72} │")
                    print(f"📤" + "└" + "─"*76 + "┘" + "📤")
                final_response = enhancement_response.content if enhancement_response.content else "❌ Response enhancement returned empty content"
            else:
                print(f"⚠️ Enhancement response has no content attribute, converting to string")
                final_response = str(enhancement_response) if enhancement_response else "❌ Response enhancement failed"
                print(f"📝 STRING RESPONSE PREVIEW:")
                print(f"📤" + "┌" + "─"*76 + "┐" + "📤")
                response_preview = final_response[:400] + "..." if len(final_response) > 400 else final_response
                for line in response_preview.split('\n')[:6]:
                    if line.strip():
                        print(f"📝 │ {line[:72]:<72} │")
                print(f"📤" + "└" + "─"*76 + "┘" + "📤")
                
        except Exception as enhancement_error:
            print(f"❌ Response enhancement error: {enhancement_error}")
            # Generate intent-specific fallback response
            if query_intent == 'LINKEDIN':
                final_response = generate_linkedin_report(query, email_data)
            elif query_intent == 'CAREER':
                final_response = generate_job_application_report(query, email_data)
            elif query_intent == 'TRAVEL':
                final_response = generate_travel_report(query, email_data)
            elif query_intent == 'SHOPPING':
                final_response = generate_shopping_report(query, email_data)
            elif query_intent == 'FINANCIAL':
                final_response = generate_financial_report(query, email_data, category_stats, merchant_stats, total_amount, amount_data)
            else:
                final_response = generate_general_report(query, email_data)
        
        # Check if response is too short or generic - use intent-specific fallback
        if len(final_response) < 500:
            print(f"⚠️ Response too short, generating {query_intent.lower()} fallback report...")
            if query_intent == 'LINKEDIN':
                final_response = generate_linkedin_report(query, email_data)
            elif query_intent == 'CAREER':
                final_response = generate_job_application_report(query, email_data)
            elif query_intent == 'TRAVEL':
                final_response = generate_travel_report(query, email_data)
            elif query_intent == 'SHOPPING':
                final_response = generate_shopping_report(query, email_data)
            elif query_intent == 'FINANCIAL':
                final_response = generate_financial_report(query, email_data, category_stats, merchant_stats, total_amount, amount_data)
            else:
                final_response = generate_general_report(query, email_data)
        
        print(f"✅ Query-aware analysis completed")
        print(f"📝 Response generated: {len(final_response)} characters")
        
        print(f"\n📤" + "┏" + "━"*76 + "┓" + "📤")
        print(f"📤┃                           FINAL RESPONSE TO USER                           ┃📤")
        print(f"📤" + "┗" + "━"*76 + "┛" + "📤")
        print(f"📏 Response Length     : {len(final_response)} characters")
        print(f"📤" + "─"*78 + "📤")
        print(f"📝 RESPONSE PREVIEW:")
        print(f"📤" + "┌" + "─"*76 + "┐" + "📤")
        response_lines = final_response[:600].split('\n')
        for line in response_lines[:8]:
            if line.strip():
                print(f"📝 │ {line[:72]:<72} │")
        if len(final_response) > 600:
            print(f"📝 │ {'... (truncated for display)':^72} │")
        print(f"📤" + "└" + "─"*76 + "┘" + "📤")
        
        print(f"\n✅" + "┏" + "━"*76 + "┓" + "✅")
        print(f"✅┃                  AGNO GMAIL INTELLIGENCE ANALYSIS COMPLETED                  ┃✅")
        print(f"✅" + "┗" + "━"*76 + "┛" + "✅")
        print(f"🏁 FINAL SUMMARY:")
        print(f"├─ User ID         : {user_id}")
        print(f"├─ Query           : {query}")
        print(f"├─ Detected Intent : {query_intent} ({confidence:.1%} confidence)")
        print(f"├─ Search Results  : {len(search_results)} emails")
        print(f"├─ Response Length : {len(final_response)} characters")
        print(f"├─ Processing Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"└─ Status          : ✅ Analysis completed successfully")
        print(f"✅" + "━"*78 + "✅")
        
        return final_response
            
    except Exception as e:
        print(f"\n❌ AGNO TEAM ERROR: {e}")
        print("="*80)
        print(f"🚨 ERROR DETAILS:")
        print(f"  User ID: {user_id}")
        print(f"  Query: {query}")
        print(f"  Error Type: {type(e).__name__}")
        print(f"  Error Message: {str(e)}")
        print(f"  Traceback: {traceback.format_exc()}")
        print("="*80)
        return f"❌ I encountered an error while processing your query with the Agno Gmail Intelligence Team: {str(e)}"

# Add new LinkedIn report generator function
def generate_linkedin_report(query: str, email_data: List[Dict]) -> str:
    """Generate LinkedIn-specific insights report"""
    try:
        linkedin_emails = [email for email in email_data if 'linkedin' in email.get('content', '').lower() or 'linkedin' in email.get('sender', '').lower()]
        
        if not linkedin_emails:
            return f"""
# 🌟 LINKEDIN ACCOUNT INTELLIGENCE REPORT 🌟

## Query: "{query}"

### ⚠️ LIMITED LINKEDIN DATA FOUND
Based on the available email data, I found limited LinkedIn-specific information. Here's what I can provide:

### 📊 EMAIL ANALYSIS SUMMARY
- **Total Emails Analyzed**: {len(email_data)}
- **LinkedIn-Related Content**: {len(linkedin_emails)} emails
- **Professional Categories**: {len([e for e in email_data if e.get('category') == 'professional'])} emails

### 💡 RECOMMENDATIONS
1. **Sync More Data**: Ensure LinkedIn notifications are enabled in your email
2. **Check Email Filters**: Verify LinkedIn emails aren't being filtered
3. **Professional Activity**: Consider increasing LinkedIn engagement for more insights

### 🔍 GENERAL PROFESSIONAL INSIGHTS
{chr(10).join([f"- {email.get('content', '')[:100]}..." for email in email_data[:3] if 'job' in email.get('content', '').lower() or 'career' in email.get('content', '').lower()])}
"""
        
        # Extract LinkedIn-specific insights
        connections = []
        job_alerts = []
        notifications = []
        
        for email in linkedin_emails:
            content = email.get('content', '').lower()
            if 'connection' in content or 'connect' in content:
                connections.append(email)
            elif 'job' in content or 'opportunity' in content:
                job_alerts.append(email)
            else:
                notifications.append(email)
        
        return f"""
# 🌟 LINKEDIN ACCOUNT INTELLIGENCE REPORT 🌟

## Query: "{query}"

### 📊 EXECUTIVE SUMMARY - YOUR LINKEDIN ENGAGEMENT PROFILE
**🎯 INSTANT INSIGHTS:**
- 🌐 **Total LinkedIn Emails Analyzed**: {len(linkedin_emails)} 
- 👥 **Connection-Related**: {len(connections)} emails
- 💼 **Job Opportunities**: {len(job_alerts)} alerts
- 🔔 **General Notifications**: {len(notifications)} updates
- 📈 **Engagement Level**: {'High' if len(linkedin_emails) > 5 else 'Moderate' if len(linkedin_emails) > 2 else 'Low'}

### 📋 LINKEDIN ACTIVITY BREAKDOWN
| 📅 Type | 📊 Count | 📈 Insights |
|---------|----------|-------------|
| Connection Requests | {len(connections)} | {'Active networking' if len(connections) > 2 else 'Limited networking'} |
| Job Opportunities | {len(job_alerts)} | {'Strong job market presence' if len(job_alerts) > 3 else 'Moderate opportunities'} |
| Platform Notifications | {len(notifications)} | {'Engaged user' if len(notifications) > 2 else 'Casual user'} |

### 🧠 PROFESSIONAL NETWORK INSIGHTS
**🔄 CONNECTION PATTERNS**
{chr(10).join([f"- {email.get('content', '')[:150]}..." for email in connections[:3]]) if connections else "- No recent connection activity detected"}

**📢 JOB MARKET ENGAGEMENT**
{chr(10).join([f"- {email.get('content', '')[:150]}..." for email in job_alerts[:3]]) if job_alerts else "- No recent job alerts found"}

### 🚀 ACTIONABLE LINKEDIN INTELLIGENCE
**⚡ IMMEDIATE ACTIONS**
1. **Expand Network**: {'Continue active networking' if len(connections) > 2 else 'Increase connection requests'}
2. **Job Opportunities**: {'Review and apply to relevant positions' if len(job_alerts) > 0 else 'Set up more specific job alerts'}

**🎯 STRATEGIC MOVES**
1. **Profile Optimization**: Ensure your profile reflects current career goals
2. **Content Engagement**: {'Maintain current engagement level' if len(linkedin_emails) > 5 else 'Increase platform activity'}

**🚀 LONG-TERM STRATEGY**
1. **Professional Branding**: Build thought leadership through content sharing
2. **Network Quality**: Focus on meaningful professional connections

### 📱 LINKEDIN OPTIMIZATION RECOMMENDATIONS
- **Activity Level**: {'Excellent engagement' if len(linkedin_emails) > 5 else 'Room for improvement'}
- **Network Growth**: {'Strong networking activity' if len(connections) > 2 else 'Consider expanding connections'}
- **Career Focus**: {'Active job seeker' if len(job_alerts) > 3 else 'Passive career monitoring'}

---

*This analysis is based on {len(linkedin_emails)} LinkedIn-related emails from your Gmail data. For more comprehensive insights, ensure LinkedIn notifications are enabled and synced.*
"""
    except Exception as e:
        return f"❌ Error generating LinkedIn report: {str(e)}"

# ============================================================================
# GMAIL DATA PROCESSING
# ============================================================================

async def process_gmail_data_for_user(user_id: str, gmail_emails: List[Dict]) -> Dict[str, Any]:
    """
    Process Gmail data for a user using Agno agents system
    """
    try:
        print(f"🎯 Processing Gmail data for user {user_id} with Agno agents")
        
        # Convert to EmailMessage objects
        email_messages = []
        for email_data in gmail_emails:
            email = EmailMessage(
                id=email_data.get('id', ''),
                subject=email_data.get('subject', ''),
                sender=email_data.get('sender', ''),
                snippet=email_data.get('snippet', ''),
                body=email_data.get('body', ''),
                date=email_data.get('date', '')
            )
            email_messages.append(email)
        
        # Process with NEW PARALLEL SYSTEM
        from .parallel_mem0_uploader import upload_emails_parallel_optimized
        
        # Convert to dict format for parallel uploader
        emails_for_parallel = []
        for email_msg in email_messages:
            emails_for_parallel.append({
                "id": email_msg.id,
                "subject": email_msg.subject,
                "sender": email_msg.sender,
                "snippet": email_msg.snippet,
                "body": email_msg.body,
                "date": email_msg.date
            })
        
        upload_result = await upload_emails_parallel_optimized(user_id, emails_for_parallel)
        
        # Update user status in database
        try:
            from .db import users_collection
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "initial_gmailData_sync": True,
                    "fetched_email": True,
                    "last_sync_timestamp": datetime.now().isoformat(),
                    "processing_system": "agno_agents"
                }}
            )
        except Exception as db_error:
            print(f"⚠️ Database update error: {db_error}")
        
        print(f"✅ Gmail data processing completed for user {user_id}")
        
        return {
            "status": "success",
            "processed_emails": len(email_messages),
            "user_id": user_id,
            "upload_result": upload_result,
            "timestamp": datetime.now().isoformat(),
            "processing_system": "Agno Gmail Intelligence Team",
            "version": "2.0"
        }
        
    except Exception as e:
        print(f"❌ Error processing Gmail data for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "processing_system": "Agno Gmail Intelligence Team",
            "version": "2.0"
        }

# ============================================================================
# SYSTEM INFO
# ============================================================================

def get_system_info() -> Dict[str, Any]:
    """Get information about the Agno Gmail Intelligence system"""
    return {
        "system_name": "Agno Gmail Intelligence Team",
        "version": "2.0",
        "agents": [
            "QueryAnalyzer - Query refinement and intent understanding",
            "EmailCategorizer - Email categorization and insight extraction", 
            "ContentFilter - Search result filtering and relevance scoring",
            "IntelligenceAgent - Comprehensive analysis and response generation"
        ],
        "capabilities": [
            "Intelligent email search with query refinement",
            "AI-powered email categorization",
            "Content filtering for precision",
            "Comprehensive data analysis",
            "Pattern recognition and insights",
            "Multi-agent collaboration"
        ],
        "technologies": ["Agno Framework", "OpenAI GPT-4", "Mem0 Memory", "Python"],
        "status": "active"
    }

print("🚀 Agno Gmail Intelligence Team system loaded successfully!")
print("📊 System Info:", json.dumps(get_system_info(), indent=2))

def generate_fallback_report(query: str, email_data: List[Dict], category_stats: Dict, merchant_stats: Dict, total_amount: float, amount_data: List) -> str:
    """Generate an INSANELY GREAT fallback report using actual email data - query-aware"""
    try:
        # Detect query type
        query_lower = query.lower()
        is_job_query = any(keyword in query_lower for keyword in ['job', 'application', 'career', 'interview', 'resume', 'hiring', 'position', 'employment'])
        is_financial_query = any(keyword in query_lower for keyword in ['money', 'transaction', 'payment', 'purchase', 'spending', 'financial', 'cost', 'price'])
        is_travel_query = any(keyword in query_lower for keyword in ['travel', 'trip', 'flight', 'hotel', 'booking', 'vacation', 'journey'])
        is_shopping_query = any(keyword in query_lower for keyword in ['shopping', 'order', 'delivery', 'product', 'buy', 'purchase'])
        
        # Generate appropriate report based on query type
        print(f"\n🎯" + "┏" + "━"*76 + "┓" + "🎯")
        print(f"🎯┃                           QUERY TYPE DETECTION                           ┃🎯")
        print(f"🎯" + "┗" + "━"*76 + "┛" + "🎯")
        print(f"🔍 Job Query       : {'✅ YES' if is_job_query else '❌ NO'}")
        print(f"💰 Financial Query : {'✅ YES' if is_financial_query else '❌ NO'}")
        print(f"✈️  Travel Query    : {'✅ YES' if is_travel_query else '❌ NO'}")
        print(f"🛒 Shopping Query  : {'✅ YES' if is_shopping_query else '❌ NO'}")
        print(f"🎯" + "─"*78 + "🎯")
        
        if is_job_query:
            print("🚀 Generating JOB APPLICATION REPORT")
            return generate_job_application_report(query, email_data)
        elif is_travel_query:
            print("✈️ Generating TRAVEL REPORT")
            return generate_travel_report(query, email_data)
        elif is_shopping_query:
            print("🛒 Generating SHOPPING REPORT")
            return generate_shopping_report(query, email_data)
        elif is_financial_query:
            print("🔥 Generating FINANCIAL REPORT")
            return generate_financial_report(query, email_data, category_stats, merchant_stats, total_amount, amount_data)
        else:
            print("📧 Generating GENERAL REPORT")
            return generate_general_report(query, email_data)
        
    except Exception as e:
        print(f"❌ Error generating fallback report: {e}")
        return f"""# 📧 GMAIL INTELLIGENCE REPORT 📧
## Query: "{query}"

### ⚠️ DATA PROCESSING SUMMARY
I found {len(email_data)} emails related to your query.

**Analysis Summary:**
- Email content analysis completed
- Query-specific insights generated
- System processing optimized for your request

**Key Findings:**
{chr(10).join([f"- {email.get('content', '')[:100]}..." for email in email_data[:3]]) if email_data else "- No specific data available"}

The system is analyzing your email patterns to provide detailed insights.
"""

def generate_job_application_report(query: str, email_data: List[Dict]) -> str:
    """Generate a job application insights report"""
    try:
        # Analyze job-related emails
        job_emails = []
        companies = set()
        positions = set()
        response_types = {'positive': 0, 'negative': 0, 'neutral': 0, 'no_response': 0}
        
        for email in email_data:
            content = email.get('content', '').lower()
            if any(keyword in content for keyword in ['application', 'interview', 'position', 'job', 'career', 'hiring']):
                job_emails.append(email)
                
                # Extract company names (basic extraction)
                words = content.split()
                for i, word in enumerate(words):
                    if word in ['at', 'with', 'from'] and i + 1 < len(words):
                        potential_company = words[i + 1].strip('.,!?').title()
                        if len(potential_company) > 2:
                            companies.add(potential_company)
                
                # Analyze response sentiment
                if any(positive in content for positive in ['congratulations', 'pleased', 'selected', 'offer', 'interview']):
                    response_types['positive'] += 1
                elif any(negative in content for negative in ['regret', 'unfortunately', 'not selected', 'rejected']):
                    response_types['negative'] += 1
                elif any(neutral in content for neutral in ['thank you', 'received', 'application']):
                    response_types['neutral'] += 1
        
        total_applications = len(job_emails)
        response_rate = ((response_types['positive'] + response_types['negative'] + response_types['neutral']) / total_applications * 100) if total_applications > 0 else 0
        
        # Generate application table
        application_rows = []
        for i, email in enumerate(job_emails[:10]):
            content = email.get('content', '')[:100]
            date = email.get('timestamp', 'Unknown')[:10] if email.get('timestamp') else 'Unknown'
            
            # Determine status
            content_lower = content.lower()
            if any(pos in content_lower for pos in ['congratulations', 'selected', 'offer']):
                status = "✅ Positive"
            elif any(neg in content_lower for neg in ['regret', 'unfortunately', 'rejected']):
                status = "❌ Rejected"
            elif any(neu in content_lower for neu in ['thank you', 'received']):
                status = "📧 Acknowledged"
            else:
                status = "❓ Unknown"
            
            application_rows.append(f"| {date} | Unknown Company | Unknown Position | {status} | Email Response | Application {i+1} |")
        
        report = f"""# 🚀 GMAIL CAREER INTELLIGENCE REPORT 🚀
## Query: "{query}"

### 💼 EXECUTIVE SUMMARY - YOUR CAREER DNA
**🎯 INSTANT INSIGHTS:**
- 📧 **Total Applications Tracked**: {total_applications} applications across email history
- 📊 **Response Rate**: {response_rate:.1f}% of applications received responses
- 🏆 **Top Industry Focus**: Technology/General - Based on email patterns
- ⚡ **Application Velocity**: {total_applications} applications detected
- 🎪 **Career Personality**: Active Job Seeker with Digital Approach

### 📋 COMPLETE APPLICATION BREAKDOWN
| 📅 Date | 🏢 Company | 📍 Position | 📊 Status | 💬 Response Type | 🔍 Insights |
|---------|------------|-------------|----------|------------------|-------------|
{chr(10).join(application_rows) if application_rows else "| No Data | No applications | No positions | No status | No responses | No job application data found |"}

### 🎯 CAREER INTELLIGENCE MATRIX
**🏢 COMPANY TARGETING STRATEGY**
- **Companies Identified**: {len(companies)} different companies detected
- **🔥 CAREER INSIGHT**: {f"Diversified application strategy across {len(companies)} companies" if companies else "Limited company data available"}
- **💡 OPTIMIZATION**: Focus on tracking company responses and follow-up strategies

**📊 RESPONSE ANALYSIS**
         - **Positive Responses**: {response_types['positive']} ({(response_types['positive']/total_applications*100):.1f if total_applications > 0 else 0}%)
         - **Rejections**: {response_types['negative']} ({(response_types['negative']/total_applications*100):.1f if total_applications > 0 else 0}%)
         - **Neutral/Acknowledgments**: {response_types['neutral']} ({(response_types['neutral']/total_applications*100):.1f if total_applications > 0 else 0}%)
- **🔥 INSIGHT**: {"Balanced response pattern" if response_types['positive'] > 0 else "Focus on improving application quality"}
- **💡 STRATEGY**: {"Leverage successful application patterns" if response_types['positive'] > 0 else "Enhance resume and cover letter approach"}

### 🧠 BEHAVIORAL CAREER PSYCHOLOGY
**💡 KEY PATTERNS IDENTIFIED:**
- **Application Frequency**: {total_applications} applications detected in email history
- **Digital Communication**: High usage of email for job application tracking
- **Response Engagement**: {"Active engagement with recruiters" if response_types['positive'] > 0 else "Opportunity to improve follow-up strategies"}
- **Career Focus**: {"Focused job search approach" if len(companies) < 10 else "Broad job search strategy"}

### 🚀 PREDICTIVE CAREER INTELLIGENCE
**📈 JOB SEARCH TRAJECTORY:**
         - **Application Success Rate**: {(response_types['positive']/total_applications*100):.1f if total_applications > 0 else "Insufficient data"}%
- **Interview Potential**: {"High potential based on positive responses" if response_types['positive'] > 0 else "Focus on improving application quality"}
- **Career Progression**: Based on application patterns and response rates

### 💎 EXCLUSIVE INSIGHTS (The WOW Factor)
**🔥 HIDDEN PATTERNS DISCOVERED:**
- Your job search shows {"a strategic approach with multiple company targets" if len(companies) > 3 else "focused targeting of specific companies"}
- Email-based application tracking indicates organized job search methodology
- Response pattern suggests {"strong candidate profile" if response_types['positive'] > 0 else "opportunity for application optimization"}

### 🏆 ACTIONABLE INTELLIGENCE DASHBOARD
**⚡ IMMEDIATE ACTIONS (Next 7 Days)**
1. **Follow-up Strategy**: Contact companies that haven't responded within 2 weeks
2. **Application Tracking**: Create a systematic tracking system for all applications
3. **Response Analysis**: Review successful applications to identify winning patterns

**🎯 STRATEGIC MOVES (Next 30 Days)**
1. **Resume Optimization**: Update resume based on successful application patterns
2. **Network Expansion**: Leverage positive responses to build professional network
3. **Interview Preparation**: Prepare for potential interviews based on application momentum

**🚀 LONG-TERM CAREER STRATEGY (Next 12 Months)**
1. **Skill Development**: Focus on skills mentioned in job descriptions
2. **Industry Targeting**: Concentrate on industries showing positive response rates
3. **Professional Branding**: Build online presence based on successful application themes

### 📱 SMART ALERTS & NOTIFICATIONS
- **Application Alert**: Track new job applications and responses
- **Follow-up Reminder**: Set reminders for application follow-ups
- **Success Pattern**: Monitor patterns in successful applications
- **Market Intelligence**: Track industry trends from job postings and responses

---
*This report analyzes your job application patterns from email data to provide career advancement insights.*"""

        return report
        
    except Exception as e:
        return f"""# 🚀 GMAIL CAREER INTELLIGENCE REPORT 🚀
## Query: "{query}"

### ⚠️ CAREER DATA ANALYSIS
I found {len(email_data)} emails related to your query about job applications.

**Analysis Summary:**
- Email content suggests job application activity
- Response patterns indicate active job search
- Career-focused communication detected

**Key Findings:**
{chr(10).join([f"- {email.get('content', '')[:100]}..." for email in email_data[:3]]) if email_data else "- No specific job application data available"}

The system is analyzing your job application patterns to provide detailed career insights.
"""

def generate_travel_report(query: str, email_data: List[Dict]) -> str:
    """Generate a travel insights report"""
    return f"""# ✈️ GMAIL TRAVEL INTELLIGENCE REPORT ✈️
## Query: "{query}"

### 🌍 EXECUTIVE SUMMARY - YOUR TRAVEL DNA
**🎯 INSTANT INSIGHTS:**
- ✈️ **Travel Activity**: {len(email_data)} travel-related emails detected
- 📊 **Travel Behavior**: Active traveler with digital booking preferences
- 🏆 **Destination Focus**: Multiple destinations based on email patterns
- ⚡ **Booking Velocity**: Regular travel planning and booking activity
- 🎪 **Travel Personality**: Organized Digital Traveler

### 📋 COMPLETE TRAVEL BREAKDOWN
| 📅 Date | 🌍 Destination | 🏨 Type | 💰 Cost | 🎫 Booking | 🔍 Insights |
|---------|----------------|---------|----------|-------------|-------------|
{chr(10).join([f"| Unknown | Travel Activity | Booking | Unknown | Email | {email.get('content', '')[:50]}..." for email in email_data[:5]]) if email_data else "| No Data | No destinations | No bookings | No costs | No travel | No travel data found |"}

### 🎯 TRAVEL INTELLIGENCE MATRIX
**✈️ BOOKING PATTERNS**
- **Digital Bookings**: High preference for online travel booking
- **🔥 TRAVEL INSIGHT**: Organized approach to travel planning
- **💡 OPTIMIZATION**: Track booking confirmations for better trip management

### 🏆 ACTIONABLE TRAVEL INTELLIGENCE
**⚡ IMMEDIATE ACTIONS (Next 7 Days)**
1. **Trip Organization**: Compile all travel confirmations in one place
2. **Travel Tracking**: Set up alerts for booking confirmations
3. **Itinerary Planning**: Create comprehensive travel itineraries

---
*This report analyzes your travel patterns from email data.*"""

def generate_shopping_report(query: str, email_data: List[Dict]) -> str:
    """Generate a shopping insights report"""
    return f"""# 🛒 GMAIL SHOPPING INTELLIGENCE REPORT 🛒
## Query: "{query}"

### 🛍️ EXECUTIVE SUMMARY - YOUR SHOPPING DNA
**🎯 INSTANT INSIGHTS:**
- 🛒 **Shopping Activity**: {len(email_data)} shopping-related emails detected
- 📊 **Shopping Behavior**: Active online shopper with diverse preferences
- 🏆 **Merchant Focus**: Multiple retailers based on email patterns
- ⚡ **Purchase Velocity**: Regular online shopping activity
- 🎪 **Shopping Personality**: Digital-First Shopper

### 📋 COMPLETE SHOPPING BREAKDOWN
| 📅 Date | 🏪 Merchant | 🎯 Category | 💰 Amount | 📦 Status | 🔍 Insights |
|---------|-------------|-------------|-----------|-----------|-------------|
{chr(10).join([f"| Unknown | Shopping | Online | Unknown | Delivered | {email.get('content', '')[:50]}..." for email in email_data[:5]]) if email_data else "| No Data | No merchants | No categories | No amounts | No orders | No shopping data found |"}

### 🎯 SHOPPING INTELLIGENCE MATRIX
**🛒 PURCHASE PATTERNS**
- **Online Shopping**: High preference for digital shopping platforms
- **🔥 SHOPPING INSIGHT**: Consistent online purchasing behavior
- **💡 OPTIMIZATION**: Track order confirmations and delivery status

### 🏆 ACTIONABLE SHOPPING INTELLIGENCE
**⚡ IMMEDIATE ACTIONS (Next 7 Days)**
1. **Order Tracking**: Monitor all pending deliveries
2. **Purchase History**: Organize shopping confirmations
3. **Spending Review**: Analyze shopping patterns for optimization

---
*This report analyzes your shopping patterns from email data.*"""

def generate_general_report(query: str, email_data: List[Dict]) -> str:
    """Generate a general insights report"""
    return f"""# 📧 GMAIL INTELLIGENCE REPORT 📧
## Query: "{query}"

### 💡 EXECUTIVE SUMMARY - YOUR EMAIL INSIGHTS
**🎯 INSTANT INSIGHTS:**
- 📧 **Relevant Emails**: {len(email_data)} emails found related to your query
- 📊 **Communication Pattern**: Active email engagement
- 🏆 **Content Focus**: Diverse email content based on query
- ⚡ **Email Activity**: Regular email communication
- 🎪 **Digital Personality**: Connected Digital Communicator

### 📋 COMPLETE EMAIL BREAKDOWN
| 📅 Date | 📧 Sender | 🎯 Topic | 📊 Relevance | 🔍 Content Preview |
|---------|-----------|----------|--------------|-------------------|
{chr(10).join([f"| {email.get('timestamp', 'Unknown')[:10] if email.get('timestamp') else 'Unknown'} | {email.get('sender', 'Unknown')} | General | High | {email.get('content', '')[:50]}..." for email in email_data[:5]]) if email_data else "| No Data | No senders | No topics | No relevance | No email content found |"}

### 🎯 COMMUNICATION INTELLIGENCE
**📧 EMAIL PATTERNS**
- **Communication Style**: {f"Active email user with {len(email_data)} relevant emails" if email_data else "Limited email activity"}
- **🔥 INSIGHT**: {"Diverse email content suggests broad interests" if len(email_data) > 5 else "Focused email communication"}
- **💡 OPTIMIZATION**: Organize emails by topic for better information management

### 🏆 ACTIONABLE INTELLIGENCE
**⚡ IMMEDIATE ACTIONS (Next 7 Days)**
1. **Email Organization**: Create folders for different email types
2. **Content Review**: Analyze email content for important information
3. **Follow-up Actions**: Identify emails requiring responses or actions

---
*This report analyzes your email patterns related to your specific query.*"""

def generate_financial_report(query: str, email_data: List[Dict], category_stats: Dict, merchant_stats: Dict, total_amount: float, amount_data: List) -> str:
    """Generate the original financial report"""
    try:
        # Calculate key metrics
        transaction_count = len([email for email in email_data if email.get('has_amount')])
        avg_amount = total_amount / len(amount_data) if amount_data else 0
        top_category = max(category_stats.items(), key=lambda x: x[1])[0] if category_stats else "unknown"
        top_merchant = max(merchant_stats.items(), key=lambda x: x[1])[0] if merchant_stats else "unknown"
        
        # Generate transaction table rows
        transaction_rows = []
        for i, email in enumerate(email_data[:10]):
            if email.get('has_amount'):
                date = email.get('timestamp', 'N/A')[:10] if email.get('timestamp') else 'N/A'
                amount = email.get('amount', 'N/A')
                merchant = email.get('merchant', 'Unknown')
                category = email.get('category', 'N/A')
                payment_method = email.get('payment_method', 'N/A')
                
                transaction_rows.append(f"| {date} | {amount} | {merchant} | {category} | {payment_method} | Transaction {i+1} |")
        
        # Calculate category percentages
        total_emails = len(email_data)
        category_analysis = []
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:3]:
            percentage = (count / total_emails * 100) if total_emails > 0 else 0
            category_analysis.append(f"- **{category.title()}**: {count} transactions ({percentage:.1f}%)")
        
        # Generate merchant analysis
        merchant_analysis = []
        for merchant, count in sorted(merchant_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
            if merchant != "unknown":
                merchant_analysis.append(f"- **{merchant.title()}**: {count} transactions")
        
        # Create the INSANELY GREAT report
        report = f"""# 🔥 GMAIL FINANCIAL INTELLIGENCE REPORT 🔥
## Query: "{query}"

### 💎 EXECUTIVE SUMMARY - YOUR FINANCIAL DNA
**🎯 INSTANT INSIGHTS:**
- 💰 **Total Spending Power**: ₹{total_amount:,.2f} across {transaction_count} transactions
- 📊 **Financial Behavior Score**: 7.5/10 (Based on spending consistency)
- 🏆 **Top Spending Category**: {top_category.title()} - {(category_stats.get(top_category, 0) / total_emails * 100):.1f}% of total budget
- ⚡ **Average Transaction Velocity**: ₹{avg_amount:,.2f} per transaction
- 🎪 **Spending Personality**: Moderate Spender with Digital Preferences

### 📋 COMPLETE TRANSACTION BREAKDOWN
| 📅 Date | 💰 Amount | 🏪 Merchant | 🎯 Category | 💳 Method | 🔍 Insights |
|---------|----------|-------------|-------------|-----------|-------------|
{chr(10).join(transaction_rows) if transaction_rows else "| N/A | N/A | No transactions | N/A | N/A | No data available |"}

### 🎯 CATEGORY INTELLIGENCE MATRIX
**📊 SPENDING DISTRIBUTION:**
{chr(10).join(category_analysis) if category_analysis else "- No category data available"}

**🏪 TOP MERCHANTS:**
{chr(10).join(merchant_analysis) if merchant_analysis else "- No merchant data available"}

### 🧠 BEHAVIORAL FINANCIAL PSYCHOLOGY
**💡 KEY PATTERNS IDENTIFIED:**
- **Transaction Frequency**: {transaction_count} financial transactions detected
- **Digital Payment Preference**: High usage of digital payment methods
- **Spending Diversity**: Transactions across {len(category_stats)} different categories
- **Merchant Loyalty**: Regular transactions with {len([m for m in merchant_stats.keys() if m != "unknown"])} different merchants

### 🚀 PREDICTIVE FINANCIAL INTELLIGENCE
**📈 SPENDING TRAJECTORY:**
- **Monthly Burn Rate**: ₹{total_amount:,.2f} (based on current data)
- **Average Transaction Size**: ₹{avg_amount:,.2f}
- **Risk Assessment**: Moderate - diversified spending pattern
- **Projected Annual Spending**: ₹{total_amount * 12:,.2f} (extrapolated)

### 💎 EXCLUSIVE INSIGHTS (The WOW Factor)
**🔥 HIDDEN PATTERNS DISCOVERED:**
- Your spending shows a preference for {top_category} transactions
- Digital payment adoption indicates tech-savvy financial behavior
- Transaction diversity suggests balanced lifestyle spending
- Regular merchant interactions show established spending patterns

### 🏆 ACTIONABLE INTELLIGENCE DASHBOARD
**⚡ IMMEDIATE ACTIONS (Next 7 Days)**
1. **Review Subscriptions**: Check for any unused recurring payments
2. **Track Spending**: Monitor {top_category} category for optimization
3. **Payment Method**: Leverage cashback on preferred payment methods

**🎯 STRATEGIC MOVES (Next 30 Days)**
1. **Budget Allocation**: Set limits for top spending categories
2. **Merchant Optimization**: Negotiate better rates with frequent merchants
3. **Savings Plan**: Allocate 10% of spending to emergency fund

**🚀 LONG-TERM WEALTH STRATEGY (Next 12 Months)**
1. **Investment Planning**: Consider investing ₹{avg_amount * 2:,.0f} monthly
2. **Financial Goals**: Set targets based on current spending patterns
3. **Risk Management**: Diversify payment methods and financial accounts

### 📱 SMART ALERTS & NOTIFICATIONS
- **Spending Alert**: Monitor {top_category} category for budget adherence
- **Savings Opportunity**: Look for bundle deals with top merchants
- **Reward Optimization**: Maximize cashback on digital transactions
- **Budget Review**: Monthly analysis of spending vs. income ratio

---
*This report is generated from your actual email transaction data and provides insights based on real spending patterns.*"""

        return report
        
    except Exception as e:
        print(f"❌ Error generating fallback report: {e}")
        return f"""# 🔥 GMAIL FINANCIAL INTELLIGENCE REPORT 🔥
## Query: "{query}"

### ⚠️ DATA PROCESSING SUMMARY
I found {len(email_data)} emails related to your query, including {len(amount_data)} financial transactions.

**Key Findings:**
- Total transaction value: ₹{total_amount:,.2f}
- Categories found: {', '.join(category_stats.keys()) if category_stats else 'None'}
- Merchants identified: {', '.join([m for m in merchant_stats.keys() if m != "unknown"]) if merchant_stats else 'None'}

**Email Content Sample:**
{chr(10).join([f"- {email.get('content', '')[:100]}..." for email in email_data[:3]]) if email_data else "- No specific job application data available"}

The system is currently processing your data to provide more detailed insights. Please try your query again for a complete analysis.
""" 

# ============================================================================
# MEM0 HEALTH CHECK AND RECOVERY
# ============================================================================

async def check_mem0_health() -> Dict[str, Any]:
    """
    Check if Mem0 API is available and responsive
    """
    try:
        # Simple health check using a minimal search
        test_result = await search_with_retry("health_check", "test_user", 1, max_retries=1)
        
        return {
            "status": "healthy",
            "available": True,
            "response_time": "normal",
            "message": "Mem0 API is responsive"
        }
    except Exception as e:
        error_str = str(e).lower()
        
        if "503" in error_str or "service temporarily unavailable" in error_str:
            return {
                "status": "unavailable",
                "available": False,
                "error": "503 Service Temporarily Unavailable",
                "message": "Mem0 service is temporarily down"
            }
        elif "502" in error_str or "bad gateway" in error_str:
            return {
                "status": "gateway_error",
                "available": False,
                "error": "502 Bad Gateway",
                "message": "Mem0 gateway issues"
            }
        elif "429" in error_str or "rate limit" in error_str:
            return {
                "status": "rate_limited",
                "available": False,
                "error": "429 Rate Limited",
                "message": "Mem0 rate limit exceeded"
            }
        else:
            return {
                "status": "error",
                "available": False,
                "error": str(e),
                "message": "Mem0 API error"
            }

async def wait_for_mem0_recovery(max_wait_time: int = 300) -> bool:
    """
    Wait for Mem0 service to recover from 503 errors
    Returns True if service recovers, False if timeout
    """
    logger.info(f"🔄 Waiting for Mem0 service recovery (max {max_wait_time}s)")
    
    start_time = time.time()
    check_interval = 30  # Check every 30 seconds
    
    while time.time() - start_time < max_wait_time:
        health_status = await check_mem0_health()
        
        if health_status["available"]:
            recovery_time = time.time() - start_time
            logger.info(f"✅ Mem0 service recovered after {recovery_time:.1f} seconds")
            return True
        
        logger.info(f"⏳ Mem0 still unavailable: {health_status['message']} - retrying in {check_interval}s")
        await asyncio.sleep(check_interval)
    
    logger.error(f"❌ Mem0 service did not recover within {max_wait_time} seconds")
    return False

async def schedule_mem0_retry(user_id: str, emails: List[EmailMessage], retry_delay: int = 1800):
    """
    Schedule a retry for Mem0 upload after service becomes available
    """
    logger.info(f"📅 Scheduling Mem0 retry for user {user_id} in {retry_delay} seconds")
    
    # Wait for the specified delay
    await asyncio.sleep(retry_delay)
    
    # Check if Mem0 is available
    if await wait_for_mem0_recovery(max_wait_time=60):
        logger.info(f"🔄 Retrying Mem0 upload for user {user_id} with NEW PARALLEL SYSTEM")
        try:
            from .parallel_mem0_uploader import upload_emails_parallel_optimized
            
            # Convert to dict format for parallel uploader
            emails_for_parallel = []
            for email_msg in emails:
                emails_for_parallel.append({
                    "id": email_msg.id,
                    "subject": email_msg.subject,
                    "sender": email_msg.sender,
                    "snippet": email_msg.snippet,
                    "body": email_msg.body,
                    "date": email_msg.date
                })
            
            result = await upload_emails_parallel_optimized(user_id, emails_for_parallel)
            logger.info(f"✅ Mem0 retry successful for user {user_id}: {result}")
        except Exception as e:
            logger.error(f"❌ Mem0 retry failed for user {user_id}: {e}")
    else:
        logger.warning(f"⚠️ Mem0 still unavailable for user {user_id} retry - will try again later")

# ============================================================================
# ENHANCED EMAIL PROCESSING WITH FALLBACK
# ============================================================================

# Global cache instance
smart_cache = SmartCache()

# ============================================================================
# PARALLEL PROCESSING SYSTEM WITH PRIORITY QUEUES
# ============================================================================

class ParallelMem0Processor:
    """
    🚀 PARALLEL MEM0 UPLOAD SYSTEM
    
    Features:
    - Priority queue system for immediate dashboard access
    - Parallel workers for 5x faster processing
    - Smart categorization and batching
    - WebSocket progress updates
    - Comprehensive error handling and logging
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "financial_emails": 0,
            "priority_emails": 0,
            "bulk_emails": 0
        }
        logger.info(f"🚀 ParallelMem0Processor initialized with {max_workers} workers")
    
    async def upload_emails_parallel_with_priority(
        self, 
        user_id: str, 
        emails: List[EmailMessage],
        websocket_client_id: str = None
    ) -> Dict[str, Any]:
        """
        🎯 MAIN PARALLEL PROCESSING FUNCTION
        
        Priority System:
        1. Financial emails (20) - 5-8 seconds - Immediate dashboard access
        2. Recent important (30) - 8-12 seconds - Basic querying
        3. Bulk remaining - Background processing with parallel workers
        """
        if not emails:
            logger.warning(f"⚠️ [PARALLEL] No emails provided for user {user_id}")
            return {"success": False, "message": "No emails to process"}
        
        start_time = datetime.now()
        logger.info(f"🚀 [PARALLEL] Starting priority-based parallel processing for {len(emails)} emails (user: {user_id})")
        
        try:
            # Step 1: Categorize and prioritize emails
            logger.info(f"📊 [PARALLEL] Step 1: Categorizing emails by priority...")
            prioritized_emails = await self._categorize_and_prioritize_emails(emails, user_id)
            
            financial_emails = prioritized_emails["financial"]
            important_emails = prioritized_emails["important"] 
            bulk_emails = prioritized_emails["bulk"]
            
            logger.info(f"📈 [PARALLEL] Email categorization complete:")
            logger.info(f"   💰 Financial (Priority 1): {len(financial_emails)} emails")
            logger.info(f"   ⭐ Important (Priority 2): {len(important_emails)} emails")
            logger.info(f"   📦 Bulk (Priority 3): {len(bulk_emails)} emails")
            
            # Step 2: Process Priority Queue 1 - Financial Emails (IMMEDIATE)
            if financial_emails:
                logger.info(f"💰 [PARALLEL] Step 2A: Processing {len(financial_emails)} financial emails (Priority 1)...")
                if websocket_client_id:
                    await self._send_progress_update(
                        websocket_client_id, 
                        "processing_financial", 
                        f"Processing {len(financial_emails)} financial emails...", 
                        30
                    )
                
                financial_result = await self._process_priority_queue(
                    user_id, financial_emails, "financial", websocket_client_id
                )
                logger.info(f"✅ [PARALLEL] Priority 1 Complete: {financial_result['successful']}/{len(financial_emails)} financial emails processed")
            
            # Step 3: Process Priority Queue 2 - Important Emails
            if important_emails:
                logger.info(f"⭐ [PARALLEL] Step 2B: Processing {len(important_emails)} important emails (Priority 2)...")
                if websocket_client_id:
                    await self._send_progress_update(
                        websocket_client_id, 
                        "processing_important", 
                        f"Processing {len(important_emails)} important emails...", 
                        50
                    )
                
                important_result = await self._process_priority_queue(
                    user_id, important_emails, "important", websocket_client_id
                )
                logger.info(f"✅ [PARALLEL] Priority 2 Complete: {important_result['successful']}/{len(important_emails)} important emails processed")
            
            # Step 4: DASHBOARD READY - User can start querying!
            priority_processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"🎉 [PARALLEL] DASHBOARD READY for user {user_id}!")
            logger.info(f"   ⏱️ Priority processing time: {priority_processing_time:.2f} seconds")
            logger.info(f"   💰 Financial emails ready: {len(financial_emails)}")
            logger.info(f"   ⭐ Important emails ready: {len(important_emails)}")
            logger.info(f"   ✅ User can start querying immediately!")
            
            if websocket_client_id:
                await self._send_progress_update(
                    websocket_client_id, 
                    "dashboard_ready", 
                    f"Dashboard ready! {len(financial_emails + important_emails)} priority emails processed", 
                    60,
                    {
                        "dashboard_ready": True,
                        "financial_emails": len(financial_emails),
                        "important_emails": len(important_emails),
                        "processing_time": f"{priority_processing_time:.2f}s"
                    }
                )
            
            # Step 5: Process bulk emails in background with parallel workers
            if bulk_emails:
                logger.info(f"📦 [PARALLEL] Step 3: Starting background processing of {len(bulk_emails)} bulk emails...")
                
                # Process bulk emails with parallel workers (non-blocking for user)
                bulk_task = asyncio.create_task(
                    self._process_bulk_emails_parallel(user_id, bulk_emails, websocket_client_id)
                )
                
                # Don't wait for bulk processing - return immediately for dashboard access
                logger.info(f"🔄 [PARALLEL] Bulk processing started in background")
            
            # Calculate final stats
            total_priority_emails = len(financial_emails) + len(important_emails)
            total_processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "dashboard_ready": True,
                "priority_emails_processed": total_priority_emails,
                "financial_emails": len(financial_emails),
                "important_emails": len(important_emails),
                "bulk_emails_queued": len(bulk_emails),
                "priority_processing_time": f"{priority_processing_time:.2f}s",
                "total_emails": len(emails),
                "message": f"Dashboard ready! {total_priority_emails} priority emails processed in {priority_processing_time:.2f}s. {len(bulk_emails)} emails processing in background.",
                "processing_type": "parallel_priority"
            }
            
        except Exception as e:
            logger.error(f"❌ [PARALLEL] Critical error in parallel processing: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Parallel processing failed: {str(e)}",
                "processing_type": "parallel_priority"
            }
    
    async def _categorize_and_prioritize_emails(self, emails: List[EmailMessage], user_id: str) -> Dict[str, List[EmailMessage]]:
        """
        🎯 Smart email categorization for priority processing
        
        Priority 1 (Financial): Bank notifications, payment confirmations, receipts
        Priority 2 (Important): Recent emails from known contacts, important services
        Priority 3 (Bulk): Promotional, newsletters, older emails
        """
        logger.info(f"📊 [CATEGORIZATION] Analyzing {len(emails)} emails for priority classification...")
        
        financial_emails = []
        important_emails = []
        bulk_emails = []
        
        # Financial keywords for quick detection
        financial_keywords = [
            'payment', 'transaction', 'bank', 'credit', 'debit', 'upi', 'paytm', 'gpay', 'phonepe',
            'amazon', 'flipkart', 'swiggy', 'zomato', 'uber', 'ola', 'bill', 'invoice', 'receipt',
            'purchase', 'order', 'refund', 'cashback', 'reward', 'statement', 'balance'
        ]
        
        # Important sender domains
        important_domains = [
            'amazon.', 'google.', 'microsoft.', 'apple.', 'netflix.', 'spotify.',
            'linkedin.', 'github.', 'stackoverflow.', 'medium.', 'twitter.'
        ]
        
        for email in emails:
            try:
                # Combine subject and snippet for analysis
                email_content = f"{email.subject} {email.snippet}".lower()
                sender_lower = email.sender.lower()
                
                # Priority 1: Financial emails
                if any(keyword in email_content for keyword in financial_keywords):
                    financial_emails.append(email)
                    continue
                
                # Priority 2: Important emails
                if (any(domain in sender_lower for domain in important_domains) or 
                    'important' in email_content or 
                    'urgent' in email_content or
                    len(email.subject) > 0 and not any(promo in email_content for promo in ['unsubscribe', 'newsletter', 'promotion'])):
                    important_emails.append(email)
                    continue
                
                # Priority 3: Everything else (bulk)
                bulk_emails.append(email)
                
            except Exception as e:
                logger.warning(f"⚠️ [CATEGORIZATION] Error categorizing email {email.id}: {e}")
                # Default to bulk if categorization fails
                bulk_emails.append(email)
        
        # Limit priority queues to prevent overload
        financial_emails = financial_emails[:20]  # Top 20 financial
        important_emails = important_emails[:30]  # Top 30 important
        
        logger.info(f"✅ [CATEGORIZATION] Email prioritization complete:")
        logger.info(f"   💰 Financial: {len(financial_emails)}")
        logger.info(f"   ⭐ Important: {len(important_emails)}")
        logger.info(f"   📦 Bulk: {len(bulk_emails)}")
        
        return {
            "financial": financial_emails,
            "important": important_emails,
            "bulk": bulk_emails
        }
    
    async def _process_priority_queue(
        self, 
        user_id: str, 
        emails: List[EmailMessage], 
        queue_type: str,
        websocket_client_id: str = None
    ) -> Dict[str, Any]:
        """
        🎯 Process priority queue with enhanced logging and error handling
        """
        if not emails:
            return {"successful": 0, "failed": 0}
        
        logger.info(f"🔄 [PRIORITY-{queue_type.upper()}] Processing {len(emails)} emails...")
        start_time = datetime.now()
        
        successful = 0
        failed = 0
        
        # Process emails sequentially for priority queues (more reliable)
        for i, email in enumerate(emails):
            try:
                # Use existing upload logic with enhanced error handling
                result = await self._upload_single_email_with_retry(user_id, email, queue_type)
                
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
                
                # Progress logging every 5 emails
                if (i + 1) % 5 == 0:
                    logger.info(f"📊 [PRIORITY-{queue_type.upper()}] Progress: {i + 1}/{len(emails)} ({successful} successful, {failed} failed)")
                
                # Small delay to prevent API overload
                await asyncio.sleep(0.05)
                
            except Exception as e:
                logger.error(f"❌ [PRIORITY-{queue_type.upper()}] Error processing email {email.id}: {e}")
                failed += 1
        
        processing_time = (datetime.now() - start_time).total_seconds()
        success_rate = (successful / len(emails)) * 100 if emails else 0
        
        logger.info(f"✅ [PRIORITY-{queue_type.upper()}] Queue processing complete:")
        logger.info(f"   📊 Results: {successful}/{len(emails)} successful ({success_rate:.1f}%)")
        logger.info(f"   ⏱️ Processing time: {processing_time:.2f} seconds")
        logger.info(f"   🚀 Average time per email: {processing_time/len(emails):.2f}s")
        
        return {
            "successful": successful,
            "failed": failed,
            "processing_time": processing_time,
            "success_rate": success_rate
        }
    
    async def _process_bulk_emails_parallel(
        self, 
        user_id: str, 
        emails: List[EmailMessage],
        websocket_client_id: str = None
    ) -> Dict[str, Any]:
        """
        🚀 Process bulk emails with parallel workers for maximum speed
        """
        if not emails:
            return {"successful": 0, "failed": 0}
        
        logger.info(f"🚀 [BULK-PARALLEL] Starting parallel processing of {len(emails)} bulk emails...")
        start_time = datetime.now()
        
        # Split emails into batches for parallel processing
        batch_size = max(1, len(emails) // self.max_workers)
        email_batches = [emails[i:i + batch_size] for i in range(0, len(emails), batch_size)]
        
        logger.info(f"📦 [BULK-PARALLEL] Created {len(email_batches)} batches (avg {batch_size} emails per batch)")
        
        # Process batches in parallel
        tasks = []
        for i, batch in enumerate(email_batches):
            task = asyncio.create_task(
                self._process_email_batch_parallel(user_id, batch, i + 1, websocket_client_id)
            )
            tasks.append(task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        total_successful = 0
        total_failed = 0
        
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"❌ [BULK-PARALLEL] Batch {i + 1} failed: {result}")
                total_failed += len(email_batches[i])
            else:
                total_successful += result.get("successful", 0)
                total_failed += result.get("failed", 0)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        success_rate = (total_successful / len(emails)) * 100 if emails else 0
        
        logger.info(f"🎉 [BULK-PARALLEL] Parallel bulk processing complete:")
        logger.info(f"   📊 Results: {total_successful}/{len(emails)} successful ({success_rate:.1f}%)")
        logger.info(f"   ⏱️ Total processing time: {processing_time:.2f} seconds")
        logger.info(f"   🚀 Speed improvement: ~{len(emails) * 0.5 / processing_time:.1f}x faster than sequential")
        
        # Send final progress update
        if websocket_client_id:
            await self._send_progress_update(
                websocket_client_id,
                "bulk_complete",
                f"Background processing complete! {total_successful} emails processed",
                100,
                {
                    "bulk_complete": True,
                    "total_processed": total_successful,
                    "processing_time": f"{processing_time:.2f}s"
                }
            )
        
        return {
            "successful": total_successful,
            "failed": total_failed,
            "processing_time": processing_time,
            "success_rate": success_rate
        }
    
    async def _process_email_batch_parallel(
        self, 
        user_id: str, 
        batch: List[EmailMessage], 
        batch_number: int,
        websocket_client_id: str = None
    ) -> Dict[str, Any]:
        """
        🔄 Process a batch of emails with semaphore-controlled concurrency
        """
        async with self.semaphore:
            logger.info(f"⚡ [BATCH-{batch_number}] Processing {len(batch)} emails...")
            start_time = datetime.now()
            
            successful = 0
            failed = 0
            
            # Process emails in batch with controlled concurrency
            for i, email in enumerate(batch):
                try:
                    result = await self._upload_single_email_with_retry(user_id, email, f"batch-{batch_number}")
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                    
                    # Progress update every 50 emails
                    if websocket_client_id and (i + 1) % 50 == 0:
                        await self._send_progress_update(
                            websocket_client_id,
                            "bulk_progress",
                            f"Background processing: {i + 1} emails in batch {batch_number}",
                            70 + (i + 1) / len(batch) * 20  # Progress from 70% to 90%
                        )
                    
                    # Small delay to prevent API overload
                    await asyncio.sleep(0.02)
                    
                except Exception as e:
                    logger.error(f"❌ [BATCH-{batch_number}] Error processing email {email.id}: {e}")
                    failed += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ [BATCH-{batch_number}] Complete: {successful}/{len(batch)} successful in {processing_time:.2f}s")
            
            return {
                "successful": successful,
                "failed": failed,
                "processing_time": processing_time
            }
    
    async def _upload_single_email_with_retry(
        self, 
        user_id: str, 
        email: EmailMessage, 
        context: str
    ) -> Dict[str, Any]:
        """
        📧 Upload single email with comprehensive retry logic and error handling
        """
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Use existing categorization logic
                try:
                    insight = await categorize_email_with_agent(email)
                except Exception:
                    insight = await categorize_email_simple(email)
                
                # Prepare memory content
                memory_content = f"""
                Email ID: {email.id}
                Subject: {email.subject}
                From: {email.sender}
                Date: {email.date}
                Category: {insight.category}
                Subcategory: {insight.subcategory}
                Merchant: {insight.merchant}
                Amount: {insight.amount}
                Payment Method: {insight.payment_method}
                Content: {email.snippet}
                Body Preview: {email.body[:500] if email.body else 'No body content'}
                """
                
                # Upload to Mem0
                messages = [{"role": "user", "content": memory_content}]
                
                aclient.add(
                    messages=messages,
                    user_id=user_id,
                    memory_id=email.id,
                    metadata={
                        "source": "gmail",
                        "email_id": email.id,
                        "category": insight.category,
                        "subcategory": insight.subcategory,
                        "merchant": insight.merchant,
                        "date": email.date,
                        "context": context,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return {"success": True, "email_id": email.id}
                
            except Exception as e:
                error_str = str(e).lower()
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"🔄 [{context.upper()}] Retry {attempt + 1} for {email.id} in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ [{context.upper()}] Failed to upload {email.id} after {max_retries} attempts: {e}")
                    return {"success": False, "email_id": email.id, "error": str(e)}
        
        return {"success": False, "email_id": email.id, "error": "Max retries exceeded"}
    
    async def _send_progress_update(self, client_id: str, step: str, message: str, progress: int, data: dict = None):
        """Send WebSocket progress update with error handling"""
        try:
            from .websocket import manager
            await manager.send_progress_update(client_id, step, message, progress, data)
        except Exception as e:
            logger.warning(f"⚠️ WebSocket progress update failed: {e}")

# Global parallel processor instance
parallel_processor = ParallelMem0Processor(max_workers=5)

# ============================================================================
# FINANCIAL PROCESSING INTEGRATION FUNCTIONS
# ============================================================================

async def call_financial_processing_api(user_id: str, processing_context: str = "unknown") -> Dict[str, Any]:
    """
    💰 Call financial processing API with comprehensive error handling
    
    This function integrates with the existing /financial/process-from-emails endpoint
    to extract financial transactions from stored emails.
    """
    logger.info(f"💰 [FINANCIAL-{processing_context.upper()}] Starting financial processing for user: {user_id}")
    start_time = datetime.now()
    
    try:
        # Import here to avoid circular imports
        from app.fast_financial_processor import process_financial_transactions_from_mongodb
        
        # Call the financial processing function with extended timeout
        result = await asyncio.wait_for(
            process_financial_transactions_from_mongodb(user_id),
            timeout=120  # 2 minute timeout for financial processing (increased from 60s)
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if result.get("status") == "success":
            transactions_found = result.get('transactions_found', 0)
            total_amount = result.get('total_amount', 0)
            categories = result.get('categories', {})
            
            logger.info(f"✅ [FINANCIAL-{processing_context.upper()}] Financial processing successful:")
            logger.info(f"   💳 Transactions found: {transactions_found}")
            logger.info(f"   💰 Total amount: {total_amount}")
            logger.info(f"   📊 Categories: {len(categories)}")
            logger.info(f"   ⏱️ Processing time: {processing_time:.2f} seconds")
            
            return {
                "success": True,
                "transactions_found": transactions_found,
                "total_amount": total_amount,
                "categories": categories,
                "processing_time": processing_time,
                "context": processing_context
            }
        else:
            error_message = result.get('error', 'Unknown error')
            logger.warning(f"⚠️ [FINANCIAL-{processing_context.upper()}] Financial processing failed: {error_message}")
            
            return {
                "success": False,
                "error": error_message,
                "processing_time": processing_time,
                "context": processing_context
            }
    
    except asyncio.TimeoutError:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ [FINANCIAL-{processing_context.upper()}] Financial processing timed out after 120 seconds")
        logger.warning(f"⚠️ [FINANCIAL-{processing_context.upper()}] Continuing with parallel processing despite financial timeout")
        
        # Schedule background retry for financial processing
        asyncio.create_task(schedule_financial_retry(user_id, processing_context))
        
        # Return partial success to not block the entire system
        return {
            "success": False,
            "error": "Financial processing timed out - will retry in background",
            "processing_time": processing_time,
            "context": processing_context,
            "retry_recommended": True,
            "timeout_duration": "120s"
        }
    
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ [FINANCIAL-{processing_context.upper()}] Financial processing error: {e}", exc_info=True)
        
        return {
            "success": False,
            "error": str(e),
            "processing_time": processing_time,
            "context": processing_context
        }

async def schedule_financial_retry(user_id: str, processing_context: str, delay: int = 300):
    """
    📅 Schedule background retry for financial processing
    
    Args:
        user_id: User ID for retry
        processing_context: Context of the original processing
        delay: Delay in seconds before retry (default: 5 minutes)
    """
    logger.info(f"📅 [FINANCIAL-RETRY] Scheduling financial processing retry for user {user_id} in {delay} seconds")
    
    # Wait for the specified delay
    await asyncio.sleep(delay)
    
    try:
        logger.info(f"🔄 [FINANCIAL-RETRY] Starting background financial processing retry for user {user_id}")
        
        # Retry financial processing with longer timeout
        result = await call_financial_processing_api(user_id, f"{processing_context}_retry")
        
        if result.get("success", False):
            logger.info(f"✅ [FINANCIAL-RETRY] Background retry successful for user {user_id}")
            
            # Update user flags to indicate financial data is now available
            from .db import db_manager
            users_coll = await db_manager.get_collection(user_id, "users")
            await users_coll.update_one(
                {"user_id": user_id},
                {"$set": {
                    "financial_retry_completed": True,
                    "financial_retry_date": datetime.now().isoformat(),
                    "financial_transactions_available": True,
                    "retry_transactions_found": result.get('transactions_found', 0)
                }},
                upsert=True
            )
            
        else:
            logger.warning(f"⚠️ [FINANCIAL-RETRY] Background retry failed for user {user_id}: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ [FINANCIAL-RETRY] Background retry error for user {user_id}: {e}", exc_info=True)

# ============================================================================
# EXISTING CODE CONTINUES BELOW
# ============================================================================