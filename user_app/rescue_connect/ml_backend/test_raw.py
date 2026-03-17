#!/usr/bin/env python
"""Test /process-full and capture raw response"""
import httpx, os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

resp = sb.table("posts").select("id").eq("ai_processed", False).limit(1).execute()
if not resp.data:
    resp = sb.table("posts").select("id").limit(1).execute()

pid = resp.data[0]['id']
print(f"Testing post: {pid}")

r = httpx.post('http://localhost:9003/process-full', json={"post_id": pid}, timeout=180)
print(f"\nStatus: {r.status_code}")
print(f"Headers: {dict(r.headers)}")
print(f"Content-Type: {r.headers.get('content-type')}")
print(f"\nRaw response ({len(r.content)} bytes):")
print(repr(r.text[:1000]))
