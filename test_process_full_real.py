#!/usr/bin/env python
"""Test /process-full and capture the actual error"""
import httpx
import json
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
os.chdir(os.path.dirname(__file__) or '.')

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# Get first unprocessed post
print("Finding an unprocessed post...")
response = supabase.table("posts").select("id, caption, image_url").eq("ai_processed", False).limit(1).execute()

if not response.data:
    print("All posts are processed. Getting any post...")
    response = supabase.table("posts").select("id, caption, image_url").limit(1).execute()
    if not response.data:
        print("No posts in database!")
        exit(1)

post = response.data[0]
print(f"Testing with post: {post['id']}")
print(f"  Caption: {post['caption']}")
print(f"  Image: {post['image_url'][:60]}")

print(f"\nCalling /process-full...")
try:
    response = httpx.post(
        'http://localhost:9003/process-full',
        json={"post_id": post['id']},
        timeout=180
    )
    print(f"\n✓ Status: {response.status_code}")
    
    try:
        data = response.json()
        if response.status_code == 200:
            print("✓ SUCCESS!")
            print(f"  New status: {data.get('new_status')}")
            print(f"  Geo coords: {data.get('geo_result', {}).get('latitude')}, {data.get('geo_result', {}).get('longitude')}")
        else:
            print(f"✗ ERROR: {json.dumps(data, indent=2)}")
    except json.JSONDecodeError:
        print(f"Response: {response.text[:500]}")
        
except httpx.TimeoutException:
    print("✗ Request timed out")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
