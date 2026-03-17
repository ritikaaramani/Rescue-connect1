#!/usr/bin/env python
"""Test the full process-full pipeline with real data"""
import httpx
import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY not configured")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

# Get the first post without AI processing
print("Fetching a post from the database...")
try:
    response = supabase.table("posts").select("id, caption, image_url, ai_processed").eq("ai_processed", False).limit(1).execute()
    posts = response.data
    
    if not posts:
        print("No unprocessed posts found in database")
        exit(0)
    
    post = posts[0]
    print(f"Found post: {post['id']}")
    print(f"  Caption: {post['caption'][:100] if post['caption'] else '(none)'}")
    print(f"  Image URL: {post['image_url'][:80] if post['image_url'] else '(none)'}")
    
    # Test the /process-full endpoint with this real post
    print(f"\nCalling /process-full for post {post['id']}...")
    try:
        response = httpx.post(
            'http://localhost:9003/process-full',
            json={"post_id": post['id']},
            timeout=180  # 3 minute timeout for full processing
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS! Response keys: {list(data.keys())}")
            print(f"  New status: {data.get('new_status')}")
            print(f"  Geo result: {data.get('geo_result', {}).get('location')}")
        else:
            try:
                error = response.json()
                print(f"ERROR: {json.dumps(error, indent=2)}")
            except:
                print(f"ERROR: {response.text[:500]}")
                
    except httpx.TimeoutException:
        print("ERROR: Request timed out (180 seconds)")
    except httpx.ConnectError as e:
        print(f"ERROR: Connection failed: {e}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        
except Exception as e:
    print(f"Database error: {e}")
