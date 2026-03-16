"""
Google Vision Location Inference Service

Uses Google Cloud Vision API for:
- Landmark detection from photos
- Text extraction (street signs, building names)
- Location inference when GPS is unavailable
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
try:
    from google.cloud import vision
    from google.cloud.vision_v1 import types
    _VISION_AVAILABLE = True
except ImportError:
    vision = None
    types = None
    _VISION_AVAILABLE = False
import os

logger = logging.getLogger(__name__)


class LocationInferenceService:
    """Infers location from images using Google Vision API."""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Vision client.
        
        Args:
            credentials_path: Path to Google Cloud credentials JSON file.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        self.client = None
        if not _VISION_AVAILABLE:
            logger.warning("Google Vision not installed - location inference will use fallback methods")
            return
        try:
            if credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            self.client = vision.ImageAnnotatorClient()
            logger.info("Google Vision API initialized")
        except Exception as e:
            logger.warning("Google Vision API initialization failed: %s - using fallback methods", e)

    async def infer_location_from_photo(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        fallback_gps: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        Infer location from a photo using landmark detection and text extraction.
        
        Args:
            image_path: Path to image file
            image_bytes: Raw image bytes
            fallback_gps: Fallback GPS coordinates if inference fails
            
        Returns:
            {
                "inferred_location": [lat, lon],
                "confidence_score": 0.0-1.0,
                "method": "landmark|text|gps|fallback",
                "detected_landmarks": ["Apollo Hospital", "Main Street"],
                "extracted_text": ["Street sign text"],
                "details": {...}
            }
        """
        
        if not self.client:
            return self._fallback_inference(fallback_gps)
        
        try:
            # Load image
            image = types.Image()
            if image_path:
                with open(image_path, 'rb') as f:
                    image.content = f.read()
            elif image_bytes:
                image.content = image_bytes
            else:
                return self._fallback_inference(fallback_gps)

            # Run landmark detection
            landmark_response = self.client.landmark_detection(image)
            
            # Run text detection
            text_response = self.client.text_detection(image)

            return self._process_vision_response(
                landmark_response,
                text_response,
                fallback_gps
            )

        except Exception as e:
            logger.warning(f"Vision API error: {e}")
            return self._fallback_inference(fallback_gps)

    def _process_vision_response(
        self,
        landmark_response,
        text_response,
        fallback_gps: Optional[Tuple[float, float]]
    ) -> Dict[str, Any]:
        """Process Vision API responses and infer location."""
        
        detected_landmarks = []
        extracted_text = []
        inferred_location = None
        confidence = 0.0
        method = "fallback"

        # Extract landmarks
        if landmark_response.landmark_annotations:
            for landmark in landmark_response.landmark_annotations:
                detected_landmarks.append({
                    "name": landmark.description,
                    "confidence": landmark.score,
                    "locations": [
                        {
                            "lat": loc.lat_lng.latitude,
                            "lng": loc.lat_lng.longitude
                        }
                        for loc in landmark.locations
                    ]
                })
            
            # Use highest confidence landmark
            if detected_landmarks:
                top_landmark = max(detected_landmarks, key=lambda x: x["confidence"])
                if top_landmark["locations"]:
                    inferred_location = [
                        top_landmark["locations"][0]["lat"],
                        top_landmark["locations"][0]["lng"]
                    ]
                    confidence = top_landmark["confidence"]
                    method = "landmark"
                    logger.info(f"Landmark detected: {top_landmark['name']} (confidence: {confidence:.2f})")

        # Extract text (street signs, building names)
        if text_response.text_annotations:
            for annotation in text_response.text_annotations[1:]:  # Skip first (full text)
                extracted_text.append(annotation.description)

        # Fallback if needed
        if inferred_location is None and fallback_gps:
            inferred_location = list(fallback_gps)
            confidence = 0.5
            method = "gps_fallback"

        return {
            "inferred_location": inferred_location,
            "confidence_score": confidence,
            "method": method,
            "detected_landmarks": [lm["name"] for lm in detected_landmarks],
            "extracted_text": extracted_text,
            "details": {
                "landmarks": detected_landmarks,
                "text_annotations": extracted_text
            }
        }

    def _fallback_inference(self, fallback_gps: Optional[Tuple[float, float]]) -> Dict[str, Any]:
        """Return fallback inference result."""
        if fallback_gps:
            return {
                "inferred_location": list(fallback_gps),
                "confidence_score": 0.5,
                "method": "gps_fallback",
                "detected_landmarks": [],
                "extracted_text": [],
                "details": {"reason": "Using fallback GPS location"}
            }
        else:
            return {
                "inferred_location": None,
                "confidence_score": 0.0,
                "method": "unknown",
                "detected_landmarks": [],
                "extracted_text": [],
                "details": {"reason": "No image and no fallback GPS provided"}
            }

    @staticmethod
    def landmark_to_coordinates(landmark_name: str) -> Optional[Tuple[float, float]]:
        """
        Hardcoded mapping of common landmarks to coordinates.
        In production, query a landmark database or geocoding service.
        """
        landmark_db = {
            # Indore landmarks
            "Indore Apollo Hospital": (22.7533, 75.8937),
            "CHL Hospital": (22.7441, 75.8901),
            "Medanta Super Specialty": (22.7600, 75.9000),
            "Bhawarkuan Square": (22.7400, 75.8950),
            "Moodh Bazaar": (22.7300, 75.9100),
            "Main Street": (22.7450, 75.8950),
            
            # Bangalore landmarks
            "Bangalore Apollo Hospital": (13.0382, 77.6245),
            "St. Johns Medical College": (13.0365, 77.6245),
            "Koramangala": (12.9352, 77.6245),
            "Whitefield": (12.9698, 77.7499),
            
            # Delhi landmarks
            "AIIMS Delhi": (28.5673, 77.2074),
            "Fortis Hospital Delhi": (28.5500, 77.1950),
            "Connaught Place": (28.6328, 77.1899),
        }
        
        return landmark_db.get(landmark_name)


# Global instance
location_inference_service = LocationInferenceService()
