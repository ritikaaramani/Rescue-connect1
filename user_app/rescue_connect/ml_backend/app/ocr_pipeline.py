"""
ocr_pipeline.py - OCR Text Extraction from Disaster Images

Adapted from OCR-Module/inference/yolo_ocr_pipeline.py for integration.
Provides a class-based OCR pipeline that can process image URLs and bytes.
"""

import os
import cv2
import numpy as np
import pytesseract
import tempfile
import httpx
from typing import Dict, Any, List, Optional
from PIL import Image
from io import BytesIO

# Try to import YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[OCR] Warning: ultralytics not installed. Install with: pip install ultralytics")

# Configure Tesseract path from environment or use default
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH", 
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    print(f"[OCR] Warning: Tesseract not found at {TESSERACT_PATH}")


class OCRPipeline:
    """
    OCR Pipeline for extracting text from disaster images.
    Uses YOLO for text region detection and Tesseract for OCR.
    """
    
    def __init__(self, yolo_model_path: Optional[str] = None):
        """
        Initialize the OCR pipeline.
        
        Args:
            yolo_model_path: Path to YOLO model weights (optional)
        """
        self.yolo_model = None
        self.yolo_available = YOLO_AVAILABLE
        
        if YOLO_AVAILABLE and yolo_model_path and os.path.exists(yolo_model_path):
            try:
                self.yolo_model = YOLO(yolo_model_path)
                print(f"[OCR] Loaded YOLO model from {yolo_model_path}")
            except Exception as e:
                print(f"[OCR] Failed to load YOLO model: {e}")
    
    async def extract_from_url(self, image_url: str) -> Dict[str, Any]:
        """
        Extract text from an image URL.
        
        Args:
            image_url: URL of the image to process
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image_bytes = response.content
            
            return self.extract_from_bytes(image_bytes)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "regions": []
            }
    
    def extract_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            # Convert bytes to OpenCV image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {
                    "success": False,
                    "error": "Failed to decode image",
                    "extracted_text": "",
                    "regions": []
                }
            
            return self._process_image(image)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "regions": []
            }
    
    def extract_from_path(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image file path.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            image = cv2.imread(image_path)
            
            if image is None:
                return {
                    "success": False,
                    "error": "Failed to read image file",
                    "extracted_text": "",
                    "regions": []
                }
            
            return self._process_image(image)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "regions": []
            }
    
    def _process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process an OpenCV image and extract text.
        
        Args:
            image: OpenCV image array (BGR)
            
        Returns:
            Dict with extracted text and metadata
        """
        regions = []
        all_text = []
        
        # If YOLO model is available, use it for text detection
        if self.yolo_model is not None:
            regions = self._extract_with_yolo(image)
            all_text = [r["text"] for r in regions if r.get("text")]
        else:
            # Fallback: Direct OCR on whole image with preprocessing
            text = self._direct_ocr(image)
            if text:
                all_text = [text]
                regions = [{
                    "text": text,
                    "confidence": 0.5,
                    "method": "direct_ocr"
                }]
        
        # Combine all extracted text
        combined_text = " ".join(all_text).strip()
        
        return {
            "success": True,
            "extracted_text": combined_text,
            "regions": regions,
            "num_regions": len(regions),
            "method": "yolo" if self.yolo_model else "direct"
        }
    
    def _extract_with_yolo(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract text using YOLO for region detection.
        
        Args:
            image: OpenCV image
            
        Returns:
            List of detected text regions
        """
        regions = []
        
        try:
            # Run YOLO detection
            results = self.yolo_model(image, conf=0.02, imgsz=960)
            
            for idx, box in enumerate(results[0].boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                
                # Crop detected region
                crop = image[y1:y2, x1:x2]
                
                if crop.size == 0:
                    continue
                
                # OCR on cropped region
                text = self._ocr_region(crop)
                
                regions.append({
                    "text": text,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                    "method": "yolo_ocr"
                })
            
        except Exception as e:
            print(f"[OCR] YOLO extraction error: {e}")
        
        return regions
    
    def _ocr_region(self, crop: np.ndarray) -> str:
        """
        Perform OCR on a cropped image region with preprocessing.
        
        Args:
            crop: Cropped image region
            
        Returns:
            Extracted text
        """
        try:
            # Preprocessing
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            _, thresh = cv2.threshold(
                enhanced, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            
            # OCR
            text = pytesseract.image_to_string(
                thresh,
                config="--oem 3 --psm 6"
            ).strip()
            
            return text
            
        except Exception as e:
            print(f"[OCR] Region OCR error: {e}")
            return ""
    
    def _direct_ocr(self, image: np.ndarray) -> str:
        """
        Perform direct OCR on the full image.
        
        Args:
            image: OpenCV image
            
        Returns:
            Extracted text
        """
        try:
            # Convert to PIL Image for Tesseract
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb)
            
            # Direct OCR
            text = pytesseract.image_to_string(
                pil_image,
                config="--oem 3 --psm 3"
            ).strip()
            
            return text
            
        except Exception as e:
            print(f"[OCR] Direct OCR error: {e}")
            return ""


# Module-level pipeline instance
_pipeline: Optional[OCRPipeline] = None


def get_pipeline(yolo_model_path: Optional[str] = None) -> OCRPipeline:
    """Get or create the OCR pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = OCRPipeline(yolo_model_path)
    return _pipeline


async def extract_text_from_url(image_url: str) -> Dict[str, Any]:
    """
    Convenience function to extract text from an image URL.
    
    Args:
        image_url: URL of the image
        
    Returns:
        Dict with extracted text and metadata
    """
    return await get_pipeline().extract_from_url(image_url)


def extract_text_from_path(image_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract text from an image file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dict with extracted text and metadata
    """
    return get_pipeline().extract_from_path(image_path)
