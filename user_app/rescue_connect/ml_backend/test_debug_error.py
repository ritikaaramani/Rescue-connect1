#!/usr/bin/env python
"""Capture the actual error from the backend during process-full"""
import httpx
import json
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# Create  a test post with dummy data
print("Creating a test post...")
test_post = {
    "caption": "Test flood in Bangalore",
    "image_url": "https://uhlnwyrikuiprkuubloh.supabase.co/storage/v1/object/public/disaster_images/test.jpg",
    "user_id": "00000000-0000-0000-0000-000000000000",
    "media_type": "image"
}

result = supabase.table("posts").insert(test_post).execute()
test_post_id = result.data[0]["id"]
print(f"Created test post: {test_post_id}")

# Now call process-full and capture the full error response
print(f"\nCalling /process-full...")
response = httpx.post(
    'http://localhost:9003/process-full',
    json={"post_id": test_post_id},
    timeout=180
)

print(f"Status: {response.status_code}")
print(f"Response:\n{response.text}")

if response.status_code >= 400:
    try:
        error_data = response.json()
        print(f"\nParsed error detail:")
        print(json.dumps(error_data, indent=2))
    except json.JSONDecodeError:
        print("Could not parse response as JSON")
