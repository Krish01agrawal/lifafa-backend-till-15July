"""
Statement Processor Service
==========================

Service for processing bank statements (PDF/CSV/Excel) and generating
AI-powered financial insights and transaction analysis.
"""

import os
import json
import asyncio
import logging
import pandas as pd
import pdfplumber
import camelot
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO, StringIO
import tempfile
import hashlib

from .config import (
    STATEMENT_PROCESSING_TIMEOUT, MAX_STATEMENT_FILE_SIZE_MB, SUPPORTED_STATEMENT_FORMATS,
    PDF_PROCESSING_ENGINE, COMMON_PDF_PASSWORDS, STATEMENT_ANALYSIS_LOOKBACK_MONTHS,
    MIN_TRANSACTIONS_FOR_ANALYSIS, TRANSACTION_CATEGORIES, STATEMENT_ANALYSIS_PROMPTS,
    FINANCIAL_ANALYSIS_MODEL, FINANCIAL_ANALYSIS_MAX_TOKENS, ENABLE_CATEGORY_AUTO_CLASSIFICATION,
    ENABLE_RECURRING_PAYMENT_DETECTION
)
from .models import (
    StatementUploadRequest, StatementData, StatementInsights, BankTransaction
)
from .db import db_manager
import openai

logger = logging.getLogger(__name__)

class StatementProcessor:
    """Service for processing bank statements and generating insights"""
    
    def __init__(self):
        self.db_manager = db_manager
        
    async def process_statement(self, file_content: bytes, file_type: str, request: StatementUploadRequest) -> Dict[str, Any]:
        """Process uploaded bank statement"""
        try:
            # Validate file size
            if len(file_content) > MAX_STATEMENT_FILE_SIZE_MB * 1024 * 1024:
                return {"success": False, "error": f"File size exceeds {MAX_STATEMENT_FILE_SIZE_MB}MB limit"}
            
            # Validate file type
            if file_type.lower() not in SUPPORTED_STATEMENT_FORMATS:
                return {"success": False, "error": f"Unsupported file format. Supported: {SUPPORTED_STATEMENT_FORMATS}"}
            
            # Extract transactions based on file type
            if file_type.lower() == "pdf":
                transactions = await self._extract_from_pdf(file_content, request)
            elif file_type.lower() in ["csv"]:
                transactions = await self._extract_from_csv(file_content, request)
            elif file_type.lower() in ["xlsx", "xls"]:
                transactions = await self._extract_from_excel(file_content, request)
            else:
                return {"success": False, "error": f"Unsupported file type: {file_type}"}
            
            if not transactions:
                return {"success": False, "error": "No transactions found in the statement"}
            
            # Create statement data
            statement_data = await self._create_statement_data(transactions, request)
            
            # Store statement
            await self._store_statement(statement_data)
            
            # Generate insights
            insights = await self._generate_statement_insights(statement_data)
            
            return {
                "success": True,
                "statement_id": statement_data.statement_id,
                "transactions_count": len(transactions),
                "insights": insights.dict() if insights else None
            }
            
        except Exception as e:
            logger.error(f"Error processing statement: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_from_pdf(self, file_content: bytes, request: StatementUploadRequest) -> List[BankTransaction]:
        """Extract transactions from PDF statement"""
        try:
            transactions = []
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                if PDF_PROCESSING_ENGINE == "pdfplumber":
                    transactions = await self._extract_with_pdfplumber(temp_file_path)
                elif PDF_PROCESSING_ENGINE == "camelot":
                    transactions = await self._extract_with_camelot(temp_file_path)
                else:
                    # Try both engines
                    transactions = await self._extract_with_pdfplumber(temp_file_path)
                    if not transactions:
                        transactions = await self._extract_with_camelot(temp_file_path)
            finally:
                os.unlink(temp_file_path)
            
            return await self._process_and_categorize_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            return []
    
    async def _extract_with_pdfplumber(self, file_path: str) -> List[Dict]:
        """Extract transactions using pdfplumber"""
        try:
            transactions = []
            
            with pdfplumber.open(file_path) as pdf:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        all_text += page_text + "\n"
                
                # Parse transactions from text
                transactions = self._parse_transactions_from_text(all_text)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error with pdfplumber: {e}")
            return []
    
    async def _extract_with_camelot(self, file_path: str) -> List[Dict]:
        """Extract transactions using camelot"""
        try:
            transactions = []
            
            # Extract tables from PDF
            tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')
            
            for table in tables:
                df = table.df
                if len(df) > 0:
                    # Convert table to transactions
                    table_transactions = self._parse_transactions_from_dataframe(df)
                    transactions.extend(table_transactions)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error with camelot: {e}")
            return []
    
    def _parse_transactions_from_text(self, text: str) -> List[Dict]:
        """Parse transactions from extracted text"""
        transactions = []
        
        # Common patterns for Indian bank statements
        patterns = [
            # Pattern 1: Date Amount Description
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+([+-]?[\d,]+\.?\d*)\s+(.+?)(?=\n|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|$)',
            # Pattern 2: Date Description Amount Balance
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.+?)\s+([+-]?[\d,]+\.?\d*)\s+([+-]?[\d,]+\.?\d*)',
            # Pattern 3: Description Date Amount
            r'(.+?)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+([+-]?[\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                try:
                    transaction = self._parse_transaction_match(match)
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    logger.warning(f"Error parsing transaction match: {e}")
                    continue
        
        return transactions
    
    def _parse_transaction_match(self, match: tuple) -> Optional[Dict]:
        """Parse individual transaction match"""
        try:
            if len(match) >= 3:
                # Extract date, amount, description
                date_str = match[0] if match[0] else ""
                amount_str = match[1] if len(match) > 1 else ""
                description = match[2] if len(match) > 2 else ""
                balance_str = match[3] if len(match) > 3 else ""
                
                # Clean and parse amount
                amount = self._parse_amount(amount_str)
                balance = self._parse_amount(balance_str) if balance_str else 0.0
                
                # Parse date
                date = self._parse_date(date_str)
                
                if date and amount != 0:
                    return {
                        "date": date,
                        "description": description.strip(),
                        "amount": amount,
                        "balance": balance,
                        "transaction_type": "CREDIT" if amount > 0 else "DEBIT"
                    }
        except Exception as e:
            logger.warning(f"Error parsing transaction: {e}")
        
        return None
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        try:
            # Remove commas and extra spaces
            clean_amount = re.sub(r'[,\s]', '', amount_str)
            
            # Handle negative amounts
            if clean_amount.startswith('-') or clean_amount.endswith('DR'):
                clean_amount = clean_amount.replace('-', '').replace('DR', '')
                return -float(clean_amount)
            elif clean_amount.endswith('CR'):
                clean_amount = clean_amount.replace('CR', '')
                return float(clean_amount)
            else:
                return float(clean_amount)
        except:
            return 0.0
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        try:
            # Common date formats
            formats = [
                "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                "%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        except:
            pass
        
        return None
    
    def _parse_transactions_from_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Parse transactions from DataFrame"""
        transactions = []
        
        try:
            # Common column patterns
            date_cols = [col for col in df.columns if any(word in str(col).lower() for word in ['date', 'dt', 'txn'])]
            desc_cols = [col for col in df.columns if any(word in str(col).lower() for word in ['description', 'narration', 'particular'])]
            amount_cols = [col for col in df.columns if any(word in str(col).lower() for word in ['amount', 'debit', 'credit'])]
            balance_cols = [col for col in df.columns if any(word in str(col).lower() for word in ['balance', 'bal'])]
            
            for _, row in df.iterrows():
                try:
                    transaction = {}
                    
                    # Extract date
                    if date_cols:
                        date_val = row[date_cols[0]]
                        transaction['date'] = self._parse_date(str(date_val))
                    
                    # Extract description
                    if desc_cols:
                        transaction['description'] = str(row[desc_cols[0]]).strip()
                    
                    # Extract amount
                    if amount_cols:
                        amount_val = row[amount_cols[0]]
                        transaction['amount'] = self._parse_amount(str(amount_val))
                        transaction['transaction_type'] = "CREDIT" if transaction['amount'] > 0 else "DEBIT"
                    
                    # Extract balance
                    if balance_cols:
                        balance_val = row[balance_cols[0]]
                        transaction['balance'] = self._parse_amount(str(balance_val))
                    
                    if transaction.get('date') and transaction.get('amount', 0) != 0:
                        transactions.append(transaction)
                        
                except Exception as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing DataFrame: {e}")
        
        return transactions
    
    async def _extract_from_csv(self, file_content: bytes, request: StatementUploadRequest) -> List[BankTransaction]:
        """Extract transactions from CSV statement"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    csv_string = file_content.decode(encoding)
                    df = pd.read_csv(StringIO(csv_string))
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Error reading CSV with {encoding}: {e}")
                    continue
            
            if df is None:
                return []
            
            # Parse transactions from DataFrame
            transactions = self._parse_transactions_from_dataframe(df)
            return await self._process_and_categorize_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Error extracting from CSV: {e}")
            return []
    
    async def _extract_from_excel(self, file_content: bytes, request: StatementUploadRequest) -> List[BankTransaction]:
        """Extract transactions from Excel statement"""
        try:
            # Read Excel file
            df = pd.read_excel(BytesIO(file_content), sheet_name=0)
            
            # Parse transactions from DataFrame
            transactions = self._parse_transactions_from_dataframe(df)
            return await self._process_and_categorize_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Error extracting from Excel: {e}")
            return []
    
    async def _process_and_categorize_transactions(self, raw_transactions: List[Dict]) -> List[BankTransaction]:
        """Process raw transactions and categorize them"""
        processed_transactions = []
        
        for i, txn in enumerate(raw_transactions):
            try:
                # Generate transaction ID
                txn_id = hashlib.md5(f"{txn.get('date', '')}_{txn.get('description', '')}_{txn.get('amount', 0)}_{i}".encode()).hexdigest()
                
                # Categorize transaction
                category = self._categorize_transaction(txn.get('description', ''))
                
                # Create BankTransaction object
                transaction = BankTransaction(
                    transaction_id=txn_id,
                    date=txn.get('date', ''),
                    description=txn.get('description', ''),
                    debit_amount=abs(txn['amount']) if txn.get('amount', 0) < 0 else None,
                    credit_amount=txn['amount'] if txn.get('amount', 0) > 0 else None,
                    balance=txn.get('balance', 0.0),
                    transaction_type=txn.get('transaction_type', 'DEBIT'),
                    reference_number=txn.get('reference', ''),
                    category=category
                )
                
                processed_transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"Error processing transaction: {e}")
                continue
        
        return processed_transactions
    
    def _categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        if not ENABLE_CATEGORY_AUTO_CLASSIFICATION:
            return "Uncategorized"
        
        description_lower = description.lower()
        
        for category, keywords in TRANSACTION_CATEGORIES.items():
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    return category
        
        return "Uncategorized"
    
    async def _create_statement_data(self, transactions: List[BankTransaction], request: StatementUploadRequest) -> StatementData:
        """Create StatementData object from transactions"""
        statement_id = hashlib.md5(f"{request.jwt_token}_{datetime.now()}".encode()).hexdigest()
        
        # Calculate totals
        total_credits = sum(txn.credit_amount or 0 for txn in transactions)
        total_debits = sum(txn.debit_amount or 0 for txn in transactions)
        
        # Get opening and closing balance
        opening_balance = transactions[0].balance if transactions else 0.0
        closing_balance = transactions[-1].balance if transactions else 0.0
        
        return StatementData(
            statement_id=statement_id,
            user_id=request.jwt_token,
            bank_name=request.bank_name or "Unknown Bank",
            account_number=request.account_number or "Unknown Account",
            account_type=request.statement_type or "Unknown",
            statement_period=request.statement_period,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
            transactions=transactions,
            uploaded_at=datetime.now().isoformat()
        )
    
    async def _store_statement(self, statement_data: StatementData) -> bool:
        """Store statement data in database"""
        try:
            statement_dict = statement_data.dict()
            statement_dict["_id"] = statement_data.statement_id
            statement_dict["created_at"] = datetime.now().isoformat()
            
            await self.statements_collection.insert_one(statement_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing statement: {e}")
            return False
    
    async def _generate_statement_insights(self, statement_data: StatementData) -> Optional[StatementInsights]:
        """Generate AI-powered insights from statement data"""
        try:
            if len(statement_data.transactions) < MIN_TRANSACTIONS_FOR_ANALYSIS:
                logger.warning(f"Insufficient transactions for analysis: {len(statement_data.transactions)}")
                return None
            
            # Generate different types of analysis
            spending_analysis = await self._analyze_spending_patterns(statement_data)
            income_analysis = await self._analyze_income_patterns(statement_data)
            financial_health = await self._analyze_financial_health(statement_data)
            
            # Detect recurring payments
            recurring_payments = await self._detect_recurring_payments(statement_data)
            
            # Detect unusual transactions
            unusual_transactions = await self._detect_unusual_transactions(statement_data)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(statement_data, spending_analysis, income_analysis)
            
            insights = StatementInsights(
                user_id=statement_data.user_id,
                statement_id=statement_data.statement_id,
                spending_analysis=spending_analysis,
                income_analysis=income_analysis,
                savings_analysis=self._calculate_savings_analysis(statement_data),
                cash_flow_pattern=self._analyze_cash_flow(statement_data),
                recurring_payments=recurring_payments,
                unusual_transactions=unusual_transactions,
                financial_habits=financial_health,
                recommendations=recommendations,
                risk_indicators=self._identify_risk_indicators(statement_data),
                generated_at=datetime.now().isoformat()
            )
            
            # Store insights
            await self._store_insights(insights)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating statement insights: {e}")
            return None
    
    async def _analyze_spending_patterns(self, statement_data: StatementData) -> Dict[str, Any]:
        """Analyze spending patterns using AI"""
        try:
            # Prepare spending data
            spending_data = {}
            category_spending = {}
            
            for txn in statement_data.transactions:
                if txn.debit_amount and txn.debit_amount > 0:
                    category = txn.category or "Uncategorized"
                    category_spending[category] = category_spending.get(category, 0) + txn.debit_amount
            
            spending_data = {
                "total_spending": statement_data.total_debits,
                "category_breakdown": category_spending,
                "average_transaction": statement_data.total_debits / len([t for t in statement_data.transactions if t.debit_amount]),
                "transaction_count": len([t for t in statement_data.transactions if t.debit_amount])
            }
            
            # Get AI analysis
            ai_analysis = await self._get_ai_analysis("spending_pattern", spending_data)
            
            return {
                "raw_data": spending_data,
                "ai_insights": ai_analysis,
                "top_categories": sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing spending patterns: {e}")
            return {}
    
    async def _analyze_income_patterns(self, statement_data: StatementData) -> Dict[str, Any]:
        """Analyze income patterns"""
        try:
            income_transactions = [t for t in statement_data.transactions if t.credit_amount and t.credit_amount > 0]
            
            # Group by description patterns to identify salary, etc.
            income_sources = {}
            for txn in income_transactions:
                description = txn.description.lower()
                if any(keyword in description for keyword in ["salary", "sal", "payroll"]):
                    income_sources["Salary"] = income_sources.get("Salary", 0) + txn.credit_amount
                elif any(keyword in description for keyword in ["interest", "int"]):
                    income_sources["Interest"] = income_sources.get("Interest", 0) + txn.credit_amount
                else:
                    income_sources["Other"] = income_sources.get("Other", 0) + txn.credit_amount
            
            income_data = {
                "total_income": statement_data.total_credits,
                "income_sources": income_sources,
                "average_income": statement_data.total_credits / max(1, len(income_transactions)),
                "income_frequency": len(income_transactions)
            }
            
            # Get AI analysis
            ai_analysis = await self._get_ai_analysis("income_stability", income_data)
            
            return {
                "raw_data": income_data,
                "ai_insights": ai_analysis,
                "income_sources": income_sources
            }
            
        except Exception as e:
            logger.error(f"Error analyzing income patterns: {e}")
            return {}
    
    async def _analyze_financial_health(self, statement_data: StatementData) -> Dict[str, Any]:
        """Analyze overall financial health"""
        try:
            # Calculate financial health metrics
            net_cash_flow = statement_data.total_credits - statement_data.total_debits
            savings_rate = (net_cash_flow / statement_data.total_credits) * 100 if statement_data.total_credits > 0 else 0
            
            health_data = {
                "net_cash_flow": net_cash_flow,
                "savings_rate": savings_rate,
                "total_income": statement_data.total_credits,
                "total_expenses": statement_data.total_debits,
                "opening_balance": statement_data.opening_balance,
                "closing_balance": statement_data.closing_balance
            }
            
            # Get AI analysis
            ai_analysis = await self._get_ai_analysis("financial_health", health_data)
            
            return {
                "raw_data": health_data,
                "ai_insights": ai_analysis,
                "health_score": self._calculate_health_score(health_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing financial health: {e}")
            return {}
    
    def _calculate_health_score(self, health_data: Dict) -> int:
        """Calculate financial health score (0-100)"""
        score = 50  # Base score
        
        # Savings rate contribution (0-30 points)
        savings_rate = health_data.get("savings_rate", 0)
        if savings_rate > 20:
            score += 30
        elif savings_rate > 10:
            score += 20
        elif savings_rate > 0:
            score += 10
        
        # Cash flow contribution (0-20 points)
        net_cash_flow = health_data.get("net_cash_flow", 0)
        if net_cash_flow > 0:
            score += 20
        elif net_cash_flow > -5000:
            score += 10
        
        return min(100, max(0, score))
    
    def _calculate_savings_analysis(self, statement_data: StatementData) -> Dict[str, Any]:
        """Calculate savings analysis"""
        net_savings = statement_data.total_credits - statement_data.total_debits
        savings_rate = (net_savings / statement_data.total_credits) * 100 if statement_data.total_credits > 0 else 0
        
        return {
            "net_savings": net_savings,
            "savings_rate": savings_rate,
            "monthly_average": net_savings,  # Assuming monthly statement
            "recommendation": "Good" if savings_rate > 20 else "Needs Improvement"
        }
    
    def _analyze_cash_flow(self, statement_data: StatementData) -> Dict[str, Any]:
        """Analyze cash flow patterns"""
        # Group transactions by date to show daily cash flow
        daily_flow = {}
        for txn in statement_data.transactions:
            date = txn.date
            if date not in daily_flow:
                daily_flow[date] = {"inflow": 0, "outflow": 0}
            
            if txn.credit_amount:
                daily_flow[date]["inflow"] += txn.credit_amount
            if txn.debit_amount:
                daily_flow[date]["outflow"] += txn.debit_amount
        
        return {
            "daily_flow": daily_flow,
            "average_daily_inflow": sum(d["inflow"] for d in daily_flow.values()) / len(daily_flow),
            "average_daily_outflow": sum(d["outflow"] for d in daily_flow.values()) / len(daily_flow)
        }
    
    async def _detect_recurring_payments(self, statement_data: StatementData) -> List[Dict[str, Any]]:
        """Detect recurring payments like EMIs, subscriptions"""
        if not ENABLE_RECURRING_PAYMENT_DETECTION:
            return []
        
        # Group similar transactions
        payment_groups = {}
        for txn in statement_data.transactions:
            if txn.debit_amount and txn.debit_amount > 0:
                # Normalize description
                normalized_desc = re.sub(r'\d+', '', txn.description.lower()).strip()
                if normalized_desc not in payment_groups:
                    payment_groups[normalized_desc] = []
                payment_groups[normalized_desc].append(txn)
        
        # Identify recurring payments
        recurring_payments = []
        for desc, transactions in payment_groups.items():
            if len(transactions) >= 2:  # At least 2 transactions to be considered recurring
                amounts = [t.debit_amount for t in transactions]
                avg_amount = sum(amounts) / len(amounts)
                
                # Check if amounts are similar (within 10% variation)
                if all(abs(amt - avg_amount) / avg_amount <= 0.1 for amt in amounts):
                    recurring_payments.append({
                        "description": desc,
                        "frequency": len(transactions),
                        "average_amount": avg_amount,
                        "category": transactions[0].category,
                        "is_emi": any(keyword in desc for keyword in ["emi", "loan", "installment"])
                    })
        
        return recurring_payments
    
    async def _detect_unusual_transactions(self, statement_data: StatementData) -> List[Dict[str, Any]]:
        """Detect unusual or outlier transactions"""
        unusual_transactions = []
        
        # Calculate average transaction amounts
        debit_amounts = [t.debit_amount for t in statement_data.transactions if t.debit_amount]
        credit_amounts = [t.credit_amount for t in statement_data.transactions if t.credit_amount]
        
        if debit_amounts:
            avg_debit = sum(debit_amounts) / len(debit_amounts)
            std_debit = (sum((x - avg_debit) ** 2 for x in debit_amounts) / len(debit_amounts)) ** 0.5
            
            # Find outliers (transactions > 2 standard deviations)
            for txn in statement_data.transactions:
                if txn.debit_amount and txn.debit_amount > avg_debit + 2 * std_debit:
                    unusual_transactions.append({
                        "transaction_id": txn.transaction_id,
                        "date": txn.date,
                        "description": txn.description,
                        "amount": txn.debit_amount,
                        "reason": "Unusually high debit amount"
                    })
        
        return unusual_transactions
    
    async def _generate_recommendations(self, statement_data: StatementData, spending_analysis: Dict, income_analysis: Dict) -> List[str]:
        """Generate personalized financial recommendations"""
        recommendations = []
        
        # Spending recommendations
        if spending_analysis.get("raw_data", {}).get("total_spending", 0) > income_analysis.get("raw_data", {}).get("total_income", 0):
            recommendations.append("Your expenses exceed your income. Consider reducing discretionary spending.")
        
        # Category-specific recommendations
        category_spending = spending_analysis.get("raw_data", {}).get("category_breakdown", {})
        total_spending = spending_analysis.get("raw_data", {}).get("total_spending", 1)
        
        for category, amount in category_spending.items():
            percentage = (amount / total_spending) * 100
            if category == "Food & Dining" and percentage > 30:
                recommendations.append("Consider reducing dining out expenses - they account for over 30% of your spending.")
            elif category == "Shopping" and percentage > 25:
                recommendations.append("Your shopping expenses are high. Try to budget for discretionary purchases.")
        
        # Savings recommendations
        savings_rate = (income_analysis.get("raw_data", {}).get("total_income", 0) - total_spending) / income_analysis.get("raw_data", {}).get("total_income", 1) * 100
        if savings_rate < 10:
            recommendations.append("Aim to save at least 10% of your income for financial security.")
        elif savings_rate > 30:
            recommendations.append("Great job on saving! Consider investing your surplus for better returns.")
        
        return recommendations
    
    def _identify_risk_indicators(self, statement_data: StatementData) -> List[str]:
        """Identify financial risk indicators"""
        risk_indicators = []
        
        # Low balance risk
        if statement_data.closing_balance < 5000:
            risk_indicators.append("Low account balance - maintain emergency fund")
        
        # Negative cash flow
        if statement_data.total_credits < statement_data.total_debits:
            risk_indicators.append("Negative cash flow - expenses exceed income")
        
        # High frequency of small transactions (possible financial stress)
        small_transactions = [t for t in statement_data.transactions if t.debit_amount and t.debit_amount < 100]
        if len(small_transactions) > len(statement_data.transactions) * 0.7:
            risk_indicators.append("High frequency of small transactions - possible cash flow management issues")
        
        return risk_indicators
    
    async def _get_ai_analysis(self, analysis_type: str, data: Dict) -> Dict:
        """Get AI analysis for specific aspect of statement"""
        try:
            prompt = STATEMENT_ANALYSIS_PROMPTS.get(analysis_type, "")
            if not prompt:
                return {}
            
            # Prepare the full prompt
            full_prompt = f"{prompt}\n\nStatement Data:\n{json.dumps(data, indent=2)}\n\nProvide analysis in JSON format with relevant insights."
            
            # Call OpenAI API
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await client.chat.completions.create(
                model=FINANCIAL_ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": "You are a financial advisor expert in statement analysis. Provide detailed, actionable insights."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=FINANCIAL_ANALYSIS_MAX_TOKENS,
                temperature=0.3
            )
            
            # Parse response
            analysis_text = response.choices[0].message.content
            try:
                return json.loads(analysis_text)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"analysis": analysis_text}
                
        except Exception as e:
            logger.error(f"Error getting AI analysis: {e}")
            return {}
    
    async def _store_insights(self, insights: StatementInsights) -> bool:
        """Store statement insights in database"""
        try:
            insights_dict = insights.dict()
            insights_dict["_id"] = f"{insights.user_id}_{insights.statement_id}"
            insights_dict["created_at"] = datetime.now().isoformat()
            
            await self.insights_collection.insert_one(insights_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing insights: {e}")
            return False
    
    async def get_user_statements(self, user_id: str) -> List[Dict]:
        """Get all statements for a user"""
        try:
            statements = await self.statements_collection.find(
                {"user_id": user_id},
                sort=[("uploaded_at", -1)]
            ).to_list(length=10)
            
            return statements
            
        except Exception as e:
            logger.error(f"Error getting user statements: {e}")
            return []
    
    async def get_statement_insights(self, user_id: str, statement_id: str) -> Optional[Dict]:
        """Get insights for a specific statement"""
        try:
            insights = await self.insights_collection.find_one({
                "user_id": user_id,
                "statement_id": statement_id
            })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting statement insights: {e}")
            return None

# Global service instance
statement_processor = StatementProcessor() 