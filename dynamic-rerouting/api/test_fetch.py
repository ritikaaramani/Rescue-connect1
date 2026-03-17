import os, json, httpx
from dotenv import load_dotenv

# Try to load .env from the React Authority app
env_path = r"C:\Users\VAIBHAVI\Rescue-connect1\user_app\rescue_connect\authority\.env"
load_dotenv(env_path)
    
url = os.environ.get("VITE_SUPABASE_URL")
key = os.environ.get("VITE_SUPABASE_ANON_KEY")

try:
    with httpx.Client(timeout=5) as client:
        resp = client.get(
            f"{url}/rest/v1/posts",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            params={
                "dispatch_status": "in.(pending,assigned,in-progress)",
                "order": "created_at.desc",
                "limit": "50",
            },
        )
        resp.raise_for_status()
        posts = resp.json()
        print(f"SUCCESS: Fetched {len(posts)} posts.")
        for p in posts:
            print(f"- Post {p.get('id')}: {p.get('dispatch_status')} | Location: {p.get('location')}")
except Exception as e:
    print(f"FAILED: {e}")
