# Financial Transactions API Documentation

## Overview
This document describes the new GET API endpoint that retrieves all financial transactions from user email data stored in MongoDB.

## Endpoint Details

### GET /financial/transactions/all

**Description**: Retrieves all financial transactions (credit card, debit card, UPI, bank transfers, etc.) for an authenticated user.

**Authentication**: JWT token as query parameter

**Method**: GET

**URL**: `http://your-server.com/financial/transactions/all?jwt_token=YOUR_JWT_TOKEN`

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| jwt_token | string | Yes | JWT authentication token obtained from Google login |

## Response Format

```json
{
  "status": "success",
  "user_info": {
    "user_id": "google_user_id",
    "email": "user@example.com"
  },
  "transactions": {
    "count": 150,
    "total_amount": 75250.50,
    "data": [
      {
        "id": "transaction_id",
        "email_id": "email_reference_id",
        "user_id": "google_user_id",
        "date": "2024-01-15T10:30:00",
        "amount": 1250.00,
        "currency": "INR",
        "transaction_type": "debit",
        "merchant": "Amazon India",
        "description": "Order confirmation",
        "payment_method": "credit_card",
        "account_info": "****1234",
        "transaction_id": "TXN123456789",
        "sender": "noreply@amazon.in",
        "subject": "Your order has been confirmed",
        "snippet": "Thank you for your order...",
        "extracted_at": "2024-01-15T11:00:00",
        "confidence_score": 0.95
      }
    ]
  },
  "analytics": {
    "transaction_types": {
      "debit": 120,
      "credit": 25,
      "refund": 5
    },
    "payment_methods": {
      "credit_card": 80,
      "upi": 45,
      "debit_card": 20,
      "bank_transfer": 5
    },
    "top_merchants": {
      "Amazon India": 25,
      "Swiggy": 18,
      "Paytm": 15,
      "Flipkart": 12,
      "Zomato": 10
    },
    "summary": {
      "period": "5_months",
      "total_transactions": 150,
      "total_amount": 75250.50,
      "average_transaction": 501.67,
      "category_breakdown": {},
      "monthly_trends": {}
    }
  },
  "metadata": {
    "extracted_at": "2024-01-15T11:00:00",
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

## Transaction Types Supported

- **Credit Card Transactions**: Purchases, payments, cashbacks
- **Debit Card Transactions**: ATM withdrawals, POS payments, online purchases
- **UPI Transactions**: Paytm, PhonePe, Google Pay, BHIM transactions
- **Bank Transfers**: NEFT, RTGS, IMPS transfers
- **Online Payments**: E-commerce, bill payments, subscriptions
- **Investment Transactions**: Mutual funds, stocks, SIPs
- **Utility Payments**: Electricity, water, gas, telecom bills
- **Refunds and Cashbacks**: Transaction reversals, promotional cashbacks

## Usage Examples

### Postman
1. Create a new GET request
2. URL: `http://localhost:8001/financial/transactions/all`
3. Add query parameter:
   - Key: `jwt_token`
   - Value: `your_jwt_token_here`
4. Send request

### cURL
```bash
curl "http://localhost:8001/financial/transactions/all?jwt_token=YOUR_JWT_TOKEN"
```

### Python
```python
import requests

response = requests.get(
    'http://localhost:8001/financial/transactions/all',
    params={'jwt_token': 'YOUR_JWT_TOKEN'}
)

if response.status_code == 200:
    data = response.json()
    print(f"Found {data['transactions']['count']} transactions")
    print(f"Total amount: ₹{data['transactions']['total_amount']}")
else:
    print(f"Error: {response.status_code}")
```

### JavaScript/Fetch
```javascript
const jwt_token = 'YOUR_JWT_TOKEN';
const url = `http://localhost:8001/financial/transactions/all?jwt_token=${jwt_token}`;

fetch(url)
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.transactions.count} transactions`);
    console.log(`Total amount: ₹${data.transactions.total_amount}`);
  })
  .catch(error => console.error('Error:', error));
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid JWT token"
}
```

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred while fetching financial transactions: <error_message>"
}
```

## Data Processing

The API processes email data to extract financial transactions using:

1. **Email Filtering**: Identifies financial emails from banks, payment gateways, e-commerce platforms
2. **Content Analysis**: Extracts transaction details using regex patterns and NLP
3. **Data Normalization**: Standardizes amounts, dates, merchant names
4. **Categorization**: Classifies transactions by type, payment method, merchant category
5. **Deduplication**: Removes duplicate transactions from multiple email sources
6. **Analytics Generation**: Calculates summaries, trends, and insights

## Security Features

- JWT token validation for user authentication
- User isolation (users can only access their own data)
- Sensitive data masking (account numbers, card details)
- Secure database queries with proper indexing
- Error handling without exposing internal details

## Testing

Run the test script to validate the endpoint:

```bash
cd backend
python test_financial_api.py
```

## Integration Notes

This endpoint integrates with:
- **Existing Gmail API**: Uses processed email data from MongoDB
- **Authentication System**: Leverages existing JWT token system
- **Financial Agent**: Uses existing transaction extraction algorithms
- **Database**: Queries existing `emails_collection` and user data
- **Mem0 System**: Can be enhanced with memory-based insights

## Performance Considerations

- Default limit of 10,000 transactions (configurable)
- Optimized database queries with proper indexing
- Caching of frequently accessed financial summaries
- Asynchronous processing for large datasets
- Response compression for large transaction lists

## Future Enhancements

1. **Pagination**: Add skip/limit parameters for large datasets
2. **Filtering**: Add date range, amount range, merchant filters
3. **Sorting**: Add sorting by date, amount, merchant
4. **Export**: Add CSV/Excel export functionality
5. **Real-time Updates**: WebSocket support for live transaction updates
6. **Advanced Analytics**: ML-powered spending insights and predictions 