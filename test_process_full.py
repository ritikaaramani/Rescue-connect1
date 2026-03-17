#!/usr/bin/env python
"""Test the /process-full endpoint"""
import httpx
import json
import sys

test_post_id = "test-post-123"

try:
    print(f"Testing /process-full endpoint with post_id={test_post_id}")
    response = httpx.post(
        'http://localhost:9003/process-full',
        json={"post_id": test_post_id},
        timeout=15
    )
    print(f"Status: {response.status_code}")
    print(f"Response:\n{response.text}")
    
    if response.status_code >= 400:
        try:
            error_data = response.json()
            print(f"\nParsed error: {json.dumps(error_data, indent=2)}")
        except:
            pass
except httpx.ConnectError as e:
    print(f"Connection error: {e}")
except httpx.TimeoutException as e:
    print(f"Timeout error: {e}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
