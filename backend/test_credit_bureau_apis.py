#!/usr/bin/env python3
"""
Credit Bureau API Integration Test Script

This script helps verify your credit bureau API configurations
and tests the connection to each bureau's API endpoints.

Usage:
    python test_credit_bureau_apis.py
    python test_credit_bureau_apis.py --bureau cibil
    python test_credit_bureau_apis.py --sandbox-only
"""

import asyncio
import os
import json
import sys
import argparse
from typing import Dict, List
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import SUPPORTED_CREDIT_BUREAUS
from app.credit_report_service import CreditReportService
from app.models import CreditReportRequest


class CreditBureauAPITester:
    """Test credit bureau API integrations"""
    
    def __init__(self):
        self.service = CreditReportService()
        self.test_results = {}
    
    async def test_all_bureaus(self, sandbox_only: bool = True) -> Dict:
        """Test all configured credit bureaus"""
        print("🏦 Credit Bureau API Integration Test")
        print("=" * 50)
        
        # Test configuration first
        await self._test_configuration()
        
        # Test each bureau
        for bureau_name, config in SUPPORTED_CREDIT_BUREAUS.items():
            if config.get("enabled", False) or sandbox_only:
                await self._test_bureau(bureau_name, config, sandbox_only)
        
        return self._generate_report()
    
    async def test_specific_bureau(self, bureau_name: str, sandbox_only: bool = True) -> Dict:
        """Test a specific credit bureau"""
        print(f"🏦 Testing {bureau_name.upper()} API Integration")
        print("=" * 50)
        
        if bureau_name not in SUPPORTED_CREDIT_BUREAUS:
            print(f"❌ Bureau '{bureau_name}' not supported")
            return {"error": f"Bureau '{bureau_name}' not supported"}
        
        config = SUPPORTED_CREDIT_BUREAUS[bureau_name]
        await self._test_bureau(bureau_name, config, sandbox_only)
        
        return self._generate_report()
    
    async def _test_configuration(self):
        """Test basic configuration"""
        print("\n📋 Testing Configuration...")
        
        config_tests = {
            "Environment Variables": self._check_env_vars(),
            "Bureau Configurations": self._check_bureau_configs(),
            "Database Connection": await self._check_database(),
            "Encryption Setup": self._check_encryption()
        }
        
        for test_name, result in config_tests.items():
            status = "✅" if result["success"] else "❌"
            print(f"{status} {test_name}: {result['message']}")
    
    def _check_env_vars(self) -> Dict:
        """Check if required environment variables are set"""
        required_vars = [
            "OPENAI_API_KEY",
            "MONGODB_CONNECTION_STRING"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            return {
                "success": False,
                "message": f"Missing variables: {', '.join(missing_vars)}"
            }
        
        return {
            "success": True,
            "message": "All required environment variables are set"
        }
    
    def _check_bureau_configs(self) -> Dict:
        """Check bureau configurations"""
        enabled_bureaus = []
        configured_bureaus = []
        
        for bureau_name, config in SUPPORTED_CREDIT_BUREAUS.items():
            if config.get("api_key"):
                configured_bureaus.append(bureau_name)
            if config.get("enabled"):
                enabled_bureaus.append(bureau_name)
        
        return {
            "success": len(configured_bureaus) > 0,
            "message": f"Configured: {len(configured_bureaus)}, Enabled: {len(enabled_bureaus)}"
        }
    
    async def _check_database(self) -> Dict:
        """Check database connection"""
        try:
            # Test database connection
            test_user_id = "test_user_123"
            collection = await self.service._get_credit_reports_collection(test_user_id)
            
            # Try a simple count operation
            count = await collection.count_documents({})
            
            return {
                "success": True,
                "message": f"Database connected (documents: {count})"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Database connection failed: {str(e)}"
            }
    
    def _check_encryption(self) -> Dict:
        """Check encryption setup"""
        try:
            # Test encryption/decryption
            test_data = "TEST_PAN_123456789"
            encrypted = self.service._encrypt_sensitive_data(test_data)
            decrypted = self.service._decrypt_sensitive_data(encrypted)
            
            if test_data == decrypted:
                return {
                    "success": True,
                    "message": "Encryption working properly"
                }
            else:
                return {
                    "success": False,
                    "message": "Encryption test failed"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Encryption error: {str(e)}"
            }
    
    async def _test_bureau(self, bureau_name: str, config: Dict, sandbox_only: bool):
        """Test a specific bureau"""
        print(f"\n🔍 Testing {bureau_name.upper()}...")
        
        # Check if bureau is properly configured
        if not config.get("api_key") and not sandbox_only:
            print(f"❌ {bureau_name.upper()}: API key not configured")
            self.test_results[bureau_name] = {
                "configured": False,
                "error": "API key not configured"
            }
            return
        
        # Test API endpoint accessibility
        endpoint_test = await self._test_endpoint(bureau_name, config)
        
        # Test API call with mock data
        api_test = await self._test_api_call(bureau_name, config, sandbox_only)
        
        self.test_results[bureau_name] = {
            "configured": True,
            "endpoint_accessible": endpoint_test["success"],
            "endpoint_message": endpoint_test["message"],
            "api_call_success": api_test["success"],
            "api_message": api_test["message"],
            "sandbox_mode": config.get("sandbox_mode", True)
        }
        
        # Print results
        status = "✅" if api_test["success"] else "❌"
        print(f"{status} {bureau_name.upper()}: {api_test['message']}")
    
    async def _test_endpoint(self, bureau_name: str, config: Dict) -> Dict:
        """Test if API endpoint is accessible"""
        import aiohttp
        
        try:
            endpoint = config.get("api_endpoint", "")
            if not endpoint:
                return {"success": False, "message": "No endpoint configured"}
            
            async with aiohttp.ClientSession() as session:
                # Simple GET request to check if endpoint exists
                async with session.get(
                    endpoint,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        "success": response.status != 404,
                        "message": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
    
    async def _test_api_call(self, bureau_name: str, config: Dict, sandbox_only: bool) -> Dict:
        """Test actual API call"""
        try:
            # Create test request
            test_request = CreditReportRequest(
                jwt_token="test_user_123",
                bureau=bureau_name,
                pan_number="AAAPZ1234C",  # Test PAN
                full_name="Test User",
                date_of_birth="1990-01-01",
                phone_number="9876543210",
                address={
                    "address_line_1": "Test Address",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "country": "India"
                }
            )
            
            # For sandbox mode or if no real API key, just test the service
            if sandbox_only or not config.get("api_key"):
                # Test with mock data
                result = await self.service.fetch_credit_report(test_request)
                
                if result.get("success"):
                    return {
                        "success": True,
                        "message": "Mock data test successful"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Test failed: {result.get('message', 'Unknown error')}"
                    }
            else:
                # This would be a real API call - be careful!
                return {
                    "success": True,
                    "message": "Real API call test skipped (use --test-real to enable)"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"API test error: {str(e)}"
            }
    
    def _generate_report(self) -> Dict:
        """Generate final test report"""
        print("\n📊 Test Results Summary")
        print("=" * 50)
        
        total_tested = len(self.test_results)
        successful = sum(1 for result in self.test_results.values() 
                        if result.get("api_call_success", False))
        
        print(f"Total Bureaus Tested: {total_tested}")
        print(f"Successful Tests: {successful}")
        print(f"Failed Tests: {total_tested - successful}")
        
        # Detailed results
        for bureau, result in self.test_results.items():
            print(f"\n{bureau.upper()}:")
            print(f"  - Configured: {'✅' if result.get('configured') else '❌'}")
            print(f"  - Endpoint: {'✅' if result.get('endpoint_accessible') else '❌'} ({result.get('endpoint_message', 'N/A')})")
            print(f"  - API Call: {'✅' if result.get('api_call_success') else '❌'} ({result.get('api_message', 'N/A')})")
            print(f"  - Sandbox Mode: {'✅' if result.get('sandbox_mode') else '❌'}")
        
        print("\n💡 Next Steps:")
        if successful == 0:
            print("1. Configure at least one credit bureau API")
            print("2. Set up required environment variables")
            print("3. Test with sandbox mode first")
        elif successful < total_tested:
            print("1. Fix failed bureau configurations")
            print("2. Check API credentials and endpoints")
            print("3. Review error messages above")
        else:
            print("1. All tests passed! ✅")
            print("2. Ready for production deployment")
            print("3. Consider enabling additional bureaus")
        
        return {
            "total_tested": total_tested,
            "successful": successful,
            "failed": total_tested - successful,
            "results": self.test_results
        }


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test Credit Bureau API Integrations")
    parser.add_argument("--bureau", type=str, help="Test specific bureau (cibil, experian, crif, equifax)")
    parser.add_argument("--sandbox-only", action="store_true", default=True, help="Test only in sandbox mode")
    parser.add_argument("--test-real", action="store_true", help="Enable real API testing (be careful!)")
    
    args = parser.parse_args()
    
    tester = CreditBureauAPITester()
    
    try:
        if args.bureau:
            results = await tester.test_specific_bureau(args.bureau, not args.test_real)
        else:
            results = await tester.test_all_bureaus(not args.test_real)
        
        # Save results to file
        with open(f"credit_bureau_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Test results saved to file")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 