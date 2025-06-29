# Credit Bureau API Integration Setup Guide

## 🏦 **Supported Credit Bureaus in India**

This guide helps you configure API integrations with the four major credit bureaus in India:

1. **CIBIL (TransUnion CIBIL)** - Market leader, ~70% market share
2. **Experian India** - Second largest, comprehensive reports
3. **CRIF High Mark** - Strong in commercial credit
4. **Equifax India** - Global presence, detailed analytics

## 🔧 **Environment Variables Configuration**

Create a `.env` file in your backend directory:

```bash
# ============================================================================
# CREDIT BUREAU API CONFIGURATION
# ============================================================================

# CIBIL (TransUnion CIBIL) - Primary Credit Bureau in India
CIBIL_API_ENDPOINT=https://api.cibil.com/v1
CIBIL_API_KEY=your_cibil_api_key_here
CIBIL_MERCHANT_ID=your_cibil_merchant_id
CIBIL_USERNAME=your_cibil_username
CIBIL_PASSWORD=your_cibil_password
CIBIL_ENABLED=false
CIBIL_SANDBOX=true

# Experian India - Second largest credit bureau
EXPERIAN_API_ENDPOINT=https://api.experian.in/v1
EXPERIAN_API_KEY=your_experian_api_key_here
EXPERIAN_CLIENT_ID=your_experian_client_id
EXPERIAN_CLIENT_SECRET=your_experian_client_secret
EXPERIAN_ENABLED=false
EXPERIAN_SANDBOX=true

# CRIF High Mark - Third credit bureau
CRIF_API_ENDPOINT=https://api.crifhighmark.com/v1
CRIF_API_KEY=your_crif_api_key_here
CRIF_PARTNER_ID=your_crif_partner_id
CRIF_ACCESS_TOKEN=your_crif_access_token
CRIF_ENABLED=false
CRIF_SANDBOX=true

# Equifax India - Fourth major credit bureau
EQUIFAX_API_ENDPOINT=https://api.equifax.co.in/v1
EQUIFAX_API_KEY=your_equifax_api_key_here
EQUIFAX_SUBSCRIBER_ID=your_equifax_subscriber_id
EQUIFAX_SECURITY_CODE=your_equifax_security_code
EQUIFAX_ENABLED=false
EQUIFAX_SANDBOX=true

# Rate Limits and Costs
CIBIL_DAILY_LIMIT=100
EXPERIAN_DAILY_LIMIT=100
CRIF_DAILY_LIMIT=100
EQUIFAX_DAILY_LIMIT=100

# Cost per API call (in INR)
CIBIL_COST_PER_CALL=15
EXPERIAN_COST_PER_CALL=12
CRIF_COST_PER_CALL=10
EQUIFAX_COST_PER_CALL=10
```

## 🚀 **Step-by-Step Setup Process**

### **1. CIBIL (TransUnion CIBIL) Setup**

**Registration Process:**
1. Visit: https://www.cibil.com/business-solutions
2. Contact their B2B team: business@cibil.com
3. Fill out partnership application
4. Provide business registration documents
5. Sign API agreement and pay setup fees (~₹50,000)

**Required Documents:**
- GST Certificate
- Business Registration Certificate
- PAN Card of Company
- Bank Account Details
- Data Security Compliance Certificate

**API Access:**
- **Sandbox URL**: `https://sandbox.cibil.com/v1`
- **Production URL**: `https://api.cibil.com/v1`
- **Cost**: ₹15-20 per credit report
- **Rate Limit**: 100 requests/day (default)

### **2. Experian India Setup**

**Registration Process:**
1. Visit: https://www.experian.in/business-services
2. Email: business.india@experian.com
3. Complete KYC and business verification
4. Technical integration discussion
5. Contract signing and API provisioning

**API Access:**
- **Sandbox URL**: `https://sandbox.experian.in/v1`
- **Production URL**: `https://api.experian.in/v1`
- **Cost**: ₹10-15 per credit report
- **Rate Limit**: 150 requests/day (default)

### **3. CRIF High Mark Setup**

**Registration Process:**
1. Visit: https://www.crifhighmark.com/business
2. Contact: info@crifhighmark.com
3. Business partnership discussion
4. Technical integration setup
5. API credentials provisioning

**API Access:**
- **Sandbox URL**: `https://sandbox.crifhighmark.com/v1`
- **Production URL**: `https://api.crifhighmark.com/v1`
- **Cost**: ₹8-12 per credit report
- **Rate Limit**: 200 requests/day (default)

### **4. Equifax India Setup**

**Registration Process:**
1. Visit: https://www.equifax.co.in/business
2. Contact: business.india@equifax.com
3. Partnership application and verification
4. API integration testing
5. Production access approval

**API Access:**
- **Sandbox URL**: `https://sandbox.equifax.co.in/v1`
- **Production URL**: `https://api.equifax.co.in/v1`
- **Cost**: ₹10-15 per credit report
- **Rate Limit**: 100 requests/day (default)

## 🔐 **Security & Compliance Requirements**

### **Mandatory Compliance:**
1. **Data Security Standards**: ISO 27001 certification
2. **RBI Guidelines**: Follow RBI guidelines for credit information companies
3. **Data Privacy**: GDPR-equivalent data protection measures
4. **Encryption**: End-to-end encryption for sensitive data
5. **Audit Trail**: Complete logging of all API calls

### **Technical Requirements:**
- SSL/TLS encryption for all API calls
- IP whitelisting for production access
- Webhook endpoints for async processing
- Data retention policies (max 12 months)
- User consent management system

## 💰 **Cost Structure & Budgeting**

### **Setup Costs (One-time):**
- CIBIL: ₹50,000 - ₹1,00,000
- Experian: ₹30,000 - ₹75,000
- CRIF: ₹25,000 - ₹50,000
- Equifax: ₹30,000 - ₹60,000

### **Per-Report Costs:**
- CIBIL: ₹15-20 per report
- Experian: ₹10-15 per report
- CRIF: ₹8-12 per report
- Equifax: ₹10-15 per report

### **Volume Discounts:**
- 1,000+ reports/month: 10-15% discount
- 5,000+ reports/month: 15-25% discount
- 10,000+ reports/month: 25-35% discount

## 🧪 **Testing & Development**

### **Sandbox Testing:**
All bureaus provide sandbox environments for testing:

```bash
# Enable sandbox mode in .env
CIBIL_SANDBOX=true
EXPERIAN_SANDBOX=true
CRIF_SANDBOX=true
EQUIFAX_SANDBOX=true
```

### **Test API Calls:**
```python
# Test CIBIL API
POST /credit-report/fetch
{
    "bureau": "cibil",
    "pan_number": "AAAPZ1234C",
    "full_name": "Test User",
    "date_of_birth": "1990-01-01",
    "phone_number": "9876543210",
    "address": "Test Address, Mumbai"
}
```

## 📋 **Implementation Checklist**

### **Phase 1: Basic Setup**
- [ ] Register with at least one credit bureau (recommend CIBIL)
- [ ] Get sandbox access and test credentials
- [ ] Configure environment variables
- [ ] Test basic API integration
- [ ] Implement error handling and logging

### **Phase 2: Production Ready**
- [ ] Complete compliance documentation
- [ ] Get production API credentials
- [ ] Implement rate limiting and cost controls
- [ ] Set up monitoring and alerting
- [ ] Create user consent workflow

### **Phase 3: Scale & Optimize**
- [ ] Integrate with multiple bureaus
- [ ] Implement intelligent bureau selection
- [ ] Set up automated cost monitoring
- [ ] Create analytics dashboard
- [ ] Optimize for volume discounts

## 🔄 **API Implementation Status**

The current implementation includes:

✅ **Ready:** Mock data generation for testing
✅ **Ready:** Database schema and models
✅ **Ready:** API endpoints and validation
✅ **Ready:** Security and encryption
✅ **Ready:** Rate limiting and cost controls

🔄 **Pending:** Real API integration (requires credentials)
🔄 **Pending:** Production compliance setup
🔄 **Pending:** Webhook handling for async processing

## 📞 **Contact Information**

### **Bureau Contact Details:**

**CIBIL:**
- Email: business@cibil.com
- Phone: +91-22-6638-4500
- Business Hours: 9 AM - 6 PM IST

**Experian:**
- Email: business.india@experian.com
- Phone: +91-124-4715000
- Business Hours: 9 AM - 6 PM IST

**CRIF High Mark:**
- Email: info@crifhighmark.com
- Phone: +91-22-6715-5555
- Business Hours: 9 AM - 6 PM IST

**Equifax:**
- Email: business.india@equifax.com
- Phone: +91-22-6641-7000
- Business Hours: 9 AM - 6 PM IST

## ⚠️ **Important Notes**

1. **Regulatory Compliance**: Ensure you have proper licenses to access and process credit data
2. **User Consent**: Always get explicit user consent before fetching credit reports
3. **Data Retention**: Follow strict data retention and deletion policies
4. **Cost Management**: Monitor API usage to avoid unexpected costs
5. **Backup Strategy**: Always have multiple bureau integrations for redundancy

## 🛠️ **Next Steps**

1. Choose your primary bureau (recommend starting with CIBIL)
2. Contact their business team with your use case
3. Complete the registration and compliance process
4. Get sandbox credentials and test the integration
5. Move to production after thorough testing

For technical support during implementation, refer to the `credit_report_service.py` file where the actual API calls are implemented. 