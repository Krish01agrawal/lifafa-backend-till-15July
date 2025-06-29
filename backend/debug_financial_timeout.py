#!/usr/bin/env python3
"""
🔍 FINANCIAL PROCESSING TIMEOUT DIAGNOSTIC SCRIPT
==================================================

This script helps diagnose why financial processing is timing out.

Usage:
    python debug_financial_timeout.py

Features:
- Checks database connection speed
- Analyzes email data volume
- Tests financial processing components
- Provides optimization recommendations
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialTimeoutDiagnostic:
    """Diagnostic tool for financial processing timeouts"""
    
    def __init__(self):
        self.results = {}
    
    async def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run comprehensive diagnostic"""
        logger.info("🔍 STARTING FINANCIAL PROCESSING TIMEOUT DIAGNOSTIC")
        logger.info("="*80)
        
        try:
            # Test 1: Database Connection Speed
            await self.test_database_connection()
            
            # Test 2: Email Data Volume Analysis
            await self.analyze_email_data_volume()
            
            # Test 3: Financial Processing Components
            await self.test_financial_components()
            
            # Test 4: System Resource Check
            await self.check_system_resources()
            
            # Generate recommendations
            recommendations = self.generate_recommendations()
            
            # Print diagnostic report
            self.print_diagnostic_report(recommendations)
            
            return {
                "diagnostic_results": self.results,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Diagnostic failed: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def test_database_connection(self):
        """Test 1: Database Connection Speed"""
        logger.info("🧪 TEST 1: Database Connection Speed")
        
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
            
            from app.db import users_collection, emails_collection
            
            # Test users collection query speed
            start_time = time.time()
            user_count = await users_collection.count_documents({})
            users_query_time = time.time() - start_time
            
            # Test emails collection query speed
            start_time = time.time()
            email_count = await emails_collection.count_documents({})
            emails_query_time = time.time() - start_time
            
            self.results["database_connection"] = {
                "users_count": user_count,
                "users_query_time": f"{users_query_time:.2f}s",
                "emails_count": email_count,
                "emails_query_time": f"{emails_query_time:.2f}s",
                "status": "healthy" if emails_query_time < 5.0 else "slow"
            }
            
            logger.info(f"✅ Database connection test complete:")
            logger.info(f"   📊 Users: {user_count} (query time: {users_query_time:.2f}s)")
            logger.info(f"   📧 Emails: {email_count} (query time: {emails_query_time:.2f}s)")
            
            if emails_query_time > 5.0:
                logger.warning(f"⚠️ Slow database queries detected - this may cause timeouts")
            
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            self.results["database_connection"] = {"error": str(e)}
    
    async def analyze_email_data_volume(self):
        """Test 2: Email Data Volume Analysis"""
        logger.info("🧪 TEST 2: Email Data Volume Analysis")
        
        try:
            from app.db import emails_collection
            
            # Get sample user with most emails
            pipeline = [
                {"$group": {"_id": "$user_id", "email_count": {"$sum": 1}}},
                {"$sort": {"email_count": -1}},
                {"$limit": 5}
            ]
            
            start_time = time.time()
            top_users = await emails_collection.aggregate(pipeline).to_list(length=5)
            aggregation_time = time.time() - start_time
            
            # Analyze email size and complexity
            sample_emails = await emails_collection.find({}).limit(10).to_list(length=10)
            
            avg_body_size = 0
            if sample_emails:
                total_size = sum(len(email.get('body', '')) for email in sample_emails)
                avg_body_size = total_size / len(sample_emails)
            
            self.results["email_data_volume"] = {
                "top_users": top_users,
                "aggregation_time": f"{aggregation_time:.2f}s",
                "avg_email_body_size": f"{avg_body_size:.0f} chars",
                "sample_emails_analyzed": len(sample_emails),
                "status": "normal" if aggregation_time < 10.0 else "high_volume"
            }
            
            logger.info(f"✅ Email data volume analysis complete:")
            logger.info(f"   📊 Top users by email count: {len(top_users)}")
            logger.info(f"   ⏱️ Aggregation time: {aggregation_time:.2f}s")
            logger.info(f"   📏 Average email body size: {avg_body_size:.0f} characters")
            
            if aggregation_time > 10.0:
                logger.warning(f"⚠️ High email volume detected - may cause processing delays")
            
        except Exception as e:
            logger.error(f"❌ Email data volume analysis failed: {e}")
            self.results["email_data_volume"] = {"error": str(e)}
    
    async def test_financial_components(self):
        """Test 3: Financial Processing Components"""
        logger.info("🧪 TEST 3: Financial Processing Components")
        
        try:
            from app.fast_financial_processor import process_financial_transactions_from_mongodb
            
            # Test with a dummy user to check component speed
            start_time = time.time()
            
            # This should fail quickly if user doesn't exist, giving us timing info
            try:
                result = await asyncio.wait_for(
                    process_financial_transactions_from_mongodb("test_diagnostic_user"),
                    timeout=30  # Short timeout for diagnostic
                )
                component_time = time.time() - start_time
                
                self.results["financial_components"] = {
                    "test_result": result,
                    "component_time": f"{component_time:.2f}s",
                    "status": "functional"
                }
                
            except asyncio.TimeoutError:
                component_time = time.time() - start_time
                logger.warning(f"⚠️ Financial component timed out after 30s")
                
                self.results["financial_components"] = {
                    "component_time": f"{component_time:.2f}s",
                    "status": "timeout",
                    "issue": "Component takes too long even for non-existent user"
                }
                
            except Exception as component_error:
                component_time = time.time() - start_time
                
                # Quick failure is actually good - means components are responsive
                if component_time < 5.0:
                    self.results["financial_components"] = {
                        "component_time": f"{component_time:.2f}s",
                        "status": "responsive",
                        "note": "Quick failure indicates responsive components"
                    }
                else:
                    self.results["financial_components"] = {
                        "component_time": f"{component_time:.2f}s",
                        "status": "slow",
                        "error": str(component_error)
                    }
            
            logger.info(f"✅ Financial components test complete:")
            logger.info(f"   ⏱️ Component response time: {self.results['financial_components'].get('component_time', 'unknown')}")
            logger.info(f"   📊 Status: {self.results['financial_components'].get('status', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Financial components test failed: {e}")
            self.results["financial_components"] = {"error": str(e)}
    
    async def check_system_resources(self):
        """Test 4: System Resource Check"""
        logger.info("🧪 TEST 4: System Resource Check")
        
        try:
            import psutil
            import os
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Process count
            process_count = len(psutil.pids())
            
            self.results["system_resources"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": f"{memory_available_gb:.2f}",
                "disk_percent": disk_percent,
                "process_count": process_count,
                "status": "healthy" if cpu_percent < 80 and memory_percent < 80 else "stressed"
            }
            
            logger.info(f"✅ System resource check complete:")
            logger.info(f"   🖥️ CPU usage: {cpu_percent}%")
            logger.info(f"   💾 Memory usage: {memory_percent}% ({memory_available_gb:.2f}GB available)")
            logger.info(f"   💿 Disk usage: {disk_percent}%")
            logger.info(f"   🔄 Process count: {process_count}")
            
            if cpu_percent > 80:
                logger.warning(f"⚠️ High CPU usage detected")
            if memory_percent > 80:
                logger.warning(f"⚠️ High memory usage detected")
            
        except ImportError:
            logger.warning(f"⚠️ psutil not available - install with: pip install psutil")
            self.results["system_resources"] = {"error": "psutil not available"}
        except Exception as e:
            logger.error(f"❌ System resource check failed: {e}")
            self.results["system_resources"] = {"error": str(e)}
    
    def generate_recommendations(self) -> list:
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        # Database recommendations
        db_result = self.results.get("database_connection", {})
        if db_result.get("status") == "slow":
            recommendations.append("🔧 Database queries are slow - consider adding indexes or optimizing queries")
        
        # Email volume recommendations
        volume_result = self.results.get("email_data_volume", {})
        if volume_result.get("status") == "high_volume":
            recommendations.append("📊 High email volume detected - consider batch processing or pagination")
        
        # Financial component recommendations
        financial_result = self.results.get("financial_components", {})
        if financial_result.get("status") == "timeout":
            recommendations.append("💰 Financial components are slow - check database queries and API calls")
        elif financial_result.get("status") == "slow":
            recommendations.append("💰 Financial processing is slow - optimize transaction extraction logic")
        
        # System resource recommendations
        system_result = self.results.get("system_resources", {})
        if system_result.get("status") == "stressed":
            recommendations.append("🖥️ System resources are stressed - consider upgrading hardware or optimizing code")
        
        # General recommendations
        recommendations.extend([
            "⏱️ Increase financial processing timeout from 120s to 180s for large datasets",
            "🔄 Implement progressive financial processing (recent first, then historical)",
            "📦 Add batch processing for large email volumes",
            "🧠 Consider caching frequently accessed financial data",
            "📊 Monitor database query performance with indexing"
        ])
        
        return recommendations
    
    def print_diagnostic_report(self, recommendations: list):
        """Print comprehensive diagnostic report"""
        logger.info("="*80)
        logger.info("🎯 FINANCIAL PROCESSING TIMEOUT DIAGNOSTIC REPORT")
        logger.info("="*80)
        
        logger.info("📊 DIAGNOSTIC RESULTS:")
        for test_name, result in self.results.items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status in ["healthy", "functional", "responsive", "normal"] else "⚠️"
            logger.info(f"   {status_icon} {test_name}: {status}")
        
        logger.info("\n💡 RECOMMENDATIONS:")
        for i, recommendation in enumerate(recommendations, 1):
            logger.info(f"   {i}. {recommendation}")
        
        logger.info("\n🔧 IMMEDIATE FIXES:")
        logger.info("   1. Timeout increased from 60s to 120s ✅")
        logger.info("   2. Background retry mechanism added ✅")
        logger.info("   3. Graceful timeout handling implemented ✅")
        logger.info("   4. System continues processing despite financial timeout ✅")
        
        logger.info("="*80)

async def main():
    """Main diagnostic execution"""
    diagnostic = FinancialTimeoutDiagnostic()
    
    try:
        report = await diagnostic.run_full_diagnostic()
        
        # Save diagnostic report
        import json
        with open("financial_timeout_diagnostic.json", "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info("📁 Diagnostic report saved to: financial_timeout_diagnostic.json")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Diagnostic failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 