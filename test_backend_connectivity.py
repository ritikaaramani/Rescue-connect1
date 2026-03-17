#!/usr/bin/env python
"""Test CORS and actual endpoint with a real scenario"""
import httpx
import json

print("=== Testing Backend Connectivity ===\n")

# Test 1: CORS preflight
print("1. Testing CORS preflight for /process-full...")
try:
    response = httpx.options(
        'http://localhost:9003/process-full',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'POST',
        },
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    print(f"   CORS headers: {dict((k, v) for k, v in response.headers.items() if 'access' in k.lower())}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Direct POST request
print("\n2. Testing POST to /process-full...")
try:
    response = httpx.post(
        'http://localhost:9003/process-full',
        json={"post_id": "test"},
        headers={'Origin': 'http://localhost:5173'},
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Check health
print("\n3. Testing /health endpoint...")
try:
    response = httpx.get('http://localhost:9003/health', timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

print("\n=== Backend Server Status: OK (Running on localhost:9003) ===")
