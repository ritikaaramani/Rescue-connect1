"""
Image Analysis Service using Vision Language Models

Supports both Google Gemini (free) and OpenAI GPT-4 Vision.
"""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


class ImageAnalyzer:
    """Analyzes disaster images using Gemini or OpenAI Vision models."""

    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        
        if self.provider == "gemini" and self.gemini_key and self.gemini_key != "your-gemini-api-key-here":
            print("✅ Using Google Gemini for image analysis")
            self.active_provider = "gemini"
        elif self.openai_key:
            print("✅ Using OpenAI GPT-4 Vision for image analysis")
            self.active_provider = "openai"
        elif self.gemini_key and self.gemini_key != "your-gemini-api-key-here":
            print("✅ Using Google Gemini for image analysis")
            self.active_provider = "gemini"
        else:
            print("⚠️ No API key configured - using basic analysis only")
            self.active_provider = None

    async def analyze_image(self, image_url: str) -> dict:
        """
        Analyze an image and extract disaster-related information.
        """
        try:
            if self.active_provider == "gemini":
                return await self._analyze_with_gemini(image_url)
            elif self.active_provider == "openai":
                return await self._analyze_with_openai(image_url)
            else:
                return await self._basic_analysis(image_url)
                
        except Exception as e:
            print(f"❌ Error analyzing image: {e}")
            return self._default_response(str(e))

    def _get_prompt(self) -> str:
        """Get the flood detection prompt."""
        return """Analyze this image for DISASTER response (specifically FLOODS).

You MUST respond with ONLY valid JSON (no markdown, no explanation, no code blocks):
{
    "is_disaster": true or false,
    "disaster_type": "flood" or "none",
    "severity": "low" or "medium" or "high" or "critical",
    "description": "Brief description of what you see",
    "detected_elements": ["element1", "element2"],
    "location_hints": ["visually identified location name", "landmarks", "text on signs"],
    "people_affected": "none" or "few" or "many" or "crowd",
    "urgency_score": 1-10
}

IMPORTANT RULES:
1. **STRICT FLOOD CRITERIA**: Set is_disaster=true ONLY if you see ACTUAL UNCONTROLLED FLOODING that causes disruption or danger:
   - Submerged infrastructure (roads completely under water, vehicles stuck).
   - Water entering homes, shops, or buildings.
   - People/Animals wading through knee-deep (or deeper) dirty/flood water.
   - Rivers explicitly overflowing banks and flooding surrounding land.
   - Rescue operations (boats on streets).

2. **FALSE POSITIVES (Set is_disaster=false)**:
   - **Recreational**: Water parks, swimming pools, beaches, lakes, boating, surfing, people playing in rain/puddles.
   - **Weather**: Wet roads/pavement (rainy day), gray skies, small puddles, splashing cars (unless submerged).
   - **Controlled**: Canals, dams, irrigation channels, fountains.
   - **Context**: Movies, cartoons, memes, or screenshots unless they clearly depict a real-world disaster scenario.

3. **DECISION THRESHOLD**: If the scene looks like "normal life" or "fun" or "just wet", it is NOT a disaster. Only flag if it looks "abnormal", "dangerous", or "disruptive".
3. **LOCATION**: If you see a specific place name (e.g., on a sign like "Wonderla"), distinct landmark, or city skyline, include it in "location_hints".
4. **VISIBLE TEXT**: transcribe any readable text on signs, billboards, or buildings into "visible_text". This is CRITICAL for identifying the location.
5. Only respond with the JSON object, nothing else.

JSON Format:
{
    "is_disaster": boolean,
    "disaster_type": "string or null",
    "severity": "critical/high/medium/low",
    "description": "string",
    "location_hints": ["list", "of", "strings"],
    "visible_text": "string (all text seen in image)"
}"""

    async def _analyze_with_gemini(self, image_url: str) -> dict:
        """Analyze image using Google Gemini."""
        # Use the new google-genai package (google.generativeai is deprecated)
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=self.gemini_key)
        
        # Try different models in order of preference
        # Updated: use current stable models that support vision
        models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
        last_error = None
        
        for model_name in models_to_try:
            try:
                print(f"🔍 Trying model: {model_name}")
                
                # Download image
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.get(image_url)
                    image_data = response.content
                
                # Create image part for Gemini using new SDK
                image_part = types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/jpeg"
                )
                
                # Generate response using the new SDK
                response = client.models.generate_content(
                    model=model_name,
                    contents=[self._get_prompt(), image_part]
                )
                content = response.text
                
                print(f"📝 Gemini response: {content[:200]}...")
                
                return self._parse_json_response(content)
                    
            except Exception as e:
                print(f"⚠️ Model {model_name} failed: {e}")
                last_error = e
                continue
        
        # All models failed
        print(f"❌ All Gemini models failed")
        return self._default_response(f"Gemini error: {str(last_error)}")

    async def _analyze_with_openai(self, image_url: str) -> dict:
        """Analyze image using OpenAI GPT-4 Vision."""
        from openai import OpenAI
        
        client = OpenAI(api_key=self.openai_key)
        
        try:
            print(f"🔍 Analyzing with OpenAI: {image_url[:80]}...")
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._get_prompt()},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            print(f"📝 OpenAI response: {content[:200]}...")
            
            return self._parse_json_response(content)
                
        except Exception as e:
            print(f"❌ OpenAI error: {type(e).__name__}: {e}")
            return self._default_response(f"OpenAI error: {str(e)}")

    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from AI response."""
        try:
            # Clean up response - remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Find JSON object
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                result = json.loads(json_str)
                
                return {
                    "is_disaster": result.get("is_disaster", False),
                    "disaster_type": result.get("disaster_type", "unknown"),
                    "severity": result.get("severity", "medium"),
                    "description": result.get("description", "Analysis complete"),
                    "detected_elements": result.get("detected_elements", []),
                    "location_hints": result.get("location_hints", []) if isinstance(result.get("location_hints"), list) else [result.get("location_hints")] if result.get("location_hints") else [],
                    "visible_text": result.get("visible_text", ""), # Captured from prompt
                    "people_affected": result.get("people_affected", "unknown"),
                    "urgency_score": int(result.get("urgency_score", 5))
                }
            else:
                return self._default_response("No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            return self._default_response(f"JSON parse error: {str(e)}")

    async def _basic_analysis(self, image_url: str) -> dict:
        """Basic analysis when no AI model is available."""
        return {
            "is_disaster": True,
            "disaster_type": "unknown",
            "severity": "medium",
            "description": "Image uploaded - requires manual review (no AI key configured)",
            "detected_elements": ["image"],
            "location_hints": "",
            "people_affected": "unknown",
            "urgency_score": 5
        }

    def _default_response(self, error: str = "") -> dict:
        """Return default response when analysis fails."""
        return {
            "is_disaster": False,
            "disaster_type": "unknown",
            "severity": "unknown",
            "description": f"Analysis failed: {error}" if error else "Could not analyze image",
            "detected_elements": [],
            "location_hints": "",
            "people_affected": "unknown",
            "urgency_score": 0
        }


# Singleton instance
analyzer = ImageAnalyzer()
