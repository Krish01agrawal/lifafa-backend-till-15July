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
from dotenv import load_dotenv

# Load environment variables from .env file (two levels up from this file)
# mem0_agent.py is in backend/app/mem0_agent.py, .env is in the root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)
print(f"🔧 Loaded .env from: {dotenv_path}")

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
print(f"🔑 Initializing Mem0 clients with API key: {MEM0_API_KEY[:8]}...{MEM0_API_KEY[-4:] if len(MEM0_API_KEY) > 12 else MEM0_API_KEY}")
aclient = AsyncMemoryClient()
sync_client = MemoryClient()
print(f"✅ Mem0 clients initialized successfully")

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
    instructions=[
        "You are an expert email processor that categorizes and extracts insights from email data.",
        "Process emails and store them in Mem0 with proper categorization and metadata.",
        "Handle Gmail data and prepare it for intelligent storage and retrieval.",
        "Always provide detailed categorization and extract relevant financial information.",
        "Categorize emails into: banking, food, utilities, shopping, entertainment, investment, reminders, orders, general.",
        "Extract amounts, merchants, payment methods, and timestamps when available.",
        "Provide clear, structured responses without complex reasoning chains.",
    ],
    markdown=True,
)

# Email Query Agent
email_query_agent = Agent(
    name="Email Query Agent", 
    role="Handle intelligent email search and analysis",
    agent_id="email_query",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are an intelligent email query agent that helps users find and analyze their email data.",
        "Use advanced search techniques including sub-query generation and semantic search.",
        "Provide comprehensive, well-formatted responses with insights and analytics.",
        "Excel at understanding user intent and finding relevant emails from Mem0 storage.",
        "Generate multiple related sub-queries to improve search coverage.",
        "Format responses clearly with sections and actionable insights.",
        "Provide direct, helpful responses without complex reasoning chains.",
    ],
    markdown=True,
)

# Email Analytics Agent
email_analytics_agent = Agent(
    name="Email Analytics Agent",
    role="Generate comprehensive email insights and reports", 
    agent_id="email_analytics",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are an email analytics specialist that generates comprehensive insights and reports.",
        "Analyze email patterns, spending habits, subscription management, and financial trends.",
        "Create detailed reports with spending summaries, category breakdowns, and recommendations.",
        "Identify patterns in user behavior, payment methods, and merchant preferences.",
        "Provide actionable insights for better email and financial management.",
        "Use tables and structured formats to present data clearly.",
        "Focus on delivering data-driven observations and recommendations.",
        "Provide clear, direct insights without complex reasoning chains.",
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
    instructions=[
        "You are a Gmail Intelligence Team that provides email analysis based on ACTUAL email content.",
        "CRITICAL: Never fabricate or invent data. Only use the actual email content provided in search results.",
        "If the user asks for recent/latest emails, analyze the most recent emails found in the search results.",
        "If the user asks for specific insights about emails, provide analysis based on the actual email content.",
        "For recent email queries, focus on the email content, sender, subject, and any extractable information.",
        "Use the Email Processor Agent for categorizing and storing emails with proper metadata.",
        "Use the Email Query Agent for intelligent search and retrieval of email information.",
        "Use the Email Analytics Agent for generating insights based on REAL email data only.",
        "Leverage Mem0 memory for persistent, semantic storage and retrieval of email data.",
        "Provide structured, factual responses based only on the actual search results provided.",
        "If search results are empty or insufficient, clearly state this instead of fabricating information.",
        "For queries about latest emails, provide details about the actual email found (subject, sender, content summary).",
        "Ensure all responses are well-formatted, factual, and based on real email data.",
        "Only output the final consolidated response based on actual search results, not fictional data.",
        "If no relevant emails are found, suggest ways to refine the search or explain what data is available.",
    ],
    markdown=True,
    success_criteria="The team has provided accurate email intelligence based on actual search results with proper analysis of real email content.",
)
# *******************************

# ************* Direct Data Analysis Functions *************

def analyze_transactions_directly(transactions: List[Dict]) -> Dict[str, Any]:
    """Directly analyze transaction data and extract real insights"""
    import re
    from collections import defaultdict, Counter
    
    analysis = {
        'total_count': len(transactions),
        'total_amount': 0.0,
        'average_amount': 0.0,
        'transactions_with_amounts': 0,
        'categories': defaultdict(int),
        'merchants': defaultdict(int),
        'payment_methods': defaultdict(int),
        'amount_ranges': defaultdict(int),
        'sample_transactions': [],
        'top_merchants': [],
        'monthly_breakdown': defaultdict(float),
        'daily_breakdown': defaultdict(float)
    }
    
    amount_pattern = r'[₹Rs\.]\s*(\d+(?:,\d+)*(?:\.\d+)?)'
    
    for transaction in transactions:
        if not transaction or not isinstance(transaction, dict):
            continue
            
        memory = transaction.get('memory', '')
        metadata = transaction.get('metadata', {})
        
        if not isinstance(metadata, dict):
            metadata = {}
        
        # Extract category
        category = metadata.get('category', 'unknown')
        analysis['categories'][category] += 1
        
        # Extract merchant
        merchant = metadata.get('merchant', 'unknown')
        if merchant == 'unknown' and memory:
            # Try to extract merchant from memory content
            merchant_keywords = ['swiggy', 'zomato', 'amazon', 'flipkart', 'uber', 'ola', 'paytm', 'phonepe', 'gpay']
            for keyword in merchant_keywords:
                if keyword.lower() in memory.lower():
                    merchant = keyword.title()
                    break
        
        analysis['merchants'][merchant] += 1
        
        # Extract payment method
        payment_method = metadata.get('payment_method', 'unknown')
        if payment_method == 'unknown' and memory:
            # Try to extract payment method from memory content
            if any(word in memory.lower() for word in ['upi', 'phonepe', 'gpay', 'paytm']):
                payment_method = 'UPI'
            elif any(word in memory.lower() for word in ['credit card', 'credit']):
                payment_method = 'Credit Card'
            elif any(word in memory.lower() for word in ['debit card', 'debit']):
                payment_method = 'Debit Card'
        
        analysis['payment_methods'][payment_method] += 1
        
        # Extract amount
        amount = 0.0
        amount_str = metadata.get('amount', '')
        
        if amount_str and isinstance(amount_str, str):
            # Try to extract number from amount string
            amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', amount_str.replace(',', ''))
            if amount_match:
                try:
                    amount = float(amount_match.group(1))
                except ValueError:
                    pass
        
        # If no amount in metadata, try to extract from memory content
        if amount == 0.0 and memory:
            amount_matches = re.findall(amount_pattern, memory)
            if amount_matches:
                try:
                    # Take the first amount found, clean it up
                    amount_str = amount_matches[0].replace(',', '')
                    amount = float(amount_str)
                except ValueError:
                    pass
        
        if amount > 0:
            analysis['total_amount'] += amount
            analysis['transactions_with_amounts'] += 1
            
            # Categorize by amount ranges
            if amount < 100:
                analysis['amount_ranges']['Under ₹100'] += 1
            elif amount < 500:
                analysis['amount_ranges']['₹100-500'] += 1
            elif amount < 1000:
                analysis['amount_ranges']['₹500-1000'] += 1
            elif amount < 5000:
                analysis['amount_ranges']['₹1000-5000'] += 1
            else:
                analysis['amount_ranges']['Over ₹5000'] += 1
            
            # Add to sample transactions
            if len(analysis['sample_transactions']) < 20:
                analysis['sample_transactions'].append({
                    'merchant': merchant,
                    'amount': amount,
                    'category': category,
                    'method': payment_method,
                    'memory_preview': memory[:100] + '...' if len(memory) > 100 else memory
                })
    
    # Calculate average
    if analysis['transactions_with_amounts'] > 0:
        analysis['average_amount'] = analysis['total_amount'] / analysis['transactions_with_amounts']
    
    # Sort top merchants
    analysis['top_merchants'] = sorted(analysis['merchants'].items(), key=lambda x: x[1], reverse=True)
    
    # Sort sample transactions by amount (highest first)
    analysis['sample_transactions'].sort(key=lambda x: x['amount'], reverse=True)
    
    return analysis

def extract_financial_insights(analysis: Dict[str, Any], query: str = "") -> str:
    """Generate detailed financial insights from direct analysis"""
    insights = []
    
    insights.append("## 📊 COMPREHENSIVE FINANCIAL ANALYSIS")
    insights.append(f"Based on direct data extraction from your email transactions:\n")
    
    # Transaction Overview
    insights.append("### 💰 TRANSACTION OVERVIEW")
    insights.append(f"- **Total Transactions Analyzed**: {analysis['total_count']}")
    insights.append(f"- **Transactions with Amount Data**: {analysis['transactions_with_amounts']}")
    insights.append(f"- **Total Amount Spent**: ₹{analysis['total_amount']:,.2f}")
    if analysis['transactions_with_amounts'] > 0:
        insights.append(f"- **Average Transaction Value**: ₹{analysis['average_amount']:,.2f}")
    insights.append("")
    
    # Category Breakdown
    if analysis['categories']:
        insights.append("### 📈 SPENDING BY CATEGORY")
        total_cat_transactions = sum(analysis['categories'].values())
        for category, count in sorted(analysis['categories'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_cat_transactions) * 100
            insights.append(f"- **{category.title()}**: {count} transactions ({percentage:.1f}%)")
        insights.append("")
    
    # Top Merchants
    if analysis['top_merchants']:
        insights.append("### 🏪 TOP MERCHANTS BY FREQUENCY")
        for i, (merchant, count) in enumerate(analysis['top_merchants'][:10], 1):
            insights.append(f"{i:2d}. **{merchant}**: {count} transactions")
        insights.append("")
    
    # Payment Methods
    if analysis['payment_methods']:
        insights.append("### 💳 PAYMENT METHOD DISTRIBUTION")
        total_payment_transactions = sum(analysis['payment_methods'].values())
        for method, count in sorted(analysis['payment_methods'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_payment_transactions) * 100
            insights.append(f"- **{method}**: {count} transactions ({percentage:.1f}%)")
        insights.append("")
    
    # Amount Distribution
    if analysis['amount_ranges']:
        insights.append("### 💰 SPENDING DISTRIBUTION")
        for range_desc, count in analysis['amount_ranges'].items():
            insights.append(f"- **{range_desc}**: {count} transactions")
        insights.append("")
    
    # Top Transactions
    if analysis['sample_transactions']:
        insights.append("### 🎯 HIGHEST VALUE TRANSACTIONS")
        for i, tx in enumerate(analysis['sample_transactions'][:5], 1):
            insights.append(f"{i}. **{tx['merchant']}** - ₹{tx['amount']:,.2f} ({tx['category']}) via {tx['method']}")
        insights.append("")
    
    # Data-Driven Insights
    insights.append("### 📊 KEY INSIGHTS & RECOMMENDATIONS")
    
    if analysis['total_amount'] > 0:
        # Food spending analysis
        food_categories = ['food', 'delivery', 'restaurant']
        food_transactions = sum(count for cat, count in analysis['categories'].items() if any(food_cat in cat.lower() for food_cat in food_categories))
        if food_transactions > 0:
            food_percentage = (food_transactions / analysis['total_count']) * 100
            insights.append(f"- **Food & Dining**: {food_transactions} transactions ({food_percentage:.1f}% of all transactions)")
            insights.append(f"  - Consider meal planning to potentially reduce food delivery expenses")
        
        # UPI usage analysis
        upi_transactions = analysis['payment_methods'].get('UPI', 0) + analysis['payment_methods'].get('upi', 0)
        if upi_transactions > 0:
            upi_percentage = (upi_transactions / analysis['total_count']) * 100
            insights.append(f"- **UPI Usage**: {upi_transactions} transactions ({upi_percentage:.1f}%) - Good for cashback rewards")
        
        # High-value transaction analysis
        high_value_transactions = analysis['amount_ranges'].get('Over ₹5000', 0)
        if high_value_transactions > 0:
            insights.append(f"- **Large Purchases**: {high_value_transactions} transactions over ₹5000 - Consider using credit cards for better rewards")
        
        # Monthly spending estimate
        if analysis['transactions_with_amounts'] > 0:
            estimated_monthly = analysis['total_amount']  # Assuming this is monthly data
            insights.append(f"- **Estimated Monthly Spending**: ₹{estimated_monthly:,.2f}")
            insights.append(f"- **Suggested Emergency Fund**: ₹{estimated_monthly * 3:,.2f} (3 months of expenses)")
    
    return "\n".join(insights)

def extract_transaction_table(transactions: List[Dict]) -> Dict[str, Any]:
    """Extract transactions into a proper table format with specific details"""
    import re
    from datetime import datetime
    from collections import defaultdict
    
    # Initialize table structure
    transaction_table = []
    
    # Patterns for extraction
    amount_pattern = r'[₹Rs\.]\s*(\d+(?:,\d+)*(?:\.\d+)?)'
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',  # Month DD, YYYY
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # DD Month YYYY
        r'(May\s+2025|April\s+2025|June\s+2025)',  # Month Year
    ]
    
    # Merchant keywords mapping
    merchant_patterns = {
        'Swiggy': ['swiggy', 'SWIGGY'],
        'Zomato': ['zomato', 'ZOMATO'],
        'Amazon': ['amazon', 'AMAZON'],
        'Flipkart': ['flipkart', 'FLIPKART'],
        'Uber': ['uber', 'UBER'],
        'Ola': ['ola', 'OLA'],
        'PayTM': ['paytm', 'PAYTM'],
        'PhonePe': ['phonepe', 'PHONEPE', 'phone pe'],
        'Google Pay': ['gpay', 'GPAY', 'google pay'],
        'Netflix': ['netflix', 'NETFLIX'],
        'Spotify': ['spotify', 'SPOTIFY'],
        'BookMyShow': ['bookmyshow', 'BOOKMYSHOW'],
        'BOX8': ['box8', 'BOX8'],
        'FOOD COURT': ['food court', 'FOOD COURT'],
    }
    
    # Process each transaction
    for i, transaction in enumerate(transactions):
        if not transaction or not isinstance(transaction, dict):
            continue
        
        memory = transaction.get('memory', '')
        metadata = transaction.get('metadata', {})
        
        if not isinstance(metadata, dict):
            metadata = {}
        
        # Extract transaction details
        row = {
            'serial': i + 1,
            'date': 'Not specified',
            'amount': 'Not specified',
            'amount_numeric': 0.0,
            'receiver': 'Unknown',
            'purpose': 'General',
            'payment_method': 'Not specified',
            'raw_memory': memory[:200] + '...' if len(memory) > 200 else memory
        }
        
        # Extract date
        for date_pattern in date_patterns:
            date_match = re.search(date_pattern, memory, re.IGNORECASE)
            if date_match:
                row['date'] = date_match.group(1)
                break
        
        # If no date in memory, try metadata
        if row['date'] == 'Not specified' and metadata.get('timestamp'):
            try:
                timestamp = metadata['timestamp']
                if timestamp:
                    # Try to parse and format timestamp
                    row['date'] = timestamp[:10] if len(timestamp) > 10 else timestamp
            except:
                pass
        
        # Extract amount
        amount_matches = re.findall(amount_pattern, memory)
        if amount_matches:
            try:
                # Take the first amount found
                amount_str = amount_matches[0].replace(',', '')
                row['amount'] = f"₹{amount_str}"
                row['amount_numeric'] = float(amount_str)
            except ValueError:
                pass
        
        # Try amount from metadata if not found in memory
        if row['amount'] == 'Not specified' and metadata.get('amount'):
            amount_str = str(metadata['amount'])
            amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', amount_str.replace(',', ''))
            if amount_match:
                try:
                    amount_numeric = float(amount_match.group(1))
                    row['amount'] = f"₹{amount_numeric:.2f}"
                    row['amount_numeric'] = amount_numeric
                except ValueError:
                    pass
        
        # Extract merchant/receiver
        for merchant, patterns in merchant_patterns.items():
            for pattern in patterns:
                if pattern.lower() in memory.lower():
                    row['receiver'] = merchant
                    break
            if row['receiver'] != 'Unknown':
                break
        
        # Try metadata for merchant if not found
        if row['receiver'] == 'Unknown' and metadata.get('merchant'):
            merchant = metadata['merchant']
            if merchant and merchant != 'unknown':
                row['receiver'] = merchant.title()
        
        # Extract purpose/category
        purpose_keywords = {
            'Food Order': ['food', 'meal', 'delivery', 'restaurant', 'order', 'swiggy', 'zomato', 'box8'],
            'Shopping': ['shopping', 'purchase', 'buy', 'amazon', 'flipkart', 'myntra'],
            'Transportation': ['uber', 'ola', 'cab', 'taxi', 'ride', 'transport'],
            'Entertainment': ['netflix', 'spotify', 'bookmyshow', 'movie', 'music'],
            'Bill Payment': ['bill', 'electricity', 'utility', 'payment', 'due'],
            'Subscription': ['subscription', 'renewal', 'plan', 'premium'],
        }
        
        for purpose, keywords in purpose_keywords.items():
            if any(keyword.lower() in memory.lower() for keyword in keywords):
                row['purpose'] = purpose
                break
        
        # Try metadata for category
        if row['purpose'] == 'General' and metadata.get('category'):
            category = metadata['category']
            if category and category != 'unknown':
                row['purpose'] = category.replace('_', ' ').title()
        
        # Extract payment method
        payment_methods = {
            'UPI': ['upi', 'phonepe', 'gpay', 'paytm', 'google pay'],
            'Credit Card': ['credit card', 'credit'],
            'Debit Card': ['debit card', 'debit'],
            'Net Banking': ['net banking', 'netbanking', 'bank transfer'],
        }
        
        for method, keywords in payment_methods.items():
            if any(keyword.lower() in memory.lower() for keyword in keywords):
                row['payment_method'] = method
                break
        
        # Try metadata for payment method
        if row['payment_method'] == 'Not specified' and metadata.get('payment_method'):
            method = metadata['payment_method']
            if method and method != 'unknown':
                row['payment_method'] = method.replace('_', ' ').title()
        
        transaction_table.append(row)
    
    return transaction_table

def generate_financial_insights_from_table(transaction_table: List[Dict]) -> str:
    """Generate specific financial insights from the transaction table"""
    if not transaction_table:
        return "No transaction data available for analysis."
    
    insights = []
    insights.append("## 📊 DETAILED TRANSACTION ANALYSIS")
    insights.append("")
    
    # Create the table
    insights.append("### 💳 TRANSACTION TABLE")
    insights.append("")
    insights.append("| # | Date | Amount | Receiver/Merchant | Purpose | Payment Method |")
    insights.append("|---|------|--------|-------------------|---------|----------------|")
    
    for row in transaction_table:
        insights.append(f"| {row['serial']:2d} | {row['date'][:10]} | {row['amount'][:12]} | {row['receiver'][:18]} | {row['purpose'][:15]} | {row['payment_method'][:12]} |")
    
    insights.append("")
    
    # Calculate summary statistics
    total_transactions = len(transaction_table)
    transactions_with_amounts = [t for t in transaction_table if t['amount_numeric'] > 0]
    total_amount = sum(t['amount_numeric'] for t in transactions_with_amounts)
    avg_amount = total_amount / len(transactions_with_amounts) if transactions_with_amounts else 0
    
    insights.append("### 💰 FINANCIAL SUMMARY")
    insights.append("")
    insights.append(f"- **Total Transactions**: {total_transactions}")
    insights.append(f"- **Transactions with Amount Data**: {len(transactions_with_amounts)}")
    insights.append(f"- **Total Amount Spent**: ₹{total_amount:,.2f}")
    insights.append(f"- **Average Transaction**: ₹{avg_amount:,.2f}")
    insights.append("")
    
    # Category breakdown
    from collections import defaultdict
    category_totals = defaultdict(lambda: {'count': 0, 'total': 0.0})
    merchant_totals = defaultdict(lambda: {'count': 0, 'total': 0.0})
    payment_totals = defaultdict(lambda: {'count': 0, 'total': 0.0})
    
    for transaction in transaction_table:
        category = transaction['purpose']
        merchant = transaction['receiver']
        payment = transaction['payment_method']
        amount = transaction['amount_numeric']
        
        category_totals[category]['count'] += 1
        category_totals[category]['total'] += amount
        
        merchant_totals[merchant]['count'] += 1
        merchant_totals[merchant]['total'] += amount
        
        payment_totals[payment]['count'] += 1
        payment_totals[payment]['total'] += amount
    
    # Category breakdown
    insights.append("### 📈 SPENDING BY CATEGORY")
    insights.append("")
    for category, data in sorted(category_totals.items(), key=lambda x: x[1]['total'], reverse=True):
        if data['total'] > 0:
            insights.append(f"- **{category}**: ₹{data['total']:,.2f} ({data['count']} transactions) - Avg: ₹{data['total']/data['count']:,.2f}")
        else:
            insights.append(f"- **{category}**: {data['count']} transactions (amount not specified)")
    insights.append("")
    
    # Top merchants
    insights.append("### 🏪 TOP MERCHANTS")
    insights.append("")
    merchant_list = sorted(merchant_totals.items(), key=lambda x: x[1]['count'], reverse=True)
    for i, (merchant, data) in enumerate(merchant_list[:10], 1):
        if data['total'] > 0:
            insights.append(f"{i:2d}. **{merchant}**: ₹{data['total']:,.2f} ({data['count']} transactions)")
        else:
            insights.append(f"{i:2d}. **{merchant}**: {data['count']} transactions")
    insights.append("")
    
    # Payment method analysis
    insights.append("### 💳 PAYMENT METHOD BREAKDOWN")
    insights.append("")
    for method, data in sorted(payment_totals.items(), key=lambda x: x[1]['total'], reverse=True):
        if data['total'] > 0:
            insights.append(f"- **{method}**: ₹{data['total']:,.2f} ({data['count']} transactions)")
        else:
            insights.append(f"- **{method}**: {data['count']} transactions")
    insights.append("")
    
    # Specific insights
    insights.append("### 🎯 KEY INSIGHTS")
    insights.append("")
    
    if transactions_with_amounts:
        highest_transaction = max(transactions_with_amounts, key=lambda x: x['amount_numeric'])
        insights.append(f"- **Highest Transaction**: {highest_transaction['amount']} to {highest_transaction['receiver']} on {highest_transaction['date']}")
        
        # Most frequent merchant
        top_merchant = max(merchant_totals.items(), key=lambda x: x[1]['count'])
        insights.append(f"- **Most Frequent Merchant**: {top_merchant[0]} ({top_merchant[1]['count']} transactions)")
        
        # Category insights
        if category_totals:
            top_category = max(category_totals.items(), key=lambda x: x[1]['total'])
            insights.append(f"- **Top Spending Category**: {top_category[0]} - ₹{top_category[1]['total']:,.2f}")
    
    insights.append("")
    insights.append("### 💡 RECOMMENDATIONS")
    insights.append("")
    
    # Food delivery insights
    food_data = category_totals.get('Food Order', {'count': 0, 'total': 0.0})
    if food_data['count'] > 0:
        insights.append(f"- **Food Delivery**: {food_data['count']} orders totaling ₹{food_data['total']:,.2f}")
        if food_data['total'] > 0:
            avg_food = food_data['total'] / food_data['count']
            insights.append(f"  - Average per order: ₹{avg_food:.2f}")
            insights.append(f"  - Consider cooking {max(1, food_data['count']//3)} meals per week to save ~₹{food_data['total']*0.7:.0f}")
    
    # UPI usage
    upi_data = payment_totals.get('UPI', {'count': 0, 'total': 0.0})
    if upi_data['count'] > 0:
        upi_percentage = (upi_data['count'] / total_transactions) * 100
        insights.append(f"- **UPI Usage**: {upi_data['count']} transactions ({upi_percentage:.1f}%) - Good for cashback rewards")
    
    return "\n".join(insights)

# ************* Debug and Analysis Functions *************

def debug_mem0_configuration():
    """Debug Mem0 configuration and search parameters"""
    print("🔧 MEM0 CONFIGURATION DEBUG:")
    print(f"   - Mem0 API Key: {'✅ Set' if MEM0_API_KEY else '❌ Missing'}")
    print(f"   - OpenAI API Key: {'✅ Set' if OPENAI_API_KEY else '❌ Missing'}")
    
    try:
        # Test basic Mem0 connection
        test_result = sync_client.search(
            query="test",
            user_id="debug_test",
            limit=1
        )
        print(f"   - Mem0 Connection: ✅ Working")
    except Exception as e:
        print(f"   - Mem0 Connection: ❌ Error - {e}")
    
    print("\n📊 SEARCH PARAMETERS ANALYSIS:")
    print("   Current search settings:")
    print("   - Default limit: 500 (primary search)")
    print("   - Query limit: 1000 (for queries)")
    print("   - Broader search limit: 200 (per broader term)")
    print("   - Analytics limit: 300 (per analytics query)")
    print("   - Comprehensive limit: 2000 (for get_all function)")
    
    print("\n🔍 SEARCH BEHAVIOR ANALYSIS:")
    print("   - keyword_search: True (enables keyword matching)")
    print("   - rerank: True (improves relevance but may limit results)")
    print("   - filter_memories: False (includes all memories)")
    print("   - filters: {'metadata.source': 'gmail'} (only Gmail emails)")
    
    print("\n⚠️ POTENTIAL LIMITING FACTORS:")
    print("   1. Mem0 Platform limitations (if using platform version)")
    print("   2. Reranking reducing result diversity")
    print("   3. Search query specificity affecting relevance scoring")
    print("   4. LLM response length limits during processing")
    print("   5. Token limits in team prompt processing")

async def test_mem0_limits(user_id: str):
    """Test Mem0 search limits with progressively higher limits"""
    print(f"🧪 TESTING MEM0 SEARCH LIMITS for user {user_id}")
    
    test_limits = [10, 50, 100, 250, 500, 1000, 2000]
    test_query = "payment transaction amount rupees"
    
    results_by_limit = {}
    
    for limit in test_limits:
        try:
            results = sync_client.search(
                query=test_query,
                user_id=user_id,
                limit=limit,
                filters={"metadata.source": "gmail"},
                keyword_search=True,
                rerank=False,  # Disable reranking for this test
                filter_memories=False
            )
            
            results_count = len(results) if results else 0
            results_by_limit[limit] = results_count
            print(f"   - Limit {limit:4d}: {results_count:4d} results returned")
            
        except Exception as e:
            print(f"   - Limit {limit:4d}: ❌ Error - {e}")
            results_by_limit[limit] = f"Error: {e}"
    
    print(f"\n📊 SEARCH LIMIT TEST RESULTS:")
    print(f"   Query: '{test_query}'")
    print(f"   Results by limit: {results_by_limit}")
    
    # Find the plateau point
    max_results = max([r for r in results_by_limit.values() if isinstance(r, int)])
    plateau_limits = [limit for limit, count in results_by_limit.items() if count == max_results]
    
    if plateau_limits:
        print(f"\n🎯 ANALYSIS:")
        print(f"   - Maximum results found: {max_results}")
        print(f"   - Plateau reached at limit: {min(plateau_limits)}")
        print(f"   - This suggests you have ~{max_results} matching transactions")
        
        if max_results < 100:
            print(f"   - ⚠️ This is less than your expected 100+ transactions")
            print(f"   - Possible reasons:")
            print(f"     • Search query too specific")
            print(f"     • Transactions stored with different keywords")
            print(f"     • Metadata filtering excluding results")
            print(f"     • Transactions not properly categorized during upload")
    
    return results_by_limit

# ************* Helper Functions *************

async def get_all_user_transactions(user_id: str, limit: int = 2000) -> Dict[str, Any]:
    """Get ALL user transactions from Mem0 with comprehensive details"""
    try:
        print(f"🔍 RETRIEVING ALL TRANSACTIONS for user {user_id}")
        
        # Try multiple broad search terms to get ALL transactions
        broad_searches = [
            "payment paid transaction amount rupees upi",
            "swiggy zomato amazon flipkart food order",
            "subscription netflix spotify prime renewal",
            "bill electricity utility reminder due",
            "shopping purchase buy ecommerce online",
            "₹ Rs rupees money cost price total",
            "credit debit card bank transfer",
            "delivery order confirmation receipt",
            "2024 2025 january february march april may june"
        ]
        
        all_transactions = []
        seen_memories = set()
        
        # Search with each broad term using retry logic
        for search_term in broad_searches:
            try:
                results = await search_with_retry(search_term, user_id, 300, max_retries=2)
                
                if results:
                    for result in results:
                        if result and isinstance(result, dict):
                            memory_text = result.get('memory', '')
                            if memory_text not in seen_memories and len(memory_text) > 20:  # Avoid duplicates and empty memories
                                all_transactions.append(result)
                                seen_memories.add(memory_text)
                            
                print(f"   - Search '{search_term}': Found {len(results)} results, {len(all_transactions)} total unique")
                        
            except Exception as e:
                print(f"❌ Search error for '{search_term}': {e}")
        
        # Also try getting ALL memories without query (if supported)
        try:
            all_memories = sync_client.get_all(user_id=user_id, limit=limit)
            if all_memories:
                print(f"📊 Retrieved {len(all_memories)} total memories via get_all()")
                for memory in all_memories:
                    memory_text = memory.get('memory', '')
                    if memory_text not in seen_memories and len(memory_text) > 20:
                        all_transactions.append(memory)
                        seen_memories.add(memory_text)
        except Exception as e:
            print(f"⚠️ get_all() not available or failed: {e}")
        
        print(f"📊 FINAL RESULT: Retrieved {len(all_transactions)} unique transactions")
        
        # Analyze transaction data
        categories = {}
        merchants = {}
        amounts = []
        dates = []
        
        for transaction in all_transactions:
            metadata = transaction.get('metadata', {})
            
            # Count categories
            category = metadata.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
            
            # Count merchants  
            merchant = metadata.get('merchant', 'unknown')
            merchants[merchant] = merchants.get(merchant, 0) + 1
            
            # Collect amounts
            amount = metadata.get('amount')
            if amount:
                amounts.append(amount)
            
            # Collect dates
            timestamp = metadata.get('timestamp')
            if timestamp:
                dates.append(timestamp)
        
        return {
            "status": "success",
            "user_id": user_id,
            "total_transactions": len(all_transactions),
            "search_terms_used": len(broad_searches),
            "unique_categories": len(categories),
            "unique_merchants": len(merchants),
            "transactions_with_amounts": len(amounts),
            "transactions_with_dates": len(dates),
            "category_breakdown": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
            "merchant_breakdown": dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True)),
            "sample_transactions": all_transactions[:5],  # First 5 for preview
            "all_transactions": all_transactions,  # All transactions for processing
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error retrieving all transactions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

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
    """Search emails in Mem0 memory with comprehensive search strategy and error handling"""
    try:
        query_lower = query.lower()
        
        # Check if this is a recent/latest email query
        is_recent_query = any(word in query_lower for word in ["recent", "latest", "newest", "last"])
        
        # Primary search with original query
        results = await search_with_retry(query, user_id, limit)
        
        # For recent email queries, try to get all emails and sort by timestamp
        if is_recent_query and len(results) < 10:
            print(f"🔍 Detected recent email query, searching for all recent emails...")
            
            # Search for all emails with broader terms
            recent_searches = [
                "email message",
                "subject",
                "sender",
                "2025 2024",
                "gmail"
            ]
            
            all_results = results.copy() if results else []
            seen_memories = set()
            
            # Add existing results to seen set
            for result in all_results:
                if result and isinstance(result, dict):
                    seen_memories.add(result.get('memory', ''))
            
            for recent_search in recent_searches:
                try:
                    recent_results = await search_with_retry(recent_search, user_id, 200)
                    
                    if recent_results:
                        for result in recent_results:
                            if result and isinstance(result, dict):
                                memory_text = result.get('memory', '')
                                if memory_text not in seen_memories:
                                    all_results.append(result)
                                    seen_memories.add(memory_text)
                                    
                except Exception as e:
                    print(f"❌ Recent search error for '{recent_search}': {e}")
            
            # Sort by timestamp or score to get most recent
            def get_timestamp_score(result):
                if not result or not isinstance(result, dict):
                    return 0
                
                metadata = result.get('metadata', {})
                if isinstance(metadata, dict):
                    timestamp = metadata.get('timestamp')
                    if timestamp:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            return dt.timestamp()
                        except:
                            pass
                
                # Fallback to score
                return result.get('score', 0)
            
            all_results.sort(key=get_timestamp_score, reverse=True)
            results = all_results[:limit]  # Get most recent ones
            
        # If we still have few results and it's not a recent query, try broader searches
        elif len(results) < 100 and not is_recent_query:
            broader_queries = []
            
            # Generate broader search terms based on the original query
            if any(term in query_lower for term in ["food", "order", "delivery", "restaurant"]):
                broader_queries.extend(["food", "delivery", "order", "restaurant", "swiggy", "zomato", "ubereats", "dominos"])
            
            if any(term in query_lower for term in ["upi", "payment", "transaction"]):
                broader_queries.extend(["upi", "payment", "paid", "transaction", "gpay", "phonepe", "paytm"])
            
            if any(term in query_lower for term in ["may", "april", "2025"]):
                broader_queries.extend(["may 2025", "april 2025", "2025"])
            
            if any(term in query_lower for term in ["spending", "expense", "money"]):
                broader_queries.extend(["amount", "rupees", "₹", "paid", "cost", "price"])
            
            # Perform additional searches with broader terms
            all_results = results.copy() if results else []
            seen_memories = set()
            
            # Add existing results to seen set
            for result in all_results:
                if result and isinstance(result, dict):
                    seen_memories.add(result.get('memory', ''))
            
            for broader_query in broader_queries:
                try:
                    broader_results = await search_with_retry(broader_query, user_id, 500)
                    
                    # Add unique results
                    if broader_results:
                        for result in broader_results:
                            if result and isinstance(result, dict):
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

async def search_with_retry(query: str, user_id: str, limit: int, max_retries: int = 3) -> List[Dict]:
    """Search with retry logic for handling API errors"""
    import asyncio
    
    print(f"🔍 Mem0 Search - API Key: {MEM0_API_KEY[:8]}...{MEM0_API_KEY[-4:] if len(MEM0_API_KEY) > 12 else MEM0_API_KEY}")
    
    for attempt in range(max_retries):
        try:
            # Use sync_client for searches with proper error handling
            print(f"🔄 Attempting Mem0 search for '{query}' (user: {user_id}, limit: {limit})")
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
                # Filter out None or invalid results
                valid_results = [r for r in results if r and isinstance(r, dict)]
                print(f"✅ Search successful for '{query}': {len(valid_results)} valid results (attempt {attempt + 1})")
                return valid_results
            else:
                print(f"⚠️ Search returned None for '{query}' (attempt {attempt + 1})")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg or "server error" in error_msg:
                print(f"🔄 API error (502 Bad Gateway) for '{query}' - Attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2, 4, 6 seconds
                    print(f"   Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Max retries reached for '{query}': {e}")
            else:
                print(f"❌ Non-retryable error for '{query}': {e}")
                break
    
    return []  # Return empty list if all retries failed

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
        
        # DEBUG: Print detailed search results info
        print(f"📊 SEARCH DEBUG INFO:")
        print(f"   - Total results retrieved: {len(search_results)}")
        print(f"   - Search limit used: {limit}")
        
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
                        cat_results = await search_emails_in_mem0(user_id, term, 100)
                        
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
        
        # DEBUG: Print sample of results to understand data structure
        if search_results:
            print(f"📄 SAMPLE RESULT STRUCTURE (first result):")
            sample_result = search_results[0]
            if sample_result and isinstance(sample_result, dict):
                print(f"   - Keys: {list(sample_result.keys())}")
                print(f"   - Memory preview: {sample_result.get('memory', '')[:100]}...")
                metadata = sample_result.get('metadata')
                if metadata and isinstance(metadata, dict):
                    print(f"   - Metadata keys: {list(metadata.keys())}")
                else:
                    print(f"   - Metadata: None or invalid format")
            else:
                print(f"   - Invalid result format: {type(sample_result)}")
        
        # Extract all transaction data from search results for better processing with null checks
        transaction_data = []
        for i, result in enumerate(search_results):
            if result and isinstance(result, dict):
                transaction_info = {
                    "index": i + 1,
                    "memory": result.get('memory', '') if result.get('memory') else '',
                    "metadata": result.get('metadata', {}) if result.get('metadata') else {},
                    "score": result.get('score', 0) if result.get('score') is not None else 0
                }
                transaction_data.append(transaction_info)
            else:
                print(f"⚠️ Skipping invalid result at index {i}: {type(result)}")
        
        print(f"📊 TRANSACTION DATA PREPARED: {len(transaction_data)} valid transactions from {len(search_results)} search results")
        
        # Use team to process query with search results - FORCE ALL RESULTS PROCESSING
        team_prompt = f"""
        CRITICAL INSTRUCTIONS: Analyze this email query using ONLY the actual search results provided. DO NOT fabricate any data.

        User Query: "{query}"
        User ID: {user_id}
        Search Results Count: {len(search_results)} emails found
        Transaction Data Count: {len(transaction_data)} processed records

        SEARCH RESULTS (Actual Email Data):
        {json.dumps(search_results[:10], indent=2) if search_results else "No email results found"}

        ANALYSIS INSTRUCTIONS:
        1. If this is a query about recent/latest emails:
           - Focus on the most recent emails in the search results
           - Provide details about the actual email content (subject, sender, snippet)
           - Extract any relevant information from the email content
           - Do NOT fabricate financial data or transaction details
        
        2. If this is a general email analysis query:
           - Analyze the actual email content provided
           - Extract patterns and insights from the real email data
           - Categorize based on actual email senders and content
           - Provide statistics based only on the found emails
        
        3. Response format:
           - Start with a clear statement about what emails were found
           - Provide actual email details (subject, sender, date if available)
           - Give insights based on the real email content
           - If insufficient data, suggest how to refine the search
        
        4. NEVER DO:
           - Create fictional transaction amounts or financial data
           - Invent email content or details not in the search results
           - Generate fake spending reports or financial analytics
           - Provide data that contradicts the actual search results

        5. ALWAYS DO:
           - Base your response entirely on the provided search results
           - State clearly if no relevant emails were found
           - Provide factual analysis of the actual email content
           - Be specific about what data is available vs. what is missing

        Provide a comprehensive, factual response based ONLY on the actual search results provided above.
        """
        
        team_response = gmail_intelligence_team.run(team_prompt)
        
        return {
            "status": "success",
            "user_id": user_id,
            "query": query,
            "results_count": len(search_results),
            "search_results_sample": search_results[:3] if search_results else [],  # Include sample for debugging
            "team_response": team_response.content if hasattr(team_response, 'content') else str(team_response),
            "debug_info": {
                "total_results_found": len(search_results),
                "limit_used": limit,
                "transaction_data_prepared": len(transaction_data)
            },
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
            
            # Collect all unique results with null checks
            if results:
                for result in results:
                    if result and isinstance(result, dict):
                        memory_text = result.get('memory', '')
                        if memory_text not in seen_memories:
                            all_unique_results.append(result)
                            seen_memories.add(memory_text)
        
        print(f"📊 Total unique results collected: {len(all_unique_results)}")
        
        # Use team to generate comprehensive analytics report
        team_prompt = f"""
        You are a MASTER FINANCIAL DATA ANALYST creating a COMPREHENSIVE FINANCIAL DASHBOARD. Extract REAL data, calculate ACTUAL totals, and provide SPECIFIC insights with exact numbers.

        TRANSACTION DATABASE TO ANALYZE: {json.dumps(analytics_data, indent=1)}
        TOTAL TRANSACTIONS TO PROCESS: {len(all_unique_results)}

        CREATE A DETAILED FINANCIAL ANALYTICS REPORT:

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
        1. Use ONLY real amounts from actual emails (₹299, ₹649, etc.) - NO PLACEHOLDERS
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
    print("- Type your email query (e.g., 'May 2025 food transactions')")
    print("- Type 'auto' to get AUTOMATED ANALYSIS for ANY query! 🚀 UNIVERSAL!")
    print("- Type 'wow' to get WOW FACTOR RESPONSE that will blow your mind! 🚀 NEW!")
    print("- Type 'table' to get TRANSACTION TABLE with specific details ⭐ RECOMMENDED")
    print("- Type 'detailed' to get direct data analysis with EXACT NUMBERS")
    print("- Type 'upload' to upload sample emails")
    print("- Type 'analytics' to get comprehensive email analytics (LLM-powered)")
    print("- Type 'all' to get ALL your transactions (comprehensive LLM analysis)")
    print("- Type 'debug' to debug Mem0 configuration and limits")
    print("- Type 'test' to test Mem0 search limits")
    print("- Type 'simple' to run a simple transaction query (basic data only)")
    print("- Type 'team' to test direct team interaction")
    print("- Type 'help' to see detailed command explanations")
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
            
            elif user_input.lower() == 'all':
                print("🔍 Retrieving ALL your transactions with comprehensive search...")
                all_transactions = await get_all_user_transactions(user_id)
                if all_transactions.get('status') == 'success':
                    print(f"\n📊 COMPREHENSIVE TRANSACTION RETRIEVAL RESULTS:")
                    print(f"   - Total Transactions Found: {all_transactions.get('total_transactions', 0)}")
                    print(f"   - Search Terms Used: {all_transactions.get('search_terms_used', 0)}")
                    print(f"   - Unique Categories: {all_transactions.get('unique_categories', 0)}")
                    print(f"   - Unique Merchants: {all_transactions.get('unique_merchants', 0)}")
                    print(f"   - Transactions with Amounts: {all_transactions.get('transactions_with_amounts', 0)}")
                    print(f"   - Transactions with Dates: {all_transactions.get('transactions_with_dates', 0)}")
                    
                    print(f"\n📈 TOP CATEGORIES:")
                    for category, count in list(all_transactions.get('category_breakdown', {}).items())[:10]:
                        print(f"   - {category}: {count} transactions")
                    
                    print(f"\n🏪 TOP MERCHANTS:")
                    for merchant, count in list(all_transactions.get('merchant_breakdown', {}).items())[:10]:
                        print(f"   - {merchant}: {count} transactions")
                    
                    # Now process all transactions with the team
                    if all_transactions.get('total_transactions', 0) > 0:
                        print(f"\n🤖 Processing ALL {all_transactions['total_transactions']} transactions with Gmail Intelligence Team...")
                        team_prompt = f"""
                        PROCESS EVERY SINGLE TRANSACTION - NO EXCEPTIONS
                        
                        You have {all_transactions['total_transactions']} transactions to process.
                        
                        COMPLETE TRANSACTION DATA:
                        {json.dumps(all_transactions['all_transactions'], indent=1)}
                        
                        Create a comprehensive report showing:
                        1. Table with ALL {all_transactions['total_transactions']} transactions
                        2. Complete spending totals and averages
                        3. Category breakdown with real numbers
                        4. Merchant analysis with transaction counts
                        5. Payment method distribution
                        6. Monthly/chronological breakdown
                        
                        CRITICAL: Process EVERY transaction. If response is too long, 
                        provide summary tables with actual counts and totals.
                        
                        Transaction count verification: You MUST process exactly {all_transactions['total_transactions']} transactions.
                        """
                        
                        team_response = gmail_intelligence_team.run(team_prompt)
                        print(f"\n{team_response.content if hasattr(team_response, 'content') else str(team_response)}")
                    else:
                        print("❌ No transactions found to process.")
                else:
                    print(f"❌ Error retrieving transactions: {all_transactions.get('error', 'Unknown error')}")
            
            elif user_input.lower() == 'debug':
                print("🔧 Running Mem0 configuration and parameter debug...")
                debug_mem0_configuration()
            
            elif user_input.lower() == 'test':
                print("🧪 Testing Mem0 search limits...")
                limit_results = await test_mem0_limits(user_id)
                print(f"\n📊 Test completed. Results: {limit_results}")
            
            elif user_input.lower() == 'simple':
                print("🔍 Running simple transaction query (avoiding complex processing)...")
                try:
                    # Direct search without complex processing
                    simple_results = await search_with_retry("food order shopping", user_id, 100, max_retries=2)
                    print(f"✅ Found {len(simple_results)} results")
                    
                    if simple_results:
                        print(f"\n📊 SIMPLE RESULTS PREVIEW:")
                        for i, result in enumerate(simple_results[:10]):  # Show first 10
                            if result and isinstance(result, dict):
                                memory = result.get('memory', '')[:150] + "..." if len(result.get('memory', '')) > 150 else result.get('memory', '')
                                metadata = result.get('metadata', {})
                                merchant = metadata.get('merchant', 'Unknown') if isinstance(metadata, dict) else 'Unknown'
                                amount = metadata.get('amount', 'N/A') if isinstance(metadata, dict) else 'N/A'
                                category = metadata.get('category', 'N/A') if isinstance(metadata, dict) else 'N/A'
                                
                                print(f"   {i+1:2d}. {merchant} | {amount} | {category}")
                                print(f"       Memory: {memory}")
                                print()
                    else:
                        print("❌ No results found")
                        
                except Exception as e:
                    print(f"❌ Simple query error: {e}")
                    import traceback
                    traceback.print_exc()
            
            elif user_input.lower() == 'detailed':
                print("💰 Running detailed transaction analysis with direct data extraction...")
                try:
                    # Get comprehensive transaction data
                    detailed_results = await search_with_retry("upi payment transaction amount rupees food shopping", user_id, 200, max_retries=2)
                    print(f"✅ Found {len(detailed_results)} results for detailed analysis")
                    
                    if detailed_results:
                        # Direct data extraction and analysis
                        transaction_analysis = analyze_transactions_directly(detailed_results)
                        
                        print(f"\n📊 DETAILED TRANSACTION ANALYSIS:")
                        print(f"   - Total Transactions Analyzed: {transaction_analysis['total_count']}")
                        print(f"   - Total Amount Extracted: ₹{transaction_analysis['total_amount']:.2f}")
                        print(f"   - Average Transaction: ₹{transaction_analysis['average_amount']:.2f}")
                        print(f"   - Transactions with Amounts: {transaction_analysis['transactions_with_amounts']}")
                        
                        print(f"\n🏪 TOP MERCHANTS BY FREQUENCY:")
                        for merchant, count in transaction_analysis['top_merchants'][:10]:
                            print(f"   - {merchant}: {count} transactions")
                        
                        print(f"\n📈 CATEGORY BREAKDOWN:")
                        for category, count in transaction_analysis['categories'].items():
                            print(f"   - {category}: {count} transactions")
                        
                        print(f"\n💳 PAYMENT METHOD BREAKDOWN:")
                        for method, count in transaction_analysis['payment_methods'].items():
                            print(f"   - {method}: {count} transactions")
                        
                        print(f"\n💰 AMOUNT DISTRIBUTION:")
                        for range_desc, count in transaction_analysis['amount_ranges'].items():
                            print(f"   - {range_desc}: {count} transactions")
                        
                        print(f"\n📝 SAMPLE TRANSACTIONS WITH AMOUNTS:")
                        for tx in transaction_analysis['sample_transactions'][:5]:
                            print(f"   - {tx['merchant']} | ₹{tx['amount']} | {tx['category']} | {tx['method']}")
                        
                        # Generate comprehensive insights
                        financial_insights = extract_financial_insights(transaction_analysis, user_input)
                        print(f"\n{financial_insights}")
                    else:
                        print("❌ No transaction data found for detailed analysis")
                        
                except Exception as e:
                    print(f"❌ Detailed analysis error: {e}")
                    import traceback
                    traceback.print_exc()
            
            elif user_input.lower() == 'table':
                print("📋 Extracting transactions into detailed table format...")
                
                # Get query for table if user wants specific filtering
                table_query = input("Enter search terms (or press Enter for all transactions): ").strip()
                if not table_query:
                    table_query = "payment transaction upi food shopping amount"
                
                try:
                    # Get transaction data
                    table_results = await search_with_retry(table_query, user_id, 150, max_retries=2)
                    print(f"✅ Found {len(table_results)} transactions for table extraction")
                    
                    if table_results:
                        # Extract transactions into table format
                        transaction_table = extract_transaction_table(table_results)
                        
                        print(f"\n📊 EXTRACTED {len(transaction_table)} TRANSACTIONS")
                        
                        # Generate and display the detailed analysis with table
                        table_insights = generate_financial_insights_from_table(transaction_table)
                        print(f"\n{table_insights}")
                        
                        # Ask if user wants to see raw transaction details
                        show_raw = input("\nShow raw memory content for verification? (y/n): ").lower().strip()
                        if show_raw == 'y':
                            print(f"\n🔍 RAW TRANSACTION DETAILS (first 5):")
                            for i, tx in enumerate(transaction_table[:5], 1):
                                print(f"\n{i}. {tx['receiver']} - {tx['amount']} - {tx['purpose']}")
                                print(f"   Raw memory: {tx['raw_memory']}")
                        
                    else:
                        print("❌ No transactions found for table creation")
                        
                except Exception as e:
                    print(f"❌ Table extraction error: {e}")
                    import traceback
                    traceback.print_exc()
            
            elif user_input.lower() == 'wow':
                print("🚀 Generating WOW FACTOR response that will blow your mind!")
                wow_query = input("Enter your query (or press Enter for 'April May 2025 transactions'): ").strip()
                if not wow_query:
                    wow_query = "April May 2025 transactions"
                
                try:
                    print(f"🎯 Processing: '{wow_query}' with WOW Factor intelligence...")
                    wow_result = await query_email_database_wow(user_id, wow_query)
                    
                    if wow_result.get('status') == 'success':
                        print(f"\n{wow_result.get('wow_response', 'No WOW response generated')}")
                    else:
                        print(f"❌ WOW Factor error: {wow_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"❌ WOW Factor processing error: {e}")
                    import traceback
                    traceback.print_exc()
            
            elif user_input.lower() == 'auto':
                print("🚀 UNIVERSAL AUTOMATED ANALYSIS - Works for ANY query!")
                auto_query = input("Enter your query (risk profiling, spending analysis, etc.): ").strip()
                if not auto_query:
                    auto_query = "Do risk profiling for me"
                
                try:
                    print(f"🎯 Processing: '{auto_query}' with Universal Intelligence...")
                    
                    # Get comprehensive data with high limits
                    search_terms = [
                        "payment transaction amount rupees upi paid",
                        "food delivery order restaurant swiggy zomato", 
                        "shopping amazon flipkart purchase buy",
                        "subscription netflix spotify renewal",
                        "bill electricity utility reminder due"
                    ]
                    
                    all_transactions = []
                    seen_memories = set()
                    
                    for search_term in search_terms:
                        try:
                            results = await search_with_retry(search_term, user_id, 500, max_retries=2)
                            
                            if results:
                                for result in results:
                                    if result and isinstance(result, dict):
                                        memory_text = result.get('memory', '')
                                        if memory_text not in seen_memories and len(memory_text) > 20:
                                            all_transactions.append(result)
                                            seen_memories.add(memory_text)
                                            
                            print(f"   - '{search_term}': Found {len(results)} results, {len(all_transactions)} total unique")
                                    
                        except Exception as e:
                            print(f"❌ Search error for '{search_term}': {e}")
                    
                    print(f"📊 TOTAL DATA RETRIEVED: {len(all_transactions)} unique transactions")
                    
                    if all_transactions:
                        # Direct analysis
                        analysis = analyze_transactions_directly(all_transactions)
                        
                        # Generate risk profiling response
                        if "risk" in auto_query.lower():
                            print("🎯 Generating RISK PROFILING with real data...")
                            
                            total_amount = analysis['total_amount']
                            total_count = analysis['total_count']
                            avg_amount = analysis['average_amount']
                            
                            # Calculate risk score
                            risk_score = 5
                            if avg_amount > 2000: risk_score += 2
                            elif avg_amount < 500: risk_score -= 1
                            
                            high_value = analysis['amount_ranges'].get('Over ₹5000', 0)
                            if high_value > 5: risk_score += 2
                            
                            category_diversity = len(analysis['categories'])
                            if category_diversity > 8: risk_score += 1
                            
                            upi_count = analysis['payment_methods'].get('UPI', 0)
                            digital_adoption = (upi_count / total_count) * 100 if total_count > 0 else 0
                            if digital_adoption > 70: risk_score += 1
                            
                            risk_score = min(10, max(1, risk_score))
                            
                            if risk_score <= 3:
                                risk_profile = "Conservative"
                            elif risk_score <= 6:
                                risk_profile = "Moderate"
                            else:
                                risk_profile = "Aggressive"
                            
                            print(f"""
# 🎯 COMPREHENSIVE RISK PROFILING REPORT
## Based on Analysis of {total_count} Transactions (₹{total_amount:,.2f})

### 💎 YOUR FINANCIAL RISK PROFILE

**🏆 RISK SCORE: {risk_score}/10**
**📊 RISK CATEGORY: {risk_profile}**

### 📈 RISK ASSESSMENT BREAKDOWN

**💰 SPENDING BEHAVIOR ANALYSIS:**
- **Average Transaction**: ₹{avg_amount:,.2f}
- **High-Value Transactions**: {high_value} transactions over ₹5,000
- **Category Diversity**: {category_diversity} different spending categories
- **Digital Adoption**: {digital_adoption:.1f}% UPI usage

**🚀 INVESTMENT RECOMMENDATIONS:**

Based on your {risk_profile} risk profile:
- **Recommended SIP**: ₹{min(total_amount * 0.1, 25000):.0f}/month
- **Emergency Fund**: ₹{total_amount * 6:.0f} (6 months expenses)
- **Risk Tolerance**: {risk_profile} investor

**🎯 NEXT STEPS:**
1. Start SIP with ₹{min(total_amount * 0.1, 25000):.0f}/month
2. Build emergency fund of ₹{total_amount * 6:.0f}
3. Consider {risk_profile.lower()} investment options

*Analysis based on {total_count} actual transactions from your Gmail data.*
""")
                        else:
                            # General analysis
                            insights = extract_financial_insights(analysis, auto_query)
                            print(f"\n{insights}")
                    else:
                        print("❌ No transaction data found for analysis")
                        
                except Exception as e:
                    print(f"❌ Universal analysis error: {e}")
                    import traceback
                    traceback.print_exc()
            
            elif user_input.lower() == 'help':
                print("📖 COMMAND EXPLANATIONS:")
                print()
                print("🔍 QUERY COMMANDS:")
                print("  • Natural language query: Ask specific questions about your transactions")
                print("    Example: 'Show me food orders in May 2025'")
                print("    Example: 'UPI transactions over ₹500'")
                print()
                print("📊 ANALYSIS COMMANDS:")
                print("  • 'wow' - 🚀 WOW FACTOR: Mind-blowing financial intelligence report!")
                print("    ✅ Complete financial DNA analysis with personality insights")
                print("    ✅ Behavioral psychology and spending patterns")
                print("    ✅ Predictive intelligence and future forecasting")
                print("    ✅ Exclusive insights you can't get anywhere else")
                print("    ✅ Makes you think: 'How did Gmail know all this about me?!'")
                print()
                print("  • 'table' - ⭐ BEST OPTION: Complete transaction table with specific details")
                print("    ✅ Proper table format: Date | Amount | Receiver | Purpose | Payment Method")
                print("    ✅ Real extracted data from each transaction")
                print("    ✅ Specific financial insights and recommendations")
                print("    ✅ Verifiable transaction details")
                print()
                print("  • 'detailed' - Direct data extraction with EXACT NUMBERS")
                print("    ✅ Real amounts, counts, averages, percentages")
                print("    ✅ Actual merchant names and categories")
                print("    ✅ Specific insights and recommendations")
                print("    ✅ No vague placeholders")
                print()
                print("  • 'all' - Comprehensive LLM analysis of ALL transactions")
                print("    ⚠️ May provide generic responses")
                print("    ⚠️ Dependent on LLM processing quality")
                print()
                print("  • 'analytics' - Email analytics with pattern analysis")
                print("    ⚠️ May include placeholders instead of real numbers")
                print()
                print("  • 'simple' - Basic transaction preview (first 10 results)")
                print("    ℹ️ Quick overview without detailed analysis")
                print()
                print("🔧 DEBUG COMMANDS:")
                print("  • 'debug' - Check Mem0 configuration and connection")
                print("  • 'test' - Test search limits to see how many transactions you have")
                print("  • 'upload' - Add sample transaction data for testing")
                print()
                print("💡 FOR BEST RESULTS:")
                print("  1. Use 'wow' command for the most impressive financial intelligence report")
                print("  2. Use 'table' command to see individual transactions in proper format")
                print("  3. Use 'detailed' command for aggregate analysis and calculations")
                print("  4. Use natural language queries for specific date ranges or merchants")
                print("  5. Use 'test' first to verify your transaction count")
                print()
            
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

# ************* WOW Factor Response Generator *************

def create_wow_factor_response(transaction_data: List[Dict], query: str, user_id: str) -> str:
    """Create a mind-blowing response that makes users think 'DAMN, that's powerful!'"""
    
    # Extract real data first
    analysis = analyze_transactions_directly(transaction_data)
    table = extract_transaction_table(transaction_data)
    
    # Calculate advanced metrics
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    avg_amount = analysis['average_amount']
    
    # Time-based analysis
    from datetime import datetime
    import calendar
    
    # Merchant analysis
    top_merchants = analysis['top_merchants'][:5]
    categories = analysis['categories']
    
    # Create the WOW response
    response = f"""
# 🚀 GMAIL FINANCIAL INTELLIGENCE REPORT 🚀
## Query: "{query}"

### 💎 YOUR FINANCIAL DNA DECODED
**🎯 INSTANT POWER INSIGHTS:**
- 💰 **Total Financial Footprint**: ₹{total_amount:,.2f} across {total_count} transactions
- 📊 **Your Spending Velocity**: ₹{avg_amount:,.2f} per transaction
- 🏆 **Financial Activity Level**: {total_count} transactions = {'High' if total_count > 50 else 'Moderate' if total_count > 20 else 'Conservative'} spender
- ⚡ **Money Flow Pattern**: {'Consistent' if len(set(analysis['categories'].keys())) > 5 else 'Focused'} across {len(analysis['categories'])} categories
- 🎪 **Spending Personality**: {'Diversified Explorer' if len(analysis['merchants']) > 10 else 'Brand Loyal' if len(analysis['merchants']) < 5 else 'Balanced Shopper'}

### 📋 COMPLETE TRANSACTION INTELLIGENCE
"""
    
    # Add transaction table
    if table:
        response += """
| 📅 Date | 💰 Amount | 🏪 Merchant | 🎯 Category | 💳 Method | 🔍 Smart Insight |
|----------|-----------|-------------|-------------|-----------|------------------|
"""
        for i, tx in enumerate(table[:15]):  # Show top 15 transactions
            insight = ""
            if tx['amount_numeric'] > avg_amount * 2:
                insight = "🔥 Big Spender Alert!"
            elif tx['purpose'] == 'Food Order' and tx['amount_numeric'] > 500:
                insight = "🍔 Premium Foodie"
            elif tx['payment_method'] == 'UPI':
                insight = "⚡ Digital Native"
            else:
                insight = "💫 Regular Purchase"
                
            response += f"| {tx['date'][:10]} | {tx['amount']} | {tx['receiver'][:15]} | {tx['purpose'][:12]} | {tx['payment_method'][:8]} | {insight} |\n"
    
    # Category Intelligence
    response += f"""

### 🎯 CATEGORY INTELLIGENCE MATRIX
"""
    
    # Food analysis
    food_data = {k: v for k, v in categories.items() if 'food' in k.lower() or 'delivery' in k.lower()}
    if food_data:
        food_total = sum(food_data.values())
        food_percentage = (food_total / total_count) * 100
        response += f"""
**🍔 FOOD & DINING EMPIRE**
- **Food Addiction Level**: {food_total} orders ({food_percentage:.1f}% of all transactions)
- **Dining Frequency**: You order food every {max(1, 30//food_total)} days on average
- **🔥 FOOD INSIGHT**: You're a {'Heavy' if food_percentage > 30 else 'Moderate' if food_percentage > 15 else 'Light'} food delivery user
- **💡 OPTIMIZATION**: Cook {max(1, food_total//4)} meals/week → Save ₹{food_total * 200:.0f}/month
"""
    
    # Shopping analysis
    shopping_merchants = [m for m, c in top_merchants if any(shop in m.lower() for shop in ['amazon', 'flipkart', 'myntra', 'shopping'])]
    if shopping_merchants:
        response += f"""
**🛒 SHOPPING PSYCHOLOGY**
- **E-commerce Dependency**: {len(shopping_merchants)} major platforms
- **Shopping Frequency**: {sum(c for m, c in shopping_merchants)} orders
- **🔥 SHOPPING INSIGHT**: You're a {'Serial' if len(shopping_merchants) > 3 else 'Selective'} online shopper
- **💡 STRATEGY**: Use price comparison tools → Save 15-20% on purchases
"""
    
    # UPI analysis
    upi_count = analysis['payment_methods'].get('UPI', 0) + analysis['payment_methods'].get('upi', 0)
    if upi_count > 0:
        upi_percentage = (upi_count / total_count) * 100
        response += f"""
**💳 DIGITAL PAYMENT MASTERY**
- **UPI Adoption**: {upi_count} transactions ({upi_percentage:.1f}%) - You're digitally advanced!
- **Payment Efficiency**: {'Cashless Champion' if upi_percentage > 70 else 'Digital Adopter' if upi_percentage > 40 else 'Traditional Mix'}
- **🔥 PAYMENT INSIGHT**: You save ~₹{upi_count * 5:.0f}/year in cash handling costs
"""
    
    # Behavioral insights
    response += f"""

### 🧠 BEHAVIORAL FINANCIAL PSYCHOLOGY
**🎭 YOUR SPENDING PERSONALITY REVEALED:**
- **Decision Style**: {'Impulse Buyer' if avg_amount < 500 else 'Calculated Spender' if avg_amount > 2000 else 'Balanced Purchaser'}
- **Brand Loyalty**: {'High' if len(analysis['merchants']) < total_count/3 else 'Low'} - You {'stick to favorites' if len(analysis['merchants']) < total_count/3 else 'love variety'}
- **Financial Discipline**: {'Excellent' if len(analysis['amount_ranges']) > 3 else 'Good'} spending distribution
- **Risk Profile**: {'Conservative' if analysis['amount_ranges'].get('Under ₹100', 0) > total_count/2 else 'Aggressive' if analysis['amount_ranges'].get('Over ₹5000', 0) > 5 else 'Moderate'}

**🔮 PREDICTIVE INSIGHTS:**
- **Monthly Burn Rate**: ₹{total_amount:,.0f} (Based on current pattern)
- **Annual Projection**: ₹{total_amount * 12:,.0f} if spending continues
- **Savings Potential**: ₹{total_amount * 0.15:,.0f}/month with optimization
"""
    
    # Exclusive insights
    response += f"""

### 💎 EXCLUSIVE INSIGHTS (The WOW Factor!)
**🔥 HIDDEN PATTERNS DISCOVERED:**
- **Your Financial Fingerprint**: {total_count} transactions reveal you're a {'Tech-Savvy Urban Professional' if upi_count > total_count/2 else 'Traditional Spender'}
- **Spending Rhythm**: You make {total_count//30 if total_count > 30 else 1} transactions per day on average
- **Value Consciousness**: {'Price-sensitive' if analysis['amount_ranges'].get('Under ₹500', 0) > total_count/2 else 'Value-focused' if avg_amount < 1000 else 'Premium-oriented'}
- **Digital Maturity**: {'Advanced' if upi_count > total_count * 0.7 else 'Moderate' if upi_count > total_count * 0.3 else 'Traditional'} digital payment adoption

**🎪 FINANCIAL PERSONALITY PROFILE:**
- **Spending Style**: {analysis['categories']} categories show you're a {'Diversified' if len(analysis['categories']) > 5 else 'Focused'} spender
- **Transaction Behavior**: {'Frequent small purchases' if avg_amount < 500 else 'Occasional big purchases' if avg_amount > 2000 else 'Balanced spending pattern'}
- **Financial Habits**: {'Organized' if len(analysis['payment_methods']) < 4 else 'Flexible'} payment preferences
"""
    
    # Actionable intelligence
    response += f"""

### 🏆 ACTIONABLE INTELLIGENCE DASHBOARD
**⚡ IMMEDIATE ACTIONS (Next 7 Days)**
1. **💰 Quick Win**: Switch to cashback cards for top category → Save ₹{total_amount * 0.02:.0f}/month
2. **📊 Optimization**: Review {len([m for m, c in top_merchants if c == 1])} single-purchase merchants → Consolidate orders
3. **🎯 Focus**: Your top spending is {max(categories.items(), key=lambda x: x[1])[0]} → Set budget alerts

**🚀 STRATEGIC MOVES (Next 30 Days)**
1. **Budget Restructuring**: Allocate ₹{total_amount * 0.6:.0f} for essentials, ₹{total_amount * 0.4:.0f} for lifestyle
2. **Reward Maximization**: Use specific cards for your top 3 categories → Earn ₹{total_amount * 0.03:.0f} in rewards
3. **Spending Optimization**: Reduce {max(categories.items(), key=lambda x: x[1])[0]} by 20% → Save ₹{total_amount * 0.2:.0f}

**💡 EXCLUSIVE RECOMMENDATIONS:**
- **Your Spending Sweet Spot**: ₹{avg_amount:.0f} per transaction is {'optimal' if 200 <= avg_amount <= 1000 else 'high' if avg_amount > 1000 else 'low'}
- **Financial Health Score**: {min(10, max(1, int((total_count/10) + (len(analysis['categories'])/2))))}/10 based on transaction diversity
- **Savings Opportunity**: ₹{total_amount * 0.25:.0f}/month potential savings identified
"""
    
    # Smart alerts
    food_percentage = 0
    upi_percentage = 0
    if food_data:
        food_percentage = (sum(food_data.values()) / total_count) * 100
    if upi_count > 0:
        upi_percentage = (upi_count / total_count) * 100
        
    response += f"""

### 📱 SMART FINANCIAL ALERTS
- **🚨 Pattern Alert**: You spend {food_percentage:.0f}% on food delivery - Consider meal prep
- **💎 Opportunity**: Your UPI usage ({upi_percentage:.0f}%) qualifies for premium cashback cards
- **⚡ Efficiency**: Consolidate purchases from {len(analysis['merchants'])} merchants → Reduce to top 5
- **🎯 Goal Setting**: Based on your ₹{avg_amount:.0f} average, set ₹{avg_amount * 1.2:.0f} transaction alerts

### 🔮 FINANCIAL FORTUNE TELLING
**📊 NEXT 30 DAYS PREDICTION:**
- **Expected Spending**: ₹{total_amount * 1.1:.0f} (10% seasonal increase)
- **High-Risk Categories**: {max(categories.items(), key=lambda x: x[1])[0]} likely to spike
- **Savings Target**: ₹{total_amount * 0.15:.0f} achievable with current patterns
- **Reward Potential**: ₹{total_amount * 0.025:.0f} in cashback/rewards possible

---

## 🎯 THE BOTTOM LINE
**Your Gmail emails revealed {total_count} financial decisions totaling ₹{total_amount:,.2f}**

You're a {analysis['categories']} spender with {len(analysis['merchants'])} merchant relationships, showing {'excellent' if len(analysis['categories']) > 5 else 'good'} financial diversity. Your ₹{avg_amount:.0f} average transaction suggests {'premium' if avg_amount > 1000 else 'value-conscious'} spending habits.

**🚀 Key Takeaway**: You have ₹{total_amount * 0.2:.0f}/month optimization potential while maintaining your lifestyle!

*How did Gmail Insights decode all this from your emails? That's the power of AI financial intelligence!* 🤖✨
"""
    
    return response

# ************* Enhanced Query Function *************

async def query_email_database_wow(user_id: str, query: str, limit: int = 1000) -> Dict[str, Any]:
    """Enhanced query function that uses the WOW factor response generator"""
    try:
        print(f"🚀 WOW Factor Gmail Intelligence: Processing query '{query}' for user {user_id}")
        
        # Get comprehensive search results
        search_results = await search_emails_in_mem0(user_id, query, limit)
        
        # Extract transaction data with null checks
        transaction_data = []
        for i, result in enumerate(search_results):
            if result and isinstance(result, dict):
                transaction_info = {
                    "index": i + 1,
                    "memory": result.get('memory', '') if result.get('memory') else '',
                    "metadata": result.get('metadata', {}) if result.get('metadata') else {},
                    "score": result.get('score', 0) if result.get('score') is not None else 0
                }
                transaction_data.append(transaction_info)
        
        print(f"📊 WOW FACTOR: Processing {len(transaction_data)} transactions for mind-blowing insights")
        
        # Generate WOW factor response
        wow_response = create_wow_factor_response(transaction_data, query, user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "query": query,
            "results_count": len(search_results),
            "wow_response": wow_response,
            "debug_info": {
                "total_results_found": len(search_results),
                "limit_used": limit,
                "transaction_data_prepared": len(transaction_data)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ WOW Factor query error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }

# ************* Universal Automated Analysis System *************

async def universal_gmail_analysis(user_id: str, query: str) -> Dict[str, Any]:
    """Universal automated analysis system that works for ANY query type"""
    try:
        print(f"🚀 UNIVERSAL ANALYSIS: Processing '{query}' for user {user_id}")
        
        # Step 1: Get comprehensive transaction data with high limits
        print("📊 Step 1: Comprehensive data retrieval...")
        
        # Use multiple broad search terms to get ALL relevant data
        search_terms = [
            "payment transaction amount rupees upi paid",
            "food delivery order restaurant swiggy zomato",
            "shopping amazon flipkart purchase buy",
            "subscription netflix spotify renewal",
            "bill electricity utility reminder due",
            "investment mutual fund sip trading",
            "insurance premium policy health life",
            "travel booking flight hotel uber ola",
            "entertainment movie ticket bookmyshow",
            "₹ Rs rupees money cost price total",
            "2024 2025 january february march april may june",
            "credit debit card bank transfer netbanking"
        ]
        
        all_transactions = []
        seen_memories = set()
        
        for search_term in search_terms:
            try:
                results = await search_with_retry(search_term, user_id, 1000, max_retries=2)  # High limit
                
                if results:
                    for result in results:
                        if result and isinstance(result, dict):
                            memory_text = result.get('memory', '')
                            if memory_text not in seen_memories and len(memory_text) > 20:
                                all_transactions.append(result)
                                seen_memories.add(memory_text)
                                
                print(f"   - '{search_term}': Found {len(results)} results, {len(all_transactions)} total unique")
                        
            except Exception as e:
                print(f"❌ Search error for '{search_term}': {e}")
        
        print(f"📊 TOTAL DATA RETRIEVED: {len(all_transactions)} unique transactions")
        
        # Step 2: Direct data analysis
        print("🔍 Step 2: Direct data extraction and analysis...")
        analysis = analyze_transactions_directly(all_transactions)
        table = extract_transaction_table(all_transactions)
        
        # Step 3: Query-specific analysis
        print(f"🎯 Step 3: Query-specific analysis for '{query}'...")
        
        # Determine analysis type based on query
        query_lower = query.lower()
        analysis_type = "general"
        
        if any(word in query_lower for word in ["risk", "profile", "profiling", "assessment"]):
            analysis_type = "risk_profiling"
        elif any(word in query_lower for word in ["spending", "expense", "budget", "money"]):
            analysis_type = "spending_analysis"
        elif any(word in query_lower for word in ["food", "delivery", "restaurant"]):
            analysis_type = "food_analysis"
        elif any(word in query_lower for word in ["subscription", "recurring", "monthly"]):
            analysis_type = "subscription_analysis"
        elif any(word in query_lower for word in ["investment", "mutual", "fund", "sip"]):
            analysis_type = "investment_analysis"
        elif any(word in query_lower for word in ["april", "may", "march", "month"]):
            analysis_type = "monthly_analysis"
        
        # Step 4: Generate intelligent response based on analysis type
        print(f"📝 Step 4: Generating {analysis_type} response...")
        
        response = generate_intelligent_response(
            query=query,
            analysis_type=analysis_type,
            analysis=analysis,
            table=table,
            all_transactions=all_transactions,
            user_id=user_id
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "query": query,
            "analysis_type": analysis_type,
            "total_transactions": len(all_transactions),
            "response": response,
            "debug_info": {
                "search_terms_used": len(search_terms),
                "unique_transactions_found": len(all_transactions),
                "analysis_summary": {
                    "total_amount": analysis['total_amount'],
                    "transaction_count": analysis['total_count'],
                    "categories": len(analysis['categories']),
                    "merchants": len(analysis['merchants'])
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Universal analysis error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }

def generate_intelligent_response(query: str, analysis_type: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict], user_id: str) -> str:
    """Generate intelligent response based on analysis type and real data"""
    
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    avg_amount = analysis['average_amount']
    categories = analysis['categories']
    merchants = analysis['merchants']
    payment_methods = analysis['payment_methods']
    
    if analysis_type == "risk_profiling":
        return generate_risk_profiling_response(query, analysis, table, all_transactions)
    elif analysis_type == "spending_analysis":
        return generate_spending_analysis_response(query, analysis, table, all_transactions)
    elif analysis_type == "food_analysis":
        return generate_food_analysis_response(query, analysis, table, all_transactions)
    elif analysis_type == "subscription_analysis":
        return generate_subscription_analysis_response(query, analysis, table, all_transactions)
    elif analysis_type == "investment_analysis":
        return generate_investment_analysis_response(query, analysis, table, all_transactions)
    elif analysis_type == "monthly_analysis":
        return generate_monthly_analysis_response(query, analysis, table, all_transactions)
    else:
        return generate_general_analysis_response(query, analysis, table, all_transactions)

def generate_risk_profiling_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate comprehensive risk profiling based on actual transaction data"""
    
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    avg_amount = analysis['average_amount']
    
    # Calculate risk metrics
    high_value_transactions = analysis['amount_ranges'].get('Over ₹5000', 0)
    low_value_transactions = analysis['amount_ranges'].get('Under ₹100', 0)
    
    # Risk scoring
    risk_score = 5  # Base score
    
    # Adjust based on spending patterns
    if avg_amount > 2000:
        risk_score += 2  # Higher spending = higher risk tolerance
    elif avg_amount < 500:
        risk_score -= 1  # Lower spending = more conservative
    
    if high_value_transactions > 5:
        risk_score += 2  # Frequent high-value transactions
    
    if low_value_transactions > total_count * 0.5:
        risk_score -= 1  # Many small transactions = conservative
    
    # Diversification score
    category_diversity = len(analysis['categories'])
    merchant_diversity = len(analysis['merchants'])
    
    if category_diversity > 8:
        risk_score += 1  # Good diversification
    if merchant_diversity > 15:
        risk_score += 1  # Good merchant diversification
    
    # Payment method analysis
    upi_count = analysis['payment_methods'].get('UPI', 0) + analysis['payment_methods'].get('upi', 0)
    digital_adoption = (upi_count / total_count) * 100 if total_count > 0 else 0
    
    if digital_adoption > 70:
        risk_score += 1  # High digital adoption = tech-savvy
    
    risk_score = min(10, max(1, risk_score))  # Keep between 1-10
    
    # Risk profile classification
    if risk_score <= 3:
        risk_profile = "Conservative"
        risk_description = "Low risk tolerance, prefers stable investments"
    elif risk_score <= 6:
        risk_profile = "Moderate"
        risk_description = "Balanced approach to risk and returns"
    else:
        risk_profile = "Aggressive"
        risk_description = "High risk tolerance, seeks higher returns"
    
    response = f"""
# 🎯 COMPREHENSIVE RISK PROFILING REPORT
## Based on Analysis of {total_count} Transactions (₹{total_amount:,.2f})

### 💎 YOUR FINANCIAL RISK PROFILE

**🏆 RISK SCORE: {risk_score}/10**
**📊 RISK CATEGORY: {risk_profile}**
**💡 PROFILE DESCRIPTION: {risk_description}**

### 📈 RISK ASSESSMENT BREAKDOWN

**💰 SPENDING BEHAVIOR ANALYSIS:**
- **Average Transaction**: ₹{avg_amount:,.2f}
- **High-Value Transactions**: {high_value_transactions} transactions over ₹5,000
- **Small Transactions**: {low_value_transactions} transactions under ₹100
- **Spending Consistency**: {'Stable' if len(analysis['amount_ranges']) > 3 else 'Variable'}

**🎯 DIVERSIFICATION ANALYSIS:**
- **Category Spread**: {category_diversity} different spending categories
- **Merchant Diversity**: {merchant_diversity} different merchants
- **Diversification Score**: {'Excellent' if category_diversity > 8 else 'Good' if category_diversity > 5 else 'Limited'}

**💳 DIGITAL ADOPTION:**
- **UPI Usage**: {upi_count} transactions ({digital_adoption:.1f}%)
- **Digital Maturity**: {'Advanced' if digital_adoption > 70 else 'Moderate' if digital_adoption > 40 else 'Traditional'}
- **Tech Comfort Level**: {'High' if digital_adoption > 60 else 'Medium' if digital_adoption > 30 else 'Low'}

### 🔍 DETAILED RISK FACTORS

**✅ POSITIVE RISK INDICATORS:**
"""
    
    # Add positive indicators
    positive_indicators = []
    if category_diversity > 6:
        positive_indicators.append(f"- Good spending diversification across {category_diversity} categories")
    if digital_adoption > 50:
        positive_indicators.append(f"- High digital payment adoption ({digital_adoption:.1f}%)")
    if avg_amount > 500 and avg_amount < 2000:
        positive_indicators.append(f"- Balanced average transaction size (₹{avg_amount:.0f})")
    if merchant_diversity > 10:
        positive_indicators.append(f"- Good merchant diversification ({merchant_diversity} merchants)")
    
    for indicator in positive_indicators:
        response += f"\n{indicator}"
    
    response += f"""

**⚠️ RISK CONSIDERATIONS:**
"""
    
    # Add risk considerations
    risk_considerations = []
    if high_value_transactions > 10:
        risk_considerations.append(f"- Frequent high-value transactions ({high_value_transactions} over ₹5,000)")
    if avg_amount > 3000:
        risk_considerations.append(f"- High average spending (₹{avg_amount:.0f}) indicates aggressive spending")
    if category_diversity < 4:
        risk_considerations.append(f"- Limited spending categories ({category_diversity}) - consider diversification")
    if digital_adoption < 30:
        risk_considerations.append(f"- Low digital adoption ({digital_adoption:.1f}%) - may miss tech opportunities")
    
    for consideration in risk_considerations:
        response += f"\n{consideration}"
    
    # Investment recommendations based on risk profile
    response += f"""

### 🚀 INVESTMENT RECOMMENDATIONS

**Based on your {risk_profile} risk profile:**

"""
    
    if risk_profile == "Conservative":
        response += """
**💰 CONSERVATIVE INVESTMENT STRATEGY:**
- **Fixed Deposits**: 40-50% allocation for stability
- **Government Bonds**: 20-30% for guaranteed returns
- **Large-cap Mutual Funds**: 15-20% for steady growth
- **Emergency Fund**: 6-12 months of expenses in liquid funds
- **Gold/Silver**: 5-10% as hedge against inflation

**📊 Expected Returns**: 6-8% annually with low volatility
**⏰ Investment Horizon**: Focus on capital preservation
"""
    elif risk_profile == "Moderate":
        response += """
**⚖️ BALANCED INVESTMENT STRATEGY:**
- **Equity Mutual Funds**: 50-60% (mix of large and mid-cap)
- **Debt Funds**: 25-30% for stability
- **ELSS Funds**: 10-15% for tax saving
- **International Funds**: 5-10% for global exposure
- **Emergency Fund**: 6 months expenses

**📊 Expected Returns**: 8-12% annually with moderate volatility
**⏰ Investment Horizon**: 5-10 years for optimal growth
"""
    else:  # Aggressive
        response += """
**🚀 AGGRESSIVE INVESTMENT STRATEGY:**
- **Small & Mid-cap Funds**: 40-50% for high growth
- **Large-cap Equity**: 25-30% for stability
- **Sectoral/Thematic Funds**: 10-15% for targeted exposure
- **International Equity**: 10-15% for global diversification
- **Crypto/Alternative**: 5% for high-risk, high-reward

**📊 Expected Returns**: 12-18% annually with high volatility
**⏰ Investment Horizon**: 10+ years for wealth creation
"""
    
    # Specific recommendations based on spending patterns
    response += f"""

### 🎯 PERSONALIZED RECOMMENDATIONS

**Based on your spending pattern of ₹{total_amount:,.0f}:**

**💡 MONTHLY INVESTMENT CAPACITY:**
- **Recommended SIP Amount**: ₹{min(total_amount * 0.2, 50000):.0f}/month
- **Emergency Fund Target**: ₹{total_amount * 6:.0f} (6 months expenses)
- **Insurance Coverage**: ₹{total_amount * 120:.0f} (10x annual expenses)

**🔥 IMMEDIATE ACTION ITEMS:**
1. **Start SIP**: Begin with ₹{min(total_amount * 0.1, 25000):.0f}/month in {risk_profile.lower()} funds
2. **Build Emergency Fund**: Save ₹{total_amount * 0.15:.0f}/month for 6 months
3. **Review Insurance**: Ensure adequate life and health coverage
4. **Tax Planning**: Invest ₹1.5L in ELSS for 80C benefits

**📊 PORTFOLIO ALLOCATION FOR YOU:**
"""
    
    # Show specific allocation based on their spending
    if risk_profile == "Conservative":
        response += f"""
- **Debt/FD**: ₹{min(total_amount * 0.4, 200000):.0f} (40%)
- **Large-cap Equity**: ₹{min(total_amount * 0.3, 150000):.0f} (30%)
- **Gold**: ₹{min(total_amount * 0.1, 50000):.0f} (10%)
- **Liquid Fund**: ₹{min(total_amount * 0.2, 100000):.0f} (20%)
"""
    elif risk_profile == "Moderate":
        response += f"""
- **Equity Funds**: ₹{min(total_amount * 0.6, 300000):.0f} (60%)
- **Debt Funds**: ₹{min(total_amount * 0.25, 125000):.0f} (25%)
- **International**: ₹{min(total_amount * 0.1, 50000):.0f} (10%)
- **Emergency Fund**: ₹{min(total_amount * 0.05, 25000):.0f} (5%)
"""
    else:
        response += f"""
- **Growth Equity**: ₹{min(total_amount * 0.7, 350000):.0f} (70%)
- **International**: ₹{min(total_amount * 0.15, 75000):.0f} (15%)
- **Sectoral Funds**: ₹{min(total_amount * 0.1, 50000):.0f} (10%)
- **Alternative**: ₹{min(total_amount * 0.05, 25000):.0f} (5%)
"""
    
    response += f"""

### 📱 RISK MONITORING DASHBOARD

**🚨 MONTHLY REVIEW CHECKLIST:**
- [ ] Track portfolio performance vs benchmark
- [ ] Rebalance if allocation deviates >5%
- [ ] Review and adjust SIP amounts
- [ ] Monitor expense ratios and fund performance

**⚡ RISK ALERTS:**
- **Concentration Risk**: Don't put >10% in single stock/fund
- **Liquidity Risk**: Keep 6 months expenses liquid
- **Inflation Risk**: Ensure 70%+ in equity for long-term
- **Currency Risk**: Limit international exposure to 20%

---

## 🎯 FINAL RISK ASSESSMENT

**Your {risk_profile} profile with {risk_score}/10 risk score suggests:**

You're a {risk_description.lower()} investor who should focus on {'capital preservation with moderate growth' if risk_profile == 'Conservative' else 'balanced growth with managed risk' if risk_profile == 'Moderate' else 'aggressive wealth creation with high growth potential'}.

**🚀 Next Steps**: Start with a ₹{min(total_amount * 0.1, 25000):.0f}/month SIP in {risk_profile.lower()} funds and build your emergency fund simultaneously.

*This analysis is based on your actual spending patterns from {total_count} transactions. Consult a financial advisor for personalized advice.*
"""
    
    return response

# ************* Other Analysis Response Generators *************

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
    print("4. WOW Factor Demo (NEW!)")
    
    choice = input("Enter choice (1-4): ").strip()
    
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
    elif choice == "4":
        print("🚀 WOW Factor Demo - Mind-blowing Gmail Insights!")
        user_id = input("Enter user ID (or press Enter for 'demo_user'): ").strip() or "demo_user"
        query = input("Enter your query (or press Enter for 'April May 2025 transactions'): ").strip() or "April May 2025 transactions"
        print(f"\n🎯 Generating WOW Factor response for: '{query}'")
        result = asyncio.run(query_email_database_wow(user_id, query))
        if result.get('status') == 'success':
            print(f"\n{result.get('wow_response', 'No response generated')}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    else:
        print("Invalid choice. Please run again and select 1-4.")

# ************* Integration Functions for WebSocket and Main App *************

async def query_mem0(user_id: str, query: str) -> str:
    """
    Main query function for WebSocket integration
    Integrates Query Analyzer → Mem0 Search → AI Response
    """
    try:
        print(f"🔍 Processing query for user {user_id}: '{query}'")
        print(f"🔑 Using Mem0 API Key: {MEM0_API_KEY[:8]}...{MEM0_API_KEY[-4:] if len(MEM0_API_KEY) > 12 else MEM0_API_KEY}")
        
        # Step 1: Analyze and refine query using Query Analyzer Agent
        refined_query = await analyze_and_refine_query(query)
        print(f"📝 Refined query: '{refined_query}'")
        
        # Step 2: Query Gmail Intelligence Team with refined query
        result = await query_email_database(user_id, refined_query, limit=1000)
        
        if result.get('status') == 'success':
            return result.get('team_response', 'No response generated')
        else:
            return f"❌ Error processing query: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        print(f"❌ Error in query_mem0: {e}")
        return f"❌ Sorry, I encountered an error while processing your query: {str(e)}"

async def analyze_and_refine_query(query: str) -> str:
    """
    Use Query Analyzer Agent to refine user queries - PRESERVING USER INTENT
    """
    try:
        # Check for specific intent patterns that should NOT be heavily refined
        query_lower = query.lower()
        
        # If user is asking for recent/latest/last emails, preserve that intent
        if any(word in query_lower for word in ["last", "latest", "recent", "newest", "most recent"]):
            if any(word in query_lower for word in ["email", "mail", "message"]):
                # For recent email queries, use timestamp-based search terms
                return f"recent latest newest {query}"
        
        # If user is asking for specific email analysis, preserve specificity
        if any(word in query_lower for word in ["insight", "analysis", "about", "details"]) and any(word in query_lower for word in ["email", "mail"]):
            # Don't over-refine analysis requests
            return query
        
        # For general queries, do light refinement
        from app.query_analyzer_agent import queryAnalyzerAgent
        
        # Create a better prompt that preserves intent
        analysis_prompt = f"""
        Analyze this user query and provide a LIGHTLY refined search query for Gmail email data.
        
        CRITICAL: If the user is asking for recent/latest/last emails, preserve that intent.
        CRITICAL: If the user is asking for specific insights or analysis, preserve the specificity.
        
        Original Query: "{query}"
        
        Your task:
        1. Identify the user's intent (recent emails, specific analysis, transaction search, etc.)
        2. If asking for recent emails, include temporal terms
        3. If asking for analysis, preserve the analytical intent
        4. Add relevant email-related keywords only if needed
        
        Return ONLY a refined search query that preserves the original intent.
        
        Examples:
        - "last email" → "latest recent newest email"
        - "insight about last email" → "recent latest email analysis insight"
        - "food expenses" → "food delivery swiggy zomato restaurant payment"
        """
        
        # Get refined query from analyzer agent
        response = queryAnalyzerAgent.run(analysis_prompt)
        
        # Extract the refined query from the response
        if hasattr(response, 'content'):
            refined_query = response.content.strip()
        else:
            refined_query = str(response).strip()
        
        # Clean up the response to get just the query
        lines = refined_query.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('*') and len(line) > 10:
                # Final check - don't let it become too generic
                if line.lower() not in ["based on the analysis", "analysis", "email analysis"]:
                    return line
        
        # If refinement failed or became too generic, return original query
        print(f"⚠️ Query refinement resulted in generic response, using original query")
        return query
        
    except Exception as e:
        print(f"⚠️ Query analysis failed, using original query: {e}")
        return query

async def process_gmail_data_for_user(user_id: str, gmail_emails: List[Dict]) -> Dict[str, Any]:
    """
    Process Gmail data for a specific user (called from main.py)
    Automatically uses the signed-in user's user_id
    """
    try:
        print(f"🎯 Processing Gmail data for signed-in user: {user_id}")
        
        # Use the existing process_gmail_data function
        result = await process_gmail_data(user_id, gmail_emails)
        
        # Update user status in database to mark Gmail sync as complete
        from app.db import users_collection
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "initial_gmailData_sync": True,
                "fetched_email": True,
                "last_sync_timestamp": datetime.now().isoformat()
            }}
        )
        
        print(f"✅ Gmail data processed and user status updated for {user_id}")
        return result
        
    except Exception as e:
        print(f"❌ Error processing Gmail data for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

# ************* Enhanced WebSocket Integration *************

async def handle_websocket_query(user_id: str, query: str, chat_id: str = None) -> Dict[str, Any]:
    """
    Enhanced WebSocket query handler with full pipeline
    """
    try:
        print(f"🌐 WebSocket query from user {user_id} in chat {chat_id}: '{query}'")
        
        # Check if user has Gmail data synced
        from app.db import users_collection
        user_data = await users_collection.find_one({"user_id": user_id})
        
        if not user_data or not user_data.get("initial_gmailData_sync", False):
            return {
                "message": "⚠️ Please sync your Gmail data first before querying. Use the Gmail fetch feature in the app.",
                "type": "warning",
                "requires_sync": True
            }
        
        # Process query through the complete pipeline
        response = await query_mem0(user_id, query)
        
        return {
            "message": response,
            "type": "success",
            "user_id": user_id,
            "chat_id": chat_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ WebSocket query error: {e}")
        return {
            "message": f"❌ Error processing your query: {str(e)}",
            "type": "error",
            "user_id": user_id,
            "chat_id": chat_id
        }
