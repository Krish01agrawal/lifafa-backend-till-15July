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
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")

queryAnalyzerAgent = Agent(
            model=OpenAIChat(id="gpt-3.5-turbo", api_key=OPENAI_API_KEY),
            tools=[ReasoningTools(add_instructions=True)],
            instructions="""
            You are a query analysis expert. Your job is to break down complex user queries into multiple focused sub-queries to reveal user intent and core concepts.

            For each query you receive:
            1. Identify the user's primary intent (what they're trying to accomplish)
            2. Extract core concepts and entities mentioned
            3. Break the query into 3-5 focused sub-queries that capture different aspects
            4. Classify the query type (informational, transactional, navigational, etc.)
            5. Assess complexity level (simple, moderate, complex)

            Always use reasoning to think through your analysis step by step.
            Focus on making sub-queries that are:
            - Specific and actionable
            - Covering different aspects of the original query
            - Useful for search or research purposes
            """,
            markdown=True,
            debug_mode=True,
)
queryAnalyzerAgent.print_response("tell me about credit card details")