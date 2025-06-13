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

# Email Processing Agent
class EmailProcessorAgent(Agent):
    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4"),
            name="EmailProcessor",
            role="Email data processor and categorizer",
            instructions=[
                "You are an expert email processor that categorizes and extracts insights from email data.",
                "You process emails and store them in Mem0 with proper categorization and metadata.",
                "You handle Gmail data and prepare it for intelligent storage and retrieval.",
                "Always provide detailed categorization and extract relevant financial information."
            ],
        )

    async def categorize_email(self, email: EmailMessage) -> EmailInsight:
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

    async def upload_emails(self, request: EmailUploadRequest) -> str:
        """Upload emails to Mem0 with categorization"""
        print(f"🔄 EmailProcessor Agent: Processing {len(request.emails)} emails for user {request.user_id}")
        
        processed_count = 0
        for email in request.emails:
            if not email.id:
                continue

            # Categorize email
            insight = await self.categorize_email(email)
            
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
                    user_id=request.user_id, 
                    memory_id=email.id, 
                    metadata=metadata
                )
                processed_count += 1
                print(f"✅ Processed: {email.id} | {insight.category}/{insight.subcategory} | {insight.merchant}")
            except Exception as e:
                print(f"❌ Error processing {email.id}: {e}")

        return f"Successfully processed {processed_count}/{len(request.emails)} emails for user {request.user_id}"

# Email Query Agent
class EmailQueryAgent(Agent):
    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4"),
            name="EmailQueryAgent",
            role="Intelligent email search and analysis assistant",
            instructions=[
                "You are an intelligent email query agent that helps users find and analyze their email data.",
                "You use advanced search techniques including sub-query generation and semantic search.",
                "You provide comprehensive, well-formatted responses with insights and analytics.",
                "You excel at understanding user intent and finding relevant emails from Mem0 storage.",
                "Always format responses clearly with emojis, sections, and actionable insights."
            ],
        )

    async def generate_sub_queries(self, original_query: str) -> List[str]:
        """Generate intelligent sub-queries using LLM"""
        try:
            prompt = f"""
Generate 3-5 related sub-queries for email search based on: "{original_query}"

Consider:
- Synonyms and related terms
- Different email formats and patterns
- Broader and narrower interpretations
- Common merchant names and services

Examples:
- "food orders" → ["food delivery", "Swiggy orders", "Zomato orders", "restaurant orders"]
- "bills" → ["utility bills", "electricity bill", "payment reminders", "due dates"]

Return only a JSON array of strings.
"""
            
            response = self.run(prompt)
            
            if response and hasattr(response, 'content'):
                try:
                    sub_queries = json.loads(response.content)
                    if original_query not in sub_queries:
                        sub_queries.insert(0, original_query)
                    return sub_queries[:5]
                except json.JSONDecodeError:
                    return [original_query]
            
            return [original_query]
        except Exception as e:
            print(f"❌ Error generating sub-queries: {e}")
            return [original_query]

    async def search_emails(self, user_id: str, sub_queries: List[str]) -> List[Dict]:
        """Search Mem0 for emails using multiple sub-queries"""
        all_results = []
        
        for sub_query in sub_queries:
            try:
                results = sync_client.search(
                    query=sub_query,
                    user_id=user_id,
                    limit=2220,
                    filters={"metadata.source": "gmail"},
                    keyword_search=True,
                    rerank=True,
                    filter_memories=False
                )
                
                if results:
                    all_results.extend(results)
                    
            except Exception as e:
                print(f"❌ Search error for '{sub_query}': {e}")
        
        # Remove duplicates
        unique_results = []
        seen_memories = set()
        for result in all_results:
            memory_text = result.get('memory', '')
            if memory_text not in seen_memories:
                unique_results.append(result)
                seen_memories.add(memory_text)
        
        return unique_results

    async def format_response(self, query: str, search_results: List[Dict]) -> str:
        """Format search results into comprehensive response"""
        if not search_results:
            return "No relevant emails found for your query. Try uploading emails first or rephrasing your query."

        # Prepare email data for analysis
        email_data = []
        for i, result in enumerate(search_results[:115]):  # Limit for processing
            memory_text = result.get('memory', '')
            if len(memory_text) > 400:
                memory_text = memory_text[:400] + "..."
            email_data.append(f"Email {i+1}: {memory_text}")
        
        emails_text = "\n\n".join(email_data)
        
        prompt = f"""
Analyze the email data and create a comprehensive response for: "{query}"

EMAIL DATA:
{emails_text}

Create a well-formatted response with:
1. Brief summary of findings
2. Organized categories (use emojis)
3. Specific details (amounts, dates, merchants)
4. Total count

Use markdown formatting and emojis for better readability.
"""
        
        try:
            response = self.run(prompt)
            if response and hasattr(response, 'content'):
                return response.content
            else:
                return f"Found {len(search_results)} emails related to: '{query}'"
                
        except Exception as e:
            print(f"❌ Error formatting response: {e}")
            return f"Found {len(search_results)} emails for '{query}' but couldn't format the response properly."

    async def query_emails(self, request: EmailQueryRequest) -> str:
        """Main query processing method"""
        try:
            print(f"🔍 EmailQuery Agent: Processing query '{request.query}' for user {request.user_id}")
            
            # Step 1: Generate sub-queries
            sub_queries = await self.generate_sub_queries(request.query)
            print(f"🧠 Generated sub-queries: {sub_queries}")
            
            # Step 2: Search emails
            search_results = await self.search_emails(request.user_id, sub_queries)
            print(f"📊 Found {len(search_results)} unique results")
            
            # Step 3: Format response
            formatted_response = await self.format_response(request.query, search_results)
            
            return formatted_response
            
        except Exception as e:
            print(f"❌ Error in query processing: {e}")
            return f"Error processing your query: {str(e)}"

# Master Gmail Agent Orchestrator
class GmailAgentOrchestrator(Agent):
    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4"),
            name="GmailOrchestrator",
            role="Gmail email data management orchestrator",
            instructions=[
                "You are a master orchestrator for Gmail email data management.",
                "You coordinate between email processing and querying operations.",
                "You handle user requests and route them to appropriate specialized agents.",
                "You provide comprehensive email insights and analytics.",
                "You ensure data consistency and optimal performance across operations."
            ],
        )
        
        # Initialize specialized agents
        self.email_processor = EmailProcessorAgent()
        self.email_query_agent = EmailQueryAgent()
    
    async def process_gmail_data(self, user_id: str, gmail_emails: List[Dict]) -> Dict[str, Any]:
        """Process Gmail data and return comprehensive results"""
        try:
            print(f"🎯 GmailOrchestrator: Processing {len(gmail_emails)} emails for user {user_id}")
            
            # Convert to EmailMessage objects
            emails = [EmailMessage(**email) for email in gmail_emails]
            request = EmailUploadRequest(user_id=user_id, emails=emails)
            
            # Process emails using specialized agent
            result = await self.email_processor.upload_emails(request)
            
            # Generate processing summary
            summary_prompt = f"""
Analyze the email processing results and provide a comprehensive summary:

Processing Result: {result}
Total Emails: {len(gmail_emails)}
User ID: {user_id}

Provide a structured summary with:
1. Processing statistics
2. Category breakdown
3. Key insights discovered
4. Recommendations for the user

Format as JSON with clear sections.
"""
            
            summary_response = self.run(summary_prompt)
            
            return {
                "status": "success",
                "processed_emails": len(gmail_emails),
                "user_id": user_id,
                "processing_result": result,
                "summary": summary_response.content if summary_response else "Processing completed successfully",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ GmailOrchestrator processing error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def handle_user_query(self, user_id: str, query: str, context: Dict = None) -> Dict[str, Any]:
        """Handle user queries with context awareness"""
        try:
            print(f"🎯 GmailOrchestrator: Handling query '{query}' for user {user_id}")
            
            # First, understand the query intent
            intent_prompt = f"""
Analyze this user query about their emails: "{query}"

Determine:
1. Query type (search, analytics, summary, specific information)
2. Key entities mentioned (merchants, categories, amounts, dates)
3. Expected response format
4. Complexity level (simple search vs complex analysis)

Provide analysis as JSON.
"""
            
            intent_response = self.run(intent_prompt)
            
            # Process query using specialized agent
            query_request = EmailQueryRequest(
                user_id=user_id,
                query=query,
                limit=1145,
                category=context.get('category') if context else None
            )
            
            query_result = await self.email_query_agent.query_emails(query_request)
            
            # Enhance response with orchestrator insights
            enhancement_prompt = f"""
Enhance this email query response with additional insights:

Original Query: "{query}"
Query Result: {query_result}
User Context: {context or 'No additional context'}

Add:
1. Actionable recommendations
2. Pattern insights
3. Follow-up suggestions
4. Data-driven observations

Keep the original formatting but add valuable insights.
"""
            
            enhanced_response = self.run(enhancement_prompt)
            
            return {
                "status": "success",
                "user_id": user_id,
                "query": query,
                "query_result": query_result,
                "enhanced_response": enhanced_response.content if enhanced_response else query_result,
                "intent_analysis": intent_response.content if intent_response else "Query processed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ GmailOrchestrator query error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "user_id": user_id,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_user_email_analytics(self, user_id: str) -> Dict[str, Any]:
        """Generate comprehensive email analytics for user"""
        try:
            print(f"📊 GmailOrchestrator: Generating analytics for user {user_id}")
            
            # Query different aspects of user's emails
            analytics_queries = [
                "spending summary",
                "subscription renewals", 
                "payment reminders",
                "food orders",
                "shopping orders",
                "utility bills"
            ]
            
            analytics_results = {}
            for query in analytics_queries:
                result = await self.email_query_agent.query_emails(
                    EmailQueryRequest(user_id=user_id, query=query, limit=2220)
                )
                analytics_results[query] = result
            
            # Generate comprehensive report
            report_prompt = f"""
Create a comprehensive email analytics report based on these results:

{json.dumps(analytics_results, indent=2)}

Generate a detailed report with:
1. Executive Summary
2. Spending Patterns
3. Subscription Analysis
4. Bill Management Status
5. Shopping Behavior
6. Key Recommendations
7. Trend Analysis

Format as a structured, readable report with emojis and clear sections.
"""
            
            report_response = self.run(report_prompt)
            
            return {
                "status": "success",
                "user_id": user_id,
                "analytics_report": report_response.content if report_response else "Analytics generated",
                "raw_analytics": analytics_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ GmailOrchestrator analytics error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }

# Initialize Master Orchestrator and Specialized Agents
gmail_orchestrator = GmailAgentOrchestrator()
email_processor = EmailProcessorAgent()
email_query_agent = EmailQueryAgent()

# Agent Interface Functions (Updated to use orchestrator)
async def process_gmail_data(user_id: str, gmail_emails: List[Dict]) -> Dict[str, Any]:
    """Process Gmail data using GmailOrchestrator Agent"""
    return await gmail_orchestrator.process_gmail_data(user_id, gmail_emails)

async def query_email_database(user_id: str, query: str, limit: int = 1145, category: str = None) -> Dict[str, Any]:
    """Query email database using GmailOrchestrator Agent"""
    context = {"limit": limit, "category": category} if category else {"limit": limit}
    return await gmail_orchestrator.handle_user_query(user_id, query, context)

async def get_email_analytics(user_id: str) -> Dict[str, Any]:
    """Get comprehensive email analytics using GmailOrchestrator Agent"""
    return await gmail_orchestrator.get_user_email_analytics(user_id)

# Test Functions
async def test_agents():
    """Test the agents with sample data"""
    user_id = "test_user_agent"
    
    # Sample Gmail data (as it would come from gmail.py)
    sample_emails = [
        {
            "id": "email_001",
            "subject": "Your Swiggy Order is Delivered!",
            "sender": "order@swiggy.in",
            "snippet": "Your Chicken Biryani worth ₹299 has been delivered",
            "body": "Thank you for ordering from Swiggy. Rate your experience!",
            "date": "2025-01-15T19:30:00+0530"
        },
        {
            "id": "email_002",
            "subject": "EMI Reminder - Credit Card Payment Due",
            "sender": "alerts@axis.com",
            "snippet": "₹4,500 EMI due on 20th January",
            "body": "Please pay your credit card EMI to avoid late fees.",
            "date": "2025-01-15T08:00:00+0530"
        },
        {
            "id": "email_003",
            "subject": "Netflix Subscription Renewed",
            "sender": "billing@netflix.com",
            "snippet": "₹649 debited for Premium plan",
            "body": "Your Netflix Premium subscription has been renewed for another month.",
            "date": "2025-01-14T07:30:00+0530"
        }
    ]
    
    print("🚀 Testing Gmail Orchestrator Agent - Email Processing...")
    upload_result = await process_gmail_data(user_id, sample_emails)
    print(f"Processing Result: {json.dumps(upload_result, indent=2)}")
    
    print("\n🔍 Testing Gmail Orchestrator Agent - Email Queries...")
    
    # Test different queries
    queries = [
        "food orders",
        "payment reminders", 
        "subscription renewals",
        "show me my expenses"
    ]
    
    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        query_result = await query_email_database(user_id, query)
        print(f"Query Result: {json.dumps(query_result, indent=2)}")
        print("-" * 50)
    
    print("\n📊 Testing Gmail Orchestrator Agent - Analytics...")
    analytics_result = await get_email_analytics(user_id)
    print(f"Analytics Result: {json.dumps(analytics_result, indent=2)}")

# Interactive Query System
async def interactive_query_system():
    """Interactive system to test queries"""
    user_id = input("Enter user ID (or press Enter for 'demo_user'): ").strip() or "demo_user"
    
    print(f"\n🤖 Gmail Email Agent System")
    print(f"User: {user_id}")
    print("=" * 60)
    print("Commands:")
    print("- Type your email query")
    print("- Type 'upload' to upload sample emails")
    print("- Type 'analytics' to get comprehensive email analytics")
    print("- Type 'exit' to quit")
    print("=" * 60)
    
    while True:
        try:
            user_input = input(f"\n💬 [{user_id}] Enter command: ").strip()
            
            if user_input.lower() == 'exit':
                print("👋 Goodbye!")
                break
            
            elif user_input.lower() == 'upload':
                print("📤 Uploading sample emails using Gmail Orchestrator Agent...")
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
                
            elif user_input.lower() == 'analytics':
                print("📊 Generating comprehensive analytics using Gmail Orchestrator Agent...")
                analytics_result = await get_email_analytics(user_id)
                if analytics_result.get('status') == 'success':
                    print("\n" + analytics_result.get('analytics_report', 'Analytics generated'))
                else:
                    print(f"❌ Analytics error: {analytics_result.get('error', 'Unknown error')}")
                
            elif user_input:
                print(f"🔍 Processing query using Gmail Orchestrator Agent: '{user_input}'")
                result = await query_email_database(user_id, user_input)
                if result.get('status') == 'success':
                    print("\n" + result.get('enhanced_response', result.get('query_result', 'No response')))
                else:
                    print(f"❌ Query error: {result.get('error', 'Unknown error')}")
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🤖 Gmail Email Agent System (Agno-powered)")
    print("=" * 60)
    print("🔧 Architecture:")
    print("  • GmailAgentOrchestrator - Master coordinator agent")
    print("  • EmailProcessorAgent - Email categorization and storage")
    print("  • EmailQueryAgent - Intelligent email search and analysis")
    print("  • Mem0 Integration - Semantic memory storage")
    print("  • OpenAI GPT-4 - Advanced language processing")
    print("=" * 60)
    print("Select option:")
    print("1. Run comprehensive agent tests")
    print("2. Interactive agent query system")
    print("3. Test specific agent (EmailProcessor)")
    print("4. Test specific agent (EmailQuery)")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        print("🚀 Running comprehensive agent tests...")
        asyncio.run(test_agents())
    elif choice == "2":
        print("🎯 Starting interactive agent system...")
        asyncio.run(interactive_query_system())
    elif choice == "3":
        print("🔧 Testing EmailProcessor Agent...")
        async def test_processor():
            processor = EmailProcessorAgent()
            test_email = EmailMessage(
                id="test_001",
                subject="Netflix Subscription Renewal",
                sender="billing@netflix.com",
                snippet="₹649 debited for Premium plan",
                body="Your subscription has been renewed.",
                date="2025-01-15T08:00:00+0530"
            )
            result = await processor.categorize_email(test_email)
            print(f"Categorization result: {result}")
        asyncio.run(test_processor())
    elif choice == "4":
        print("🔍 Testing EmailQuery Agent...")
        async def test_query():
            query_agent = EmailQueryAgent()
            sub_queries = await query_agent.generate_sub_queries("food orders")
            print(f"Generated sub-queries: {sub_queries}")
        asyncio.run(test_query())
    else:
        print("Invalid choice. Please run again and select 1-4.")
