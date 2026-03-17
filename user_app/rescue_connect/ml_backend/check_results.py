#!/usr/bin/env python
"""Check the processed post to see the results"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(supabase_url, supabase_key)

# Get the most recently processed post
print("Fetching recently processed posts...")
response = supabase.table("posts").select("id, caption, ai_processed, disaster_type, inferred_latitude, inferred_longitude, location_method, ocr_text").eq("ai_processed", True).order("created_at", desc=True).limit(5).execute()

posts = response.data
if not posts:
    print("No processed posts found")
else:
    for post in posts:
        print(f"\nPost: {post['id']}")
        print(f"  Caption: {post['caption']}")
        print(f"  Disaster Type: {post['disaster_type']}")
        print(f"  AI Processed: {post['ai_processed']}")
        print(f"  Inferred Location: ({post['inferred_latitude']}, {post['inferred_longitude']})")
        print(f"  Location Method: {post['location_method']}")
        print(f"  OCR Text: {post['ocr_text'][:100] if post['ocr_text'] else '(none)'}")
