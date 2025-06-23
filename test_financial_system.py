#!/usr/bin/env python3
"""
Financial Transaction System Testing Script
==========================================

This script tests the newly implemented Gmail Financial Transactions system
to ensure all components work correctly before production deployment.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_imports():
    """Test that all new financial modules can be imported successfully"""
    print("🔍 Testing Module Imports...")
    
    try:
        # Test financial agent imports
        from app.financial_agent import (
            TransactionData, 
            FinancialSummary, 
            FinancialTransactionFilter,
            TransactionExtractor,
            FinancialAnalytics,
            fetch_extended_financial_emails,
            process_financial_transactions_for_user,
            get_financial_summary,
            get_financial_transactions
        )
        print("✅ financial_agent.py - All imports successful")
        
        # Test financial mem0 agent imports
        from app.financial_mem0_agent import (
            financial_detector,
            financial_extractor,
            detect_financial_transactions_with_ai,
            process_financial_intelligence_for_user
        )
        print("✅ financial_mem0_agent.py - All imports successful")
        
        # Test existing system integration
        from app.mem0_agent_agno import EmailMessage, query_mem0
        from app.db import users_collection, emails_collection
        from app.auth import verify_google_token, create_jwt_token, decode_jwt_token
        print("✅ Existing system integration - All imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

async def test_data_models():
    """Test the new data models and their validation"""
    print("\n📊 Testing Data Models...")
    
    try:
        from app.financial_agent import TransactionData, FinancialSummary
        
        # Test TransactionData model
        transaction = TransactionData(
            id="test_123",
            email_id="email_456",
            user_id="user_789",
            date=datetime.now(),
            amount=1500.50,
            currency="INR",
            transaction_type="debit",
            merchant="Swiggy",
            description="Food delivery order",
            payment_method="upi",
            transaction_id="TXN123456",
            sender="noreply@swiggy.in",
            subject="Order Confirmed",
            snippet="Your order has been confirmed",
            confidence_score=0.95
        )
        print("✅ TransactionData model - Validation successful")
        print(f"   Sample: {transaction.merchant} - {transaction.currency} {transaction.amount}")
        
        # Test FinancialSummary model
        summary = FinancialSummary(
            user_id="user_789",
            period="5_months",
            total_transactions=100,
            total_amount=45000.00,
            average_transaction=450.00,
            category_breakdown={"food": 15000, "shopping": 20000, "transport": 10000},
            merchant_breakdown={"Swiggy": 8000, "Amazon": 12000, "Uber": 5000},
            monthly_trends={"2024-07": 9000, "2024-08": 8500, "2024-09": 9200}
        )
        print("✅ FinancialSummary model - Validation successful")
        print(f"   Sample: {summary.total_transactions} transactions, {summary.total_amount} total")
        
        return True
        
    except Exception as e:
        print(f"❌ Data Model Error: {e}")
        return False

async def test_financial_filter():
    """Test the financial transaction filter logic"""
    print("\n🔍 Testing Financial Transaction Filter...")
    
    try:
        from app.financial_agent import FinancialTransactionFilter
        from app.mem0_agent_agno import EmailMessage
        
        filter_engine = FinancialTransactionFilter()
        
        # Test cases for financial email detection
        test_emails = [
            # Positive cases (should be detected as financial)
            EmailMessage(
                id="1",
                subject="Payment of ₹1,500 successful - Swiggy",
                sender="noreply@swiggy.in",
                snippet="Your payment has been processed",
                body="Amount charged: ₹1,500 via UPI",
                date="2024-12-15"
            ),
            EmailMessage(
                id="2", 
                subject="Transaction Alert",
                sender="alerts@hdfcbank.net",
                snippet="Rs. 2,400 debited from your account",
                body="Your account ending 1234 has been debited for Rs. 2,400",
                date="2024-12-15"
            ),
            # Negative cases (should NOT be detected as financial)
            EmailMessage(
                id="3",
                subject="Welcome to our newsletter",
                sender="marketing@company.com", 
                snippet="Thanks for subscribing to our updates",
                body="We're excited to have you as a subscriber",
                date="2024-12-15"
            )
        ]
        
        results = []
        for email in test_emails:
            is_financial, confidence = filter_engine.is_financial_transaction(email)
            results.append({
                "email_id": email.id,
                "subject": email.subject[:30] + "...",
                "is_financial": is_financial,
                "confidence": confidence
            })
            
        # Validate results
        assert results[0]["is_financial"] == True, "First email should be detected as financial"
        assert results[1]["is_financial"] == True, "Second email should be detected as financial"
        assert results[2]["is_financial"] == False, "Third email should NOT be detected as financial"
        
        print("✅ Financial Filter - All test cases passed")
        for result in results:
            status = "✅" if result["is_financial"] else "❌"
            print(f"   {status} {result['subject']} - Confidence: {result['confidence']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Financial Filter Error: {e}")
        return False

async def test_transaction_extractor():
    """Test the transaction data extraction logic"""
    print("\n💰 Testing Transaction Data Extractor...")
    
    try:
        from app.financial_agent import TransactionExtractor
        from app.mem0_agent_agno import EmailMessage
        
        extractor = TransactionExtractor()
        
        # Test email with financial data
        test_email = EmailMessage(
            id="test_email_123",
            subject="Payment Confirmation - Swiggy Order",
            sender="noreply@swiggy.in",
            snippet="Your payment of ₹1,250 has been processed",
            body="""
            Dear Customer,
            
            Your order has been confirmed!
            
            Order Details:
            Amount: ₹1,250.00
            Payment Method: UPI
            Transaction ID: TXN987654321
            Date: 15-12-2024
            Merchant: Swiggy
            
            Thank you for choosing Swiggy!
            """,
            date="Mon, 15 Dec 2024 14:30:00 +0530"
        )
        
        # Extract transaction data
        transaction = extractor.extract_transaction_data(test_email, "test_user_123")
        
        if transaction:
            print("✅ Transaction Extraction - Successful")
            print(f"   Amount: {transaction.currency} {transaction.amount}")
            print(f"   Merchant: {transaction.merchant}")
            print(f"   Payment Method: {transaction.payment_method}")
            print(f"   Transaction Type: {transaction.transaction_type}")
            print(f"   Confidence: {transaction.confidence_score}")
            
            # Validate extracted data
            assert transaction.amount is not None, "Amount should be extracted"
            assert transaction.currency is not None, "Currency should be extracted" 
            assert transaction.merchant is not None, "Merchant should be extracted"
            
        else:
            print("❌ Transaction Extraction - Failed to extract data")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Transaction Extractor Error: {e}")
        return False

async def test_analytics_engine():
    """Test the financial analytics engine"""
    print("\n📊 Testing Financial Analytics Engine...")
    
    try:
        from app.financial_agent import FinancialAnalytics, TransactionData
        from datetime import datetime, timedelta
        
        analytics = FinancialAnalytics()
        
        # Create sample transaction data
        sample_transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        # Sample transactions over the last month
        transactions_data = [
            {"amount": 1200, "merchant": "Swiggy", "method": "upi", "type": "food_delivery"},
            {"amount": 2500, "merchant": "Amazon", "method": "card", "type": "shopping"},
            {"amount": 800, "merchant": "Uber", "method": "upi", "type": "transportation"},
            {"amount": 1500, "merchant": "Zomato", "method": "upi", "type": "food_delivery"},
            {"amount": 3200, "merchant": "Flipkart", "method": "card", "type": "shopping"},
        ]
        
        for i, data in enumerate(transactions_data):
            transaction = TransactionData(
                id=f"test_{i}",
                email_id=f"email_{i}",
                user_id="test_user",
                date=base_date + timedelta(days=i*5),
                amount=data["amount"],
                currency="INR",
                transaction_type="debit",
                merchant=data["merchant"],
                payment_method=data["method"],
                sender=f"noreply@{data['merchant'].lower()}.com",
                subject=f"Transaction from {data['merchant']}",
                snippet=f"Payment of ₹{data['amount']}",
                confidence_score=0.9
            )
            sample_transactions.append(transaction)
        
        # Generate financial summary
        summary = analytics.generate_financial_summary("test_user", sample_transactions)
        
        print("✅ Financial Analytics - Summary generated successfully")
        print(f"   Total Transactions: {summary.total_transactions}")
        print(f"   Total Amount: ₹{summary.total_amount:,.2f}")
        print(f"   Average Transaction: ₹{summary.average_transaction:,.2f}")
        print(f"   Payment Methods: {list(summary.category_breakdown.keys())}")
        print(f"   Merchants: {list(summary.merchant_breakdown.keys())}")
        
        # Validate analytics
        assert summary.total_transactions == len(sample_transactions), "Transaction count should match"
        assert summary.total_amount > 0, "Total amount should be positive"
        assert len(summary.merchant_breakdown) > 0, "Should have merchant breakdown"
        
        return True
        
    except Exception as e:
        print(f"❌ Analytics Engine Error: {e}")
        return False

async def test_database_connectivity():
    """Test MongoDB database connectivity"""
    print("\n🗄️ Testing Database Connectivity...")
    
    try:
        from app.db import users_collection, emails_collection
        
        # Test basic database operations
        test_user = {
            "user_id": "financial_test_user",
            "email": "test@financial.com", 
            "name": "Financial Test User",
            "financial_test": True
        }
        
        # Insert test user
        result = await users_collection.insert_one(test_user)
        print(f"✅ Database Insert - User inserted with ID: {result.inserted_id}")
        
        # Retrieve test user
        retrieved_user = await users_collection.find_one({"user_id": "financial_test_user"})
        assert retrieved_user is not None, "User should be retrievable"
        print("✅ Database Retrieve - User retrieved successfully")
        
        # Clean up test data
        await users_collection.delete_one({"user_id": "financial_test_user"})
        print("✅ Database Cleanup - Test data removed")
        
        return True
        
    except Exception as e:
        print(f"❌ Database Connectivity Error: {e}")
        return False

async def test_api_integration():
    """Test API endpoint integration (without actual server)"""
    print("\n🔌 Testing API Integration...")
    
    try:
        # Import the new financial functions from main.py
        import app.main as main_module
        
        # Check if new endpoints are properly defined
        app = main_module.app
        routes = [route.path for route in app.routes]
        
        expected_financial_routes = [
            "/financial/process",
            "/financial/summary", 
            "/financial/transactions",
            "/financial/analyze"
        ]
        
        for route in expected_financial_routes:
            if route in routes:
                print(f"✅ API Route - {route} is properly registered")
            else:
                print(f"❌ API Route - {route} is missing")
                return False
        
        # Test model imports
        from app.main import FinancialProcessingRequest, FinancialQueryRequest
        
        # Test model validation
        financial_request = FinancialProcessingRequest(jwt_token="test_token")
        assert financial_request.jwt_token == "test_token", "Request model validation failed"
        
        print("✅ API Integration - All endpoints and models properly configured")
        return True
        
    except Exception as e:
        print(f"❌ API Integration Error: {e}")
        return False

async def run_comprehensive_test():
    """Run all tests and provide a comprehensive report"""
    print("🚀 STARTING COMPREHENSIVE FINANCIAL SYSTEM TESTING")
    print("=" * 60)
    
    test_results = {}
    
    # Run all test suites
    test_suites = [
        ("Module Imports", test_imports),
        ("Data Models", test_data_models),
        ("Financial Filter", test_financial_filter),
        ("Transaction Extractor", test_transaction_extractor),
        ("Analytics Engine", test_analytics_engine),
        ("Database Connectivity", test_database_connectivity),
        ("API Integration", test_api_integration),
    ]
    
    for test_name, test_func in test_suites:
        try:
            result = await test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} - Critical Error: {e}")
            test_results[test_name] = False
    
    # Generate test report
    print("\n" + "=" * 60)
    print("📋 COMPREHENSIVE TEST REPORT")
    print("=" * 60)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 OVERALL RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Financial system is ready for production.")
        return True
    else:
        print("⚠️ Some tests failed. Please review and fix issues before deployment.")
        return False

if __name__ == "__main__":
    # Run the comprehensive test suite
    success = asyncio.run(run_comprehensive_test())
    
    if success:
        print("\n🚀 NEXT STEPS:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("2. Test the financial endpoints with a real user")
        print("3. Integrate with your frontend for visualization")
        print("4. Deploy to production")
    else:
        print("\n🔧 REQUIRED ACTIONS:")
        print("1. Fix the failing tests above")
        print("2. Re-run this test script")
        print("3. Proceed only after all tests pass")
    
    sys.exit(0 if success else 1) 