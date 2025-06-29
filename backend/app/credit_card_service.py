"""
Credit Card Recommendation Service
=================================

Service for recommending personalized credit cards based on user's financial profile,
spending patterns, and credit score. Integrates with card databases and generates
AI-powered recommendations.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib

from .config import (
    CARD_RECOMMENDATION_PROMPTS, FINANCIAL_ANALYSIS_MODEL, FINANCIAL_ANALYSIS_MAX_TOKENS,
    BANK_APPLICATION_URLS, MAX_APPLICATION_ATTEMPTS_PER_DAY
)
from .models import (
    CreditCardCriteria, CreditCardInfo, CreditCardRecommendation, 
    CreditCardApplication, CreditHealthResponse
)
from .db import db_manager
from .credit_report_service import credit_report_service
from .statement_processor import statement_processor
import openai

logger = logging.getLogger(__name__)

class CreditCardRecommendationService:
    """Service for credit card recommendations and applications"""
    
    def __init__(self):
        self.db_manager = db_manager
        self._db_initialized = False
    
    async def _initialize_card_database(self):
        """Initialize credit card database with Indian credit cards"""
        try:
            # Check if cards already exist
            card_count = await self.cards_collection.count_documents({})
            if card_count > 0:
                logger.info(f"Card database already initialized with {card_count} cards")
                return
            
            # Initialize with popular Indian credit cards
            cards_data = self._get_initial_cards_data()
            
            for card_data in cards_data:
                card_data["_id"] = card_data["card_id"]
                card_data["created_at"] = datetime.now().isoformat()
            
            await self.cards_collection.insert_many(cards_data)
            logger.info(f"Initialized card database with {len(cards_data)} cards")
            
        except Exception as e:
            logger.error(f"Error initializing card database: {e}")
    
    def _get_initial_cards_data(self) -> List[Dict]:
        """Get initial credit card data for Indian market"""
        return [
            {
                "card_id": "hdfc_regalia",
                "card_name": "HDFC Bank Regalia Credit Card",
                "bank_name": "HDFC Bank",
                "card_type": "Premium",
                "annual_fee": 2500.0,
                "joining_fee": 2500.0,
                "reward_rate": {
                    "default": 2.0,
                    "dining": 10.0,
                    "fuel": 10.0,
                    "grocery": 5.0
                },
                "benefits": [
                    "10X reward points on dining and fuel",
                    "Complimentary airport lounge access",
                    "Golf privileges",
                    "Insurance coverage"
                ],
                "eligibility_criteria": {
                    "min_income": 250000,
                    "min_age": 21,
                    "min_credit_score": 750
                },
                "application_url": BANK_APPLICATION_URLS.get("hdfc", ""),
                "rating": 4.3,
                "user_reviews": []
            },
            {
                "card_id": "sbi_cashback",
                "card_name": "SBI Cashback Credit Card",
                "bank_name": "State Bank of India",
                "card_type": "Cashback",
                "annual_fee": 999.0,
                "joining_fee": 999.0,
                "reward_rate": {
                    "default": 1.0,
                    "online": 5.0,
                    "fuel": 1.0
                },
                "benefits": [
                    "5% cashback on online spends",
                    "1% on all other spends",
                    "Fuel surcharge waiver",
                    "Welcome bonus"
                ],
                "eligibility_criteria": {
                    "min_income": 200000,
                    "min_age": 21,
                    "min_credit_score": 700
                },
                "application_url": BANK_APPLICATION_URLS.get("sbi", ""),
                "rating": 4.1,
                "user_reviews": []
            },
            {
                "card_id": "icici_amazon",
                "card_name": "Amazon Pay ICICI Credit Card",
                "bank_name": "ICICI Bank",
                "card_type": "Cashback",
                "annual_fee": 0.0,
                "joining_fee": 0.0,
                "reward_rate": {
                    "default": 1.0,
                    "amazon": 5.0,
                    "bill_payments": 2.0
                },
                "benefits": [
                    "5% unlimited cashback on Amazon",
                    "2% on bill payments via Amazon Pay",
                    "1% on all other spends",
                    "No annual fee"
                ],
                "eligibility_criteria": {
                    "min_income": 300000,
                    "min_age": 21,
                    "min_credit_score": 650
                },
                "application_url": BANK_APPLICATION_URLS.get("icici", ""),
                "rating": 4.5,
                "user_reviews": []
            },
            {
                "card_id": "axis_magnus",
                "card_name": "Axis Bank Magnus Credit Card",
                "bank_name": "Axis Bank",
                "card_type": "Premium",
                "annual_fee": 12500.0,
                "joining_fee": 12500.0,
                "reward_rate": {
                    "default": 12.0,
                    "travel": 25.0,
                    "dining": 25.0
                },
                "benefits": [
                    "25X Edge Miles on travel and dining",
                    "12X Edge Miles on other spends",
                    "Airport lounge access",
                    "Golf privileges"
                ],
                "eligibility_criteria": {
                    "min_income": 1500000,
                    "min_age": 21,
                    "min_credit_score": 780
                },
                "application_url": BANK_APPLICATION_URLS.get("axis", ""),
                "rating": 4.2,
                "user_reviews": []
            },
            {
                "card_id": "kotak_league",
                "card_name": "Kotak League Platinum Credit Card",
                "bank_name": "Kotak Mahindra Bank",
                "card_type": "Travel",
                "annual_fee": 1000.0,
                "joining_fee": 1000.0,
                "reward_rate": {
                    "default": 2.0,
                    "fuel": 4.0,
                    "utility": 4.0
                },
                "benefits": [
                    "4X reward points on fuel and utility",
                    "Welcome bonus points",
                    "Fuel surcharge waiver",
                    "Insurance coverage"
                ],
                "eligibility_criteria": {
                    "min_income": 400000,
                    "min_age": 21,
                    "min_credit_score": 720
                },
                "application_url": BANK_APPLICATION_URLS.get("kotak", ""),
                "rating": 4.0,
                "user_reviews": []
            },
            {
                "card_id": "yes_first",
                "card_name": "YES FIRST Credit Card",
                "bank_name": "YES Bank",
                "card_type": "Rewards",
                "annual_fee": 2500.0,
                "joining_fee": 2500.0,
                "reward_rate": {
                    "default": 6.0,
                    "dining": 18.0,
                    "movies": 18.0
                },
                "benefits": [
                    "18X reward points on dining and movies",
                    "6X on all other spends",
                    "Movie ticket offers",
                    "Dining discounts"
                ],
                "eligibility_criteria": {
                    "min_income": 600000,
                    "min_age": 21,
                    "min_credit_score": 730
                },
                "application_url": BANK_APPLICATION_URLS.get("yes", ""),
                "rating": 3.9,
                "user_reviews": []
            }
        ]
    
    async def get_personalized_recommendations(self, criteria: CreditCardCriteria) -> CreditCardRecommendation:
        """Get personalized credit card recommendations"""
        try:
            # Parse income and credit score ranges
            min_income = self._parse_income_range(criteria.income_range)
            min_credit_score, max_credit_score = self._parse_credit_score_range(criteria.credit_score_range)
            
            # Get eligible cards from database
            eligible_cards = await self._get_eligible_cards(min_income, min_credit_score, max_credit_score)
            
            if not eligible_cards:
                # Return basic cards if no premium cards qualify
                eligible_cards = await self._get_basic_cards()
            
            # Filter by preferred category if specified
            if criteria.preferred_category:
                eligible_cards = [card for card in eligible_cards if card["card_type"].lower() == criteria.preferred_category.lower()]
            
            # Score and rank cards based on user profile
            scored_cards = await self._score_cards_for_user(eligible_cards, criteria)
            
            # Get top 5 recommendations
            top_cards = scored_cards[:5]
            
            # Generate personalized reasons and benefits
            personalized_reasons = {}
            estimated_benefits = {}
            
            for card in top_cards:
                reasons = await self._generate_personalized_reasons(card, criteria)
                benefits = await self._calculate_estimated_benefits(card, criteria)
                
                personalized_reasons[card["card_id"]] = reasons
                estimated_benefits[card["card_id"]] = benefits
            
            # Create comparison matrix
            comparison_matrix = self._create_comparison_matrix(top_cards)
            
            # Convert to CreditCardInfo objects
            recommended_cards = [self._dict_to_credit_card_info(card) for card in top_cards]
            
            recommendation = CreditCardRecommendation(
                user_id=criteria.jwt_token,
                recommended_cards=recommended_cards,
                personalized_reasons=personalized_reasons,
                estimated_benefits=estimated_benefits,
                comparison_matrix=comparison_matrix,
                generated_at=datetime.now().isoformat()
            )
            
            # Store recommendation
            await self._store_recommendation(recommendation)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            raise
    
    def _parse_income_range(self, income_range: str) -> int:
        """Parse income range string to minimum income"""
        ranges = {
            "0-25000": 0,
            "25000-50000": 25000,
            "50000-100000": 50000,
            "100000+": 100000
        }
        return ranges.get(income_range, 0)
    
    def _parse_credit_score_range(self, score_range: str) -> Tuple[int, int]:
        """Parse credit score range string to min and max scores"""
        ranges = {
            "300-550": (300, 550),
            "550-650": (550, 650),
            "650-750": (650, 750),
            "750-900": (750, 900)
        }
        return ranges.get(score_range, (300, 900))
    
    async def _get_eligible_cards(self, min_income: int, min_credit_score: int, max_credit_score: int) -> List[Dict]:
        """Get cards eligible for user's income and credit score"""
        try:
            query = {
                "eligibility_criteria.min_income": {"$lte": min_income * 12},  # Annual income
                "eligibility_criteria.min_credit_score": {"$gte": min_credit_score, "$lte": max_credit_score}
            }
            
            cards = await self.cards_collection.find(query).to_list(length=50)
            return cards
            
        except Exception as e:
            logger.error(f"Error getting eligible cards: {e}")
            return []
    
    async def _get_basic_cards(self) -> List[Dict]:
        """Get basic/entry-level cards when user doesn't qualify for premium cards"""
        try:
            query = {
                "eligibility_criteria.min_income": {"$lte": 200000},  # Low income requirement
                "annual_fee": {"$lte": 1000}  # Low or no annual fee
            }
            
            cards = await self.cards_collection.find(query).to_list(length=10)
            return cards
            
        except Exception as e:
            logger.error(f"Error getting basic cards: {e}")
            return []
    
    async def _score_cards_for_user(self, cards: List[Dict], criteria: CreditCardCriteria) -> List[Dict]:
        """Score and rank cards based on user criteria"""
        scored_cards = []
        
        for card in cards:
            score = 0
            
            # Annual fee preference (lower is better)
            if card["annual_fee"] == 0:
                score += 20
            elif card["annual_fee"] <= 1000:
                score += 15
            elif card["annual_fee"] <= 5000:
                score += 10
            
            # Reward rate matching spending categories
            if criteria.spending_categories:
                for category, monthly_spend in criteria.spending_categories.items():
                    if monthly_spend > 0:
                        reward_rate = card["reward_rate"].get(category.lower(), card["reward_rate"]["default"])
                        score += min(reward_rate * 2, 20)  # Cap category bonus
            
            # Card type preference
            if criteria.preferred_category and card["card_type"].lower() == criteria.preferred_category.lower():
                score += 15
            
            # Rating bonus
            score += card.get("rating", 0) * 5
            
            # Age appropriateness
            if criteria.age >= card["eligibility_criteria"]["min_age"]:
                score += 10
            
            card["recommendation_score"] = score
            scored_cards.append(card)
        
        # Sort by score (highest first)
        return sorted(scored_cards, key=lambda x: x["recommendation_score"], reverse=True)
    
    async def _generate_personalized_reasons(self, card: Dict, criteria: CreditCardCriteria) -> List[str]:
        """Generate personalized reasons for recommending this card"""
        reasons = []
        
        # Annual fee reasoning
        if card["annual_fee"] == 0:
            reasons.append("No annual fee - great for getting started with credit cards")
        elif card["annual_fee"] <= 1000:
            reasons.append(f"Low annual fee of ₹{card['annual_fee']} with good benefits")
        
        # Spending category matching
        if criteria.spending_categories:
            for category, spend in criteria.spending_categories.items():
                if spend > 0:
                    reward_rate = card["reward_rate"].get(category.lower(), 0)
                    if reward_rate > card["reward_rate"]["default"]:
                        monthly_benefit = (spend * reward_rate / 100) * 0.25  # Assuming 0.25 rupee per point
                        reasons.append(f"Earn {reward_rate}X rewards on {category} - potential monthly benefit of ₹{monthly_benefit:.0f}")
        
        # Income matching
        min_income = card["eligibility_criteria"]["min_income"]
        user_annual_income = self._parse_income_range(criteria.income_range) * 12
        if user_annual_income >= min_income * 1.5:
            reasons.append("Your income comfortably meets the eligibility criteria")
        
        # Card type benefits
        if card["card_type"] == "Cashback":
            reasons.append("Simple cashback structure - easy to understand and maximize")
        elif card["card_type"] == "Travel":
            reasons.append("Great for travel enthusiasts with airport lounge access and travel benefits")
        elif card["card_type"] == "Premium":
            reasons.append("Premium lifestyle benefits including golf, dining, and concierge services")
        
        return reasons[:4]  # Return top 4 reasons
    
    async def _calculate_estimated_benefits(self, card: Dict, criteria: CreditCardCriteria) -> Dict[str, Any]:
        """Calculate estimated monthly/annual benefits for the user"""
        try:
            monthly_rewards = 0
            annual_fee = card["annual_fee"]
            
            # Calculate rewards based on spending categories
            if criteria.spending_categories:
                for category, monthly_spend in criteria.spending_categories.items():
                    if monthly_spend > 0:
                        reward_rate = card["reward_rate"].get(category.lower(), card["reward_rate"]["default"])
                        category_rewards = (monthly_spend * reward_rate / 100) * 0.25  # 0.25 rupee per point
                        monthly_rewards += category_rewards
            
            annual_rewards = monthly_rewards * 12
            net_annual_benefit = annual_rewards - annual_fee
            
            return {
                "monthly_rewards": round(monthly_rewards, 2),
                "annual_rewards": round(annual_rewards, 2),
                "annual_fee": annual_fee,
                "net_annual_benefit": round(net_annual_benefit, 2),
                "break_even_spend": round(annual_fee / (card["reward_rate"]["default"] / 100 * 0.25), 2) if card["reward_rate"]["default"] > 0 else 0,
                "roi_percentage": round((net_annual_benefit / max(annual_fee, 1)) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating estimated benefits: {e}")
            return {}
    
    def _create_comparison_matrix(self, cards: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Create comparison matrix for recommended cards"""
        comparison = {}
        
        for card in cards:
            comparison[card["card_id"]] = {
                "card_name": card["card_name"],
                "bank_name": card["bank_name"],
                "annual_fee": card["annual_fee"],
                "reward_rate_default": card["reward_rate"]["default"],
                "key_benefits": card["benefits"][:3],  # Top 3 benefits
                "rating": card.get("rating", 0),
                "card_type": card["card_type"]
            }
        
        return comparison
    
    def _dict_to_credit_card_info(self, card_dict: Dict) -> CreditCardInfo:
        """Convert card dictionary to CreditCardInfo object"""
        return CreditCardInfo(
            card_id=card_dict["card_id"],
            card_name=card_dict["card_name"],
            bank_name=card_dict["bank_name"],
            card_type=card_dict["card_type"],
            annual_fee=card_dict["annual_fee"],
            joining_fee=card_dict["joining_fee"],
            reward_rate=card_dict["reward_rate"],
            benefits=card_dict["benefits"],
            eligibility_criteria=card_dict["eligibility_criteria"],
            application_url=card_dict["application_url"],
            card_image_url=card_dict.get("card_image_url"),
            rating=card_dict.get("rating", 0),
            user_reviews=card_dict.get("user_reviews", [])
        )
    
    async def _store_recommendation(self, recommendation: CreditCardRecommendation) -> bool:
        """Store recommendation in database"""
        try:
            rec_dict = recommendation.dict()
            rec_dict["_id"] = f"{recommendation.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            rec_dict["created_at"] = datetime.now().isoformat()
            
            await self.recommendations_collection.insert_one(rec_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing recommendation: {e}")
            return False
    
    async def initiate_card_application(self, user_id: str, card_id: str, pre_filled_data: Dict[str, Any]) -> CreditCardApplication:
        """Initiate credit card application process"""
        try:
            # Check daily application limit
            today = datetime.now().date()
            applications_today = await self.applications_collection.count_documents({
                "user_id": user_id,
                "submitted_at": {
                    "$gte": today.isoformat(),
                    "$lt": (today + timedelta(days=1)).isoformat()
                }
            })
            
            if applications_today >= MAX_APPLICATION_ATTEMPTS_PER_DAY:
                raise ValueError(f"Daily application limit of {MAX_APPLICATION_ATTEMPTS_PER_DAY} exceeded")
            
            # Get card details
            card = await self.cards_collection.find_one({"card_id": card_id})
            if not card:
                raise ValueError("Card not found")
            
            # Create application
            application_id = hashlib.md5(f"{user_id}_{card_id}_{datetime.now()}".encode()).hexdigest()
            
            application = CreditCardApplication(
                application_id=application_id,
                user_id=user_id,
                card_id=card_id,
                bank_name=card["bank_name"],
                card_name=card["card_name"],
                application_status="initiated",
                application_data=pre_filled_data,
                documents_required=self._get_required_documents(card),
                application_url=card["application_url"],
                tracking_number=None,
                submitted_at=None,
                status_updates=[]
            )
            
            # Store application
            await self._store_application(application)
            
            return application
            
        except Exception as e:
            logger.error(f"Error initiating card application: {e}")
            raise
    
    def _get_required_documents(self, card: Dict) -> List[str]:
        """Get required documents for card application"""
        base_documents = [
            "PAN Card",
            "Aadhaar Card",
            "Address Proof",
            "Income Proof (Salary Slips/ITR)",
            "Bank Statements (3 months)"
        ]
        
        # Add additional documents for premium cards
        if card.get("annual_fee", 0) > 5000:
            base_documents.extend([
                "Form 16",
                "Employment Certificate"
            ])
        
        return base_documents
    
    async def _store_application(self, application: CreditCardApplication) -> bool:
        """Store application in database"""
        try:
            app_dict = application.dict()
            app_dict["_id"] = application.application_id
            app_dict["created_at"] = datetime.now().isoformat()
            
            await self.applications_collection.insert_one(app_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing application: {e}")
            return False
    
    async def get_user_recommendations(self, user_id: str) -> List[Dict]:
        """Get user's credit card recommendations history"""
        try:
            recommendations = await self.recommendations_collection.find(
                {"user_id": user_id},
                sort=[("generated_at", -1)]
            ).to_list(length=5)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting user recommendations: {e}")
            return []
    
    async def get_user_applications(self, user_id: str) -> List[Dict]:
        """Get user's credit card applications"""
        try:
            applications = await self.applications_collection.find(
                {"user_id": user_id},
                sort=[("created_at", -1)]
            ).to_list(length=10)
            
            return applications
            
        except Exception as e:
            logger.error(f"Error getting user applications: {e}")
            return []
    
    async def generate_complete_credit_health_report(self, user_id: str) -> CreditHealthResponse:
        """Generate comprehensive credit health report combining all data"""
        try:
            # Get latest credit report
            credit_reports = await credit_report_service.get_user_credit_reports(user_id)
            credit_score = 0
            credit_report_summary = {}
            
            if credit_reports:
                latest_report = credit_reports[0]
                credit_score = latest_report.get("credit_score_info", {}).get("score", 0)
                credit_report_summary = {
                    "score": credit_score,
                    "total_accounts": latest_report.get("summary_stats", {}).get("total_accounts", 0),
                    "credit_utilization": latest_report.get("summary_stats", {}).get("credit_utilization", 0),
                    "report_date": latest_report.get("report_date", "")
                }
            
            # Get statement insights
            statements = await statement_processor.get_user_statements(user_id)
            statement_insights = {}
            
            if statements:
                latest_statement = statements[0]
                insights = await statement_processor.get_statement_insights(user_id, latest_statement["statement_id"])
                if insights:
                    statement_insights = {
                        "monthly_income": insights.get("income_analysis", {}).get("raw_data", {}).get("total_income", 0),
                        "monthly_expenses": insights.get("spending_analysis", {}).get("raw_data", {}).get("total_spending", 0),
                        "savings_rate": insights.get("savings_analysis", {}).get("savings_rate", 0),
                        "financial_health_score": insights.get("financial_habits", {}).get("health_score", 0)
                    }
            
            # Get personalized card recommendations
            criteria = CreditCardCriteria(
                jwt_token=user_id,
                income_range="50000-100000",  # Default, should be determined from statement
                credit_score_range=f"{max(credit_score-50, 300)}-{min(credit_score+50, 900)}",
                age=30,  # Default
                employment_type="Salaried",
                city="Mumbai"
            )
            
            recommendations = await self.get_personalized_recommendations(criteria)
            
            # Generate financial goals and action plan
            financial_goals = self._generate_financial_goals(credit_score, statement_insights)
            action_plan = self._generate_action_plan(credit_score, statement_insights)
            risk_assessment = self._assess_financial_risk(credit_score, statement_insights)
            
            return CreditHealthResponse(
                user_id=user_id,
                credit_score=credit_score,
                credit_report_summary=credit_report_summary,
                statement_insights=statement_insights,
                recommended_cards=recommendations.recommended_cards,
                financial_goals=financial_goals,
                action_plan=action_plan,
                risk_assessment=risk_assessment,
                generated_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error generating credit health report: {e}")
            raise
    
    def _generate_financial_goals(self, credit_score: int, statement_insights: Dict) -> List[str]:
        """Generate personalized financial goals"""
        goals = []
        
        if credit_score < 700:
            goals.append("Improve credit score to 750+ for better credit card approvals")
        elif credit_score < 800:
            goals.append("Achieve excellent credit score (800+) for premium card eligibility")
        
        savings_rate = statement_insights.get("savings_rate", 0)
        if savings_rate < 10:
            goals.append("Increase savings rate to at least 20% of income")
        elif savings_rate < 20:
            goals.append("Optimize savings rate to 25-30% for wealth building")
        
        goals.append("Build emergency fund covering 6 months of expenses")
        goals.append("Start investing in diversified portfolio for long-term wealth")
        
        return goals
    
    def _generate_action_plan(self, credit_score: int, statement_insights: Dict) -> List[Dict[str, Any]]:
        """Generate actionable financial plan"""
        actions = []
        
        if credit_score < 750:
            actions.append({
                "action": "Improve Credit Score",
                "steps": [
                    "Pay all bills on time",
                    "Keep credit utilization below 30%",
                    "Don't close old credit cards",
                    "Monitor credit report monthly"
                ],
                "timeline": "3-6 months",
                "priority": "High"
            })
        
        expenses = statement_insights.get("monthly_expenses", 0)
        income = statement_insights.get("monthly_income", 0)
        
        if expenses > income * 0.8:
            actions.append({
                "action": "Reduce Monthly Expenses",
                "steps": [
                    "Review and cut unnecessary subscriptions",
                    "Optimize dining and entertainment expenses",
                    "Negotiate better rates for utilities",
                    "Create and stick to a monthly budget"
                ],
                "timeline": "1-2 months",
                "priority": "High"
            })
        
        if statement_insights.get("savings_rate", 0) < 20:
            actions.append({
                "action": "Increase Savings Rate",
                "steps": [
                    "Automate savings transfers",
                    "Start SIP investments",
                    "Track expenses daily",
                    "Set specific savings targets"
                ],
                "timeline": "3 months",
                "priority": "Medium"
            })
        
        return actions
    
    def _assess_financial_risk(self, credit_score: int, statement_insights: Dict) -> Dict[str, Any]:
        """Assess overall financial risk profile"""
        risk_score = 0  # 0-100, higher is riskier
        risk_factors = []
        
        # Credit score risk
        if credit_score < 600:
            risk_score += 30
            risk_factors.append("Poor credit score limits financial options")
        elif credit_score < 700:
            risk_score += 15
            risk_factors.append("Fair credit score - room for improvement")
        
        # Savings rate risk
        savings_rate = statement_insights.get("savings_rate", 0)
        if savings_rate < 0:
            risk_score += 40
            risk_factors.append("Negative savings - spending exceeds income")
        elif savings_rate < 10:
            risk_score += 20
            risk_factors.append("Low savings rate - insufficient emergency buffer")
        
        # Financial health score
        health_score = statement_insights.get("financial_health_score", 50)
        if health_score < 40:
            risk_score += 20
            risk_factors.append("Poor financial health indicators")
        
        # Risk level determination
        if risk_score >= 60:
            risk_level = "High"
        elif risk_score >= 30:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        return {
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": self._get_risk_mitigation_recommendations(risk_level)
        }
    
    def _get_risk_mitigation_recommendations(self, risk_level: str) -> List[str]:
        """Get recommendations based on risk level"""
        if risk_level == "High":
            return [
                "Focus on debt reduction and expense control",
                "Build emergency fund as top priority",
                "Avoid taking new credit until finances stabilize",
                "Consider financial counseling"
            ]
        elif risk_level == "Medium":
            return [
                "Improve credit score through disciplined payments",
                "Increase savings rate gradually",
                "Diversify income sources if possible",
                "Monitor expenses closely"
            ]
        else:
            return [
                "Maintain good financial habits",
                "Consider investment opportunities",
                "Optimize credit card rewards",
                "Plan for long-term financial goals"
            ]

# Global service instance
credit_card_service = CreditCardRecommendationService() 