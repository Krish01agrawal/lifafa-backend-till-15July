"""
Enhanced Query Processing System
===============================

This module implements an intelligent query processing system that:
1. Classifies queries (General, Financial, Mixed)
2. Breaks down queries into sub-questions
3. Retrieves structured data from MongoDB for financial queries
4. Combines MongoDB and Mem0 responses intelligently
5. Generates comprehensive, data-rich responses

Key Features:
- Smart query classification
- Sub-question generation (8-9 questions)
- MongoDB structured data retrieval
- Mem0 contextual data
- Intelligent response fusion
- Priority to actual transaction data
"""

import os
import json
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel
import openai
from .db import db_manager, emails_collection
from .mem0_agent_agno import query_mem0, search_emails_in_mem0
from .financial_agent import get_financial_summary, get_financial_transactions

# Configure comprehensive logging for enhanced query processor
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create specialized loggers for different components
query_logger = logging.getLogger(f"{__name__}.query")
classification_logger = logging.getLogger(f"{__name__}.classification")
mongodb_logger = logging.getLogger(f"{__name__}.mongodb")
mem0_logger = logging.getLogger(f"{__name__}.mem0")
response_logger = logging.getLogger(f"{__name__}.response")
performance_logger = logging.getLogger(f"{__name__}.performance")

logger.info("🚀 ENHANCED QUERY PROCESSOR - Enhanced logging initialized")
logger.info("📊 Component loggers: query, classification, mongodb, mem0, response, performance")

class QueryClassification(BaseModel):
    """Query classification result"""
    query_type: str  # "GENERAL", "FINANCIAL", "MIXED"
    confidence: float
    financial_keywords: List[str]
    sub_questions: List[str]
    mongodb_queries_needed: bool
    mem0_queries_needed: bool

class MongoDBQueryResult(BaseModel):
    """MongoDB query result"""
    query_type: str
    total_transactions: int
    total_amount: float
    transactions: List[Dict]
    summary: Optional[Dict]
    merchants: Dict[str, float]
    payment_methods: Dict[str, int]
    date_range: Dict[str, str]

class EnhancedQueryResponse(BaseModel):
    """Enhanced query response"""
    original_query: str
    classification: QueryClassification
    mongodb_data: Optional[MongoDBQueryResult]
    mem0_response: Optional[str]
    final_response: str
    data_sources_used: List[str]
    response_quality_score: float

class EnhancedQueryProcessor:
    """Enhanced query processor with intelligent data source selection"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.financial_keywords = [
            'transaction', 'payment', 'money', 'amount', 'spend', 'spent', 'cost', 'price',
            'bank', 'card', 'upi', 'transfer', 'bill', 'invoice', 'receipt', 'order',
            'merchant', 'vendor', 'purchase', 'buy', 'sale', 'refund', 'cashback',
            'balance', 'account', 'debit', 'credit', 'charge', 'fee', 'subscription'
        ]
    
    async def process_enhanced_query(self, user_id: str, query: str) -> EnhancedQueryResponse:
        """Main enhanced query processing function"""
        start_time = datetime.now()
        query_id = f"query_{user_id}_{int(time.time() * 1000)}"
        
        query_logger.info(f"🚀 [START] ENHANCED QUERY PROCESSING - Query ID: {query_id}")
        query_logger.info(f"👤 [USER] {user_id}")
        query_logger.info(f"❓ [QUERY] '{query}'")
        query_logger.info(f"📏 [LENGTH] {len(query)} characters")
        
        try:
            # Step 1: Classify Query
            classification_start = datetime.now()
            query_logger.info(f"🔍 [STEP 1] Starting query classification - Query ID: {query_id}")
            
            classification = await self._classify_query(query, query_id)
            classification_time = (datetime.now() - classification_start).total_seconds()
            
            classification_logger.info(f"✅ [STEP 1] Classification complete - Query ID: {query_id}, Time: {classification_time:.2f}s")
            classification_logger.info(f"📊 [RESULT] Type: {classification.query_type}, Confidence: {classification.confidence:.2%}")
            classification_logger.info(f"🔍 [KEYWORDS] Financial keywords found: {classification.financial_keywords}")
            
            # Step 2: Generate Sub-questions
            subquestion_start = datetime.now()
            query_logger.info(f"❓ [STEP 2] Generating sub-questions - Query ID: {query_id}")
            
            sub_questions = await self._generate_sub_questions(query, classification, query_id)
            classification.sub_questions = sub_questions
            subquestion_time = (datetime.now() - subquestion_start).total_seconds()
            
            query_logger.info(f"✅ [STEP 2] Sub-questions generated - Query ID: {query_id}, Time: {subquestion_time:.2f}s")
            query_logger.info(f"📊 [RESULT] Generated {len(sub_questions)} sub-questions")
            for i, sq in enumerate(sub_questions[:3], 1):  # Log first 3
                query_logger.info(f"   {i}. {sq}")
            if len(sub_questions) > 3:
                query_logger.info(f"   ... and {len(sub_questions) - 3} more")
            
            # Step 3: Get MongoDB Data (if financial query)
            mongodb_data = None
            mongodb_time = 0
            if classification.mongodb_queries_needed:
                mongodb_start = datetime.now()
                mongodb_logger.info(f"💾 [STEP 3] Starting MongoDB financial data retrieval - Query ID: {query_id}")
                
                mongodb_data = await self._query_mongodb_financial_data(user_id, query, sub_questions, query_id)
                mongodb_time = (datetime.now() - mongodb_start).total_seconds()
                
                mongodb_logger.info(f"✅ [STEP 3] MongoDB data retrieved - Query ID: {query_id}, Time: {mongodb_time:.2f}s")
                if mongodb_data:
                    mongodb_logger.info(f"📊 [RESULT] Transactions: {mongodb_data.total_transactions}, Amount: ₹{mongodb_data.total_amount:,.2f}")
                    mongodb_logger.info(f"🏪 [MERCHANTS] Found {len(mongodb_data.merchants)} unique merchants")
                    mongodb_logger.info(f"💳 [PAYMENT METHODS] {len(mongodb_data.payment_methods)} payment methods")
            else:
                mongodb_logger.info(f"⏭️ [STEP 3] Skipping MongoDB query - Not needed for {classification.query_type} query")
            
            # Step 4: Get Mem0 Contextual Data
            mem0_response = None
            mem0_time = 0
            if classification.mem0_queries_needed:
                mem0_start = datetime.now()
                mem0_logger.info(f"🧠 [STEP 4] Starting Mem0 contextual data retrieval - Query ID: {query_id}")
                
                mem0_response = await self._query_mem0_contextual_data(user_id, query, sub_questions, query_id)
                mem0_time = (datetime.now() - mem0_start).total_seconds()
                
                mem0_logger.info(f"✅ [STEP 4] Mem0 data retrieved - Query ID: {query_id}, Time: {mem0_time:.2f}s")
                mem0_logger.info(f"📊 [RESULT] Response length: {len(mem0_response) if mem0_response else 0} characters")
            else:
                mem0_logger.info(f"⏭️ [STEP 4] Skipping Mem0 query - Not needed")
            
            # Step 5: Generate Enhanced Response
            response_start = datetime.now()
            response_logger.info(f"🎯 [STEP 5] Generating enhanced response - Query ID: {query_id}")
            
            final_response = await self._generate_enhanced_response(
                query, classification, mongodb_data, mem0_response, query_id
            )
            response_time = (datetime.now() - response_start).total_seconds()
            
            response_logger.info(f"✅ [STEP 5] Enhanced response generated - Query ID: {query_id}, Time: {response_time:.2f}s")
            response_logger.info(f"📊 [RESULT] Response length: {len(final_response)} characters")
            
            # Step 6: Calculate Quality Score
            quality_start = datetime.now()
            quality_score = self._calculate_response_quality(final_response, mongodb_data, mem0_response)
            quality_time = (datetime.now() - quality_start).total_seconds()
            
            response_logger.info(f"🎯 [STEP 6] Quality score calculated - Query ID: {query_id}, Score: {quality_score:.2f}")
            
            # Final Performance Summary
            total_time = (datetime.now() - start_time).total_seconds()
            data_sources = self._get_data_sources_used(mongodb_data, mem0_response)
            
            performance_logger.info(f"🎯 [PERFORMANCE] ENHANCED QUERY PROCESSING - Query ID: {query_id}")
            performance_logger.info(f"   ⏱️ Total time: {total_time:.2f}s")
            performance_logger.info(f"   🔍 Classification time: {classification_time:.2f}s ({classification_time/total_time*100:.1f}%)")
            performance_logger.info(f"   ❓ Sub-questions time: {subquestion_time:.2f}s ({subquestion_time/total_time*100:.1f}%)")
            performance_logger.info(f"   💾 MongoDB time: {mongodb_time:.2f}s ({mongodb_time/total_time*100:.1f}%)")
            performance_logger.info(f"   🧠 Mem0 time: {mem0_time:.2f}s ({mem0_time/total_time*100:.1f}%)")
            performance_logger.info(f"   🎯 Response time: {response_time:.2f}s ({response_time/total_time*100:.1f}%)")
            performance_logger.info(f"   📊 Quality score: {quality_score:.2f}")
            performance_logger.info(f"   🔗 Data sources: {', '.join(data_sources)}")
            
            query_logger.info(f"🎉 [COMPLETE] ENHANCED QUERY PROCESSING SUCCESS - Query ID: {query_id}, Time: {total_time:.2f}s")
            
            return EnhancedQueryResponse(
                original_query=query,
                classification=classification,
                mongodb_data=mongodb_data,
                mem0_response=mem0_response,
                final_response=final_response,
                data_sources_used=data_sources,
                response_quality_score=quality_score
            )
            
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            query_logger.error(f"❌ [CRITICAL] ENHANCED QUERY PROCESSING FAILED - Query ID: {query_id}, Time: {total_time:.2f}s")
            query_logger.error(f"🔍 [DEBUG] Exception: {str(e)}", exc_info=True)
            # Fallback to basic response
            return await self._generate_fallback_response(user_id, query, query_id)
    
    async def _classify_query(self, query: str, query_id: str = None) -> QueryClassification:
        """Classify query into GENERAL, FINANCIAL, or MIXED"""
        try:
            # Check for financial keywords
            query_lower = query.lower()
            financial_keywords_found = [kw for kw in self.financial_keywords if kw in query_lower]
            
            # LLM-based classification
            classification_prompt = f"""
            Analyze this user query and classify it accurately:
            
            Query: "{query}"
            
            Classification Rules:
            - FINANCIAL: Any query about money, transactions, payments, spending, costs, banks, cards, merchants, purchases, financial data
            - GENERAL: Queries about non-financial topics (travel, job applications, general emails, social media, etc.)
            - MIXED: Queries that combine financial and non-financial elements
            
            Financial Keywords Found: {financial_keywords_found}
            
            Respond in JSON format:
            {{
                "query_type": "FINANCIAL",
                "confidence": 0.95,
                "reasoning": "Why this classification was chosen",
                "mongodb_queries_needed": true,
                "mem0_queries_needed": true
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": classification_prompt}],
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return QueryClassification(
                query_type=result.get("query_type", "GENERAL"),
                confidence=result.get("confidence", 0.5),
                financial_keywords=financial_keywords_found,
                sub_questions=[],  # Will be filled later
                mongodb_queries_needed=result.get("mongodb_queries_needed", False),
                mem0_queries_needed=result.get("mem0_queries_needed", True)
            )
            
        except Exception as e:
            logger.error(f"❌ Query classification error: {e}")
            # Fallback classification
            has_financial_keywords = len(financial_keywords_found) > 0
            return QueryClassification(
                query_type="FINANCIAL" if has_financial_keywords else "GENERAL",
                confidence=0.7 if has_financial_keywords else 0.6,
                financial_keywords=financial_keywords_found,
                sub_questions=[],
                mongodb_queries_needed=has_financial_keywords,
                mem0_queries_needed=True
            )
    
    async def _generate_sub_questions(self, query: str, classification: QueryClassification, query_id: str = None) -> List[str]:
        """Generate 8-9 sub-questions to comprehensively answer the main query"""
        try:
            sub_question_prompt = f"""
            Break down this user query into 8-9 specific sub-questions.
            
            Original Query: "{query}"
            Query Type: {classification.query_type}
            
            Generate sub-questions that cover transaction details, amounts, merchants, dates, patterns, and insights.
            
            Respond with a JSON array of exactly 8-9 sub-questions.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": sub_question_prompt}],
                temperature=0.2
            )
            
            sub_questions = json.loads(response.choices[0].message.content)
            return sub_questions[:9]  # Ensure max 9 questions
            
        except Exception as e:
            logger.error(f"❌ Sub-question generation error: {e}")
            # Fallback sub-questions
            return [
                "What is the total transaction amount?",
                "Which merchants are involved?", 
                "What time period is covered?",
                "What payment methods were used?",
                "What are the spending patterns?",
                "How many transactions occurred?",
                "What is the average transaction value?",
                "Are there any notable insights?"
            ]
    
    async def _query_mongodb_financial_data(self, user_id: str, query: str, sub_questions: List[str], query_id: str = None) -> MongoDBQueryResult:
        """Query MongoDB for structured financial data"""
        try:
            logger.info(f"💾 Querying MongoDB financial data for user {user_id}")
            
            # Get financial transactions
            transactions = await get_financial_transactions(user_id, limit=5000)
            
            # Get financial summary
            summary = await get_financial_summary(user_id)
            
            if not transactions:
                logger.warning(f"⚠️ No financial transactions found in MongoDB for user {user_id}")
                return MongoDBQueryResult(
                    query_type="FINANCIAL",
                    total_transactions=0,
                    total_amount=0.0,
                    transactions=[],
                    summary=summary,
                    merchants={},
                    payment_methods={},
                    date_range={}
                )
            
            # Calculate aggregations
            total_amount = sum(float(t.get('amount', 0)) for t in transactions if t.get('amount'))
            
            # Merchant breakdown
            merchants = {}
            for t in transactions:
                merchant = t.get('merchant', 'Unknown')
                merchants[merchant] = merchants.get(merchant, 0) + float(t.get('amount', 0))
            
            # Payment method breakdown  
            payment_methods = {}
            for t in transactions:
                method = t.get('payment_method', 'unknown')
                payment_methods[method] = payment_methods.get(method, 0) + 1
            
            # Date range
            dates = [t.get('date') for t in transactions if t.get('date')]
            date_range = {}
            if dates:
                date_range = {
                    'earliest': min(dates),
                    'latest': max(dates)
                }
            
            logger.info(f"✅ MongoDB query complete: {len(transactions)} transactions")
            
            return MongoDBQueryResult(
                query_type="FINANCIAL",
                total_transactions=len(transactions),
                total_amount=total_amount,
                transactions=transactions[:50],  # Limit for performance
                summary=summary,
                merchants=dict(sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:10]),
                payment_methods=payment_methods,
                date_range=date_range
            )
            
        except Exception as e:
            logger.error(f"❌ MongoDB query error: {e}")
            return MongoDBQueryResult(
                query_type="FINANCIAL",
                total_transactions=0,
                total_amount=0.0,
                transactions=[],
                summary=None,
                merchants={},
                payment_methods={},
                date_range={}
            )
    
    async def _query_mem0_contextual_data(self, user_id: str, query: str, sub_questions: List[str], query_id: str = None) -> Optional[str]:
        """Query Mem0 for contextual and conversational data"""
        try:
            logger.info(f"🧠 Querying Mem0 for contextual data")
            
            # Create a refined query for Mem0
            mem0_query = f"Context for: {query}. Additional questions: {'; '.join(sub_questions[:3])}"
            
            # Get Mem0 response
            mem0_response = await query_mem0(user_id, mem0_query)
            
            return mem0_response
            
        except Exception as e:
            logger.error(f"❌ Mem0 query error: {e}")
            return None
    
    async def _generate_enhanced_response(
        self, 
        query: str, 
        classification: QueryClassification,
        mongodb_data: Optional[MongoDBQueryResult],
        mem0_response: Optional[str],
        query_id: str = None
    ) -> str:
        """Generate enhanced response combining MongoDB and Mem0 data"""
        try:
            # Prepare data summary
            data_summary = self._prepare_data_summary(mongodb_data, mem0_response)
            
            response_prompt = f"""
            Generate a comprehensive, data-rich response to the user's query using the available data.
            
            ORIGINAL QUERY: "{query}"
            QUERY TYPE: {classification.query_type}
            
            STRUCTURED DATA FROM MONGODB:
            {json.dumps(data_summary, indent=2) if data_summary else "No structured data available"}
            
            RESPONSE REQUIREMENTS:
            1. PRIORITIZE STRUCTURED DATA: Use actual amounts, dates, merchants from MongoDB
            2. INCLUDE SPECIFIC NUMBERS: Always show exact amounts, transaction counts, percentages
            3. PROVIDE DETAILED BREAKDOWN: Merchants, payment methods, categories, time periods
            4. BE COMPREHENSIVE: Answer all aspects of the query
            5. USE CLEAR FORMATTING: Headers, bullet points, tables where appropriate
            
            Generate a response that provides actual value with real data and insights.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": response_prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Enhanced response generation error: {e}")
            return self._generate_basic_response(query, mongodb_data, mem0_response)
    
    def _prepare_data_summary(self, mongodb_data: Optional[MongoDBQueryResult], mem0_response: Optional[str]) -> Dict:
        """Prepare structured data summary for LLM processing"""
        summary = {}
        
        if mongodb_data:
            summary["mongodb_financial_data"] = {
                "total_transactions": mongodb_data.total_transactions,
                "total_amount": mongodb_data.total_amount,
                "top_merchants": mongodb_data.merchants,
                "payment_methods": mongodb_data.payment_methods,
                "date_range": mongodb_data.date_range,
                "sample_transactions": mongodb_data.transactions[:5] if mongodb_data.transactions else [],
                "summary_stats": mongodb_data.summary
            }
        
        return summary
    
    def _generate_basic_response(self, query: str, mongodb_data: Optional[MongoDBQueryResult], mem0_response: Optional[str]) -> str:
        """Generate basic response as fallback"""
        if mongodb_data and mongodb_data.total_transactions > 0:
            return f"""
# 📊 Financial Analysis: {query}

## 💰 Transaction Summary
- **Total Transactions**: {mongodb_data.total_transactions:,}
- **Total Amount**: ₹{mongodb_data.total_amount:,.2f}
- **Average Transaction**: ₹{mongodb_data.total_amount/mongodb_data.total_transactions:,.2f}

## 🏪 Top Merchants
{chr(10).join([f"- **{merchant}**: ₹{amount:,.2f}" for merchant, amount in list(mongodb_data.merchants.items())[:5]])}

## 💳 Payment Methods
{chr(10).join([f"- **{method}**: {count} transactions" for method, count in mongodb_data.payment_methods.items()])}

*This analysis is based on structured financial data from your transaction history.*
"""
        else:
            return f"""
# 📧 Query Response: {query}

⚠️ **Limited Financial Data Available**

I found minimal transaction data in your records. This could mean:
- Financial transactions haven't been fully processed yet
- The data might be stored in a different format

Please try running financial processing first or ask about a different topic.
"""
    
    def _calculate_response_quality(self, response: str, mongodb_data: Optional[MongoDBQueryResult], mem0_response: Optional[str]) -> float:
        """Calculate response quality score"""
        score = 0.0
        
        # Length check
        if len(response) > 200:
            score += 0.2
        
        # Data richness
        if mongodb_data and mongodb_data.total_transactions > 0:
            score += 0.4
        
        # Specific numbers included
        if any(char in response for char in ['₹', '₨', '$']):
            score += 0.2
        
        # Structured formatting
        if '##' in response or '**' in response:
            score += 0.1
        
        # Actionable insights
        if any(word in response.lower() for word in ['insight', 'recommendation', 'pattern', 'trend']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_data_sources_used(self, mongodb_data: Optional[MongoDBQueryResult], mem0_response: Optional[str]) -> List[str]:
        """Get list of data sources used in response"""
        sources = []
        if mongodb_data and mongodb_data.total_transactions > 0:
            sources.append("MongoDB Financial Transactions")
        if mem0_response:
            sources.append("Mem0 AI Memory")
        return sources
    
    async def _generate_fallback_response(self, user_id: str, query: str, query_id: str = None) -> EnhancedQueryResponse:
        """Generate fallback response when main processing fails"""
        try:
            # Try basic Mem0 query
            mem0_response = await query_mem0(user_id, query)
            
            return EnhancedQueryResponse(
                original_query=query,
                classification=QueryClassification(
                    query_type="GENERAL",
                    confidence=0.5,
                    financial_keywords=[],
                    sub_questions=[],
                    mongodb_queries_needed=False,
                    mem0_queries_needed=True
                ),
                mongodb_data=None,
                mem0_response=mem0_response,
                final_response=mem0_response or "I apologize, but I'm having trouble processing your query right now.",
                data_sources_used=["Mem0 AI Memory"] if mem0_response else [],
                response_quality_score=0.3
            )
            
        except Exception as e:
            logger.error(f"❌ Fallback response generation failed: {e}")
            return EnhancedQueryResponse(
                original_query=query,
                classification=QueryClassification(
                    query_type="GENERAL",
                    confidence=0.1,
                    financial_keywords=[],
                    sub_questions=[],
                    mongodb_queries_needed=False,
                    mem0_queries_needed=False
                ),
                mongodb_data=None,
                mem0_response=None,
                final_response="I apologize, but I'm experiencing technical difficulties.",
                data_sources_used=[],
                response_quality_score=0.1
            )

# Global enhanced query processor instance
enhanced_query_processor = EnhancedQueryProcessor() 