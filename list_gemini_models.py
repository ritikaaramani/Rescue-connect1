
import sys
import os
import asyncio
from dotenv import load_dotenv

# Use forward slashes
sys.path.append('c:/Ritika/RescueConnect-indorehacky/user_app/rescue_connect/ml_backend')

from app.image_analyzer import ImageAnalyzer

async def list_models():
    load_dotenv('c:/Ritika/RescueConnect-indorehacky/user_app/rescue_connect/ml_backend/.env')
    analyzer = ImageAnalyzer()
    
    from google import genai
    
    print(f"Listing models for API Key: {analyzer.gemini_key[:5]}...")
    client = genai.Client(api_key=analyzer.gemini_key)
    
    try:
        # List models
        for model in client.models.list():
            print(f"- {model.name} (Methods: {model.supported_methods})")
    except Exception as e:
        print(f"FAILED to list models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
