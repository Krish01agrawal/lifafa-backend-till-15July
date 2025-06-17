#!/usr/bin/env python3
"""
Debug script to check user OAuth tokens in the database
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_user_tokens():
    """Check user tokens in MongoDB"""
    
    # Connect to MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.get_database("gmail_chatbot")
    users_collection = db.get_collection("users")
    
    print("🔍 Checking user OAuth tokens in database...")
    print("=" * 60)
    
    # Find all users
    users = await users_collection.find({}).to_list(length=None)
    
    if not users:
        print("❌ No users found in database")
        return
    
    for user in users:
        user_id = user.get("user_id", "Unknown")
        email = user.get("email", "Unknown")
        access_token = user.get("access_token")
        refresh_token = user.get("refresh_token")
        token_expiry = user.get("token_expiry")
        fetched_email = user.get("fetched_email", False)
        
        print(f"👤 User: {email} (ID: {user_id})")
        print(f"   📧 Fetched Email: {fetched_email}")
        print(f"   🔑 Access Token: {'✅ Present' if access_token else '❌ Missing'}")
        print(f"   🔄 Refresh Token: {'✅ Present' if refresh_token else '❌ Missing'}")
        print(f"   ⏰ Token Expiry: {token_expiry if token_expiry else 'Not set'}")
        
        if access_token:
            print(f"   🔑 Access Token (first 20 chars): {access_token[:20]}...")
        if refresh_token:
            print(f"   🔄 Refresh Token (first 20 chars): {refresh_token[:20]}...")
        
        print()
    
    # Check environment variables
    print("🌍 Environment Variables:")
    print("=" * 60)
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    print(f"   GOOGLE_CLIENT_ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"   GOOGLE_CLIENT_SECRET: {'✅ Set' if client_secret else '❌ Missing'}")
    
    if client_id:
        print(f"   Client ID (first 20 chars): {client_id[:20]}...")
    if client_secret:
        print(f"   Client Secret (first 10 chars): {client_secret[:10]}...")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_user_tokens()) 