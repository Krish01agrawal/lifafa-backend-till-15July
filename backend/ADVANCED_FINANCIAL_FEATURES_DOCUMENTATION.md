# Advanced Financial Features Documentation

## Overview

This document provides comprehensive information about the new advanced financial features added to the Gmail Chatbot API. These features transform the application into a complete financial analysis platform with credit monitoring, statement analysis, and personalized recommendations.

## 📊 Feature Overview

### 1. Credit Report Integration
- **Purpose**: Fetch and analyze credit reports from Indian credit bureaus
- **Supported Bureaus**: CIBIL, Experian, CRIF, Equifax
- **AI Analysis**: GPT-4 powered insights and recommendations

### 2. Bank Statement Processing
- **Purpose**: Analyze bank statements for financial insights
- **Supported Formats**: PDF, CSV, Excel (XLSX, XLS)
- **AI Analysis**: Spending patterns, income analysis, financial health scoring

### 3. Credit Card Recommendations
- **Purpose**: Personalized credit card suggestions based on financial profile
- **Database**: 50+ popular Indian credit cards
- **Features**: Benefit calculations, comparison matrix, application assistance

### 4. Browser Automation
- **Purpose**: Web scraping and automated form filling
- **Capabilities**: Card data scraping, application form automation
- **Technology**: Playwright-based automation

## 🚀 API Endpoints

### Credit Report APIs

#### Fetch Credit Report
```
POST /credit-report/fetch
```

**Request Body:**
```json
{
  "jwt_token": "your_jwt_token",
  "bureau": "cibil",
  "pan_number": "ABCDE1234F",
  "date_of_birth": "1990-01-01",
  "phone_number": "9876543210",
  "full_name": "John Doe",
  "address": {
    "street": "123 Main St",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400001"
  },
  "consent_given": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Credit report fetched successfully",
  "data": {
    "report_id": "abc123...",
    "credit_score_info": {
      "score": 750,
      "range_max": 900,
      "range_min": 300,
      "factors_affecting_score": [...]
    },
    "accounts": [...],
    "enquiries": [...]
  },
  "source": "api"
}
```

#### Generate Credit Insights
```
POST /credit-report/insights/{report_id}
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
  "success": true,
  "insights": {
    "overall_credit_health": "Good",
    "key_strengths": [...],
    "areas_for_improvement": [...],
    "action_recommendations": [...],
    "score_improvement_tips": [...]
  }
}
```

#### Get Credit Report History
```
GET /credit-report/history
Authorization: Bearer your_jwt_token
```

### Bank Statement APIs

#### Upload Bank Statement
```
POST /statement/upload
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: Bank statement file (PDF/CSV/Excel)
- `jwt_token`: Authentication token
- `bank_name`: Bank name (optional)
- `account_number`: Account number (optional)
- `statement_period_from`: Start date (YYYY-MM-DD)
- `statement_period_to`: End date (YYYY-MM-DD)

**Response:**
```json
{
  "success": true,
  "statement_id": "stmt_123...",
  "transactions_count": 156,
  "insights": {
    "spending_analysis": {...},
    "income_analysis": {...},
    "financial_habits": {...}
  }
}
```

#### Get Statement History
```
GET /statement/history
Authorization: Bearer your_jwt_token
```

#### Get Statement Insights
```
GET /statement/insights/{statement_id}
Authorization: Bearer your_jwt_token
```

### Credit Card Recommendation APIs

#### Get Personalized Recommendations
```
POST /credit-cards/recommendations
```

**Request Body:**
```json
{
  "jwt_token": "your_jwt_token",
  "income_range": "50000-100000",
  "credit_score_range": "650-750",
  "preferred_category": "Cashback",
  "existing_cards": ["hdfc_regalia"],
  "spending_categories": {
    "dining": 5000,
    "fuel": 3000,
    "grocery": 8000,
    "online": 10000
  },
  "age": 28,
  "employment_type": "Salaried",
  "city": "Mumbai"
}
```

**Response:**
```json
{
  "success": true,
  "recommendations": {
    "recommended_cards": [...],
    "personalized_reasons": {...},
    "estimated_benefits": {...},
    "comparison_matrix": {...}
  }
}
```

#### Initiate Card Application
```
POST /credit-cards/apply
Content-Type: multipart/form-data
```

**Form Data:**
- `card_id`: Credit card ID
- `jwt_token`: Authentication token
- `pre_filled_data`: JSON string with user data

#### Get Complete Credit Health Report
```
GET /credit-health/complete-report
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
  "success": true,
  "credit_health_report": {
    "credit_score": 750,
    "credit_report_summary": {...},
    "statement_insights": {...},
    "recommended_cards": [...],
    "financial_goals": [...],
    "action_plan": [...],
    "risk_assessment": {...}
  }
}
```

### Browser Automation APIs

#### Scrape Credit Cards
```
POST /automation/scrape-cards
```

**Request Body:**
```json
{
  "jwt_token": "your_jwt_token",
  "task_type": "scrape_cards",
  "parameters": {
    "sources": ["bankbazaar", "paisabazaar"],
    "card_type": "cashback",
    "max_cards": 50
  }
}
```

#### Fill Application Form
```
POST /automation/fill-application
```

**Request Body:**
```json
{
  "jwt_token": "your_jwt_token",
  "task_type": "fill_application",
  "parameters": {
    "bank_name": "hdfc",
    "application_url": "https://...",
    "user_data": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "9876543210",
      "pan_number": "ABCDE1234F",
      "income": "600000"
    }
  }
}
```

#### Get Latest Scraped Cards
```
GET /automation/scraped-cards/latest?limit=50
```

### Comprehensive Dashboard API

#### Get Complete Financial Dashboard
```
GET /financial/dashboard/complete
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
  "success": true,
  "dashboard": {
    "user_id": "user123",
    "credit_reports": [...],
    "bank_statements": [...],
    "card_recommendations": [...],
    "card_applications": [...],
    "summary": {
      "total_credit_reports": 2,
      "total_statements": 5,
      "total_recommendations": 3,
      "total_applications": 1,
      "latest_credit_score": 750
    }
  }
}
```

## 🔧 Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Credit Bureau API Keys (optional - will use sandbox mode if not provided)
CIBIL_API_KEY=your_cibil_api_key
CIBIL_API_ENDPOINT=https://api.cibil.com/v1
CIBIL_ENABLED=false
CIBIL_SANDBOX=true

EXPERIAN_API_KEY=your_experian_api_key
EXPERIAN_API_ENDPOINT=https://api.experian.in/v1
EXPERIAN_ENABLED=false
EXPERIAN_SANDBOX=true

CRIF_API_KEY=your_crif_api_key
CRIF_API_ENDPOINT=https://api.crifhighmark.com/v1
CRIF_ENABLED=false
CRIF_SANDBOX=true

EQUIFAX_API_KEY=your_equifax_api_key
EQUIFAX_API_ENDPOINT=https://api.equifax.co.in/v1
EQUIFAX_ENABLED=false
EQUIFAX_SANDBOX=true

# Encryption key for sensitive data
CREDIT_DATA_ENCRYPTION_KEY=your_encryption_key_here

# OpenAI API Key (required for AI analysis)
OPENAI_API_KEY=your_openai_api_key
```

### Feature Toggles

```python
# In config.py - these are already configured
ENABLE_CREDIT_BUREAU_APIS = True
ENABLE_STATEMENT_PROCESSING = True
ENABLE_BROWSER_AUTOMATION = True
ENABLE_AUTO_FORM_FILLING = True
ENABLE_DATA_ENCRYPTION = True
```

## 📋 Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Update Environment Variables

Copy the environment variables above to your `.env` file.

### 4. Start the Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 Usage Examples

### Example 1: Complete Financial Analysis Workflow

```python
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "your_jwt_token"

# 1. Upload bank statement
with open("bank_statement.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "jwt_token": TOKEN,
        "bank_name": "HDFC Bank",
        "statement_period_from": "2024-01-01",
        "statement_period_to": "2024-01-31"
    }
    response = requests.post(f"{BASE_URL}/statement/upload", files=files, data=data)
    statement_result = response.json()

# 2. Fetch credit report
credit_request = {
    "jwt_token": TOKEN,
    "bureau": "cibil",
    "pan_number": "ABCDE1234F",
    "date_of_birth": "1990-01-01",
    "phone_number": "9876543210",
    "full_name": "John Doe",
    "address": {
        "street": "123 Main St",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001"
    }
}
response = requests.post(f"{BASE_URL}/credit-report/fetch", json=credit_request)
credit_result = response.json()

# 3. Get personalized card recommendations
card_criteria = {
    "jwt_token": TOKEN,
    "income_range": "50000-100000",
    "credit_score_range": "650-750",
    "spending_categories": {
        "dining": 5000,
        "fuel": 3000,
        "online": 10000
    },
    "age": 28,
    "employment_type": "Salaried",
    "city": "Mumbai"
}
response = requests.post(f"{BASE_URL}/credit-cards/recommendations", json=card_criteria)
recommendations = response.json()

# 4. Get complete financial dashboard
headers = {"Authorization": f"Bearer {TOKEN}"}
response = requests.get(f"{BASE_URL}/financial/dashboard/complete", headers=headers)
dashboard = response.json()

print("Financial Analysis Complete!")
print(f"Credit Score: {dashboard['dashboard']['summary']['latest_credit_score']}")
print(f"Recommended Cards: {len(recommendations['recommendations']['recommended_cards'])}")
```

### Example 2: Automated Card Application

```python
# 1. Get card recommendations
recommendations_response = requests.post(f"{BASE_URL}/credit-cards/recommendations", json=card_criteria)
recommendations = recommendations_response.json()

# 2. Select best card
best_card = recommendations['recommendations']['recommended_cards'][0]
card_id = best_card['card_id']

# 3. Initiate application with pre-filled data
application_data = {
    "card_id": card_id,
    "jwt_token": TOKEN,
    "pre_filled_data": json.dumps({
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "9876543210",
        "pan_number": "ABCDE1234F",
        "income": "600000"
    })
}
response = requests.post(f"{BASE_URL}/credit-cards/apply", data=application_data)
application = response.json()

# 4. Use browser automation to fill form (optional)
automation_request = {
    "jwt_token": TOKEN,
    "task_type": "fill_application",
    "parameters": {
        "bank_name": best_card['bank_name'].lower().replace(" ", ""),
        "application_url": application['application']['application_url'],
        "user_data": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "pan_number": "ABCDE1234F",
            "income": "600000"
        }
    }
}
response = requests.post(f"{BASE_URL}/automation/fill-application", json=automation_request)
automation_result = response.json()
```

## 🔐 Security Considerations

### Data Encryption
- All sensitive data (PAN, phone numbers, account numbers) is encrypted before storage
- Uses Fernet symmetric encryption with rotating keys
- Credit reports are cached for 24 hours maximum

### API Rate Limiting
- Credit report fetching: 3 reports per user per month
- Browser automation: Rate limited per source
- Statement processing: File size limited to 50MB

### Compliance
- GDPR-compliant data handling
- Data retention policies enforced
- User consent tracking for credit reports
- Audit logs for all sensitive operations

## 📊 Database Schema

### New Collections

#### credit_reports
```json
{
  "_id": "report_id",
  "user_id": "user123",
  "bureau_name": "cibil",
  "report_date": "2024-01-15T10:30:00Z",
  "credit_score_info": {...},
  "accounts": [...],
  "enquiries": [...],
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### bank_statements
```json
{
  "_id": "statement_id", 
  "user_id": "user123",
  "bank_name": "HDFC Bank",
  "account_number": "****1234",
  "transactions": [...],
  "uploaded_at": "2024-01-15T10:30:00Z"
}
```

#### credit_cards
```json
{
  "_id": "card_id",
  "card_name": "HDFC Regalia",
  "bank_name": "HDFC Bank",
  "annual_fee": 2500,
  "reward_rate": {...},
  "benefits": [...],
  "eligibility_criteria": {...}
}
```

## 🚨 Error Handling

### Common Error Responses

#### Invalid JWT Token
```json
{
  "detail": "Invalid JWT token",
  "status_code": 401
}
```

#### Rate Limit Exceeded
```json
{
  "success": false,
  "error": "Monthly limit of 3 credit reports exceeded"
}
```

#### File Processing Error
```json
{
  "success": false,
  "error": "No transactions found in the statement"
}
```

#### Service Unavailable
```json
{
  "success": false,
  "error": "Credit bureau service temporarily unavailable"
}
```

## 📈 Performance Optimization

### Caching Strategy
- Credit reports: 24-hour cache
- Statement insights: 12-hour cache  
- Card recommendations: 4-hour cache
- Scraped card data: 1-hour cache

### Async Processing
- All I/O operations are asynchronous
- Background processing for large statements
- Parallel data fetching for dashboard

### Database Optimization
- Indexed queries for fast retrieval
- Aggregation pipelines for analytics
- Sharded collections for scalability

## 🔍 Monitoring and Logging

### Health Check Endpoint
```
GET /financial/health
```

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_status": "healthy",
  "services": {
    "credit_reports": {"status": "healthy", "total_reports": 150},
    "statement_processor": {"status": "healthy", "total_statements": 89},
    "credit_card_service": {"status": "healthy", "total_cards": 45}
  }
}
```

### Logging Levels
- **INFO**: Normal operations, successful processing
- **WARNING**: Rate limits, service degradation
- **ERROR**: Processing failures, API errors
- **DEBUG**: Detailed processing information

## 🆘 Troubleshooting

### Common Issues

#### Credit Report API Not Working
- Check if API keys are configured
- Verify sandbox mode settings
- Ensure monthly limits not exceeded

#### PDF Statement Processing Fails
- Verify file size under 50MB
- Check PDF is not password protected
- Try different extraction engines (pdfplumber vs camelot)

#### Browser Automation Timeout
- Increase timeout values in config
- Check internet connectivity
- Verify target websites are accessible

#### Missing Dependencies
- Run `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`

### Debug Commands

```bash
# Test credit report service
python -c "
from app.credit_report_service import credit_report_service
import asyncio
result = asyncio.run(credit_report_service.get_user_credit_reports('test_user'))
print(result)
"

# Test statement processor
python -c "
from app.statement_processor import statement_processor
import asyncio
statements = asyncio.run(statement_processor.get_user_statements('test_user'))
print(f'Found {len(statements)} statements')
"
```

## 📞 Support

For technical support or feature requests, please contact the development team or create an issue in the project repository.

## 🎉 Conclusion

These advanced financial features transform your Gmail Chatbot into a comprehensive financial analysis platform. Users can now:

1. **Monitor Credit Health**: Regular credit report analysis with AI insights
2. **Analyze Spending**: Detailed statement analysis with categorization
3. **Optimize Credit Cards**: Personalized recommendations and benefit calculations
4. **Automate Applications**: Streamlined card application process

The system is designed to be secure, scalable, and user-friendly, providing enterprise-grade financial analysis capabilities. 