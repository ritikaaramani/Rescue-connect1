"""
Image Analysis Service using Vision Language Models

Supports Google Gemini, OpenAI GPT-4 Vision, and Groq (Llama Vision).
"""

import os
import json
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()


class ImageAnalyzer:
    """Analyzes disaster images using Gemini, OpenAI, or Groq Vision models."""

    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        
        if self.provider == "groq" and self.groq_key:
            print("[OK] Using Groq (Llama Vision) for image analysis")
            self.active_provider = "groq"
        elif self.provider == "gemini" and self.gemini_key and self.gemini_key != "your-gemini-api-key-here":
            print("[OK] Using Google Gemini for image analysis")
            self.active_provider = "gemini"
        elif self.provider == "openai" and self.openai_key:
            print("[OK] Using OpenAI GPT-4 Vision for image analysis")
            self.active_provider = "openai"
        elif self.groq_key:
            print("[OK] Falling back to Groq (Llama Vision) for image analysis")
            self.active_provider = "groq"
        elif self.gemini_key and self.gemini_key != "your-gemini-api-key-here":
            print("[OK] Falling back to Google Gemini for image analysis")
            self.active_provider = "gemini"
        elif self.openai_key:
            print("[OK] Falling back to OpenAI for image analysis")
            self.active_provider = "openai"
        else:
            print("[WARN] No API key configured - using basic analysis only")
            self.active_provider = None

    async def analyze_image(self, image_url: str) -> dict:
        """
        Analyze an image and extract disaster-related information.
        """
        try:
            if self.active_provider == "groq":
                result = await self._analyze_with_groq(image_url)
                # If Groq failed (returned default error), try Gemini as fallback
                if not result.get("is_disaster", False) and "error" in result.get("description", "").lower():
                    print("[WARN] Groq failed, attempting Gemini fallback...")
                    if self.gemini_key and self.gemini_key != "your-gemini-api-key-here":
                        return await self._analyze_with_gemini(image_url)
                return result
            elif self.active_provider == "gemini":
                return await self._analyze_with_gemini(image_url)
            elif self.active_provider == "openai":
                return await self._analyze_with_openai(image_url)
            else:
                return await self._basic_analysis(image_url)
                
        except Exception as e:
            print(f"[ERROR] Error analyzing image: {e}")
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
    "visible_text": "any readable text found in the image (signboards, shop names, street signs)",
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

CRITICAL FOR LOCATION:
- If you see ANY landmark (e.g., "Gateway of India", "Charminar", "Vidhana Soudha"), include it.
- If you see ANY city name (e.g., "Mumbai", "Bangalore", "Chennai"), include it.
- If you see ANY street signs or shop names that hint at a location, include them.
- Include these in "location_hints". This is what we use for geocoding. Be as specific as possible.
- If you see a specific area name (e.g., "Indiranagar", "Thane", "Noida Sector 18"), include it."""

    async def _analyze_with_groq(self, image_url: str) -> dict:
        """Analyze image using Groq (Llama Vision) - OpenAI-compatible API."""
        try:
            print(f"[INFO] Analyzing with Groq: {image_url[:80]}...")
            
            # Groq vision models to try (current as of 2026)
            models_to_try = [
                "meta-llama/llama-4-scout-17b-16e-instruct",
                "meta-llama/llama-4-maverick-17b-128e-instruct",
            ]
            last_error = None
            
            for model_name in models_to_try:
                try:
                    print(f"[INFO] Trying Groq model: {model_name}")
                    
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.groq_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": model_name,
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": self._get_prompt()},
                                            {
                                                "type": "image_url",
                                                "image_url": {
                                                    "url": image_url
                                                }
                                            }
                                        ]
                                    }
                                ],
                                "max_tokens": 1000,
                                "temperature": 0.1
                            }
                        )
                    
                    if response.status_code != 200:
                        error_text = response.text
                        print(f"[WARN] Groq model {model_name} returned {response.status_code}: {error_text[:200]}")
                        last_error = f"HTTP {response.status_code}: {error_text[:200]}"
                        continue
                    
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    print(f"[INFO] Groq response: {content[:200]}...")
                    
                    return self._parse_json_response(content)
                    
                except Exception as e:
                    print(f"[WARN] Groq model {model_name} failed: {e}")
                    last_error = e
                    continue
            
            # All models failed
            print("[ERROR] All Groq models failed")
            return self._default_response(f"Groq error: {str(last_error)}")
                
        except Exception as e:
            print(f"[ERROR] Groq error: {type(e).__name__}: {e}")
            return self._default_response(f"Groq error: {str(e)}")

    async def _analyze_with_gemini(self, image_url: str) -> dict:
        """Analyze image using Google Gemini."""
        # Use the Generative Language REST API directly to avoid SDK/model-version
        # mismatches (we've seen 404s for older model ids via some SDK paths).
        #
        # This matches the frontend's working pattern:
        #   /v1beta/models/<model>:generateContent

        # Allow override via env for quick hotfixes without code changes
        preferred_model = os.getenv("GEMINI_MODEL", "").strip()
        models_to_try = [
            preferred_model,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
        ]
        models_to_try = [m for m in models_to_try if m]

        last_error = None

        async with httpx.AsyncClient(timeout=90.0) as client:
            # Download image once
            try:
                img_res = await client.get(image_url)
                img_res.raise_for_status()
                image_bytes = img_res.content
            except Exception as e:
                return self._default_response(f"Gemini error: could not download image ({type(e).__name__}: {e})")

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            for model_name in models_to_try:
                try:
                    print(f"[INFO] Trying Gemini model: {model_name}")

                    url = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{model_name}:generateContent?key={self.gemini_key}"
                    )
                    payload = {
                        "contents": [
                            {
                                "parts": [
                                    {"text": self._get_prompt()},
                                    {
                                        "inline_data": {
                                            "mime_type": "image/jpeg",
                                            "data": image_b64,
                                        }
                                    },
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 1000,
                        },
                    }

                    res = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
                    if not res.ok:
                        # Preserve the real server message; model 404s are common.
                        try:
                            err_json = res.json()
                        except Exception:
                            err_json = {"error": {"message": res.text[:500]}}
                        last_error = f"{res.status_code} {err_json}"
                        print(f"[WARN] Gemini model {model_name} failed: {last_error}")
                        continue

                    data = res.json()
                    content = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    if not content:
                        last_error = f"Empty response from {model_name}: {str(data)[:300]}"
                        print(f"[WARN] Gemini model {model_name} returned empty text")
                        continue

                    print(f"[INFO] Gemini response: {content[:200]}...")
                    return self._parse_json_response(content)

                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    print(f"[WARN] Gemini model {model_name} exception: {last_error}")
                    continue

        print("[ERROR] All Gemini models failed")
        return self._default_response(f"Gemini error: {str(last_error)}")

    async def _analyze_with_openai(self, image_url: str) -> dict:
        """Analyze image using OpenAI GPT-4 Vision."""
        from openai import OpenAI
        
        client = OpenAI(api_key=self.openai_key)
        
        try:
            print(f"[INFO] Analyzing with OpenAI: {image_url[:80]}...")
            
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
            print(f"[INFO] OpenAI response: {content[:200]}...")
            
            return self._parse_json_response(content)
                
        except Exception as e:
            print(f"[ERROR] OpenAI error: {type(e).__name__}: {e}")
            return self._default_response(f"OpenAI error: {str(e)}")

    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from AI response."""
        try:
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
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
                    "visible_text": result.get("visible_text", ""),
                    "people_affected": result.get("people_affected", "unknown"),
                    "urgency_score": int(result.get("urgency_score", 5))
                }
            else:
                return self._default_response("No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parse error: {e}")
            return self._default_response(f"JSON parse error: {str(e)}")

    async def _basic_analysis(self, image_url: str) -> dict:
        """Basic analysis when no AI model is available."""
        return {
            "is_disaster": True,
            "disaster_type": "unknown",
            "severity": "medium",
            "description": "Image uploaded - requires manual review (no AI key configured)",
            "detected_elements": ["image"],
            "location_hints": [],
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
            "location_hints": [],
            "people_affected": "unknown",
            "urgency_score": 0
        }


# Singleton instance
analyzer = ImageAnalyzer()
