"""
Credit Report Service
====================

Service for integrating with Indian credit bureaus (CIBIL, Experian, CRIF, Equifax)
to fetch credit reports and generate AI-powered insights for users.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import hashlib
from cryptography.fernet import Fernet

from .config import (
    SUPPORTED_CREDIT_BUREAUS, CREDIT_REPORT_TIMEOUT, CREDIT_REPORT_CACHE_HOURS,
    CREDIT_REPORT_RETRY_ATTEMPTS, MAX_CREDIT_REPORTS_PER_USER_PER_MONTH,
    ENABLE_DATA_ENCRYPTION, CREDIT_REPORT_ANALYSIS_PROMPTS,
    FINANCIAL_ANALYSIS_MODEL, FINANCIAL_ANALYSIS_MAX_TOKENS
)
from .models import (
    CreditReportRequest, CreditReportData, CreditReportInsights,
    CreditScoreInfo, CreditAccount, CreditEnquiry
)
from .db import users_collection, db_manager
import openai

logger = logging.getLogger(__name__)

class CreditReportService:
    """Service for credit report fetching and analysis"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.encryption_key = self._get_or_create_encryption_key()
    
    async def _get_credit_reports_collection(self, user_id: str):
        """Get credit reports collection for user"""
        return await self.db_manager.get_collection(user_id, "credit_reports")
    
    async def _get_credit_insights_collection(self, user_id: str):
        """Get credit insights collection for user"""
        return await self.db_manager.get_collection(user_id, "credit_insights")
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_env = os.getenv("CREDIT_DATA_ENCRYPTION_KEY")
        if key_env:
            return key_env.encode()
        
        # Generate new key (in production, store this securely)
        key = Fernet.generate_key()
        logger.warning("Generated new encryption key. Store this securely in production!")
        return key
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like PAN, phone numbers"""
        if not ENABLE_DATA_ENCRYPTION:
            return data
        
        fernet = Fernet(self.encryption_key)
        return fernet.encrypt(data.encode()).decode()
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not ENABLE_DATA_ENCRYPTION:
            return encrypted_data
        
        fernet = Fernet(self.encryption_key)
        return fernet.decrypt(encrypted_data.encode()).decode()
    
    async def check_user_eligibility(self, user_id: str) -> Tuple[bool, str]:
        """Check if user is eligible for credit report fetch"""
        try:
            # Check monthly limit
            current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            credit_reports_collection = await self._get_credit_reports_collection(user_id)
            reports_this_month = await credit_reports_collection.count_documents({
                "user_id": user_id,
                "report_date": {"$gte": current_month.isoformat()}
            })
            
            if reports_this_month >= MAX_CREDIT_REPORTS_PER_USER_PER_MONTH:
                return False, f"Monthly limit of {MAX_CREDIT_REPORTS_PER_USER_PER_MONTH} credit reports exceeded"
            
            return True, "Eligible for credit report"
            
        except Exception as e:
            logger.error(f"Error checking user eligibility: {e}")
            return False, "Error checking eligibility"
    
    async def fetch_credit_report(self, request: CreditReportRequest) -> Dict[str, Any]:
        """Fetch credit report from specified bureau"""
        try:
            # Check eligibility
            is_eligible, message = await self.check_user_eligibility(request.jwt_token)
            if not is_eligible:
                return {"success": False, "error": message}
            
            # Get bureau configuration
            bureau_config = SUPPORTED_CREDIT_BUREAUS.get(request.bureau.lower())
            if not bureau_config or not bureau_config["enabled"]:
                return {"success": False, "error": f"Bureau {request.bureau} not available"}
            
            # Check cache first
            cached_report = await self._get_cached_report(request.jwt_token, request.bureau)
            if cached_report:
                return {"success": True, "data": cached_report, "source": "cache"}
            
            # Fetch from bureau API
            if bureau_config["sandbox_mode"]:
                # Use mock data for sandbox/testing
                report_data = await self._fetch_mock_credit_report(request)
            else:
                # Use real API
                report_data = await self._fetch_real_credit_report(request, bureau_config)
            
            if report_data:
                # Store in database
                await self._store_credit_report(report_data)
                return {"success": True, "data": report_data, "source": "api"}
            else:
                return {"success": False, "error": "Failed to fetch credit report"}
            
        except Exception as e:
            logger.error(f"Error fetching credit report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_cached_report(self, user_id: str, bureau: str) -> Optional[Dict]:
        """Get cached credit report if available and recent"""
        try:
            cache_cutoff = datetime.now() - timedelta(hours=CREDIT_REPORT_CACHE_HOURS)
            
            credit_reports_collection = await self._get_credit_reports_collection(user_id)
            cached_report = await credit_reports_collection.find_one({
                "user_id": user_id,
                "bureau_name": bureau.lower(),
                "report_date": {"$gte": cache_cutoff.isoformat()}
            })
            
            return cached_report
            
        except Exception as e:
            logger.error(f"Error getting cached report: {e}")
            return None
    
    async def _fetch_mock_credit_report(self, request: CreditReportRequest) -> CreditReportData:
        """Generate mock credit report for testing"""
        report_id = hashlib.md5(f"{request.jwt_token}_{request.bureau}_{datetime.now()}".encode()).hexdigest()
        
        # Mock credit score info
        credit_score_info = CreditScoreInfo(
            score=750 + hash(request.jwt_token) % 150,  # Score between 750-900
            range_max=900,
            range_min=300,
            factors_affecting_score=[
                "Payment history (35%)",
                "Credit utilization (30%)",
                "Length of credit history (15%)",
                "Credit mix (10%)",
                "New credit (10%)"
            ],
            score_change=5,
            previous_score=745
        )
        
        # Mock credit accounts
        accounts = [
            CreditAccount(
                account_number=self._encrypt_sensitive_data("HDFC****1234"),
                account_type="Credit Card",
                bank_name="HDFC Bank",
                current_balance=25000.0,
                credit_limit=100000.0,
                overdue_amount=0.0,
                days_past_due=0,
                payment_history=[
                    {"month": "2024-01", "status": "Paid", "amount": 15000},
                    {"month": "2024-02", "status": "Paid", "amount": 18000},
                ],
                account_status="Active",
                date_opened="2020-01-15",
                date_last_payment="2024-01-05"
            ),
            CreditAccount(
                account_number=self._encrypt_sensitive_data("ICICI****5678"),
                account_type="Personal Loan",
                bank_name="ICICI Bank",
                current_balance=150000.0,
                credit_limit=None,
                overdue_amount=0.0,
                days_past_due=0,
                payment_history=[
                    {"month": "2024-01", "status": "Paid", "amount": 12500},
                    {"month": "2024-02", "status": "Paid", "amount": 12500},
                ],
                account_status="Active",
                date_opened="2023-06-01",
                date_last_payment="2024-02-05"
            )
        ]
        
        # Mock enquiries
        enquiries = [
            CreditEnquiry(
                enquiry_date="2024-01-15",
                enquiring_member="HDFC Bank",
                enquiry_purpose="Credit Card",
                enquiry_amount=100000.0
            )
        ]
        
        return CreditReportData(
            report_id=report_id,
            user_id=request.jwt_token,
            bureau_name=request.bureau.lower(),
            report_date=datetime.now().isoformat(),
            credit_score_info=credit_score_info,
            personal_info={
                "name": request.full_name,
                "pan": self._encrypt_sensitive_data(request.pan_number),
                "dob": request.date_of_birth,
                "phone": self._encrypt_sensitive_data(request.phone_number),
                "address": request.address
            },
            accounts=accounts,
            enquiries=enquiries,
            public_records=[],
            summary_stats={
                "total_accounts": len(accounts),
                "active_accounts": len([a for a in accounts if a.account_status == "Active"]),
                "total_credit_limit": sum(a.credit_limit or 0 for a in accounts),
                "total_outstanding": sum(a.current_balance for a in accounts),
                "credit_utilization": 25.0
            },
            raw_report_data={"mock_data": True, "bureau": request.bureau}
        )
    
    async def _fetch_real_credit_report(self, request: CreditReportRequest, bureau_config: Dict) -> Optional[CreditReportData]:
        """Fetch real credit report from bureau API"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=CREDIT_REPORT_TIMEOUT)) as session:
                
                # Prepare API request based on bureau
                if request.bureau.lower() == "cibil":
                    return await self._fetch_cibil_report(session, request, bureau_config)
                elif request.bureau.lower() == "experian":
                    return await self._fetch_experian_report(session, request, bureau_config)
                elif request.bureau.lower() == "crif":
                    return await self._fetch_crif_report(session, request, bureau_config)
                elif request.bureau.lower() == "equifax":
                    return await self._fetch_equifax_report(session, request, bureau_config)
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching real credit report: {e}")
            return None
    
    async def _fetch_cibil_report(self, session: aiohttp.ClientSession, request: CreditReportRequest, config: Dict) -> Optional[CreditReportData]:
        """Fetch report from CIBIL API"""
        try:
            # CIBIL API Integration
            if config.get("sandbox_mode", True):
                logger.info("CIBIL sandbox mode - using mock data")
                return await self._fetch_mock_credit_report(request)
            
            # Real CIBIL API call
            api_endpoint = config["api_endpoint"]
            api_key = config["api_key"]
            
            # CIBIL requires specific headers and authentication
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-CIBIL-Merchant-ID": os.getenv("CIBIL_MERCHANT_ID", ""),
                "X-CIBIL-User-Name": os.getenv("CIBIL_USERNAME", ""),
                "X-CIBIL-Password": os.getenv("CIBIL_PASSWORD", "")
            }
            
            # CIBIL API payload structure
            payload = {
                "ConsumerData": {
                    "PAN": request.pan_number,
                    "Name": request.full_name,
                    "DateOfBirth": request.date_of_birth,
                    "Gender": "M",  # Default, can be enhanced
                    "ContactInfo": {
                        "MobileNumber": request.phone_number,
                        "EmailAddress": getattr(request, 'email_address', ''),
                        "Address": {
                            "AddressLine1": request.address,
                            "City": getattr(request, 'city', ''),
                            "State": getattr(request, 'state', ''),
                            "Pincode": getattr(request, 'pincode', '')
                        }
                    }
                },
                "RequestInfo": {
                    "Purpose": "CRED",  # Credit Decision
                    "Amount": "0",
                    "ScoreType": "CIBIL_SCORE_2.0",
                    "ReportType": "CIR",  # Credit Information Report
                    "MemberRefNo": f"REF_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
            }
            
            # Make API call to CIBIL
            async with session.post(
                f"{api_endpoint}/report/credit-information",
                headers=headers,
                json=payload,
                timeout=CREDIT_REPORT_TIMEOUT
            ) as response:
                
                if response.status == 200:
                    cibil_data = await response.json()
                    
                    # Parse CIBIL response and convert to our format
                    return self._parse_cibil_response(cibil_data, request)
                    
                elif response.status == 429:
                    logger.warning(f"CIBIL rate limit exceeded: {response.status}")
                    return None
                    
                else:
                    error_text = await response.text()
                    logger.error(f"CIBIL API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching CIBIL report: {e}")
            return None

    async def _fetch_experian_report(self, session: aiohttp.ClientSession, request: CreditReportRequest, config: Dict) -> Optional[CreditReportData]:
        """Fetch report from Experian API"""
        try:
            # Experian API Integration
            if config.get("sandbox_mode", True):
                logger.info("Experian sandbox mode - using mock data")
                return await self._fetch_mock_credit_report(request)
            
            # Real Experian API call
            api_endpoint = config["api_endpoint"]
            client_id = os.getenv("EXPERIAN_CLIENT_ID", "")
            client_secret = os.getenv("EXPERIAN_CLIENT_SECRET", "")
            
            # First, get OAuth token
            auth_token = await self._get_experian_auth_token(session, client_id, client_secret)
            if not auth_token:
                return None
            
            # Experian API headers
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
                "X-Experian-Client-ID": client_id
            }
            
            # Experian API payload structure
            payload = {
                "ConsumerIdentity": {
                    "PersonalIdentifiers": {
                        "PAN": request.pan_number,
                        "FullName": request.full_name,
                        "DateOfBirth": request.date_of_birth,
                        "Gender": "M"
                    },
                    "ContactDetails": {
                        "PhoneNumber": request.phone_number,
                        "EmailAddress": getattr(request, 'email_address', ''),
                        "CurrentAddress": {
                            "AddressText": request.address
                        }
                    }
                },
                "CreditReportRequest": {
                    "ProductCode": "EXPERIAN_CREDIT_PROFILE",
                    "Version": "2.0",
                    "Purpose": "ACCOUNT_REVIEW",
                    "ConsentFlag": "Y"
                }
            }
            
            # Make API call to Experian
            async with session.post(
                f"{api_endpoint}/creditreport/individual",
                headers=headers,
                json=payload,
                timeout=CREDIT_REPORT_TIMEOUT
            ) as response:
                
                if response.status == 200:
                    experian_data = await response.json()
                    return self._parse_experian_response(experian_data, request)
                    
                else:
                    error_text = await response.text()
                    logger.error(f"Experian API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Experian report: {e}")
            return None

    async def _fetch_crif_report(self, session: aiohttp.ClientSession, request: CreditReportRequest, config: Dict) -> Optional[CreditReportData]:
        """Fetch report from CRIF API"""
        try:
            # CRIF API Integration
            if config.get("sandbox_mode", True):
                logger.info("CRIF sandbox mode - using mock data")
                return await self._fetch_mock_credit_report(request)
            
            # Real CRIF API call
            api_endpoint = config["api_endpoint"]
            api_key = config["api_key"]
            partner_id = os.getenv("CRIF_PARTNER_ID", "")
            
            # CRIF API headers
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-CRIF-Partner-ID": partner_id,
                "X-CRIF-Request-ID": f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            # CRIF API payload structure
            payload = {
                "RequestHeader": {
                    "MessageId": f"MSG_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "Timestamp": datetime.now().isoformat(),
                    "PartnerId": partner_id
                },
                "ConsumerRequest": {
                    "IdentificationData": {
                        "PAN": request.pan_number,
                        "Name": request.full_name,
                        "DOB": request.date_of_birth,
                        "Mobile": request.phone_number,
                        "Address": request.address
                    },
                    "ProductRequest": {
                        "ProductType": "CreditProfile",
                        "ScoreRequired": "Y",
                        "ReportFormat": "JSON"
                    }
                }
            }
            
            # Make API call to CRIF
            async with session.post(
                f"{api_endpoint}/creditreport",
                headers=headers,
                json=payload,
                timeout=CREDIT_REPORT_TIMEOUT
            ) as response:
                
                if response.status == 200:
                    crif_data = await response.json()
                    return self._parse_crif_response(crif_data, request)
                    
                else:
                    error_text = await response.text()
                    logger.error(f"CRIF API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching CRIF report: {e}")
            return None

    async def _fetch_equifax_report(self, session: aiohttp.ClientSession, request: CreditReportRequest, config: Dict) -> Optional[CreditReportData]:
        """Fetch report from Equifax API"""
        try:
            # Equifax API Integration
            if config.get("sandbox_mode", True):
                logger.info("Equifax sandbox mode - using mock data")
                return await self._fetch_mock_credit_report(request)
            
            # Real Equifax API call
            api_endpoint = config["api_endpoint"]
            api_key = config["api_key"]
            subscriber_id = os.getenv("EQUIFAX_SUBSCRIBER_ID", "")
            security_code = os.getenv("EQUIFAX_SECURITY_CODE", "")
            
            # Equifax API headers
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Equifax-Subscriber-ID": subscriber_id,
                "X-Equifax-Security-Code": security_code
            }
            
            # Equifax API payload structure
            payload = {
                "RequestData": {
                    "Header": {
                        "SubscriberID": subscriber_id,
                        "SecurityCode": security_code,
                        "TransactionID": f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    },
                    "Body": {
                        "ConsumerProfile": {
                            "PAN": request.pan_number,
                            "ConsumerName": request.full_name,
                            "DateOfBirth": request.date_of_birth,
                            "ContactNumber": request.phone_number,
                            "ResidentialAddress": request.address
                        },
                        "InquiryPurpose": "05",  # Account Review
                        "ProductCode": "ERS",   # Equifax Risk Score
                        "OutputFormat": "JSON"
                    }
                }
            }
            
            # Make API call to Equifax
            async with session.post(
                f"{api_endpoint}/consumer/creditreport",
                headers=headers,
                json=payload,
                timeout=CREDIT_REPORT_TIMEOUT
            ) as response:
                
                if response.status == 200:
                    equifax_data = await response.json()
                    return self._parse_equifax_response(equifax_data, request)
                    
                else:
                    error_text = await response.text()
                    logger.error(f"Equifax API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Equifax report: {e}")
            return None

    # Response parsing methods for each bureau
    def _parse_cibil_response(self, cibil_data: Dict, request: CreditReportRequest) -> CreditReportData:
        """Parse CIBIL API response and convert to our standard format"""
        try:
            # Extract credit score
            score_info = cibil_data.get("ScoreInfo", {})
            credit_score_info = CreditScoreInfo(
                score=int(score_info.get("Score", 0)),
                range_max=900,
                range_min=300,
                factors_affecting_score=score_info.get("Factors", []),
                score_change=score_info.get("Change", 0),
                previous_score=score_info.get("PreviousScore", 0)
            )
            
            # Extract accounts
            accounts = []
            for acc_data in cibil_data.get("AccountDetails", []):
                account = CreditAccount(
                    account_number=self._encrypt_sensitive_data(acc_data.get("AccountNumber", "")),
                    account_type=acc_data.get("AccountType", ""),
                    bank_name=acc_data.get("BankName", ""),
                    current_balance=float(acc_data.get("CurrentBalance", 0)),
                    credit_limit=float(acc_data.get("CreditLimit", 0)) if acc_data.get("CreditLimit") else None,
                    overdue_amount=float(acc_data.get("OverdueAmount", 0)),
                    days_past_due=int(acc_data.get("DaysPastDue", 0)),
                    payment_history=acc_data.get("PaymentHistory", []),
                    account_status=acc_data.get("Status", ""),
                    date_opened=acc_data.get("DateOpened", ""),
                    date_last_payment=acc_data.get("LastPaymentDate", "")
                )
                accounts.append(account)
            
            # Extract enquiries
            enquiries = []
            for enq_data in cibil_data.get("Enquiries", []):
                enquiry = CreditEnquiry(
                    enquiry_date=enq_data.get("Date", ""),
                    enquiring_member=enq_data.get("Member", ""),
                    enquiry_purpose=enq_data.get("Purpose", ""),
                    enquiry_amount=float(enq_data.get("Amount", 0))
                )
                enquiries.append(enquiry)
            
            # Create and return credit report
            return CreditReportData(
                report_id=f"CIBIL_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=request.jwt_token,
                bureau_name="cibil",
                report_date=datetime.now().isoformat(),
                credit_score_info=credit_score_info,
                personal_info={
                    "name": request.full_name,
                    "pan": self._encrypt_sensitive_data(request.pan_number),
                    "dob": request.date_of_birth,
                    "phone": self._encrypt_sensitive_data(request.phone_number),
                    "address": request.address
                },
                accounts=accounts,
                enquiries=enquiries,
                public_records=cibil_data.get("PublicRecords", []),
                summary_stats={
                    "total_accounts": len(accounts),
                    "active_accounts": len([a for a in accounts if a.account_status == "Active"]),
                    "total_credit_limit": sum(a.credit_limit or 0 for a in accounts),
                    "total_outstanding": sum(a.current_balance for a in accounts),
                    "credit_utilization": cibil_data.get("SummaryStats", {}).get("CreditUtilization", 0)
                },
                raw_report_data=cibil_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing CIBIL response: {e}")
            raise ValueError(f"Failed to parse CIBIL response: {e}")

    def _parse_experian_response(self, experian_data: Dict, request: CreditReportRequest) -> CreditReportData:
        """Parse Experian API response and convert to our standard format"""
        # Similar structure to CIBIL parser but adapted for Experian format
        # Implementation would follow the same pattern
        logger.info("Parsing Experian response - not implemented yet")
        raise NotImplementedError("Experian response parsing not implemented")

    def _parse_crif_response(self, crif_data: Dict, request: CreditReportRequest) -> CreditReportData:
        """Parse CRIF API response and convert to our standard format"""
        # Similar structure to CIBIL parser but adapted for CRIF format
        logger.info("Parsing CRIF response - not implemented yet")
        raise NotImplementedError("CRIF response parsing not implemented")

    def _parse_equifax_response(self, equifax_data: Dict, request: CreditReportRequest) -> CreditReportData:
        """Parse Equifax API response and convert to our standard format"""
        # Similar structure to CIBIL parser but adapted for Equifax format
        logger.info("Parsing Equifax response - not implemented yet")
        raise NotImplementedError("Equifax response parsing not implemented")

    async def _get_experian_auth_token(self, session: aiohttp.ClientSession, client_id: str, client_secret: str) -> Optional[str]:
        """Get OAuth token for Experian API"""
        try:
            auth_payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "creditreport"
            }
            
            async with session.post(
                "https://api.experian.in/oauth/token",
                data=auth_payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    auth_data = await response.json()
                    return auth_data.get("access_token")
                else:
                    logger.error(f"Experian auth failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting Experian auth token: {e}")
            return None
    
    async def _store_credit_report(self, report_data: CreditReportData) -> bool:
        """Store credit report in database"""
        try:
            report_dict = report_data.dict()
            report_dict["_id"] = report_data.report_id
            report_dict["created_at"] = datetime.now().isoformat()
            
            credit_reports_collection = await self._get_credit_reports_collection(report_data.user_id)
            await credit_reports_collection.insert_one(report_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing credit report: {e}")
            return False
    
    async def generate_credit_insights(self, user_id: str, report_id: str) -> CreditReportInsights:
        """Generate AI-powered insights from credit report"""
        try:
            # Get credit report
            credit_reports_collection = await self._get_credit_reports_collection(user_id)
            report = await credit_reports_collection.find_one({"report_id": report_id, "user_id": user_id})
            if not report:
                raise ValueError("Credit report not found")
            
            # Generate insights using OpenAI
            insights = await self._analyze_credit_report_with_ai(report)
            
            # Store insights
            await self._store_credit_insights(insights)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating credit insights: {e}")
            raise
    
    async def _analyze_credit_report_with_ai(self, report: Dict) -> CreditReportInsights:
        """Use AI to analyze credit report and generate insights"""
        try:
            # Prepare data for AI analysis
            analysis_data = {
                "credit_score": report["credit_score_info"]["score"],
                "accounts": report["accounts"],
                "enquiries": report["enquiries"],
                "summary_stats": report["summary_stats"]
            }
            
            # Generate different types of analysis
            score_analysis = await self._get_ai_analysis("score_analysis", analysis_data)
            debt_analysis = await self._get_ai_analysis("debt_analysis", analysis_data)
            risk_assessment = await self._get_ai_analysis("risk_assessment", analysis_data)
            
            # Determine overall credit health
            score = report["credit_score_info"]["score"]
            if score >= 800:
                health = "Excellent"
            elif score >= 750:
                health = "Good"
            elif score >= 650:
                health = "Fair"
            else:
                health = "Poor"
            
            return CreditReportInsights(
                user_id=report["user_id"],
                report_id=report["report_id"],
                overall_credit_health=health,
                key_strengths=score_analysis.get("strengths", []),
                areas_for_improvement=debt_analysis.get("improvements", []),
                action_recommendations=risk_assessment.get("recommendations", []),
                risk_factors=risk_assessment.get("risks", []),
                score_improvement_tips=score_analysis.get("tips", []),
                debt_to_income_analysis=debt_analysis.get("debt_analysis", {}),
                credit_utilization_analysis=score_analysis.get("utilization_analysis", {}),
                payment_behavior_analysis=debt_analysis.get("payment_analysis", {}),
                generated_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing credit report with AI: {e}")
            raise
    
    async def _get_ai_analysis(self, analysis_type: str, data: Dict) -> Dict:
        """Get AI analysis for specific aspect of credit report"""
        try:
            prompt = CREDIT_REPORT_ANALYSIS_PROMPTS.get(analysis_type, "")
            if not prompt:
                return {}
            
            # Prepare the full prompt
            full_prompt = f"{prompt}\n\nCredit Report Data:\n{json.dumps(data, indent=2)}\n\nProvide analysis in JSON format with relevant fields."
            
            # Call OpenAI API
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await client.chat.completions.create(
                model=FINANCIAL_ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": "You are a financial advisor expert in credit analysis. Provide detailed, actionable insights."},
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
    
    async def _store_credit_insights(self, insights: CreditReportInsights) -> bool:
        """Store credit insights in database"""
        try:
            insights_dict = insights.dict()
            insights_dict["_id"] = f"{insights.user_id}_{insights.report_id}"
            insights_dict["created_at"] = datetime.now().isoformat()
            
            credit_insights_collection = await self._get_credit_insights_collection(insights.user_id)
            await credit_insights_collection.insert_one(insights_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing credit insights: {e}")
            return False
    
    async def get_user_credit_reports(self, user_id: str) -> List[Dict]:
        """Get all credit reports for a user"""
        try:
            credit_reports_collection = await self._get_credit_reports_collection(user_id)
            reports = await credit_reports_collection.find(
                {"user_id": user_id},
                sort=[("report_date", -1)]
            ).to_list(length=10)
            
            # Decrypt sensitive fields for display
            for report in reports:
                if "personal_info" in report:
                    personal_info = report["personal_info"]
                    if "pan" in personal_info:
                        personal_info["pan"] = self._mask_sensitive_data(personal_info["pan"])
                    if "phone" in personal_info:
                        personal_info["phone"] = self._mask_sensitive_data(personal_info["phone"])
            
            return reports
            
        except Exception as e:
            logger.error(f"Error getting user credit reports: {e}")
            return []
    
    async def get_credit_insights(self, user_id: str, report_id: str) -> Optional[Dict]:
        """Get credit insights for a specific report"""
        try:
            credit_insights_collection = await self._get_credit_insights_collection(user_id)
            insights = await credit_insights_collection.find_one({
                "user_id": user_id,
                "report_id": report_id
            })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting credit insights: {e}")
            return None
    
    def _mask_sensitive_data(self, data: str) -> str:
        """Mask sensitive data for display"""
        if len(data) <= 4:
            return "****"
        return data[:2] + "*" * (len(data) - 4) + data[-2:]

# Global service instance
credit_report_service = CreditReportService() 