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

async def categorize_email(email: EmailMessage) -> EmailInsight:
    """Categorize email and extract insights"""
    subject_lower = email.subject.lower()
    sender_lower = email.sender.lower()
    content_lower = f"{subject_lower} {email.snippet.lower()} {email.body.lower()}"

    # Extract amount if present
    amount_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', content_lower)
    amount = amount_match.group(1).replace(',', '') if amount_match else None

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
            print(f"✅ Processed: {email.id} | {insight.category}/{insight.subcategory} | {insight.merchant}")
        except Exception as e:
            print(f"❌ Error processing {email.id}: {e}")

    return f"Successfully processed {processed_count}/{len(emails)} emails for user {user_id}"

async def search_emails_in_mem0(user_id: str, query: str, limit: int = 100) -> List[Dict]:
    """Search emails in Mem0 memory"""
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
        Analyze the Gmail data processing results:
        
        - User ID: {user_id}
        - Total emails processed: {len(gmail_emails)}
        - Processing result: {upload_result}
        
        Provide a comprehensive processing summary with:
        1. Processing statistics and success rate
        2. Category insights discovered from the emails
        3. Key patterns and trends identified
        4. Actionable recommendations for the user
        5. Next steps for email management
        
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

async def query_email_database(user_id: str, query: str, limit: int = 100, category: str = None) -> Dict[str, Any]:
    """Query email database using Gmail Intelligence Team"""
    try:
        print(f"🔍 Gmail Intelligence Team: Processing query '{query}' for user {user_id}")
        
        # Search Mem0 memory
        search_results = await search_emails_in_mem0(user_id, query, limit)
        
        # Use team to process query with search results
        team_prompt = f"""
        Process this email query with intelligent analysis:
        
        User Query: "{query}"
        User ID: {user_id}
        Category Filter: {category or "None"}
        Search Results Count: {len(search_results)}
        Search Results from Mem0: {json.dumps(search_results[:10], indent=2) if search_results else "No results found"}
        
        Provide a comprehensive response that:
        1. Analyzes the user's query intent and context
        2. Processes the search results intelligently
        3. Provides structured, actionable insights
        4. Includes relevant details (amounts, dates, merchants, categories)
        5. Offers follow-up suggestions and recommendations
        6. Summarizes key findings and patterns
        
        Format the response clearly with sections, insights, and professional presentation.
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
        
        # Query different aspects of user's emails from Mem0
        analytics_queries = [
            "spending and expenses",
            "subscription services and renewals",
            "payment reminders and bills",
            "food delivery orders",
            "shopping and ecommerce orders",
            "banking and financial transactions"
        ]
        
        analytics_data = {}
        for query in analytics_queries:
            results = await search_emails_in_mem0(user_id, query, 50)
            analytics_data[query] = results
        
        # Use team to generate comprehensive analytics report
        team_prompt = f"""
        Generate a comprehensive email analytics report for user {user_id}:
        
        Analytics Data from Mem0 Memory:
        {json.dumps(analytics_data, indent=2)}
        
        Create a detailed, professional analytics report with:
        1. Executive Summary of email patterns and insights
        2. Spending Analysis and Financial Patterns
        3. Subscription Management Status and Recommendations
        4. Bill and Payment Tracking Analysis
        5. Shopping Behavior Insights and Trends
        6. Financial Health Indicators and Alerts
        7. Category-wise Breakdown and Statistics
        8. Key Recommendations and Action Items
        9. Trend Analysis and Future Predictions
        10. Risk Assessment and Alerts
        
        Format as a comprehensive, structured report with:
        - Clear sections and headings
        - Data-driven insights with specific numbers
        - Actionable recommendations
        - Professional presentation with tables where appropriate
        - Key takeaways and next steps
        """
        
        team_response = gmail_intelligence_team.run(team_prompt)
        
        return {
            "status": "success",
            "user_id": user_id,
            "analytics_report": team_response.content if hasattr(team_response, 'content') else str(team_response),
            "data_sources": list(analytics_data.keys()),
            "total_data_points": sum(len(results) for results in analytics_data.values()),
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
                print("📤 Uploading sample emails using Gmail Intelligence Team...")
                sample_emails = [
                    {
                        "id": f"sample_{user_id}_001",
                        "subject": "Your Swiggy Order Delivered",
                        "sender": "order@swiggy.in",
                        "snippet": "Chicken Biryani ₹299 delivered",
                        "body": "Thank you for ordering!",
                        "date": "2025-01-15T19:30:00+0530"
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
