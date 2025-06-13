"""
Gmail Email Agent System - Agno-powered Email Intelligence

This module implements a comprehensive email management system using Agno agents:

ARCHITECTURE:
- GmailAgentOrchestrator: Master coordinator that manages email processing and queries
- EmailProcessorAgent: Specializes in email categorization, extraction, and Mem0 storage
- EmailQueryAgent: Handles intelligent email search with sub-query generation and LLM enhancement

FEATURES:
- Smart email categorization (banking, food, utilities, shopping, etc.)
- Intelligent query processing with intent analysis
- Comprehensive email analytics and insights
- Semantic memory storage with Mem0
- Gmail API integration ready
- MongoDB backup storage
- Advanced financial data extraction

USAGE:
- process_gmail_data(user_id, gmail_emails) -> Process emails from Gmail API
- query_email_database(user_id, query) -> Query emails with natural language
- get_email_analytics(user_id) -> Generate comprehensive email analytics

This replaces standalone functions with intelligent Agno agents for better 
coordination, context awareness, and enhanced user experience.
"""

import os
import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Agno and AI imports
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.team.team import Team
from agno.tools.reasoning import ReasoningTools

# Memory and database imports
from mem0 import AsyncMemoryClient, MemoryClient
import openai

# Environment Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

if not MEM0_API_KEY:
    raise ValueError("MEM0_API_KEY environment variable not set")

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize Mem0 clients
aclient = AsyncMemoryClient()
sync_client = MemoryClient()

# Pydantic Models for Data Validation
class EmailMessage(BaseModel):
    id: str
    subject: str = ""
    sender: str = ""
    snippet: str = ""
    body: str = ""
    date: Optional[str] = None

class EmailUploadRequest(BaseModel):
    user_id: str
    emails: List[EmailMessage]

class EmailQueryRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 1145
    category: Optional[str] = None

class EmailInsight(BaseModel):
    category: str
    subcategory: str
    merchant: str
    amount: Optional[str] = None
    payment_method: str
    timestamp: Optional[str] = None

# ************* Team Members *************

# Email Processing Agent
email_processor_agent = Agent(
    name="Email Processor Agent",
    role="Process and categorize email data with Mem0 storage",
    agent_id="email_processor",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "You are an expert email processor that categorizes and extracts insights from email data.",
        "Process emails and store them in Mem0 with proper categorization and metadata.",
        "Handle Gmail data and prepare it for intelligent storage and retrieval.",
        "Always provide detailed categorization and extract relevant financial information.",
        "Categorize emails into: banking, food, utilities, shopping, entertainment, investment, reminders, orders, general.",
        "Extract amounts, merchants, payment methods, and timestamps when available.",
        "Use reasoning to understand email context and provide accurate categorization.",
    ],
    markdown=True,
)

# Email Query Agent
email_query_agent = Agent(
    name="Email Query Agent", 
    role="Handle intelligent email search and analysis",
    agent_id="email_query",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "You are an intelligent email query agent that helps users find and analyze their email data.",
        "Use advanced search techniques including sub-query generation and semantic search.",
        "Provide comprehensive, well-formatted responses with insights and analytics.",
        "Excel at understanding user intent and finding relevant emails from Mem0 storage.",
        "Generate multiple related sub-queries to improve search coverage.",
        "Format responses clearly with sections and actionable insights.",
        "Use reasoning to understand complex queries and provide accurate results.",
    ],
    markdown=True,
)

# Email Analytics Agent
email_analytics_agent = Agent(
    name="Email Analytics Agent",
    role="Generate comprehensive email insights and reports", 
    agent_id="email_analytics",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "You are an email analytics specialist that generates comprehensive insights and reports.",
        "Analyze email patterns, spending habits, subscription management, and financial trends.",
        "Create detailed reports with spending summaries, category breakdowns, and recommendations.",
        "Identify patterns in user behavior, payment methods, and merchant preferences.",
        "Provide actionable insights for better email and financial management.",
        "Use tables and structured formats to present data clearly.",
        "Focus on delivering data-driven observations and recommendations.",
        "Use reasoning to identify trends and provide strategic insights.",
    ],
    markdown=True,
)

# *******************************

# ************* Gmail Intelligence Team *************
gmail_intelligence_team = Team(
    name="Gmail Intelligence Team",
    mode="coordinate", 
    team_id="gmail_intelligence_team",
    model=OpenAIChat(id="gpt-4o"),
    members=[
        email_processor_agent,
        email_query_agent,
        email_analytics_agent
    ],
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "You are a Gmail Intelligence Team that provides comprehensive email management and analytics.",
        "Collaborate to process, analyze, and provide insights from Gmail email data using Mem0 memory.",
        "Use the Email Processor Agent for categorizing and storing emails with proper metadata.",
        "Use the Email Query Agent for intelligent search and retrieval of email information.",
        "Use the Email Analytics Agent for generating comprehensive reports and insights.",
        "Leverage Mem0 memory for persistent, semantic storage and retrieval of email data.",
        "Provide structured, actionable responses with clear categorization and insights.",
        "Focus on financial insights, spending patterns, subscription management, and email organization.",
        "Ensure all responses are well-formatted, comprehensive, and user-friendly.",
        "Use reasoning to provide intelligent coordination between agents.",
        "Only output the final consolidated response, not individual agent responses.",
    ],
    markdown=True,
    success_criteria="The team has provided comprehensive email intelligence with proper categorization, storage in Mem0, intelligent search capabilities, and actionable analytics insights.",
)
# *******************************

# ************* Helper Functions *************

def detect_user_location(emails: List[EmailMessage]) -> str:
    """Detect user's primary location based on merchant patterns"""
    indian_merchants = ['swiggy', 'zomato', 'flipkart', 'myntra', 'paytm', 'phonepe', 'gpay', 'bescom', 'bsnl', 'airtel', 'jio']
    us_merchants = ['walmart', 'target', 'bestbuy', 'amazon.com', 'apple.com', 'google.com', 'microsoft.com']
    uk_merchants = ['tesco', 'sainsbury', 'amazon.co.uk', 'argos']
    
    indian_count = 0
    us_count = 0
    uk_count = 0
    
    for email in emails:
        content = f"{email.sender.lower()} {email.subject.lower()} {email.snippet.lower()}"
        
        for merchant in indian_merchants:
            if merchant in content:
                indian_count += 1
                break
        
        for merchant in us_merchants:
            if merchant in content:
                us_count += 1
                break
                
        for merchant in uk_merchants:
            if merchant in content:
                uk_count += 1
                break
    
    if indian_count >= us_count and indian_count >= uk_count:
        return "India"
    elif us_count >= uk_count:
        return "US"
    else:
        return "UK"

def extract_amount_with_currency(content: str) -> tuple:
    """Extract amount with currency symbol from email content"""
    # Try different currency patterns
    patterns = [
        (r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', '₹'),  # Indian Rupees
        (r'\$\s*(\d+(?:,\d+)*(?:\.\d+)?)', '$'),  # US Dollars
        (r'€\s*(\d+(?:,\d+)*(?:\.\d+)?)', '€'),  # Euros
        (r'£\s*(\d+(?:,\d+)*(?:\.\d+)?)', '£'),  # British Pounds
        (r'(\d+(?:,\d+)*(?:\.\d+)?)\s*USD', '$'), # USD format
        (r'(\d+(?:,\d+)*(?:\.\d+)?)\s*INR', '₹'), # INR format
    ]
    
    for pattern, currency in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            amount = match.group(1).replace(',', '')
            return amount, currency
    
    return None, None

async def categorize_email(email: EmailMessage) -> EmailInsight:
    """Categorize email and extract insights"""
    subject_lower = email.subject.lower()
    sender_lower = email.sender.lower()
    content_lower = f"{subject_lower} {email.snippet.lower()} {email.body.lower()}"

    # Extract amount with currency
    amount, currency = extract_amount_with_currency(content_lower)
    if amount and currency:
        amount = f"{currency}{amount}"
    else:
        amount = None

    # Default values
    category = "general"
    subcategory = "misc"
    payment_method = "unknown"
    merchant = "unknown"

    # Detect payment methods
    if any(method in content_lower for method in ["paytm", "gpay", "phonepe", "upi"]):
        payment_method = "digital_wallet"
    elif any(method in content_lower for method in ["credit card", "debit card", "card"]):
        payment_method = "card"
    elif any(method in content_lower for method in ["bank transfer", "neft", "rtgs"]):
        payment_method = "bank_transfer"

    # Comprehensive category detection
    if any(keyword in content_lower for keyword in ["statement", "account summary", "monthly statement"]):
        category = "banking"
        subcategory = "statement"
    elif any(keyword in content_lower for keyword in ["reminder", "due", "payment due", "overdue"]):
        category = "reminders"
        if any(keyword in content_lower for keyword in ["emi", "loan", "credit card"]):
            subcategory = "payment_reminder"
            merchant = "bank"
        elif any(keyword in content_lower for keyword in ["bill", "electricity", "utility"]):
            subcategory = "bill_reminder"
            merchant = "utility_company"
        elif any(keyword in content_lower for keyword in ["subscription", "renewal"]):
            subcategory = "subscription_reminder"
        else:
            subcategory = "general_reminder"
    elif any(keyword in content_lower for keyword in ["electricity", "power", "bescom", "mseb", "kseb"]):
        category = "utilities"
        subcategory = "electricity"
        merchant = "electricity_board"
    elif any(vendor in sender_lower for vendor in ["swiggy", "zomato", "ubereats", "dominos"]):
        category = "food"
        subcategory = "delivery"
        merchant = next((vendor for vendor in ["swiggy", "zomato", "ubereats", "dominos"] if vendor in sender_lower), "food_delivery")
    elif any(vendor in sender_lower for vendor in ["flipkart", "amazon", "myntra", "ajio"]):
        category = "shopping"
        subcategory = "ecommerce"
        merchant = next((vendor for vendor in ["flipkart", "amazon", "myntra", "ajio"] if vendor in sender_lower), "ecommerce")
    elif any(keyword in content_lower for keyword in ["netflix", "spotify", "prime", "subscription"]):
        category = "entertainment"
        subcategory = "subscription"
    elif any(keyword in content_lower for keyword in ["sip", "mutual fund", "investment"]):
        category = "investment"
        subcategory = "mutual_fund"
    elif "order" in subject_lower:
        category = "orders"
        subcategory = "general"

    # Parse timestamp
    timestamp = None
    if email.date:
        try:
            timestamp = datetime.strptime(email.date, "%Y-%m-%dT%H:%M:%S%z").isoformat()
        except:
            timestamp = None

    return EmailInsight(
        category=category,
        subcategory=subcategory,
        merchant=merchant,
        amount=amount,
        payment_method=payment_method,
        timestamp=timestamp
    )

async def upload_emails_to_mem0(user_id: str, emails: List[EmailMessage]) -> str:
    """Upload emails to Mem0 with categorization"""
    print(f"🔄 Processing {len(emails)} emails for user {user_id}")
    
    # Detect user location for better currency handling
    user_location = detect_user_location(emails)
    print(f"🌍 Detected user location: {user_location}")
    
    processed_count = 0
    for email in emails:
        if not email.id:
            continue

        # Categorize email
        insight = await categorize_email(email)
        
        # Prepare content for Mem0
        content = f"Subject: {email.subject}\nSnippet: {email.snippet}\nBody: {email.body}"
        
        messages = [{
            "role": "user",
            "content": content,
        }]

        # Comprehensive metadata
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
            "content_type": "email"
        }

        try:
            await aclient.add(
                messages=messages, 
                user_id=user_id, 
                memory_id=email.id, 
                metadata=metadata
            )
            processed_count += 1
            print(f"✅ Processed: {email.id} | {insight.category}/{insight.subcategory} | {insight.merchant} | {insight.amount}")
        except Exception as e:
            print(f"❌ Error processing {email.id}: {e}")

    return f"Successfully processed {processed_count}/{len(emails)} emails for user {user_id} (Location: {user_location})"

async def search_emails_in_mem0(user_id: str, query: str, limit: int = 500) -> List[Dict]:
    """Search emails in Mem0 memory with comprehensive search strategy"""
    try:
        # Primary search with original query
        results = sync_client.search(
            query=query,
            user_id=user_id,
            limit=limit,
            filters={"metadata.source": "gmail"},
            keyword_search=True,
            rerank=True,
            filter_memories=False
        )
        
        # If we get fewer results than expected, try broader searches
        if len(results) < 50:  # If we have fewer than 50 results, search more broadly
            broader_queries = []
            
            # Generate broader search terms based on the original query
            if any(term in query.lower() for term in ["food", "order", "delivery", "restaurant"]):
                broader_queries.extend(["food", "delivery", "order", "restaurant", "swiggy", "zomato", "ubereats", "dominos"])
            
            if any(term in query.lower() for term in ["upi", "payment", "transaction"]):
                broader_queries.extend(["upi", "payment", "paid", "transaction", "gpay", "phonepe", "paytm"])
            
            if any(term in query.lower() for term in ["may", "april", "2025"]):
                broader_queries.extend(["may 2025", "april 2025", "2025"])
            
            if any(term in query.lower() for term in ["spending", "expense", "money"]):
                broader_queries.extend(["amount", "rupees", "₹", "paid", "cost", "price"])
            
            # Perform additional searches with broader terms
            all_results = results.copy() if results else []
            seen_memories = set()
            
            # Add existing results to seen set
            for result in all_results:
                seen_memories.add(result.get('memory', ''))
            
            for broader_query in broader_queries:
                try:
                    broader_results = sync_client.search(
                        query=broader_query,
                        user_id=user_id,
                        limit=200,  # Smaller limit per broader query
                        filters={"metadata.source": "gmail"},
                        keyword_search=True,
                        rerank=True,
                        filter_memories=False
                    )
                    
                    # Add unique results
                    if broader_results:
                        for result in broader_results:
                            memory_text = result.get('memory', '')
                            if memory_text not in seen_memories:
                                all_results.append(result)
                                seen_memories.add(memory_text)
                                
                except Exception as e:
                    print(f"❌ Broader search error for '{broader_query}': {e}")
            
            results = all_results
        
        print(f"🔍 Search for '{query}': Found {len(results)} total results")
        return results if results else []
        
    except Exception as e:
        print(f"❌ Search error for '{query}': {e}")
        return []

# ************* Team Interface Functions *************

async def process_gmail_data(user_id: str, gmail_emails: List[Dict]) -> Dict[str, Any]:
    """Process Gmail data using Gmail Intelligence Team"""
    try:
        print(f"🎯 Gmail Intelligence Team: Processing {len(gmail_emails)} emails for user {user_id}")
        
        # Convert to EmailMessage objects
        emails = [EmailMessage(**email) for email in gmail_emails]
        
        # Upload to Mem0
        upload_result = await upload_emails_to_mem0(user_id, emails)
        
        # Use team to generate processing summary
        team_prompt = f"""
        Analyze the Gmail data processing results with location-aware currency intelligence:
        
        - User ID: {user_id}
        - Total emails processed: {len(gmail_emails)}
        - Processing result: {upload_result}
        - Location Detection: Auto-detected user location for appropriate currency handling
        - Currency Intelligence: Preserves original currency symbols (₹, $, €, £) from emails
        
        Provide a comprehensive processing summary with:
        1. Processing statistics and success rate
        2. Location detection results and currency patterns found
        3. Category insights discovered from the emails
        4. Currency breakdown (domestic vs international transactions)
        5. Key patterns and trends identified
        6. Actionable recommendations for the user
        7. Next steps for email management
        
        Format as a structured, professional report with clear sections.
        """
        
        team_response = gmail_intelligence_team.run(team_prompt)
        
        return {
            "status": "success",
            "processed_emails": len(gmail_emails),
            "user_id": user_id,
            "upload_result": upload_result,
            "team_analysis": team_response.content if hasattr(team_response, 'content') else str(team_response),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Gmail Intelligence Team processing error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

async def query_email_database(user_id: str, query: str, limit: int = 1000, category: str = None) -> Dict[str, Any]:
    """Query email database using Gmail Intelligence Team with comprehensive search"""
    try:
        print(f"🔍 Gmail Intelligence Team: Processing query '{query}' for user {user_id}")
        
        # Use higher limit and comprehensive search
        search_results = await search_emails_in_mem0(user_id, query, limit)
        
        # If still low results, try category-based searches
        if len(search_results) < 20 and not category:
            print(f"🔄 Low results ({len(search_results)}), trying category-based searches...")
            
            category_searches = {
                "food_orders": ["food", "delivery", "order", "restaurant", "swiggy", "zomato", "meal"],
                "payments": ["payment", "paid", "upi", "transaction", "amount", "rupees"],
                "subscriptions": ["subscription", "renewal", "netflix", "spotify", "prime"],
                "shopping": ["shopping", "purchase", "amazon", "flipkart", "order"],
                "bills": ["bill", "electricity", "utility", "reminder", "due"]
            }
            
            all_results = search_results.copy()
            seen_memories = set(result.get('memory', '') for result in all_results)
            
            for category_name, terms in category_searches.items():
                for term in terms:
                    try:
                        cat_results = sync_client.search(
                            query=term,
                            user_id=user_id,
                            limit=100,
                            filters={"metadata.source": "gmail"},
                            keyword_search=True,
                            rerank=True,
                            filter_memories=False
                        )
                        
                        if cat_results:
                            for result in cat_results:
                                memory_text = result.get('memory', '')
                                if memory_text not in seen_memories:
                                    all_results.append(result)
                                    seen_memories.add(memory_text)
                                    
                    except Exception as e:
                        print(f"❌ Category search error for '{term}': {e}")
            
            search_results = all_results
            print(f"🔍 After category searches: Found {len(search_results)} total results")
        
        # Use team to process query with search results
        team_prompt = f"""
        You are a DATA-FOCUSED FINANCIAL ANALYST. Your PRIMARY job is to extract and present ACTUAL TRANSACTION DATA from emails in a visually stunning, attention-grabbing format. Focus on REAL DATA, not generic insights.

        User Query: "{query}"
        User ID: {user_id}
        Total Search Results: {len(search_results)}
        
        ACTUAL EMAIL DATA FROM MEM0:
        {json.dumps(search_results, indent=2) if search_results else "No email data found"}

        CRITICAL REQUIREMENTS - EXTRACT REAL NUMBERS:

        ## 💰 ACTUAL TRANSACTION DATA TABLE
        Extract and present EVERY transaction with complete details (preserve original currency symbols):
        
        | Date | Time | Merchant/Receiver | Amount | Payment Method | Category | Transaction ID | Purpose |
        |------|------|-------------------|--------|----------------|----------|----------------|---------|
        
        IMPORTANT: Fill this table with ACTUAL data from the emails above. Extract real dates, real merchant names, real amounts (₹299, ₹649, etc.), real payment methods from the email content.

        ## 📊 REAL SPENDING BREAKDOWN (with exact amounts in original currencies)
        **Primary Currency Totals (Calculate from actual email data):**
        - **Total Domestic Spending**: [Calculate actual sum from all INR transactions found]
        - **Food Delivery**: [Calculate actual sum] ([Count actual transactions]) - List each merchant with real amounts
        - **Subscriptions**: [Calculate actual sum] ([Count actual services]) - List each service with real amounts
        - **Shopping**: [Calculate actual sum] ([Count actual purchases]) - List each merchant with real amounts
        - **Bills & Utilities**: [Calculate actual sum] - List each bill with real amounts
        - **Transportation**: [Calculate actual sum] - List each ride with real amounts
        
        **International Transactions (if any):**
        - **USD Transactions**: [Calculate actual sum] ([Count actual transactions]) - List actual merchants
        - **EUR Transactions**: [Calculate actual sum] ([Count actual transactions]) - List actual merchants

        ## 📅 CHRONOLOGICAL TRANSACTION TIMELINE
        Show transactions in date order with full details (preserve original currencies):
        
        Extract ACTUAL dates and amounts from the email data above. Do not use placeholders.
        
        **May 2025:** (List all actual May 2025 transactions found)
        **April 2025:** (List all actual April 2025 transactions found)

        ## 🏪 MERCHANT-WISE SPENDING ANALYSIS
        For each merchant found in the email data, calculate:
        - Total: [Actual sum of all transactions for this merchant]
        - Count: [Actual number of transactions]
        - Average: [Actual total ÷ actual count]
        - Most expensive: [Actual highest amount] on [actual date]

        ## 💳 PAYMENT METHOD BREAKDOWN
        Count and sum actual transactions by payment method:
        - **UPI Transactions**: [Actual sum] ([Actual count])
        - **Credit Card**: [Actual sum] ([Actual count])
        - **Debit Card**: [Actual sum] ([Actual count])
        - **Net Banking**: [Actual sum] ([Actual count])

        ## 🎯 DATA-DRIVEN INSIGHTS (based on actual numbers)
        1. **Highest Single Transaction**: [Find actual highest amount] ([Actual merchant] on [actual date])
        2. **Most Frequent Merchant**: [Count transactions per merchant, find highest]
        3. **Peak Spending Day**: [Calculate daily totals, find highest]
        4. **Average Daily Spending**: [Total spending ÷ number of days with transactions]
        5. **Weekend vs Weekday**: [Calculate actual weekend total vs weekday total]

        MANDATORY CALCULATION RULES:
        1. Extract EXACT amounts from email content (₹299, ₹649, etc.) - NO PLACEHOLDERS
        2. Calculate REAL totals by adding up actual amounts found
        3. Count ACTUAL number of transactions, not estimates
        4. Show REAL dates from email timestamps
        5. List ACTUAL merchant names from email senders/content
        6. Calculate REAL averages using actual numbers (total ÷ count)
        7. If no data available, clearly state "No transaction data found" - DO NOT use XXX or placeholders

        EXAMPLE OF CORRECT OUTPUT:
        - Food Delivery: ₹1,148 (4 transactions) - Swiggy: ₹299, Zomato: ₹850, etc.
        - NOT: Food Delivery: ₹X,XXX (X transactions) - Swiggy: ₹XXX, Zomato: ₹XXX

        ## 🔍 TRANSACTION SEARCH RESULTS
        Show exactly what was found for the user's query with complete details and real numbers.

        If no transaction data is available, clearly state:
        "❌ **No transaction data found for your query.** 
        
        To get detailed transaction analysis:
        1. Upload your Gmail emails first using the 'upload' command
        2. Ensure emails contain transaction details (amounts, dates, merchants)
        3. Try broader search terms like 'UPI', 'payment', 'order', or specific merchant names"

        IMPORTANT: Process ALL {len(search_results)} search results, extract real numbers, calculate actual totals. NO PLACEHOLDERS ALLOWED.
        """
        
        team_response = gmail_intelligence_team.run(team_prompt)
        
        return {
            "status": "success",
            "user_id": user_id,
            "query": query,
            "results_count": len(search_results),
            "team_response": team_response.content if hasattr(team_response, 'content') else str(team_response),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Gmail Intelligence Team query error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }

async def get_email_analytics(user_id: str) -> Dict[str, Any]:
    """Generate comprehensive email analytics using Gmail Intelligence Team"""
    try:
        print(f"📊 Gmail Intelligence Team: Generating analytics for user {user_id}")
        
        # Query different aspects of user's emails from Mem0 with broader search terms and higher limits
        analytics_queries = [
            "spending expenses money amount rupees payment paid",
            "subscription renewal netflix spotify amazon prime service",
            "payment reminder bill due electricity utility water gas",
            "food delivery swiggy zomato ubereats order restaurant meal",
            "shopping ecommerce flipkart amazon myntra purchase buy",
            "banking financial transaction credit debit card bank",
            "entertainment movie ticket bookmyshow cinema theater",
            "travel booking flight hotel ola uber cab taxi",
            "investment mutual fund sip trading stock market",
            "insurance premium policy payment health life",
            "upi phonepe gpay paytm digital wallet",
            "order delivery purchase buy paid amount",
            "may 2025 april 2025 march 2025 recent transactions",
            "rupees ₹ amount cost price total"
        ]
        
        analytics_data = {}
        all_unique_results = []
        seen_memories = set()
        
        for query in analytics_queries:
            print(f"🔍 Searching for: {query}")
            results = await search_emails_in_mem0(user_id, query, 300)  # Higher limit per query
            analytics_data[query] = results
            
            # Collect all unique results
            if results:
                for result in results:
                    memory_text = result.get('memory', '')
                    if memory_text not in seen_memories:
                        all_unique_results.append(result)
                        seen_memories.add(memory_text)
        
        print(f"📊 Total unique results collected: {len(all_unique_results)}")
        
        # Use team to generate comprehensive analytics report
        team_prompt = f"""
        You are a MASTER DATA ANALYST specializing in extracting and presenting REAL TRANSACTION DATA from emails. Your job is to create a comprehensive, data-rich report that focuses on ACTUAL NUMBERS, DATES, AMOUNTS, and MERCHANTS - not generic insights.

        COMPLETE EMAIL TRANSACTION DATA: {json.dumps(analytics_data, indent=2)}
        TOTAL UNIQUE TRANSACTIONS FOUND: {len(all_unique_results)}

        CREATE A COMPREHENSIVE DATA-FOCUSED REPORT WITH REAL NUMBERS:

        # 💰 COMPLETE FINANCIAL DATA DASHBOARD

        ## 📊 MASTER TRANSACTION TABLE
        Extract and display ALL transactions with complete details (calculate actual amounts):
        
        | Date | Time | Merchant | Amount | Category | Payment Method | Purpose/Item | Status |
        |------|------|----------|--------|----------|----------------|--------------|--------|
        
        IMPORTANT: Fill this table with ACTUAL data from the {len(all_unique_results)} transactions found. Extract real dates, real merchant names, real amounts, real payment methods.

        ## 💸 EXACT SPENDING TOTALS BY CATEGORY (Calculate actual sums)
        **Food Delivery & Dining:**
        - Swiggy: [Calculate actual sum] ([Count actual orders]) - Last: [Actual amount] on [actual date]
        - Zomato: [Calculate actual sum] ([Count actual orders]) - Last: [Actual amount] on [actual date]
        - Restaurant bills: [Calculate actual sum] ([Count actual transactions])
        - **Category Total: [Calculate actual sum of all food transactions]**

        **Subscriptions & Services:**
        - Netflix: [Find actual amount]/month ([Plan type]) - Next: [actual date]
        - Spotify: [Find actual amount]/month ([Plan type]) - Next: [actual date]
        - Amazon Prime: [Find actual amount]/year - Expires: [actual date]
        - **Category Total: [Calculate actual sum of all subscription transactions]**

        **Shopping & E-commerce:**
        - Amazon: [Calculate actual sum] ([Count actual orders]) - Biggest: [Actual highest amount] ([Item name])
        - Flipkart: [Calculate actual sum] ([Count actual orders])
        - Myntra: [Calculate actual sum] ([Count actual orders])
        - **Category Total: [Calculate actual sum of all shopping transactions]**

        **Bills & Utilities:**
        - Electricity: [Find actual amount] (Due: [actual date])
        - Internet: [Find actual amount]
        - Mobile: [Find actual amount]
        - **Category Total: [Calculate actual sum of all bill transactions]**

        ## 📅 MONTHLY SPENDING BREAKDOWN (Calculate from actual data)
        **May 2025: [Calculate actual total for May 2025]**
        - Food: [Calculate actual May food total] ([Count May food transactions])
        - Shopping: [Calculate actual May shopping total] ([Count May shopping transactions])
        - Subscriptions: [Calculate actual May subscription total] ([Count May subscription transactions])
        - Bills: [Calculate actual May bills total] ([Count May bill transactions])

        **April 2025: [Calculate actual total for April 2025]**
        - Food: [Calculate actual April food total] ([Count April food transactions])
        - Shopping: [Calculate actual April shopping total] ([Count April shopping transactions])
        - Subscriptions: [Calculate actual April subscription total] ([Count April subscription transactions])
        - Bills: [Calculate actual April bills total] ([Count April bill transactions])

        ## 🏪 MERCHANT ANALYSIS WITH REAL DATA
        **Top 10 Merchants by Spending (Calculate from actual data):**
        1. [Merchant name]: [Actual total] ([Actual count] transactions) - Avg: [Actual total ÷ count] per order
        2. [Merchant name]: [Actual total] ([Actual count] transactions) - Avg: [Actual total ÷ count] per order
        3. [Continue for all merchants found...]

        ## 💳 PAYMENT METHOD USAGE (Count and sum actual transactions)
        **UPI Transactions: [Calculate actual UPI total] ([Count actual UPI transactions])**
        - PhonePe: [Calculate actual PhonePe total] ([Count PhonePe transactions])
        - Google Pay: [Calculate actual GPay total] ([Count GPay transactions])
        - Paytm: [Calculate actual Paytm total] ([Count Paytm transactions])

        **Credit Card: [Calculate actual credit card total] ([Count credit card transactions])**
        - Highest: [Find actual highest credit card amount] ([Merchant] - [Item])
        - Average: [Calculate actual average: total ÷ count] per transaction

        **Auto-debit/Subscriptions: [Calculate actual auto-debit total] ([Count auto-debit services])**
        - List each service with actual amounts

        ## 📈 SPENDING PATTERNS & TRENDS (Calculate from actual data)
        **Daily Average:** [Calculate: total spending ÷ number of days with transactions]
        **Weekly Pattern (Calculate actual averages for each day):**
        - Monday: [Calculate actual Monday average]
        - Tuesday: [Calculate actual Tuesday average]
        - Wednesday: [Calculate actual Wednesday average]
        - Thursday: [Calculate actual Thursday average]
        - Friday: [Calculate actual Friday average]
        - Saturday: [Calculate actual Saturday average]
        - Sunday: [Calculate actual Sunday average]

        **Time-based Spending (Calculate from actual transaction times):**
        - Morning (6-12): [Calculate actual morning total]
        - Afternoon (12-18): [Calculate actual afternoon total]
        - Evening (18-24): [Calculate actual evening total]
        - Night (24-6): [Calculate actual night total]

        ## 🎯 KEY FINANCIAL METRICS (Calculate from actual data)
        - **Total Monthly Spending**: [Calculate actual total from all transactions]
        - **Largest Single Purchase**: [Find actual highest amount] ([Merchant] - [Item])
        - **Most Frequent Merchant**: [Count transactions per merchant, find highest] ([Actual count] orders)
        - **Average Order Value**: [Calculate: total spending ÷ total transactions]
        - **Subscription Costs**: [Calculate actual subscription total]/month
        - **Food Delivery Frequency**: [Calculate: food transactions ÷ weeks] times/week
        - **Weekend vs Weekday Ratio**: [Calculate weekend total]:[Calculate weekday total]

        ## 💡 DATA-DRIVEN RECOMMENDATIONS (Based on actual spending data)
        1. **Subscription Optimization**: You're paying [Calculate actual subscription total]/month for [Count services] services
        2. **Food Delivery**: [Count food orders]/month costing [Calculate food total] - Consider cooking [Suggest number] meals to save [Calculate potential savings]
        3. **High-Value Purchases**: [Actual highest amount] on [Item] - Plan similar purchases during sales
        4. **Bill Management**: [Actual bill amount] due [Actual date] - Set auto-pay to avoid late fees

        CRITICAL CALCULATION REQUIREMENTS:
        1. Use ONLY real amounts from actual emails (₹299, ₹649, ₹24,999, etc.) - NO PLACEHOLDERS
        2. Calculate REAL totals by adding up actual amounts found in the data
        3. Count ACTUAL number of transactions, not estimates
        4. Show REAL dates from email timestamps
        5. List ACTUAL merchant names from email senders/content
        6. Calculate REAL averages using actual numbers (total ÷ count)
        7. If insufficient data, clearly state what's missing - DO NOT use XXX or placeholders

        EXAMPLE OF CORRECT OUTPUT:
        - Food Delivery: ₹2,847 (12 transactions) - Swiggy: ₹1,299 (5 orders), Zomato: ₹1,548 (7 orders)
        - NOT: Food Delivery: ₹X,XXX (X transactions) - Swiggy: ₹XXX, Zomato: ₹XXX

        ## 📋 SUMMARY REPORT
        Present a clean, executive summary of all financial data with actual calculated totals and insights.

        If insufficient email data is available, clearly state:
        "❌ **Insufficient email data for comprehensive analytics.**
        
        To generate detailed financial analytics:
        1. Upload more Gmail emails containing transaction details
        2. Ensure emails include receipts, bills, and payment confirmations
        3. Look for emails from banks, merchants, and service providers"

        IMPORTANT: Process ALL {len(all_unique_results)} unique transactions found. Calculate real numbers, show actual totals. NO PLACEHOLDERS (XXX) ALLOWED.
        """
        
        team_response = gmail_intelligence_team.run(team_prompt)
        
        return {
            "status": "success",
            "user_id": user_id,
            "analytics_report": team_response.content if hasattr(team_response, 'content') else str(team_response),
            "data_sources": list(analytics_data.keys()),
            "total_data_points": sum(len(results) for results in analytics_data.values()),
            "unique_transactions": len(all_unique_results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Gmail Intelligence Team analytics error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

# ************* Test Functions *************

async def test_gmail_team():
    """Test the Gmail Intelligence Team with sample data"""
    user_id = "test_user_team"
    
    # Sample Gmail data
    sample_emails = [
        {
            "id": "team_email_001",
            "subject": "Your Swiggy Order is Delivered!",
            "sender": "order@swiggy.in",
            "snippet": "Your Chicken Biryani worth ₹299 has been delivered",
            "body": "Thank you for ordering from Swiggy. Rate your experience!",
            "date": "2025-01-15T19:30:00+0530"
        },
        {
            "id": "team_email_002",
            "subject": "Netflix Subscription Renewed",
            "sender": "billing@netflix.com",
            "snippet": "₹649 debited for Premium plan",
            "body": "Your Netflix Premium subscription has been renewed.",
            "date": "2025-01-14T07:30:00+0530"
        },
        {
            "id": "team_email_003",
            "subject": "EMI Reminder - Credit Card Payment Due",
            "sender": "alerts@axis.com",
            "snippet": "₹4,500 EMI due on 20th January",
            "body": "Please pay your credit card EMI to avoid late fees.",
            "date": "2025-01-15T08:00:00+0530"
        }
    ]
    
    print("🚀 Testing Gmail Intelligence Team - Email Processing...")
    upload_result = await process_gmail_data(user_id, sample_emails)
    print(f"Processing Result: {json.dumps(upload_result, indent=2)}")
    
    print("\n🔍 Testing Gmail Intelligence Team - Email Queries...")
    queries = ["food orders", "subscription renewals", "payment reminders", "show me my expenses"]
    
    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        query_result = await query_email_database(user_id, query)
        print(f"Query Result: {json.dumps(query_result, indent=2)}")
    
    print("\n📊 Testing Gmail Intelligence Team - Analytics...")
    analytics_result = await get_email_analytics(user_id)
    print(f"Analytics Result: {json.dumps(analytics_result, indent=2)}")

async def interactive_team_system():
    """Interactive system to test the Gmail Intelligence Team"""
    user_id = input("Enter user ID (or press Enter for 'demo_user'): ").strip() or "demo_user"
    
    print(f"\n🤖 Gmail Intelligence Team System")
    print(f"User: {user_id}")
    print("=" * 60)
    print("Commands:")
    print("- Type your email query")
    print("- Type 'upload' to upload sample emails")
    print("- Type 'analytics' to get comprehensive email analytics")
    print("- Type 'team' to test direct team interaction")
    print("- Type 'exit' to quit")
    print("=" * 60)
    
    while True:
        try:
            user_input = input(f"\n💬 [{user_id}] Enter command: ").strip()
            
            if user_input.lower() == 'exit':
                print("👋 Goodbye!")
                break
            
            elif user_input.lower() == 'upload':
                print("📤 Uploading comprehensive sample emails using Gmail Intelligence Team...")
                sample_emails = [
                    {
                        "id": f"sample_{user_id}_001",
                        "subject": "Your Swiggy Order Delivered - Chicken Biryani",
                        "sender": "order@swiggy.in",
                        "snippet": "Your Chicken Biryani worth ₹299 has been delivered successfully",
                        "body": "Thank you for ordering from Swiggy! Your order of Chicken Biryani (₹299) has been delivered. Rate your experience and get exclusive offers!",
                        "date": "2025-01-15T20:30:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_002",
                        "subject": "Netflix Subscription Renewed - Premium Plan",
                        "sender": "billing@netflix.com",
                        "snippet": "₹649 debited for Netflix Premium plan renewal",
                        "body": "Your Netflix Premium subscription has been renewed for ₹649. Enjoy unlimited streaming!",
                        "date": "2025-01-14T09:15:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_003",
                        "subject": "Amazon Purchase Confirmation - Wireless Headphones",
                        "sender": "order-update@amazon.in",
                        "snippet": "Your order of Sony WH-1000XM4 Headphones for ₹24,999 has been confirmed",
                        "body": "Thank you for your purchase! Sony WH-1000XM4 Wireless Headphones (₹24,999) will be delivered by tomorrow.",
                        "date": "2025-01-13T14:22:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_004",
                        "subject": "Zomato Order Delivered - Pizza Hut",
                        "sender": "noreply@zomato.com",
                        "snippet": "Your Pizza Hut order worth ₹850 has been delivered",
                        "body": "Your delicious Pizza Hut order (₹850) has been delivered. Hope you enjoyed your meal!",
                        "date": "2025-01-12T21:45:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_005",
                        "subject": "Electricity Bill Payment Reminder",
                        "sender": "alerts@bescom.gov.in",
                        "snippet": "Your electricity bill of ₹2,340 is due on 20th January",
                        "body": "Dear Customer, your electricity bill for ₹2,340 is due on 20th January 2025. Please pay to avoid disconnection.",
                        "date": "2025-01-11T10:00:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_006",
                        "subject": "Uber Ride Receipt - Airport Trip",
                        "sender": "receipts@uber.com",
                        "snippet": "Your ride to Bangalore Airport cost ₹450",
                        "body": "Thanks for riding with Uber! Your trip to Kempegowda International Airport cost ₹450.",
                        "date": "2025-01-10T06:30:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_007",
                        "subject": "Spotify Premium Subscription Renewed",
                        "sender": "noreply@spotify.com",
                        "snippet": "₹119 charged for Spotify Premium Individual plan",
                        "body": "Your Spotify Premium subscription has been renewed for ₹119. Enjoy ad-free music!",
                        "date": "2025-01-09T12:00:00+0530"
                    },
                    {
                        "id": f"sample_{user_id}_008",
                        "subject": "BookMyShow Ticket Confirmation - Avengers Movie",
                        "sender": "donotreply@bookmyshow.com",
                        "snippet": "2 tickets for Avengers movie - ₹600 total",
                        "body": "Your movie tickets for Avengers (2 tickets × ₹300 = ₹600) have been confirmed for PVR Cinemas.",
                        "date": "2025-01-08T16:20:00+0530"
                    }
                ]
                upload_result = await process_gmail_data(user_id, sample_emails)
                print(f"✅ Upload completed: {upload_result.get('status', 'unknown')}")
                if upload_result.get('team_analysis'):
                    print(f"\n{upload_result['team_analysis']}")
                
            elif user_input.lower() == 'analytics':
                print("📊 Generating comprehensive analytics using Gmail Intelligence Team...")
                analytics_result = await get_email_analytics(user_id)
                if analytics_result.get('status') == 'success':
                    print(f"\n{analytics_result.get('analytics_report', 'Analytics generated')}")
                else:
                    print(f"❌ Analytics error: {analytics_result.get('error', 'Unknown error')}")
            
            elif user_input.lower() == 'team':
                print("🤖 Direct team interaction...")
                team_query = input("Enter query for the team: ").strip()
                if team_query:
                    response = gmail_intelligence_team.run(team_query)
                    print(f"\n🎯 Team Response:\n{response.content if hasattr(response, 'content') else str(response)}")
                
            elif user_input:
                print(f"🔍 Processing query using Gmail Intelligence Team: '{user_input}'")
                result = await query_email_database(user_id, user_input)
                if result.get('status') == 'success':
                    print(f"\n{result.get('team_response', 'No response')}")
                else:
                    print(f"❌ Query error: {result.get('error', 'Unknown error')}")
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🤖 Gmail Intelligence Team System (Agno + Mem0)")
    print("=" * 60)
    print("🔧 Architecture:")
    print("  • Gmail Intelligence Team - Master coordination team")
    print("  • Email Processor Agent - Email categorization and Mem0 storage")
    print("  • Email Query Agent - Intelligent email search and analysis")
    print("  • Email Analytics Agent - Comprehensive insights and reports")
    print("  • Mem0 Integration - Semantic memory storage and retrieval")
    print("  • Claude Sonnet 4 - Advanced team coordination")
    print("  • OpenAI GPT-4o - Individual agent processing")
    print("=" * 60)
    print("Select option:")
    print("1. Run comprehensive team tests")
    print("2. Interactive team system")
    print("3. Test direct team interaction")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        print("🚀 Running comprehensive team tests...")
        asyncio.run(test_gmail_team())
    elif choice == "2":
        print("🎯 Starting interactive team system...")
        asyncio.run(interactive_team_system())
    elif choice == "3":
        print("🤖 Testing direct team interaction...")
        test_query = input("Enter test query: ").strip()
        if test_query:
            response = gmail_intelligence_team.run(test_query)
            print(f"\n🎯 Team Response:\n{response.content if hasattr(response, 'content') else str(response)}")
    else:
        print("Invalid choice. Please run again and select 1-3.")
