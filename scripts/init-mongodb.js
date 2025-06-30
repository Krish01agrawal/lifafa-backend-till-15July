// ============================================================================
// Gmail Intelligence Platform - MongoDB Initialization
// ============================================================================
// This script initializes the MongoDB database with proper indexes and collections

print('🚀 Initializing Gmail Intelligence MongoDB...');

// Switch to the gmail_intelligence database
db = db.getSiblingDB('gmail_intelligence');

print('📁 Creating collections and indexes...');

// ============================================================================
// USERS COLLECTION
// ============================================================================
print('👥 Setting up users collection...');

// Create users collection if it doesn't exist
db.createCollection('users');

// Create indexes for users collection
db.users.createIndex({ "user_id": 1 }, { unique: true, name: "idx_user_id" });
db.users.createIndex({ "email": 1 }, { unique: true, name: "idx_email" });
db.users.createIndex({ "last_sync_timestamp": 1 }, { name: "idx_last_sync" });
db.users.createIndex({ "initial_gmailData_sync": 1, "background_sync_needed": 1 }, { name: "idx_sync_status" });
db.users.createIndex({ "created_at": 1 }, { name: "idx_created_at" });

// ============================================================================
// EMAILS COLLECTION
// ============================================================================
print('📧 Setting up emails collection...');

// Create emails collection
db.createCollection('emails');

// Create indexes for emails collection
db.emails.createIndex({ "user_id": 1, "id": 1 }, { unique: true, name: "idx_user_email_id" });
db.emails.createIndex({ "user_id": 1, "date": -1 }, { name: "idx_user_date" });
db.emails.createIndex({ "user_id": 1, "sender": 1 }, { name: "idx_user_sender" });
db.emails.createIndex({ "user_id": 1, "category": 1 }, { name: "idx_user_category" });
db.emails.createIndex({ "user_id": 1, "subcategory": 1 }, { name: "idx_user_subcategory" });
db.emails.createIndex({ "user_id": 1, "merchant": 1 }, { name: "idx_user_merchant" });
db.emails.createIndex({ "user_id": 1, "amount": 1 }, { name: "idx_user_amount" });
db.emails.createIndex({ "user_id": 1, "payment_method": 1 }, { name: "idx_user_payment_method" });
db.emails.createIndex({ "processed_at": 1 }, { name: "idx_processed_at" });
db.emails.createIndex({ "mem0_stored": 1 }, { name: "idx_mem0_stored" });

// Text search index for email content
db.emails.createIndex({ 
  "subject": "text", 
  "snippet": "text", 
  "body": "text" 
}, { 
  name: "idx_email_text_search",
  weights: { "subject": 3, "snippet": 2, "body": 1 }
});

// ============================================================================
// FINANCIAL COLLECTIONS
// ============================================================================
print('💰 Setting up financial collections...');

// Financial transactions collection
db.createCollection('financial_transactions');
db.financial_transactions.createIndex({ "user_id": 1, "date": -1 }, { name: "idx_user_transaction_date" });
db.financial_transactions.createIndex({ "user_id": 1, "category": 1 }, { name: "idx_user_transaction_category" });
db.financial_transactions.createIndex({ "user_id": 1, "merchant": 1 }, { name: "idx_user_transaction_merchant" });
db.financial_transactions.createIndex({ "user_id": 1, "amount": 1 }, { name: "idx_user_transaction_amount" });
db.financial_transactions.createIndex({ "email_id": 1 }, { name: "idx_transaction_email_id" });

// ============================================================================
// CREDIT COLLECTIONS
// ============================================================================
print('🏦 Setting up credit collections...');

// Credit reports collection
db.createCollection('credit_reports');
db.credit_reports.createIndex({ "user_id": 1, "bureau": 1, "generated_at": -1 }, { name: "idx_user_credit_report" });
db.credit_reports.createIndex({ "report_id": 1 }, { unique: true, name: "idx_credit_report_id" });
db.credit_reports.createIndex({ "user_id": 1, "credit_score.score": -1 }, { name: "idx_user_credit_score" });

// Credit cards collection
db.createCollection('credit_cards');
db.credit_cards.createIndex({ "card_id": 1 }, { unique: true, name: "idx_card_id" });
db.credit_cards.createIndex({ "bank_name": 1 }, { name: "idx_bank_name" });
db.credit_cards.createIndex({ "annual_fee": 1 }, { name: "idx_annual_fee" });
db.credit_cards.createIndex({ "source": 1, "scraped_at": -1 }, { name: "idx_card_source_date" });

// Credit card applications collection
db.createCollection('credit_card_applications');
db.credit_card_applications.createIndex({ "user_id": 1, "application_date": -1 }, { name: "idx_user_applications" });
db.credit_card_applications.createIndex({ "application_id": 1 }, { unique: true, name: "idx_application_id" });
db.credit_card_applications.createIndex({ "card_id": 1 }, { name: "idx_application_card" });
db.credit_card_applications.createIndex({ "status": 1 }, { name: "idx_application_status" });

// ============================================================================
// STATEMENT COLLECTIONS
// ============================================================================
print('📊 Setting up statement collections...');

// Bank statements collection
db.createCollection('bank_statements');
db.bank_statements.createIndex({ "user_id": 1, "uploaded_at": -1 }, { name: "idx_user_statements" });
db.bank_statements.createIndex({ "statement_id": 1 }, { unique: true, name: "idx_statement_id" });
db.bank_statements.createIndex({ "bank_name": 1 }, { name: "idx_statement_bank" });
db.bank_statements.createIndex({ "account_number": 1 }, { name: "idx_account_number" });

// Statement insights collection
db.createCollection('statement_insights');
db.statement_insights.createIndex({ "user_id": 1, "statement_id": 1 }, { unique: true, name: "idx_user_statement_insights" });
db.statement_insights.createIndex({ "generated_at": -1 }, { name: "idx_insights_generated_at" });

// ============================================================================
// AUTOMATION COLLECTIONS
// ============================================================================
print('🤖 Setting up automation collections...');

// Browser automation tasks collection
db.createCollection('automation_tasks');
db.automation_tasks.createIndex({ "user_id": 1, "created_at": -1 }, { name: "idx_user_automation_tasks" });
db.automation_tasks.createIndex({ "task_id": 1 }, { unique: true, name: "idx_task_id" });
db.automation_tasks.createIndex({ "task_type": 1, "status": 1 }, { name: "idx_task_type_status" });
db.automation_tasks.createIndex({ "status": 1, "created_at": -1 }, { name: "idx_task_status_date" });

// ============================================================================
// SYSTEM COLLECTIONS
// ============================================================================
print('⚙️ Setting up system collections...');

// Application logs collection (for monitoring)
db.createCollection('app_logs', {
  capped: true,
  size: 100000000, // 100MB
  max: 100000 // 100k documents
});
db.app_logs.createIndex({ "timestamp": 1 }, { name: "idx_log_timestamp" });
db.app_logs.createIndex({ "level": 1 }, { name: "idx_log_level" });
db.app_logs.createIndex({ "user_id": 1 }, { name: "idx_log_user" });

// Performance metrics collection
db.createCollection('performance_metrics');
db.performance_metrics.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 604800, name: "idx_metrics_ttl" }); // 7 days TTL
db.performance_metrics.createIndex({ "metric_type": 1, "timestamp": -1 }, { name: "idx_metrics_type_time" });

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================
print('🔧 Creating helper functions...');

// Function to get user statistics
db.system.js.save({
  _id: "getUserStats",
  value: function(userId) {
    var stats = {
      user_id: userId,
      total_emails: db.emails.countDocuments({user_id: userId}),
      financial_transactions: db.financial_transactions.countDocuments({user_id: userId}),
      credit_reports: db.credit_reports.countDocuments({user_id: userId}),
      bank_statements: db.bank_statements.countDocuments({user_id: userId}),
      automation_tasks: db.automation_tasks.countDocuments({user_id: userId})
    };
    
    // Get latest sync info
    var user = db.users.findOne({user_id: userId});
    if (user) {
      stats.last_sync = user.last_sync_timestamp;
      stats.sync_status = {
        dashboard_ready: user.dashboard_ready || false,
        initial_sync: user.initial_gmailData_sync || false,
        historical_sync: user.historical_sync_completed || false
      };
    }
    
    return stats;
  }
});

// Function to cleanup old data
db.system.js.save({
  _id: "cleanupOldData",
  value: function(daysOld) {
    var cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysOld);
    
    var result = {
      automation_tasks_deleted: db.automation_tasks.deleteMany({
        created_at: { $lt: cutoffDate },
        status: { $in: ["completed", "failed"] }
      }).deletedCount,
      
      old_logs_deleted: db.app_logs.deleteMany({
        timestamp: { $lt: cutoffDate },
        level: { $ne: "ERROR" }
      }).deletedCount
    };
    
    return result;
  }
});

// ============================================================================
// COMPLETION
// ============================================================================
print('✅ MongoDB initialization completed successfully!');
print('📊 Collections created:');
print('   - users (with user_id, email indexes)');
print('   - emails (with user_id, date, category, text search indexes)');
print('   - financial_transactions (with user_id, date, category indexes)');
print('   - credit_reports (with user_id, bureau, score indexes)');
print('   - credit_cards (with card_id, bank, fee indexes)');
print('   - credit_card_applications (with user_id, status indexes)');
print('   - bank_statements (with user_id, bank, account indexes)');
print('   - statement_insights (with user_id, statement_id indexes)');
print('   - automation_tasks (with user_id, task_type, status indexes)');
print('   - app_logs (capped collection with TTL)');
print('   - performance_metrics (with TTL)');
print('🔧 Helper functions available: getUserStats(), cleanupOldData()');
print('🚀 Gmail Intelligence database is ready for use!');

// Set up sample data (optional, for testing)
// Uncomment the following lines if you want to insert sample data
/*
print('📝 Inserting sample data for testing...');

// Sample user
db.users.insertOne({
  user_id: "test_user_123",
  email: "test@example.com",
  name: "Test User",
  picture: "https://example.com/avatar.jpg",
  dashboard_ready: false,
  initial_gmailData_sync: false,
  historical_sync_completed: false,
  background_sync_needed: true,
  complete_financial_ready: false,
  financial_analysis_completed: false,
  recent_financial_transactions: 0,
  created_at: new ISODate(),
  last_sync_timestamp: new ISODate()
});

print('✅ Sample data inserted');
*/ 