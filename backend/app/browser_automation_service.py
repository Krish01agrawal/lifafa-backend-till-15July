"""
Browser Automation Service
==========================

Service for browser automation including credit card scraping from comparison sites
and automated form filling for credit card applications using Playwright.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import re
import hashlib
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from .config import (
    BROWSER_AUTOMATION_TIMEOUT, BROWSER_TYPE, BROWSER_HEADLESS_MODE, PLAYWRIGHT_BROWSER_ARGS,
    CREDIT_CARD_SOURCES, ENABLE_AUTO_FORM_FILLING, FORM_FILLING_DELAY_SECONDS,
    BANK_APPLICATION_URLS, MAX_APPLICATION_ATTEMPTS_PER_DAY
)
from .models import (
    BrowserAutomationRequest, ScrapingResult, CreditCardInfo
)
from .db import db_manager

logger = logging.getLogger(__name__)

class BrowserAutomationService:
    """Service for browser automation tasks"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.browser_instance = None
        self.browser_context = None
    
    async def _get_scraping_results_collection(self, user_id: str):
        """Get scraping results collection for user"""
        return await self.db_manager.get_collection(user_id, "scraping_results")
    
    async def _get_automation_logs_collection(self, user_id: str):
        """Get automation logs collection for user"""
        return await self.db_manager.get_collection(user_id, "automation_logs")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()
    
    async def initialize_browser(self):
        """Initialize Playwright browser instance"""
        try:
            self.playwright = await async_playwright().start()
            
            # Choose browser type
            if BROWSER_TYPE == "chromium":
                browser_launcher = self.playwright.chromium
            elif BROWSER_TYPE == "firefox":
                browser_launcher = self.playwright.firefox
            elif BROWSER_TYPE == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium
            
            # Launch browser with configuration
            self.browser_instance = await browser_launcher.launch(
                headless=BROWSER_HEADLESS_MODE,
                args=PLAYWRIGHT_BROWSER_ARGS
            )
            
            # Create browser context with mobile user agent for better scraping
            self.browser_context = await self.browser_instance.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            logger.info("Browser automation service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            raise
    
    async def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.browser_context:
                await self.browser_context.close()
            if self.browser_instance:
                await self.browser_instance.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
                
            logger.info("Browser automation service closed")
            
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def execute_automation_request(self, request: BrowserAutomationRequest) -> ScrapingResult:
        """Execute browser automation request"""
        try:
            task_id = hashlib.md5(f"{request.jwt_token}_{request.task_type}_{datetime.now()}".encode()).hexdigest()
            
            # Log automation request
            await self._log_automation_request(task_id, request)
            
            if request.task_type == "scrape_cards":
                result = await self._scrape_credit_cards(task_id, request.parameters)
            elif request.task_type == "fill_application":
                result = await self._fill_application_form(task_id, request.parameters)
            elif request.task_type == "track_status":
                result = await self._track_application_status(task_id, request.parameters)
            else:
                raise ValueError(f"Unsupported task type: {request.task_type}")
            
            # Store result
            await self._store_scraping_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing automation request: {e}")
            return ScrapingResult(
                task_id=task_id if 'task_id' in locals() else "error",
                status="failed",
                data={},
                errors=[str(e)],
                scraped_at=datetime.now().isoformat(),
                source_urls=[]
            )
    
    async def _scrape_credit_cards(self, task_id: str, parameters: Dict[str, Any]) -> ScrapingResult:
        """Scrape credit card information from comparison websites"""
        try:
            scraped_cards = []
            source_urls = []
            errors = []
            
            # Get enabled sources
            enabled_sources = {k: v for k, v in CREDIT_CARD_SOURCES.items() if v.get("enabled", False)}
            
            for source_name, source_config in enabled_sources.items():
                try:
                    logger.info(f"Scraping cards from {source_name}")
                    
                    cards = await self._scrape_from_source(source_name, source_config, parameters)
                    scraped_cards.extend(cards)
                    source_urls.append(source_config["url"])
                    
                    # Rate limiting
                    await asyncio.sleep(source_config.get("rate_limit", 60))
                    
                except Exception as e:
                    logger.error(f"Error scraping from {source_name}: {e}")
                    errors.append(f"Failed to scrape {source_name}: {str(e)}")
            
            # Remove duplicates based on card name and bank
            unique_cards = self._deduplicate_cards(scraped_cards)
            
            return ScrapingResult(
                task_id=task_id,
                status="success" if unique_cards else "partial",
                data={
                    "cards": unique_cards,
                    "total_cards": len(unique_cards),
                    "sources_scraped": len(source_urls)
                },
                errors=errors,
                scraped_at=datetime.now().isoformat(),
                source_urls=source_urls
            )
            
        except Exception as e:
            logger.error(f"Error in _scrape_credit_cards: {e}")
            raise
    
    async def _scrape_from_source(self, source_name: str, source_config: Dict, parameters: Dict) -> List[Dict]:
        """Scrape credit cards from a specific source"""
        try:
            page = await self.browser_context.new_page()
            cards = []
            
            try:
                # Navigate to source
                await page.goto(source_config["url"], timeout=30000)
                
                # Wait for page to load
                await page.wait_for_load_state("networkidle")
                
                if source_name == "bankbazaar":
                    cards = await self._scrape_bankbazaar(page, parameters)
                elif source_name == "paisabazaar":
                    cards = await self._scrape_paisabazaar(page, parameters)
                elif source_name == "cardexpert":
                    cards = await self._scrape_cardexpert(page, parameters)
                
            finally:
                await page.close()
            
            return cards
            
        except Exception as e:
            logger.error(f"Error scraping from {source_name}: {e}")
            return []
    
    async def _scrape_bankbazaar(self, page: Page, parameters: Dict) -> List[Dict]:
        """Scrape credit cards from BankBazaar"""
        try:
            cards = []
            
            # Wait for card listings to load
            await page.wait_for_selector(".card-item, .product-item, [data-testid*='card']", timeout=10000)
            
            # Extract card information
            card_elements = await page.query_selector_all(".card-item, .product-item")
            
            for element in card_elements[:20]:  # Limit to first 20 cards
                try:
                    # Extract card name
                    card_name_element = await element.query_selector("h3, .card-name, .product-name")
                    card_name = await card_name_element.inner_text() if card_name_element else ""
                    
                    # Extract bank name
                    bank_element = await element.query_selector(".bank-name, .issuer")
                    bank_name = await bank_element.inner_text() if bank_element else ""
                    
                    # Extract annual fee
                    fee_element = await element.query_selector(".annual-fee, .fee")
                    fee_text = await fee_element.inner_text() if fee_element else "0"
                    annual_fee = self._extract_amount_from_text(fee_text)
                    
                    # Extract benefits
                    benefits_elements = await element.query_selector_all(".benefit, .feature")
                    benefits = []
                    for benefit_elem in benefits_elements[:5]:  # Top 5 benefits
                        benefit_text = await benefit_elem.inner_text()
                        if benefit_text.strip():
                            benefits.append(benefit_text.strip())
                    
                    # Extract application URL
                    apply_button = await element.query_selector("a[href*='apply'], .apply-button")
                    apply_url = await apply_button.get_attribute("href") if apply_button else ""
                    
                    if card_name and bank_name:
                        card = {
                            "card_id": self._generate_card_id(bank_name, card_name),
                            "card_name": card_name.strip(),
                            "bank_name": bank_name.strip(),
                            "annual_fee": annual_fee,
                            "joining_fee": annual_fee,  # Assume same as annual fee
                            "benefits": benefits,
                            "application_url": urljoin(page.url, apply_url) if apply_url else "",
                            "source": "bankbazaar",
                            "scraped_at": datetime.now().isoformat()
                        }
                        cards.append(card)
                        
                except Exception as e:
                    logger.warning(f"Error extracting card from element: {e}")
                    continue
            
            return cards
            
        except Exception as e:
            logger.error(f"Error scraping BankBazaar: {e}")
            return []
    
    async def _scrape_paisabazaar(self, page: Page, parameters: Dict) -> List[Dict]:
        """Scrape credit cards from PaisaBazaar"""
        try:
            cards = []
            
            # Wait for card listings
            await page.wait_for_selector(".product-card, .card-list-item", timeout=10000)
            
            # Extract card information
            card_elements = await page.query_selector_all(".product-card, .card-list-item")
            
            for element in card_elements[:20]:
                try:
                    # Similar extraction logic as BankBazaar
                    card_name_element = await element.query_selector("h2, h3, .product-title")
                    card_name = await card_name_element.inner_text() if card_name_element else ""
                    
                    bank_element = await element.query_selector(".bank-name, .issuer-name")
                    bank_name = await bank_element.inner_text() if bank_element else ""
                    
                    # Extract more specific information for PaisaBazaar
                    features_elements = await element.query_selector_all(".feature-item, .benefit-item")
                    benefits = []
                    for feature_elem in features_elements[:5]:
                        feature_text = await feature_elem.inner_text()
                        if feature_text.strip():
                            benefits.append(feature_text.strip())
                    
                    if card_name and bank_name:
                        card = {
                            "card_id": self._generate_card_id(bank_name, card_name),
                            "card_name": card_name.strip(),
                            "bank_name": bank_name.strip(),
                            "annual_fee": 0.0,  # Default, extract if available
                            "joining_fee": 0.0,
                            "benefits": benefits,
                            "application_url": "",
                            "source": "paisabazaar",
                            "scraped_at": datetime.now().isoformat()
                        }
                        cards.append(card)
                        
                except Exception as e:
                    logger.warning(f"Error extracting card from PaisaBazaar element: {e}")
                    continue
            
            return cards
            
        except Exception as e:
            logger.error(f"Error scraping PaisaBazaar: {e}")
            return []
    
    async def _scrape_cardexpert(self, page: Page, parameters: Dict) -> List[Dict]:
        """Scrape credit cards from CardExpert"""
        try:
            cards = []
            
            # CardExpert specific selectors and logic
            await page.wait_for_selector(".card-tile, .card-container", timeout=10000)
            
            card_elements = await page.query_selector_all(".card-tile, .card-container")
            
            for element in card_elements[:15]:  # Smaller limit for CardExpert
                try:
                    card_name_element = await element.query_selector(".card-title, h3")
                    card_name = await card_name_element.inner_text() if card_name_element else ""
                    
                    bank_element = await element.query_selector(".bank-logo, .issuer")
                    bank_name = await bank_element.get_attribute("alt") if bank_element else ""
                    
                    if not bank_name:
                        # Try to extract bank name from card name
                        bank_name = self._extract_bank_from_card_name(card_name)
                    
                    if card_name and bank_name:
                        card = {
                            "card_id": self._generate_card_id(bank_name, card_name),
                            "card_name": card_name.strip(),
                            "bank_name": bank_name.strip(),
                            "annual_fee": 0.0,
                            "joining_fee": 0.0,
                            "benefits": [],
                            "application_url": "",
                            "source": "cardexpert",
                            "scraped_at": datetime.now().isoformat()
                        }
                        cards.append(card)
                        
                except Exception as e:
                    logger.warning(f"Error extracting card from CardExpert element: {e}")
                    continue
            
            return cards
            
        except Exception as e:
            logger.error(f"Error scraping CardExpert: {e}")
            return []
    
    def _extract_amount_from_text(self, text: str) -> float:
        """Extract amount from text (e.g., '₹2,500' -> 2500.0)"""
        try:
            # Remove currency symbols and commas
            clean_text = re.sub(r'[₹,\s]', '', text)
            
            # Extract numbers
            amount_match = re.search(r'(\d+(?:\.\d+)?)', clean_text)
            if amount_match:
                return float(amount_match.group(1))
            
            # Handle 'Free' or 'Nil' cases
            if any(word in text.lower() for word in ['free', 'nil', 'waived', 'zero']):
                return 0.0
                
        except Exception as e:
            logger.warning(f"Error extracting amount from '{text}': {e}")
        
        return 0.0
    
    def _generate_card_id(self, bank_name: str, card_name: str) -> str:
        """Generate unique card ID from bank and card name"""
        clean_bank = re.sub(r'[^a-zA-Z0-9]', '', bank_name.lower())
        clean_card = re.sub(r'[^a-zA-Z0-9]', '', card_name.lower())
        return f"{clean_bank}_{clean_card}"[:50]  # Limit length
    
    def _extract_bank_from_card_name(self, card_name: str) -> str:
        """Extract bank name from card name"""
        indian_banks = [
            "HDFC", "ICICI", "SBI", "Axis", "Kotak", "Yes", "IDFC", "IndusInd",
            "Citi", "Standard Chartered", "HSBC", "American Express", "RBL"
        ]
        
        for bank in indian_banks:
            if bank.lower() in card_name.lower():
                return bank
        
        return "Unknown Bank"
    
    def _deduplicate_cards(self, cards: List[Dict]) -> List[Dict]:
        """Remove duplicate cards based on card name and bank"""
        seen = set()
        unique_cards = []
        
        for card in cards:
            card_key = f"{card['bank_name'].lower()}_{card['card_name'].lower()}"
            if card_key not in seen:
                seen.add(card_key)
                unique_cards.append(card)
        
        return unique_cards
    
    async def _fill_application_form(self, task_id: str, parameters: Dict[str, Any]) -> ScrapingResult:
        """Automatically fill credit card application form"""
        try:
            if not ENABLE_AUTO_FORM_FILLING:
                return ScrapingResult(
                    task_id=task_id,
                    status="failed",
                    data={},
                    errors=["Auto form filling is disabled"],
                    scraped_at=datetime.now().isoformat(),
                    source_urls=[]
                )
            
            bank_name = parameters.get("bank_name", "").lower()
            application_url = BANK_APPLICATION_URLS.get(bank_name, parameters.get("application_url", ""))
            
            if not application_url:
                raise ValueError(f"No application URL found for bank: {bank_name}")
            
            user_data = parameters.get("user_data", {})
            page = await self.browser_context.new_page()
            
            try:
                # Navigate to application form
                await page.goto(application_url, timeout=30000)
                await page.wait_for_load_state("networkidle")
                
                # Fill form based on bank
                filled_fields = await self._fill_bank_specific_form(page, bank_name, user_data)
                
                return ScrapingResult(
                    task_id=task_id,
                    status="success",
                    data={
                        "filled_fields": filled_fields,
                        "form_url": application_url,
                        "next_steps": "Manual verification and submission required"
                    },
                    errors=[],
                    scraped_at=datetime.now().isoformat(),
                    source_urls=[application_url]
                )
                
            finally:
                await page.close()
            
        except Exception as e:
            logger.error(f"Error filling application form: {e}")
            return ScrapingResult(
                task_id=task_id,
                status="failed",
                data={},
                errors=[str(e)],
                scraped_at=datetime.now().isoformat(),
                source_urls=[application_url] if 'application_url' in locals() else []
            )
    
    async def _fill_bank_specific_form(self, page: Page, bank_name: str, user_data: Dict) -> List[str]:
        """Fill bank-specific application form"""
        filled_fields = []
        
        try:
            # Common form fields across banks
            field_mappings = {
                "first_name": ["input[name*='first'], input[id*='first'], input[placeholder*='First']"],
                "last_name": ["input[name*='last'], input[id*='last'], input[placeholder*='Last']"],
                "email": ["input[type='email'], input[name*='email'], input[id*='email']"],
                "phone": ["input[type='tel'], input[name*='phone'], input[name*='mobile']"],
                "pan_number": ["input[name*='pan'], input[id*='pan']"],
                "date_of_birth": ["input[type='date'], input[name*='dob'], input[name*='birth']"],
                "pincode": ["input[name*='pin'], input[name*='postal']"],
                "income": ["input[name*='income'], input[name*='salary']"]
            }
            
            # Fill each field
            for field_name, selectors in field_mappings.items():
                if field_name in user_data:
                    value = user_data[field_name]
                    
                    for selector in selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                await element.fill(str(value))
                                filled_fields.append(f"Filled {field_name}")
                                
                                # Add delay between field fills
                                await asyncio.sleep(FORM_FILLING_DELAY_SECONDS)
                                break
                                
                        except Exception as e:
                            logger.warning(f"Error filling {field_name}: {e}")
                            continue
            
            # Handle dropdowns (employment type, city, etc.)
            if "employment_type" in user_data:
                try:
                    employment_dropdown = await page.query_selector("select[name*='employment'], select[id*='employment']")
                    if employment_dropdown:
                        await employment_dropdown.select_option(value=user_data["employment_type"])
                        filled_fields.append("Selected employment type")
                except Exception as e:
                    logger.warning(f"Error selecting employment type: {e}")
            
        except Exception as e:
            logger.error(f"Error in form filling: {e}")
        
        return filled_fields
    
    async def _track_application_status(self, task_id: str, parameters: Dict[str, Any]) -> ScrapingResult:
        """Track credit card application status"""
        try:
            tracking_number = parameters.get("tracking_number", "")
            application_id = parameters.get("application_id", "")
            
            if not (tracking_number or application_id):
                raise ValueError("Either tracking number or application ID is required")
            
            # This would implement status tracking logic for different banks
            # For now, return a mock response
            
            return ScrapingResult(
                task_id=task_id,
                status="success",
                data={
                    "application_status": "Under Review",
                    "tracking_number": tracking_number,
                    "last_updated": datetime.now().isoformat(),
                    "estimated_decision_date": (datetime.now() + timedelta(days=7)).isoformat()
                },
                errors=[],
                scraped_at=datetime.now().isoformat(),
                source_urls=[]
            )
            
        except Exception as e:
            logger.error(f"Error tracking application status: {e}")
            return ScrapingResult(
                task_id=task_id,
                status="failed",
                data={},
                errors=[str(e)],
                scraped_at=datetime.now().isoformat(),
                source_urls=[]
            )
    
    async def _log_automation_request(self, task_id: str, request: BrowserAutomationRequest):
        """Log automation request for audit purposes"""
        try:
            log_entry = {
                "_id": task_id,
                "user_id": request.jwt_token,
                "task_type": request.task_type,
                "parameters": request.parameters,
                "timestamp": datetime.now().isoformat(),
                "status": "initiated"
            }
            
            await self.automation_logs_collection.insert_one(log_entry)
            
        except Exception as e:
            logger.error(f"Error logging automation request: {e}")
    
    async def _store_scraping_result(self, result: ScrapingResult) -> bool:
        """Store scraping result in database"""
        try:
            result_dict = result.dict()
            result_dict["_id"] = result.task_id
            result_dict["created_at"] = datetime.now().isoformat()
            
            await self.scraping_results_collection.insert_one(result_dict)
            return True
            
        except Exception as e:
            logger.error(f"Error storing scraping result: {e}")
            return False
    
    async def get_scraping_history(self, user_id: str) -> List[Dict]:
        """Get scraping history for a user"""
        try:
            # Get from automation logs
            logs = await self.automation_logs_collection.find(
                {"user_id": user_id},
                sort=[("timestamp", -1)]
            ).to_list(length=20)
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting scraping history: {e}")
            return []
    
    async def get_latest_scraped_cards(self, limit: int = 50) -> List[Dict]:
        """Get latest scraped credit cards"""
        try:
            results = await self.scraping_results_collection.find(
                {"status": "success", "data.cards": {"$exists": True}},
                sort=[("scraped_at", -1)]
            ).to_list(length=10)
            
            all_cards = []
            for result in results:
                cards = result.get("data", {}).get("cards", [])
                all_cards.extend(cards)
            
            # Remove duplicates and return latest cards
            unique_cards = self._deduplicate_cards(all_cards)
            return unique_cards[:limit]
            
        except Exception as e:
            logger.error(f"Error getting latest scraped cards: {e}")
            return []

# Global service instance
browser_automation_service = BrowserAutomationService() 