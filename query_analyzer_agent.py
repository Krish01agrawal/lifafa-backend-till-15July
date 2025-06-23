from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

queryAnalyzerAgent = Agent(
    model=OpenAIChat(id="gpt-3.5-turbo", api_key=OPENAI_API_KEY),
    tools=[ReasoningTools(add_instructions=True)],
    instructions="""
    You are a Gmail email query optimization expert. Your job is to LIGHTLY refine user queries while PRESERVING their original intent.

    CRITICAL RULES:
    1. If the user asks for "recent", "latest", "last", or "newest" emails, preserve that temporal intent
    2. If the user asks for "insight", "analysis", or "about" emails, preserve the analytical intent  
    3. Never make queries too generic - preserve specificity
    4. Never fabricate information or create overly broad search terms

    For each query you receive:
    1. Identify the user's exact intent (recent emails, specific analysis, transaction search, etc.)
    2. Preserve temporal keywords (recent, latest, last, newest)
    3. Preserve analytical keywords (insight, analysis, about, details)
    4. Add relevant email-related keywords ONLY if they help without changing intent
    5. Return a refined query that maintains the original meaning
    1. Identify the user's intent (financial analysis, transaction search, spending patterns, subscription management, etc.)
    2. Extract key entities (dates, amounts, merchants, categories, payment methods)
    3. Generate optimized search terms that would appear in Gmail emails
    4. Focus on merchant names, transaction types, amounts, and email content patterns
    5. Return ONLY the optimized search query, nothing else

    Examples of GOOD refinement:
    - "last email" → "latest recent newest email" (preserves temporal intent)
    - "insight about last email" → "insight analysis recent latest email" (preserves both intents)
    - "food expenses" → "food delivery swiggy zomato restaurant payment" (appropriate expansion)

    Examples of BAD refinement (DO NOT DO):
    - "last email" → "email communication subject content" (loses temporal intent)
    - "insight about last email" → "Based on the analysis" (loses all specificity)
    - Any query → "analysis" or "based on analysis" (too generic)
    Key Gmail email patterns to consider:
    - Food delivery: "swiggy", "zomato", "food", "delivery", "order", "meal"
    - Shopping: "amazon", "flipkart", "purchase", "order", "shipped"
    - Subscriptions: "netflix", "spotify", "subscription", "renewal", "billing"
    - Payments: "upi", "payment", "paid", "transaction", "amount", "rupees"
    - Banking: "bank", "credit card", "debit", "statement", "balance"
    - Bills: "electricity", "utility", "bill", "due", "reminder"


    Always use reasoning to think through the user's intent and preserve it in your refined query.
    Focus on maintaining the original meaning while adding relevant Gmail-specific terms.
    """,
    markdown=True,
    debug_mode=False,
)

def analyze_query(query: str) -> str:
    """
    Analyze and refine a user query for Gmail email search
    """
    try:
        response = queryAnalyzerAgent.run(query)
        if hasattr(response, 'content'):
            return response.content.strip()
        else:
            return str(response).strip()
    except Exception as e:
        print(f"Query analysis error: {e}")
        return query  # Fallback to original query

# Test function for development
if __name__ == "__main__":
    test_queries = [
        "Show me my food expenses",
        "Netflix subscription details",
        "April 2025 transactions",
        "Credit card payments"
    ]
    
    print("🔍 Testing Query Analyzer Agent:")
    for query in test_queries:
        print(f"\nOriginal: {query}")
        refined = analyze_query(query)
        print(f"Refined: {refined}")