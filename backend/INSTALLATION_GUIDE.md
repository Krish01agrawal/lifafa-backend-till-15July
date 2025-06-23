# Installation Guide for Scalability Features

## 📦 **New Dependencies**

The scalability features require one additional Python package:

### **Install psutil for System Monitoring:**

```bash
# In your virtual environment
pip install psutil==6.1.0

# Or install all dependencies
pip install -r requirements.txt
```

## 🚀 **Quick Setup**

1. **Install Dependencies:**
   ```bash
   cd backend
   pip install psutil==6.1.0
   ```

2. **Test Configuration:**
   ```bash
   python -c "from app.config import CONFIG; print('✅ Config loaded!')"
   ```

3. **Start Backend:**
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

4. **Test Health Endpoint:**
   ```bash
   curl http://localhost:8001/health
   ```

## ✅ **Verification**

If everything is working correctly, you should see:
- Configuration loaded messages
- Scalability middleware active
- Health endpoint returning system metrics

## 🔧 **Environment Variables**

Optional environment variables for customization:

```bash
# .env file
CONCURRENT_USERS_LIMIT=15
EMAIL_PROCESSING_TIMEOUT=300
MAX_MEMORY_USAGE=1024
GMAIL_API_RATE_LIMIT=250
```

## 🎯 **Ready to Go!**

Your backend now has production-ready scalability features! 