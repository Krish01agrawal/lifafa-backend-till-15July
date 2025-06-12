
import os
import asyncio
from datetime import datetime
from mem0 import AsyncMemoryClient, MemoryClient
from agno.models.openai import OpenAIChat
import openai

# Environment Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    raise ValueError("OPENAI_API_KEY not set")

# Clients
aclient = AsyncMemoryClient()
sync_client = MemoryClient()

# Upload emails with comprehensive metadata, timestamp, categories
async def upload_emails_to_mem0(user_id: str, emails: list):
    print(f"Uploading {len(emails)} emails for user {user_id}...")

    for email in emails:
        email_id = email.get("id")
        if not email_id:
            continue

        subject = email.get("subject", "")
        sender = email.get("sender", "")
        snippet = email.get("snippet", "")
        body = email.get("body", "")
        timestamp = email.get("date")

        if timestamp:
            try:
                timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z").isoformat()
            except:
                timestamp = None

        subject_lower = subject.lower()
        sender_lower = sender.lower()
        content_lower = f"{subject_lower} {snippet.lower()} {body.lower()}"

        # Comprehensive categorization system
        category = "general"
        subcategory = "misc"
        payment_method = "unknown"
        merchant = "unknown"
        amount = None
        
        # Extract amount if present
        import re
        amount_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', content_lower)
        if amount_match:
            amount = amount_match.group(1).replace(',', '')

        # Detect payment methods
        if any(method in content_lower for method in ["paytm", "gpay", "phonepe", "upi"]):
            payment_method = "digital_wallet"
        elif any(method in content_lower for method in ["credit card", "debit card", "card"]):
            payment_method = "card"
        elif any(method in content_lower for method in ["bank transfer", "neft", "rtgs"]):
            payment_method = "bank_transfer"

        # Comprehensive category detection
        if any(keyword in content_lower for keyword in ["statement", "account summary", "monthly statement"]):
            category = "banking"
            subcategory = "statement"
        
        elif any(keyword in content_lower for keyword in ["reminder", "due", "payment due", "overdue"]):
            category = "reminders"
            if any(keyword in content_lower for keyword in ["emi", "loan", "credit card"]):
                subcategory = "payment_reminder"
                merchant = "bank"
            elif any(keyword in content_lower for keyword in ["bill", "electricity", "utility"]):
                subcategory = "bill_reminder"
                merchant = "utility_company"
            elif any(keyword in content_lower for keyword in ["subscription", "renewal"]):
                subcategory = "subscription_reminder"
            else:
                subcategory = "general_reminder"
        
        elif any(keyword in content_lower for keyword in ["electricity", "power", "bescom", "mseb", "kseb", "electric bill"]):
            category = "utilities"
            subcategory = "electricity"
            merchant = "electricity_board"
        
        elif any(keyword in content_lower for keyword in ["water bill", "water tax", "water supply"]):
            category = "utilities"
            subcategory = "water"
            merchant = "water_board"
        
        elif any(keyword in content_lower for keyword in ["gas bill", "lpg", "cooking gas"]):
            category = "utilities"
            subcategory = "gas"
            merchant = "gas_company"
        
        elif any(keyword in content_lower for keyword in ["internet", "broadband", "wifi", "airtel", "jio fiber"]):
            category = "utilities"
            subcategory = "internet"
        
        elif any(keyword in content_lower for keyword in ["mobile", "phone", "recharge", "prepaid", "postpaid"]):
            category = "utilities"
            subcategory = "mobile"
        
        elif any(vendor in sender_lower for vendor in ["swiggy", "zomato", "ubereats", "dominos"]):
            category = "food"
            subcategory = "delivery"
            merchant = next((vendor for vendor in ["swiggy", "zomato", "ubereats", "dominos"] if vendor in sender_lower), "food_delivery")
        
        elif any(vendor in sender_lower for vendor in ["flipkart", "amazon", "myntra", "ajio"]):
            category = "shopping"
            subcategory = "ecommerce"
            merchant = next((vendor for vendor in ["flipkart", "amazon", "myntra", "ajio"] if vendor in sender_lower), "ecommerce")
        
        elif any(keyword in content_lower for keyword in ["netflix", "spotify", "prime", "subscription", "renewal"]):
            category = "entertainment"
            subcategory = "subscription"
            if "netflix" in content_lower:
                merchant = "netflix"
            elif "spotify" in content_lower:
                merchant = "spotify"
            elif "prime" in content_lower:
                merchant = "amazon_prime"
        
        elif any(keyword in content_lower for keyword in ["sip", "mutual fund", "investment", "equity"]):
            category = "investment"
            subcategory = "mutual_fund"
        
        elif any(keyword in content_lower for keyword in ["insurance", "policy", "premium"]):
            category = "insurance"
            subcategory = "premium"
        
        elif any(keyword in content_lower for keyword in ["loan", "emi", "credit"]):
            category = "finance"
            subcategory = "loan"
        
        elif "order" in subject_lower:
            if any(vendor in sender_lower for vendor in ["swiggy", "zomato"]):
                category = "food"
                subcategory = "delivery"
                merchant = next((vendor for vendor in ["swiggy", "zomato"] if vendor in sender_lower), "food_delivery")
            elif any(vendor in sender_lower for vendor in ["flipkart", "amazon"]):
                category = "shopping"
                subcategory = "ecommerce"
                merchant = next((vendor for vendor in ["flipkart", "amazon"] if vendor in sender_lower), "ecommerce")
            else:
                category = "orders"
                subcategory = "general"

        content = f"Subject: {subject}\nSnippet: {snippet}\nBody: {body}"

        messages = [{
            "role": "user",
            "content": content,
        }]

        # Comprehensive metadata for advanced filtering
        metadata = {
            "sender": sender,
            "category": category,
            "subcategory": subcategory,
            "payment_method": payment_method,
            "merchant": merchant,
            "source": "gmail",
            "timestamp": timestamp,
            "has_amount": amount is not None,
            "amount": amount,
            "subject_keywords": " ".join([word for word in subject_lower.split() if len(word) > 3]),
            "content_type": "email"
        }

        try:
            await aclient.add(messages=messages, user_id=user_id, memory_id=email_id, metadata=metadata)
            print(f"✅ Uploaded email ID: {email_id} | Category: {category}/{subcategory} | Merchant: {merchant}")
        except Exception as e:
            print(f"❌ Error uploading {email_id}: {e}")

# Intelligent query system with LLM-driven sub-query generation and response refinement
async def query_mem0(user_id: str, query: str, limit=45, page=0, category=None):
    try:
        print(f"🔍 Processing intelligent query: '{query}'")
        
        # Step 1: Generate sub-queries using LLM
        sub_queries = await generate_sub_queries(query)
        print(f"🧠 Generated sub-queries: {sub_queries}")
        
        # Step 2: Search Mem0 for each sub-query
        all_results = []
        for sub_query in sub_queries:
            print(f"🔎 Searching for: '{sub_query}'")
            
            # Search with minimal filters for maximum recall
            results = sync_client.search(
                query=sub_query,
                user_id=user_id,
                limit=20,  # Get more results per sub-query
                filters={"metadata.source": "gmail"},
                keyword_search=True,
                rerank=True,
                filter_memories=False
            )
            
            if results:
                print(f"📊 Found {len(results)} results for '{sub_query}'")
                all_results.extend(results)
        
        # Step 3: Remove duplicates based on memory content
        unique_results = []
        seen_memories = set()
        for result in all_results:
            memory_text = result.get('memory', '')
            if memory_text not in seen_memories:
                unique_results.append(result)
                seen_memories.add(memory_text)
        
        print(f"📈 Total unique results found: {len(unique_results)}")
        print(f"🔍 Unique results: {unique_results}")
        
        if not unique_results:
            return "No relevant emails found for your query. Try uploading emails first or rephrasing your query."
        
        # Step 4: Use LLM to refine and format the final response
        refined_response = await refine_response_with_llm(query, unique_results[:limit])
        
        return refined_response

    except Exception as e:
        print(f"❌ Error in intelligent query processing: {e}")
        return f"Error processing your query: {str(e)}"

# Generate intelligent sub-queries using LLM
async def generate_sub_queries(original_query: str) -> list:
    try:
        system_prompt = """
You are an intelligent query expansion system. Given a user's email search query, generate 3-5 related sub-queries that will help find all relevant emails.

Consider these aspects:
1. Synonyms and related terms
2. Different ways the same information might appear in emails
3. Broader and narrower interpretations of the query
4. Common email patterns and formats

For example:
- Query: "reminders" → ["payment reminders", "due date notifications", "bill alerts", "subscription renewals", "overdue notices"]
- Query: "food orders" → ["food delivery", "restaurant orders", "Swiggy orders", "Zomato orders", "meal deliveries"]
- Query: "electricity bill" → ["power bill", "BESCOM payment", "electricity payment", "utility bill", "electric bill"]

Return ONLY a JSON array of strings, no other text.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate sub-queries for: '{original_query}'"}
        ]

        response = await asyncio.to_thread(
            openai.chat.completions.create,
            model="gpt-4",
            messages=messages,
            temperature=0.3,
            max_tokens=200
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            import json
            try:
                sub_queries = json.loads(response.choices[0].message.content.strip())
                # Add the original query to the list
                if original_query not in sub_queries:
                    sub_queries.insert(0, original_query)
                return sub_queries[:10]  # Limit to 5 sub-queries
            except json.JSONDecodeError:
                # Fallback: return original query
                return [original_query]
        
        return [original_query]
        
    except Exception as e:
        print(f"❌ Error generating sub-queries: {e}")
        return [original_query]

# Refine response using LLM for better formatting and accuracy
async def refine_response_with_llm(original_query: str, search_results: list) -> str:
    try:
        # Prepare email data for LLM analysis
        email_data = []
        for i, result in enumerate(search_results):
            memory_text = result.get('memory', '')
            # Truncate very long emails for better processing
            if len(memory_text) > 400:
                memory_text = memory_text[:400] + "..."
            email_data.append(f"Email {i+1}: {memory_text}")
        
        emails_text = "\n\n".join(email_data)
        
        system_prompt = f"""
You are an intelligent email assistant. Analyze the provided email data and create a comprehensive, well-formatted response to the user's query.

USER QUERY: "{original_query}"

INSTRUCTIONS:
1. Carefully analyze each email to determine relevance to the user's query
2. Group similar emails together (e.g., all food orders, all reminders, etc.)
3. Present information in a clear, organized format
4. Include specific details like amounts, dates, merchants when relevant
5. If no emails are directly relevant, clearly state that
6. Use bullet points, numbering, or sections for better readability
7. Be concise but informative

RESPONSE FORMAT:
- Start with a brief summary of what was found
- Organize results by category or type
- Include specific details from the emails
- Use emojis for better visual appeal
- End with a summary count

EXAMPLE FORMAT:
## 📧 Email Search Results for: "your query"

**Summary:** Found X relevant emails

### 💳 Payment Reminders
• EMI Reminder: ₹4,000 due on 14 June (Axis Bank)
• Credit card payment overdue

### 🍕 Food Orders  
• Swiggy order: Chicken Biryani ₹239 delivered
• Zomato order: Pizza delivered

**Total:** X emails found
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"EMAIL DATA:\n\n{emails_text}"}
        ]

        response = await asyncio.to_thread(
            openai.chat.completions.create,
            model="gpt-4",
            messages=messages,
            temperature=0.2,
            max_tokens=1000
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            # Fallback response
            return f"Found {len(search_results)} emails related to your query: '{original_query}'"
        
    except Exception as e:
        print(f"❌ Error refining response: {e}")
        # Fallback: return basic formatted response
        response = f"\n\n**📧 Found {len(search_results)} Email(s) for: '{original_query}'**\n\n"
        for i, item in enumerate(search_results[:10]):
            memory_text = item.get('memory', '')
            response += f"{i+1}. {memory_text}\n\n"
        return response

# Optional: Add graph memory (nodes and edges)
# async def add_graph_memory(user_id: str):
#     try:
#         await aclient.graph.add_nodes_and_edges(
#             user_id=user_id,
#             nodes=[
#                 {"id": "txn_001", "label": "Transaction", "properties": {"amount": "₹500", "merchant": "Flipkart"}},
#                 {"id": "merchant_flipkart", "label": "Merchant", "properties": {"category": "e-commerce"}}
#             ],
#             edges=[
#                 {"source": "txn_001", "target": "merchant_flipkart", "label": "made_to"}
#             ]
#         )
#         print("✅ Graph memory added")
#     except Exception as e:
#         print(f"Graph memory error: {e}")

# Optional: Run graph query
# def run_graph_query(user_id: str, query: str):
#     try:
#         result = sync_client.graph.query(user_id=user_id, query=query)
#         return result
#     except Exception as e:
#         return f"Graph query error: {e}"

# Standalone test functions
async def test_upload():
    user_id = "test_user"
    test_emails = [
        {
            "id": "email_001",
            "subject": "Statement from HDFC",
            "sender": "bank@hdfc.com",
            "snippet": "Here is your account statement",
            "body": "Attached is your PDF statement for May.",
            "date": "2025-06-10T09:30:00+0530"
        },
        {
            "id": "email_002",
            "subject": "Order Confirmed - Flipkart",
            "sender": "orders@flipkart.com",
            "snippet": "Your order has been placed",
            "body": "Order ID: XYZ123 confirmed.",
            "date": "2025-06-11T11:00:00+0530"
        },
        {
            "id": "email_003",
            "subject": "Your Zomato Order is on the way!",
            "sender": "order@zomato.com",
            "snippet": "Track your chicken biryani order",
            "body": "Your Chicken Biryani will arrive in 30 minutes. Enjoy!",
            "date": "2025-06-10T19:45:00+0530"
        },
        {
            "id": "email_004",
            "subject": "Tinder Match Found 😍",
            "sender": "notify@tinder.com",
            "snippet": "You matched with Priya from Bengaluru",
            "body": "Say hi to Priya and plan your first date!",
            "date": "2025-06-09T21:15:00+0530"
        },
        {
            "id": "email_005",
            "subject": "You're Invited: Club Night at Glitch",
            "sender": "events@partynight.com",
            "snippet": "Guestlist + Free drinks before 10 PM",
            "body": "Join us at Glitch, MG Road, Bengaluru this Saturday. DJ nights and free drinks!",
            "date": "2025-06-08T14:30:00+0530"
        },
        {
            "id": "email_006",
            "subject": "Netflix Subscription Renewal",
            "sender": "support@netflix.com",
            "snippet": "Your monthly plan has been renewed",
            "body": "₹499 has been debited for your Netflix subscription",
            "date": "2025-06-01T08:00:00+0530"
        },
        {
            "id": "email_007",
            "subject": "Interview Scheduled with Google",
            "sender": "careers@google.com",
            "snippet": "Your interview is confirmed",
            "body": "Your interview for the SDE role is scheduled on June 15 at 2 PM IST.",
            "date": "2025-06-10T13:20:00+0530"
        },
        {
            "id": "email_008",
            "subject": "Amazon Order Shipped",
            "sender": "shipments@amazon.in",
            "snippet": "Your Nike Shoes are on the way",
            "body": "Track your order ID: AMZ0987 expected to arrive by June 13.",
            "date": "2025-06-11T10:10:00+0530"
        },
        {
            "id": "email_009",
            "subject": "SIP Payment Successful",
            "sender": "mutualfunds@zerodha.com",
            "snippet": "Your SIP in Axis Bluechip Fund is successful",
            "body": "₹1500 has been invested in your Axis Bluechip Fund on 10th June.",
            "date": "2025-06-10T07:50:00+0530"
        },
        {
            "id": "email_010",
            "subject": "Your Swiggy Order Delivered",
            "sender": "order@swiggy.in",
            "snippet": "Your Butter Paneer order has been delivered",
            "body": "Thanks for ordering from Swiggy. Rate your meal!",
            "date": "2025-06-09T20:30:00+0530"
        },
        {
            "id": "email_011",
            "subject": "New Job Alert: UI/UX Designer at Cred",
            "sender": "alerts@naukri.com",
            "snippet": "Cred is hiring in Bengaluru",
            "body": "Apply to the latest job openings at Cred. High-paying design roles available.",
            "date": "2025-06-12T10:00:00+0530"
        },
        {
            "id": "email_012",
            "subject": "BYJU'S Class Reminder",
            "sender": "support@byjus.com",
            "snippet": "Your live class starts in 30 minutes",
            "body": "Subject: Math. Time: 6 PM today. Join using the app link.",
            "date": "2025-06-11T17:30:00+0530"
        },
        {
            "id": "email_013",
            "subject": "LinkedIn - Someone viewed your profile",
            "sender": "notifications@linkedin.com",
            "snippet": "Harsh from Wipro viewed your profile",
            "body": "Check who's been looking at your profile this week.",
            "date": "2025-06-11T16:45:00+0530"
        },
        {
            "id": "email_014",
            "subject": "BookMyShow: Spider-Man Tickets Confirmed",
            "sender": "tickets@bookmyshow.com",
            "snippet": "Your tickets are booked for PVR, Bengaluru",
            "body": "Enjoy Spider-Man on 12th June, 6:30 PM. Seat A12-A13.",
            "date": "2025-06-10T12:10:00+0530"
        },
        {
            "id": "email_015",
            "subject": "Spotify Premium Renewed",
            "sender": "notify@spotify.com",
            "snippet": "₹129 has been deducted",
            "body": "Enjoy ad-free music and offline downloads with Spotify Premium.",
            "date": "2025-06-01T06:00:00+0530"
        },
        {
            "id": "email_016",
            "subject": "CoinDCX Investment Confirmation",
            "sender": "invest@coindcx.com",
            "snippet": "Your order in Bitcoin is complete",
            "body": "₹2000 invested in BTC at ₹58L on 9th June.",
            "date": "2025-06-09T11:15:00+0530"
        },
        {
            "id": "email_017",
            "subject": "Semester Exam Timetable",
            "sender": "exams@college.edu.in",
            "snippet": "Check your June exam schedule",
            "body": "Download your exam schedule for 2nd year B.Tech - CSE.",
            "date": "2025-06-05T08:30:00+0530"
        },
        {
            "id": "email_018",
            "subject": "Cafe Mocha - You're Invited 🎉",
            "sender": "invite@cafemocha.in",
            "snippet": "Open Mic Night this Friday!",
            "body": "Poetry, music, and more! Grab your seat now for Cafe Mocha's Open Mic.",
            "date": "2025-06-10T18:00:00+0530"
        },
        {
            "id": "email_019",
            "subject": "Wakefit Mattress Offer: 40% Off",
            "sender": "deals@wakefit.co",
            "snippet": "Save big on Sleep Essentials",
            "body": "Buy premium mattresses with 40% off. Limited-time offer.",
            "date": "2025-06-04T10:15:00+0530"
        },
        {
            "id": "email_020",
            "subject": "Meesho Order Delivered",
            "sender": "notifications@meesho.com",
            "snippet": "Your Kurtis are delivered",
            "body": "Thanks for shopping with us. Return window open till June 14.",
            "date": "2025-06-09T19:00:00+0530"
        },
        {
            "id": "email_021",
            "subject": "Your Swiggy Order is on the Way!",
            "sender": "order@swiggy.in",
            "snippet": "Your Chicken Biryani worth ₹239 is arriving soon.",
            "body": "Enjoy your meal! Order amount: ₹239. Expected delivery in 30 minutes.",
            "date": "2025-06-10T19:30:00+0530"
        },
        {
            "id": "email_022",
            "subject": "Your Flipkart Order Has Shipped",
            "sender": "orders@flipkart.com",
            "snippet": "Your headset worth ₹1,499 is on the way.",
            "body": "Order ID: FLK9876 confirmed and shipped. Amount paid: ₹1,499.",
            "date": "2025-06-09T11:15:00+0530"
        },
        {
            "id": "email_023",
            "subject": "SIP Investment Confirmed",
            "sender": "invest@zerodha.com",
            "snippet": "₹2,000 has been successfully invested",
            "body": "Your SIP in Axis Bluechip Fund is complete. ₹2,000 invested on 10 June.",
            "date": "2025-06-10T08:45:00+0530"
        },
        {
            "id": "email_024",
            "subject": "You're Invited to Saturday Club Night!",
            "sender": "events@nightlife.in",
            "snippet": "Free entry and 1 drink at Boho Club, Bengaluru",
            "body": "Dance the night away! Show this email for your free entry. Offer valid till 10 PM.",
            "date": "2025-06-08T17:00:00+0530"
        },
        {
            "id": "email_025",
            "subject": "You Matched with Anjali 💖",
            "sender": "notify@tinder.com",
            "snippet": "Start a chat with Anjali from Bengaluru",
            "body": "Say hi to Anjali and maybe plan a coffee date at Koramangala.",
            "date": "2025-06-11T21:00:00+0530"
        },
        {
            "id": "email_026",
            "subject": "Amazon Order Delivered",
            "sender": "shipments@amazon.in",
            "snippet": "Your Smartwatch worth ₹2,799 has been delivered",
            "body": "Thanks for shopping with us. We hope you enjoy your product!",
            "date": "2025-06-07T14:40:00+0530"
        },
        {
            "id": "email_027",
            "subject": "Bank Statement - June",
            "sender": "alerts@icici.com",
            "snippet": "Your ICICI statement is ready",
            "body": "Total debit: ₹12,452 | Credit: ₹15,000 | View PDF for complete summary.",
            "date": "2025-06-05T09:00:00+0530"
        },
        {
            "id": "email_028",
            "subject": "Hotstar Subscription Renewal",
            "sender": "notify@hotstar.com",
            "snippet": "₹499 debited for Premium Plan",
            "body": "Your Premium plan has been renewed for another month. Enjoy your binge!",
            "date": "2025-06-01T06:30:00+0530"
        },
        {
            "id": "email_029",
            "subject": "Job Opportunity: UI Designer at Razorpay",
            "sender": "jobs@linkedin.com",
            "snippet": "Razorpay is hiring in Bengaluru",
            "body": "Your profile matches an opening for a UI Designer. Click to apply now.",
            "date": "2025-06-12T10:30:00+0530"
        },
        {
            "id": "email_030",
            "subject": "Spotify Premium Renewed",
            "sender": "notify@spotify.com",
            "snippet": "₹129 successfully deducted",
            "body": "You're all set for another month of ad-free music. Bop away!",
            "date": "2025-06-01T08:00:00+0530"
        },
        {
            "id": "email_031",
            "subject": "Interview Scheduled with CRED",
            "sender": "careers@cred.club",
            "snippet": "SDE Interview confirmed",
            "body": "Your interview is scheduled on 15 June at 4 PM IST via Zoom.",
            "date": "2025-06-10T13:00:00+0530"
        },
        {
            "id": "email_032",
            "subject": "Nykaa Order Confirmed",
            "sender": "orders@nykaa.com",
            "snippet": "Your makeup kit worth ₹1,299 is confirmed",
            "body": "Track your order using this link. Expected delivery by 13 June.",
            "date": "2025-06-10T10:00:00+0530"
        },
        {
            "id": "email_033",
            "subject": "BookMyShow: Movie Tickets Confirmed",
            "sender": "tickets@bookmyshow.com",
            "snippet": "Enjoy 'Inside Out 2' at PVR Forum",
            "body": "Showtime: June 12, 6:45 PM | Seats: C10-C11 | ₹500 total.",
            "date": "2025-06-08T16:20:00+0530"
        },
        {
            "id": "email_034",
            "subject": "Zomato Promo - 50% OFF Today",
            "sender": "promo@zomato.com",
            "snippet": "Your favorite dishes at half price!",
            "body": "Use code ZMT50 during checkout. Valid only till midnight.",
            "date": "2025-06-12T15:30:00+0530"
        },
        {
            "id": "email_035",
            "subject": "PhonePe Recharge Successful",
            "sender": "alerts@phonepe.com",
            "snippet": "₹299 mobile recharge completed",
            "body": "Your Jio number has been recharged for ₹299 with 1.5GB/day plan.",
            "date": "2025-06-06T10:10:00+0530"
        },
        {
            "id": "email_036",
            "subject": "Café Dori - Poetry Night Entry Pass",
            "sender": "invite@cafedori.in",
            "snippet": "Entry confirmed for Friday's Open Mic",
            "body": "Join us for an evening of poetry, art, and espresso. Entry: ₹100.",
            "date": "2025-06-11T18:45:00+0530"
        },
        {
            "id": "email_037",
            "subject": "EMI Reminder: Credit Card Payment",
            "sender": "bank@axis.com",
            "snippet": "₹4,000 EMI due on 14 June",
            "body": "Avoid late fees. Pay now via Axis app or net banking.",
            "date": "2025-06-10T08:00:00+0530"
        },
        {
            "id": "email_038",
            "subject": "Myntra Order - Cotton Shirt Delivered",
            "sender": "orders@myntra.com",
            "snippet": "₹899 shirt delivered. Return till 15 June.",
            "body": "We hope you love your purchase! Need help? Click here to chat.",
            "date": "2025-06-09T14:30:00+0530"
        },
        {
            "id": "email_039",
            "subject": "Cred Coins Redeemed",
            "sender": "rewards@cred.club",
            "snippet": "You redeemed 2,000 coins for a ₹100 voucher",
            "body": "Use your reward at Starbucks. Expires in 7 days.",
            "date": "2025-06-08T12:00:00+0530"
        },
        {
            "id": "email_040",
            "subject": "Uber Ride Summary - ₹278",
            "sender": "receipt@uber.com",
            "snippet": "Your ride from Indiranagar to Koramangala",
            "body": "Trip completed on 10 June, ₹278 paid via UPI.",
            "date": "2025-06-10T21:00:00+0530"
        },
        {
            "id": "email_041",
            "subject": "Your EMI Payment is Confirmed",
            "sender": "alerts@bajajfinance.in",
            "snippet": "₹2,300 EMI debited from your account",
            "body": "Thanks for paying your EMI on time. Next due date: 10 July.",
            "date": "2025-06-10T07:30:00+0530"
        },
        {
            "id": "email_042",
            "subject": "Unacademy Class Reminder",
            "sender": "notify@unacademy.in",
            "snippet": "Join your live class at 8 PM",
            "body": "Subject: Polity | Educator: M. Rajan | Zoom link inside.",
            "date": "2025-06-11T19:30:00+0530"
        },
        {
            "id": "email_043",
            "subject": "Groww SIP Alert - ₹1,000 Invested",
            "sender": "notify@groww.in",
            "snippet": "Your SIP in Parag Parikh FlexiCap is confirmed",
            "body": "Investment Date: 9 June | Amount: ₹1,000 | Mode: Auto-debit",
            "date": "2025-06-09T08:45:00+0530"
        },
        {
            "id": "email_044",
            "subject": "Blinkit Order Delivered",
            "sender": "order@blinkit.com",
            "snippet": "Your groceries worth ₹520 delivered",
            "body": "Items: Milk, Bread, Eggs, Maggi, etc. Delivered in 11 minutes.",
            "date": "2025-06-07T20:15:00+0530"
        },
        {
            "id": "email_045",
            "subject": "LinkedIn Weekly Digest",
            "sender": "notifications@linkedin.com",
            "snippet": "3 people viewed your profile this week",
            "body": "Plus, check 5 new job openings that match your skills.",
            "date": "2025-06-11T13:00:00+0530"
        },
        {
            "id": "email_046",
            "subject": "Recharge Offer Just for You!",
            "sender": "deals@phonepe.com",
            "snippet": "Flat ₹25 cashback on next recharge",
            "body": "Use code PHONE25 to avail the offer. Valid till 13 June.",
            "date": "2025-06-11T10:10:00+0530"
        },
        {
            "id": "email_047",
            "subject": "Paytm - Electricity Bill Paid",
            "sender": "alerts@paytm.com",
            "snippet": "₹865 paid to BESCOM",
            "body": "Your BESCOM bill for June has been paid via UPI. Txn ID: 998877.",
            "date": "2025-06-06T08:30:00+0530"
        },
        {
            "id": "email_048",
            "subject": "HealthifyMe: Calorie Goal Achieved!",
            "sender": "alerts@healthifyme.com",
            "snippet": "You've stayed within your limit 5 days in a row",
            "body": "Great job! Your streak is building. Keep tracking your meals!",
            "date": "2025-06-09T22:00:00+0530"
        },
        {
            "id": "email_049",
            "subject": "BESCOM Reminder: Bill Due Soon",
            "sender": "billing@bescom.in",
            "snippet": "₹865 due by 10 June",
            "body": "Avoid disconnection. Pay via any UPI or credit card.",
            "date": "2025-06-05T09:10:00+0530"
        },
        {
            "id": "email_050",
            "subject": "Google Pay Offer - Win Scratch Card!",
            "sender": "offers@googlepay.in",
            "snippet": "Pay rent & win ₹1,000 cashback",
            "body": "Pay rent above ₹7,000 this month and unlock a scratch card reward.",
            "date": "2025-06-04T13:30:00+0530"
        },
        {
            "id": "email_051",
            "subject": "Cred - Pay Credit Card and Earn",
            "sender": "reminders@cred.club",
            "snippet": "Earn rewards every time you pay",
            "body": "Don't miss your due date. Earn up to 1,000 coins on this payment.",
            "date": "2025-06-11T11:45:00+0530"
        },
        {
            "id": "email_052",
            "subject": "YouTube Premium Activated",
            "sender": "subscriptions@youtube.com",
            "snippet": "₹129 deducted for monthly plan",
            "body": "Ad-free YouTube and Music Premium unlocked till July 10.",
            "date": "2025-06-10T07:45:00+0530"
        },
        {
            "id": "email_053",
            "subject": "Boat Accessories - ₹300 OFF Today!",
            "sender": "offers@boat.com",
            "snippet": "Special coupon code inside",
            "body": "Use BOAT300 on orders above ₹1,499. Limited time only.",
            "date": "2025-06-12T12:00:00+0530"
        },
        {
            "id": "email_054",
            "subject": "Ola Ride Completed",
            "sender": "ride@olacabs.com",
            "snippet": "₹312 trip to Bengaluru Airport",
            "body": "Thank you for riding with Ola. View receipt in app.",
            "date": "2025-06-08T10:15:00+0530"
        },
        {
            "id": "email_055",
            "subject": "JioCinema - Watch IPL Final Today",
            "sender": "alerts@jiocinema.com",
            "snippet": "Live from 7 PM",
            "body": "Don't miss the biggest cricket clash of the year. Streaming free.",
            "date": "2025-06-12T16:00:00+0530"
        },
        {
            "id": "email_056",
            "subject": "Paytm - Electricity Bill Paid",
            "sender": "alerts@paytm.com",
            "snippet": "₹865 paid to BESCOM",
            "body": "Your BESCOM bill for June has been paid via UPI. Txn ID: 998877.",
            "date": "2025-06-06T08:30:00+0530"
        },
        {
            "id": "email_057",
            "subject": "Paytm - Electricity Bill Paid",
            "sender": "alerts@paytm.com",
            "snippet": "₹865 paid to BESCOM",
            "body": "Your BESCOM bill for June has been paid via UPI. Txn ID: 998877.",
            "date": "2025-06-06T08:30:00+0530"
        },
        {
            "id": "email_058",
            "subject": "HealthifyMe: Calorie Goal Achieved!",
            "sender": "alerts@healthifyme.com",
            "snippet": "You've stayed within your limit 5 days in a row",
            "body": "Great job! Your streak is building. Keep tracking your meals!",
            "date": "2025-06-09T22:00:00+0530"
        }
    ]

    await upload_emails_to_mem0(user_id, test_emails)

async def test_query():
    user_id = "test_user"
    print(f"\n🔍 Interactive Query System - Type 'exit' to quit")
    print(f"=" * 60)
    
    while True:
        try:
            # Ask user for their query
            user_query = input("\n💬 Enter your query (or 'exit' to quit): ").strip()
            
            if user_query.lower() == 'exit':
                print("👋 Goodbye! Exiting query system.")
                break
            
            if not user_query:
                print("⚠️ Please enter a valid query.")
                continue
            
            print(f"\n🔍 Processing query: '{user_query}'")
            print("-" * 50)
            
            # Process the query
            result = await query_mem0(user_id, user_query)
            print(result)
            
            print("\n" + "=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            print("Please try again with a different query.")
            continue

# async def test_graph():
#     user_id = "test_user"
#     await add_graph_memory(user_id)
#     print(run_graph_query(user_id, "Transactions made to Flipkart"))

# Run individual test functions
if __name__ == "__main__":
    print("Select test to run: 1 = Upload, 2 = Query, 3 = Graph")
    choice = input("Enter choice: ").strip()

    if choice == "1":
        asyncio.run(test_upload())
    elif choice == "2":
        asyncio.run(test_query())
    elif choice == "3":
        # asyncio.run(test_graph())
        print("Graph functionality is currently disabled.")
    else:
        print("Invalid choice. Please enter 1, 2 or 3.")
