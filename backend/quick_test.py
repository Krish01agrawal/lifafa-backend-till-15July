#!/usr/bin/env python3
import requests
import json

# Your JWT token
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImtyaXNoLmFncmF3YWxAcGx1dG9tb25leS5pbiIsInVzZXJfaWQiOiIxMTc0NTQ4Nzc5Nzk1MDA1MjA3MDAiLCJuYW1lIjoiS3Jpc2ggQWdyYXdhbCIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NJUEtSdmtITTdaWjdOZkJBZllfWGdEWnVUajZtV0RQOEwwSHNOM0ozZVR4VzciLCJhY2Nlc3NfdG9rZW4iOiJ5YTI5LmEwQVNINk53dHZnYTkyLi4uIiwicmVmcmVzaF90b2tlbiI6IjEvLzBnbXViMWN3QTM1dGVDZ1lJQVJBQUdBU053Ri1MOUlybWVob0c2WE1COHBTNEVZSGVSU0tnSVpMVDBUX3UxYlZENnhVZHE1WUFPSEY3RDdKZmNHdjJtNDRKIiwiZXhwIjoxNzM2NzYyMjczfQ.QfOJlZmqGT8sj3pALdDmuKGPzj"

url = "http://localhost:8001/gmail/download-data"
payload = {"jwt_token": JWT_TOKEN}

print("🔄 Testing Gmail Download API...")
print(f"📡 URL: {url}")

try:
    response = requests.post(url, json=payload, timeout=300)  # 5 minutes
    
    print(f"📊 Status: {response.status_code}")
    print(f"📊 Size: {len(response.content)} bytes")
    
    if response.status_code == 200:
        print("✅ SUCCESS! Gmail data downloaded!")
        data = response.json()
        print(f"📧 Total emails: {data.get('data_info', {}).get('total_emails', 0)}")
        print(f"📅 Date range: {data.get('data_info', {}).get('date_range', 'unknown')}")
        
        # Save sample
        with open('gmail_download_success.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("💾 Saved to gmail_download_success.json")
        
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}") 