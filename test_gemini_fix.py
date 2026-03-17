
import sys
import os
import asyncio
import httpx
from dotenv import load_dotenv

# Use forward slashes
sys.path.append('c:/Ritika/RescueConnect-indorehacky/user_app/rescue_connect/ml_backend')

from app.image_analyzer import ImageAnalyzer

async def test_gemini():
    load_dotenv('c:/Ritika/RescueConnect-indorehacky/user_app/rescue_connect/ml_backend/.env')
    analyzer = ImageAnalyzer()
    
    test_image_url = "https://images.unsplash.com/photo-1547683908-21aa53db3c5d?auto=format&fit=crop&q=80&w=1000"
    
    from google import genai
    from google.genai import types
    
    client = genai.Client(
        api_key=analyzer.gemini_key,
        http_options={'api_version': 'v1'}
    )
    
    model = 'gemini-2.0-flash'
    print(f"\n--- Trying model: {model} ---")
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(test_image_url)
            image_data = response.content
        
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
        
        response = client.models.generate_content(
            model=model,
            contents=["Respond with 'OK' if you can see this.", image_part]
        )
        print(f"SUCCESS with {model}: {response.text}")
    except Exception as e:
        print(f"FAILED with {model}: {e}")
        if hasattr(e, 'status_code'):
            print(f"Status Code: {e.status_code}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
