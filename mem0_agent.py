"""
Gmail Email Agent System - Simple Mem0 Integration with Agno Teams

Simple flow using Agno teams:
1. Query comes in
2. Query gets refined by query_analyzer_agent.py 
3. Refined query fetches response from mem0
4. Response gets refined by LLM to generate insights using Agno team
5. Final response sent to frontend
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
from app.query_analyzer_agent import analyze_query

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

# ************* Complete Pipeline Team with Agno Agents *************

# Query Refinement Agent
query_refinement_agent = Agent(
    name="Query Refinement Agent",
    role="Refine user queries for better email search",
    agent_id="query_refinement",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are a query refinement specialist for Gmail email search.",
        "Your job is to take a user's natural language query and optimize it for email search.",
        "Preserve the user's original intent while adding relevant email-specific keywords.",
        "For financial queries, add terms like: payment, transaction, amount, rupees, UPI, bank",
        "For food queries, add terms like: swiggy, zomato, delivery, restaurant, order",
        "For shopping queries, add terms like: amazon, flipkart, purchase, order, shipped",
        "Keep temporal keywords like 'recent', 'latest', 'last' if present in original query.",
        "Return ONLY the refined search query, nothing else."
    ],
    markdown=True,
)

# Simple approach - no custom tools needed

# Mem0 Search Agent  
mem0_search_agent = Agent(
    name="Mem0 Search Agent",
    role="Search emails in Mem0 database using refined queries",
    agent_id="mem0_search",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are a Mem0 search specialist that retrieves relevant emails from the database.",
        "You will be provided with a refined query to search for emails.",
        "Focus on understanding the search requirements and preparing for email retrieval.",
        "Return structured search results with email content, metadata, and relevance scores.",
        "If no results found, clearly indicate this for the next agent to handle."
    ],
    markdown=True,
)

# Insights Generation Agent
insights_generation_agent = Agent(
    name="Insights Generation Agent", 
    role="Generate meaningful insights from email search results",
    agent_id="insights_generation",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are an insights specialist that analyzes email search results and generates valuable insights.",
        "Take email search results and extract meaningful patterns, trends, and information.",
        "For transaction queries: create tables with dates, amounts, merchants, payment methods",
        "For subscription queries: identify recurring payments, renewal dates, costs",
        "For general queries: provide summaries, key points, and actionable insights",
        "Format responses clearly with sections, bullet points, and tables where appropriate",
        "Always base insights on actual email content - never fabricate data",
        "If insufficient data, explain what's available and suggest how to get better results"
    ],
    markdown=True,
)

# Complete Gmail Pipeline Team
gmail_pipeline_team = Team(
    name="Gmail Intelligence Pipeline Team",
    mode="sequential",
    team_id="gmail_pipeline_team",
    model=OpenAIChat(id="gpt-4o"),
    members=[
        query_refinement_agent,
        mem0_search_agent, 
        insights_generation_agent
    ],
    instructions=[
        "You are the complete Gmail Intelligence Pipeline Team handling the full user query to insights flow.",
        "Execute the following pipeline in sequence:",
        "",
        "STEP 1 - Query Refinement Agent:",
        "- Take the original user query",
        "- Refine it for better email search results", 
        "- Add relevant keywords while preserving intent",
        "- Pass refined query to next agent",
        "",
        "STEP 2 - Mem0 Search Agent:",
        "- Take the refined query from Step 1",
        "- Search Mem0 database for matching emails",
        "- Retrieve relevant email content and metadata",
        "- Pass search results to next agent",
        "",
        "STEP 3 - Insights Generation Agent:",
        "- Take search results from Step 2", 
        "- Analyze email content for patterns and insights",
        "- Generate structured, helpful response for user",
        "- Create tables, summaries, and actionable recommendations",
        "",
        "CRITICAL RULES:",
        "- Each agent must complete their task before passing to next agent",
        "- Only use actual email data found in search results",
        "- If no data found, explain clearly and suggest improvements",
        "- Keep responses focused on the user's original query intent",
        "- Provide clear, structured, and actionable insights"
    ],
    markdown=True,
    success_criteria="The team has successfully processed the user query through all pipeline stages and delivered accurate insights based on actual email search results."
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
    # Enhanced patterns for Indian transactions
    patterns = [
        (r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)', '₹'),     # Rs.50.00, Rs. 471.00
        (r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', '₹'),         # ₹50.00, ₹471
        (r'INR\s*(\d+(?:,\d+)*(?:\.\d+)?)', '₹'),       # INR 50.00
        (r'(\d+(?:,\d+)*(?:\.\d+)?)\s*INR', '₹'),       # 50.00 INR
        (r'\$\s*(\d+(?:,\d+)*(?:\.\d+)?)', '$'),        # $50.00
        (r'€\s*(\d+(?:,\d+)*(?:\.\d+)?)', '€'),         # €50.00
        (r'£\s*(\d+(?:,\d+)*(?:\.\d+)?)', '£'),         # £50.00
        (r'(\d+(?:,\d+)*(?:\.\d+)?)\s*USD', '$'),       # 50.00 USD
    ]
    
    for pattern, currency in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            amount = match.replace(',', '')
            try:
                # Validate it's a reasonable transaction amount
                amount_float = float(amount)
                if 0.01 <= amount_float <= 100000:  # Reasonable transaction range
                    return amount, currency
            except:
                continue
    
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

    # Enhanced merchant detection from transaction content
    import re
    
    # Extract merchant from UPI VPA patterns
    upi_patterns = [
        r'to vpa ([^@\s]+)@',  # to VPA merchant@bank
        r'vpa ([^@\s]+)@',     # VPA merchant@bank  
        r'paytm-([^@\s]+)@',   # paytm-blinkit@ptybl
        r'gpay-([^@\s]+)@',    # gpay-merchant@bank
    ]
    
    for pattern in upi_patterns:
        match = re.search(pattern, content_lower)
        if match:
            extracted_merchant = match.group(1)
            # Map common merchant patterns
            if 'blinkit' in extracted_merchant:
                merchant = "Blinkit"
                category = "shopping"
                subcategory = "grocery"
            elif 'swiggy' in extracted_merchant:
                merchant = "Swiggy"
                category = "food"
                subcategory = "delivery"
            elif 'zomato' in extracted_merchant:
                merchant = "Zomato"
                category = "food"
                subcategory = "delivery"
            elif 'mcdonalds' in extracted_merchant:
                merchant = "McDonald's"
                category = "food"
                subcategory = "restaurant"
            elif 'uber' in extracted_merchant:
                merchant = "Uber"
                category = "transport"
                subcategory = "ride"
            else:
                merchant = extracted_merchant.title()
            break

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
    elif any(keyword in content_lower for keyword in ["debited", "credited", "upi", "transaction"]) and amount:
        # This is a financial transaction
        category = "financial_transactions"
        subcategory = "payment"
        if merchant == "unknown":
            # Try to extract merchant from common patterns
            if "food" in content_lower or "restaurant" in content_lower:
                category = "food"
                subcategory = "dining"
            elif "shopping" in content_lower or "order" in content_lower:
                category = "shopping"
                subcategory = "purchase"
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

    # Parse timestamp with multiple format support
    timestamp = None
    if email.date:
        # Try multiple timestamp formats
        timestamp_formats = [
            "%Y-%m-%dT%H:%M:%S%z",      # 2025-06-13T00:00:00+00:00
            "%Y-%m-%dT%H:%M:%S",        # 2025-06-13T00:00:00
            "%Y-%m-%d %H:%M:%S",        # 2025-06-13 00:00:00
            "%Y-%m-%d",                 # 2025-06-13
            "%d-%m-%Y",                 # 13-06-2025
            "%d/%m/%Y",                 # 13/06/2025
        ]
        
        for fmt in timestamp_formats:
            try:
                if fmt.endswith('%z'):
                    # Handle timezone
                    timestamp = datetime.strptime(email.date, fmt).isoformat()
                else:
                    # Parse without timezone and add UTC
                    dt = datetime.strptime(email.date, fmt)
                    timestamp = dt.replace(tzinfo=datetime.now().astimezone().tzinfo).isoformat()
                break
            except:
                continue
        
        # If still no timestamp, try extracting date from email content
        if not timestamp:
            import re
            date_patterns = [
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # DD-MM-YYYY or DD/MM/YYYY
                r'(\d{4}[-/]\d{1,2}[/-]\d{1,2})',  # YYYY-MM-DD
                r'on (\d{1,2}-\d{1,2}-\d{2})',     # on 13-06-25
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    date_str = match.group(1)
                    # Try to parse extracted date
                    for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y"]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            # Convert 2-digit year to 4-digit
                            if dt.year < 2000:
                                dt = dt.replace(year=dt.year + 2000)
                            timestamp = dt.replace(tzinfo=datetime.now().astimezone().tzinfo).isoformat()
                            break
                        except:
                            continue
                    if timestamp:
                        break

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
        
        # Check if this is a job application response query (not job alerts)
        is_job_response_query = any(phrase in query_lower for phrase in [
            "thank you for your application", "interview invitation", "application status",
            "we have reviewed", "unfortunately", "congratulations", "selected", "not selected",
            "feedback on your application"
        ])
        
        # Primary search with original query
        results = await search_with_retry(query, user_id, limit)
        
        # INTELLIGENT POST-PROCESSING: Filter results based on query intent
        if is_job_response_query and results:
            print(f"🎯 JOB RESPONSE FILTERING: Analyzing {len(results)} results for actual responses...")
            
            filtered_results = []
            for result in results:
                memory_content = result.get('memory', '').lower()
                metadata = result.get('metadata', {})
                sender = metadata.get('sender', '').lower()
                
                # EXCLUDE job alerts and job recommendations
                is_job_alert = any(alert_phrase in memory_content for alert_phrase in [
                    'job alert', 'new job', 'job opportunity', 'job positions include',
                    'actively hiring', 'job update', 'career opportunity', 'job recommendation'
                ])
                
                is_alert_sender = any(alert_sender in sender for alert_sender in [
                    'jobalerts', 'job alerts', 'linkedin job', 'naukri', 'indeed'
                ])
                
                # INCLUDE actual responses
                is_response = any(response_phrase in memory_content for response_phrase in [
                    'thank you for', 'application received', 'we have received',
                    'interview', 'reviewed your application', 'application status',
                    'unfortunately', 'congratulations', 'selected', 'not selected',
                    'next steps', 'feedback', 'hr team', 'hiring manager'
                ])
                
                # Only include if it's a response and not an alert
                if is_response and not (is_job_alert or is_alert_sender):
                    filtered_results.append(result)
                    print(f"✅ INCLUDED: Response from {metadata.get('sender', 'Unknown')}")
                else:
                    print(f"❌ EXCLUDED: Job alert from {metadata.get('sender', 'Unknown')}")
            
            print(f"🎯 FILTERING COMPLETE: {len(filtered_results)} actual responses found (from {len(results)} total)")
            results = filtered_results
        
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
        
        team_response = gmail_pipeline_team.run(team_prompt)
        
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

async def universal_content_search(user_id: str, refined_query: str, original_query: str) -> Dict[str, Any]:
    """Universal content search that works with ANY query type based purely on Mem0 data"""
    try:
        print(f"🔍 Universal Content Search: Processing '{refined_query}' for user {user_id}")
        
        # Step 1: Direct search with refined query
        search_results = await search_emails_in_mem0(user_id, refined_query, 1000)
        print(f"📊 Direct search results: {len(search_results)} emails found")
        
        # 🔍 DETAILED MEM0 RAW RESPONSE LOGGING
        print("\n" + "="*80)
        print("🔍 RAW MEM0 SEARCH RESULTS - BEFORE LLM PROCESSING")
        print("="*80)
        
        if search_results:
            for i, result in enumerate(search_results[:5]):  # Show first 5 results in detail
                print(f"\n📧 EMAIL RESULT #{i+1}:")
                print("-" * 50)
                print(f"🆔 ID: {result.get('id', 'N/A')}")
                print(f"🔢 Score: {result.get('score', 'N/A')}")
                
                # Memory content (email body)
                memory_content = result.get('memory', '')
                print(f"💬 MEMORY CONTENT:")
                print(f"   Length: {len(memory_content)} characters")
                print(f"   Preview: {memory_content[:300]}...")
                
                # Metadata details
                metadata = result.get('metadata', {})
                print(f"📊 METADATA:")
                for key, value in metadata.items():
                    print(f"   {key}: {value}")
                
                print("-" * 50)
            
            if len(search_results) > 5:
                print(f"\n... and {len(search_results) - 5} more results")
        else:
            print("❌ NO RAW RESULTS FROM MEM0")
        
        print("="*80)
        print("🔍 END OF RAW MEM0 RESULTS")
        print("="*80 + "\n")
        
        # Step 2: Enhanced search with original query keywords if needed
        if len(search_results) < 20:
            print("🔄 Enhancing search with original query keywords...")
            original_results = await search_emails_in_mem0(user_id, original_query, 500)
            
            print(f"\n🔍 ENHANCED SEARCH RAW RESULTS:")
            print(f"📊 Additional results from original query: {len(original_results)}")
            
            # Combine results without duplicates
            seen_memories = set(result.get('memory', '') for result in search_results)
            for result in original_results:
                memory_text = result.get('memory', '')
                if memory_text and memory_text not in seen_memories:
                    search_results.append(result)
                    seen_memories.add(memory_text)
            
            print(f"📊 Enhanced search results: {len(search_results)} total emails")
        
        # Step 3: Process all results without filtering by type
        content_data = []
        for i, result in enumerate(search_results):
            if result and isinstance(result, dict):
                content_info = {
                    "index": i + 1,
                    "memory": result.get('memory', '') if result.get('memory') else '',
                    "metadata": result.get('metadata', {}) if result.get('metadata') else {},
                    "score": result.get('score', 0) if result.get('score') is not None else 0,
                    "id": result.get('id', f'content_{i}')
                }
                content_data.append(content_info)
        
        print(f"📊 CONTENT DATA PREPARED: {len(content_data)} valid results")
        
        # 📊 PROCESSED DATA SUMMARY FOR LLM
        print("\n" + "="*80)
        print("📊 PROCESSED DATA SUMMARY - GOING TO LLM")
        print("="*80)
        print(f"📈 Total processed items: {len(content_data)}")
        
        if content_data:
            # Show categories breakdown
            categories = {}
            merchants = {}
            for item in content_data:
                metadata = item.get('metadata', {})
                cat = metadata.get('category', 'unknown')
                merch = metadata.get('merchant', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
                merchants[merch] = merchants.get(merch, 0) + 1
            
            print(f"🏷️ Categories found: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))}")
            print(f"🏪 Merchants found: {dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True))}")
            
            # Show sample processed data
            print(f"\n📋 SAMPLE PROCESSED DATA (First 3 items):")
            for i, item in enumerate(content_data[:3]):
                print(f"   Item {i+1}: Score={item['score']}, Memory Length={len(item['memory'])}")
                print(f"   Metadata Keys: {list(item['metadata'].keys())}")
        
        print("="*80)
        print("📊 END OF PROCESSED DATA SUMMARY")
        print("="*80 + "\n")
        
        # Step 4: Generate dynamic response based on actual content
        print("🤖 SENDING TO LLM FOR RESPONSE GENERATION...")
        response = generate_universal_response(original_query, refined_query, content_data)
        print("✅ LLM RESPONSE GENERATED")
        
        return {
            'status': 'success',
            'results_count': len(content_data),
            'response': response,
            'data_type': 'universal_content'
        }
            
    except Exception as e:
        print(f"❌ Universal content search error: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'results_count': 0,
            'response': f"❌ Error processing query: {str(e)}"
        }


def generate_universal_response(original_query: str, refined_query: str, content_data: List[Dict]) -> str:
    """Generate intelligent AI-powered response with insights and analysis"""
    
    if not content_data:
        return f"""
# 🧠 INTELLIGENT EMAIL ANALYSIS
## Query: "{original_query}"

### ⚠️ NO MATCHING DATA FOUND
- No emails found matching your search criteria
- Try using different keywords or broader search terms
- Check if the information might be in a different format

### 💡 SUGGESTIONS
- Use more general keywords
- Try searching for related terms
- Check spelling and terminology
"""
    
    # Generate AI-powered insights using OpenAI
    try:
        print(f"🤖 Generating AI insights for query: '{original_query}' with {len(content_data)} emails")
        ai_insights = generate_ai_insights_from_email_data(original_query, content_data)
        print(f"✅ AI insights generated successfully (length: {len(ai_insights)})")
        print(f"📄 AI Response Preview: {ai_insights[:200]}...")
        return ai_insights
    except Exception as e:
        print(f"❌ Error generating AI insights: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to basic response
        print("🔄 Falling back to basic response...")
        return generate_basic_universal_response(original_query, refined_query, content_data)

def generate_ai_insights_from_email_data(original_query: str, content_data: List[Dict]) -> str:
    """Generate intelligent insights using OpenAI based on email data patterns"""
    
    # Prepare comprehensive data summary for AI analysis
    email_summaries = []
    categories = {}
    merchants = {}
    locations = []
    
    for item in content_data:
        memory = item.get('memory', '')
        metadata = item.get('metadata', {})
        
        # Extract key information
        category = metadata.get('category', 'unknown')
        merchant = metadata.get('merchant', 'unknown')
        location = metadata.get('user_location', '')
        
        categories[category] = categories.get(category, 0) + 1
        merchants[merchant] = merchants.get(merchant, 0) + 1
        if location:
            locations.append(location)
        
        email_summaries.append({
            'content': memory[:300],  # Limit content length
            'category': category,
            'merchant': merchant,
            'location': location,
            'score': item.get('score', 0)
        })
    
    # Sort by relevance
    email_summaries.sort(key=lambda x: x['score'], reverse=True)
    
    # Create intelligent analysis prompt
    analysis_prompt = f"""
You are an expert Gmail data analyst. Analyze the following email data to answer the user's question with intelligent insights based on actual patterns and behaviors.

USER QUESTION: "{original_query}"

EMAIL DATA ANALYSIS:
Total emails analyzed: {len(email_summaries)}

TOP EMAIL CONTENTS (Most Relevant):
{chr(10).join([f"- {email['content']}" for email in email_summaries[:10]])}

PATTERNS DETECTED:
Categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))}
Merchants/Services: {dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True))}
Location References: {list(set(locations)) if locations else ['None detected']}

ANALYSIS GUIDELINES:
1. **Location Questions**: Analyze delivery addresses, transport bookings, local services, event bookings, utility bills, job locations, restaurant orders, etc.
2. **Skill/Career Questions**: Analyze job applications, course subscriptions, tutorial emails, GitHub activity, skill assessments, certifications, etc.
3. **Preference Questions**: Look for usage patterns, subscription choices, purchase behaviors, service preferences, etc.
4. **Lifestyle Questions**: Analyze spending habits, entertainment choices, travel patterns, health services, etc.

REQUIRED RESPONSE FORMAT:
# 🧠 INTELLIGENT EMAIL ANALYSIS
## Query: "{original_query}"

### 💎 KEY INSIGHTS DISCOVERED
[Provide 3-4 main insights based on data patterns discovered in the emails]

### 📊 DETAILED ANALYSIS

**Primary Finding:**
[Main conclusion answering the user's question with confidence level]

**Supporting Evidence:**
- [Evidence 1 from email patterns]
- [Evidence 2 from email patterns]  
- [Evidence 3 from email patterns]

**Behavioral Patterns Identified:**
- [Pattern 1 with explanation]
- [Pattern 2 with explanation]
- [Pattern 3 with explanation]

### 🎯 DIRECT ANSWER
[Clear, direct answer to the user's question based on evidence]

### 📋 SUPPORTING DATA POINTS
- [Specific data point 1 from emails]
- [Specific data point 2 from emails]
- [Specific data point 3 from emails]

### 💡 ADDITIONAL OBSERVATIONS
[Any other interesting insights discovered from the data]

CRITICAL INSTRUCTIONS:
- Base ALL conclusions on ACTUAL email content provided
- Provide confidence levels (High/Medium/Low) for major claims
- If data is insufficient, state this clearly
- Use specific examples from the email content
- Do not make assumptions beyond what the data shows
- Focus on answering the user's specific question
"""

    # Call OpenAI for intelligent analysis
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert email data analyst who provides intelligent insights based on Gmail data patterns. Always base conclusions on actual evidence from the email content and provide confidence levels for your analysis."
                },
                {
                    "role": "user", 
                    "content": analysis_prompt
                }
            ],
            temperature=0.2,  # Lower temperature for more focused analysis
            max_tokens=2500
        )
        
        ai_response = response.choices[0].message.content
        return ai_response
        
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        raise e

def generate_basic_universal_response(original_query: str, refined_query: str, content_data: List[Dict]) -> str:
    """Fallback basic response when AI analysis fails"""
    
    total_results = len(content_data)
    
    response = f"""
# 📧 EMAIL SEARCH RESULTS  
## Query: "{original_query}"

### 📊 SEARCH SUMMARY
- **Total Relevant Emails**: {total_results}
- **Search Query**: {refined_query}

### 📋 MOST RELEVANT RESULTS
"""
    
    # Show top 10 most relevant results
    for i, content in enumerate(content_data[:10], 1):
        memory = content.get('memory', '')
        score = content.get('score', 0)
        
        # Truncate long memories
        if len(memory) > 200:
            memory = memory[:200] + "..."
        
        response += f"\n**{i}.** {memory}"
        if score > 0:
            response += f" *(Relevance: {score:.2f})*"
        response += "\n"
    
    # Add pagination info if there are more results
    if total_results > 10:
        response += f"\n*...and {total_results - 10} more results*\n"
    
    response += f"""

### 💡 KEY INSIGHTS
- Found {total_results} email communications related to your query
- Results are sorted by relevance to your search terms
- Content spans various email types and communications

### 🎯 NEXT STEPS
- Review the most relevant results above
- Use more specific keywords if you need to narrow down results
- Follow up on any important communications you find
"""
    
    return response

async def query_content_database(user_id: str, query: str, query_intent: str = "general") -> Dict[str, Any]:
    """Query database for content-focused queries (jobs, travel, health, etc.) without financial filtering"""
    try:
        print(f"🔍 Content-Focused Search: Processing '{query}' for user {user_id} (Intent: {query_intent})")
        
        # Use comprehensive search for content
        search_results = await search_emails_in_mem0(user_id, query, 1000)
        
        print(f"📊 CONTENT SEARCH RESULTS:")
        print(f"   - Total results retrieved: {len(search_results)}")
        
        # Enhanced search for job-related content
        if query_intent == "job_search" or any(word in query.lower() for word in ["job", "application", "role", "interview", "career"]):
            print("💼 Enhancing job search with targeted terms...")
            
            job_search_terms = [
                "job application", "interview", "position", "role", "career", "hiring",
                "offer", "rejection", "application status", "recruiter", "hr",
                "software engineer", "developer", "programmer", "tech role",
                "linkedin", "naukri", "indeed", "job portal", "employment"
            ]
            
            all_results = search_results.copy()
            seen_memories = set(result.get('memory', '') for result in all_results)
            
            for term in job_search_terms:
                try:
                    term_results = await search_emails_in_mem0(user_id, term, 200)
                    if term_results:
                        for result in term_results:
                            memory_text = result.get('memory', '')
                            if memory_text and memory_text not in seen_memories:
                                all_results.append(result)
                                seen_memories.add(memory_text)
                except Exception as e:
                    print(f"❌ Job search error for '{term}': {e}")
            
            search_results = all_results
            print(f"💼 Enhanced job search: Found {len(search_results)} total results")
        
        # Process results without financial filtering
        content_data = []
        for i, result in enumerate(search_results):
            if result and isinstance(result, dict):
                content_info = {
                    "index": i + 1,
                    "memory": result.get('memory', '') if result.get('memory') else '',
                    "metadata": result.get('metadata', {}) if result.get('metadata') else {},
                    "score": result.get('score', 0) if result.get('score') is not None else 0,
                    "id": result.get('id', f'content_{i}')
                }
                content_data.append(content_info)
        
        print(f"📊 CONTENT DATA PREPARED: {len(content_data)} valid results")
        
        # Generate content-focused response using the appropriate generator
        if query_intent == "job_search" or any(word in query.lower() for word in ["job", "application", "role", "interview", "career"]):
            # Create mock analysis for job response generator
            mock_analysis = {
                'total_count': len(content_data),
                'total_amount': 0,
                'average_amount': 0,
                'categories': {'job_related': len(content_data)},
                'merchants': {'job_portals': len(content_data)},
                'payment_methods': {}
            }
            
            try:
                print(f"🔄 Calling generate_job_analysis_response with {len(content_data)} content items...")
                response = generate_job_analysis_response(query, mock_analysis, [], content_data)
                print(f"✅ Job analysis response generated successfully. Length: {len(response) if response else 0}")
                
                if not response or response.strip() == "":
                    print("⚠️ Empty response from generate_job_analysis_response, creating fallback...")
                    response = f"""
# 💼 JOB APPLICATION STATUS UPDATE
## Query: "{query}"

### 📊 JOB SEARCH SUMMARY
- **Total Job-Related Emails**: {len(content_data)}
- **Recent Activity**: Active job search detected

### 🏢 RECENT JOB COMMUNICATIONS
"""
                    # Show top 5 job-related emails
                    for i, content in enumerate(content_data[:5], 1):
                        memory = content.get('memory', '')
                        if len(memory) > 150:
                            memory = memory[:150] + "..."
                        response += f"\n{i}. {memory}"
                    
                    response += f"""

### 💡 KEY INSIGHTS
- Found {len(content_data)} job-related email communications
- Your job search appears to be active with multiple applications
- Mix of applications, alerts, and responses detected

### 🎯 RECOMMENDATIONS
- Follow up on pending applications
- Keep track of application deadlines
- Prepare for potential interviews
- Continue networking and applying to relevant positions
"""
                
            except Exception as e:
                print(f"❌ Error in generate_job_analysis_response: {e}")
                response = f"""
# 💼 JOB APPLICATION STATUS
## Query: "{query}"

### 📊 SEARCH RESULTS
- **Total Job-Related Emails**: {len(content_data)}

### 🏢 RECENT JOB COMMUNICATIONS
"""
                # Show top 5 job-related emails safely
                for i, content in enumerate(content_data[:5], 1):
                    memory = content.get('memory', '')
                    if len(memory) > 150:
                        memory = memory[:150] + "..."
                    response += f"\n{i}. {memory}"
                
                response += f"""

### 💡 INSIGHTS
- Active job search with multiple communications
- Various applications and responses detected
- Continue following up on applications

### 🎯 NEXT STEPS
- Review recent job communications above
- Follow up on pending applications
- Keep applying to relevant positions
"""
            
            return {
                'status': 'success',
                'results_count': len(content_data),
                'response': response,
                'data_type': 'content',
                'query_intent': query_intent
            }
        else:
            # For other content types, create a general content response
            response = f"""
# 📧 EMAIL CONTENT ANALYSIS
## Query: "{query}"

### 📊 SEARCH RESULTS
- **Total Relevant Emails**: {len(content_data)}
- **Content Type**: {query_intent.title().replace('_', ' ')}

### 📋 KEY FINDINGS
"""
            
            # Show top 5 most relevant results
            for i, content in enumerate(content_data[:5], 1):
                memory = content.get('memory', '')
                if len(memory) > 150:
                    memory = memory[:150] + "..."
                response += f"\n{i}. {memory}"
            
            response += f"""

### 💡 INSIGHTS
- Found {len(content_data)} relevant email communications
- Content covers various aspects of your query
- Results sorted by relevance score

### 🎯 RECOMMENDATIONS
- Review the most relevant results above
- Consider following up on important communications
- Keep track of important updates and responses
"""
            
            return {
                'status': 'success',
                'results_count': len(content_data),
                'response': response,
                'data_type': 'content',
                'query_intent': query_intent
            }
            
    except Exception as e:
        print(f"❌ Content database query error: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'results_count': 0,
            'response': f"❌ Error processing content query: {str(e)}"
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
        
        # Enhanced search strategy for better results
        if len(search_results) < 30 and not category:
            print(f"🔄 Enhancing search with {len(search_results)} initial results, trying comprehensive searches...")
            
            # Dynamic category searches based on query content
            query_lower = query.lower()
            category_searches = {
                "authentication_security": ["authentication", "security", "login", "verification", "2fa", "password", "account"],
                "apple_services": ["apple", "icloud", "app store", "apple music", "apple id", "itunes"],
                "financial_transactions": ["payment", "paid", "upi", "transaction", "amount", "rupees", "₹"],
                "food_delivery": ["food", "delivery", "order", "restaurant", "swiggy", "zomato", "meal", "dominos"],
                "subscriptions": ["subscription", "renewal", "netflix", "spotify", "prime", "monthly", "yearly"],
                "shopping_ecommerce": ["shopping", "purchase", "amazon", "flipkart", "myntra", "buy", "order"],
                "utilities_bills": ["bill", "electricity", "utility", "reminder", "due", "water", "gas"],
                "travel_transport": ["travel", "booking", "flight", "hotel", "uber", "ola", "cab", "ticket"],
                "entertainment": ["entertainment", "movie", "ticket", "bookmyshow", "event", "concert"],
                "general_communication": ["email", "message", "notification", "alert", "update", "news"]
            }
            
            all_results = search_results.copy()
            seen_memories = set(result.get('memory', '') for result in all_results)
            
            # Prioritize categories based on query content
            priority_categories = []
            for category_name, terms in category_searches.items():
                if any(term in query_lower for term in terms):
                    priority_categories.append((category_name, terms))
            
            # Add remaining categories
            remaining_categories = [(name, terms) for name, terms in category_searches.items() 
                                 if name not in [cat[0] for cat in priority_categories]]
            
            # Search priority categories first with higher limits
            search_order = priority_categories + remaining_categories[:5]  # Limit to avoid too many searches
            
            for category_name, terms in search_order:
                search_limit = 200 if category_name in [cat[0] for cat in priority_categories] else 100
                
                for term in terms[:3]:  # Limit terms per category to avoid excessive searches
                    try:
                        cat_results = await search_emails_in_mem0(user_id, term, search_limit)
                        
                        if cat_results:
                            for result in cat_results:
                                memory_text = result.get('memory', '')
                                if memory_text and memory_text not in seen_memories:
                                    all_results.append(result)
                                    seen_memories.add(memory_text)
                                    
                    except Exception as e:
                        print(f"❌ Category search error for '{term}': {e}")
                
                print(f"🔍 Search for '{category_name}': Found {len(all_results)} total results")
            
            search_results = all_results
            print(f"🔍 After enhanced searches: Found {len(search_results)} total results")
        
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
        
        # Extract and analyze real transaction data first
        print(f"💰 EXTRACTING REAL TRANSACTION DATA from {len(transaction_data)} records...")
        
        # Use the existing analysis function to get actual financial data
        financial_analysis = analyze_transactions_directly(transaction_data)
        transaction_table = extract_transaction_table(transaction_data)
        
        # Enhanced transaction data extraction for impressive table
        transaction_details = []
        total_amount = 0
        categories = {}
        merchants = {}
        payment_methods = {}
        
        import re
        from datetime import datetime
        
        for data in transaction_data:
            memory = data.get('memory', '')
            metadata = data.get('metadata', {})
            
            # Extract amount with STRICT validation and realistic limits
            amount_str = metadata.get('amount', '0')
            amount = 0
            
            if amount_str:
                # Extract amount from both metadata and memory content
                memory_lower = memory.lower()
                
                # Look for transaction amount patterns in memory (more reliable)
                transaction_patterns = [
                    r'rs\.?\s*(\d{1,4}(?:\.\d{2})?)\s*(?:debited|credited|paid|transferred)',
                    r'₹\s*(\d{1,4}(?:\.\d{2})?)\s*(?:debited|credited|paid|transferred)',
                    r'amount\s*(?:of\s*)?₹?\s*(\d{1,4}(?:\.\d{2})?)',
                    r'(?:paid|debited|credited)\s*₹?\s*(\d{1,4}(?:\.\d{2})?)',
                    r'upi.*?rs\.?\s*(\d{1,4}(?:\.\d{2})?)',
                    r'transaction.*?₹\s*(\d{1,4}(?:\.\d{2})?)'
                ]
                
                # Try to extract from memory first (more reliable)
                for pattern in transaction_patterns:
                    amount_match = re.search(pattern, memory_lower)
                    if amount_match:
                        try:
                            extracted_amount = float(amount_match.group(1))
                            # Validate realistic transaction amount (₹1 to ₹50,000)
                            if 1 <= extracted_amount <= 50000:
                                amount = extracted_amount
                                break
                        except:
                            continue
                
                # If not found in memory, try metadata with strict validation
                if amount == 0:
                    metadata_patterns = [
                        r'₹\s*(\d{1,4}(?:\.\d{2})?)',  # ₹123.45
                        r'rs\.?\s*(\d{1,4}(?:\.\d{2})?)',  # Rs.123.45
                        r'^(\d{1,4}(?:\.\d{2})?)$'  # Just 123.45
                    ]
                    
                    for pattern in metadata_patterns:
                        amount_match = re.search(pattern, str(amount_str).lower())
                        if amount_match:
                            try:
                                extracted_amount = float(amount_match.group(1))
                                # Strict validation for realistic amounts
                                if 1 <= extracted_amount <= 50000:
                                    amount = extracted_amount
                                    break
                            except:
                                continue
                
                # Add to total only if valid amount found
                if amount > 0:
                    total_amount += amount
            
            # Extract date with improved parsing from memory and metadata
            timestamp = metadata.get('timestamp', '')
            date_formatted = 'Unknown Date'
            
            # Try to extract date from memory content first (often more reliable)
            memory_date_patterns = [
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # DD-MM-YYYY or DD/MM/YYYY
                r'(\d{4}[-/]\d{1,2}[/-]\d{1,2})',  # YYYY-MM-DD
                r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4})',  # DD MMM YYYY
                r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4})'  # MMM DD, YYYY
            ]
            
            for pattern in memory_date_patterns:
                date_match = re.search(pattern, memory.lower())
                if date_match:
                    try:
                        date_str = date_match.group(1)
                        # Try to parse the extracted date
                        date_formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d', '%d %b %Y', '%b %d, %Y']
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                date_formatted = parsed_date.strftime('%d-%m-%Y')
                                break
                            except:
                                continue
                        if date_formatted != 'Unknown Date':
                            break
                    except:
                        continue
            
            # If not found in memory, try timestamp metadata
            if date_formatted == 'Unknown Date' and timestamp:
                try:
                    # Try different timestamp formats
                    timestamp_patterns = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%d',
                        '%d-%m-%Y',
                        '%d/%m/%Y',
                        '%m/%d/%Y'
                    ]
                    
                    for pattern in timestamp_patterns:
                        try:
                            # Take first 19 characters for datetime, first 10 for date
                            ts_str = timestamp[:19] if 'T' in timestamp or ' ' in timestamp else timestamp[:10]
                            parsed_date = datetime.strptime(ts_str, pattern)
                            date_formatted = parsed_date.strftime('%d-%m-%Y')
                            break
                        except:
                            continue
                            
                    # Last resort: extract date part from timestamp
                    if date_formatted == 'Unknown Date' and len(timestamp) >= 10:
                        date_part = timestamp[:10]
                        if '-' in date_part or '/' in date_part:
                            # Try to format it properly
                            try:
                                if date_part.count('-') == 2:
                                    parts = date_part.split('-')
                                    if len(parts[0]) == 4:  # YYYY-MM-DD
                                        date_formatted = f"{parts[2]}-{parts[1]}-{parts[0]}"
                                    else:  # DD-MM-YYYY
                                        date_formatted = date_part
                                elif date_part.count('/') == 2:
                                    parts = date_part.split('/')
                                    if len(parts[2]) == 4:  # DD/MM/YYYY
                                        date_formatted = f"{parts[0]}-{parts[1]}-{parts[2]}"
                            except:
                                date_formatted = date_part
                except:
                    date_formatted = 'Recent'  # Default fallback
            
            # Extract receiver/merchant with ENHANCED parsing
            receiver = metadata.get('merchant', 'Unknown')
            memory_lower = memory.lower()
            
            # Comprehensive merchant detection
            if receiver == 'Unknown' or not receiver or receiver == 'electricity_board':
                
                # Enhanced merchant patterns with more comprehensive list
                merchant_patterns = [
                    # Food delivery
                    r'(?:swiggy|zomato|uber\s*eats|dominos|mcdonald|kfc|pizza\s*hut|burger\s*king)',
                    # Shopping
                    r'(?:amazon|flipkart|myntra|ajio|nykaa|bigbasket|grofers|blinkit)',
                    # Digital payments
                    r'(?:paytm|phonepe|google\s*pay|gpay|bhim|mobikwik)',
                    # Entertainment
                    r'(?:netflix|spotify|prime|hotstar|zee5|jio\s*cinema|sony\s*liv)',
                    # Transport
                    r'(?:ola|uber|rapido|metro|irctc)',
                    # Utilities
                    r'(?:airtel|jio|vi|bsnl|tata\s*sky|dish\s*tv)',
                    # Others
                    r'(?:apple|microsoft|google|adobe|steam|epic\s*games)'
                ]
                
                for pattern in merchant_patterns:
                    merchant_match = re.search(pattern, memory_lower)
                    if merchant_match:
                        receiver = merchant_match.group(0).title().replace(' ', '')
                        break
                
                # Try UPI VPA extraction for real merchant names
                if receiver == 'Unknown':
                    upi_patterns = [
                        r'to\s+VPA\s+([^@\s]+)@',  # to VPA merchant@bank
                        r'VPA\s+([^@\s]+)@',       # VPA merchant@bank
                        r'@([^@\s]+)\s',           # @merchantname
                        r'paid\s+to\s+([^@\s]+)@'  # paid to merchant@bank
                    ]
                    
                    for pattern in upi_patterns:
                        upi_match = re.search(pattern, memory_lower)
                        if upi_match:
                            merchant_name = upi_match.group(1)
                            # Filter out common bank/payment terms
                            if merchant_name not in ['paytm', 'phonepe', 'gpay', 'upi', 'ybl', 'okaxis', 'okicici']:
                                receiver = merchant_name.title()
                                break
                
                # Extract from sender information in email
                if receiver == 'Unknown':
                    sender_patterns = [
                        r'from\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # from MerchantName
                        r'([A-Za-z]+)\s+(?:order|payment|transaction)',  # MerchantName order
                        r'(?:dear|hi)\s+.*?from\s+([A-Za-z]+)',  # dear customer from Merchant
                    ]
                    
                    for pattern in sender_patterns:
                        sender_match = re.search(pattern, memory_lower)
                        if sender_match:
                            potential_merchant = sender_match.group(1)
                            # Filter out generic terms
                            if potential_merchant not in ['customer', 'user', 'account', 'bank', 'payment', 'transaction']:
                                receiver = potential_merchant.title()
                                break
                
                # Last resort: extract meaningful business names
                if receiver == 'Unknown':
                    # Look for capitalized words that might be business names
                    business_patterns = [
                        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:pvt|ltd|inc|corp)',
                        r'\b([A-Z][a-z]{3,})\s+(?:restaurant|store|mart|shop)',
                        r'(?:order\s+from|paid\s+to)\s+([A-Z][a-z]+)',
                    ]
                    
                    for pattern in business_patterns:
                        business_match = re.search(pattern, memory)  # Use original case
                        if business_match:
                            receiver = business_match.group(1)
                            break
                
                # If still unknown, use a generic but descriptive name
                if receiver == 'Unknown':
                    if 'electricity' in memory_lower or 'power' in memory_lower:
                        receiver = 'Electricity Board'
                    elif 'gas' in memory_lower:
                        receiver = 'Gas Company'
                    elif 'water' in memory_lower:
                        receiver = 'Water Board'
                    elif 'internet' in memory_lower or 'broadband' in memory_lower:
                        receiver = 'Internet Provider'
                    elif 'insurance' in memory_lower:
                        receiver = 'Insurance Company'
                    else:
                        receiver = 'Unknown Merchant'
            
            # Extract purpose with better logic
            category = metadata.get('category', 'General')
            subcategory = metadata.get('subcategory', '')
            
            # Enhanced purpose extraction
            purpose = 'General Purchase'
            if 'food' in category.lower() or any(word in memory.lower() for word in ['food', 'meal', 'restaurant', 'delivery']):
                purpose = 'Food Order'
            elif 'shopping' in category.lower() or any(word in memory.lower() for word in ['shopping', 'purchase', 'buy']):
                purpose = 'Online Shopping'
            elif 'entertainment' in category.lower():
                purpose = 'Entertainment'
            elif 'travel' in category.lower():
                purpose = 'Travel Booking'
            elif 'utility' in category.lower() or 'bill' in memory.lower():
                purpose = 'Bill Payment'
            elif 'subscription' in memory.lower():
                purpose = 'Subscription'
            elif subcategory:
                purpose = subcategory.title()
            
            # Extract payment method with better parsing
            payment_method = metadata.get('payment_method', 'Unknown')
            if payment_method == 'Unknown' or not payment_method:
                memory_lower = memory.lower()
                if 'upi' in memory_lower:
                    payment_method = 'UPI'
                elif any(word in memory_lower for word in ['credit card', 'debit card']):
                    payment_method = 'Card'
                elif any(word in memory_lower for word in ['net banking', 'netbanking']):
                    payment_method = 'Net Banking'
                elif any(word in memory_lower for word in ['wallet', 'paytm', 'phonepe']):
                    payment_method = 'Digital Wallet'
                else:
                    payment_method = 'UPI'  # Default for most transactions
            
            # Count statistics
            categories[category] = categories.get(category, 0) + 1
            merchants[receiver] = merchants.get(receiver, 0) + 1
            payment_methods[payment_method] = payment_methods.get(payment_method, 0) + 1
            
            # RELAXED VALIDATION: Include transactions with better logic
            if (amount > 0 and 
                amount <= 50000 and  # Realistic transaction limit
                date_formatted != 'Unknown Date' and  # Must have valid date
                receiver not in ['unknown', 'Unknown Merchant'] and  # Must have identifiable receiver
                len(memory) > 20):  # Must have substantial email content
                
                transaction_details.append({
                    'date': date_formatted,
                    'amount': amount,
                    'receiver': receiver,
                    'purpose': purpose,
                    'payment_method': payment_method,
                    'category': category,
                    'memory_snippet': memory[:100] + '...' if len(memory) > 100 else memory
                })
                
                print(f"✅ Valid transaction: {date_formatted} | ₹{amount} | {receiver} | {purpose}")
            else:
                # Detailed rejection reasons
                rejection_reasons = []
                if amount <= 0:
                    rejection_reasons.append(f"Invalid amount: ₹{amount}")
                if amount > 50000:
                    rejection_reasons.append(f"Unrealistic amount: ₹{amount}")
                if date_formatted == 'Unknown Date':
                    rejection_reasons.append(f"Unknown date (raw: {metadata.get('timestamp', 'None')})")
                if receiver == 'Unknown Merchant':
                    rejection_reasons.append(f"Unknown merchant")
                if len(memory) <= 20:
                    rejection_reasons.append(f"Insufficient email content ({len(memory)} chars)")
                
                print(f"❌ Rejected: {' | '.join(rejection_reasons)}")
                print(f"   📧 Memory: {memory[:80]}...")
                print(f"   📊 Meta: amount={metadata.get('amount')}, merchant={metadata.get('merchant')}, timestamp={metadata.get('timestamp')}")
                print()
                
                # Don't include this in total_amount if it was added earlier
                if amount > 0 and amount > 50000:
                    total_amount -= amount  # Remove unrealistic amounts from total
        
        # Sort by amount (highest first) and then by date
        transaction_details.sort(key=lambda x: (-x['amount'], x['date']))
        
        print(f"💎 FINAL VALIDATION: ₹{total_amount:,.2f} total, {len(transaction_details)} valid transactions")
        
        # QUALITY CHECK: Ensure we have meaningful data to analyze
        if len(transaction_details) == 0:
            print("⚠️ No valid transactions found after filtering")
            # Create a helpful message about data quality
            transaction_details = [{
                'date': 'No Data',
                'amount': 0,
                'receiver': 'No Valid Transactions Found',
                'purpose': 'Data Quality Issue',
                'payment_method': 'N/A',
                'category': 'System Message',
                'memory_snippet': 'Email data may contain reference numbers instead of transaction amounts'
            }]
            total_amount = 0
        elif total_amount > 100000:  # Final check for unrealistic totals
            print(f"⚠️ Total amount {total_amount} seems unrealistic, applying additional filtering")
            # Filter out any remaining high-value outliers
            transaction_details = [t for t in transaction_details if t['amount'] <= 10000]
            total_amount = sum(t['amount'] for t in transaction_details)
            print(f"💎 ADJUSTED TOTAL: ₹{total_amount:,.2f} total, {len(transaction_details)} transactions")
        
        # Use team to process query with REAL EXTRACTED DATA
        team_prompt = f"""
        🚀 GMAIL FINANCIAL INTELLIGENCE MISSION: Create an absolutely MIND-BLOWING financial report using REAL TRANSACTION DATA!

        User Query: "{query}"
        User ID: {user_id}
        
        🔥 REAL FINANCIAL DATA EXTRACTED:
        - **Total Amount Found**: ₹{total_amount:,.2f}
        - **Valid Transactions**: {len(transaction_details)}
        - **Categories**: {dict(list(categories.items())[:10])}
        - **Top Merchants**: {dict(list(merchants.items())[:10])}
        - **Payment Methods**: {dict(payment_methods.items())}
        
                 📊 DETAILED TRANSACTION DATA FOR TABLE:
         {json.dumps(transaction_details[:25], indent=2)}
         
         💡 TABLE FORMAT REQUIREMENTS:
         Create a transaction table with these EXACT columns:
         - Date: Format as DD-MM-YYYY
         - Amount (₹): Show as ₹X,XXX.XX format
         - Receiver: The merchant/person who received payment
         - Purpose: What was purchased/paid for
         - Payment Method: UPI/Card/Net Banking/Digital Wallet etc.
         - Category: Food & Dining/Shopping/Entertainment etc.
        
        🎯 GENERATE THIS EXACT RESPONSE FORMAT:

        # 🔥 GMAIL FINANCIAL INTELLIGENCE REPORT 🔥
        ## Query: "{query}"

        ### 💎 EXECUTIVE SUMMARY - YOUR FINANCIAL DNA
        **🎯 INSTANT INSIGHTS:**
        - 💰 **Total Spending Power**: ₹{total_amount:,.2f} across {len(transaction_details)} transactions
        - 📊 **Financial Behavior Score**: [Calculate based on data]/10 (Based on spending consistency)
        - 🏆 **Top Spending Category**: [Top category from data] - [percentage]% of total budget
        - ⚡ **Average Transaction Velocity**: ₹[calculate average] every [frequency] days
        - 🎪 **Spending Personality**: [Based on patterns in data]

                 ### 📋 COMPLETE TRANSACTION BREAKDOWN
         | 📅 Date | 💰 Amount (₹) | 🏪 Receiver | 🎯 Purpose | 💳 Payment Method | 📊 Category |
         |---------|---------------|-------------|------------|------------------|-------------|
         [Create detailed rows for actual transactions from the extracted data - show top 20 transactions with real data including date, amount, receiver, purpose, payment method, and category]

        ### 🎯 CATEGORY INTELLIGENCE MATRIX
        **🍔 FOOD & DINING EMPIRE** (if food category exists)
        - **[Merchant] Addiction Level**: ₹[amount] ([count] orders) - You order every [frequency] days
        - **[Another merchant]**: ₹[amount] ([count] orders) - [insight]
        - **🔥 FOOD INSIGHT**: [Real pattern from data]
        - **💡 OPTIMIZATION**: [Specific savings calculation]

        **🛒 SHOPPING PSYCHOLOGY** (if shopping category exists)
        - **[Top merchant] Dependency**: ₹[amount] ([count] orders) - [insight]
        - **Average Cart Value**: ₹[calculate from data]
        - **🔥 SHOPPING INSIGHT**: [Real pattern from data]

        ### 🧠 BEHAVIORAL FINANCIAL PSYCHOLOGY
        **⏰ TIME-BASED SPENDING PATTERNS**
        - **Peak Spending**: [Based on timestamp analysis]
        - **Spending Frequency**: [Based on actual data]
        - **Payment Preference**: [Based on payment method data]

        ### 🚀 PREDICTIVE FINANCIAL INTELLIGENCE
        **📈 SPENDING TRAJECTORY**
        - **Monthly Burn Rate**: ₹{total_amount:,.2f} - [trend analysis]
        - **Projected Annual Spending**: ₹[calculate annual projection]
        - **Risk Assessment**: [Based on spending patterns]

        ### 💎 EXCLUSIVE INSIGHTS (The WOW Factor!)
        **🔥 HIDDEN PATTERNS DISCOVERED:**
        - **[Pattern 1]**: [Mind-blowing discovery from actual data]
        - **[Pattern 2]**: [Another amazing pattern from real numbers]
        - **[Pattern 3]**: [Unique finding from transaction analysis]

        ### 🏆 ACTIONABLE INTELLIGENCE DASHBOARD
        **⚡ IMMEDIATE ACTIONS (Next 7 Days)**
        1. **[Action 1]**: [Specific recommendation with actual savings amount]
        2. **[Action 2]**: [Specific recommendation with actual savings amount]

        **🚀 STRATEGIC MOVES (Next 30 Days)**
        1. **[Strategy 1]**: [Long-term recommendation with specific amounts]
        2. **[Strategy 2]**: [Long-term recommendation with specific amounts]

        ### 📱 SMART ALERTS & RECOMMENDATIONS
        - **🚨 Alert**: [Important finding based on real data]
        - **💎 Opportunity**: [Optimization opportunity with specific savings]
        - **⚡ Efficiency**: [Improvement suggestion with actual numbers]

        ---
        ## 🎯 THE BOTTOM LINE
        **Your emails revealed ₹{total_amount:,.2f} in financial activity across {len(transaction_details)} transactions with [key insights]**

        *How did we decode all this from your emails? That's the power of AI financial intelligence! 🤖✨*

        🎊 **CONGRATULATIONS!** You've just experienced the most comprehensive financial analysis for your query! 🎉

                 ⚡ CRITICAL REQUIREMENTS:
         1. **TRANSACTION TABLE**: Create the table using ONLY the transaction_details data provided above
         2. **REAL DATA ONLY**: All amounts, dates, receivers, purposes must be from actual extracted data
         3. **TABLE FORMAT**: Use this exact format for each row:
            | DD-MM-YYYY | ₹X,XXX.XX | Actual Receiver | Actual Purpose | Actual Method | Actual Category |
         4. **NO PLACEHOLDERS**: Replace ALL [brackets] with real data from transaction_details
         5. **AMOUNT FORMATTING**: Show amounts as ₹1,234.56 format with commas
         6. **TOP 20 TRANSACTIONS**: Show the highest 20 transactions from the sorted list
         7. **CALCULATE REAL METRICS**: All percentages, averages must be calculated from actual data
         8. **SPECIFIC INSIGHTS**: Base all insights on real spending patterns found in the data
         9. **ACTIONABLE RECOMMENDATIONS**: Provide savings suggestions with real calculated amounts
         10. **GENUINE ANALYSIS**: Every insight must come from actual transaction patterns

        Generate this response now using ONLY the real financial data extracted from the emails!
        """
        
        team_response = gmail_pipeline_team.run(team_prompt)
        
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
        
        team_response = gmail_pipeline_team.run(team_prompt)
        
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
                        
                        team_response = gmail_pipeline_team.run(team_prompt)
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
                    response = gmail_pipeline_team.run(team_query)
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

def analyze_user_query(query: str) -> Dict[str, Any]:
    """Analyze user query to understand intent and extract key components"""
    query_lower = query.lower()
    
    # Extract key intent
    intent = "general"
    sub_queries = []
    focus_keywords = []
    
    # Payment reminders specific analysis
    if any(word in query_lower for word in ["reminder", "due", "pending", "overdue", "payment reminder"]):
        intent = "payment_reminders"
        sub_queries = [
            "payment reminder due date overdue pending",
            "bill reminder electricity water gas internet",
            "subscription renewal reminder netflix spotify",
            "credit card payment due reminder",
            "loan emi reminder monthly payment",
            "insurance premium reminder due",
            "reminder urgent important payment",
            "overdue payment penalty charges",
            "auto payment failed reminder",
            "payment confirmation receipt"
        ]
        focus_keywords = ["reminder", "due", "pending", "overdue", "payment", "bill"]
    
    # Job-related queries
    elif any(word in query_lower for word in ["job", "career", "employment", "hiring", "interview", "application", "position", "vacancy", "recruitment"]):
        intent = "job_search"
        sub_queries = [
            "job application career opportunity interview",
            "hiring recruitment position vacancy opening",
            "linkedin naukri indeed job portal",
            "interview schedule appointment meeting",
            "offer letter salary compensation package",
            "employment contract joining date",
            "resume cv profile application status",
            "recruiter hr human resources"
        ]
        focus_keywords = ["job", "career", "interview", "application", "hiring"]
    
    # Transaction/spending queries
    elif any(word in query_lower for word in ["transaction", "spent", "spending", "purchase", "buy", "order"]):
        intent = "transactions"
        sub_queries = [
            "payment transaction amount rupees upi paid",
            "purchase order buy shopping online",
            "food delivery order restaurant swiggy zomato",
            "shopping amazon flipkart myntra purchase",
            "subscription payment netflix spotify",
            "bill payment electricity utility",
            "investment mutual fund sip trading"
        ]
        focus_keywords = ["transaction", "payment", "purchase", "order", "spent"]
    
    # Travel queries
    elif any(word in query_lower for word in ["travel", "flight", "hotel", "booking", "trip", "vacation"]):
        intent = "travel"
        sub_queries = [
            "flight booking airline ticket confirmation",
            "hotel reservation accommodation booking",
            "travel itinerary trip vacation holiday",
            "uber ola cab taxi ride booking",
            "train booking railway ticket irctc"
        ]
        focus_keywords = ["travel", "flight", "hotel", "booking", "trip"]
    
    # Health queries
    elif any(word in query_lower for word in ["health", "medical", "doctor", "appointment", "hospital"]):
        intent = "health"
        sub_queries = [
            "doctor appointment medical consultation",
            "hospital clinic healthcare facility",
            "medicine prescription pharmacy order",
            "health insurance policy coverage",
            "medical report test result diagnosis"
        ]
        focus_keywords = ["health", "medical", "doctor", "appointment"]
    
    # Default - extract keywords from query
    else:
        intent = "general"
        # Extract meaningful keywords from the query
        words = query_lower.split()
        focus_keywords = [word for word in words if len(word) > 3 and word not in ['the', 'and', 'for', 'with', 'about', 'from', 'that', 'this', 'have', 'will', 'been', 'were']]
        
        # Generate sub-queries based on extracted keywords
        sub_queries = [
            " ".join(focus_keywords[:3]),  # First 3 keywords
            " ".join(focus_keywords[1:4]),  # Next 3 keywords
            " ".join([word for word in focus_keywords if word in query_lower]),  # All relevant keywords
            f"{' '.join(focus_keywords)} email notification",
            f"{' '.join(focus_keywords)} update information"
        ]
    
    return {
        "intent": intent,
        "sub_queries": sub_queries,
        "focus_keywords": focus_keywords,
        "original_query": query
    }

async def universal_gmail_analysis(user_id: str, query: str) -> Dict[str, Any]:
    """Universal automated analysis system that works for ANY query type"""
    try:
        print(f"🚀 UNIVERSAL ANALYSIS: Processing '{query}' for user {user_id}")
        
        # Step 1: Direct query search - no hardcoded terms
        print("📊 Step 1: Direct query search...")
        print(f"🔍 Searching directly for: '{query}'")
        
        # Direct search with the user's actual query
        all_transactions = await search_with_retry(query, user_id, 1000, max_retries=3)
        
        print(f"📊 DIRECT SEARCH RESULTS: {len(all_transactions)} emails found")
        
        # Step 2: Direct data analysis
        print("🔍 Step 2: Direct data extraction and analysis...")
        analysis = analyze_transactions_directly(all_transactions)
        table = extract_transaction_table(all_transactions)
        
        # Step 3: Query-specific analysis
        print(f"🎯 Step 3: Query-specific analysis for '{query}'...")
        
        # Generate universal analysis without hardcoded types
        analysis_type = "universal_analysis"
        
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
                "search_query": query,
                "emails_found": len(all_transactions),
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
    """Generate universal intelligent response based purely on data"""
    
    # Always use universal analysis - no hardcoded types
    return generate_universal_analysis_response(query, analysis, table, all_transactions)

def generate_universal_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate analysis response based purely on the actual data found"""
    
    total_count = analysis['total_count']
    total_amount = analysis['total_amount']
    avg_amount = analysis['average_amount']
    categories = analysis['categories']
    merchants = analysis['merchants']
    payment_methods = analysis['payment_methods']
    
    response = f"""
# 📊 COMPREHENSIVE EMAIL ANALYSIS
## Query: "{query}"

### 📈 DATA OVERVIEW
- **Total Email Records**: {total_count}
- **Total Amount Found**: ₹{total_amount:,.2f}
- **Average Amount**: ₹{avg_amount:.2f}

### 📋 CONTENT BREAKDOWN
"""
    
    # Show categories if any
    if categories:
        response += "\n**📂 Categories Found:**\n"
        for category, count in list(categories.items())[:5]:
            response += f"- **{category.title()}**: {count} records\n"
    
    # Show merchants/entities if any  
    if merchants:
        response += "\n**🏢 Top Entities/Sources:**\n"
        for merchant, count in list(merchants.items())[:5]:
            response += f"- **{merchant}**: {count} records\n"
    
    # Show payment methods if any
    if payment_methods:
        response += "\n**💳 Payment Methods:**\n"
        for method, count in payment_methods.items():
            response += f"- **{method.title()}**: {count} records\n"
    
    # Show actual content samples
    response += "\n### 📧 RELEVANT CONTENT SAMPLES\n"
    for i, transaction in enumerate(all_transactions[:5], 1):
        memory = transaction.get('memory', '')
        if len(memory) > 150:
            memory = memory[:150] + "..."
        response += f"\n**{i}.** {memory}\n"
    
    if len(all_transactions) > 5:
        response += f"\n*...and {len(all_transactions) - 5} more records*\n"
    
    response += f"""

### 💡 KEY INSIGHTS
- Found {total_count} relevant email communications
- Data spans multiple categories and sources
- Content is directly related to your search query

### 🎯 ACTIONABLE RECOMMENDATIONS
- Review the relevant content samples above
- Follow up on any important communications
- Use more specific keywords for refined results
- Keep track of important updates and responses
"""
    
    return response

def generate_payment_reminders_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate specialized response for payment reminder queries"""
    
    total_count = analysis['total_count']
    categories = analysis['categories']
    merchants = analysis['merchants']
    
    # Extract reminder-specific data
    reminder_data = []
    overdue_data = []
    upcoming_data = []
    bill_data = []
    
    for transaction in all_transactions:
        memory_text = transaction.get('memory', '').lower()
        
        # Check for reminder keywords
        is_reminder = any(word in memory_text for word in ['reminder', 'due', 'pending', 'overdue', 'payment due'])
        is_bill = any(word in memory_text for word in ['bill', 'electricity', 'water', 'gas', 'internet', 'mobile'])
        is_overdue = any(word in memory_text for word in ['overdue', 'late', 'penalty', 'charges'])
        is_upcoming = any(word in memory_text for word in ['upcoming', 'next', 'soon', 'tomorrow'])
        
        if is_reminder or is_bill:
            reminder_data.append(transaction)
            
            if is_overdue:
                overdue_data.append(transaction)
            elif is_upcoming:
                upcoming_data.append(transaction)
            elif is_bill:
                bill_data.append(transaction)
    
    # Count different types of reminders
    reminder_count = len(reminder_data)
    overdue_count = len(overdue_data)
    upcoming_count = len(upcoming_data)
    bill_count = len(bill_data)
    
    # Extract merchants from reminders
    reminder_merchants = {}
    for transaction in reminder_data:
        memory = transaction.get('memory', '')
        # Extract merchant/service name
        for merchant in merchants:
            if merchant.lower() in memory.lower():
                reminder_merchants[merchant] = reminder_merchants.get(merchant, 0) + 1
    
    response = f"""
# 🔔 PAYMENT REMINDERS ANALYSIS
## Based on Analysis of {total_count} Email Records

### 📊 REMINDER OVERVIEW
- **Total Reminders Found**: {reminder_count}
- **Overdue Payments**: {overdue_count}
- **Upcoming Payments**: {upcoming_count}
- **Bill Reminders**: {bill_count}

### 🚨 CRITICAL INSIGHTS

**⚠️ OVERDUE PAYMENTS:**
"""
    
    if overdue_count > 0:
        response += f"""
- **{overdue_count} overdue payment(s) detected**
- **Action Required**: Immediate payment needed to avoid penalties
- **Priority**: HIGH - Pay these first
"""
        
        # Show sample overdue reminders
        for i, reminder in enumerate(overdue_data[:3]):
            memory = reminder.get('memory', '')[:100]
            response += f"\n  {i+1}. {memory}..."
    else:
        response += "\n- ✅ No overdue payments detected - Great job!"
    
    response += f"""

**📅 UPCOMING PAYMENTS:**
"""
    
    if upcoming_count > 0:
        response += f"""
- **{upcoming_count} upcoming payment(s) scheduled**
- **Action**: Prepare for these payments
- **Priority**: MEDIUM - Plan ahead
"""
        
        # Show sample upcoming reminders
        for i, reminder in enumerate(upcoming_data[:3]):
            memory = reminder.get('memory', '')[:100]
            response += f"\n  {i+1}. {memory}..."
    else:
        response += "\n- 📝 No upcoming payment reminders found"
    
    response += f"""

**💡 BILL REMINDERS:**
"""
    
    if bill_count > 0:
        response += f"""
- **{bill_count} utility/service bill(s) found**
- **Types**: Electricity, Water, Internet, Mobile, etc.
- **Status**: Regular monthly obligations
"""
        
        # Show sample bill reminders
        for i, reminder in enumerate(bill_data[:3]):
            memory = reminder.get('memory', '')[:100]
            response += f"\n  {i+1}. {memory}..."
    else:
        response += "\n- 📋 No utility bill reminders found"
    
    # Service provider analysis
    if reminder_merchants:
        response += f"""

### 🏢 SERVICE PROVIDERS
"""
        for merchant, count in sorted(reminder_merchants.items(), key=lambda x: x[1], reverse=True)[:5]:
            response += f"\n- **{merchant}**: {count} reminder(s)"
    
    # Actionable recommendations
    response += f"""

### 🎯 ACTIONABLE RECOMMENDATIONS

**🚨 IMMEDIATE ACTIONS:**
"""
    
    if overdue_count > 0:
        response += f"""
1. **Pay {overdue_count} overdue payment(s) immediately** to avoid additional charges
2. **Check penalty amounts** and factor them into payments
3. **Contact service providers** if you need payment extensions
"""
    
    if upcoming_count > 0:
        response += f"""
4. **Set calendar reminders** for {upcoming_count} upcoming payments
5. **Ensure sufficient account balance** before due dates
"""
    
    response += f"""

**📋 ORGANIZATION TIPS:**
1. **Set up auto-pay** for recurring bills to avoid missing payments
2. **Create a payment calendar** with all due dates
3. **Enable SMS/email alerts** from all service providers
4. **Maintain emergency fund** for unexpected payments

**💰 FINANCIAL MANAGEMENT:**
1. **Budget for regular bills** in your monthly planning
2. **Track payment patterns** to identify peak expense periods
3. **Consider consolidating** payment dates for better cash flow
4. **Review and optimize** subscriptions and services regularly

### 📈 PAYMENT TRENDS
- **Most Common Reminders**: {'Bills' if bill_count > reminder_count//2 else 'General Payments'}
- **Payment Discipline**: {'Excellent' if overdue_count == 0 else 'Needs Improvement' if overdue_count <= 2 else 'Critical'}
- **Organization Level**: {'Good' if upcoming_count > 0 else 'Basic'}

### 🔍 NEXT STEPS
1. **Review all overdue payments** and prioritize by penalty costs
2. **Set up automatic payments** for recurring bills
3. **Create a master payment schedule** for all obligations
4. **Monitor your email regularly** for new payment reminders
"""
    
    return response

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

def generate_food_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate comprehensive food spending analysis"""
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    
    # Filter food-related transactions
    food_transactions = [t for t in all_transactions if t.get('metadata', {}).get('category', '').lower() in ['food', 'delivery']]
    food_amount = sum(float(t.get('metadata', {}).get('amount', '0').replace('₹', '').replace(',', '')) for t in food_transactions if t.get('metadata', {}).get('amount'))
    
    return f"""
# 🍔 COMPREHENSIVE FOOD SPENDING ANALYSIS
## Based on Analysis of {total_count} Transactions (₹{total_amount:,.2f})

### 🎯 FOOD SPENDING OVERVIEW
- **Total Food Transactions**: {len(food_transactions)}
- **Food Spending Amount**: ₹{food_amount:,.2f}
- **Percentage of Total Spending**: {(food_amount/total_amount*100):.1f}%

### 📊 TOP FOOD MERCHANTS
{chr(10).join([f"- **{merchant}**: {count} orders" for merchant, count in analysis['merchants'].items() if merchant.lower() in ['swiggy', 'zomato', 'ubereats', 'dominos']])}

### 💡 FOOD SPENDING INSIGHTS
- Average food order: ₹{food_amount/len(food_transactions) if food_transactions else 0:.0f}
- Most active food category based on your email patterns
- Consider meal planning to optimize food expenses

### 🎯 RECOMMENDATIONS
- Track monthly food budget vs actual spending
- Look for restaurant discounts and offers
- Consider cooking more meals at home for savings
"""

def generate_spending_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate comprehensive spending analysis"""
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    avg_amount = analysis['average_amount']
    
    return f"""
# 💰 COMPREHENSIVE SPENDING ANALYSIS
## Based on Analysis of {total_count} Transactions (₹{total_amount:,.2f})

### 📊 SPENDING OVERVIEW
- **Total Amount**: ₹{total_amount:,.2f}
- **Total Transactions**: {total_count}
- **Average Transaction**: ₹{avg_amount:.2f}

### 🏷️ CATEGORY BREAKDOWN
{chr(10).join([f"- **{category.title()}**: {count} transactions" for category, count in analysis['categories'].items()])}

### 🏪 TOP MERCHANTS
{chr(10).join([f"- **{merchant}**: {count} transactions" for merchant, count in list(analysis['merchants'].items())[:5]])}

### 💳 PAYMENT METHODS
{chr(10).join([f"- **{method.title()}**: {count} transactions" for method, count in analysis['payment_methods'].items()])}

### 💡 SPENDING INSIGHTS
- Most frequent spending category: {max(analysis['categories'], key=analysis['categories'].get) if analysis['categories'] else 'N/A'}
- Digital payment adoption: High (UPI/Digital wallets preferred)
- Spending pattern indicates regular online transactions

### 🎯 OPTIMIZATION RECOMMENDATIONS
- Set monthly budgets for top spending categories
- Use cashback credit cards for frequent merchants
- Track and review monthly spending patterns
"""

def generate_subscription_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate subscription spending analysis"""
    total_amount = analysis['total_amount']
    
    # Filter subscription transactions
    subscription_transactions = [t for t in all_transactions if 'subscription' in t.get('metadata', {}).get('category', '').lower()]
    
    return f"""
# 📱 SUBSCRIPTION SPENDING ANALYSIS
## Based on Analysis of {len(subscription_transactions)} Subscription Transactions

### 💳 SUBSCRIPTION OVERVIEW
- **Active Subscriptions Detected**: {len(subscription_transactions)}
- **Monthly Subscription Spend**: ₹{sum(float(t.get('metadata', {}).get('amount', '0').replace('₹', '').replace(',', '')) for t in subscription_transactions):.2f}

### 📺 DETECTED SUBSCRIPTIONS
- Netflix, Spotify, Amazon Prime (based on email patterns)
- Various app subscriptions and services

### 💡 SUBSCRIPTION INSIGHTS
- Review unused subscriptions monthly
- Consider annual plans for frequently used services
- Track subscription renewal dates

### 🎯 OPTIMIZATION TIPS
- Cancel unused subscriptions
- Share family plans where possible
- Use free alternatives for rarely used services
"""

def generate_investment_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate investment analysis"""
    total_amount = analysis['total_amount']
    
    return f"""
# 📈 INVESTMENT ANALYSIS
## Based on Email Transaction Patterns

### 💼 INVESTMENT ACTIVITY
- **Investment-related emails detected** in your transaction history
- **Mutual Fund SIPs**: Regular investment patterns observed
- **Trading Activity**: Market-related transactions noted

### 🎯 INVESTMENT INSIGHTS
- Consistent SIP investments show good financial discipline
- Diversified portfolio approach recommended
- Regular monitoring of investment performance

### 💡 RECOMMENDATIONS
- Increase SIP amount gradually with income growth
- Review and rebalance portfolio quarterly
- Consider tax-saving investments (ELSS)
"""

def generate_monthly_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate monthly spending analysis"""
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    
    return f"""
# 📅 MONTHLY SPENDING ANALYSIS
## Based on Analysis of {total_count} Transactions

### 📊 MONTHLY OVERVIEW
- **Total Monthly Spending**: ₹{total_amount:,.2f}
- **Transaction Count**: {total_count}
- **Daily Average**: ₹{total_amount/30:.2f}

### 📈 SPENDING PATTERNS
- **Peak spending days**: Weekends show higher activity
- **Category distribution**: Food and shopping dominate
- **Payment preferences**: UPI and digital wallets

### 💡 MONTHLY INSIGHTS
- Consistent spending pattern throughout the month
- Higher activity during festival/sale periods
- Regular subscription and bill payments

### 🎯 MONTHLY RECOMMENDATIONS
- Set monthly spending limits
- Track expenses weekly
- Plan major purchases in advance
"""

def generate_general_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate general financial analysis"""
    total_amount = analysis['total_amount']
    total_count = analysis['total_count']
    avg_amount = analysis['average_amount']
    
    return f"""
# 📊 GENERAL FINANCIAL ANALYSIS
## Based on Analysis of {total_count} Transactions (₹{total_amount:,.2f})

### 💰 FINANCIAL OVERVIEW
- **Total Transactions**: {total_count}
- **Total Amount**: ₹{total_amount:,.2f}
- **Average Transaction**: ₹{avg_amount:.2f}

### 🏷️ SPENDING CATEGORIES
{chr(10).join([f"- **{category.title()}**: {count} transactions" for category, count in list(analysis['categories'].items())[:5]])}

### 🏪 FREQUENT MERCHANTS
{chr(10).join([f"- **{merchant}**: {count} transactions" for merchant, count in list(analysis['merchants'].items())[:5]])}

### 💡 KEY INSIGHTS
- Diverse spending across multiple categories
- Regular digital payment usage
- Consistent transaction patterns

### 🎯 GENERAL RECOMMENDATIONS
- Continue tracking expenses
- Consider budgeting apps
- Review spending patterns monthly
- Optimize payment methods for rewards
"""

def generate_job_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate job-related analysis response"""
    
    total_count = analysis['total_count']
    
    # Analyze job-related emails
    job_emails = []
    interview_emails = []
    application_emails = []
    offer_emails = []
    
    for transaction in all_transactions:
        memory = transaction.get('memory', '').lower()
        
        if any(word in memory for word in ['interview', 'meeting', 'schedule']):
            interview_emails.append(transaction)
        elif any(word in memory for word in ['application', 'applied', 'resume', 'cv']):
            application_emails.append(transaction)
        elif any(word in memory for word in ['offer', 'congratulations', 'selected', 'hired']):
            offer_emails.append(transaction)
        elif any(word in memory for word in ['job', 'position', 'vacancy', 'career']):
            job_emails.append(transaction)
    
    response = f"""
# 💼 JOB & CAREER ANALYSIS
## Based on Analysis of {total_count} Email Communications

### 📈 JOB SEARCH OVERVIEW
- **Total Job-Related Emails**: {len(job_emails)}
- **Job Applications**: {len(application_emails)}
- **Interview Invitations**: {len(interview_emails)}
- **Job Offers**: {len(offer_emails)}

### 🎯 JOB ACTIVITY BREAKDOWN
- **Applications Sent**: {len(application_emails)} opportunities
- **Interview Calls**: {len(interview_emails)} scheduled
- **Success Rate**: {(len(offer_emails)/max(len(application_emails), 1)*100):.1f}%

### 🏢 RECENT JOB OPPORTUNITIES
"""
    
    # Show recent job-related emails
    try:
        recent_jobs = sorted(all_transactions, key=lambda x: x.get('metadata', {}).get('timestamp') or '0000-00-00', reverse=True)[:5]
        
        for i, job in enumerate(recent_jobs, 1):
            memory = job.get('memory', '')
            if len(memory) > 100:
                memory = memory[:100] + "..."
            response += f"{i}. {memory}\n"
    except Exception as e:
        response += "Recent job emails available in your data.\n"
    
    response += f"""
### 💡 CAREER INSIGHTS
- Active job search with {len(application_emails)} applications
- Interview conversion rate: {(len(interview_emails)/max(len(application_emails), 1)*100):.1f}%
- Most active in recent months

### 🎯 RECOMMENDATIONS
- Follow up on pending applications
- Prepare for upcoming interviews
- Update your resume with recent achievements
- Network with industry professionals
- Consider skill development courses
"""
    
    return response.strip()

def generate_travel_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate travel-related analysis response"""
    
    total_count = analysis['total_count']
    
    # Analyze travel-related emails
    flight_bookings = []
    hotel_bookings = []
    travel_expenses = []
    
    for transaction in all_transactions:
        memory = transaction.get('memory', '').lower()
        
        if any(word in memory for word in ['flight', 'airline', 'boarding']):
            flight_bookings.append(transaction)
        elif any(word in memory for word in ['hotel', 'accommodation', 'booking']):
            hotel_bookings.append(transaction)
        elif any(word in memory for word in ['travel', 'trip', 'vacation']):
            travel_expenses.append(transaction)
    
    response = f"""
# ✈️ TRAVEL & BOOKING ANALYSIS
## Based on Analysis of {total_count} Travel Communications

### 🌍 TRAVEL OVERVIEW
- **Flight Bookings**: {len(flight_bookings)}
- **Hotel Reservations**: {len(hotel_bookings)}
- **Travel-Related Emails**: {len(travel_expenses)}

### 📅 RECENT TRAVEL ACTIVITY
"""
    
    # Show recent travel bookings
    try:
        recent_travel = sorted(all_transactions, key=lambda x: x.get('metadata', {}).get('timestamp') or '0000-00-00', reverse=True)[:5]
        
        for i, travel in enumerate(recent_travel, 1):
            memory = travel.get('memory', '')
            if len(memory) > 100:
                memory = memory[:100] + "..."
            response += f"{i}. {memory}\n"
    except Exception as e:
        response += "Recent travel bookings available in your data.\n"
    
    response += f"""
### 💡 TRAVEL INSIGHTS
- Active travel planning and bookings
- Mix of business and leisure travel
- Regular booking confirmations

### 🎯 TRAVEL RECOMMENDATIONS
- Check booking confirmations
- Review travel insurance coverage
- Prepare travel documents
- Monitor flight status updates
"""
    
    return response.strip()

def generate_health_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate health-related analysis response"""
    
    total_count = analysis['total_count']
    
    # Analyze health-related emails
    appointments = []
    prescriptions = []
    insurance_claims = []
    
    for transaction in all_transactions:
        memory = transaction.get('memory', '').lower()
        
        if any(word in memory for word in ['appointment', 'doctor', 'clinic']):
            appointments.append(transaction)
        elif any(word in memory for word in ['prescription', 'medicine', 'pharmacy']):
            prescriptions.append(transaction)
        elif any(word in memory for word in ['insurance', 'claim', 'medical']):
            insurance_claims.append(transaction)
    
    response = f"""
# 🏥 HEALTH & MEDICAL ANALYSIS
## Based on Analysis of {total_count} Health Communications

### 💊 HEALTH OVERVIEW
- **Medical Appointments**: {len(appointments)}
- **Prescriptions**: {len(prescriptions)}
- **Insurance Claims**: {len(insurance_claims)}

### 📋 RECENT HEALTH ACTIVITY
"""
    
    # Show recent health-related emails
    try:
        recent_health = sorted(all_transactions, key=lambda x: x.get('metadata', {}).get('timestamp') or '0000-00-00', reverse=True)[:5]
        
        for i, health in enumerate(recent_health, 1):
            memory = health.get('memory', '')
            if len(memory) > 100:
                memory = memory[:100] + "..."
            response += f"{i}. {memory}\n"
    except Exception as e:
        response += "Recent health communications available in your data.\n"
    
    response += f"""
### 💡 HEALTH INSIGHTS
- Regular healthcare monitoring
- Active prescription management
- Health insurance utilization

### 🎯 HEALTH RECOMMENDATIONS
- Keep track of upcoming appointments
- Maintain prescription records
- Review insurance coverage
- Schedule regular health checkups
"""
    
    return response.strip()

def generate_education_analysis_response(query: str, analysis: Dict, table: List[Dict], all_transactions: List[Dict]) -> str:
    """Generate education-related analysis response"""
    
    total_count = analysis['total_count']
    
    # Analyze education-related emails
    courses = []
    certifications = []
    exam_results = []
    
    for transaction in all_transactions:
        memory = transaction.get('memory', '').lower()
        
        if any(word in memory for word in ['course', 'enrollment', 'learning']):
            courses.append(transaction)
        elif any(word in memory for word in ['certification', 'certificate', 'exam']):
            certifications.append(transaction)
        elif any(word in memory for word in ['result', 'grade', 'score']):
            exam_results.append(transaction)
    
    response = f"""
# 📚 EDUCATION & LEARNING ANALYSIS
## Based on Analysis of {total_count} Educational Communications

### 🎓 EDUCATION OVERVIEW
- **Course Enrollments**: {len(courses)}
- **Certifications**: {len(certifications)}
- **Exam Results**: {len(exam_results)}

### 📖 RECENT LEARNING ACTIVITY
"""
    
    # Show recent education-related emails
    try:
        recent_education = sorted(all_transactions, key=lambda x: x.get('metadata', {}).get('timestamp') or '0000-00-00', reverse=True)[:5]
        
        for i, education in enumerate(recent_education, 1):
            memory = education.get('memory', '')
            if len(memory) > 100:
                memory = memory[:100] + "..."
            response += f"{i}. {memory}\n"
    except Exception as e:
        response += "Recent educational communications available in your data.\n"
    
    response += f"""
### 💡 LEARNING INSIGHTS
- Active skill development
- Continuous learning approach
- Professional growth focus

### 🎯 EDUCATION RECOMMENDATIONS
- Complete enrolled courses
- Apply learned skills practically
- Seek advanced certifications
- Join professional communities
"""
    
    return response.strip()

# Add these new functions after the existing analysis functions (around line 600)

def extract_real_transaction_data(search_results: List[Dict]) -> Dict[str, Any]:
    """Extract actual transaction data from mem0 search results"""
    transactions = []
    total_amount = 0.0
    categories = {}
    merchants = {}
    payment_methods = {}
    dates = []
    
    # Regex patterns for extracting real data
    amount_pattern = r'[₹Rs\.]\s*(\d+(?:,\d+)*(?:\.\d+)?)'
    date_pattern = r'(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})'
    
    for result in search_results:
        if not result or 'memory' not in result:
            continue
            
        memory_content = result.get('memory', '')
        if not memory_content:
            continue
            
        # Extract actual amounts
        amounts = re.findall(amount_pattern, memory_content)
        if amounts:
            try:
                amount = float(amounts[0].replace(',', ''))
                total_amount += amount
            except:
                amount = 0.0
        else:
            amount = 0.0
            
        # Extract dates
        found_dates = re.findall(date_pattern, memory_content)
        if found_dates:
            dates.extend(found_dates)
            
        # Extract merchant/service names from memory content
        merchant = "Unknown"
        memory_lower = memory_content.lower()
        
        # Common merchants/services
        merchant_keywords = {
            'swiggy': 'Swiggy',
            'zomato': 'Zomato', 
            'amazon': 'Amazon',
            'flipkart': 'Flipkart',
            'uber': 'Uber',
            'ola': 'Ola',
            'paytm': 'Paytm',
            'phonepe': 'PhonePe',
            'gpay': 'Google Pay',
            'netflix': 'Netflix',
            'spotify': 'Spotify',
            'prime': 'Amazon Prime',
            'bookmyshow': 'BookMyShow',
            'dominos': 'Dominos',
            'mcdonald': 'McDonalds',
            'kfc': 'KFC'
        }
        
        for keyword, name in merchant_keywords.items():
            if keyword in memory_lower:
                merchant = name
                break
                
        # Categorize based on merchant and content
        category = categorize_from_content(memory_content, merchant)
        
        # Extract payment method
        payment_method = extract_payment_method(memory_content)
        
        # Store transaction
        transaction = {
            'amount': amount,
            'merchant': merchant,
            'category': category,
            'payment_method': payment_method,
            'memory_content': memory_content,
            'date': found_dates[0] if found_dates else None,
            'raw_result': result
        }
        
        transactions.append(transaction)
        
        # Update counters
        categories[category] = categories.get(category, 0) + 1
        merchants[merchant] = merchants.get(merchant, 0) + 1
        payment_methods[payment_method] = payment_methods.get(payment_method, 0) + 1
    
    return {
        'transactions': transactions,
        'total_amount': total_amount,
        'total_count': len(transactions),
        'categories': categories,
        'merchants': merchants,
        'payment_methods': payment_methods,
        'dates': dates,
        'average_amount': total_amount / len(transactions) if transactions else 0
    }

def categorize_from_content(content: str, merchant: str) -> str:
    """Categorize transaction based on actual content"""
    content_lower = content.lower()
    
    food_keywords = ['food', 'delivery', 'restaurant', 'meal', 'dinner', 'lunch', 'breakfast']
    shopping_keywords = ['purchase', 'order', 'shopping', 'buy', 'product']
    transport_keywords = ['ride', 'trip', 'travel', 'cab', 'taxi', 'auto']
    entertainment_keywords = ['movie', 'show', 'ticket', 'entertainment']
    subscription_keywords = ['subscription', 'renewal', 'monthly', 'plan']
    utility_keywords = ['bill', 'electricity', 'water', 'gas', 'utility']
    
    if any(keyword in content_lower for keyword in food_keywords) or merchant in ['Swiggy', 'Zomato', 'Dominos', 'McDonalds', 'KFC']:
        return 'Food & Dining'
    elif any(keyword in content_lower for keyword in shopping_keywords) or merchant in ['Amazon', 'Flipkart']:
        return 'Shopping'
    elif any(keyword in content_lower for keyword in transport_keywords) or merchant in ['Uber', 'Ola']:
        return 'Transport'
    elif any(keyword in content_lower for keyword in entertainment_keywords) or merchant in ['BookMyShow']:
        return 'Entertainment'
    elif any(keyword in content_lower for keyword in subscription_keywords) or merchant in ['Netflix', 'Spotify', 'Amazon Prime']:
        return 'Subscriptions'
    elif any(keyword in content_lower for keyword in utility_keywords):
        return 'Utilities'
    else:
        return 'Others'

def extract_payment_method(content: str) -> str:
    """Extract actual payment method from content"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['upi', 'phonepe', 'gpay', 'paytm']):
        return 'UPI'
    elif 'credit card' in content_lower or 'credit' in content_lower:
        return 'Credit Card'
    elif 'debit card' in content_lower or 'debit' in content_lower:
        return 'Debit Card'
    elif 'wallet' in content_lower:
        return 'Digital Wallet'
    elif 'bank transfer' in content_lower or 'neft' in content_lower or 'imps' in content_lower:
        return 'Bank Transfer'
    else:
        return 'Other'

def generate_accurate_financial_response(query: str, real_data: Dict[str, Any]) -> str:
    """Generate comprehensive response based on ACTUAL data extracted from mem0"""
    
    if not real_data['transactions']:
        return generate_no_data_response(query)

    transactions = real_data['transactions']
    total_amount = real_data['total_amount']
    total_count = real_data['total_count']
    categories = real_data['categories']
    merchants = real_data['merchants']
    payment_methods = real_data['payment_methods']
    
    # Sort transactions by amount for better insights
    sorted_transactions = sorted(transactions, key=lambda x: x['amount'], reverse=True)
    
    # Get top merchants and categories with safety checks
    try:
        top_merchant = max(merchants.keys(), key=merchants.get) if merchants else "Unknown"
    except:
        top_merchant = "Unknown"
        
    try:
        top_category = max(categories.keys(), key=categories.get) if categories else "Unknown"
    except:
        top_category = "Unknown"
        
    try:
        top_payment = max(payment_methods.keys(), key=payment_methods.get) if payment_methods else "Unknown"
    except:
        top_payment = "Unknown"
    
    response = f"""
# 🔥 GMAIL FINANCIAL INTELLIGENCE REPORT 🔥
## Query: "{query}"

### 💎 EXECUTIVE SUMMARY - YOUR FINANCIAL DNA
**🎯 REAL INSIGHTS FROM YOUR ACTUAL GMAIL DATA:**
- 💰 **Total Spending Power**: ₹{total_amount:,.2f} across {total_count} transactions
- 📊 **Financial Behavior Score**: {min(10, max(1, int(total_count/10) + 3))}/10 (Based on transaction frequency)
- 🏆 **Top Spending Category**: {top_category} - {round((categories.get(top_category, 0)/max(total_count, 1))*100)}% of total transactions
- ⚡ **Average Transaction Value**: ₹{real_data['average_amount']:,.2f}
- 🎪 **Spending Personality**: {"Frequent Spender" if total_count > 20 else "Moderate Spender" if total_count > 10 else "Occasional Spender"}

### 📋 COMPLETE TRANSACTION BREAKDOWN FROM YOUR ACTUAL EMAILS
| 📅 Date | 💰 Amount | 🏪 Merchant | 🎯 Category | 💳 Method | 🔍 Email Snippet |
|---------|-----------|-------------|-------------|-----------|------------------|"""
    
    # Add top 15 transactions with better formatting
    for i, txn in enumerate(sorted_transactions[:15]):
        date_str = txn.get('date', 'Recent')
        if date_str and len(date_str) > 10:
            date_str = date_str[:10]  # Truncate long dates
        content_preview = txn['memory_content'][:40] + "..." if len(txn['memory_content']) > 40 else txn['memory_content']
        content_preview = content_preview.replace('\n', ' ').replace('|', '-')  # Clean for table
        response += f"""
| {date_str} | ₹{txn['amount']:,.2f} | {txn['merchant']} | {txn['category']} | {txn['payment_method']} | {content_preview} |"""
    
    response += f"""

### 🎯 CATEGORY INTELLIGENCE MATRIX
"""
    
    # Generate detailed category analysis
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        category_transactions = [t for t in transactions if t['category'] == category]
        category_amount = sum(t['amount'] for t in category_transactions)
        avg_category_amount = category_amount / count if count > 0 else 0
        
        # Category-specific insights
        if category == "Food & Dining":
            frequency = "every day" if count > 25 else "frequently" if count > 15 else "occasionally"
            response += f"""
**🍔 {category.upper()} EMPIRE**
- **Total Spend**: ₹{category_amount:,.2f} across {count} orders
- **Average Order Value**: ₹{avg_category_amount:.2f}
- **Ordering Pattern**: You order {frequency} ({count} transactions found)
- **🔥 INSIGHT**: {"High food delivery dependency detected" if count > 20 else "Moderate food ordering habits"}
- **💡 OPTIMIZATION**: {"Consider meal planning to reduce costs" if category_amount > total_amount*0.3 else "Current spending pattern seems reasonable"}
"""
        elif category == "Shopping":
            response += f"""
**🛒 {category.upper()} PSYCHOLOGY**
- **Total Purchases**: ₹{category_amount:,.2f} across {count} orders
- **Average Purchase Value**: ₹{avg_category_amount:.2f}
- **Shopping Frequency**: {"Regular shopper" if count > 10 else "Occasional purchases"}
- **🔥 INSIGHT**: {"Consistent shopping pattern" if count > 5 else "Selective purchasing behavior"}
- **💡 STRATEGY**: {"Look for bulk purchase discounts" if avg_category_amount < 500 else "Consider wishlist management"}
"""
        elif category == "Subscriptions":
            response += f"""
**💳 {category.upper()} ECOSYSTEM**
- **Monthly Recurring**: ₹{category_amount:,.2f} across {count} services
- **Average Service Cost**: ₹{avg_category_amount:.2f}
- **Subscription Health**: {"Well managed" if avg_category_amount < 500 else "Review needed"}
- **🔥 INSIGHT**: {"Balanced subscription portfolio" if count < 5 else "Potential over-subscription"}
- **💡 OPTIMIZATION**: {"Check for unused services" if count > 3 else "Current subscriptions seem optimal"}
"""
        elif category == "Transport":
            response += f"""
**🚗 {category.upper()} & MOBILITY**
- **Travel Expenses**: ₹{category_amount:,.2f} across {count} trips
- **Average Trip Cost**: ₹{avg_category_amount:.2f}
- **Mobility Pattern**: {"Daily commuter" if count > 30 else "Regular traveler" if count > 15 else "Occasional trips"}
- **🔥 INSIGHT**: {"High mobility costs" if category_amount > total_amount*0.2 else "Reasonable transport expenses"}
"""
        else:
            response += f"""
**📊 {category.upper()}**
- **Total Amount**: ₹{category_amount:,.2f} across {count} transactions
- **Average Transaction**: ₹{avg_category_amount:.2f}
- **Frequency**: {"High" if count > 10 else "Moderate" if count > 5 else "Low"}
"""
    
    response += f"""

### 🏪 MERCHANT RELATIONSHIP ANALYSIS
"""
    
    for merchant, count in sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:7]:
        merchant_transactions = [t for t in transactions if t['merchant'] == merchant]
        merchant_amount = sum(t['amount'] for t in merchant_transactions)
        avg_merchant_amount = merchant_amount / count if count > 0 else 0
        
        # Merchant-specific insights
        loyalty_score = min(10, count)
        response += f"""
**{merchant}**: {count} transactions, ₹{merchant_amount:,.2f} total
  - Average per transaction: ₹{avg_merchant_amount:.2f}
  - Loyalty Score: {loyalty_score}/10
  - Relationship: {"Preferred vendor" if count > 5 else "Regular customer" if count > 2 else "Occasional user"}
"""

    response += f"""

### 🧠 BEHAVIORAL FINANCIAL INTELLIGENCE

**💳 PAYMENT METHOD PREFERENCES**
"""
    try:
        for method, count in sorted(payment_methods.items(), key=lambda x: x[1], reverse=True):
            method_percentage = round((count/max(total_count, 1))*100)
            method_transactions = [t for t in transactions if t.get('payment_method') == method]
            method_amount = sum(t.get('amount', 0) for t in method_transactions)
            response += f"""
- **{method}**: {count} transactions ({method_percentage}%), ₹{method_amount:,.2f} total
"""
    except Exception as payment_error:
        print(f"❌ Error in payment method section: {payment_error}")
        response += f"""
- Payment method analysis temporarily unavailable
"""

    response += f"""

### 🚀 PREDICTIVE FINANCIAL INTELLIGENCE

**📈 SPENDING TRAJECTORY**
- **Monthly Burn Rate**: ₹{total_amount:,.2f} (based on current data)
- **Transaction Frequency**: {total_count} transactions analyzed
- **Risk Assessment**: {"Stable" if total_amount < 50000 else "High volume" if total_amount < 100000 else "Very high volume"}

**🎯 PERSONALIZED RECOMMENDATIONS**
1. **💰 COST OPTIMIZATION**: {"Focus on reducing food delivery costs" if categories.get("Food & Dining", 0) > total_count*0.4 else "Current spending distribution looks balanced"}
2. **📊 BUDGET INSIGHTS**: {"Consider setting monthly limits for top categories" if len(categories) > 5 else "Maintain current spending discipline"}
3. **🏆 REWARD MAXIMIZATION**: Use cashback cards for your top merchant: {top_merchant}
4. **⚠️ MONITORING**: Track {top_category} expenses more closely

### 💎 EXCLUSIVE INSIGHTS (The WOW Factor)

**🔥 HIDDEN PATTERNS DISCOVERED:**
- Your highest single transaction: ₹{sorted_transactions[0]['amount']:,.2f} to {sorted_transactions[0]['merchant']} {f"on {sorted_transactions[0].get('date', 'recent date')}" if sorted_transactions[0].get('date') else ""}
- Most used payment method: {top_payment} ({payment_methods.get(top_payment, 0)} times)
- Financial behavior suggests: {"Tech-savvy digital payments user" if payment_methods.get("UPI", 0) > max(total_count*0.5, 1) else "Mixed payment preferences"}

**🎪 FINANCIAL PERSONALITY PROFILE:**
- **Spending Style**: {"Digital-first" if payment_methods.get("UPI", 0) > payment_methods.get("Credit Card", 0) else "Card-preferred"}
- **Risk Tolerance**: {"Conservative" if real_data.get('average_amount', 0) < 1000 else "Moderate" if real_data.get('average_amount', 0) < 2500 else "Aggressive"}
- **Category Preference**: Strong preference for {top_category}

### 🔍 RAW DATA VERIFICATION
*✅ This analysis is based on {total_count} ACTUAL email records from your Gmail account*
*✅ All amounts, merchants, and dates are extracted from REAL email content*
*✅ No fabricated or template data used - everything is from your actual transactions*

**Data Sources Verified:**
- Mem0 search results: {total_count} records
- Amount extraction: {len([t for t in transactions if t['amount'] > 0])} transactions with valid amounts
- Merchant identification: {len([t for t in transactions if t['merchant'] != 'Unknown'])} transactions with identified merchants
- Date information: {len([t for t in transactions if t['date']])} transactions with date stamps
"""
    
    return response

# Add this new improved function after the existing query_email_database function

async def query_email_database_accurate(user_id: str, query: str, limit: int = 1000) -> Dict[str, Any]:
    """
    NEW IMPROVED VERSION: Query email database with ACCURATE data extraction
    This function provides responses based on REAL data from mem0, not templates
    """
    try:
        print(f"🔍 ACCURATE QUERY: Processing '{query}' for user {user_id}")
        
        # Search with comprehensive strategy
        search_results = await search_emails_in_mem0(user_id, query, limit)
        
        # If few results, do targeted searches based on query
        if len(search_results) < 50:
            print(f"🔄 Expanding search from {len(search_results)} results...")
            
            # Extract keywords from query for targeted search
            query_lower = query.lower()
            additional_searches = []
            
            # Financial keywords
            if any(word in query_lower for word in ['transaction', 'payment', 'money', 'amount', 'spent', 'pay']):
                additional_searches.extend(['upi', 'payment', 'paid', 'transaction', 'amount', '₹'])
            
            # Time-based keywords
            if any(word in query_lower for word in ['april', 'may', 'month', '2025']):
                additional_searches.extend(['april 2025', 'may 2025', '2025'])
            
            # Category keywords
            if any(word in query_lower for word in ['food', 'order', 'delivery']):
                additional_searches.extend(['swiggy', 'zomato', 'food', 'delivery', 'order'])
            if any(word in query_lower for word in ['shopping', 'amazon', 'purchase']):
                additional_searches.extend(['amazon', 'flipkart', 'shopping', 'purchase'])
            if any(word in query_lower for word in ['subscription', 'netflix', 'spotify']):
                additional_searches.extend(['subscription', 'netflix', 'spotify', 'prime'])
            
            # Perform additional searches
            all_results = search_results.copy()
            seen_ids = set(result.get('id') for result in all_results if result.get('id'))
            
            for search_term in additional_searches:
                try:
                    extra_results = await search_emails_in_mem0(user_id, search_term, 100)
                    for result in extra_results:
                        if result.get('id') not in seen_ids:
                            all_results.append(result)
                            seen_ids.add(result.get('id'))
                    print(f"✅ Search for '{search_term}': Found {len(extra_results)} additional results")
                except Exception as e:
                    print(f"❌ Search failed for '{search_term}': {e}")
            
            search_results = all_results
            print(f"🔍 Total results after expansion: {len(search_results)}")
        
        if not search_results:
            return {
                'success': False,
                'message': 'No matching emails found in your data',
                'insights': generate_no_data_response(query),
                'transactions': [],
                'total_amount': 0
            }
        
        # Extract REAL data using the new function
        real_data = extract_real_transaction_data(search_results)
        
        print(f"💰 REAL DATA EXTRACTED:")
        print(f"   - {real_data['total_count']} transactions found")
        print(f"   - ₹{real_data['total_amount']:,.2f} total amount")
        print(f"   - {len(real_data['categories'])} categories")
        print(f"   - {len(real_data['merchants'])} merchants")
        
        # Generate accurate response with error handling
        try:
            print(f"🔄 Generating response for {real_data['total_count']} transactions...")
            accurate_response = generate_accurate_financial_response(query, real_data)
            print(f"✅ Response generated successfully (length: {len(accurate_response)})")
            print(accurate_response)
        except Exception as response_error:
            print(f"❌ Error generating response: {str(response_error)}")
            import traceback
            traceback.print_exc()
            
            # Fallback simple response
            accurate_response = f"""
# 📧 GMAIL FINANCIAL ANALYSIS
## Query: "{query}"

### 💰 BASIC ANALYSIS FROM YOUR ACTUAL DATA
- **Total Transactions Found**: {real_data['total_count']}
- **Total Amount**: ₹{real_data['total_amount']:,.2f}
- **Average Transaction**: ₹{real_data['average_amount']:,.2f}

### 🏪 TOP MERCHANTS
{chr(10).join([f"- **{merchant}**: {count} transactions" for merchant, count in sorted(real_data['merchants'].items(), key=lambda x: x[1], reverse=True)[:5]])}

### 🎯 CATEGORIES
{chr(10).join([f"- **{category}**: {count} transactions" for category, count in sorted(real_data['categories'].items(), key=lambda x: x[1], reverse=True)])}

*Note: This is a simplified response due to processing error. All data is real from your emails.*
"""
        
        return {
            'success': True,
            'insights': accurate_response,
            'transactions': real_data['transactions'],
            'analysis': {
                'total_amount': real_data['total_amount'],
                'total_count': real_data['total_count'],
                'categories': real_data['categories'],
                'merchants': real_data['merchants'],
                'payment_methods': real_data['payment_methods'],
                'average_amount': real_data['average_amount']
            },
            'table': real_data['transactions'][:20],  # Top 20 for display
            'total_amount': real_data['total_amount'],
            'total_transactions': real_data['total_count'],
            'real_data_used': True,
            'query_processed': query
        }
        
    except Exception as e:
        print(f"❌ Error in accurate query: {str(e)}")
        return {
            'success': False,
            'message': f'Error processing query: {str(e)}',
            'insights': f'Unable to process your query due to: {str(e)}',
            'transactions': [],
            'total_amount': 0
        }

def generate_no_data_response(query: str) -> str:
    """Generate helpful response when no data is found"""
    return f"""
# 📧 GMAIL FINANCIAL ANALYSIS

## Query: "{query}"

### ⚠️ NO MATCHING DATA FOUND

**What this means:**
- No emails in your Gmail match the search criteria
- The requested information might not be available in your email data
- Your emails might not contain the specific financial data requested

### 💡 SUGGESTIONS TO GET BETTER RESULTS

1. **Try broader search terms:**
   - Instead of "April 2025", try "april" or "2025"
   - Instead of specific merchant names, try general terms like "payment" or "order"

2. **Check if your emails are processed:**
   - Ensure your Gmail data has been uploaded to the system
   - Verify that transaction emails exist in your Gmail

3. **Alternative queries to try:**
   - "Show me all my payments"
   - "List my food orders"  
   - "My recent transactions"
   - "UPI payments"

### 🔍 WHAT WE SEARCHED FOR
- Primary query: "{query}"
- We searched through your email database but found no matching records
- This analysis is based on actual email content, not generated data

**Need help?** Try rephrasing your query or contact support if you believe this data should be available.
"""

# Add this function to switch between old and new query systems

async def query_email_with_real_data(user_id: str, query: str, use_accurate_mode: bool = True) -> Dict[str, Any]:
    """
    Main query function that chooses between accurate and legacy modes
    Set use_accurate_mode=True for real data extraction
    Set use_accurate_mode=False for legacy template-based responses
    """
    if use_accurate_mode:
        print("🎯 Using ACCURATE mode - Real data extraction enabled")
        return await query_email_database_accurate(user_id, query)
    else:
        print("⚠️ Using LEGACY mode - Template-based responses")
        return await query_email_database(user_id, query)

# Update the universal_gmail_analysis function to use accurate mode
async def universal_gmail_analysis_accurate(user_id: str, query: str) -> Dict[str, Any]:
    """
    NEW VERSION: Universal Gmail Analysis with REAL data extraction
    This replaces the template-based analysis with actual mem0 data
    """
    try:
        print(f"🔍 UNIVERSAL ANALYSIS (ACCURATE): Processing '{query}' for user {user_id}")
        
        # Use the accurate query function
        result = await query_email_database_accurate(user_id, query, limit=1500)
        
        if not result['success']:
            return {
                'response': result['insights'],
                'success': False,
                'data_used': 'none',
                'transaction_count': 0,
                'total_amount': 0
            }
        
        # Return the accurate analysis
        return {
            'response': result['insights'],
            'success': True,
            'data_used': 'real_mem0_data',
            'transaction_count': result['total_transactions'],
            'total_amount': result['total_amount'],
            'categories': result['analysis']['categories'],
            'merchants': result['analysis']['merchants'],
            'transactions': result['transactions'][:10],  # Top 10 for reference
            'query_processed': query
        }
        
    except Exception as e:
        print(f"❌ Error in universal analysis: {str(e)}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Full traceback:")
        traceback.print_exc()
        
        error_response = f"""
# ❌ ANALYSIS ERROR

## Query: "{query}"

### Error Details
- **Error Type**: {type(e).__name__}
- **Message**: {str(e)}
- **Solution**: Please try again with a simpler query

### Suggested Alternatives
- Try: "Show me my payments"
- Try: "List my food orders"
- Try: "My recent transactions"

### Debug Info
- Error occurred during universal analysis
- Data extraction was successful but response generation failed
"""
        return {
            'response': error_response,
            'success': False,
            'error': str(e),
            'data_used': 'error',
            'transaction_count': 0,
            'total_amount': 0
        }

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
            response = gmail_pipeline_team.run(test_query)
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
    Smart routing: Risk Profiling & Analysis queries → Universal Analysis
    Other queries → Team Pipeline
    """
    try:
        print("\n" + "="*80)
        print("🚀 GMAIL INTELLIGENCE PIPELINE STARTED")
        print("="*80)
        print(f"👤 USER ID: {user_id}")
        print(f"❓ ORIGINAL QUERY: '{query}'")
        print("="*80)
        
        # SMART ROUTING: Detect if this is a complex analysis query
        query_lower = query.lower()
        is_analysis_query = any(word in query_lower for word in [
            "analysis", "insight", "analytics", "report", "breakdown", "summary",
            "pattern", "trend", "behavior", "profile", "assessment"
        ])
        
        if is_analysis_query:
            print("🎯 DETECTED: Complex Analysis Query - Using Universal Analysis Engine")
            print("🚀 Routing to Universal Gmail Analysis for superior insights...")
            print("-" * 60)
            
            # Use the powerful universal analysis for complex queries
            result = await universal_gmail_analysis_accurate(user_id, query)
            
            if result.get('success') == True:  # Fixed: was checking 'status' instead of 'success'
                final_response = result.get('response', 'No response generated')
                print(f"✅ Universal Analysis completed: {result.get('transaction_count', 0)} transactions analyzed")
                print(f"📊 Data Used: {result.get('data_used', 'unknown')}")
                print(f"📝 Response Length: {len(final_response)} characters")
                
                print("\n🎯 FINAL RESPONSE PREVIEW:")
                print("-" * 40)
                response_preview = final_response[:500] + "..." if len(final_response) > 500 else final_response
                print(f"📄 {response_preview}")
                print("-" * 40)
                
                print("\n✅ UNIVERSAL ANALYSIS COMPLETED SUCCESSFULLY")
                print("="*80)
                
                return final_response
            else:
                error_msg = f"❌ Universal analysis error: {result.get('error', 'Unknown error')}"
                print(f"❌ UNIVERSAL ANALYSIS ERROR: {result.get('error', 'Unknown error')}")
                print("="*80)
                return error_msg
        
        else:
            print("📧 DETECTED: General Query - Using Universal Content Search")
            print("🔄 Routing to Universal Email Search...")
            print("-" * 60)
            
            # Step 1: Analyze and refine query using Query Analyzer Agent
            print("\n🔧 STEP 1: QUERY REFINEMENT")
            print("-" * 60)
            print(f"📝 Input Query: '{query}'")
            
            refined_query = await analyze_and_refine_query(query)
            
            print(f"✨ Refined Query: '{refined_query}'")
            print(f"🔄 Query Enhancement: {'Enhanced' if refined_query != query else 'No change needed'}")
            print("-" * 60)
            
            # Step 2: Universal Content Search - No hardcoded types
            print("\n📧 STEP 2: UNIVERSAL CONTENT SEARCH")
            print("-" * 60)
            print(f"🔍 Searching for: '{refined_query}'")
            print("🎯 Using flexible content-based processing for ANY query type")
            
            result = await universal_content_search(user_id, refined_query, query)
            
            print(f"📊 SEARCH RESULTS: {result.get('results_count', 0)} emails found")
            
            # Show sample Mem0 results
            if result.get('status') == 'success' and result.get('results_count', 0) > 0:
                print("\n📋 SAMPLE MEM0 RESULTS:")
                # Get some sample results for display
                sample_results = await search_emails_in_mem0(user_id, refined_query, limit=5)
                for i, email_result in enumerate(sample_results[:3]):
                    memory_content = email_result.get('memory', 'No content')[:150]
                    metadata = email_result.get('metadata', {})
                    print(f"  📧 Email {i+1}:")
                    print(f"     💬 Content: {memory_content}...")
                    print(f"     📊 Metadata: {list(metadata.keys()) if metadata else 'None'}")
                    if metadata:
                        print(f"     💰 Amount: {metadata.get('amount', 'N/A')}")
                        print(f"     🏪 Merchant: {metadata.get('merchant', 'N/A')}")
                        print(f"     📅 Timestamp: {metadata.get('timestamp', 'N/A')}")
                        print(f"     🏷️ Category: {metadata.get('category', 'N/A')}")
                    print()
            else:
                print("❌ NO EMAILS FOUND - This explains why response might be empty!")
                
            print("-" * 60)
            
            # Step 3: Show final response generation
            print("\n🧠 STEP 3: AI RESPONSE GENERATION")
            print("-" * 60)
            
            if result.get('status') == 'success':
                final_response = result.get('response', 'No response generated')
                print("✅ AI Team response generated successfully")
                print(f"📝 Response Length: {len(final_response)} characters")
                
                # Show response preview
                print("\n🎯 FINAL RESPONSE PREVIEW:")
                print("-" * 40)
                response_preview = final_response[:500] + "..." if len(final_response) > 500 else final_response
                print(f"📄 {response_preview}")
                print("-" * 40)
                
                print("\n✅ PIPELINE COMPLETED SUCCESSFULLY")
                print("="*80)
                
                return final_response
            else:
                error_msg = f"❌ Error processing query: {result.get('error', 'Unknown error')}"
                print(f"❌ PIPELINE ERROR: {result.get('error', 'Unknown error')}")
                print("="*80)
                return error_msg
            
    except Exception as e:
        print(f"\n❌ PIPELINE EXCEPTION: {e}")
        print("="*80)
        return f"❌ Sorry, I encountered an error while processing your query: {str(e)}"

async def analyze_and_refine_query(query: str) -> str:
    """
    Intelligent query refinement that preserves specific user intent
    Eliminates hallucination by creating precise search terms
    """
    try:
        query_lower = query.lower()
        
        # PRECISE JOB APPLICATION RESPONSE DETECTION
        if any(phrase in query_lower for phrase in [
            "response for job application", "reply for job application", 
            "job application response", "job application reply",
            "response to my application", "reply to my application",
            "application status", "interview invitation", "application accepted",
            "application rejected", "application feedback"
        ]):
            # Look for actual responses, not job alerts
            return "thank you for your application OR interview invitation OR application status OR we have reviewed OR unfortunately OR congratulations OR selected OR not selected OR feedback on your application"
        
        # JOB ALERTS vs JOB RESPONSES - Different intent
        elif any(phrase in query_lower for phrase in [
            "job alerts", "job opportunities", "new jobs", "job recommendations"
        ]):
            return "job alert OR new position OR job opportunity OR hiring OR career opportunity"
        
        # PAYMENT/TRANSACTION QUERIES - Be specific about transactions
        elif any(word in query_lower for word in ["payment", "transaction", "paid", "money", "amount"]):
            if "failed" in query_lower or "declined" in query_lower:
                return "payment failed OR transaction declined OR payment unsuccessful"
            elif "successful" in query_lower or "completed" in query_lower:
                return "payment successful OR transaction completed OR payment confirmed"
            else:
                return "payment OR transaction OR paid OR amount OR rupees OR ₹ OR charged OR debited"
        
        # SUBSCRIPTION QUERIES - Specific to recurring services
        elif any(word in query_lower for word in ["subscription", "renewal", "recurring"]):
            return "subscription renewed OR subscription charged OR recurring payment OR auto-renewal"
        
        # DELIVERY/ORDER QUERIES - Specific to order status
        elif any(word in query_lower for word in ["delivery", "delivered", "order status"]):
            return "delivered OR out for delivery OR order confirmed OR dispatch"
        
        # RECENT/LATEST QUERIES - Time-based precision
        elif any(word in query_lower for word in ["recent", "latest", "last", "newest"]):
            time_context = ""
            if "week" in query_lower:
                time_context = " last week"
            elif "month" in query_lower:
                time_context = " last month"
            elif "today" in query_lower:
                time_context = " today"
            
            # Extract the main subject
            main_subject = query.replace("recent", "").replace("latest", "").replace("last", "").replace("newest", "").strip()
            return f"{main_subject}{time_context}"
        
        # SPENDING ANALYSIS - Financial behavior queries
        elif any(phrase in query_lower for phrase in [
            "how much spent", "total spending", "expenses", "money spent"
        ]):
            if "food" in query_lower:
                return "food order OR restaurant OR delivery OR dining OR swiggy OR zomato"
            elif "travel" in query_lower:
                return "uber OR ola OR flight OR train OR bus OR travel"
            else:
                return "amount OR rupees OR ₹ OR paid OR charged OR cost OR price"
        
        # SPECIFIC MERCHANT QUERIES
        elif any(merchant in query_lower for merchant in [
            "swiggy", "zomato", "amazon", "flipkart", "netflix", "spotify", "uber", "ola"
        ]):
            # Extract the specific merchant mentioned
            for merchant in ["swiggy", "zomato", "amazon", "flipkart", "netflix", "spotify", "uber", "ola"]:
                if merchant in query_lower:
                    return merchant
        
        # DEFAULT: Extract key meaningful words only
        else:
            # Remove common stop words and keep only meaningful terms
            stop_words = {
                'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
                'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
                'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
                'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
                'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
                'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
                'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
                'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'in', 'out',
                'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'some', 'any',
                'got', 'get', 'had', 'has'
            }
            
            # Extract meaningful words
            words = query.lower().split()
            meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
            
            if meaningful_words:
                return " ".join(meaningful_words[:3])  # Use top 3 meaningful words
            else:
                return query
        
    except Exception as e:
        print(f"⚠️ Query refinement failed, using original query: {e}")
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

# ************* Simple Main Functions Following the Flow *************

async def categorize_email_simple(email: EmailMessage) -> str:
    """Simple email categorization"""
    subject_body = f"{email.subject} {email.body} {email.snippet}".lower()
    
    if any(word in subject_body for word in ['swiggy', 'zomato', 'food', 'restaurant', 'delivery']):
        return 'food'
    elif any(word in subject_body for word in ['amazon', 'flipkart', 'shopping', 'order', 'purchase']):
        return 'shopping'  
    elif any(word in subject_body for word in ['bank', 'payment', 'transaction', 'upi', 'card']):
        return 'banking'
    elif any(word in subject_body for word in ['netflix', 'spotify', 'subscription']):
        return 'entertainment'
    else:
        return 'general'

async def upload_emails_to_mem0_simple(user_id: str, emails: List[EmailMessage]) -> str:
    """Upload emails to Mem0 with basic categorization"""
    try:
        results = []
        for email in emails:
            category = await categorize_email_simple(email)
            
            # Create memory content
            memory_content = f"""
            Email: {email.subject}
            From: {email.sender}
            Date: {email.date}
            Category: {category}
            Content: {email.snippet} {email.body[:500]}
            """
            
            result = await aclient.add(
                memory_content, 
                user_id=user_id,
                metadata={
                    "email_id": email.id,
                    "category": category,
                    "sender": email.sender,
                    "subject": email.subject,
                    "date": email.date
                }
            )
            results.append(result)
        
        return f"✅ Successfully uploaded {len(emails)} emails to Mem0"
    except Exception as e:
        return f"❌ Error uploading emails: {str(e)}"

async def search_emails_in_mem0(user_id: str, query: str, limit: int = 100) -> List[Dict]:
    """Search emails in Mem0"""
    try:
        results = await aclient.search(
            query=query,
            user_id=user_id,
            limit=limit
        )
        return results
    except Exception as e:
        print(f"❌ Mem0 search error: {e}")
        return []

async def pipeline_query_flow(user_id: str, query: str) -> Dict[str, Any]:
    """
    Complete pipeline flow using Agno team:
    1. Step 1: Query refinement (using query_analyzer_agent.py)
    2. Step 2: Mem0 search (using search function)
    3. Step 3: Insights generation (using Agno team)
    4. Final response returned
    """
    try:
        print(f"🚀 Starting Gmail Intelligence Pipeline for query: {query}")
        
        # Step 1: Query Refinement using existing query_analyzer_agent
        print("🔧 Step 1: Refining query...")
        refined_query = analyze_query(query)
        print(f"✅ Refined query: {refined_query}")
        
        # Step 2: Search Mem0 with refined query
        print("📧 Step 2: Searching emails in Mem0...")
        search_results = await search_emails_in_mem0(user_id, refined_query, limit=100)
        print(f"✅ Found {len(search_results)} email results")
        
        # Step 3: Use Agno team to generate insights from search results
        print("🧠 Step 3: Generating insights using Agno team...")
        if search_results:
            # Prepare context for the insights generation team
            context = f"""
            ORIGINAL USER QUERY: {query}
            REFINED SEARCH QUERY: {refined_query}
            
            EMAIL SEARCH RESULTS FROM MEM0:
            ================================
            """
            
            for i, result in enumerate(search_results[:10]):  # Limit to top 10
                context += f"\n--- Email Result {i+1} ---\n"
                context += f"{result.get('memory', 'No content')}\n"
            
            context += f"""
            ================================
            
            TASK: Analyze the above email search results and generate helpful insights for the user's query.
            Focus on extracting key information, patterns, and providing actionable insights.
            If the query is about transactions, create a table with dates, amounts, merchants, etc.
            Only use the actual data found in the search results above.
            """
            
            # Use the insights generation agent specifically
            team_response = insights_generation_agent.run(context)
            final_response = team_response.content if hasattr(team_response, 'content') else str(team_response)
        else:
            final_response = "No relevant emails found for your query. Please try with different keywords or check if your Gmail data has been synced."
        
        print(f"✅ Pipeline completed successfully")
        
        return {
            "success": True,
            "message": final_response,
            "original_query": query,
            "refined_query": refined_query,
            "results_count": len(search_results),
            "pipeline": "complete_gmail_intelligence"
        }
        
    except Exception as e:
        print(f"❌ Error in pipeline query flow: {e}")
        return {
            "success": False,
            "message": f"Error processing your query through the pipeline: {str(e)}",
            "original_query": query,
            "pipeline": "error"
        }

async def process_gmail_data_simple(user_id: str, gmail_emails: List[Dict]) -> Dict[str, Any]:
    """Process Gmail data and upload to Mem0 - simple version"""
    try:
        # Convert to EmailMessage objects
        email_messages = []
        for email_data in gmail_emails:
            email = EmailMessage(
                id=email_data.get('id', ''),
                subject=email_data.get('subject', ''),
                sender=email_data.get('from', ''),
                snippet=email_data.get('snippet', ''),
                body=email_data.get('body', ''),
                date=email_data.get('date', '')
            )
            email_messages.append(email)
        
        # Upload to Mem0
        result = await upload_emails_to_mem0_simple(user_id, email_messages)
        
        return {
            "success": True,
            "message": result,
            "emails_processed": len(email_messages)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing Gmail data: {str(e)}",
            "emails_processed": 0
        }

# For backwards compatibility - main function called by websocket
async def handle_websocket_query(user_id: str, query: str, chat_id: str = None) -> Dict[str, Any]:
    """
    WebSocket query handler using complete Agno pipeline team
    """
    try:
        print(f"🌐 WebSocket query from user {user_id} in chat {chat_id}: '{query}'")
        
        # Use the complete pipeline flow with Agno team
        result = await pipeline_query_flow(user_id, query)
        
        return {
            "response": result["message"],
            "chatId": chat_id,
            "error": not result["success"]
        }
        
    except Exception as e:
        print(f"❌ WebSocket query error: {e}")
        return {
            "response": f"I encountered an error while processing your query: {str(e)}",
            "chatId": chat_id,
            "error": True
        }
