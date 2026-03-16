"""
scene_model.py - Image Scene Classification for Location Context

THIS IS YOUR CORE CONTRIBUTION TO THE TEAM PROJECT.

While Team 2 extracts text and Team 3 does OCR, YOUR job is to:
1. Analyze the image for VISUAL context clues
2. Identify scene types (bridge, flyover, residential, etc.)
3. Detect infrastructure that helps narrow down location
4. Use these clues to boost geocoding accuracy

Uses a pre-trained CNN (MobileNetV2/ResNet) for scene classification.
"""

import os
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import numpy as np

# Try to import PyTorch
try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    from torchvision import models
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[scene_model] PyTorch not installed. Install with: pip install torch torchvision")


# Scene categories that help with location inference
# These are the classes YOUR model will classify images into
SCENE_CATEGORIES = {
    0: "urban_road",       # City streets, traffic signals, vehicles
    1: "bridge_flyover",   # Bridges, flyovers, underpasses
    2: "residential",      # Housing areas, apartments, colonies
    3: "water_flood",      # Rivers, lakes, flooded areas
    4: "rural",            # Villages, farmland, open areas
    5: "commercial",       # Shops, markets, malls
    6: "landmark",         # Temples, churches, monuments
    7: "transit",          # Bus stops, metro stations, railways
    8: "industrial",       # Factories, warehouses
    9: "unknown"           # Cannot determine
}

# Location keywords to search for based on scene type
SCENE_LOCATION_HINTS = {
    "urban_road": ["junction", "signal", "road", "highway", "main road", "circle"],
    "bridge_flyover": ["bridge", "flyover", "underpass", "overpass", "elevated"],
    "residential": ["layout", "nagar", "colony", "apartments", "enclave", "phase"],
    "water_flood": ["lake", "river", "tank", "canal", "nala", "kere"],
    "rural": ["village", "gram", "halli", "rural"],
    "commercial": ["market", "mall", "complex", "plaza", "bazaar"],
    "landmark": ["temple", "church", "mosque", "stadium", "park", "garden"],
    "transit": ["bus stand", "metro", "station", "terminal", "depot"],
    "industrial": ["industrial", "factory", "zone", "area"],
    "unknown": []
}


class SceneClassifier:
    """
    CNN-based scene classifier for extracting location context from images.
    
    This is the CORE of your geo module's image analysis.
    It uses transfer learning from MobileNetV2 (lightweight, fast).
    """
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        """
        Initialize the scene classifier.
        
        Args:
            model_path: Path to your fine-tuned model weights (optional)
            device: 'cpu' or 'cuda' for GPU
        """
        self.device = device
        self.model = None
        self.transform = None
        self.num_classes = len(SCENE_CATEGORIES)
        
        if TORCH_AVAILABLE:
            self._setup_model(model_path)
            self._setup_transforms()
    
    def _setup_transforms(self):
        """Setup image preprocessing for the model."""
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def _setup_model(self, model_path: Optional[str]):
        """
        Setup the CNN model.
        
        Uses MobileNetV2 pretrained on ImageNet.
        If you have fine-tuned weights, load them.
        """
        try:
            # Load pretrained MobileNetV2
            self.model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
            
            # Replace classifier for our scene classes
            # MobileNetV2 has classifier[1] as the final layer
            in_features = self.model.classifier[1].in_features
            self.model.classifier[1] = nn.Linear(in_features, self.num_classes)
            
            # Check for trained model in standard location
            trained_model_path = model_path or "models/scene_classifier.pth"
            
            if os.path.exists(trained_model_path):
                state_dict = torch.load(trained_model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print(f"[SceneClassifier] ✅ Loaded trained model from {trained_model_path}")
            else:
                print("[SceneClassifier] Using ImageNet pretrained weights (not fine-tuned for scenes)")
                print("[SceneClassifier] For better accuracy, train on disaster scene dataset")
            
            self.model.to(self.device)
            self.model.eval()
            
        except Exception as e:
            print(f"[SceneClassifier] Error setting up model: {e}")
            self.model = None
    
    def classify(self, image_path: str) -> Dict[str, Any]:
        """
        Classify an image and return scene context.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with:
                - scene_type: Predicted scene category
                - confidence: Prediction confidence (0-1)
                - top_3: Top 3 predictions with scores
                - location_hints: Keywords to help geocoding
                - features: Key visual features detected
        """
        if not TORCH_AVAILABLE:
            return self._fallback_analysis(image_path)
        
        if self.model is None:
            return self._fallback_analysis(image_path)
        
        if not os.path.exists(image_path):
            return {"error": "Image file not found", "scene_type": "unknown", "confidence": 0.0}
        
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Run inference
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)[0]
            
            # Get top predictions
            top_probs, top_indices = torch.topk(probabilities, k=min(3, self.num_classes))
            
            # Primary prediction
            top_idx = top_indices[0].item()
            scene_type = SCENE_CATEGORIES.get(top_idx, "unknown")
            confidence = top_probs[0].item()
            
            # Top 3 predictions
            top_3 = []
            for prob, idx in zip(top_probs, top_indices):
                scene = SCENE_CATEGORIES.get(idx.item(), "unknown")
                top_3.append({"scene": scene, "confidence": round(prob.item(), 3)})
            
            # Get location hints for this scene type
            location_hints = SCENE_LOCATION_HINTS.get(scene_type, [])
            
            # Analyze visual features
            features = self._analyze_features(image)
            
            return {
                "scene_type": scene_type,
                "confidence": round(confidence, 3),
                "top_3": top_3,
                "location_hints": location_hints,
                "features": features,
                "image_size": image.size,
                "analysis_method": "cnn"
            }
            
        except Exception as e:
            return {"error": str(e), "scene_type": "unknown", "confidence": 0.0}
    
    def _analyze_features(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze visual features that might indicate location.
        
        This extracts:
        - Dominant colors (water = blue, vegetation = green)
        - Brightness (night vs day)
        - Texture patterns
        """
        # Resize for fast analysis
        small = image.resize((100, 100))
        pixels = np.array(small)
        
        # Average color channels
        avg_r = np.mean(pixels[:, :, 0])
        avg_g = np.mean(pixels[:, :, 1])
        avg_b = np.mean(pixels[:, :, 2])
        
        # Brightness
        brightness = (avg_r + avg_g + avg_b) / 3 / 255
        
        # Dominant color category
        if avg_b > avg_r and avg_b > avg_g:
            dominant = "blue"  # Possibly water
        elif avg_g > avg_r and avg_g > avg_b:
            dominant = "green"  # Vegetation
        elif avg_r > avg_g and avg_r > avg_b:
            dominant = "red"  # Possibly urban/construction
        else:
            dominant = "neutral"  # Gray/mixed
        
        # Check for water indicators
        has_water_tones = avg_b > 100 and avg_b > avg_r
        
        # Check for vegetation
        has_vegetation = avg_g > 100 and avg_g > avg_r * 1.2
        
        return {
            "dominant_color": dominant,
            "brightness": round(brightness, 2),
            "has_water_tones": has_water_tones,
            "has_vegetation": has_vegetation,
            "is_daytime": brightness > 0.3
        }
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """
        Fallback analysis when PyTorch is not available.
        Uses basic image properties and color analysis.
        """
        try:
            image = Image.open(image_path).convert('RGB')
            features = self._analyze_features_basic(image)
            
            # Guess scene based on colors
            scene_type = "unknown"
            confidence = 0.3
            
            if features.get("has_water_tones"):
                scene_type = "water_flood"
                confidence = 0.4
            elif features.get("has_vegetation"):
                scene_type = "rural"
                confidence = 0.35
            elif features.get("dominant_color") == "neutral":
                scene_type = "urban_road"
                confidence = 0.3
            
            return {
                "scene_type": scene_type,
                "confidence": confidence,
                "top_3": [{"scene": scene_type, "confidence": confidence}],
                "location_hints": SCENE_LOCATION_HINTS.get(scene_type, []),
                "features": features,
                "analysis_method": "heuristic (install PyTorch for CNN)"
            }
            
        except Exception as e:
            return {"error": str(e), "scene_type": "unknown", "confidence": 0.0}
    
    def _analyze_features_basic(self, image: Image.Image) -> Dict[str, Any]:
        """Basic feature analysis without numpy."""
        small = image.resize((50, 50))
        pixels = list(small.getdata())
        
        avg_r = sum(p[0] for p in pixels) / len(pixels)
        avg_g = sum(p[1] for p in pixels) / len(pixels)
        avg_b = sum(p[2] for p in pixels) / len(pixels)
        
        brightness = (avg_r + avg_g + avg_b) / 3 / 255
        
        if avg_b > avg_r and avg_b > avg_g:
            dominant = "blue"
        elif avg_g > avg_r and avg_g > avg_b:
            dominant = "green"
        else:
            dominant = "neutral"
        
        return {
            "dominant_color": dominant,
            "brightness": round(brightness, 2),
            "has_water_tones": avg_b > 100 and avg_b > avg_r,
            "has_vegetation": avg_g > 100 and avg_g > avg_r,
            "is_daytime": brightness > 0.3
        }


# Module-level classifier instance
_classifier: Optional[SceneClassifier] = None


def get_classifier(model_path: Optional[str] = None) -> SceneClassifier:
    """Get or create the scene classifier."""
    global _classifier
    if _classifier is None:
        _classifier = SceneClassifier(model_path)
    return _classifier


def analyze_image(image_path: str) -> Dict[str, Any]:
    """
    Analyze an image for location context.
    
    This is the main function to call from geo_pipeline.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dict with scene classification and location hints
    """
    return get_classifier().classify(image_path)


def get_location_boost(scene_result: Dict[str, Any], location_name: str) -> float:
    """
    Calculate confidence boost based on scene-location match.
    
    If the detected scene matches keywords in the geocoded location,
    we boost the confidence score.
    
    Args:
        scene_result: Result from analyze_image()
        location_name: Display name from geocoding
        
    Returns:
        Boost value (0.0 to 0.2)
    """
    if not scene_result or not location_name:
        return 0.0
    
    scene_type = scene_result.get("scene_type", "unknown")
    hints = SCENE_LOCATION_HINTS.get(scene_type, [])
    
    location_lower = location_name.lower()
    
    for hint in hints:
        if hint.lower() in location_lower:
            # Scene matches location - boost confidence
            return 0.15
    
    # Check if visual features match
    features = scene_result.get("features", {})
    
    if features.get("has_water_tones") and ("lake" in location_lower or "river" in location_lower):
        return 0.1
    
    if features.get("has_vegetation") and ("garden" in location_lower or "park" in location_lower):
        return 0.1
    
    return 0.0


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("SCENE CLASSIFIER - Image Context Analysis")
    print("=" * 60)
    print()
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    print()
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Analyzing: {image_path}")
        print()
        
        result = analyze_image(image_path)
        
        print(f"Scene Type: {result.get('scene_type', 'unknown')}")
        print(f"Confidence: {result.get('confidence', 0):.1%}")
        print()
        
        if result.get('top_3'):
            print("Top 3 Predictions:")
            for pred in result['top_3']:
                print(f"  - {pred['scene']}: {pred['confidence']:.1%}")
        
        print()
        print(f"Location Hints: {result.get('location_hints', [])}")
        
        if result.get('features'):
            print()
            print("Visual Features:")
            for k, v in result['features'].items():
                print(f"  - {k}: {v}")
        
        print()
        print(f"Analysis Method: {result.get('analysis_method', 'unknown')}")
    else:
        print("Usage: python -m geo.scene_model <image_path>")
        print()
        print("Example:")
        print("  python -m geo.scene_model flood_image.jpg")
