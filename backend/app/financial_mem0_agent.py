"""
Enhanced Financial Transaction Agent using Agno Framework
=========================================================

This module extends the existing Agno Gmail Intelligence system with specialized
financial transaction processing, analysis, and insights generation.

Key Features:
- Specialized financial transaction agents
- Enhanced financial email filtering and categorization
- Comprehensive transaction data extraction
- Advanced financial analytics and reporting
- Integration with existing Mem0 and Agno infrastructure
"""

import os
import json
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import logging

# Existing system imports
from app.mem0_agent_agno import (
    EmailMessage, 
    aclient, 
    sync_client,
    MEM0_API_KEY,
    OPENAI_API_KEY
)
from app.financial_agent import TransactionData, FinancialSummary
from app.db import users_collection, emails_collection

# Agno Framework imports
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.tools.python import PythonTools
from textwrap import dedent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# SPECIALIZED FINANCIAL AGENTS
# ============================================================================

# Financial Transaction Detector Agent
financial_detector = Agent(
    name="FinancialTransactionDetector",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at detecting and classifying financial transaction emails",
    instructions=dedent("""
        You are a financial transaction detection expert.
        
        Analyze email content to determine if it's a financial transaction.
        Look for: currency symbols, transaction keywords, financial senders, amounts.
        
        Return JSON format:
        {
            "is_financial": true/false,
            "confidence": 0.0-1.0,
            "transaction_type": "payment|refund|purchase|subscription",
            "reasoning": "Brief explanation"
        }
    """),
    tools=[PythonTools()],
    show_tool_calls=False,
    markdown=False
)

# Financial Data Extractor Agent
financial_extractor = Agent(
    name="FinancialDataExtractor",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at extracting structured financial data from emails",
    instructions=dedent("""
        Extract structured financial data from transaction emails.
        
        Return JSON:
        {
            "amount": 1500.00,
            "currency": "INR",
            "date": "2024-12-15",
            "merchant": "Swiggy",
            "payment_method": "upi",
            "transaction_id": "TXN123456789",
            "description": "Food delivery order"
        }
    """),
    tools=[PythonTools()],
    show_tool_calls=False,
    markdown=False
)

# Financial Analytics Agent
financial_analyzer = Agent(
    name="FinancialAnalyzer",
    model=OpenAIChat(id="gpt-4o"),
    description="Expert at generating comprehensive financial insights and analytics",
    instructions=dedent("""
        You are a financial analytics expert specializing in personal finance insights.
        
        Your expertise:
        1. Analyze spending patterns and trends
        2. Generate actionable financial insights
        3. Identify spending categories and behaviors
        4. Provide personalized recommendations
        5. Create comprehensive financial reports
        
        Analysis capabilities:
        - Spending trend analysis (monthly, categorical)
        - Merchant preference analysis
        - Payment method usage patterns
        - Budget optimization recommendations
        - Anomaly detection in spending
        - Financial health assessment
        
        Report structure:
        - Executive summary with key metrics
        - Detailed spending breakdown
        - Trend analysis with visualizable data
        - Actionable recommendations
        - Risk assessment and alerts
        
        Always provide data-driven insights with specific numbers and percentages.
    """),
    tools=[PythonTools()],
    show_tool_calls=False,
    markdown=True
)

# Financial Intelligence Team (commented out for now due to Agno compatibility)
# financial_team = Team(
#     name="FinancialIntelligenceTeam", 
#     members=[financial_detector, financial_extractor, financial_analyzer],
#     instructions=dedent("""
#         You are an elite financial intelligence team specializing in Gmail transaction analysis.
#         
#         Team workflow:
#         1. FinancialTransactionDetector: Identify and classify financial emails
#         2. FinancialDataExtractor: Extract structured transaction data
#         3. FinancialAnalyzer: Generate comprehensive insights and reports
#         
#         Collaboration principles:
#         - Share findings between agents for enhanced accuracy
#         - Validate extracted data across team members
#         - Provide comprehensive, actionable financial intelligence
#         - Maintain data consistency and quality standards
#         
#         Output comprehensive financial reports with:
#         - Transaction summaries and trends
#         - Spending insights and patterns
#         - Actionable recommendations
#         - Visualization-ready data
#     """),
#     show_tool_calls=False
# )

# ============================================================================
# ENHANCED FINANCIAL PROCESSING FUNCTIONS
# ============================================================================

async def detect_financial_transactions_with_ai(emails: List[EmailMessage]) -> List[Dict[str, Any]]:
    """Use AI agents to detect financial transactions"""
    try:
        logger.info(f"Detecting financial transactions from {len(emails)} emails")
        
        financial_emails = []
        
        for email in emails:
            try:
                email_content = f"Subject: {email.subject}\nSender: {email.sender}\nBody: {email.body[:200]}"
                
                detection_result = financial_detector.run(
                    f"Analyze this email for financial indicators:\n{email_content}"
                )
                
                try:
                    detection_data = json.loads(detection_result.content)
                    if detection_data.get("is_financial", False) and detection_data.get("confidence", 0) >= 0.3:
                        financial_emails.append({
                            "email": email,
                            "detection": detection_data
                        })
                except json.JSONDecodeError:
                    # Fallback keyword detection
                    content_lower = f"{email.subject} {email.body}".lower()
                    if any(keyword in content_lower for keyword in ['payment', 'charged', '₹', 'rs.', 'upi']):
                        financial_emails.append({
                            "email": email,
                            "detection": {"is_financial": True, "confidence": 0.5}
                        })
                
            except Exception as e:
                logger.warning(f"Error processing email: {e}")
                continue
        
        logger.info(f"Detected {len(financial_emails)} financial emails")
        return financial_emails
        
    except Exception as e:
        logger.error(f"Error in financial detection: {e}")
        return []

async def extract_financial_data_with_ai(financial_emails: List[Dict[str, Any]], user_id: str) -> List[TransactionData]:
    """Extract structured financial data using AI agents"""
    try:
        logger.info(f"💰 Extracting financial data from {len(financial_emails)} emails using AI")
        
        transactions = []
        
        for item in financial_emails:
            try:
                email = item["email"]
                detection = item["detection"]
                
                # Prepare content for extraction
                email_content = f"""
                Subject: {email.subject}
                Sender: {email.sender}
                Date: {email.date}
                Body: {email.body}
                
                Detection Info: {json.dumps(detection)}
                """
                
                # Use financial extractor agent
                extraction_result = financial_extractor.run(
                    f"Extract structured financial data from this transaction email:\n{email_content}"
                )
                
                try:
                    # Parse extracted data
                    extracted_data = json.loads(extraction_result.content)
                    
                    # Create TransactionData object
                    transaction = TransactionData(
                        id=f"{user_id}_{email.id}_{datetime.now().timestamp()}",
                        email_id=email.id,
                        user_id=user_id,
                        date=datetime.fromisoformat(extracted_data.get("date", datetime.now().isoformat())),
                        amount=extracted_data.get("amount"),
                        currency=extracted_data.get("currency", "INR"),
                        transaction_type=detection.get("transaction_type", "payment"),
                        merchant=extracted_data.get("merchant"),
                        description=extracted_data.get("description", email.subject),
                        payment_method=extracted_data.get("payment_method", "unknown"),
                        transaction_id=extracted_data.get("transaction_id"),
                        sender=email.sender,
                        subject=email.subject,
                        snippet=email.snippet,
                        confidence_score=extracted_data.get("extraction_confidence", detection.get("confidence", 0.5))
                    )
                    
                    transactions.append(transaction)
                    logger.info(f"💰 Extracted: {transaction.merchant} - {transaction.currency} {transaction.amount}")
                    
                except json.JSONDecodeError:
                    # Fallback extraction
                    transaction = _fallback_extraction(email, user_id, detection)
                    if transaction:
                        transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"Error extracting data from email: {e}")
                continue
        
        logger.info(f"✅ Extracted {len(transactions)} financial transactions")
        return transactions
        
    except Exception as e:
        logger.error(f"Error in financial data extraction: {e}")
        return []

def _fallback_extraction(email: EmailMessage, user_id: str, detection: Dict[str, Any]) -> Optional[TransactionData]:
    """Fallback extraction using regex patterns"""
    try:
        content = f"{email.subject} {email.snippet} {email.body}"
        
        # Extract amount using regex
        amount_patterns = [
            r'₹\s*([\d,]+\.?\d*)',
            r'Rs\.?\s*([\d,]+\.?\d*)',
            r'INR\s*([\d,]+\.?\d*)'
        ]
        
        amount = None
        for pattern in amount_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    amount = float(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # Extract merchant from sender
        merchant = None
        if '@' in email.sender:
            domain = email.sender.split('@')[1].split('.')[0]
            merchant = domain.title()
        
        # Create basic transaction
        return TransactionData(
            id=f"{user_id}_{email.id}_{datetime.now().timestamp()}",
            email_id=email.id,
            user_id=user_id,
            date=datetime.now(),
            amount=amount,
            currency="INR",
            transaction_type=detection.get("transaction_type", "payment"),
            merchant=merchant,
            description=email.subject,
            payment_method="unknown",
            sender=email.sender,
            subject=email.subject,
            snippet=email.snippet,
            confidence_score=0.3
        )
        
    except Exception as e:
        logger.error(f"Error in fallback extraction: {e}")
        return None

async def generate_financial_insights_with_ai(user_id: str, transactions: List[TransactionData]) -> str:
    """Generate comprehensive financial insights using AI"""
    try:
        logger.info(f"📊 Generating financial insights for {len(transactions)} transactions")
        
        # Prepare transaction data for analysis
        transaction_summary = {
            "total_transactions": len(transactions),
            "total_amount": sum(t.amount for t in transactions if t.amount),
            "currencies": list(set(t.currency for t in transactions if t.currency)),
            "merchants": list(set(t.merchant for t in transactions if t.merchant)),
            "payment_methods": list(set(t.payment_method for t in transactions if t.payment_method)),
            "date_range": {
                "start": min(t.date for t in transactions if t.date).isoformat() if transactions else None,
                "end": max(t.date for t in transactions if t.date).isoformat() if transactions else None
            }
        }
        
        # Sample transactions for detailed analysis
        sample_transactions = [
            {
                "date": t.date.isoformat() if t.date else None,
                "amount": t.amount,
                "currency": t.currency,
                "merchant": t.merchant,
                "payment_method": t.payment_method,
                "transaction_type": t.transaction_type
            }
            for t in transactions[:20]  # First 20 transactions
        ]
        
        analysis_prompt = f"""
        Generate a comprehensive financial analysis report for this user's transaction data:
        
        SUMMARY:
        {json.dumps(transaction_summary, indent=2)}
        
        SAMPLE TRANSACTIONS:
        {json.dumps(sample_transactions, indent=2)}
        
        Please provide:
        1. Executive summary with key financial metrics
        2. Spending pattern analysis
        3. Category and merchant breakdown
        4. Payment method preferences
        5. Monthly/weekly trends if applicable
        6. Financial health assessment
        7. Actionable recommendations for optimization
        8. Spending alerts or anomalies
        
        Format as a comprehensive markdown report suitable for user presentation.
        """
        
        # Use financial analyzer agent
        analysis_result = financial_analyzer.run(analysis_prompt)
        
        insights_report = analysis_result.content if hasattr(analysis_result, 'content') else str(analysis_result)
        
        logger.info("✅ Financial insights generated successfully")
        return insights_report
        
    except Exception as e:
        logger.error(f"Error generating financial insights: {e}")
        return f"Unable to generate detailed insights. Found {len(transactions)} transactions totaling {sum(t.amount for t in transactions if t.amount):.2f} in financial activity."

# ============================================================================
# ENHANCED MEM0 INTEGRATION FOR FINANCIAL DATA
# ============================================================================

async def upload_financial_transactions_to_mem0(user_id: str, transactions: List[TransactionData]) -> str:
    """Upload financial transactions to Mem0 with enhanced metadata"""
    try:
        logger.info(f"📤 Uploading {len(transactions)} financial transactions to Mem0")
        
        processed_count = 0
        error_count = 0
        
        for transaction in transactions:
            try:
                # Prepare financial transaction content for Mem0
                content = f"""
                Financial Transaction:
                Date: {transaction.date.isoformat() if transaction.date else 'Unknown'}
                Amount: {transaction.currency} {transaction.amount}
                Merchant: {transaction.merchant}
                Type: {transaction.transaction_type}
                Payment Method: {transaction.payment_method}
                Description: {transaction.description}
                Transaction ID: {transaction.transaction_id or 'N/A'}
                """
                
                messages = [{
                    "role": "user",
                    "content": content
                }]
                
                # Enhanced metadata for financial transactions
                metadata = {
                    "type": "financial_transaction",
                    "transaction_id": transaction.id,
                    "email_id": transaction.email_id,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "merchant": transaction.merchant or "unknown",
                    "payment_method": transaction.payment_method or "unknown",
                    "transaction_type": transaction.transaction_type,
                    "date": transaction.date.isoformat() if transaction.date else None,
                    "confidence_score": transaction.confidence_score,
                    "source": "gmail_financial_agent",
                    "processing_version": "2.0_financial",
                    "categories": [
                        "financial",
                        "transaction",
                        transaction.transaction_type,
                        transaction.payment_method or "unknown"
                    ]
                }
                
                # Upload to Mem0
                aclient.add(
                    messages=messages,
                    user_id=user_id,
                    memory_id=transaction.id,
                    metadata=metadata
                )
                
                processed_count += 1
                
                if processed_count % 10 == 0:
                    logger.info(f"Uploaded {processed_count}/{len(transactions)} transactions")
                
            except Exception as e:
                error_count += 1
                logger.warning(f"Error uploading transaction {transaction.id}: {e}")
        
        result_message = f"Financial Transactions Upload: {processed_count}/{len(transactions)} successful"
        if error_count > 0:
            result_message += f" ({error_count} errors)"
        
        logger.info(f"✅ {result_message}")
        return result_message
        
    except Exception as e:
        logger.error(f"Error uploading financial transactions to Mem0: {e}")
        return f"Error uploading financial transactions: {str(e)}"

async def search_financial_transactions_in_mem0(user_id: str, query: str, limit: int = 100) -> List[Dict]:
    """Search financial transactions in Mem0 with enhanced filtering"""
    try:
        logger.info(f"🔍 Searching financial transactions: '{query}' for user {user_id}")
        
        # Enhanced financial search with metadata filters
        results = sync_client.search(
            query=query,
            user_id=user_id,
            limit=limit,
            filters={
                "metadata.type": "financial_transaction",
                "metadata.source": "gmail_financial_agent"
            },
            keyword_search=True,
            rerank=True
        )
        
        if results:
            logger.info(f"✅ Found {len(results)} financial transaction results")
            return results
        else:
            logger.info("No financial transaction results found")
            return []
        
    except Exception as e:
        logger.error(f"Error searching financial transactions: {e}")
        return []

# ============================================================================
# MAIN INTEGRATION FUNCTION
# ============================================================================

async def process_financial_intelligence_for_user(
    user_id: str, 
    emails: List[EmailMessage]
) -> Dict[str, Any]:
    """
    Main function to process financial intelligence using AI agents
    Integrates with existing Mem0 and Agno infrastructure
    """
    try:
        logger.info(f"🚀 Starting AI-powered financial intelligence processing for user {user_id}")
        
        # Step 1: Detect financial transactions using AI
        financial_emails = await detect_financial_transactions_with_ai(emails)
        
        if not financial_emails:
            return {
                "status": "success",
                "message": "No financial transactions detected",
                "transactions_found": 0,
                "user_id": user_id
            }
        
        # Step 2: Extract structured financial data using AI
        transactions = await extract_financial_data_with_ai(financial_emails, user_id)
        
        # Step 3: Upload to Mem0 with financial metadata
        mem0_result = await upload_financial_transactions_to_mem0(user_id, transactions)
        
        # Step 4: Generate comprehensive financial insights
        insights = await generate_financial_insights_with_ai(user_id, transactions)
        
        # Step 5: Calculate summary statistics
        total_amount = sum(t.amount for t in transactions if t.amount)
        unique_merchants = len(set(t.merchant for t in transactions if t.merchant))
        avg_transaction = total_amount / len(transactions) if transactions else 0
        
        result = {
            "status": "success",
            "message": "Financial intelligence processing completed successfully",
            "user_id": user_id,
            "transactions_found": len(transactions),
            "total_amount": total_amount,
            "average_transaction": avg_transaction,
            "unique_merchants": unique_merchants,
            "date_range": {
                "start": min(t.date for t in transactions if t.date).isoformat() if transactions else None,
                "end": max(t.date for t in transactions if t.date).isoformat() if transactions else None
            },
            "insights": insights,
            "mem0_upload": mem0_result,
            "processing_system": "AI Financial Intelligence Team",
            "version": "2.0_financial"
        }
        
        logger.info(f"✅ Financial intelligence processing completed: {len(transactions)} transactions, {total_amount:.2f} total amount")
        return result
        
    except Exception as e:
        logger.error(f"Error in financial intelligence processing: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "processing_system": "AI Financial Intelligence Team"
        }

logger.info("🔥 Enhanced Financial Mem0 Agent loaded successfully!")
logger.info("🤖 AI Agents: FinancialTransactionDetector, FinancialDataExtractor, FinancialAnalyzer")
logger.info("📊 Features: AI-powered detection, structured extraction, comprehensive insights") 