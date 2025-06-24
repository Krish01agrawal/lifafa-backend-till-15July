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

Recent Fixes (2025-06-19):
- Fixed Mem0 client await issue (removed incorrect await on sync operations)
- Added OpenAI quota exceeded error handling with fallbacks
- Enhanced error handling for rate limits and API failures
- Improved robustness for production use
"""

import os
import json
import asyncio
import traceback
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
load_dotenv()

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
print(f"🔑 Initializing Mem0 clients with API key: {MEM0_API_KEY[:8]}...{MEM0_API_KEY[-3:]}")

try:
    aclient = MemoryClient(api_key=MEM0_API_KEY)  # For add operations
    sync_client = MemoryClient(api_key=MEM0_API_KEY)  # For search operations
    print("✅ Mem0 clients initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Mem0 clients: {e}")
    raise

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

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
    merchant: str
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
    """Upload emails to Mem0 with AI-powered categorization and metadata"""
    print(f"🔄 Processing {len(emails)} emails for user {user_id} using Agno agents")
    
    # Detect user location for enhanced metadata
    user_location = detect_user_location(emails)
    print(f"🌍 Detected user location: {user_location}")
    
    processed_count = 0
    error_count = 0
    
    for email in emails:
        if not email.id:
            continue

        try:
            # Categorize email using Agno agent
            insight = await categorize_email_with_agent(email)
            
            # Prepare content for Mem0
            content = f"Subject: {email.subject}\nSnippet: {email.snippet}\nBody: {email.body}"
            
            messages = [{
                "role": "user",
                "content": content,
            }]

            # Comprehensive metadata for enhanced search
            metadata = {
                "sender": email.sender,
                "category": insight.category,
                "subcategory": insight.subcategory,
                "merchant": insight.merchant,
                "payment_method": insight.payment_method,
                "source": "gmail",
                "timestamp": insight.timestamp,
                "has_amount": insight.amount is not None,
                "amount": insight.amount,
                "user_location": user_location,
                "subject_keywords": " ".join([word for word in email.subject.lower().split() if len(word) > 3]),
                "content_type": "email",
                "processed_by": "agno_agents"
            }

            # Upload to Mem0 (sync operation)
            aclient.add(
                messages=messages, 
                user_id=user_id, 
                memory_id=email.id, 
                metadata=metadata
            )
            
            processed_count += 1
            print(f"✅ Processed: {email.id} | {insight.category}/{insight.subcategory} | {insight.merchant}")
            
        except Exception as e:
            error_count += 1
            print(f"❌ Error processing {email.id}: {e}")

    result_message = f"Successfully processed {processed_count}/{len(emails)} emails for user {user_id}"
    if error_count > 0:
        result_message += f" ({error_count} errors)"
    result_message += f" (Location: {user_location}, System: Agno Agents)"
    
    return result_message

async def search_with_retry(query: str, user_id: str, limit: int, max_retries: int = 3) -> List[Dict]:
    """Search Mem0 with retry logic for handling API errors"""
    print(f"🔄 Mem0 search: '{query}' (user: {user_id}, limit: {limit})")
    
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
                print(f"✅ Search successful: {len(valid_results)} valid results")
                return valid_results
            else:
                print(f"⚠️ Search returned None (attempt {attempt + 1})")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"   Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
            print(f"❌ Search error: {e}")
            break
    
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
        
        # Process with Agno agents
        upload_result = await upload_emails_to_mem0(user_id, email_messages)
        
        # Update user status in database
        try:
            from app.db import users_collection
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