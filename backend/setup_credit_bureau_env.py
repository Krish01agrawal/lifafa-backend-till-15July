#!/usr/bin/env python3
"""
Credit Bureau Environment Setup Helper

This script helps you set up the required environment variables
for credit bureau API integrations.

Usage:
    python setup_credit_bureau_env.py
    python setup_credit_bureau_env.py --create-env-file
"""

import os
import sys
import argparse
from typing import Dict, List

def print_banner():
    """Print setup banner"""
    print("🏦 Credit Bureau API Environment Setup")
    print("=" * 50)
    print("This script will help you configure environment variables")
    print("for Indian credit bureau integrations.\n")

def check_existing_env() -> Dict[str, bool]:
    """Check which environment variables are already set"""
    env_vars = {
        # Core variables
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "MONGODB_CONNECTION_STRING": bool(os.getenv("MONGODB_CONNECTION_STRING")),
        
        # CIBIL variables
        "CIBIL_API_KEY": bool(os.getenv("CIBIL_API_KEY")),
        "CIBIL_MERCHANT_ID": bool(os.getenv("CIBIL_MERCHANT_ID")),
        "CIBIL_USERNAME": bool(os.getenv("CIBIL_USERNAME")),
        "CIBIL_PASSWORD": bool(os.getenv("CIBIL_PASSWORD")),
        "CIBIL_ENABLED": bool(os.getenv("CIBIL_ENABLED")),
        
        # Experian variables
        "EXPERIAN_API_KEY": bool(os.getenv("EXPERIAN_API_KEY")),
        "EXPERIAN_CLIENT_ID": bool(os.getenv("EXPERIAN_CLIENT_ID")),
        "EXPERIAN_CLIENT_SECRET": bool(os.getenv("EXPERIAN_CLIENT_SECRET")),
        "EXPERIAN_ENABLED": bool(os.getenv("EXPERIAN_ENABLED")),
        
        # CRIF variables
        "CRIF_API_KEY": bool(os.getenv("CRIF_API_KEY")),
        "CRIF_PARTNER_ID": bool(os.getenv("CRIF_PARTNER_ID")),
        "CRIF_ACCESS_TOKEN": bool(os.getenv("CRIF_ACCESS_TOKEN")),
        "CRIF_ENABLED": bool(os.getenv("CRIF_ENABLED")),
        
        # Equifax variables
        "EQUIFAX_API_KEY": bool(os.getenv("EQUIFAX_API_KEY")),
        "EQUIFAX_SUBSCRIBER_ID": bool(os.getenv("EQUIFAX_SUBSCRIBER_ID")),
        "EQUIFAX_SECURITY_CODE": bool(os.getenv("EQUIFAX_SECURITY_CODE")),
        "EQUIFAX_ENABLED": bool(os.getenv("EQUIFAX_ENABLED")),
    }
    
    return env_vars

def print_env_status():
    """Print current environment variable status"""
    print("📋 Current Environment Variable Status:")
    print("-" * 40)
    
    env_vars = check_existing_env()
    
    # Group by category
    categories = {
        "Core Configuration": ["OPENAI_API_KEY", "MONGODB_CONNECTION_STRING"],
        "CIBIL Configuration": ["CIBIL_API_KEY", "CIBIL_MERCHANT_ID", "CIBIL_USERNAME", "CIBIL_PASSWORD", "CIBIL_ENABLED"],
        "Experian Configuration": ["EXPERIAN_API_KEY", "EXPERIAN_CLIENT_ID", "EXPERIAN_CLIENT_SECRET", "EXPERIAN_ENABLED"],
        "CRIF Configuration": ["CRIF_API_KEY", "CRIF_PARTNER_ID", "CRIF_ACCESS_TOKEN", "CRIF_ENABLED"],
        "Equifax Configuration": ["EQUIFAX_API_KEY", "EQUIFAX_SUBSCRIBER_ID", "EQUIFAX_SECURITY_CODE", "EQUIFAX_ENABLED"]
    }
    
    for category, vars_list in categories.items():
        print(f"\n{category}:")
        for var in vars_list:
            status = "✅ SET" if env_vars.get(var, False) else "❌ NOT SET"
            print(f"  {var}: {status}")

def get_bureau_setup_guide(bureau: str) -> Dict:
    """Get setup guide for specific bureau"""
    guides = {
        "cibil": {
            "name": "CIBIL (TransUnion CIBIL)",
            "website": "https://www.cibil.com/business-solutions",
            "contact": "business@cibil.com",
            "phone": "+91-22-6638-4500",
            "required_vars": ["CIBIL_API_KEY", "CIBIL_MERCHANT_ID", "CIBIL_USERNAME", "CIBIL_PASSWORD"],
            "setup_steps": [
                "1. Visit https://www.cibil.com/business-solutions",
                "2. Contact business team at business@cibil.com",
                "3. Complete business registration and KYC",
                "4. Sign API agreement and pay setup fees (~₹50,000)",
                "5. Get API credentials from CIBIL team",
                "6. Test in sandbox environment first"
            ],
            "cost": "₹15-20 per credit report",
            "setup_fee": "₹50,000 - ₹1,00,000"
        },
        "experian": {
            "name": "Experian India",
            "website": "https://www.experian.in/business-services",
            "contact": "business.india@experian.com",
            "phone": "+91-124-4715000",
            "required_vars": ["EXPERIAN_API_KEY", "EXPERIAN_CLIENT_ID", "EXPERIAN_CLIENT_SECRET"],
            "setup_steps": [
                "1. Visit https://www.experian.in/business-services",
                "2. Email business.india@experian.com",
                "3. Complete KYC and business verification",
                "4. Technical integration discussion",
                "5. Contract signing and API provisioning"
            ],
            "cost": "₹10-15 per credit report",
            "setup_fee": "₹30,000 - ₹75,000"
        },
        "crif": {
            "name": "CRIF High Mark",
            "website": "https://www.crifhighmark.com/business",
            "contact": "info@crifhighmark.com",
            "phone": "+91-22-6715-5555",
            "required_vars": ["CRIF_API_KEY", "CRIF_PARTNER_ID", "CRIF_ACCESS_TOKEN"],
            "setup_steps": [
                "1. Visit https://www.crifhighmark.com/business",
                "2. Contact info@crifhighmark.com",
                "3. Business partnership discussion",
                "4. Technical integration setup",
                "5. API credentials provisioning"
            ],
            "cost": "₹8-12 per credit report",
            "setup_fee": "₹25,000 - ₹50,000"
        },
        "equifax": {
            "name": "Equifax India",
            "website": "https://www.equifax.co.in/business",
            "contact": "business.india@equifax.com",
            "phone": "+91-22-6641-7000",
            "required_vars": ["EQUIFAX_API_KEY", "EQUIFAX_SUBSCRIBER_ID", "EQUIFAX_SECURITY_CODE"],
            "setup_steps": [
                "1. Visit https://www.equifax.co.in/business",
                "2. Contact business.india@equifax.com",
                "3. Partnership application and verification",
                "4. API integration testing",
                "5. Production access approval"
            ],
            "cost": "₹10-15 per credit report",
            "setup_fee": "₹30,000 - ₹60,000"
        }
    }
    
    return guides.get(bureau, {})

def print_bureau_guide(bureau: str):
    """Print setup guide for specific bureau"""
    guide = get_bureau_setup_guide(bureau)
    if not guide:
        print(f"❌ No guide available for bureau: {bureau}")
        return
    
    print(f"\n🏦 {guide['name']} Setup Guide")
    print("=" * 50)
    print(f"Website: {guide['website']}")
    print(f"Contact: {guide['contact']}")
    print(f"Phone: {guide['phone']}")
    print(f"Cost per report: {guide['cost']}")
    print(f"Setup fee: {guide['setup_fee']}")
    
    print(f"\n📋 Setup Steps:")
    for step in guide['setup_steps']:
        print(f"  {step}")
    
    print(f"\n🔑 Required Environment Variables:")
    for var in guide['required_vars']:
        print(f"  - {var}")

def create_env_template():
    """Create .env template file"""
    template_content = '''# ============================================================================
# CREDIT BUREAU API CONFIGURATION
# ============================================================================

# Core Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/gmail_chatbot

# ============================================================================
# CIBIL (TransUnion CIBIL) Configuration
# ============================================================================
CIBIL_API_ENDPOINT=https://api.cibil.com/v1
CIBIL_API_KEY=your_cibil_api_key_here
CIBIL_MERCHANT_ID=your_cibil_merchant_id
CIBIL_USERNAME=your_cibil_username
CIBIL_PASSWORD=your_cibil_password
CIBIL_ENABLED=false
CIBIL_SANDBOX=true

# ============================================================================
# Experian India Configuration
# ============================================================================
EXPERIAN_API_ENDPOINT=https://api.experian.in/v1
EXPERIAN_API_KEY=your_experian_api_key_here
EXPERIAN_CLIENT_ID=your_experian_client_id
EXPERIAN_CLIENT_SECRET=your_experian_client_secret
EXPERIAN_ENABLED=false
EXPERIAN_SANDBOX=true

# ============================================================================
# CRIF High Mark Configuration
# ============================================================================
CRIF_API_ENDPOINT=https://api.crifhighmark.com/v1
CRIF_API_KEY=your_crif_api_key_here
CRIF_PARTNER_ID=your_crif_partner_id
CRIF_ACCESS_TOKEN=your_crif_access_token
CRIF_ENABLED=false
CRIF_SANDBOX=true

# ============================================================================
# Equifax India Configuration
# ============================================================================
EQUIFAX_API_ENDPOINT=https://api.equifax.co.in/v1
EQUIFAX_API_KEY=your_equifax_api_key_here
EQUIFAX_SUBSCRIBER_ID=your_equifax_subscriber_id
EQUIFAX_SECURITY_CODE=your_equifax_security_code
EQUIFAX_ENABLED=false
EQUIFAX_SANDBOX=true

# ============================================================================
# Rate Limiting & Cost Control
# ============================================================================
CIBIL_DAILY_LIMIT=100
EXPERIAN_DAILY_LIMIT=100
CRIF_DAILY_LIMIT=100
EQUIFAX_DAILY_LIMIT=100

# Cost per API call (in INR)
CIBIL_COST_PER_CALL=15
EXPERIAN_COST_PER_CALL=12
CRIF_COST_PER_CALL=10
EQUIFAX_COST_PER_CALL=10

# ============================================================================
# Security & Encryption
# ============================================================================
CREDIT_DATA_ENCRYPTION_KEY=your_32_character_encryption_key_here

# ============================================================================
# API Timeouts & Retry Settings
# ============================================================================
CREDIT_API_TIMEOUT=180
CREDIT_API_RETRY_ATTEMPTS=3
CREDIT_API_RETRY_DELAY=5
'''
    
    try:
        with open('.env.template', 'w') as f:
            f.write(template_content)
        print("✅ Environment template created: .env.template")
        print("📝 Copy this file to .env and fill in your API credentials")
        
        # Also create actual .env if it doesn't exist
        if not os.path.exists('.env'):
            with open('.env', 'w') as f:
                f.write(template_content)
            print("✅ Environment file created: .env")
            print("⚠️  Please update .env with your actual API credentials")
        else:
            print("ℹ️  .env file already exists - not overwriting")
            
    except Exception as e:
        print(f"❌ Error creating environment files: {e}")

def print_quick_start_guide():
    """Print quick start guide"""
    print("\n🚀 Quick Start Guide")
    print("=" * 50)
    print("1. Choose your primary credit bureau (recommend CIBIL)")
    print("2. Register with the bureau and get API credentials") 
    print("3. Update your .env file with the credentials")
    print("4. Start with sandbox mode (set BUREAU_SANDBOX=true)")
    print("5. Test the integration using the test script:")
    print("   python test_credit_bureau_apis.py --bureau cibil")
    print("6. Once tested, enable production mode and start using")
    
    print("\n📋 Recommended Bureau Priority:")
    print("1. CIBIL - Market leader, most comprehensive")
    print("2. Experian - Good backup, competitive pricing")
    print("3. CRIF - Lower cost option")
    print("4. Equifax - Additional coverage")
    
    print("\n💰 Cost Estimation:")
    print("- Setup fees: ₹25,000 - ₹1,00,000 per bureau")
    print("- Per report: ₹8 - ₹20 depending on bureau")
    print("- Volume discounts available for 1000+ reports/month")

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Credit Bureau Environment Setup Helper")
    parser.add_argument("--create-env-file", action="store_true", help="Create .env template file")
    parser.add_argument("--bureau-guide", type=str, help="Show setup guide for specific bureau")
    parser.add_argument("--check-status", action="store_true", help="Check current environment status")
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.create_env_file:
        create_env_template()
        return
    
    if args.bureau_guide:
        print_bureau_guide(args.bureau_guide)
        return
    
    if args.check_status:
        print_env_status()
        return
    
    # Default: Show interactive setup
    print_env_status()
    print_quick_start_guide()
    
    print("\n🛠️  Next Steps:")
    print("1. Run: python setup_credit_bureau_env.py --create-env-file")
    print("2. Edit .env file with your API credentials")
    print("3. Run: python test_credit_bureau_apis.py")
    print("4. Check individual bureau guides:")
    print("   python setup_credit_bureau_env.py --bureau-guide cibil")

if __name__ == "__main__":
    main() 