#!/usr/bin/env python
"""Test /process-full and capture errors"""
import httpx, json, os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# Get unprocessed post
resp = sb.table("posts").select("id, caption").eq("ai_processed", False).limit(1).execute()
if not resp.data:
    resp = sb.table("posts").select("id, caption").limit(1).execute()

post = resp.data[0]
print(f"Testing: {post['id']}")
print(f"Caption: {post['caption']}")

# Call endpoint  
print("\nCalling /process-full...")
try:
    r = httpx.post('http://localhost:9003/process-full', json={"post_id": post['id']}, timeout=180)
    print(f"Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print("✓ SUCCESS!")
        print(f"  Status: {data.get('new_status')}")
    else:
        print(f"✗ ERROR:\n{json.dumps(data, indent=2)}")
except Exception as e:
    print(f"✗ {type(e).__name__}: {e}")
