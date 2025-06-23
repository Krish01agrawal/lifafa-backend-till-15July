# Financial API Endpoints Documentation

## Overview
This document describes the complete financial transaction API system with two main endpoints:

1. **POST /financial/process-from-emails** - Fast processing from MongoDB emails
2. **GET /financial/transactions/all** - Retrieve all processed transactions

## 🚀 API Endpoints

### 1. Fast Financial Processing

**POST /financial/process-from-emails**

**Description**: Processes financial transactions from emails already stored in MongoDB. Much faster than Gmail API processing.

**Authentication**: JWT token in request body

**Request:**
```http
POST http://localhost:8001/financial/process-from-emails
Content-Type: application/json

{
  "jwt_token": "your_jwt_token_here"
}
```

**Response:**
```json
{
  "message": "Fast financial transaction processing completed successfully",
  "processing_method": "mongodb_emails",
  "speed": "fast",
  "data": {
    "status": "success",
    "user_id": "117694049755408407575",
    "transactions_found": 34,
    "total_amount": 41304.37,
    "period": "all_stored_emails",
    "processing_method": "fast_mongodb",
    "summary": {
      "user_id": "117694049755408407575",
      "period": "all_stored_emails",
      "total_transactions": 34,
      "total_amount": 41304.37,
      "average_transaction": 1214.83,
      "merchant_breakdown": {
        "HDFC Bank": 21818.00,
        "Uber": 10457.02,
        "Daily": 1382.55
      },
      "category_breakdown": {
        "upi": 13450.50,
        "bank_transfer": 8200.00,
        "debit_card": 5500.00
      }
    }
  }
}
```

### 2. Retrieve Financial Transactions

**GET /financial/transactions/all**

**Description**: Retrieves all processed financial transactions for an authenticated user.

**Authentication**: JWT token as query parameter

**Request:**
```http
GET http://localhost:8001/financial/transactions/all?jwt_token=your_jwt_token_here
```

**Response:**
```json
{
  "status": "success",
  "user_info": {
    "user_id": "117694049755408407575",
    "email": "user@example.com"
  },
  "transactions": {
    "count": 34,
    "total_amount": 41304.37,
    "data": [
      {
        "id": "117694049755408407575_email123_1719148234",
        "email_id": "email123",
        "user_id": "117694049755408407575",
        "date": "Fri, 20 Jun 2025 20:16:37 +0530",
        "amount": 577.0,
        "currency": "INR",
        "transaction_type": "debit",
        "merchant": "HDFC Bank",
        "description": "UPI Transaction Alert",
        "payment_method": "upi",
        "account_info": "****4685",
        "transaction_id": "TXN123456789",
        "sender": "alerts@hdfcbank.net",
        "subject": "UPI Transaction Alert",
        "snippet": "Dear Customer, Rs.577.00 has been debited...",
        "extracted_at": "2025-06-23T15:02:30.371876",
        "confidence_score": 0.8
      }
    ]
  },
  "analytics": {
    "transaction_types": {
      "debit": 27,
      "credit": 4,
      "refund": 3
    },
    "payment_methods": {
      "upi": 13,
      "bank_transfer": 4,
      "debit_card": 5,
      "unknown": 11,
      "credit_card": 1
    },
    "top_merchants": {
      "HDFC Bank": 21818.00,
      "Uber": 10457.02,
      "Daily": 1382.55,
      "Hi": 2709.00,
      "Yourstory": 2239.80
    },
    "summary": {
      "period": "all_stored_emails",
      "total_transactions": 34,
      "total_amount": 41304.37,
      "average_transaction": 1214.83
    }
  },
  "metadata": {
    "extracted_at": "2025-06-23T15:02:30.371876",
    "data_includes": [
      "credit_card_transactions",
      "debit_card_transactions",
      "upi_transactions",
      "bank_transfers",
      "online_payments",
      "subscription_payments",
      "refunds_and_cashbacks",
      "bill_payments",
      "investment_transactions"
    ]
  }
}
```

## 🔄 Complete Workflow

### Step 1: Process Financial Transactions
```bash
# Call processing endpoint first
curl -X POST http://localhost:8001/financial/process-from-emails \
  -H "Content-Type: application/json" \
  -d '{"jwt_token": "your_jwt_token_here"}'
```

### Step 2: Retrieve Processed Transactions
```bash
# Get all processed transactions
curl "http://localhost:8001/financial/transactions/all?jwt_token=your_jwt_token_here"
```

## 📊 Supported Transaction Types

- **Credit Card Transactions**: Purchases, payments, cashbacks
- **Debit Card Transactions**: ATM withdrawals, POS payments, online purchases
- **UPI Transactions**: Paytm, PhonePe, Google Pay, BHIM transactions
- **Bank Transfers**: NEFT, RTGS, IMPS transfers
- **Online Payments**: E-commerce, bill payments, subscriptions
- **Investment Transactions**: Mutual funds, stocks, SIPs
- **Utility Payments**: Electricity, water, gas, telecom bills
- **Refunds and Cashbacks**: Transaction reversals, promotional cashbacks

## 🧪 Testing

### Option 1: Use Test Script
```bash
cd backend
python3 test_financial_api_endpoints.py
```

### Option 2: Manual Postman Testing

1. **Process Financial Transactions:**
   - Method: POST
   - URL: `http://localhost:8001/financial/process-from-emails`
   - Body (JSON): `{"jwt_token": "your_jwt_token"}`

2. **Get Financial Transactions:**
   - Method: GET
   - URL: `http://localhost:8001/financial/transactions/all`
   - Query Parameter: `jwt_token=your_jwt_token`

## ⚡ Performance Comparison

| Feature | Fast Processing (/process-from-emails) | Slow Processing (/financial/process) |
|---------|---------------------------------------|-------------------------------------|
| **Data Source** | MongoDB emails | Gmail API |
| **Speed** | 5-10 seconds | 30-60+ minutes |
| **Network** | No external calls | 1500+ Gmail API calls |
| **Rate Limits** | None | Gmail API limits |
| **Reliability** | High | Timeout issues |
| **Use Case** | Testing & Development | Production with fresh data |

## 🔒 Security Features

- JWT token validation for user authentication
- User data isolation (users can only access their own data)
- Sensitive data masking (account numbers, transaction IDs)
- Secure database queries with proper indexing
- Error handling without exposing internal details

## 📈 Analytics Features

The API provides comprehensive analytics:

- **Transaction Summaries**: Count, total amount, averages
- **Merchant Analysis**: Top merchants by transaction volume
- **Payment Method Breakdown**: UPI, cards, bank transfers distribution
- **Transaction Type Analysis**: Debit, credit, refund categorization
- **Temporal Trends**: Monthly spending patterns
- **Confidence Scoring**: Data extraction reliability metrics

## 🚨 Error Handling

### Common Error Responses

**401 Unauthorized**
```json
{
  "detail": "Invalid JWT token"
}
```

**404 Not Found**
```json
{
  "detail": "User not found"
}
```

**500 Internal Server Error**
```json
{
  "detail": "An unexpected error occurred during fast financial processing: <error_message>"
}
```

## 🔧 Integration Notes

### Backend Integration
- Uses existing MongoDB connection (`app.db`)
- Integrates with existing JWT authentication system
- Stores data in `financial_transactions` and `financial_summaries` collections
- Compatible with existing `/financial/summary` and `/financial/transactions` endpoints

### Frontend Integration
- RESTful API design for easy frontend integration
- Structured JSON responses for visualization
- Comprehensive error handling
- CORS support for web applications

## 🚀 Production Deployment

### Environment Variables
```env
MONGO_URI=your_mongodb_connection_string
JWT_SECRET=your_jwt_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Database Collections
- `emails` - Raw email data
- `financial_transactions` - Processed transaction data
- `financial_summaries` - Aggregated financial summaries
- `users` - User authentication and status

### Monitoring
- Log transaction processing performance
- Monitor API response times
- Track error rates and user activity
- Set up alerts for processing failures

## 📝 Changelog

### Version 1.0
- Initial implementation of fast financial processing
- MongoDB-based transaction extraction
- Comprehensive analytics and summaries
- JWT authentication integration
- Error handling and logging 