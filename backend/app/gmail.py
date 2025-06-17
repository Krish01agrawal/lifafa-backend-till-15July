from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import re
from typing import List
import html
import os
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def build_gmail_service(access_token: str, refresh_token: str = None, client_id: str = None, client_secret: str = None):
    """Build Gmail service with proper credentials for token refresh"""
    
    # Get required OAuth credentials from environment if not provided
    if not client_id:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_secret:
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    print(f"🔑 Building Gmail service with:")
    print(f"   - Access token: {access_token[:20]}...")
    print(f"   - Refresh token: {refresh_token[:20] if refresh_token else 'None'}...")
    print(f"   - Client ID: {client_id[:20] if client_id else 'None'}...")
    print(f"   - Client Secret: {client_secret[:20] if client_secret else 'None'}...")
    
    # Create credentials with all required fields for refresh
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    
    print(f"🔄 Credentials created, building Gmail service...")
    service = build('gmail', 'v1', credentials=creds)
    print(f"✅ Gmail service built successfully")
    return service

async def fetch_emails(service, user_id='me', max_results=90):
    """
    Fetch emails with proper pagination to get last 2 months of data
    Gmail API limits each request to 500 messages, so we need pagination
    """
    
    # Limited time range for last 2 months of data
    query_filter = 'newer_than:60d'  # 60 days = 2 months
    
    print(f"📧 Fetching emails with query: {query_filter}, target: {max_results} emails")
    print(f"🔄 Using pagination to overcome Gmail's 500-message-per-request limit...")
    
    all_messages = []
    page_token = None
    page_count = 0
    
    try:
        while len(all_messages) < max_results:
            page_count += 1
            print(f"📄 Fetching page {page_count}... (current total: {len(all_messages)})")
            
            # Gmail API call with pagination
            request_params = {
                'userId': user_id,
                'maxResults': min(500, max_results - len(all_messages)),  # Gmail's max is 500 per request
                'q': query_filter
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            results = service.users().messages().list(**request_params).execute()
            
            messages = results.get('messages', [])
            all_messages.extend(messages)
            
            print(f"✅ Page {page_count} fetched: {len(messages)} messages (total: {len(all_messages)})")
            
            # Check if there are more pages
            page_token = results.get('nextPageToken')
            if not page_token:
                print(f"📄 No more pages available. Reached end of results.")
                break
                
            # Safety check to prevent infinite loops
            if page_count > 20:  # Max 20 pages = 10,000 messages max
                print(f"⚠️ Reached maximum page limit (20 pages). Stopping pagination.")
                break
        
        print(f"📊 PAGINATION COMPLETE: Found {len(all_messages)} messages across {page_count} pages")
        
        if not all_messages:
            print(f"❌ No emails found matching criteria: {query_filter}")
            return []
            
    except Exception as e:
        print(f"❌ Error in Gmail API pagination: {str(e)}")
        raise
    
    # Now fetch detailed content for each message
    print(f"📥 Fetching detailed content for {len(all_messages)} messages...")
    emails = []
    
    for i, msg in enumerate(all_messages):
        try:
            # Progress indicator for large batches
            if i % 100 == 0:
                print(f"📧 Processing message {i+1}/{len(all_messages)}...")
                
            message = service.users().messages().get(userId=user_id, id=msg['id'], format='full').execute()
            payload = message['payload']
            headers = payload.get('headers', [])
            
            # Extract email details
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            snippet = message.get('snippet', '')
            
            # Extract body content
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and part.get('body', {}).get('data'):
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/html' and part.get('body', {}).get('data'):
                        raw_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        body = clean_html(raw_html)
                        break
            else:
                if payload.get('body') and payload['body'].get('data'):
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

            emails.append({
                "id": msg['id'],
                "subject": subject,
                "sender": sender,
                "date": date,
                "snippet": snippet,
                "body": body,
            })
            
        except Exception as e:
            print(f"⚠️ Error processing message {i+1}: {str(e)}")
            continue  # Skip this message and continue with others
    
    print(f"✅ EMAIL FETCH COMPLETE: Successfully processed {len(emails)} emails")
    print(f"📊 Data range: {query_filter} ({60} days)")
    print(f"📄 Pages fetched: {page_count}")
    
    return emails

def clean_html(raw_html):
    # Basic clean-up to remove HTML tags, decode entities
    text = re.sub('<[^<]+?>', '', raw_html)
    text = html.unescape(text)
    return text.strip()
